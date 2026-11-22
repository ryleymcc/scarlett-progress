#!/usr/bin/env python3
"""Build a fully automated, GitHub-only Xbox Series X|S progress index.

Uses Python standard library; a public GITHUB_TOKEN is strongly recommended to
avoid the anonymous API quota. Run from any directory.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import capability_scan
import api_matrix

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com"
PER_PAGE = 100
MAX_COMMIT_PAGES = 10
MAX_PR_PAGES = 5
TOKEN = os.getenv("GITHUB_TOKEN", "")
TABLE_START = "<!-- TRACKER_TABLE_START -->"
TABLE_END = "<!-- TRACKER_TABLE_END -->"


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def utc_iso(value: dt.datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def load_json(path: Path, fallback=None):
    if not path.is_file():
        return fallback
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_projects(projects: list[dict]) -> None:
    seen = set()
    for project in projects:
        repo = project.get("repo", "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise ValueError(f"Invalid repository: {repo!r}")
        if repo.lower() in seen:
            raise ValueError(f"Duplicate repository: {repo}")
        seen.add(repo.lower())
        if project.get("scope", "").find("Xbox Series") == -1:
            raise ValueError(f"Not explicitly Xbox Series scoped: {repo}")


def api_get(path: str, params: dict | None = None, missing_ok: bool = False):
    url = API + path + ("?" + urlencode(params) if params else "")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "scarlett-progress-tracker/1.0"
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers=headers), timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data, resp.headers.get("Link", "")
        except HTTPError as exc:
            if missing_ok and exc.code == 404:
                return None, ""
            if exc.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(attempt + 1)
                continue
            raise RuntimeError(f"GitHub API HTTP {exc.code} for {path}") from exc
        except (URLError, TimeoutError) as exc:
            if attempt < 2:
                time.sleep(attempt + 1)
                continue
            raise RuntimeError(f"GitHub API unavailable for {path}: {exc}") from exc
    raise RuntimeError("Unreachable")


def fetch_pages(path: str, params: dict, max_pages: int) -> tuple[list, bool]:
    """Return items and whether pagination was truncated."""
    all_items = []
    for page in range(1, max_pages + 1):
        items, link = api_get(path, {**params, "per_page": PER_PAGE, "page": page})
        if not isinstance(items, list):
            raise RuntimeError(f"Unexpected paginated API response: {path}")
        all_items.extend(items)
        if 'rel="next"' not in link:
            return all_items, False
    return all_items, True


def delta_since_previous(repo: str, old_sha: str | None, new_sha: str | None):
    if not old_sha or not new_sha:
        return None
    if old_sha == new_sha:
        return 0
    try:
        response, _ = api_get(
            f"/repos/{repo}/compare/{quote(old_sha, safe='')}...{quote(new_sha, safe='')}"
        )
        if response.get("status") == "ahead" and response.get("behind_by") == 0:
            return response.get("ahead_by")
    except RuntimeError:
        pass
    return None  # force-push, divergence or API failure: not interpretable as 0


def snapshot_project(project: dict, previous: dict | None, now: dt.datetime):
    repo = project["repo"]
    path = f"/repos/{repo}"
    info, _ = api_get(path)
    ref = project.get("branch") or info.get("default_branch")
    since = utc_iso(now - dt.timedelta(days=30))
    commits, commits_capped = fetch_pages(
        path + "/commits", {"sha": ref, "since": since}, MAX_COMMIT_PAGES
    )
    last = commits[0] if commits else None
    if last is None:
        earlier, _ = api_get(path + "/commits", {"sha": ref, "per_page": 1})
        last = earlier[0] if earlier else None
    prs, prs_capped = fetch_pages(path + "/pulls", {"state": "open"}, MAX_PR_PAGES)
    releases, _ = api_get(path + "/releases/latest", missing_ok=True)
    new_sha = last.get("sha") if last else None
    last_commit_at = None
    if last:
        commit = last.get("commit") or {}
        last_commit_at = (commit.get("committer") or {}).get("date") or (commit.get("author") or {}).get("date")
    pr_count = len(prs) if not prs_capped else None
    issue_count = max(info.get("open_issues_count", 0) - pr_count, 0) if pr_count is not None else None
    old_sha = previous.get("last_commit_sha") if previous else None
    return {
        **project,
        "url": info.get("html_url", f"https://github.com/{repo}"),
        "branch_scanned": ref,
        "description_upstream": info.get("description"),
        "archived": info.get("archived", False),
        "stars": info.get("stargazers_count"),
        "forks": info.get("forks_count"),
        "open_prs": pr_count,
        "open_issues_estimate": issue_count,
        "issues_note": "Repository open_issues_count minus open PRs; approximate",
        "commits_30d": len(commits),
        "commits_30d_capped": commits_capped,
        "last_commit_at": last_commit_at,
        "last_commit_sha": new_sha,
        "last_push_at": info.get("pushed_at"),
        "new_commits_since_scan": delta_since_previous(repo, old_sha, new_sha),
        "latest_release": {"tag": releases.get("tag_name"), "url": releases.get("html_url")} if releases else None,
        "recent_commits": [
            {
                "sha": c.get("sha"),
                "message": (c.get("commit", {}).get("message") or "").splitlines()[0][:170],
                "url": c.get("html_url"),
                "date": (c.get("commit", {}).get("committer") or {}).get("date")
            }
            for c in commits[:4]
        ],
        "last_successful_scan": utc_iso(now),
        "scan_error": None
    }


def render_readme_table(projects: list, scanned: str) -> str:
    if not scanned:
        return "Activity is pending the first GitHub Actions sync. See [`projects.json`](projects.json)."
    lines = [f"Latest snapshot: **{scanned}**. Every count is upstream activity, **not** game compatibility.\n",
             "| Project | Commits (30d) | Last code commit | Open PRs | Stars | Published metrics |",
             "|---|---:|---|---:|---:|---:|"]
    for p in projects:
        repo = p["repo"]
        def fmt(x):
            return "?" if x is None else str(x)
        cm = fmt(p.get("commits_30d")) + ("+" if p.get("commits_30d_capped") else "")
        commit_date = (p.get("last_commit_at") or "")[:10] or "?"
        if p.get("scan_error"):
            commit_date += " ⚠ stale"
        cov = p.get("coverage") or {}
        published = len(cov.get("reported_metrics") or []) + bool(cov.get("checklist"))
        summary = f"{published} tracked" if cov else "Pending"
        branch = f" (`{p['branch']}` branch)" if p.get("branch") else ""
        lines.append(f"| [{p['name']}](https://github.com/{repo}){branch} | {cm} | {commit_date} | {fmt(p.get('open_prs'))} | {fmt(p.get('stars'))} | {summary} |")
    return "\n".join(lines)


def update_readme(data: dict) -> None:
    path = ROOT / "README.md"
    readme = path.read_text(encoding="utf-8")
    if readme.count(TABLE_START) != 1 or readme.count(TABLE_END) != 1:
        raise ValueError("README markers are missing/duplicated")
    table = render_readme_table(data["projects"], data["generated_at"])
    pre, rest = readme.split(TABLE_START, 1)
    _, post = rest.split(TABLE_END, 1)
    path.write_text(pre + TABLE_START + "\n" + table + "\n" + TABLE_END + post, encoding="utf-8")


def compact_api_scans(rows: list[dict]) -> None:
    """Leave collection diagnostics in the main feed, not duplicated symbol maps."""
    for project in rows:
        scan = project.get("api_scan")
        if scan:
            symbols = scan.pop("symbols", {})
            scan["symbols_found"] = len(symbols)


def run() -> None:
    projects = load_json(ROOT / "projects.json")
    valid_projects(projects)
    catalog = load_json(ROOT / "data/capabilities.json")
    capability_scan.validate_catalog(catalog)
    metrics_rules = load_json(ROOT / "data/declared_metrics.json", {"rules": {}})
    previous = load_json(ROOT / "data/latest.json", {})
    previous_by_repo = {p["repo"]: p for p in previous.get("projects", [])}
    now = utcnow()
    updated = []
    for project in projects:
        repo = project["repo"]
        print("Fetching", repo, flush=True)
        try:
            fresh = snapshot_project(project, previous_by_repo.get(repo), now)
            fresh["coverage"] = capability_scan.enrich_project(
                repo, fresh["branch_scanned"], catalog, api_get, metrics_rules
            )
            try:
                fresh["api_scan"] = api_matrix.scan_repository(
                    repo, fresh["branch_scanned"], api_get
                )
            except Exception as scan_exc:
                print(f"WARNING {repo} API symbol scan: {scan_exc}", flush=True)
                fresh["api_scan"] = {
                    "status": "error", "error": str(scan_exc), "symbols": {},
                    "files_scanned": 0,
                }
            updated.append(fresh)
        except (RuntimeError, KeyError, ValueError) as exc:
            print(f"WARNING {repo}: {exc}", flush=True)
            # Preserve last known metrics, but never pretend an outage is 0 commits.
            old = previous_by_repo.get(repo)
            preserved = old.copy() if old else {**project}
            preserved.update(project)
            preserved.pop("milestones", None)
            if "coverage" in preserved:
                preserved["coverage"].pop("reviewed", None)
                preserved["coverage"].pop("verified_implemented", None)
                preserved["coverage"].pop("claimed_implemented", None)
                preserved["coverage"].pop("forecast", None)
            preserved["scan_error"] = str(exc)
            preserved["api_scan"] = {
                "status": "stale", "symbols": {},
                "files_scanned": 0, "error": "Upstream metadata scan failed",
            }
            updated.append(preserved)
    # Daily snapshots support automatic forecasts for stable upstream-reported denominators.
    history_paths = sorted((ROOT / "data/history").glob("????-??-??.json"))[-180:]
    histories = [load_json(p, {}) for p in history_paths]
    for row in updated:
        cov = row.get("coverage")
        if cov:
            metrics = list(cov.get("reported_metrics") or [])
            if cov.get("checklist"):
                metrics.append({"id": "readme_tasks", **cov["checklist"]})
            cov["metric_forecasts"] = {
                metric["id"]: capability_scan.estimate_reported_metric_eta(
                    row["repo"], metric["id"], metric["implemented"], metric["total"], histories, now
                )
                for metric in metrics
            }
    detailed_matrix = api_matrix.build_matrix(updated)
    detailed_matrix["generated_at"] = utc_iso(now)
    # A dedicated file avoids shipping the same source evidence twice. Both
    # dashboard JSON feeds are written in the same sync commit.
    compact_api_scans(updated)
    payload = {
        "api_matrix_feed": "api_matrix.json",
        "catalog": {"version": catalog["version"], "scope_note": catalog["scope_note"], "features": [
            {k: v for k, v in feature.items() if k != "patterns"} for feature in catalog["features"]
        ]},
        "overlap": capability_scan.build_overlap(updated, catalog),
        "generated_at": utc_iso(now),
        "collection": "Xbox Series X|S / Scarlett",
        "methodology": "Fully automated GitHub activity, source-code candidate symbol matrix, source-path categories, and upstream README metrics; no manual compatibility certification",
        "projects": updated
    }
    write_json(ROOT / "data/latest.json", payload)
    write_json(ROOT / "docs/data.json", payload)
    write_json(ROOT / "docs/api_matrix.json", detailed_matrix)
    write_json(ROOT / "data/history" / f"{now.date().isoformat()}.json", payload)
    update_readme(payload)
    print(f"Done: {len(updated)} projects; {sum(bool(p.get('scan_error')) for p in updated)} errors")


if __name__ == "__main__":
    run()
