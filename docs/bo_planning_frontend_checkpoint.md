# Planning Frontend Checkpoint

Windows / PowerShell, 2026-11-10 local clock. This is a synthetic development
checkout checkpoint, not a release/archive result or a clean full-suite claim.
The command transcript is retained in the agent tool sessions below; this file
records their results, not a recreated complete console log.

## Commands And Results

All commands ran from `frontend`, sequentially with no concurrent model fits.

| Command | Result | Tool session |
| --- | --- | --- |
| `vitest run --maxWorkers=1 src/api/boPlanning.test.ts src/features/bayesian/boPlanningDraft.test.ts src/features/bayesian/BayesianPlanningPanel.test.tsx src/features/bayesian/BayesianPlanningSavedBatch.test.tsx src/features/bayesian/BayesianPlanningDeletion.test.tsx` | 5 files, 40 tests passed; 6.20 seconds | 56174 |
| `vitest run --maxWorkers=1` | 142 files passed, 2 failed; 1,288 tests passed, 2 failed; 157.80 seconds | 30595 |
| `vitest run --maxWorkers=1 src/lazyAnalysisPanels.test.tsx --reporter=verbose` | 3 tests passed; import test 4,305 ms; 5.74 seconds total; no timeout change | 64810 |
| `vitest run --maxWorkers=1 src/asyncHookState.test.ts -t "blocks an old runtime" --reporter=verbose` | 1 passed, 219 skipped, after runtime fixture correction | terminal chunk 36e552 |
| Targeted ESLint on planning API/types, panel/hooks/draft/fixtures/tests, workspace and deletion panel | Passed | 54918 |
| `npm run typecheck` | Passed after the runtime fixture update | 40161 |
| `npm run build` | Passed; 2,245 modules; Vite 4.27 seconds | 49049 |

Production build retained plugin-timing and large-chunk warnings. No thresholds
or test timeouts were increased to obtain these results.

## First Full-Run Failures

1. `src/asyncHookState.test.ts`: `blocks an old runtime and retries into the
   compatible contract` expected `compatible`, received `blocked`. The fixture
   advertised API 37 while the application requires API 38. The parent updated
   the fixture to the current compatibility constants and planning capability.
   The focused retry test then passed.
2. `src/lazyAnalysisPanels.test.tsx`: `keeps regression, quality, and DOE exports
   behind three module loaders` exceeded its existing 10,000 ms timeout
   (10,012 ms observed). The unchanged test passed alone at 4,305 ms. This is
   evidence of a non-reproducing narrow timeout, not proof that the full-suite
   resource/timing risk has been removed. A final integrated full run is pending.

## Implemented Boundaries

- Exact saved schema-8 batches use `planning_batch_id`, reload through exact GET,
  and reject mismatched study/model/candidate/selection hashes. Historical
  batches do not silently resolve to latest history.
- Confirmation locks sensitive controls. A separate study-owner commit fence
  preserves a committed outcome across computational draft changes while
  rejecting different-study and A-to-B-to-A outcomes.
- Managed reports obtain the existing server-generated source descriptor, verify
  its exact hashes and capability, then use the managed-report API and verified
  download helper. The frontend does not invent artifact-file hashes.
- Profiler response mean, latent SD and predictive SD curves reuse the same
  evaluated rows, with units. Display changes do not fit or POST again.
- Planning deletion dependencies are visible. Missing legacy counts are not
  fabricated as zero.
- Decimal lattice regression covers anchor 1000.1 with step 0.1.

Pure/SSR/transport checks are distinct from actual browser behavior. The parent's
built-app `bo_persistent_planning.py` journey and final product/archive checks
were not executed by this child checkpoint.
