# Stage 3h: Public Ordered Desirability Batch

Date: 2026-11-09. Local `feat/bo-desirability` worktree. No commit, push or
release publication is authorized in this gate. Earlier uncommitted stages
remain intact.

## Acceptance And Boundaries

This gate connects the existing Stage3g calculation to public review, explicit
whole-batch confirmation, individual measured response vectors, exact source
restoration and reports. The UI and real-browser evidence are recorded by the
parent implementation; backend-only success is not completion of this gate.

The calculation policy remains `conditional_mc_desirability_beta_marginal_v1`.
There is no new fitting algorithm, new desirability curve or JMP equality claim.
Each response GP fits once. Base predictions and unconditional Beta EI remain
separate from conditional planning variance and marginal MC/Beta improvement.
Rank means selection order, not experimental success probability.

Existing public schema4 q1 requests/results retain their original method0.9.0,
model5/item3 and hashes. Scalar BO is unchanged. The new public version5 accepts
q1..8; the UI retains the old q1 path and uses the new version for q2..8.

Risks: partial bundle writes, response loss/concurrent confirmation, source
history unchanged after an abandoned trial, current-state contamination of an
immutable result, stale restore/report dispatch, excessive quadrature budgets,
and conditional Beta precision limits. Tests use synthetic workspaces only.

## Versioned Contract

- API34 / metadata28. Registry method0.10.0 accepts new study creation while
  historical method versions remain readable.
- New request/config/result5, review3, shared model5, item4.
- `batch_size`: strict integer1..8.
- `batch_options`: `sample_count`16..256, `max_moment_evaluations`1..65536,
  `min_batch_distance_normalized` finite nonnegative.
- Existing response-model/noise, observation policy, xi, global search/fit/time
  budgets and total trial limit remain explicit and validated.
- Existing desirability review/confirm/exact/latest paths accept/read both
  generations. Common batch GET/list/latest includes the new result union.
- `bayesian_multiresponse_batch=true` describes this versioned public path;
  it does not claim candidate imports/manual subsets or JMP named augmentation.

Migration28 rebuilds the existing batch/item CHECK constraints with one new
exact method/policy/schema tuple. It copies old values unchanged, preserves
foreign keys/indexes and does not rewrite stored observations or JSON hashes.
No new table or second recommendation architecture is introduced.

## Review And Atomic Confirmation

Review creates no trial. The cached request/result pair retains the source
study/version/definition/history hashes, full settings and `source_trial_count`.
The source is rechecked after the owned worker returns. A changed trial count
invalidates an old review even when the observed history has not changed.

Confirmation never refits or searches. It passes all ordered pending trials,
the immutable batch and all ranked items to the existing single transaction.
Every item satisfies `trial_number - rank == source_trial_count`. History CAS,
active owner, no existing pending trials and the entire remaining budget are
checked within that transaction. A failure on a later item rolls back all items.

Same review ID plus config hash returns the same committed bundle after a lost
response, concurrent request, cache expiry or restart. Different content or
owner is rejected. Client retry is explicit; no automatic POST replay is added.
Actual values are entered individually as complete response vectors. Neither
predictions nor composite desirability are inserted as measured responses.

## Read And Report Integrity

Readers reconstruct the original calculation request from the exact saved
history and the source trial-count cutoff, not from the current observation
head or from earlier candidates in the same batch. They validate all ranks,
item/trial owners, coordinates, hashes and the saved typed calculation.

`current_trial` is a dynamic response overlay. The immutable `trial` stays in
its original pending state and `result_sha256` remains unchanged after actual
measurements or abandonment. Batch states reuse pending, partially_completed,
completed, abandoned and closed_mixed semantics.

Managed report renderer1.6.0 reads the exact source attachment without fitting,
CV or loading the current study as a replacement source. Every candidate is
rendered under `section[data-batch-rank]`, including actual settings, trial ID,
response units, base mean/latent SD/predictive SD, unconditional Beta EI and
separate planning score/MC SE/sample count/seed/conditional variance. Original
source and result hashes remain attached to the report record. Existing exports
are not overwritten. Backup/restore and dependency deletion reuse existing
owner tables and hash checks.

## Resource And Numerical Limitations

The shared one-worker admission, bounded JSON IPC and owned-process cleanup
remain. Budgets cover the whole batch, not a fresh allowance per item. q8 with
64 draws and pool32 exceeds the default8192 moment ceiling; inadmissible options
fail explicitly before fitting and are never silently reduced.

