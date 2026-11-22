# Contributing

## Add a repository

Open a PR updating `projects.json` with a public project genuinely targeting **Xbox Series X|S**, including work that also supports Xbox One. Original Xbox and Xbox 360-only emulators are out of scope. Avoid redundant forks unless they have independent development.

## Improve automatic progress tracking

All progress is collected by `scripts/update.py` from GitHub API activity, source tree paths, and upstream published README counts. No human verification of capabilities is required to refresh the dashboard.

- Add an explicitly scoped, unambiguous pattern to `data/declared_metrics.json` when a project publishes a meaningful new done/total measure. Document the unit: exported functions, shader records, test cases, and so on.
- Update `data/capabilities.json` when a source-path matcher is misleading; keep documentation, test files, and third-party code excluded.
- Add regression tests for parsing changes. Do not infer feature completeness from a filename or add together unrelated denominators.

The scope forecasts require sufficient historical evidence from unchanged upstream denominators. A source-tree match or a high GitHub commit count is not a compatibility benchmark.

## Legal and security

Never submit game dumps, proprietary SDKs, keys, account credentials, or suspicious executables. All collected data is public GitHub metadata and source-file paths. This is an independent research index, not an emulator.
