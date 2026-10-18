# Pilot Follow-up After 0849aaa

## Baseline And Boundaries

- BASE_SHA and starting local HEAD/origin/main:
  `0849aaa279e34a612c5c65d350cfccf220fe581e` (fetched before edits).
- Working branch: `fix/pilot-followup-0849aaa`.
- User-owned untracked `examples/image2.png` is preserved and excluded from commits.
- `data_prd.md` is absent. Root AGENTS, the current addendum, implementation
  guide, task list and relevant method/runtime contracts are the requirements.
- Existing A01-A15 implementations, metadata 22, stored artifact bytes,
  managed reports, platform locks and all release gates remain in place.
- Only F01 changes statistical grouping and the three affected method/result
  versions. API advances to 24 as one integrated contract change. No SQL
  migration or unrelated numerical/dependency upgrade is intended.
- Tests use synthetic data and isolated workspaces. Existing user servers,
  workspaces, models and results must not be modified.

## Acceptance And Risks

1. F01: full stripped group identities remain distinct through calculation,
   stored result, restore, charts and reports; legacy readers retain original
   bytes and do not invent unrecorded full names.
2. F02: representable axis coordinates and visible numeric labels remain
   distinct, with explicit offsets where necessary, in UI and offline HTML.
3. F03: finite nonzero predictions/SDs and nonempty stored intervals do not
   disappear through formatting. Calculations and source checksums are unchanged.
4. F04: existing execution/source guards survive deferred-response browser
   regressions without a second controller or automatic POST replay.
5. F05: local-only, explicit-action VOC copy/download uses an automatic
   diagnostic allowlist, no data/state dump, and accessible offline controls.
6. F06: source checks and native Windows/Linux gates pass; the final committed
   archive passes offline installation, built-UI edge journeys and restore.
   Only those identical verified bytes may be published as a new prerelease.

Key risks are group-index joins and contrast direction, floating-point
representability rather than display rounding, legacy schema compatibility,
accidental diagnostic disclosure, stale response ownership, and mixed release
identity. Each has an explicit test boundary rather than an assumed guarantee.

## Evidence Status

`code_confirmed`, `reproduced`, `fixed`, `unit_verified`, `api_verified`,
`browser_verified`, `archive_verified`, and `unverified` are separate claims.
The table records this checkpoint, not a future successful release.

| Item | Change kind | Current evidence |
| --- | --- | --- |
| F01 | Statistical grouping defect | code_confirmed, reproduced (13 red), fixed, unit_verified, api_verified, browser_verified (CSV/paste/filter, three methods, restore/report); archive pending |
| F02 | Axis display/coordinate defect | code_confirmed, reproduced (TS 3 red / Python 2 red), fixed, unit_verified; actual small-GP narrow/large axes and saved HTML browser_verified; archive pending |
| F03 | Numeric presentation defect | code_confirmed, reproduced (GP component 3 red / interval renderer 4 red), fixed, unit_verified, browser_verified with actual small-GP fit/prediction and managed reports; archive pending |
| F04 | Existing guard regression coverage | Existing 170 async-hook and 78 request-context tests pass; nine held-response browser cases in each locale pass (18 total) |
| F05 | New local VOC convenience feature | fixed, unit_verified (17 focused tests), browser_verified (KO/EN loaded/offline startup, copy fallback, downloads, focus, 1440/390px); archive pending |
| F06 | Source and completed-package validation | Suite registration and strict receipt tests verified; native CI and exact archive not yet verified |

### F01 Calculated Evidence

Synthetic groups are `X*121 + '-A'`, `X*121 + '-B'`, `C`, `D`, with
values 1..5, 11..15, 21..25, 31..35. BASE modules were executed independently
of current calculation helpers using NumPy 2.2.6/SciPy 1.15.3. The committed
`backend/tests/reference/fixtures/group_identity_legacy_base.json` records
source/module hashes, inputs and original result hashes.