Concentrated Beta approximations above the existing precision boundary still
return `bayesian_desirability_beta_precision_unsupported`. The public lifecycle
does not change that numerical policy. Such failure creates no pending trials
or partial successful batch. Success on one q8 fixture is not a guarantee that
all data/noise/kernel combinations support q8.

## Execution Ledger

- Red: the new q2 real HTTP test returned422 against the old q1 request contract.
- First connected run: q2 review/confirm/partial observation/restart passed;
  q8 on the existing three-point estimate/Matérn lifecycle fixture failed safely
  with `bayesian_desirability_beta_precision_unsupported` (1 passed/1 failed).
  That failure is retained as an explicit no-write regression. A distinct q8
  supported-options fixture uses Exponential kernel and fixed noise SD0.2;
  the complete file then passed: **7 passed in106.10s** on Windows/CPython3.10,
  including actual owned-worker q2/q8, later-item transaction failure,
  concurrent/restart replay, exact saved reports and migration27/28 backup.
- Additional strict public-request cases and explicit new batch-core/worker
  no-refit report guards passed in the final focused run: **315 passed,
  1 skipped in261.62s** across seven files. This includes all19 public batch
  cases, OpenAPI, metadata, Windows launcher/runtime, health and built-UI
  serving contracts. The skipped existing symlink test requires privileges
  unavailable to the current Windows account; it is not recorded as passed.
  The original precision failure is not erased by the successful fixture.
- Parent-run built-UI q2 journey passed on the synthetic local server: KO/EN,
  1024/1440px, visible base prediction parity, stale review rejection, lost
  confirmation response/same-ID retry, rank2-first individual measurements,
  partial-state reload, exact report creation/download/restoration and all
  ranks in offline HTML, with zero page errors. The parent first corrected an
  accessible-label fixture failure; the subsequent default Matérn/estimate
  seed43 attempt hit the explicit precision limit without writes. The passing
  browser fixture explicitly selects Exponential/fixed noise SD0.2 in the UI.
  This is a supported-options journey, not evidence that every q2 option works.
- Full backend mypy: **262 source files passed** after fixing typed union
  iteration and reuse of a decorated validator. Backend Ruff check passed;
  format check passed for495files. The registry-derived capability matrix was
  regenerated for method0.10.0.
- Frontend red tests first exposed the old q1-only request builder (10 failed,
  19 passed). The connected focused set passed274 tests. The first complete
  run passed1216 and failed2 old saved-notice copy assertions; those assertions
  were updated to the whole-batch wording. The final single-worker run passed
  **136 files / 1218 tests in130.81s**. Typecheck passed; lint had zero errors
  and12 existing Fast Refresh warnings.
- The final production build passed after capability regeneration. Existing
  large-chunk and localization-plugin timing warnings remain. The final built
  browser reruns passed both the preserved q1 schema4 journey and q2 schema5
  journey on Windows10 Home19045 / CPython3.10.11 / Chromium149.0.7827.55.
  All candidate ranks and visible prediction values were compared with the
  response, not just screenshot presence. Both locales and1024/1440px were
  checked. The q2 browser fixture explicitly chooses Exponential/fixed SD0.2;
  q8 is API-tested, not claimed as an actual eight-row browser journey.
- The owning test server process was stopped and restarted on the same
  synthetic external workspace. The q2 exact-source browser restore passed
  with no mutation request and the same result SHA-256:
  `59c669e3bf604a84fddd5cc241713add3f77c367720bc04439a0fc9c9139e5c9`.
  Its managed report downloaded and opened offline with every rank present;
  report SHA-256:
  `d0492623c20ad6d8fc68cd5513aecb86835adf55e85536f915bceb100a0d47ee`.
  These are synthetic result/report hashes, not release/archive hashes.
- The existing scalar `verify_bo_noise_extension` built-browser journey also
  passed on the final source: q1 target, joint batch, measured observations,
  explicit replicates, exact aggregation, numeric kernel controls, restoration,
  locale/resize without extra POST and managed report. This is separate evidence
  that the earlier scalar UI remains usable, not just a new vector-only test.
- Tutorial sync verified18 blocks, capability metadata AST passed11 tests,
  generated matrix was current, and localization checked3008 source strings
  /4688 keys.
