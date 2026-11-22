"""Automatic, bounded source-code symbol index for Xbox Series research.

Heuristic code evidence, not functional verification. No binaries or SDKs.
"""
from __future__ import annotations

import base64
import concurrent.futures
import re
from collections import defaultdict
from urllib.parse import quote

MAX_FILES = 48
MAX_BYTES_PER_FILE = 180_000
MAX_SYMBOLS_PER_REPO = 400
MAX_ROWS = 700
EXTENSIONS = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".rs", ".cs", ".zig", ".py")
EXCLUDE_SEGMENTS = frozenset({
    ".git", "docs", "documentation", "tests", "test", "fixtures", "samples",
    "examples", "third_party", "third-party", "vendor", "external", "deps",
    "node_modules", "dist", "build", "target", "generated", "obj", "bin",
})
API_NAME = re.compile(
    r"\b(?:"
    r"X(?:User|GameSave|GameRuntime|Game|TaskQueue|Task|Async|Mem|System|Package|Store|Audio|Input|Thread|Networking|Net|GameUi|App|Display|Curl|Http|Title|Storage)[A-Z][A-Za-z0-9_]{2,}"
    r"|Xbl[A-Z][A-Za-z0-9_]{2,}"
    r"|XG[A-Z][A-Za-z0-9_]{2,}"
    r"|D3D12(?:Xbox|XS)[A-Z][A-Za-z0-9_]{2,}"
    r"|GameInput[A-Z][A-Za-z0-9_]{2,}"
    r"|XboxBvh[A-Z][A-Za-z0-9_]{2,}"
    r"|AcpHal[A-Z][A-Za-z0-9_]{2,}"
    r"|XCurl[A-Z][A-Za-z0-9_]{2,}"
    r")\b"
)
COMMENT = re.compile(r"/\*[\s\S]*?\*/|^[ \t]*//[^\n]*", re.MULTILINE)
STUB = re.compile(
    r"\b(?:E_NOTIMPL|STATUS_NOT_IMPLEMENTED|ERROR_CALL_NOT_IMPLEMENTED|"
    r"ERROR_NOT_SUPPORTED|ENOSYS|todo!|unimplemented!|NotImplementedException)\b",
    re.IGNORECASE,
)
PRIORITY = {"reference": 1, "stub_candidate": 2, "definition_candidate": 3}

GROUPS = (
    ("XGameSave", "Saved data"),
    ("XUser", "Users & identity"),
    ("Xbl", "Xbox services"),
    ("XStore", "Store & licensing"),
    ("XTask", "Tasking & async"),
    ("XAsync", "Tasking & async"),
    ("XThread", "Threading"),
    ("XMem", "Memory"),
    ("XAudio", "Audio"),
    ("AcpHal", "Audio"),
    ("XInput", "Input"),
    ("GameInput", "Input"),
    ("XPackage", "Packages"),
    ("XStorage", "Storage"),
    ("XNetworking", "Network"),
    ("XNet", "Network"),
    ("XCurl", "Network"),
    ("XHttp", "Network"),
    ("D3D12", "Graphics"),
    ("XG", "Graphics"),
    ("XboxBvh", "Graphics"),
    ("XSystem", "System"),
    ("XGame", "Game Runtime"),
)


def group_name(symbol):
    return next((group for prefix, group in GROUPS if symbol.startswith(prefix)), "Other Xbox API")


def is_source(row):
    path = row.get("path", "")
    return (
        row.get("type") == "blob"
        and path.lower().endswith(EXTENSIONS)
        and not EXCLUDE_SEGMENTS.intersection(part.lower() for part in path.split("/"))
        and 0 < (row.get("size") or 0) <= MAX_BYTES_PER_FILE
    )


def candidate_key(row):
    path = row["path"].lower()
    base = path.rsplit("/", 1)[-1]
    emphasis = ("xgameruntime", "gdk", "xuser", "xmem", "xgame", "xasync", "xthread",
                "xstore", "gameinput", "d3d12", "xaudio", "xcurl", "kernel",
                "shim", "hle", "exports", "api", "runtime", "storage", "proxy")
    score = sum(6 for term in emphasis if term in base)
    score += sum(2 for term in emphasis if term in path)
    score += 5 if "/shims/" in path or "/hle/" in path else 0
    score += 3 if "/src/" in path or path.startswith("src/") else 0
    score += 2 if path.endswith((".cpp", ".rs", ".c")) else 0
    return (-score, row.get("size", 0), path)


