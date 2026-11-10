# BO Multiresponse UI: Stage 3d

Historical Stage3d evidence. The later [Stage3e q1 gate](bo_desirability_review.md)
connects the recommendation workflow that remained unimplemented at this stage;
its API33/metadata27 and new verification supersede capability status below.

Local worktree `feat/bo-desirability`, base/HEAD
`1db522a12a4023995d52bdcdcf750f9500c47381`. No commit, push or Linux
publication is authorized in this stage. Earlier uncommitted stages are retained.

## Scope And Acceptance

This is an additive UI gate on Stage3c API32/metadata26. No statistical method,
schema, database, report renderer or GP calculation changes are made here.

- Keep single-response creation/entry/recommendation as the default path.
- Explicitly select multiresponse mode; define 1..4 response goals and units.
- Preserve scalar drafts when switching modes. Stable response IDs survive edits
  and deletion of a different response. Saved goals are immutable.
- Maximize lower < target; minimize target < upper; match target lower < target
  < upper. Unused bounds are null. Importance is finite, positive and numerically
  representable when normalized. This is the approved public linear policy,
  not a claim of identical JMP curves or numerical recommendations.
- Actual measurement drafts remain strings. Strict decimal/scientific parsing
  rejects blank, partial, hex and nonfinite input without converting it to zero.
- Entirely empty pending rows are not selected. A touched incomplete row prevents
  the whole save. Values join by trial ID and response ID, not display position.
- Preview fixes a complete owner/version/history/hash/value/request-ID snapshot.
  Editing invalidates it immediately. Explicit retry after response loss keeps
  the exact request; there is no automatic PUT/POST retry.
- Success/error/finally and captured callbacks are guarded on edits, source
  changes and unmount. A stale server success is never deleted.
- Refresh after a conflict retains drafts for the same owner. If another request
  already completed a trial, a separate comparison shows local inputs and saved
  values until explicit discard. They are not silently resubmitted or erased.
- Built UI: creation, validation, review, lost-response retry, delayed response,
  KO/EN/resize, exact reload and unchanged source values.

Risks: computed desirability must not be treated as a measured response; missing
values must not become zero; transport retries must not duplicate observations;
late results must not change another owner. User names/units remain escaped and
untranslated. New error handling exposes bounded machine codes, not raw messages.
No data is transmitted externally. Resource usage stays within existing
200-trial/4-response bounds; one heavy test process at a time.

## Implementation

| Files | Responsibility |
| --- | --- |
| `bayesianVectorDraft.ts` | strict goals, measured vectors, immutable source key |
| `useBayesianStudyDraftState.ts`, `BayesianStudyBuilder.tsx`, `BayesianResponseGoals.tsx` | explicit mode and response goal editor; existing factor/constraint builder retained |
| `useBayesianVectorEntry.ts` | review snapshot, source/request guards, same-request retry |
| `BayesianVectorObservationEntry.tsx`, `bayesianVectorEntry.css` | pending input grid, complete preview, recoverable error, exact numeric confirmation |
| `useBayesianStudyLifecycleState.ts`, `BayesianOptimizationWorkspace.tsx` | accept a vector response only for the current immutable source |
| `BayesianVectorStudySnapshot.tsx`, `bayesianReviewErrors.ts`, i18n catalog | updated scope notice, explicit KO/EN display boundaries |
| `bayesianVectorDraft.test.ts`, `asyncHookState.test.ts`, `bayesianVectorSnapshot.test.tsx` | parsing, ID preservation, scalar shape, deferred request and restore regressions |
| `tests/e2e/bo_vector_history.py` | existing context-suite stage extended with real built-UI entry, not API-seeding as UI evidence |

ui-ux-pro-max targeted error-recovery/form guidance was applied: retain drafts,
explicit retry, visible labels, alert focus and existing product tokens. No new
design system, chart library or dependency was introduced.

## Verification

Current-turn results are recorded here after execution. Earlier Stage3c logs
are historical evidence, not a new pass for this UI change.

- Red: new draft test failed to import the not-yet-created implementation.
- First narrow run: 12 passed, 2 failed because the old snapshot test asserted
  the superseded read-only notice. Updated only that scope assertion.
- Expanded parsing/context/snapshot tests: 215 passed before final guard polish.
- First lint: 3 errors in new test harness (hook naming, promise callbacks) and
  12 existing Fast Refresh warnings. Test errors corrected, not suppressed.