| Result | BASE | New |
| --- | --- | --- |
| Equal Variances groups/N | 3 / 10,5,5 | 4 / 5,5,5,5 |
| Brown-Forsythe F / p | 23.97265625 / 0.000011276113521619612 | 0 / 1 |
| Brown-Forsythe df (derived k-1,N-k; not saved fields) | 2,17 | 3,16 |
| Kruskal-Wallis H / df / p | 16.07142857142857 / 2 / 0.0003236932384041894 | 17.85714285714286 / 3 / 0.0004707189529993288 |
| t with A/B/C | Wrongly accepts N=10,5 | Rejects exactly-two-groups violation |
| t with A/B | Wrongly rejects a merged single group | N=5,5; difference=-10; t=-10; Welch df=8; p=0.000008488181527628498 |

The new t 95% CI is [-12.306004135204166, -7.693995864795834].
Renaming groups bijectively to short names preserves numerical outputs exactly;
independent references retain their pre-existing absolute 1e-12 tolerances.
Interval and Dunn joins now use validated indexes; saved comparison also prefers
full values. No ANOVA/Mann-Whitney/Two-Proportion grouping rewrite was needed.
Legacy fixtures retain the original faulty collision result as historical data,
not a corrected/recomputed artifact. A verification-only provisioner creates new
synthetic legacy records before the archive server starts; it refuses a populated
workspace and does not alter existing records.

### Checkpoint Commands And Results

All Python commands used `PYTHONPATH=backend` and the existing locked remediation
venv on this Windows host; the root venv is older. Native CI uses the repository
bootstrap/check scripts in clean target environments. Logs/screenshots are
ignored `.tmp` diagnostics, never committed user data.

- F01 baseline: 14 passed; initial collision regression: 13 failed as expected.
  Focused current API/report regression: 133 passed. Final identity/API/legacy
  fixture/seed group: 42 passed, 220 deselected. Legacy CLI seed also completed.
- `npm --prefix frontend test -- --run analysisExecutionContext gpPredictionSnapshot gpPredictionRequestRace managedReportSource sourceContextGuard latestRequest`:
  78 passed; `... --run asyncHookState`: 170 passed.
- F02/F03 focused frontend: 124 passed; numeric/PLS/GP/backend-family group:
  70 passed. Paired prediction-report precision: 29 passed.
  Final numeric backend group after independent review: 92 passed. Added
  nonfinite heatmap-edge rejection and mixed integer/float interval precision
  red/green tests without changing calculations or stored values.
- VOC privacy/transport/dialog/runtime focused tests: 17 passed.
- Runtime health/web/release-readiness subset: 61 passed, 1 platform skip.
- `npm --prefix frontend run typecheck`, `npm --prefix frontend run build`,
  `npm --prefix frontend run lint`: succeeded (lint has nine existing refresh
  warnings). `python -m mypy backend/app`: 202 source files passed.
- `node scripts/check_frontend_localization.mjs`: 2875 source strings and
  4149 translation keys verified at this checkpoint.
- First full Vitest run: 847 passed / 2 lazy-import timeout failures. These are
  not reported as success. Serial run also had 847 passes / 2 timeouts; isolated
  lazy-loader rerun had 5 passes / 1 timeout. No timeout was raised or test removed.
  Clean native CI is a separate required run, not an assumed pass.
  A later unchanged-timeout full local run completed: 96 files / 850 tests passed
  (`.tmp/pilot-frontend-final.log`, 114.75 seconds).
- First full backend run encountered a stale tutorial method-version expectation
  and was stopped after further progress; it is not a completed/full pass.
  Tutorial version metadata was updated, all 18 stored numeric expectations and
  tolerances were verified unchanged, and tutorial/TwoT/group regression passed
  30 tests. The added test compares current short-group calculations to those
  unchanged tutorial values.
