# Implementation intelligence (v2)

This page explains the **implementation and overlap** panel in Scarlett Progress. It is a research index, **not** an emulator or a compatibility score.

## What the counts actually mean

| Metric | Source | Interpretation |
|---|---|---|
| **Upstream reported done / total** | Repository README | A developer's published task/function/shader count for its explicitly named scope. Do not combine different measurements into one completion percentage. Does *not* independently establish correctness or game support. |
| **Source areas / catalog** | GitHub repository file tree | Paths of first-party source files that match a rule in `data/capabilities.json`. Presence implies *investigation*, never implementation. These are 20 cross-ecosystem research topics, not all Xbox APIs. |
| **Independently verified / catalog** | `data/implementations.json` | Count of source-linked human reviews marked `state=implemented` and `evidence=independently_verified`. No entry means *unknown*, not missing or unimplemented. |
| **Overlapping research areas** | Overlap of source-path categories among repositories | Highlights areas being investigated by multiple projects. It does not prove duplicated code, compatible APIs, or shared implementations. |
| **Experimental catalog ETA** | Dated daily snapshots of reviewed items | Only estimates the date all **20 fixed catalog topics** might reach *independently verified* status in a project. It **never** estimates when GTA VI or a full Xbox Series emulator will be playable. |

### Estimation safeguards

The forecast returns **Not estimable** unless there is a relevant baseline of at least 25% independently verified catalog coverage, at least four daily observations over at least 28 days, two distinct increases, no decreases, and a forward projection no longer than three years. This is intentionally conservative. Scope changes or backfills can invalidate the simple rate model; the estimate is experimental even when available. A full compatibility date cannot reliably be projected from source file counts, GitHub stars, PRs or commits.

## Manually record a tested capability

Edit `data/implementations.json` to add a project and its reviewed capability. Use an ID from `data/capabilities.json` and link the **direct evidence**, such as an issue with a reproducible test log, a commit with exact tests, or an independent run:

```json
{
  "entries": {
    "owner/repository": {
      "shaders": {
        "state": "partial",
        "evidence": "claimed",
        "source": "https://github.com/owner/repository/issues/123",
        "reviewed_at": "2026-11-22",
        "note": "Only specific shader stages tested. No evidence of retail title execution."
      }
    }
  }
}
```

The allowed `state` values are `implemented`, `partial`, `stub`, and `not_started`. The evidence values are `claimed` or `independently_verified`. Do not fill in `not_started` merely because no source was detected. An `implemented` claim needs the boundary of what was tested specified in `note`, since a single API stub should not be classified as a fully implemented subsystem.

## How published measurements are found

`data/declared_metrics.json` contains repository-specific, explicitly labelled README patterns. The collector refreshes each matched measurement every six hours alongside ordinary GitHub data. The upstream source URL is retained in the dashboard. A denominator may mean shader *records* in one repository and tracked *functions* in another; those values must never be summed.

To add a new rule, copy an existing one and make sure the expression names a specific unit and scope. Rules should not match generic percentages that lack a denominator or conflate external projects' numbers. Missing metrics are displayed as **Not published**, not zero.

## Scanning and limitations

The collector reads the GitHub recursive tree of the scanned branch and uses path patterns on first-party source files, excluding docs, tests, vendored dependencies, generated builds and examples. GitHub's tree API may return truncated results, in which case the UI marks an asterisk next to the source-area count. Fetch failures preserve the prior ordinary activity snapshot but surface code-scan errors. No code is run or downloaded, and API credentials remain inside GitHub Actions.

For a deeper roadmap, contribute a curated API/function-level inventory with reproducible tests and known total symbols. Without such a denominator, a trustworthy global “implemented / total Xbox Series functionality” percentage simply does not exist.

### Upstream scope forecasts

Separately from the catalog forecast, the tracker may extrapolate one stable upstream **done/total** measure after at least four daily observations spanning 28 days, two increases, no regressions, and at least 10% of the reported denominator reached. If the denominator changes, older measurements are discarded. These estimates describe only that README's narrowly named task, function or shader corpus. A date for 100% shaders translated is **not** a date for full console emulation or GTA VI gameplay.
