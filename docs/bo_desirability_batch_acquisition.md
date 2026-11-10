# Multiresponse Batch Acquisition Foundation (Stage 3f)

Date: 2026-11-08. Local base/HEAD:
`1db522a12a4023995d52bdcdcf750f9500c47381`, `feat/bo-desirability`.
This stage is an internal, read-only calculation gate. It does not expose a
multiresponse batch endpoint, change a study, or create pending trials. API33,
metadata27, q1 capability and existing scalar q1..8 behavior remain unchanged.
All Stage3a..3f work remains local; no commit, push, CI or release publication
is performed at the owner's request.

## Acceptance And Risks

- Keep the existing q1 numerical path unchanged for representable posteriors.
- Preserve joint spatial latent covariance within each response; keep the
  explicit independent-response assumption between response models.
- Use fixed models fitted to actual observations only. Never refit, renormalize,
  append fantasies to history or publish conditional planning uncertainty as
  uncertainty based on newly completed experiments.
- Reuse deterministic draws across candidate comparisons, enforce cumulative
  evaluation limits and deadline callbacks, and return no partial score batch.
- Compare conditioning with independent covariance algebra and numerical
  integration, including degenerate, precision and failure cases.

Statistical risks are response independence, conditional Beta approximation and
numerically unresolved covariance directions. Privacy risk is retaining
model-derived simulated values: they stay in bounded local memory and are not
logged, sent outside the app or saved as observations. There are no dependency,
SQL, saved schema or migration changes. CPU cost grows with candidates, MC draws
and response quadrature; this gate is not a large-batch performance claim.

## Policy

Implementation: `statistics/bo_desirability_batch_acquisition.py`.
Policy ID: `conditional_mc_desirability_beta_marginal_v1`.

For the ordered, already selected normalized locations S, each response GP draws
its **joint latent** values at S. Measurement noise and numerical training jitter
are not added to that latent covariance. Raw response units use each model's
stored mean and scale. The existing DS-linear weighted geometric desirability
transforms the sampled response vector at each selected location.

For draw m:

```text
t_m = max(b + xi, max_j D(f(S_j)^m))
mu(x | m) = mu(x) + C_xS solve(C_SS, f(S)^m - mu(S))
var(x | S) = C_xx - C_xS solve(C_SS, C_Sx)
score(x) = mean_m BetaEI(conditional desirability moments, t_m)
```

`b` is the fixed q1 incumbent (maximum expected composite desirability at actual
observed locations), not the best random draw or an optimized unobserved location.
`xi` is applied once in `t_m`. A threshold at/above one yields zero improvement.
Empty S delegates to the existing `evaluate_surrogate_desirability` and
`beta_expected_improvement` exactly, without random draws. A coordinate already
in S has exactly zero marginal improvement, while its base uncertainty remains
visible in the returned base posterior.

This is a **conditional MC/Beta approximate marginal score**, not exact joint EI,
qNEI, or a coherent joint Beta process. Repeated moment matching need not obey
the tower property; summing scores is not a verified total batch EI, and no
submodularity, monotonic score decrease or global search guarantee is claimed.
The reported MC standard error excludes Beta approximation error. A reference
test separately integrates exact clipped-Gaussian improvement and demonstrates
that the Beta policy differs even with the same selected draws.

The scorer returns base actual-data posterior mean, latent SD and predictive SD
separately from conditional planning variance. Samples are not physical
measurements or promises of experimental outcomes.

## Numerical And Resource Boundaries

- Cholesky conditioning for positive-definite selected covariance; explicit
  eigenbasis conditioning for exact deterministic directions. No ridge noise is
  invented to conceal singularity.
- Scale-aware `64 * machine_epsilon * covariance_scale * selected_count`
  checks permit only roundoff-size negative eigenvalues/conditional variance.
  Adjustments and ranks are reported. Material negative values, inconsistent
  null-space cross covariance and unresolved tiny positive eigenvalues fail.
