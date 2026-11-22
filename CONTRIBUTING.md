# Contributing

## Repository additions

Open a pull request changing `projects.json` with a link to a public upstream GitHub repository and an explanation of its **actual Xbox Series X|S emulation/translation purpose**. Do not add emulators only for the original Xbox or Xbox 360. Do not duplicate forks without independent development.

## Compatibility milestone review

Add claims in `data/milestones.json`, keyed by exact `owner/repo` and selected from the documented values. Every entry needs a direct source URL and a short, neutral summary. Keep `claimed` and `independently_verified` strictly separate. Independent verification means an external reviewer could reproduce the behavior or inspect compelling test evidence. Treat README progress bars and developer assertions as claims, not verified functionality. Include a UTC review date.

Do not conflate a sample or other game's ability to boot with GTA VI compatibility. Keep branches in `projects.json` when work is limited to a non-default branch.

## Security and copyright

Never submit copyright-protected game images, licensed SDKs, proprietary keys, circumvention tooling, account credentials or suspicious executables. The tracker links to public project metadata only. All contributions should describe research accurately and avoid exposing private data.
