"""Small, read-only upstream code inventory. Presence is NOT implementation proof."""
import base64
import datetime as dt
import re
from collections import defaultdict
from urllib.parse import quote

SOURCE_EXT = ('.c', '.cc', '.cpp', '.cxx', '.h', '.hpp', '.rs', '.cs', '.zig', '.py', '.asm', '.s', '.glsl', '.hlsl', '.wgsl', '.ts', '.tsx', '.js')
IGNORED_SEGMENTS = {'third_party', 'third-party', 'vendor', 'node_modules', 'external', 'deps', 'dependency', 'dist', 'build', 'target', '.git', 'docs', 'documentation', 'tests', 'test', 'fixtures', 'samples', 'examples', 'benchmarks'}
VALID_STATES = {'implemented', 'partial', 'stub', 'not_started'}
VALID_EVIDENCE = {'claimed', 'independently_verified'}
CHECKBOX = re.compile(r'^\s*[-*]\s*\[([ xX])\]\s+(.+)$', re.MULTILINE)


def validate_catalog(catalog):
    ids = [f['id'] for f in catalog['features']]
    if len(ids) != len(set(ids)) or not ids:
        raise ValueError('Duplicate/empty feature catalog')
    for f in catalog['features']:
        if not re.fullmatch(r'[a-z0-9_]+', f['id']):
            raise ValueError('Invalid feature id')
        for pattern in f.get('patterns', []):
            re.compile(pattern, re.IGNORECASE)


def reviewed_features(raw, repo, catalog):
    valid_ids = {f['id'] for f in catalog['features']}
    source = raw.get('entries', {}).get(repo, {})
    if not isinstance(source, dict):
        raise ValueError(f'Invalid implementation entries: {repo}')
    out = {}
    for fid, item in source.items():
        if fid not in valid_ids:
            raise ValueError(f'Unknown feature {fid} for {repo}')
        if item.get('state') not in VALID_STATES or item.get('evidence') not in VALID_EVIDENCE:
            raise ValueError(f'Bad feature state/evidence: {repo}/{fid}')
        if not item.get('source', '').startswith('https://'):
            raise ValueError(f'Missing evidence URL: {repo}/{fid}')
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', item.get('reviewed_at', '')):
            raise ValueError(f'Missing review date: {repo}/{fid}')
        out[fid] = {k: item.get(k) for k in ('state', 'evidence', 'source', 'reviewed_at', 'note')}
    return out


def parse_published_metrics(text, rules, source):
    """Extract only explicitly scoped, repo-specific done/total figures."""
    output = []
    for rule in rules:
        match = re.search(rule["pattern"], text, re.IGNORECASE)
        if not match:
            continue
        try:
            done = int(match.group(rule.get("done_group", 1)).replace(",", "").replace(" ", ""))
            total = int(match.group(rule.get("total_group", 2)).replace(",", "").replace(" ", ""))
        except (ValueError, IndexError):
            continue
        if total <= 0 or total > 10_000_000 or not 0 <= done <= total:
            continue
        output.append({"id": rule["id"], "label": rule["label"],
                       "implemented": done, "total": total,
                       "status": "upstream_claim", "source": source,
                       "note": "README-reported count; denominator is limited to the upstream project's stated scope"})
    return output


def readme_status(repo, ref, api_get, rules):
    raw, _ = api_get(f'/repos/{repo}/readme', {'ref': ref}, missing_ok=True)
    if not raw or raw.get('encoding') != 'base64':
        return None, []
    text = base64.b64decode(raw.get('content', '')).decode('utf-8', errors='replace')
    checks = CHECKBOX.findall(text)
    source = f'https://github.com/{repo}/blob/{quote(ref, safe="")}/{raw.get("path", "README.md")}'
    checklist = None
    if checks:
        checklist = {'implemented': sum(mark.lower() == 'x' for mark, _ in checks),
                     'total': len(checks), 'source': source, 'kind': 'upstream_readme_tasks',
                     'note': 'Upstream README tasks, not verified API coverage or a full-emulator completion score'}
    return checklist, parse_published_metrics(text, rules, source)


