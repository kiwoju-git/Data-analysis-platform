# BO Numeric Kernel Alignment

BASE_SHA: `fb98a1fc5bc68baa2afc7c72a07a8a05f8f2ecdb`.
Stage 2 follows the reviewed-candidate workflow. Linux publication is deferred.

## Acceptance And Boundaries

- Select Gaussian, Matern 5/2, Matern 3/2 or Exponential for numeric BO inputs.
  Preserve Matern 5/2 as the default and retain the existing UI structure.
- The selected family must govern the fit, latent EI/ETI, joint batch covariance,
  stored review/confirmation, reopening and managed report, not just its label.
- Preserve noise/jitter separation, raw normalization, compression likelihood,
  budgets, source guards, immutable history and legacy readers/checksums.
- Validate covariance and posterior against independent formulas/Cholesky,
  log-parameter gradients by finite differences, raw/compressed equivalence,
  actual API storage/restore and built UI behavior.
- New request/config3, result3, model4, method0.8.0 and API31 explicitly identify
  this extension. Item2 and the existing acquisition policy retain their meaning.
  Metadata25 is needed only to extend the existing batch table's SQL version
  CHECK; it must preserve every existing JSON payload and hash.

Risks: radial versus separable covariance conventions; confusing JMP theta with
length scale; changing old serialized defaults; mismatched kernel provenance;
noise being included in acquisition uncertainty; source invalidation during a
review. No standalone GPR defaults, recent DOE features or user files change.
No new runtime dependency, telemetry or external data transfer is introduced.

## Evidence

Source inspection confirms the existing BO core is restricted to constant times
ARD Matern5/2. JMP19.2 BO lists Gaussian, Matern5/2, Matern3/2 and Exponential.
The official launch screenshot shows Matern5/2 selected. The implementation's
radial scaled-Euclidean convention and normalized-coordinate length scales must
be explicit; an undocumented JMP multidimensional convention is not inferred.
No JMP application or same-input JMP output is available. Formula checks are
not numerical parity evidence. Multiresponse desirability, imported candidate
sets and augmentation strategies remain separate subsequent stages.

The log below distinguishes source, API, browser and native CI evidence.
Prior stage test counts are not evidence for this change.

## Mathematical Contract

Each study factor retains its ID/order and bounds. Let `z_k=(x_k-low_k)/range_k`
and `d^2=sum_k((z_k-z'_k)/ell_k)^2`. With signal variance `a`:

| Choice | Signal covariance divided by a |
| --- | --- |
| Gaussian | `exp(-d^2/2)` |
| Matern 5/2 | `(1+sqrt(5)*d+5*d^2/3)*exp(-sqrt(5)*d)` |
| Matern 3/2 | `(1+sqrt(3)*d)*exp(-sqrt(3)*d)` |
| Exponential | `exp(-d)` |

These are radial, ARD-scaled Euclidean covariances, not products of one-dimensional
Matern/exponential correlations. Existing sklearn1.7.2 RBF/Matern implementations
and their analytic log-parameter gradients are reused; no dependency is added.
Signal variance starts at1 (bounds1e-3..1e3); each normalized length scale starts
at1 (bounds1e-2..1e2). These are retained product settings, not documented JMP
defaults. Actual fitted values, bounds, starts, optimizer status and package
versions are saved. Measurement noise, numerical jitter, ddof0 centering/scaling,
latent plug-in incumbent, EI/ETI and conditional MC policy remain independent of
the selected family. Single response only; nominal/ordinal BO is not added.

JMP's documented standalone Gaussian `exp(-sum(theta_k*delta_x_k^2))` is algebraically
equivalent to `theta_k=1/(2*ell_k^2)` in identical coordinate units. In actual units
our equivalent value is `1/(2*ell_normalized_k^2*range_k^2)`. This is NOT the
optimizer's log parameter and does not establish fitted-theta parity. No such
conversion is claimed for JMP BO Matern/exponential. JMP's estimated intercept,
its unpublished multidimensional details and our centered zero-mean surrogate
can differ even with matching option names. No best-kernel claim is made.

## Primary Sources (Inspected 2026-11-07)