def definition_match(name, text):
    """Find probable bodies, not bare declarations, calls or string table entries."""
    escaped = re.escape(name)
    patterns = (
        r"(?m)^[ \t]*(?:(?:pub(?:\([^)]*\))?|unsafe|extern\s+\"[^\"]+\"|async)\s+)*fn\s+"
        + escaped + r"\s*\([^;{}]{0,420}\)\s*(?:->\s*[^;{}]{1,90})?\s*\{",
        r"(?m)^[ \t]*(?:async\s+)?def\s+" + escaped + r"\s*\(",
        r"(?m)^[ \t]*(?:(?:[A-Za-z_][\w:<>,\[\]*&]*|\*|&|::|__declspec\([^)]*\))\s+){1,10}"
        + escaped + r"\s*\([^;{}]{0,420}\)\s*(?:const\s*|noexcept\s*)?\{",
    )
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            body = text[match.end():match.end()+360]
            return ("stub_candidate" if STUB.search(body) else "definition_candidate", match.start())
    return None


def source_symbols(content, path, repo, ref):
    """Separate syntactically apparent definition bodies from mentions/import maps."""
    cleaned = COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), content)
    names = set(API_NAME.findall(cleaned))
    found = {}
    urlroot = f"https://github.com/{repo}/blob/{quote(ref, safe='')}/{quote(path, safe='/')}"
    for name in names:
        definition = definition_match(name, cleaned)
        if definition:
            state, index = definition
        else:
            hit = re.search(r"\b" + re.escape(name) + r"\b", cleaned)
            if not hit:
                continue
            state, index = "reference", hit.start()
        line = cleaned.count("\n", 0, index) + 1
        found[name] = {
            "status": state, "source": f"{urlroot}#L{line}",
            "file": path, "line": line,
        }
    return found


def fetch_source(row, repo, ref, api_get):
    path = row["path"]
    data, _ = api_get(
        f"/repos/{repo}/contents/{quote(path, safe='/')}",
        {"ref": ref}, missing_ok=True
    )
    if not data or data.get("encoding") != "base64" or not data.get("content"):
        return {}
    encoded = data["content"]
    decoded = base64.b64decode(encoded)
    if len(decoded) > MAX_BYTES_PER_FILE:
        return {}
    return source_symbols(decoded.decode("utf-8", errors="replace"), path, repo, ref)


def scan_repository(repo, ref, api_get, tree=None):
    if tree is None:
        tree, _ = api_get(f"/repos/{repo}/git/trees/{quote(ref, safe='')}", {"recursive": "1"}, missing_ok=True)
    if not tree or not isinstance(tree.get("tree"), list):
        return {"status": "unavailable", "files_scanned": 0, "candidate_files": 0, "symbols": {}}
    candidates = sorted((row for row in tree["tree"] if is_source(row)), key=candidate_key)
    selected = candidates[:MAX_FILES]
    results, failures = [], 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(fetch_source, row, repo, ref, api_get) for row in selected]
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception:
                failures += 1

    combined = {}
    for result in results:
        for symbol, evidence in result.items():
            old = combined.get(symbol)
            if old is None or PRIORITY[evidence["status"]] > PRIORITY[old["status"]]:
                combined[symbol] = evidence

    # Prioritize candidates for bodies and cross-project references over unbounded token lists.
    ranked = sorted(combined.items(), key=lambda x: (-PRIORITY[x[1]["status"]], x[0]))
    combined = dict(ranked[:MAX_SYMBOLS_PER_REPO])
    return {
        "status": "partial" if failures or len(candidates) > len(selected) or tree.get("truncated") else "ok",
        "files_scanned": len(selected)-failures, "candidate_files": len(candidates),
        "files_failed": failures, "truncated_tree": bool(tree.get("truncated")),
        "limited": len(combined) < len(ranked) or len(candidates) > len(selected),
        "symbols": combined,
        "note": "Bounded static scan. Definitions are syntactic candidates, not proven implementations. Unseen means not detected in sampled files.",
    }


def build_matrix(projects):
    rows = defaultdict(dict)
    active = 0
    for project in projects:
        scan = project.get("api_scan") or {}
        if scan.get("status") not in ("ok", "partial"):
            continue
        active += 1
        repo = project["repo"]
        for name, finding in (scan.get("symbols") or {}).items():
            rows[name][repo] = finding
    expanded = []
    for symbol, by_repo in rows.items():
        count_def = sum(v["status"] == "definition_candidate" for v in by_repo.values())
        count_stub = sum(v["status"] == "stub_candidate" for v in by_repo.values())
        expanded.append({
            "symbol": symbol, "group": group_name(symbol),
            "project_count": len(by_repo), "candidate_count": count_def,
            "stub_count": count_stub, "sources": by_repo,
        })
    expanded.sort(key=lambda v: (-(v["project_count"] * 10 + v["candidate_count"] * 6 + v["stub_count"] * 2), v["group"], v["symbol"]))
    return {
        "method": "Automatic regex-based source-body/mention scan; not actual runtime compatibility",
        "files_per_repo_limit": MAX_FILES, "total_symbols": len(expanded),
        "display_limit": MAX_ROWS, "truncated": len(expanded) > MAX_ROWS,
        "repositories_scanned": active, "rows": expanded[:MAX_ROWS],
    }
