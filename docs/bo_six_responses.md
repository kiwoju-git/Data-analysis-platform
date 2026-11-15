# BO Six-Response Capacity

## Contract

API46 widens desirability from 1-4 to 1-6 measured responses. Final metadata39
adds the fitted-model SQL capacity fix identified during final review; the prior
metadata38 checkpoint did not yet include this correction. Numeric, mixed-factor and
mixture builders, existing X/Y import, complete-vector observations, model fitting,
recommendations, saved candidates, Profiler, LOO, Auto and reports share the same
response bound. A seventh response is rejected; it is not silently truncated.

Every response still needs its own Y mapping, valid goal thresholds and positive
importance. Six responses do not mean six experiments: each experiment supplies
one complete six-value observation vector. Incomplete rows retain the explicit
reject/complete-case policy and the existing field-level feedback.

This is a capacity change, not a new statistical algorithm. Desirability curves,
the weighted geometric composite, independent response-model assumption,
latent/predictive distinction and acquisition policies are unchanged. Importance
is normalized over every requested response. A zero component still forces a
zero composite; the sixth response is not omitted or treated as an average.

## Boundaries

- `core/bo_limits.py` and frontend `boLimits.ts`: response maximum 6.
- All response collection schemas and storage/domain guards use the shared cap.
- LOO metric count remains at four: it is not a response-count limit.
- Planning worker transfer and stored fitted-model snapshot limits are 24MiB.
  The previous 16MiB limit rejects the measured six-response/500-row snapshot.
- Non-model documents retain their16MiB limit; owner/workspace quotas are unchanged.
  Migration39 rebuilds only the model table, preserving JSON bytes and references.
- Owner 128MiB/workspace 256MiB planning quotas are unchanged. Many large saved
  revisions can still exhaust these quotas and must fail explicitly.
- Shared fit/evaluation/deadline limits, trial count 500, sample counts, threading,
  row policies and request-size protection are unchanged. Models are not fitted
  in six parallel workers. More responses increase cost and may reach a budget.
- Model/result/config schemas and existing serialization stay unchanged because
  no field or formula changed. API46 requires a matching backend/frontend.

Old one-four-response artifacts are read without rewriting checksums or injecting
defaults. Older four-response software is not promised to read newly created
five/six-response studies or artifacts. Code rollback does not roll back data;
preserve the workspace and use an application version that supports its artifacts.
No raw user dataset, study or model was used for these tests.

## Verification Record (2026-11-15)

Working base: `0a4f6ec5fd94217210a7b4ec11b37e611fe667ae`, isolated
`feat/bo-500-observations` worktree, with previous uncommitted500-row and import
feedback changes preserved. Native environment: Windows10 build19045,
CPython3.10.11, CPU-only. This is not evidence of a Windows11/Linux release test.

### Reproduced Before The Change

- Four backend failures: sixth-response composite, five/six-response schemas and
  six-Y import rejected. Three other tests passed.
- Four frontend failures: five/six-response construction and Add response at
  counts four/five. Four other tests passed.
- Two six-response/500-row snapshot cases failed the old16MiB document boundary.

### Verified So Far

- `pytest backend/tests/unit/test_bo_six_responses.py -q`: initial eight tests
  passed, including real HTTP/owned-worker six-model fit, saved candidate scoring,
  profiler, KO/EN stored report rendering, confirmation and restart/read.
- Independent six-term weighted product agrees within relative tolerance2e-14.
  One/four/five/six schema round trips and seventh rejection are tested.
- `pytest backend/tests/unit/test_bo_capacity.py -k snapshot -q -s`: seven passed.
  Four-response/500-row snapshot12,355,197 bytes; six-response18,532,785 bytes.
  Worker de-duplication, hydration and storage document boundaries passed.
  Highest measured process peak400,654,336 bytes in that test process. This fixture
  repeats one fitted500-row state to test transport size; it is not a six-model
  optimizer performance benchmark or an OS-enforced memory guarantee.
- Backend Ruff check/format passed. Localization inventory passed3047 sources /
  4727 keys. Frontend build passed with existing chunk-size warnings. ESLint
  passed with12 existing fast-refresh warnings and zero errors.
- Read-only independent review found no remaining production four-response cap,
  budget increase or new SQL dependency. It identified missing six-response
  mixed/mixture/LOO execution evidence, which is being added.

### Failures And Incomplete Runs

- Concurrent full frontend/backend checking coincided with physical memory pressure
  (about 0.6GB available on an 8GB machine). The full runs were interrupted rather
  than loosening tests. Frontend's lazy module-loader test reached its 10s timeout.
  No full backend pass is claimed for that interrupted run.
- First built-app E2E completed import/recommend/observe/restore assertions but
  its evidence writer incorrectly requested runtime version from `/health`.
  It failed with `KeyError`; the test now uses `/runtime-info` and is rerun.
- Linux, native CI, release archive and broad six-model500-row optimized-fit
  performance remain unverified. No GitHub push or Release is part of this turn.

## Serial Verification Follow-up