- `ruff check backend` and all changed E2E/release scripts pass. An extra sweep
  over every historical script found pre-existing unused `json` in
  `render_stat_dependency_record.py` and E402 in `validate_normality_reference.py`;
  unrelated scripts were not rewritten.
- C: had approximately 5 MB free during the first checks. A focused pytest run
  hit `database or disk is full`; own TEMP/TMP and synthetic workspaces were
  subsequently moved to D:. No user/temp/workspace files were deleted.
- First source browser start timed out before backend readiness. Next runs
  exposed test-selector and test-locale-reset defects; these are distinct from
  product calculation defects. All failed runs retain their diagnostics.
- Local built-UI run `.tmp/e2e-pilot-built-3`: long groups, CSV ingestion, and
  actual Two Variances BF/F forms passed. The small-GP run revealed an 11px page
  overflow at 1024px from a tiny training-error summary in fixed notation.
  GP summary now uses the same semantic measurement formatter, with an SSR
  regression; no GP fit/noise/uncertainty policy changed.
- `.tmp/e2e-pilot-built-6/prediction`: actual 16-row, two-predictor small-response
  fit, saved-model two-row prediction, distinct nonzero means/SD/intervals,
  KO/EN at 1440/1024px, visible unique axes, managed HTML/JSON, and unchanged
  source result passed. This is local Windows built UI, not a Linux archive pass.
- `.tmp/e2e-pilot-completion-2/completion`: nine scenarios in KO/EN passed:
  configuration, configuration A-B-A, filter, disconnected POST, dataset A-B-A,
  cross-tab schema, saved-state verification retry, failed activation and
  locale/resize-only display. Exact saved payloads and one POST were checked.
- `.tmp/e2e-pilot-feedback-final/feedback`: four loaded/startup-offline cases in
  KO/EN passed, with clipboard absence/rejection, JSON/text equality, no HTTP
  requests after opening, keyboard boundaries, Escape focus return and 390px.
  Native dialog alone let Tab enter browser chrome; explicit boundary wrapping
  fixes that reproduced UI defect. Two test fixes distinguished an accessible
  textbox role from a wrapping-label text query, and simulated all API transports
  failing rather than incorrectly treating one failed request as global offline.
- Exact committed checkpoint `ba82dee` built UI repeated the long-group,
  CSV ingestion and BF/F form journeys successfully
  (`.tmp/pilot-ba82dee-groups.log`).
- First native feature CI `39142728713`: Linux backend completed with
  2432 passed / 7 failed / 12 skipped. Six failures were old report assertions
  requiring bare `<td>` or `.10g` strings instead of the new exact-value title
  and adaptive visible precision. One was the canonical ordered E2E marker
  list missing four registered pilot steps. They are corrected without removing
  numeric assertions or weakening the CI gate. The failed run remains evidence,
  not a release-ready result; subsequent source requires a new full run.
  The same seven failures occurred on native Python 3.11. Focused report
  reproduction was 6 failed; after the assertions were corrected the two API
  cases, OLS reports and numeric/prediction reports passed 50 tests. The complete
  OpenAPI/frontend contract file passed 233 tests after the marker correction.
- Native feature CI `39143732852` at `46e4fe6` completed the Linux full checks:
  2439 backend tests passed / 12 skipped, and 96 frontend files / 850 tests
  passed. Its browser job then failed an outdated GPR profile tooltip assertion:
  the stored endpoints were still exactly 10 and 12, while the visible interval
  changed from `10 - 12` to `[10, 12]`. The expectation now checks the exact
  bracketed interval; no computation, timeout or tolerance changed. Artifact
  `12142263718` preserves the actual child failure screenshot. Its downloaded
  ZIP SHA-256 was verified as
  `5919c1922c26811059fb51accafce784291c734ec7a96c07e2f1a52866a4f4e6`.
  The parent's "no browser page" message referred to its uninitialized legacy
  page, not the separate chart-fixture context; it did not discard that child
  screenshot.