- Complex/non-numeric model arrays are rejected before float conversion.
  Positive variance cannot silently become zero raw SD/variance. Overflow and
  underflow outside representable raw-unit precision return a stable error.
  `bo_desirability_posterior.raw_posterior_standard_deviation` shares this last
  guard with q1, using its existing `bayesian_desirability_numeric_invalid` worker
  error code. Raw-unit failure is not mislabeled as Beta approximation failure;
  ordinary q1 calculations and saved payloads are unchanged.
- Seeds use SHA-256 of policy, root seed, stage/step and **full response ID**;
  never Python's randomized `hash()` or response array position. One fixed set
  of draws is reused for every evaluation in that step. No cross-platform
  bitwise-eigenvector guarantee is made.
- One to four responses; one to ten predictors; zero to seven selected points;
  16..256 draws (default64); at most4096 candidate coordinates per call.
- Candidate chunks default8, maximum128. No query-by-query full covariance is
  built; joint covariance is limited to selected points, at most7x7 per response.
- Cumulative joint-moment budget defaults8192, maximum65536. Preflight charges
  candidates times `(1 + draws)` for nonempty S, conservatively including
  candidates subsequently recognized as already selected. Actual moment,
  response-moment, quadrature and candidate counts are recorded separately.
- Callback checks surround every moment integration and chunk, including
  constructor sampling. Callback cancellation/timeout propagates without a
  partial returned result. This is cooperative checking, **not** an OS-enforced
  memory limit or hard interruption of a library call. Worker integration remains
  a later gate.

## Current Evidence

Host: native Windows10 Home19045, CPython3.10.11, CPU-only; numerical threads
limited to one. Synthetic fixtures only. This is not Windows11/Linux/archive
verification and does not reuse the prior Stage3e browser evidence as proof of
new batch functionality.

| Boundary | Evidence from this stage |
| --- | --- |
| Initial red | New tests failed collection before the scorer module existed |
| First numeric run | 25 passed/2 failed: q1 vectorized prediction changed last-bit results, and a selected coordinate acquired a tiny positive score; direct q1 delegation and exact set-membership semantics fixed both without loosening numeric tolerances |
| Precision probes | Six failing probes exposed raw variance overflow/underflow, zero-adjustment scale overflow and complex covariance truncation; fixed. Source-only agent review identified a further raw-SD-underflow path, independently reproduced by two failing probes and fixed |
| Test-reference correction | An added direct-integration probe initially used an unvalidated numeric literal; it was removed in favor of an independent survival-probability double integral. The two independent integrals agree within1e-10; this was a test correction, not a product numerical change |
| Focused calculation regression | 153 passed in17.64s across desirability, acquisition, posterior, q1 core and new batch scorer; includes52 new batch tests |
| Independent references | Explicit Matérn covariance/linear solves, conditional Gaussian algebra, SciPy quadrature of desirability and Beta density, and exact clipped-Gaussian improvement via two integral identities |
| Determinism/resources | Response reordering, candidate chunk/order, repeated evaluation, full-ID seeds,16/64/256 sample counts, cumulative budget, deadlines, no-refit and unchanged model arrays |
| Static/full checks | Recorded below after completion; not implied by the focused test result |
| Public API/browser/archive | New batch workflow intentionally unexposed; no new q>1 API/browser/archive claim |
| JMP numerical parity | No installed JMP or matching output fixture; unverified |

Precision tolerances are explicit: independent raw posterior3e-12, conditioned
Beta scores/MC standard error3e-10, response-order/chunk comparisons1e-13, exact
Gaussian integration1e-10. q1 uses exact equality with the existing path. No
production helper generates the independent covariance/integral reference.

## JMP Alignment And Next Gate

