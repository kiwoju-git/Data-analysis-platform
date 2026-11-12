# BO Desirability Recommendation Core: Stage 3b

Base/HEAD: `1db522a12a4023995d52bdcdcf750f9500c47381`.
Worktree: `feat/bo-desirability`. This stage follows the uncommitted
[Stage 3a foundation](bo_desirability_foundation.md). The owner requested local
implementation and verification, with no GitHub push or release yet.

## Scope And Acceptance

This is an **internal calculation and worker integration**, not an enabled
multiresponse study workflow. Inspection found that the current trial,
canonical history, CAS/idempotent observation update, review confirmation and
report readers all rely on a scalar measured response. Extending those owners
requires a coherent storage/API/UI change; it is not safe to put a calculated
desirability value in their `objective_value` field.

The initial proposed end-to-end connection was therefore split before editing
the production lifecycle. This step completes:

- Complete measured response vectors, keyed by response ID, with explicit goals,
  positive importance, separate kernel/noise policies and matching model IDs.
- One independently fitted raw-response GP per response, a joint desirability
  incumbent at actual completed locations, and one feasible novel candidate.
- Existing numeric kernels, exact-repeat sufficient statistics and mixed search.
- A bounded, owned Windows-spawn worker with strict input/result validation,
  cancellation, deadline cleanup and a source request digest.
- Independent numerical, mapping, resource and existing BO regression checks.

Not enabled here: multiresponse study creation, observation persistence,
confirmation into pending trials, saved multiresponse reports, UI controls or
multiresponse q>1. Existing single-response study/review/q1..8 behavior remains
unchanged. Public API31, metadata25 and BO method0.8.0 remain unchanged.
The internal calculation4/shared-model5 numbers are **reserved calculation
schemas**, not a claim that those versions can be opened as stored artifacts.

## Statistical Contract

`calculate_desirability_recommendation` uses1..4 responses and1..10 existing
continuous/discrete-numeric factors. Every completed observation supplies every
response; missing responses are an error, not a complete-case deletion. Raw
observations remain bounded to200, including when exact-repeat compression is
enabled. The existing product minimum `max(2, factor_count+1)` unique conditions
is retained. It is not a universal mathematical minimum for GP fitting.

Each model is fit once to its **original raw response**, with ddof0 normalization.
Minimize/target goals change the desirability curve, not the training response.
Prediction records expose original-unit mean, latent SD and new-observation
predictive SD separately. Jitter is not measurement noise. The response models
are independent; correlated-response/multi-output GP is not implemented.

Curves use the owner-approved `derringer_suich_linear_v1` policy. Positive
importance is normalized before the weighted geometric payoff is integrated.
For independent latent posteriors:

```text
D = product(d_i(Y_i) ** w_i)
M = product(E[d_i(Y_i) ** w_i])
S = product(E[d_i(Y_i) ** (2*w_i)])
V = S - M*M   (computed with the stable variance recurrence)
b = max(E[D at each completed actual location])
threshold = b + xi_desirability
```

The best actually observed joint payoff is separately recorded with its trial
ID. Maxima of individual responses from different trials are never combined
into a fictitious joint observation. History order is the deterministic tie
break. `xi_desirability` is dimensionless and applied once.

The selected candidate maximizes **moment-matched Beta EI**, not exact EI under
the transformed Gaussian product distribution, not qNEI, and not a claimed JMP
binary match. API43 adds a cancellation-safe positive Beta-density integral for
concentrated shapes; unresolved precision still fails with
`bayesian_desirability_beta_precision_unsupported`.
There is no silent normal/point-mass fallback for unsupported precision.
An all-zero acquisition is explicitly recorded in warnings and search metadata;
the feasible pool's deterministic tie-break is not evidence of improvement.

