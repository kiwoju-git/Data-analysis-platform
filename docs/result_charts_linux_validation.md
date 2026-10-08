# Result Charts, Two Variances and Linux Release Validation

## Source and Scope

- BASE_SHA: `5065ca9609185a8081ebefcf171dd524e3df6356`.
- Branch: `feat/result-charts-two-variances-linux-release`.
- Existing untracked `examples/image2.png` is excluded from this work.
- Statistical fit policies and existing result/model files are not rewritten.
- Installed ui-ux-pro-max guidance was inspected for keyboard navigation,
  visible focus and unobscured details. Existing application density, colors
  and the supplied implementation specification take precedence.
- `data_prd.md` is absent in this checkout; the addendum and implementation
  guide remain the available product sources.

## Baseline

- Fresh Windows frontend baseline: 47 files / 361 tests passed.
- Fresh full Windows backend baseline: 1,225 passed in 1,760.51s, native exit 0.
  No backend edits existed while this baseline ran. Log:
  `.tmp/baseline-backend-desktop-charts-linux.log`.
- Existing WSL Ubuntu 24.04.4 x86_64 / Python 3.12.3 is available; availability
  inspection alone is not a Linux installation or release verification pass.

## Incremental Validation

### Common Interaction

- Pure state/viewport-coordinate and existing async-hook checks: 54 passed.
- TypeScript strict check passed.
- Initial full frontend check: 366 passed, 3 failed because new unique SVG IDs
  interrupted a legacy title-ID prefix. Prefix compatibility was restored.
- Follow-up affected tests: 64 passed, including all three previous failures.
- Production build passed before the final source-context additions; the
  final integrated build remains required.
- Chromium synthetic fixture passed: roving focus, Arrow/Home/End, Enter/Space,
  Escape without focus movement, pin surviving hover, external controlled
  selection after Escape, source/ID invalidation, same-ID coordinate changes,
  viewport tooltip placement at 0.5/1/1.5 SVG scales, scroll and no API calls.
- Diagnostics (ignored, synthetic only):
  `.tmp/e2e-diagnostics-result-charts/interaction/chart-interaction.png`.

This is a running validation record, not a completion claim. Main and Release
publication require all implementation stages and final platform checks.

### Final Local Runs

- Full Windows backend rerun: 1,254 passed, 1 skipped, 0 failed in 1,841.69s,
  native exit 0. Command: `.venv/Scripts/python.exe -m pytest backend/tests
  --basetemp .tmp/pytest-full-chart-audit-20261008-2/cases`. TEMP/TMP use that
  isolated D: directory; numerical CPU thread environment variables are 1.
  The skip is Windows symlink creation privilege; Linux must exercise it.
  Log: `.tmp/pytest-full-chart-audit-20261008-2.log`.
- Full Chromium critical path attempt 8 passed, native exit 0, including common
  chart interaction, desktop resize, all existing analysis workflows,
  KO/EN navigation/draft preservation, Two Variances and offline stored HTML.
  Command: `powershell -ExecutionPolicy Bypass -File scripts/e2e.ps1
  -BackendPort 8135 -FrontendPort 5295 -DiagnosticsRoot .tmp/e2e-full-result-charts`.
  Actual browser zoom was separately verified by the standalone desktop fixture,
  not rerun inside this critical-path command.
  Log: `.tmp/verification-e2e-agent-20261008/critical-path-pass8.log`;
  synthetic diagnostics: `.tmp/e2e-full-result-charts/`.
- CI run37715465878 Python3.11 backend: 1,253 passed, 11 Windows-only skips.
  Its subsequent diagnostic probe failed due to a direct-script import path;
  the overall job is **not** a pass. That import path is corrected separately.
- Optimized GP checks now explicitly support test-only `static` or `independent`
  reference modes. Local Windows retains static historical checks; hosted
  Windows/Linux use independent sklearn refits of identical frozen inputs at
  unchanged tolerances. This is not a claim of cross-CPU static optimizer parity.
  See `linux_numerical_reference_validation.md` for measured differences.
