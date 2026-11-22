# Automated implementation intelligence

Scarlett Progress monitors **Xbox Series X|S** research from GitHub without requiring manual compatibility reviews. The workflow collects upstream activity, scans public source file paths, reads README progress counts, and compares daily snapshots.

## What the dashboard measures

| Measure | Automatically derived from | What it means |
|---|---|---|
| **Upstream reported done / total** | Repository README | A developer-published number for a *specific* set of tasks, functions, shader programs, or APIs. The denominator belongs to that repo and task only. |
| **Source areas / 20-area catalog** | GitHub source-tree file paths | A code-path match suggests a repo works in an area. It **does not** prove the implementation works. |
| **Overlapping research** | Common matched capability areas | Two repositories investigate similar subjects. It does not establish code duplication, interoperability, or equal maturity. |
| **Experimental scope ETA** | Daily history of the same upstream done/total measure | A trend estimate for **that named measurement**, not for a complete emulator or GTA VI gameplay. |

All of these update with the normal scheduled sync. No review spreadsheet, claim approval or manually edited milestone log is needed.

## ETA requirements

An ETA is shown only after at least four comparable daily measurements spanning 28 days, two distinct gains, a stable denominator, no regressions, at least 10% measured, and a projection within the next three years. Otherwise the dashboard displays **Not estimable**. When the upstream counter reaches its total the dashboard reports **Declared scope completed**, not that the emulator can boot GTA VI.

A project may report 100% shader *translation* and still have no functioning game executable, audio, controller support, or graphics output. Progress measures from different repos are never added together into an invented global percentage.

## How progress metrics are extracted

The collector uses repo-specific parsing patterns in `data/declared_metrics.json`. Those rules are tracking configuration, **not** a human verification queue. Every scan independently reads the current upstream README and publishes the source URL. A missing count means **Not published**; it never means 0% implemented.

The `data/capabilities.json` file defines the 20 comparable research topics. The source-tree inventory excludes third-party and generated files, documentation, tests, and examples; truncated tree responses are flagged. The comparison is indicative, not an API-level audit.

## Automatic collection

`scripts/update.py` writes `data/latest.json`, `docs/data.json`, and `data/history/YYYY-MM-DD.json`. The GitHub Actions workflow runs every six hours. The live dashboard reads `docs/data.json`. Existing snapshots are retained across upstream API failures, but marked stale.

You can add or remove upstream repositories in `projects.json` or add a new metric extraction rule without touching program code. The update process itself requires no manual assessment. No copyrighted games, console keys, SDK binaries, or circumvention tooling are included.