- Full backend regression completed with one CPU thread and no parallel heavy
  test process: **3663 passed / 8 failed / 10 skipped in3664.16s**. All eight
  failures were the four scalar kernel families by two goals in
  `test_bo_kernel_api.py:78`, which still expected newly generated report
  renderer1.5.0 instead of the new shared BO renderer1.6.0. The expectation and
  one outdated migration comment were corrected; no application code, numeric
  tolerance or stored-artifact expectation was changed. The entire affected
  file then passed **11 tests in113.02s**, including all eight failures,
  no-refit confirmation/report, download hashes and restart restoration.
  The hour-long complete suite was not rerun after this test-only correction;
  do not relabel its original nonzero result as a clean single-run pass.
- The ten skipped cases were rerun with `-rs`: six require unavailable Windows
  symlink privileges; four cover POSIX pipe framing, Linux venv symlinks,
  Linux TCP TIME_WAIT or POSIX flock. All ten remained skipped, not passed.
  Existing deprecation warnings were retained rather than hidden or resolved
  through unrelated dependency upgrades.
- Independent source-only reviews confirmed the intended public vertical gate,
  whole-batch ownership and retained numerical boundaries. They also found
  ambiguous historical roadmap wording, now marked Stage1/Stage3e/Stage3g rather
  than describing the current capability. Candidate imports/manual selection,
  profiler and named augmentation contracts remain the next feature gate.
- Final Ruff lint passed; Ruff format verified497 backend/E2E files; mypy
  passed262 source files. `git diff --check` passed with only the existing
  generated-catalog line-ending notice. Branch remains `feat/bo-desirability`
  at the unchanged HEAD below. No application source changed after the final
  browser/build checks or the full backend run.

No remote CI, Linux/Python3.11/Python3.12 native run, archive installation,
release publication, fresh dependency advisory audit or actual JMP output
comparison has run in this gate. Local build/browser evidence does not replace
those gates. No dependencies were added or upgraded. The source remains an
uncommitted worktree over `1db522a12a4023995d52bdcdcf750f9500c47381`;
this is not a new final commit or a verified main push.

All evidence is synthetic and outside Git in
`$env:TEMP\bo-stage3h-20261109`. The initial accessible-label failure and
subsequent default-policy precision failure diagnostics are retained alongside
the passing final receipts, screenshots and traces. No user workspace was used.

Commands use the current worktree backend import and a single thread:

```powershell
$env:PYTHONPATH = Join-Path $PWD 'backend'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_desirability_public_batch.py -q --tb=short
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_desirability_public_batch.py backend/tests/unit/test_openapi_frontend_contract.py backend/tests/unit/test_metadata_store.py backend/tests/unit/test_dev_startup_contract.py backend/tests/unit/test_runtime_entrypoint_versions.py backend/tests/unit/test_health.py backend/tests/unit/test_web_ui.py -q --tb=short
.\.venv\Scripts\python.exe -m mypy backend/app
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe -m ruff format --check backend
.\.venv\Scripts\python.exe scripts/generate_capability_matrix.py --write
.\.venv\Scripts\python.exe -m pytest backend/tests -q --durations=25 --tb=short
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_kernel_api.py -q --tb=short
npm --prefix frontend run test -- --run --maxWorkers=1
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
.\.venv\Scripts\python.exe tests/e2e/bo_desirability_review.py --base-url http://127.0.0.1:8677 --output "$env:TEMP\bo-stage3h-20261109\browser-final-q1"
.\.venv\Scripts\python.exe tests/e2e/bo_desirability_review.py --base-url http://127.0.0.1:8677 --batch-size 2 --output "$env:TEMP\bo-stage3h-20261109\browser-final-q2"
# After stopping and restarting only the owning synthetic test server:
.\.venv\Scripts\python.exe tests/e2e/bo_desirability_review.py --base-url http://127.0.0.1:8677 --restore-receipt "$env:TEMP\bo-stage3h-20261109\browser-final-q2\desirability-receipt.json" --output "$env:TEMP\bo-stage3h-20261109\browser-final-restart"
```

## Rollback

No rollback is executed. After eventual commits, revert only this gate's
commits newest-first, not earlier vector lifecycle work. Code revert does not
reverse metadata28 or turn new recommendation results into old q1 artifacts.
Use a verified pre-upgrade offline backup in a new empty location for an older
binary. Never delete user workspaces, trials, results or models to roll back.
