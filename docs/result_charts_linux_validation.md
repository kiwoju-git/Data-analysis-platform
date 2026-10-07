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
- Full backend baseline is being collected separately before backend changes.
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
