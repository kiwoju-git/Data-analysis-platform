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