def readme_checklist(repo, ref, api_get):
    return readme_status(repo, ref, api_get, [])[0]


def code_inventory(repo, ref, catalog, api_get):
    raw, _ = api_get(f'/repos/{repo}/git/trees/{quote(ref, safe="")}', {'recursive': '1'}, missing_ok=True)
    if not raw or 'tree' not in raw:
        return {'status': 'unavailable', 'truncated': None, 'source_files': None, 'features': []}
    paths = []
    for row in raw['tree']:
        path = row.get('path', '')
        parts = {p.lower() for p in path.split('/')}
        if row.get('type') != 'blob' or parts & IGNORED_SEGMENTS or not path.lower().endswith(SOURCE_EXT):
            continue
        if len(paths) >= 50000:
            break
        paths.append(path)
    features = []
    for feature in catalog['features']:
        patterns = [re.compile(pattern, re.IGNORECASE) for pattern in feature.get('patterns', [])]
        matching = [p for p in paths if any(pattern.search(p) for pattern in patterns)]
        if matching:
            features.append({'id': feature['id'], 'matching_files': len(matching), 'examples': [f'https://github.com/{repo}/blob/{quote(ref, safe="")}/{quote(p, safe="/")}' for p in matching[:3]]})
    return {'status': 'ok', 'truncated': bool(raw.get('truncated') or len(paths) >= 50000), 'source_files': len(paths), 'features': features, 'note': 'File-path matches are candidate code signals only, not confirmed implementations'}


def enrich_project(repo, ref, catalog, manual, api_get, metrics_rules=None):
    reviewed = reviewed_features(manual, repo, catalog)
    result = {'catalog_total': len(catalog['features']), 'reviewed': reviewed, 'verified_implemented': sum(v['state'] == 'implemented' and v['evidence'] == 'independently_verified' for v in reviewed.values()), 'claimed_implemented': sum(v['state'] == 'implemented' and v['evidence'] == 'claimed' for v in reviewed.values())}
    try:
        result['inventory'] = code_inventory(repo, ref, catalog, api_get)
    except Exception as exc:
        result['inventory'] = {'status': 'error', 'error': str(exc), 'features': [], 'source_files': None, 'truncated': None}
    try:
        result['checklist'], result['reported_metrics'] = readme_status(repo, ref, api_get, (metrics_rules or {}).get('rules', {}).get(repo, []))
    except Exception as exc:
        result['checklist_error'] = str(exc)
        result['checklist'] = None
        result['reported_metrics'] = []
    return result


def build_overlap(projects, catalog):
    index = defaultdict(list)
    for p in projects:
        inventory = (p.get('coverage') or {}).get('inventory') or {}
        if inventory.get('status') != 'ok':
            continue
        for row in inventory.get('features', []):
            index[row['id']].append({'repo': p['repo'], 'name': p['name'], 'matching_files': row['matching_files'], 'examples': row.get('examples', [])})
    return [dict(id=f['id'], title=f['title'], group=f['group'], description=f['description'], project_count=len(index[f['id']]), projects=index[f['id']]) for f in catalog['features']]


