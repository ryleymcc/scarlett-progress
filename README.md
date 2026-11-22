# Scarlett Progress · Xbox Series X|S emulator tracker

A **master tracking dashboard** for open-source work targeting **Xbox Series X|S (Scarlett)**, with particular attention to GTA VI PC compatibility. This project **does not emulate Xbox games or merge upstream source code**. It automatically compares upstream repository activity, code-path research areas, and upstream-published progress metrics.

**[Dashboard source](docs/index.html)** · For a live GitHub Pages site, enable Pages under **Settings → Pages → Deploy from a branch → main /docs**. The URL will then be `https://<username>.github.io/<repo>/`.

## Why this exists

There is no reliable single percentage for “GTA VI emulation progress.” Commit volume, GitHub stars, prototype demos, and developer statements measure different things. This tracker keeps them separate:

- **Measured automatically:** last commit, last upstream push, commits over 30 days (capped at 1,000), open PR count, estimated open issues, stars, forks, releases, and new commits since the previous scan.
- **Measured automatically:** project-published implemented/total ratios (within named scopes), 20 source-tree research areas and cross-project overlaps, plus history-based scope forecasts.
- **Not claimed:** that GTA VI is playable or that one repository has “90% compatibility.” No activity metric is a compatibility score.

## Master status

<!-- TRACKER_TABLE_START -->
Latest snapshot: **2026-11-22T17:41:17Z**. Every count is upstream activity, **not** game compatibility.

| Project | Commits (30d) | Last code commit | Open PRs | Stars | Published metrics |
|---|---:|---|---:|---:|---:|
| [Leonida](https://github.com/ItsNotRexed/Leonida) | 1000+ | 2026-11-22 | ? | 12430 | 1 tracked |
| [Xbox2Windows](https://github.com/R0Y00/Xbox2Windows) | 977 | 2026-11-22 | 69 | 1225 | 2 tracked |
| [XCL](https://github.com/ivall/xcl) | 150 | 2026-11-22 | 2 | 182 | 1 tracked |
| [Xbox Emulator](https://github.com/omonkeyz/xbox-emulator) | 212 | 2026-11-22 | 6 | 1191 | 2 tracked |
| [TomBox](https://github.com/drycheetah84/TomBox) | 136 | 2026-11-22 | 1 | 77 | 0 tracked |
| [ScarlettX](https://github.com/Freminet/ScarlettX) | 57 | 2026-11-22 | 26 | 158 | 2 tracked |
| [xvalkyrie](https://github.com/sammwyy/xvalkyrie) | 186 | 2026-11-22 | 1 | 102 | 2 tracked |
| [AnyXboxX](https://github.com/LooperSalty/AnyXboxX) | 134 | 2026-11-22 | 0 | 25 | 1 tracked |
| [OpenScarlett](https://github.com/californiaAlmonds/OpenScarlett) | 210 | 2026-11-22 | 2 | 19 | 3 tracked |
| [TuxBox](https://github.com/brcly/TuxBox) | 14 | 2026-11-22 | 0 | 11 | 0 tracked |
| [scarlett-layer](https://github.com/jadeowaowa/scarlett-layer) | 147 | 2026-11-22 | 0 | 21 | 0 tracked |
| [GDKScarlett](https://github.com/Ender-0001/GDKScarlett) | 2 | 2026-11-21 | 0 | 12 | 0 tracked |
| [americas-recomp](https://github.com/realdody/americas-recomp) (`xbox-series` branch) | 1000+ | 2026-11-22 | 7 | 455 | 0 tracked |
<!-- TRACKER_TABLE_END -->

## Start a new repository

1. Create a public GitHub repository named `scarlett-progress` (or choose your own name), without auto-generating starter files.
2. Upload/commit **all** the files from this project (including the hidden `.github` folder) to the `main` branch.
3. Open **Actions → Sync Xbox Series projects → Run workflow**. GitHub Actions will generate the first activity snapshot and update this table.
4. Under **Settings → Pages**, select **Deploy from a branch**, choose `main` and `/docs`, then save. The dashboard will become available on GitHub Pages after deployment.
5. For local testing, run `python scripts/update.py` (optional `GITHUB_TOKEN` environment variable for a higher rate limit), then `python -m unittest discover -s tests -v`.

Scheduled scans run every six hours, subject to GitHub Actions scheduling and permissions. Snapshot history is preserved daily in `data/history/`. When upstream data cannot be fetched, the last good snapshot is retained and marked stale instead of declaring the project dead.

## Add or remove a project

Edit [`projects.json`](projects.json) and rerun the sync. Entries must target Xbox Series X|S itself (projects targeting only the original Xbox or Xbox 360 are out of scope). The optional `branch` field tracks a particular research branch rather than unrelated default-branch commits.

## Unified API code matrix

The dashboard's **Code grid** tab combines Xbox Series/GDK-style function names discovered in the source of all 13 tracked repositories. Each row is a symbol and each column is a repo. The grid distinguishes a likely function body, a possible unimplemented stub, a reference/exports-only mention, and no detection in sampled files. Positive cells link straight to their source lines.

The grid loads its detailed data from a separate `docs/api_matrix.json` file while the rest of the dashboard uses the lightweight `docs/data.json` feed. Both files are produced together by the scheduled sync.

It is **fully automated** by the regular GitHub Actions sync. Scans are bounded to 48 likely source files per repo (with file-size and total-row limits), so a blank cell means **not detected in the scanned sample**, never proof that an API is absent. A candidate body is not independently verified functionality. The total rows represent a discovered union, **not** the complete Xbox Series API surface.

## Implementation tracking

Implementation measures and overlaps are **fully automated**. Every sync reads the public source tree and published README counters. For details on what those counters mean and when an experimental ETA appears, see [IMPLEMENTATION.md](IMPLEMENTATION.md).

No manual milestone or verification queue is required. The dashboard does not claim that all tracked tasks imply playable GTA VI.

## Data details

`data/latest.json` is the current machine-readable snapshot; `docs/data.json` is the mirrored static dashboard feed. `data/history/YYYY-MM-DD.json` records one snapshot per UTC day. The dashboard uses plain HTML/CSS/JS and no third-party JavaScript, analytics or external CDNs. All implementation data is collected from GitHub automatically. All upstream links are to GitHub. An API outage is shown as an error rather than as zero activity.

This is an unofficial research index, unaffiliated with Microsoft, Rockstar, or the upstream developers. Do not submit copyrighted game dumps, decryption keys, or proprietary SDK files.