- After that correction, current-source production-built synthetic chart
  fixtures passed both `verify_chart_interactions` and
  `verify_result_chart_models` in local Windows Chromium, including exact
  profile values, surface request validation, and 1440/1024/390px checks
  (`.tmp/pilot-chart-built-46e4fe6.log`). A separate fresh-workspace built-UI run
  passed `verify_reporting_summary_variance_and_scatter`, including the new
  equal-variances schema 3/full-group identity assertion, Graph Builder,
  graphical summary/mobile, saved analysis and HTML download/body rendering
  (`.tmp/pilot-report-built-46e4fe6.log`). These are local focused checks, not a
  subsequent native CI or packaged-archive pass.
- Native CI `39145371170` at `122b7ec` reached the feedback browser fixture but
  failed its expected catalog-retry button. The actual child trace, with no
  page errors or failed assets, recorded two initial `limit=20` catalog GETs:
  the one-shot fixture supplied 422 to the first and allowed 200 for the second.
  Dev StrictMode effect replay therefore cleared the expected error. Artifact
  `12143049140` was checked against ZIP SHA-256
  `660cdbd0b7ac4eae2ab8865635239fc99a7a2dd6986603bae4a1f36903f24c6a`;
  its feedback child HTML, screenshot, JSON and trace are preserved.
  Local source Vite reproduced the same 422/200 ordering and failure in
  `.tmp/pilot-feedback-source-red-122b7ec.log`, unlike the prior built-UI pass.
  The fixture now rejects all initial catalog requests until the visible error,
  sets the context offline, removes that injected route, then checks the actual
  user retry's transport failure. The error, privacy, downloads and keyboard
  assertions remain unchanged; no product code, StrictMode, timeout or retry
  policy was changed.
- The corrected source feedback fixture passed four KO/EN loaded/startup cases
  (`.tmp/pilot-feedback-source-green-122b7ec.log`). Its receipt records four
  injected initial catalog errors per locale rather than assuming one request.
  The broader source Vite `context` suite then exited 0, covering analysis
  completion, Report Center context, API translation, chart formatting and
  feedback (`.tmp/pilot-context-source-122b7ec.log`). The exact suite command was
  `.tmp/remediation-a04-source/.venv/Scripts/python.exe tests/e2e/critical_path.py --suite context --backend-port 8051 --frontend-port 5271 --diagnostics-root .tmp/e2e-pilot-context-source-122b7ec --workspace-root .tmp/pilot-temp-agent3`,
  with Node 22 on PATH, root `backend` on PYTHONPATH, TEMP/TMP on D: and numerical
  threads capped at one. Only the harness-owned servers were stopped. This
  source-browser success does not assert a new native CI or archive pass.

The final aggregate CI outcome, exact source SHA, archive bytes and installation
receipt belong to the new Release validation asset. This checkpoint does not
claim a future `release-ready` success or a completed publication.

## UI Guidance

Installed `ui-ux-pro-max/SKILL.md` was read. The targeted
`keyboard focus modal --domain ux` search returned visible focus states and
unobscured focus guidance. Existing desktop analysis density, tokens, Lucide
icons and controls take precedence; no marketing layout or new design system
is introduced. Native/mobile-only skill advice is not a desktop acceptance claim.

## Release And Rollback Policy

The existing `linux-reliability-2026.10.3` release/tag/assets remain untouched.
The next unused numeric release and tag will identify the final tested source.
README installation/run instructions must explain Python/venv prerequisites,
offline wheelhouse installation, trusted-LAN `0.0.0.0:8600`, `--local-only`,
shared workspace permissions and the absence of authentication/TLS.

Rollback will list only this task's actual commits, newest first, using
`git revert`, never a broad range/reset/force push. Code rollback does not
remove or downgrade stored results. New F01 schemas may not be readable by
older code. No actual rollback is performed without a user request.