Exact repeats share trial membership and coordinates across responses, but keep
response-specific means, within sums of squares and fitted noise. Nearby
diagnostics do not merge training data. Every proposed candidate is checked at
its canonical executable coordinate; the existing discrete-fixed/continuous
SLSQP search is reused, not rounding inside a smooth optimizer objective.

## Resource And Boundary Contract

The internal request is strict: unknown fields, booleans/numeric strings in
numeric fields, nonfinite values, mismatched IDs, duplicate trials, off-grid
observations and inconsistent actual/normalized coordinates are rejected.
The typed worker boundary requires documented UUID trial identities. Arbitrary
user-provided file paths, code, pickle or object arrays are not accepted.

One deadline covers all response fits, incumbent evaluations and search.
`model_max_evaluations` is the **combined optimizer evaluation ceiling** across
responses in this new internal policy. Each model receives the remaining
allowance, which is recorded; it does not get a fresh full budget. Final model
factorizations are counted separately. `max_evaluations_total` counts candidate
evaluations containing all response moments; actual quadrature evaluations are
also reported. These counters are not claims of equal CPU cost per candidate.

Posterior caching is limited to512 coordinates. Each response moment integral
has its existing20,000 integrand-evaluation cap. Global time checking surrounds
the bounded integrations. The parent allows20 seconds for spawn/import/protocol
overhead beyond the requested calculation budget, then terminates only its own
child. Cleanup has bounded joins. It is not an OS-enforced memory quota.

`run_desirability_calculation` admits one local worker at a time, limits input
to512KiB and output to4MiB, and uses JSON byte messages. A separate single
receiver thread prevents a partial pipe message from stopping the parent
deadline/cancellation watcher. Closing the owned read handle before joining
the receiver also handles Windows overlapped I/O during early process startup
termination. No process outside this call is terminated.

The immutable byte snapshot is SHA-256 bound to the returned calculation.
The caller changing its mutable Python containers while the worker runs does
not change that snapshot. Output validation checks response/factor/trial
identity, full observation/group provenance, raw normalization, kernel/noise
policy, prediction-noise separation, executable bounds/constraints/novelty,
moment feasibility, observed/latent incumbent selection, EI and budget counts.

This is an internal consistency check, not authentication against a local
administrator or proof of every returned posterior. It does not refit models.
Independent posterior/selection fixtures provide a separate numerical check.
The runtime guard does not reconstruct every GP posterior from fitted kernel
metadata, and it is not a future stored-model reader. Returned result digests
include timing metadata and therefore need not match between repeated runs.
Numeric seed reproducibility is tested separately from wall-clock fields.

## JMP Alignment

The publicly documented JMP workflow fits one GP per response and combines
prediction uncertainty with response goals before selecting experiments.
That workflow motivates this stage, not an exact numerical equivalence claim.
JMP's detailed smooth desirability curves differ from this explicit linear
Derringer-Suich policy. There is no licensed JMP installation/output fixture in
this verification. Persistent candidate-set revisions, manual selection,
augmentation and multiresponse batch planning remain later stages.

Official references revisited for this stage:

