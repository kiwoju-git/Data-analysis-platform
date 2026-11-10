# Stage 3g: Internal Desirability Batch Search

Date: 2026-11-09. Local worktree `feat/bo-desirability`, starting HEAD
`1db522a12a4023995d52bdcdcf750f9500c47381`. Earlier uncommitted stages are
preserved. No commit, push, remote CI or Linux publication is requested here.

## Acceptance And Scope

This gate completes executable internal q1..8 search from Stage3f's scorer:

- Fit each original response once, with one combined fit budget and fixed
  normalization. Never refit on synthetic planning draws.
- Select an ordered batch with the existing executable mixed-domain search,
  constraints, novelty and explicit minimum batch distance.
- Use a shared deadline, candidate budget and desirability-moment budget across
  all steps, including incumbent evaluation and final canonical re-evaluation.
- Return a complete typed result through the existing owned spawn worker; any
  failed step rejects the entire calculation without creating trials.
- Preserve the public q1 calculation/API/storage contract and exact first-point
  numerics for the same seed, policy, candidate pool and options.

Internal request/result schema5 is not a saved recommendation schema. Public
API33, metadata27, q1 config/result4, shared model5 and item3 are unchanged.
`bayesian_multiresponse_batch` remains false. No route, UI, migration, old
artifact rewrite or new dependency is added in this gate.

The next gate is **public source-locked review, whole ordered-batch atomic
confirmation, individual actual response vectors, exact restore, reports and
UI**. Do not insert further disconnected internal-math gates before that
vertical integration. Reuse the existing bundle transaction and introduce
explicit version dispatch rather than widening old q1 tuples.

## Calculation And Budgets

Policy: `conditional_mc_desirability_beta_marginal_v1`. The first selection
uses the unchanged analytic Beta approximation. Later selections use spatially
joint latent draws within each response, independent response GPs and common
random numbers within each step. The threshold includes xi once. This is a
conditional MC/Beta approximation, not exact noisy joint EI or qNEI.

Default64 draws, explicit16..256, q1..8. Model evaluation/time/thread limits
are inherited unchanged. The separate whole-batch moment ceiling defaults to
8192, maximum65536. One moment evaluation means the combined response
desirability moments; response-moment and quadrature-integrand counts are also
reported. These ceilings are product budgets, not statistical constants.

Preflight accounts for small discrete enumeration (up to256 assignments), the
additional continuous candidate pool, or bounded large-space neighbors. A
scalar `candidate_count_per_step` alone is not the initial pool size. It also
reserves both canonical final evaluations per step and incumbent work.
This is a conservative pool-work admission check; local search can still
exhaust the runtime budget. No options are silently reduced. In particular,
q8 with64 draws and pool32 exceeds the default moment budget and is rejected
before fitting; the caller must explicitly choose admissible options.

All stages share one runtime counter. Exact previously selected coordinates
have zero marginal improvement and skip conditional quadrature, so their
actual count is separately recorded. This matters when a local optimizer
evaluates such a coordinate even though it cannot be the final feasible point.

Every output point is executable/canonical and re-evaluated there. Search seed
is unchanged for step0; later seeds use SHA-256 domain separation. Trial
history order, complete original response vectors and observation identities
are unchanged. Numerical caching is not exact-replicate grouping.

## Base Predictions And Planning Evidence

Each item retains base mean, latent SD, predictive SD, desirability moments and
unconditional Beta EI from completed observations. Separate `planning` fields
hold marginal score, MC standard error, selected-prefix ranks, conditional
variance, seeds and budgets. Conditional variance is not presented as knowledge
already obtained from experiments. MC standard error excludes Beta/quadrature
approximation error and hyperparameter uncertainty.

The bounded per-step evidence contains the exact selected-prefix mean and
covariance, candidate mean/variance/cross-covariance, thresholds and conditional
sample desirability moments used in its final canonical evaluation. Parent
validation checks source/model/noise/normalization identities, feasible moments,
prefix consistency, PSD/Schur conditions, deterministic thresholds, score/MC
error reduction, coordinates/distances/constraints and cumulative counters.
The q1 source/candidate validator is reused without fabricating q1 budgets.

This is **not independent verification of every GP posterior or conditional
quadrature result**. Those remain worker computation, checked by independent
numerical fixtures. The parent does not refit or repeat hundreds of sample
quadratures. It repeats at most one base-moment calculation per selected item.

The same one-worker admission semaphore, bounded JSON pipe, cancellation,
timeout and child cleanup serve schema4 and schema5. No workspace or model
file is touched. Input512KiB/output4MiB bounds remain. Memory bounds are not
an OS-enforced memory limit.

## Direction Review And JMP Boundary

One independent, source-only reviewer was used serially with the parent; no
parallel model fits were delegated. Review covered correctness, old-contract
protection and adherence to the original staged workflow, not just test counts.
It found the exact-selected accounting case and inconsistent off-diagonal
prefix evidence; regression tests accompany their fixes. It also identified
the distinction between actual-coordinate identity and normalized float cache
identity for accounting. Current execution evidence is listed below.