- [JMP19.2 BO launch options](https://www.jmp.com/support/help/en/19.2/jmp/launch-the-bayesian-optimization-platform.shtml): four continuous correlation choices.
- [Official launch screenshot](https://www.jmp.com/support/help/en/19.2/jmp/images/launchwindow-7.png): Matern5/2 selected; screenshot evidence, not a textual universal default guarantee.
- [JMP BO scripting index](https://jsl.jmp.com/All%20Categories/Objects/Bayesian%20Optimization.html): input correlation terminology; unversioned supplemental source.
- [JMP Gaussian continuous details](https://www.jmp.com/support/help/en/19.2/jmp/statistical-details-for-models-with-continuous-predictors.shtml): Gaussian theta convention. Standalone GP is not the BO option contract.
- [Pinned sklearn1.7.2 kernel source](https://github.com/scikit-learn/scikit-learn/blob/1.7.2/sklearn/gaussian_process/kernels.py): scaled-distance implementation and gradients; the independent tests spell out the formulas instead of calling this implementation for expected values.

Desirability, JMP augmentation algorithms, fixed theta/intercept fitting,
categorical correlation options and external JMP output comparison remain outside
this stage. Selecting one of these families does not make EI/ETI JMP's acquisition.

## Current-Run Log

- Red: new kernel tests failed collection because `bo_kernels` did not exist.
- Green: new posterior/gradient/compression tests plus existing surrogate suite:
  47 passed on Windows CPython3.10.11, CPU-only, one BLAS thread.
- First legacy API/review/health run:38 passed,2 failed. Both failures were the
  explicit registry expectation0.7.0 after method0.8.0 was introduced. The test
  now preserves explicit0.6/0.7 cases and adds0.8. No failed product
  assertion was suppressed and no numerical tolerance was increased.
- New kernel math and real-spawn API suite:49 passed in125.80s. This includes
  all four families, target/directional requests, review/confirm/retry/restart,
  no-refit managed report generation/download and populated metadata24 backup,
  restore and migration25 with unchanged old records/checksums.
- OpenAPI, health, legacy noise/review API, metadata, backup and archive-verifier
  regression suite:572 passed in360.72s. The old registry expectation failures
  above are resolved. Archive-verifier unit tests are not an installed archive.
- Additional core/reference/runtime suite first stopped with80 passes/2 failures:
  the startup test still expected metadata24 and the contract document abbreviated
  Expected Improvement. Both expectations/documentation were corrected; final
  rerun passed89 tests in34.66s. No calculation assertion/tolerance was weakened.
- Frontend full suite:129 files/1124 tests, single worker. Related228 tests,
  TypeScript, localization (2973 source strings/4646 keys), lint and production
  build passed. Lint retains12 existing refresh warnings; build retains the
  existing large-chunk and localization-plugin timing warnings.
- Backend Ruff lint/format and mypy passed (246 source modules). Mypy initially
  rejected a float Literal; the field now uses a finite value constrained to1.
  An exploratory Ruff scan beyond the repository check scope found two existing
  unrelated script warnings; they were not suppressed or changed. The required
  `ruff check backend` gate is clean.
- Tutorial Markdown18 blocks, capability AST11 tests and generated capability
  matrix checks passed. Capability inventory was regenerated from the registry.
- Built UI on Windows/Chromium passed the shared context and workflow journeys:
  all four kernel choices, q1 target/q2 batch, raw/exact-repeat view, review
  invalidation, explicit retry after lost confirmation, reopening and managed
  HTML numeric checks. KO/EN at1024/1440 retain source/options without another
  POST on locale/resize/reload. DOM geometry and screenshots were inspected;
  no page error or document horizontal overflow occurred in those journeys.
  All inputs/workspaces/diagnostics are synthetic and outside the repository.
- The added expanded-parameter browser assertion first found two summary
  elements (the previous saved batch and new review), not a calculation failure.
  The locator was scoped to its exact review/result owner. Repeated context and
  workflow journeys passed, reading the visible amplitude/length-scale cells
  against their saved values. Expanded1024px English screenshot was inspected.
- Full Windows/Linux/Python3.11/security/release-ready and exact-archive gates
  are required on this branch before main integration. Their commit-specific
  run URLs/results are recorded in the PR and final handoff, not inferred from
  the successful baseline main run.
- First PR CI42316912601: Linux3.12 and Python3.11 each reported3312 passed,
  16 skipped,5 failed. Failures were two stale current-registry expectations in
  the legacy tutorial tests (the recorded algorithm stays0.6.0), two incomplete
  mocked HTML payload/locator fixtures, and the explicit statistical-module
  sklearn allowlist missing `bo_kernels`. No production numerical failure was
  reported in these runs. Tests now distinguish old/new HTML contracts and the
  new lazy statistical import; the startup no-sklearn assertion remains intact.
  Full CI must rerun; the first failed run is retained as evidence, not a pass.
- The three affected tutorial/HTML-fixture/dependency-boundary test files passed
  all36 tests locally in30.41s after the corrections; Ruff lint/format passed.
  Recorded tutorial input files and numerical output were not regenerated.
- Second PR CI42318187185 passed3319 backend tests (16 conditional skips) on
  Linux3.12/Python3.11 and1124 frontend tests. Linux E2E then reached the older
  comprehensive BO lifecycle driver, whose new-UI assertion still expected
  schema2. A focused built-UI run reproduced that exact assertion; it now checks
  request/result3, model4 and requested/stored family equality. The full focused
  lifecycle rerun passed creation, observations, three recommendations, abandon,
  budget, refresh, close and deletion. Production calculations are unchanged.
  Native aggregate/archive validation must run again on the resulting commit.
- The first Windows CI finished later with3322 passed/3 skipped/8 failed.
  Five failures matched the already corrected cross-platform fixtures; three
  more were Windows-only PowerShell startup tests still accepting metadata24.
  They now reject24, accept25 and require the numeric-kernel capability.
  Local red reproduced those three assertions plus two missing-worktree-venv
  setup failures. Reusing the existing locked environment at the expected
  development path resolved setup without changing the startup scripts.
  The complete startup/runtime subset then passed20 tests in56.05s on Windows;
  Ruff lint/format passed. The prior CI is not counted as a Windows pass.
  A new full CI is required after this test-only correction.

Focused PowerShell checks (use the locked environment from bootstrap):

```powershell
$env:PYTHONPATH = Join-Path $PWD 'backend'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_kernel_choices.py backend/tests/unit/test_bo_kernel_api.py -q
npm --prefix frontend run test -- --run --maxWorkers=1
powershell -ExecutionPolicy Bypass -File scripts/check.ps1
```

The shared `tests/e2e/bo_noise_extension.py` is called by the existing native
context/workflows suites and Linux archive verifier. The archive receipt now
requires numeric-kernel UI evidence as well as the prior BO workflow checks.

## Upgrade And Rollback

Before first startup of this version, stop the application and take an offline
backup with the existing source's scripts. Keep the archive outside the workspace.
Examples use synthetic operator-selected paths, not a default user workspace:

```powershell
.\.venv\Scripts\python.exe scripts/backup_workspace.py `
  --workspace "D:\Workspaces\Study" --output "D:\Backups\Study-pre-kernels.zip"
.\.venv\Scripts\python.exe scripts/restore_workspace.py `
  --archive "D:\Backups\Study-pre-kernels.zip" --workspace "D:\Workspaces\Study-restored"
```

Restore requires a fresh empty destination. The backup reader supports20..25;
restoring24 does not migrate until an explicit app startup. Migration25 extends
the BO batch version CHECK without rewriting existing payloads, hashes, trials
or observations. The API test compares every populated batch/item/trial/history
record before and after migration and verifies foreign keys and old/new readers.

Revert only this stage's commit(s), newest first: `git revert <commit>`.
Frontend/backend/runtime/storage form one contract; UI-only rollback to an old
API expectation is not a supported downgrade. Code revert does not downgrade
metadata25. Older code cannot open that workspace or new model4 results: use
the verified pre-upgrade backup in a new destination to run the older code,
keeping the current workspace and new results intact. Never delete a workspace,
rewrite results, reset hard or force push as a rollback shortcut.

Linux prerelease publication is deferred by owner instruction. Existing CI
archive/offline-install checks remain required; a built development UI check
alone is not archive evidence.
