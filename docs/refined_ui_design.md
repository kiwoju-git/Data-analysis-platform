# Refined Analysis UI

Baseline: `d6251458e6aa63763d7160028dc582f21d24b46c` (origin/main).
Branch: `feat/refined-analysis-ui`. This is a reversible presentation-only change.

## Acceptance Criteria

- Preserve all eight domains, methods, short guidance tags, warnings, filters,
  editable drafts, results, history, exports and KOR/ENG.
- Use Graph Builder's selected blue consistently for selected controls.
- Reduce navigation and repeated selection chrome, not analytical information.
- Keep controls keyboard accessible, layouts readable at 390/1024/1280/1440 px,
  and tables/plots inside their existing overflow boundaries.
- Do not change statistical code, API 18, metadata 19, routes or stored bytes.

## Design Direction

The frontend-design and ui-ux-pro-max skills were applied. The local style search
matched Data-Dense Dashboard. Its generic enterprise landing-page suggestion and
remote fonts were rejected: this product is an offline analytical workbench.

Core palette: selected `#225AA7`, selected hover `#184A8B`, selection tint
`#EAF2FF`, paper `#FFFFFF`, neutral canvas `#F4F6F9`, ink `#1F2328`.
Existing green/amber/red status and warning semantics remain distinct.
Keep the local Segoe UI / Malgun Gothic stack and supplied brand bitmap.
Use tight, left-aligned headings, tabular numeric summaries and restrained rules.

```text
neutral navigation | compact page title        KOR / ENG  API
brand + product    | current dataset + brief provenance
section            | domain heading / change-analysis disclosure
  domain           | inputs and filters
    active method  | results, charts, history and export
```

The distinctive visual cue is the existing Graph Builder selection blue, not a
new decorative theme. Sidebar groups no longer become large solid-color panels.
Selected methods and controls carry the emphasis. Root/domain cards retain brief
purposes and tags. On an open method, the repeated method catalog moves into a
native, initially closed disclosure; the executable panel stays mounted outside
it. Opening/closing navigation and changing locale must not reset a form.
Inactive sidebar groups start closed; the current group opens automatically.
User-opened groups and explicit collapses remain under user control.

## Risks and Compatibility

Main risks are CSS cascade collisions, hidden keyboard targets, mobile wrapping
and accidentally resetting React panel state. Validate these in Chromium as well
as unit tests. Do not hide warnings or explanatory content with clipping, and do
not truncate user dataset/column names. No new dependency, telemetry, remote font,
migration or statistical change. `data_prd.md` is absent in this checkout; the
existing addendum and current method/UI contracts were used.

## Verification

Before-change Vitest: 40 files, 300 tests passed. Before screenshots are local at
`.tmp/refined-ui/before/`. Screenshots and workspaces are not committed.

Environment: CPython 3.10.11, Node 22.23.2 from the already installed local
toolchain, Windows 10 Home build 19045. Windows 11 compatibility constraints are
retained, but this validation host is Windows 10, not Windows 11. No browser other
than Chromium was exercised. Existing KOR/ENG terminology was not broadly rewritten.

Exact commands (run from repository root, with Node 22 prepended to PATH):

```powershell
$env:PATH=(Resolve-Path .tmp/node22/node-v22.23.2-win-x64).Path+';'+$env:PATH
npm --prefix frontend test -- --run
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend run build
node scripts/check_frontend_localization.mjs
.\.venv\Scripts\python.exe -m ruff check tests/e2e/refined_ui.py
powershell -ExecutionPolicy Bypass -File scripts/check.ps1
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_openapi_frontend_contract.py -q
.\.venv\Scripts\python.exe -m pytest backend/tests --last-failed -q
powershell -ExecutionPolicy Bypass -File scripts/e2e.ps1 -BackendPort 18631 -FrontendPort 18721 -DiagnosticsRoot .tmp/e2e-diagnostics-refined-ui-pass3
.\.venv\Scripts\python.exe tests/e2e/refined_ui.py --diagnostics .tmp/refined-ui/final
git diff --check
```

- Focused Vitest: 41 files / 303 tests passed; strict typecheck passed.
- Lint: passed with the two existing Fast Refresh warnings in
  `RegularizationSettingsPanel.tsx`. No new lint warning.
- Localization: 2,976 source strings / 3,580 keys verified.
- Production build passed; existing large-chunk and localization-plugin timing
  warnings remain. No dependency or lazy-loading boundary was added/removed.
- Full Chromium critical path passed, including OLS/Ridge/Lasso/Elastic Net,
  PLS/GP/PCA, DOE/RSM/LHS/Bayesian, graph interactions, persistence, prediction,
  restore, deletion, HTML export and error recovery. Screenshot diagnostics:
  `.tmp/e2e-diagnostics-refined-ui-pass3/`.
- The read-only layout suite passed in English and Korean at four viewport sizes.
  It additionally verifies native disclosure keyboard operation and preserved
  route/dataset/alpha without a document reload.
- Full `check.ps1`: tutorial sync (18 blocks), Ruff (234 files), mypy (144
  modules), then backend pytest completed with **1,075 passed / 1 failed** in
  1,401.28 seconds. The sole failure was the documentation list of E2E step
  markers, not a statistical or API behavior failure. The missing marker was
  added; the entire related contract file then passed **201/201**, and a final
  `--last-failed` run passed the one previously failing test. All 1,076 cases have
  therefore passed across the full run and targeted correction, not in one
  all-green invocation. The full 23-minute suite was not repeated for this
  documentation-only fix. `check.ps1` stopped at that original failure; its
  frontend gates were run separately and passed, including final Vitest 303/303
  in 23.90 seconds and production build in 4.89 seconds. `test.ps1` was not
  redundantly run. Exact logs are `.tmp/refined-ui-check.log`,
  `.tmp/refined-ui-vitest-final.log`, and `.tmp/refined-ui-build-final.log`.

Earlier attempts are retained, not counted as passes: the initial E2E expected
every sidebar group to be expanded; the second found a real 36 px dataset/content
alignment mismatch after narrowing the sidebar. The final run incorporates the
new disclosure policy and aligned fluid workspace. A standalone mobile check also
caught and fixed the asset page's automatic min-content width escaping its table
scroll wrapper. No failing check was disabled or statistical assertion weakened.

Changed ownership: `App.css` shared surfaces/controls; `AnalysisMethodNavigation`
and `AnalysisWorkbench` selection disclosure; `SidebarNavigation` and
`sidebarExpansion` initial expansion; the typed locale catalog; related Vitest,
Chromium and documentation files. Backend, schemas, manifests, lockfiles and
statistical method definitions are unchanged. The pre-existing untracked
`examples/image2.png` is excluded from this change.

Rollback: revert the final UI commit with `git revert <ui-commit-sha>`, preserving
any subsequent work. Do not reset the repository to the baseline.