def estimate_catalog_eta(repo, current_count, total, histories, now):
    """Defensive forecast for *reviewed catalog items*, never for full emulation."""
    if total <= 0 or current_count <= 0 or current_count >= total or current_count < total * 0.25:
        return {'status': 'insufficient_data', 'reason': 'Need a meaningful independently verified catalog baseline and remaining items'}
    points = []
    for snap in histories:
        when = snap.get('generated_at')
        p = next((p for p in snap.get('projects', []) if p.get('repo') == repo), None)
        if not p:
            continue
        cov = p.get('coverage') or {}
        if cov.get('catalog_total') != total:
            continue
        count = cov.get('verified_implemented')
        if not isinstance(count, int) or not when:
            continue
        try:
            day = dt.date.fromisoformat(when[:10])
        except ValueError:
            continue
        points.append((day, count))
    points.append((now.date(), current_count))
    daily = dict(sorted(points))
    points = list(daily.items())
    if len(points) < 4 or (points[-1][0] - points[0][0]).days < 28:
        return {'status': 'insufficient_data', 'reason': 'Need four daily observations spanning at least 28 days'}
    increments = [b[1] - a[1] for a, b in zip(points, points[1:])]
    if sum(x > 0 for x in increments) < 2 or any(x < 0 for x in increments):
        return {'status': 'insufficient_data', 'reason': 'Need at least two independently verified increases without scope regressions'}
    elapsed = (points[-1][0] - points[0][0]).days
    velocity = (points[-1][1] - points[0][1]) / elapsed
    remaining_days = (total - current_count) / velocity if velocity > 0 else float('inf')
    if not 1 <= remaining_days <= 1095:
        return {'status': 'insufficient_data', 'reason': 'Observed trend cannot support a bounded three-year forecast'}
    target = now.date() + dt.timedelta(days=round(remaining_days))
    return {'status': 'experimental', 'target_date': target.isoformat(), 'days_remaining': round(remaining_days), 'rate_features_per_30d': round(velocity * 30, 2), 'sample_days': elapsed, 'observations': len(points), 'scope': 'Only independently verified items in this fixed catalog. NOT full Xbox Series emulation or GTA VI playability.'}


def estimate_reported_metric_eta(repo, metric_id, completed, total, histories, now):
    """Trend for one unchanged upstream-declared denominator, never overall emulation."""
    if not isinstance(completed, int) or not isinstance(total, int) or total <= 0 or completed < 0 or completed > total:
        return {'status': 'insufficient_data', 'reason': 'Invalid declared metric'}
    if completed == total:
        return {'status': 'scope_complete', 'reason': 'Upstream reports 100% of this declared scope; functionality is not independently verified'}
    if completed < total * 0.1:
        return {'status': 'insufficient_data', 'reason': 'Less than 10% of declared scope observed'}
    points = []
    for snap in histories:
        when = snap.get('generated_at')
        project = next((p for p in snap.get('projects', []) if p.get('repo') == repo), None)
        if not project or not when:
            continue
        cov = project.get('coverage') or {}
        metrics = list(cov.get('reported_metrics') or [])
        if cov.get('checklist'):
            metrics.append({'id': 'readme_tasks', **cov['checklist']})
        metric = next((m for m in metrics if m.get('id') == metric_id and m.get('total') == total), None)
        if metric is None or not isinstance(metric.get('implemented'), int):
            continue
        try:
            day = dt.date.fromisoformat(when[:10])
        except ValueError:
            continue
        points.append((day, metric['implemented']))
    points.append((now.date(), completed))
    points = list(dict(sorted(points)).items())
    if len(points) < 4 or (points[-1][0] - points[0][0]).days < 28:
        return {'status': 'insufficient_data', 'reason': 'Need at least 4 daily observations over 28 days with a stable denominator'}
    gains = [b[1] - a[1] for a, b in zip(points, points[1:])]
    if any(x < 0 for x in gains) or sum(x > 0 for x in gains) < 2:
        return {'status': 'insufficient_data', 'reason': 'Need two separate increases and no reported regressions'}
    elapsed = (points[-1][0] - points[0][0]).days
    per_day = (points[-1][1] - points[0][1]) / elapsed
    remaining = (total - completed) / per_day if per_day > 0 else float('inf')
    if not 1 <= remaining <= 1095:
        return {'status': 'insufficient_data', 'reason': 'Insufficient trend to project within three years'}
    return {'status': 'experimental',
            'target_date': (now.date() + dt.timedelta(days=round(remaining))).isoformat(),
            'rate_per_30d': round(per_day * 30, 2), 'sample_days': elapsed,
            'scope': 'Upstream-reported fixed denominator only; not a full-emulator or GTA VI ETA'}