- Independent source review identified inherited-property lookup for API-created
  response IDs `constructor`/`toString`, and loss of a conflicting closed-trial
  draft on refresh. Both were fixed with explicit regressions; the latter also
  passed a real browser two-client conflict/compare/discard workflow. These were
  source-confirmed findings, not claims about user-data incidents.
- Full frontend rerun after both fixes: 131 files/1,145 tests passed in137.94s.
  After adding the captured-cancel callback guard, the final full frontend rerun
  again passed131 files/1,145 tests in134.93s. Final lint: zero errors and the
  same12 pre-existing Fast Refresh warnings.
- Native backend regression: 350 passed in128.02s across multiresponse lifecycle,
  vector storage, OpenAPI/frontend contract and E2E-suite partition tests. Existing
  12 Starlette deprecation warnings remain. No statistical tolerance changed.
- Production build passed including TypeScript. Existing large-chunk and
  localization-plugin timing warnings remain.
- Built Chromium149.0.7827.55: real UI study/goal creation, strict partial-vector
  rejection without a request, measured entry, actual server commit followed by
  response loss and same-ID replay, delayed old409 after a new success, two-client
  CAS conflict, explicit draft comparison/discard, exact reload all passed.
  KO/EN at1024/1440 retained raw values, source/history and drafts with no writes
  on locale/resize/reload. No pageerrors. Screenshots and DOM bounds were checked;
  1024px English goal/entry screenshots were visually inspected.
- Existing scalar built-UI review and noise workflow passed: q1 target, q2 joint
  batch, four kernel choices, actual input, independent replicate registration,
  exact grouping (raw9/effective7), restore and managed HTML report. This confirms
  the existing flow remains usable; it is not a JMP numerical comparison.
- Localization inventory/display-boundary checker: 3,013 sources/4,687 keys.
  New Python E2E Ruff lint/format and `git diff --check` passed.
- Final sequential run after the last product edit completed with exit0:
  lint, all frontend tests, TypeScript/production build, localization checker,
  E2E Ruff lint/format, then the full vector built-UI fixture again. The final
  browser receipt repeats every vector workflow assertion above with zero
  pageerrors. No product source was edited after that build.
- Full backend suite, combined project-check exit status, remote native CI,
  Windows11-specific run, Linux/Python3.11/3.12 and release-archive installation
  were **not rerun in this UI-only stage**. They are not recorded as passes.

Environment: Windows10 Home19045, CPython3.10.11, Node24.17.0, CPU only, one heavy
test process at a time and one read-only review agent. All data was synthetic in
an external temporary workspace. Browser receipts/screenshots are under
`%TEMP%/bo-vector-ui-stage3d-20261108-r1` and
`%TEMP%/bo-scalar-stage3d-20261108`; final build rerun uses the sibling
`bo-vector-ui-stage3d-20261108-final` directory.

## Limitations And Next Gate

Multiresponse recommendation capability remains false. The internal Stage3b
worker is not yet connected to public source-locked candidate review/confirmation.
The vector UI does not offer replicate/abandon/close/successor controls or bulk
paste in this stage; their existing API contracts are not removed. Completed
closure still requires a saved recommendation, so it is not falsely enabled.
Stored history reports continue through the existing Report Center contract.
Actual JMP same-input output comparison remains unperformed.

Linux/Windows11 archive checks and remote CI are not replaced by local built-UI
tests. Publication remains deferred until the requested integrated BO work is done.

## Reproduction And Rollback

Use the locked local environment and synthetic external workspace:

```powershell
$env:PYTHONPATH = Join-Path $PWD 'backend'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
npm --prefix frontend run test -- --run --maxWorkers=1
npm --prefix frontend run lint
npm --prefix frontend run build
node scripts/check_frontend_localization.mjs
.\.venv\Scripts\python.exe -m pytest `
  backend/tests/unit/test_bayesian_multiresponse_lifecycle.py `
  backend/tests/unit/test_bayesian_vector_storage.py `
  backend/tests/unit/test_openapi_frontend_contract.py `
  backend/tests/unit/test_e2e_suite_partition.py -q
.\.venv\Scripts\python.exe tests/e2e/bo_vector_history.py `
  --base-url http://127.0.0.1:8676 --output "$env:TEMP\bo-vector-ui-evidence"
```

No rollback is executed. After eventual commits, revert only this UI stage's
commit. It adds no migration. Earlier Stage3c metadata26 still requires its
version-compatible backend; reverting this UI does not revert the database or
delete measured histories, models, workspaces or reports.
