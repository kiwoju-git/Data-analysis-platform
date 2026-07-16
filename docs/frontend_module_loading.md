# Frontend Module Loading

Last updated: 2026-07-15

## Current Contract

Regression, Quality, and DOE execution panels load on demand from three module
chunks. Exploration, Hypothesis Tests, and Categorical Methods remain in the
main application chunk. This changes only frontend delivery; method IDs,
statistical calculations, API payloads, stored results, and dataset state are
unchanged.

| Module chunk | Panels |
| --- | --- |
| `RegressionAnalysisPanels` | Pearson, X-Y correlation, Linear Model and its dedicated prediction flow |
| `QualityAnalysisPanels` | Attribute, Individuals, Subgroup, Run, Capability, Gage R&R, Gage Run Chart |
| `DoeAnalysisPanels` | Factorial DOE, RSM, and the nested Response Optimizer |

No dependency was added. `React.lazy`, `Suspense`, and the existing React 18
runtime provide the loading boundary.

## Transition And Failure Policy

- Module and method selection runs in `startTransition`, so a synchronous
  selection does not tear down the current Workbench while a chunk is loading.
- The execution-panel Suspense boundary remains mounted across method changes.
- The loading state is labeled `분석 패널 로딩`, uses `role=status`, and has a
  stable minimum height.
- A rejected module import is caught by a method-resettable error boundary.
- The public error view contains no exception, URL, stack, or internal path. It
  offers only a local page reload command.
- Changing methods resets a prior panel-load error without resetting App-owned
  dataset or analysis state.

## Bundle Measurement

Both measurements used Windows 11, Node 22, Vite 8.0.16, and
`npm --prefix .\frontend run build`.

| Asset | Before | After |
| --- | ---: | ---: |
| main JavaScript | 618.10 kB / 141.49 kB gzip | 463.89 kB / 109.30 kB gzip |
| Regression chunk | included in main | 41.53 kB / 8.37 kB gzip |
| Quality chunk | included in main | 58.83 kB / 10.62 kB gzip |
| DOE chunk | included in main | 57.26 kB / 13.47 kB gzip |
| all JavaScript assets | 618.10 kB | 621.51 kB |

The main asset decreased by 154.21 kB, or 24.95%, and no asset exceeds the
500 kB warning threshold. Total JavaScript increased by 3.41 kB because the
module loader and failure boundary add a small delivery cost. The benefit is a
smaller initial main payload and loading only the selected operational module,
not a claim that total application code decreased.

The subsequent Bayesian study/history foundation added an exported typed API
client but no UI panel. Its current production build is 464.68 kB / 109.49 kB
gzip for main, while the three module chunks remain 41.53/58.83/57.26 kB. The
0.79 kB main increase is recorded separately from the code-splitting before/
after measurement above and remains below the 500 kB warning threshold.

## Validation

- Unit tests verify accessible loading/error output, sanitized error content,
  and the exact three module export groups.
- Existing server-rendered panel tests replace only the lazy loader with the
  real panel exports; they continue to verify each panel's full content.
- Browser E2E observes each module resource request during the existing
  Regression, Quality, and DOE workflows.
- Browser E2E opens all three method routes directly.
- A separate browser page aborts the Regression module request and verifies the
  sanitized error boundary, then switches to DOE to verify reset and recovery
  without changing the primary test page or data.

## Limits

- Exploration, Hypothesis Tests, Categorical Methods, shared Workbench code,
  and shared API types remain in the main chunk.
- Chunk prefetching is not enabled; the first visit to a module may briefly
  show the loading state.
- Browser matrix coverage remains Chromium-only.