- [JMP19.2 BO workflow](https://www.jmp.com/support/help/en/19.2/jmp/bayesian-optimization.shtml).
- [NIST desirability definitions](https://www.itl.nist.gov/div898/handbook/pri/section5/pri5322.htm).
- The direct JMP curve-construction URL could not be fetched in this run; the
  prior research distinctions in [JMP alignment](jmp_gp_bo_alignment.md) remain
  explicitly separate from new execution evidence.

## Current-Run Evidence

Environment: native Windows10 Home19045, CPython3.10.11, NumPy2.2.6,
SciPy1.15.3, scikit-learn1.7.2, CPU-only, one BLAS thread. At most parent plus one
agent; heavy checks run sequentially. Only synthetic fixtures are used.

- Red: new core/contract tests initially failed collection before their modules
  existed. The first19 core tests passed after implementation.
- Independent all-discrete fixture: optimized kernel parameters feed separately
  written Matern covariance/linear solves, raw-response payoff integrals and
  Beta positive-part integrals. Selected executable candidate, incumbent and EI
  agree with absolute tolerance3e-11. It verifies evaluation/selection, not an
  independent proof that the hyperparameter optimizer found a global maximum.
- Source review found a canonical-distance discrepancy. The first probe used
  an invalid1.9e-12 normalized shift and correctly failed input preparation; the
  corrected0.9e-12 probe reproduced erroneous rejection of a valid result.
  Checking the same canonical observation/exclusion union fixed the issue.
- A tampered training variance was initially accepted. A failing regression
  now rejects impossible first/second-moment/variance combinations, including
  training points that were not the selected incumbent.
- The receive-thread change initially left a receiver alive after Windows
  startup-time termination. Both timeout/cancel regressions failed. Closing
  the owned read handle before joining fixed it; all4 native failure cleanup
  cases passed. The POSIX partial-stream-frame test is skipped on Windows,
  whose pipe protocol is message-oriented, and is not claimed as a Linux pass.
- Focused new/legacy core/reference run:230 passed,1 skipped in41.75s. Full
  project Ruff lint and format (478 files) passed at this point.
- Two additional core regressions passed in5.77s: four responses use four
  different kernels with maximize/minimize/target goals; positive affine unit
  changes applied to response/limits/noise SD preserve recommendation/payoff and
  transform raw predictions correctly. No numerical tolerance was enlarged.
- The full `scripts/check.ps1` backend phase passed3505 tests, skipped10 and
  reported118 warnings in3143.67s (52m23s). All98 newly added Stage3b cases were
  collected:97 passed and the POSIX-specific frame case was skipped on Windows.
  Skipped cases are not passes. Existing Starlette deprecation warnings and the
  intentionally duplicated archive-member fixture warning remain; no unrelated
  dependency upgrade was made to suppress them.
- Full-project Ruff/format (478 files), mypy (252 source modules), tutorial sync,
  capability AST11 tests and capability matrix checks passed. An earlier
  isolated strict-mypy invocation reported11 imported-existing-module issues;
  the repository's actual full-check invocation passed without source changes
  to those modules. Localization2973 strings/4646 keys also passed.
- Frontend lint passed with12 existing fast-refresh warnings; typecheck passed.
  All129 test files/1124 tests passed in87.09s. Production build passed in4.33s
  with existing chunk-size and localization-plugin timing warnings.
- The full `scripts/check.ps1` completed with exit code0. No product source was
  changed during or after that full run; only this evidence ledger was updated.
- Not run: actual browser E2E for a new multiresponse workflow (none is exposed),
  Linux3.11/3.12/native archive execution, Windows11 specifically, a new live
  dependency advisory audit, remote CI, or actual same-input JMP output parity.
  Source/fixture tests whose names include E2E or release are not treated as
  browser or installed-archive execution. No GitHub push or release occurred.

Reproduction from the isolated worktree with the locked environment:

```powershell
$env:PYTHONPATH = Join-Path $PWD 'backend'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_desirability_core.py backend/tests/unit/test_bo_desirability_contract.py backend/tests/unit/test_bo_desirability_worker.py -q
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

## Remaining Gate And Rollback

The original complete integration gate was split explicitly in
[Stage 3c](bo_multiresponse_lifecycle.md): vector definition/storage, atomic
CAS/idempotency, history hashes, restore/replicates/close/delete/backup, managed
history reports and read-only UI are one separately versioned capability.
Recommendation remains disabled for these studies. The next gate must connect
exact review/confirmation and editable UI without exposing an incomplete
recommendation lifecycle. Do not expose q>1 before a validated joint policy.

No user workspace, previous result, model or history is rewritten. No GitHub
push or release is performed. There is no new published commit to revert yet.
After eventual commits, revert only these stages' commits in reverse order;
never reset shared main or delete data as a code rollback.