- Linux archive installation/smoke and GitHub publication are still pending;
  no source-only or component-test result substitutes for those checks.

### Ubuntu CI Acceptance Before Archive Build

CI run `37716695085`, source `46d2a19`, completed both Linux jobs successfully:

- Ubuntu24.04 / Python3.12.15: `bash scripts/check.sh` passed Ruff/format
  (273 files), mypy (164 source files), backend (1,265 passed, 11 Windows-only
  skips), localization (2,934 source strings / 3,936 keys), frontend lint,
  strict typecheck, Vitest (55 files / 396 tests) and production build.
- `bash scripts/e2e.sh --diagnostics-root .tmp/linux-e2e` passed the complete
  Chromium critical path on Ubuntu, including stored DOE/BO/PLS/GP/PCA and
  Two Variances workflows. Log: `.tmp/ci-37716695085-linux.log`.
- Ubuntu24.04 / Python3.11.17: locked install/pip check, full backend
  (1,265 passed / 11 Windows-only skips) and independent numerical probe passed.
- Linux `dev.sh` lifecycle now has an additional executable smoke test for
  loopback/LAN bindings, shared source identity, collision refusal and owned
  process cleanup. Its actual run is a separate CI gate, not inferred from the
  browser test which launches its own servers.
- The new horizontal-bar SVG title was corrected to a single escaped text
  node after log review; a regression assertion rejects React title warnings.
  Final archive validation JSON and the release validation summary identify the
  exact published source and final check results, without rewriting this source
  document after an archive is built.

### Integrated Verification Corrections

- First integrated Windows backend run:1,246 passed,6 failed,1 skipped in1,801.92s.
  Four failures were stale catalog/handler expectations, one was nested archive
  Git identity incorrectly inheriting a parent HEAD, and one was the report-test
  dispatch map missing Two Variances. All were corrected; a fresh full run is required.
- First Ubuntu3.11/3.12 CI run37712911669: each1,238 passed,5 failed,11 Windows-only
  skips. Failures included a Python3.10-specific provenance assertion, route-map
  declaration syntax, report-test dispatch, GP smooth-case NLPD platform delta,
  and the21-record Bayesian lifecycle fixture's100-evaluation budget.
- No production GP/BO calculation or Windows numerical fixture is changed to
  suppress those failures. `probe_linux_numerics.py` collects independent sklearn
  references, production comparisons and explicit test-only budget diagnostics.
  Probe success means evidence collected, not an acceptance-test pass.
- E2E assertions were updated for portal tooltip versus explicit pin, shared
  chart frames,1100px drawer, hidden roadmap-only entries and bounded canvases.
  Earlier failing attempts remain in ignored diagnostic logs; tests were not disabled.

### Two Variances and Reports

- Method0.1.0/result1/API22 added; metadata20 unchanged. BF/F independent values,
  canonical group identities, row limits, degeneracies and finite encoding tested.
- Focused statistics/runtime/OpenAPI/web/launch checks:244 passed,1 Windows
  symlink-permission skip. Follow-up isolated web/launch:5 passed,1 skip.
- Two Variances + existing PCA/PLS/GP API/report checks:19 passed.
- Actual Windows application E2E passed CSV paste, preflight race, BF/F/SD and
  one-sided bounds, reload/restore, KO/EN,1440/1024/390, report-center downloads,
  offline HTML and source-checksum preservation. Browser review caught missing
  form classes and categorical report ticks; both fixed and browser-reverified.
- Frontend55 files/396 tests and strict typecheck passed. Initial concurrent run
  had two lazy-import timeouts and one stale35-method assertion;36-method fixture
  updated and full rerun passed without increasing timeouts.
- Diagnostics: `.tmp/verification-frontend-agent-20261008/two-variances/`.

### Linux Locks and Environment