- `test_bo_six_responses.py`: expanded to 11 tests, all passed in 75.73s.
  Added actual six-model mixed, numeric-mixture and mixed-mixture fits, prediction
  restoration and mixed LOO/Auto evidence. These are domain tests, not full mixed
  UI journeys. A separate bounded-byte rejection test was subsequently added.
- Built-app `tests/e2e/bo_six_responses.py` rerun: passed. Six Y mappings, all six
  predictions, confirm pending trial, save six actual values, reload and unchanged
  imported rows; KO/EN and 1024/1440 widths, zero pageerrors. Raw source checksum:
  `ecb4a1bba304c1f933bbee93429d3eae38aa7199bdb04f06f0207a481b9c7cb3`.
  The fixture is connected to the existing BO dataset-import E2E entry point.
- `npm --prefix frontend run test -- --run --maxWorkers=1` was attempted twice
  after the first concurrent run. One serial run was interrupted during silent
  collection; another again exceeded the loader test's 10s limit and was interrupted.
  The cause of every delay is not established. No timeout was increased.
- Isolated `src/lazyAnalysisPanels.test.tsx --reporter=verbose --maxWorkers=1`:
  3 passed; the heavy import assertion took 7.205s.
- The full remaining suite (`--exclude src/lazyAnalysisPanels.test.tsx`) completed:
  1609 passed, 1 failed. The failure expected five responses to be invalid, the old
  contract. The boundary was updated to seven; its file rerun passed all 12 tests.
  Thus all 1613 frontend cases have passing execution evidence across partitions,
  not a single green full-suite invocation. Focused BO/import tests separately
  passed 65 cases in seven files.
- `mypy backend/app`: no issues in 358 source files. Final Ruff check/format and
  capability generation check passed. No production changes followed the verified
  frontend build; only tests/documentation were adjusted.

The user approved applying the validated local build and refreshing localhost:8620.
Local deployment and final backend regression results are recorded below.

## Final Local Outcome

- Focused backend regression: **372 passed, 1 skipped**, 302.52s. Included the
  final 12 six-response tests plus desirability curves/core, Auto, augmentation,
  planning worker/storage, LOO, vector storage/lifecycle, health/web, runtime
  entrypoint and E2E partition contracts. The skip is Windows symlink creation
  permission in `test_web_ui.py`; it is not a passing security test.
- All frontend cases have passing evidence across partitions as described above.
  Build, ESLint, localization inventory, Ruff, mypy, capability sync and
  `git diff --check` passed. Existing deprecation/fast-refresh/chunk-size warnings
  were not hidden. The complete backend suite was started but interrupted under
  resource pressure; **no complete backend or CI pass is claimed**.
- Verified frontend entry checksum:
  `8bf6727565f1ea479b532b9cdc5079b690aab2a8a89f3d3ae0faf2e81b81b9bb`.
  Built UI/E2E/trace evidence is in the local temporary directory
  `DataLab-bo-six-20261115`, outside Git, using synthetic data only.
- The approved automatic preview replacement/restart command was rejected by the
  execution tool before it ran. Live localhost:8620 therefore still reports
  **API45/metadata38**, with its prior frontend checksum
  `c88fc3deafab20ad05cd1ebc980206b1e932a22d46a12f54a98e1b6590739b62`.
  No live browser refresh, study write or deployment occurred. Browser connection
  fallback could inspect the existing page but was not used to bypass the command
  restriction.
- A guarded, local-only manual helper was prepared at
  `%TEMP%\DataLab-maintenance\apply-bo-six-response-preview.ps1`. Its PowerShell
  syntax passed; **it has not been executed**. It verifies the existing API and
  exact preview processes, refuses active child calculations, preserves old
  frontend assets/index, uses the same workspace and launches the replacement
  hidden. It does not delete data or old assets. If the preview process identities
  change, it stops for review rather than terminating an unrelated process.
- No commit, push, Linux build or Release publication was performed.

Backend regression command (PowerShell, from the isolated worktree):

```powershell
$cases = @(
  'test_bo_six_responses.py', 'test_bo_desirability.py',
  'test_bo_desirability_core.py', 'test_bo_versioned_curves.py',
  'test_bo_auto_strategy.py', 'test_bo_augmentation.py',
  'test_bo_planning_storage.py', 'test_bo_planning_worker.py', 'test_bo_loo.py',
  'test_bayesian_vector_storage.py', 'test_bayesian_multiresponse_lifecycle.py',
  'test_health.py', 'test_web_ui.py', 'test_runtime_entrypoint_versions.py',
  'test_e2e_suite_partition.py'
) | ForEach-Object { "backend/tests/unit/$_" }
.\.venv\Scripts\python.exe -m pytest @cases -q --durations=10
```

The command was executed with those paths explicitly, not with parallel pytest
workers. Existing one-four-response tests remained in the regression set. Auto's
old five-response rejection fixture was updated to seven, with explicit five/six
last-response influence assertions; the invalid-value/duplicate-ID guards remain.
