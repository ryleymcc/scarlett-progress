# Scarlett Progress · Xbox Series X|S emulator tracker

A **master tracking dashboard** for open-source work targeting **Xbox Series X|S (Scarlett)**, with particular attention to GTA VI PC compatibility. This project **does not emulate Xbox games or merge upstream source code**. It compares upstream repository activity and stores separately sourced, reviewable compatibility milestones.

**[Dashboard source](docs/index.html)** · For a live GitHub Pages site, enable Pages under **Settings → Pages → Deploy from a branch → main /docs**. The URL will then be `https://<username>.github.io/<repo>/`.

## Why this exists

There is no reliable single percentage for “GTA VI emulation progress.” Commit volume, GitHub stars, prototype demos, and developer statements measure different things. This tracker keeps them separate:

- **Measured automatically:** last commit, last upstream push, commits over 30 days (capped at 1,000), open PR count, estimated open issues, stars, forks, releases, and new commits since the previous scan.
- **Recorded manually with direct evidence:** loading an executable, GDK runtime, GPU translation, sample rendering, commercial-title boot, gameplay, GTA VI boot and GTA VI gameplay.
- **Not claimed:** that GTA VI is playable or that one repository has “90% compatibility.” No activity metric is a compatibility score.

## Master status

<!-- TRACKER_TABLE_START -->
Activity is pending the first GitHub Actions sync. See [`projects.json`](projects.json) for all 13 tracked repositories.
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

## Add compatibility evidence

Edit [`data/milestones.json`](data/milestones.json), adding entries inside `milestones` keyed by `owner/repo`:

```json
"owner/repo": [
  {
    "milestone": "sample_rendering",
    "status": "claimed",
    "summary": "Developer reports a rendering demo; independent reproduction pending",
    "source": "https://github.com/owner/repo/issues/123",
    "reviewed_at": "2026-11-22"
  }
]
```

A claim is NOT independently verified simply because it appears in a project's README. Use `claimed` unless there is reproducible evidence, preferably a test build, logs and a demonstration. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Data details

`data/latest.json` is the current machine-readable snapshot; `docs/data.json` is the mirrored static dashboard feed. `data/history/YYYY-MM-DD.json` records one snapshot per UTC day. The dashboard uses plain HTML/CSS/JS and no third-party JavaScript, analytics or external CDNs. All upstream links are to GitHub. An API outage is shown as an error rather than as zero activity.

This is an unofficial research index, unaffiliated with Microsoft, Rockstar, or the upstream developers. Do not submit copyrighted game dumps, decryption keys, or proprietary SDK files.