Official [Candidate Set](https://www.jmp.com/support/help/en/19.2/jmp/candidate-set.shtml)
and [Current Batch](https://www.jmp.com/support/help/en/19.2/jmp/current-batch.shtml)
were read for workflow alignment. JMP's documented MaxPro, Refine Model and
Confirm & Challenge strategies are distinct from this policy. Imported/revised
candidate tables, manual selection and those named strategies remain later
gates. No installed JMP or matching output fixture is available; numerical
JMP parity is unverified.

## Current Execution Ledger

- Red: new core tests initially failed collection because the new module did
  not exist. This establishes an unimplemented boundary, not a numerical bug.
- Existing q1/core/contract/batch-scorer regression:120 passed in17.75s after
  shared fit/incumbent/validator extraction.
- Initial new core/worker set:32 passed in75.37s, including actual Windows
  spawn, q8 completion, mixed constraints/local search, q1 first-item equality,
  global-budget failure, immutable input and tampered output rejection.
- Reviewer findings are separately source-confirmed and tested, not attributed
  to observed production failures. Subsequent/final runs are appended below.
- The normalized-cache case was reproduced as a failing regression: five
  distinct actual coordinates include0 and1e-17 in[-1,1], both encoded as0.5.
  The worker correctly performed four incumbent evaluations while validation
  incorrectly required five. The validator now uses canonical `view.raw_x`
  for accounting only; five observation identities/training rows remain.
  That test and exact-selected/local-solver regressions passed3 tests in10.08s.
- The expanded regression before the final cache-accounting fix passed273 tests,
  with1 POSIX-stream-only skip and4 existing deprecation warnings in155.97s.
  It included public q1 HTTP review/confirm, actual spawn, independent Gaussian
  and Beta integration references and old typed results. No tolerance was
  increased to obtain a pass.
- Final source-only review confirmed the three findings' fix connections and
  no additional critical blocker or scope drift. The reviewer did not execute
  tests; parent execution results remain separate evidence.
- Native environment rechecked: Windows10 Home19045, CPython3.10.11, CPU-only.
  This is not a claim of a fresh Windows11, Linux or other-Python execution.
- New public q>1 browser workflow, remote CI, Linux/archive installation and
  JMP output comparison are not executed or claimed in this internal gate.

## Reproduction And Rollback

Native Windows CPython3.10 with installed locked dependencies, one test process:

```powershell
$env:PYTHONPATH = Join-Path $PWD 'backend'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_desirability_batch_acquisition.py backend/tests/unit/test_bo_desirability_batch_core.py backend/tests/unit/test_bo_desirability_batch_worker.py -q --tb=short
```

Changed responsibility modules: new `bo_desirability_batch_core.py`,
`bo_desirability_batch_calculation.py`, `bo_desirability_batch_contract.py`,
core/worker tests and this document. Existing scorer/core/contract/worker share
the numerical/budget and process boundaries. No frontend implementation change.

No rollback is executed. Once committed, revert only this gate's commit, not
earlier vector-history migrations. Schema5 is internal and creates no new
persistent artifact format; public q1 results remain readable. Never delete a
workspace, trial, result or model to roll back code.

## Final Native Checks

The repository check stages were run locally with one model-test process and
CPU thread caps. Frontend tests explicitly use one worker on this constrained
machine. Logs are outside Git at `$env:TEMP\bo-stage3g-20261109`.

- Final full backend: **3650 passed,10 skipped,128 warnings in3485.71s**.
  No product-code changes followed this run. The skips concern POSIX/Linux
  behavior and this Windows account's lack of symlink privilege, including the
  web-UI symlink fixture; none is counted as a pass. Existing Starlette
  deprecations and the deliberate duplicate-ZIP malicious fixture warning remain.
- Final Ruff lint/format: passed,494 files. Mypy:262 source modules passed.
- Tutorial synchronization:18 result blocks. Capability metadata AST:11 tests.
  Generated capability matrix remains current; no public capability was enabled.
- Localization:3008 source strings/4688 keys verified. Frontend lint passed
  with12 existing Fast Refresh warnings; TypeScript typecheck passed.
- Frontend full suite:135 files/1189 tests passed in134.17s, one worker.
  Production build exited0 (Vite4.33s). Existing localization plugin-timing
  and large-chunk warnings remain; they were not suppressed.
- `git diff --check` passed with an existing catalog LF/CRLF notice. HEAD is
  unchanged. No commit, push, tag, CI run or Release was created.

Executed commands in addition to the focused examples above:

```powershell
.\.venv\Scripts\python.exe scripts/render_tutorial_results.py --check
node --test scripts/read_frontend_capability_metadata.test.mjs
.\.venv\Scripts\python.exe scripts/generate_capability_matrix.py --check
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe -m ruff format --check backend
.\.venv\Scripts\python.exe -m mypy backend/app
.\.venv\Scripts\python.exe -m pytest backend/tests --durations=25 -ra
node scripts/check_frontend_localization.mjs
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test -- --run --maxWorkers=1
npm --prefix frontend run build
git diff --check
```

No new browser E2E, Linux/Python3.11/3.12 execution, archive installation,
dependency-advisory refresh, remote CI or actual JMP comparison was performed.
Existing Linux/security/release gate code was not weakened. Their unit tests
are not evidence of running those environments or publishing an archive.