- Actual WSL Ubuntu24.04.4/x86_64 generated Python3.12.3 and isolated3.11.17
  runtime25-wheel/dev42-wheel hash locks. Runtime/dev common versions agree.
- Fresh offline wheel-only hash-locked installations and pip check passed for
  3.12 runtime/dev and3.11 runtime. NumPy2.2.6/SciPy1.15.3/sklearn1.7.2 preserved.
- 3.11 dev installation was interrupted by filesystem I/O failure. C: then had
  zero free bytes and WSL could no longer execute bash. This is **not** a pass.
  User files/processes were not deleted/restarted. Further Linux validation is
  assigned to Ubuntu24.04 CI; final archive smoke remains required.
- Windows tests use isolated D: TEMP/TMP after the disk incident. An initial
  web/launch check had4 disk-full failures on C:, then passed on D: as above.
- Local Windows is Windows10 Home19045; this is not a claim of physical Win11
  testing. Hosted Windows/Ubuntu runner results will be separately identified.

### Common Frame and PCA/PLS/GP Adapters

- Frame/coordinate/state and affected regularized-result tests: 26 passed.
- PCA/PLS/GP adapters and panel tests: 19 passed.
- Strict TypeScript passed after correcting typed synthetic-fixture columns.
- Source review found and corrected marker-state CSS specificity, legend
  marker/line mismatch, and missing invalid-grid explanations.
- Existing numerical backend functions and stored schemas are unchanged.
- Full frontend check: 53 files / 386 tests passed; lint: zero errors and nine
  existing fast-refresh warnings. Production build passed (large-chunk warning).
- Chromium common + result-model fixtures passed (`--suite all`): PCA raw values
  and square axes; PLS negative predicted R-squared, separate series, twelve-item
  pagination and page preservation; GP all 25 profile points, unique SVG IDs,
  shuffled surface responses, superseded/source-stale responses, and invalid ID
  sets. 1440/1024/390 viewport overflow checks passed. Synthetic diagnostics:
  `.tmp/e2e-result-charts-verified/`. This does not yet cover the full application
  resize sequence, browser zoom, all remaining plots or Linux release smoke.

### Remaining Result Plots

- I/MR, subgroup and attribute control charts preserve stored limits, signal
  shapes and run identities. Run Chart retains only its stored median reference.
- Capability uses saved histogram bins/density and normal-fit points. Zero
  specification limits remain visible; constant count bins remain supported.
- Prediction charts show stored means and independently available CI/PI values;
  point-only predictions do not gain fabricated intervals.
- Pearson, Gage, factorial main/interactions/cube and RSM grid now use shared
  interaction/frame rules. Gage operator series remain separate. RSM's prior
  renderer was a grid, not a contour-line renderer; saved grid values are retained.
- Initial full frontend check found five legacy markup assertions; these were
  updated to verify visible axes/frames and hit targets. Follow-up: 54 files /
  392 tests passed. These are display tests, not new statistical reference tests.

### Desktop Responsive Layout

- Actual Chromium same-screen sequence passed: 1920, 1440, 1280, 1024, 900,
  768, 1440 and 390 CSS pixels. Input/dataset/component/pin/loading page and
  mount identity persisted. Charts stayed within frames; table scroll remained
  internal. Container widths below 900 use one column; 900 and above use two.
- Source CSS order initially overrode the narrow shell at 1024px. The scoped
  selector was corrected, then the strict full-width/header assertions passed.
- Drawer Tab trap/Escape/navigation and wide-resize trap cleanup passed.
- Actual browser zoom 100/125/150/100% passed using Chromium tabs.setZoom and
  getZoom in a temporary extension/profile; not deviceScaleFactor or CSS scale.
- Command: `.venv/Scripts/python.exe -X utf8 tests/e2e/desktop_resize.py --url
  http://127.0.0.1:5199 --output .tmp/e2e-desktop-resize-verified` (exit 0).
  Eleven synthetic screenshots and two JSON records are ignored diagnostics.