The official [Candidate Set](https://www.jmp.com/support/help/en/19.2/jmp/candidate-set.shtml)
and [Current Batch](https://www.jmp.com/support/help/en/19.2/jmp/current-batch.shtml)
pages were consulted again for this gate. Their selection workflow motivates
reviewing candidates before committing experiments. JMP's named Space Filling
(MaxPro), Refine Model and Confirm & Challenge strategies are not implemented by
this conditional MC policy. The [MC acquisition research](https://arxiv.org/abs/1805.10196)
is methodological context, not a guarantee for our conditional Beta approximation.

The next vertical gate must connect fixed-base-model search to the existing
bounded worker, source-locked review, atomic whole-batch confirmation, immutable
readers, reports and UI. It must carry policy/draw/budget provenance and distinguish
base from planning uncertainty. It also needs combined search/MC cost preflight;
the scalar candidate-pool size cannot be reused without checking that budget.
It must not relabel scalar schemas, silently
enable q>1, recompute old artifacts or claim JMP strategy equivalence.

## Reproduction And Rollback

```powershell
$env:PYTHONPATH = Join-Path $PWD 'backend'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_desirability_batch_acquisition.py -q
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_desirability.py backend/tests/unit/test_bo_desirability_acquisition.py backend/tests/unit/test_bo_desirability_posterior.py backend/tests/unit/test_bo_desirability_core.py backend/tests/unit/test_bo_desirability_batch_acquisition.py -q
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

For constrained machines run the same frontend test stage with `--maxWorkers=1`
and never overlap model-test processes. Full-check commands, current results and
external synthetic log location are recorded below. Later rollback must revert
only this stage's eventual commit, not prior vector-history migrations. This
stage adds no stored artifacts or SQL changes. Never remove a workspace, model,
trial or result to roll back code. No rollback is performed here.

## Final Local Verification

- Full backend: **3613 passed,10 skipped,128 warnings in3414.38s**. Skips were
  POSIX/Linux-only behavior and unavailable Windows symlink privilege, not
  silently counted as passes. Warnings include existing Starlette deprecations
  and an intentionally duplicated ZIP entry in a malicious-archive fixture.
- After that full run, the final code change reused the existing public numeric
  error code for raw-SD underflow. A direct worker-entry regression first
  reproduced the erroneous generic fit-failure mapping. The final combined
  desirability/worker/q1 HTTP API run passed **192 tests,1 POSIX-only skip in76.40s**.
  It covers the final error-code change; the hour-long full backend suite was not
  repeated after this last error-code-only adjustment.
- Frontend: **135 files/1189 tests passed in142.88s**, one worker; lint and
  typecheck passed. The12 existing Fast Refresh lint warnings remain.
- Tutorial synchronization18 blocks, capability AST11 tests, generated
  capability matrix and localization3008 source strings/4688 keys passed.
- New batch public API, browser E2E, Linux execution, exact archive, remote CI,
  dependency advisory refresh and JMP output parity were **not run** in this
  internal gate. No production dependency or public batch capability changed.

The full-check capture is outside Git at `$env:TEMP\bo-stage3f-20261108`.
It ran the repository check stages in order with CPU thread caps, changing only
the frontend test invocation to `--maxWorkers=1`. The capture wrapper initially
stopped at Vite's stderr plugin-timing warning because PowerShell treated it as
`NativeCommandError`; the direct build was separately rerun to check its exit
status, not to remove or suppress a product assertion. Direct `npm --prefix
frontend run build` finished with **exit0** (Vite4.16s); plugin-timing and large
chunk warnings remain. Final Ruff check/format passed489 files, mypy passed259
modules, and `git diff --check` passed (existing catalog line-ending notice only).

Files in this stage:
- New `bo_desirability_batch_acquisition.py`, its52-case test module and this
  contract/evidence document.
- Existing `bo_desirability_posterior.py`: shared raw-SD representability guard.
- Existing `test_bo_desirability_worker.py`: numeric-error parent/worker boundary
  assertions; worker production code is unchanged.
- README, workflow stages and JMP alignment ledger: internal versus public
  capability distinction. No frontend implementation or saved schema changes.

Additional final commands:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_desirability.py backend/tests/unit/test_bo_desirability_acquisition.py backend/tests/unit/test_bo_desirability_posterior.py backend/tests/unit/test_bo_desirability_core.py backend/tests/unit/test_bo_desirability_batch_acquisition.py backend/tests/unit/test_bo_desirability_worker.py backend/tests/unit/test_bo_desirability_review_api.py -q --tb=short -ra
npm --prefix frontend run test -- --run --maxWorkers=1
npm --prefix frontend run build
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe -m ruff format --check backend
.\.venv\Scripts\python.exe -m mypy backend/app
git diff --check
```
