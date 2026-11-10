# Mixed BO Fitted State

Status: pure-core implementation and focused Windows/Python 3.10 checks passed;
product service, browser, other native-target and archive integration remain
separate gates. This is not evidence of numerical parity with JMP.

## Version And Ownership

`BoMixedSurrogate` is an explicit subclass of the existing posterior interface.
Mixed model metadata is schema 6 (`bo_mixed_noise_latent_v1`); its reusable state
is snapshot 2 (`bo_mixed_surrogate_state_v1`). It requires at least one declared
nominal or ordinal domain. Existing numeric fitting, metadata and snapshot-1
serialization retain their original behavior and bytes.

The only numeric core extension is an overridable signal/noise extractor and an
optional likelihood extractor argument. Their defaults are the original numeric
extractor. Category codes never enter the radial distance or numeric-start
screening by accident. Existing numeric evaluators that require every coordinate
in [0,1] need explicit mixed-domain dispatch before accepting category indices.

## Training View

`fit_bo_mixed_surrogate` receives encoded X, standardized targets, complete factor
domains, a BO noise policy, existing bounded search settings, deadline and raw
normalization mean/scale. Numeric X columns are normalized to the saved bounds;
category columns are exact integer lookup indices in declared level order.
Discrete numeric columns must also lie on the saved executable lattice.

Normalization is not learned again from compressed means. The caller prepares
the raw-observation ddof-0 mean/scale and supplies it explicitly. Minimize sign
handling is explicit; desirability callers must use direction_multiplier=1.
Training uses at most 200 raw observations, 200 effective conditions, 10 factors
and the category/parameter bounds in `bo_factor_correlation_contract.md`.

For exact-repeat compression, callers supply positive integer counts and
standardized within-cell SS. Singleton within-SS must be zero, counts must sum to
the raw N, and an explicit compressed view cannot contain duplicate conditions.
Uncompressed rows keep their independent observations. The covariance is
`K_signal + diag((measurement_variance + jitter) / count)`, with the complete
raw-likelihood correction already used by numeric BO. No sample variance is
added a second time. Prediction of a future single observation adds measurement
variance, not divided noise and not jitter.

## Fitting And Diagnostics

Known category policies and their assumptions are unchanged from the factor
correlation contract. A typed descriptor identifies every free log parameter:
signal amplitude, numeric length scale, category mismatch, hyperspherical angle,
ordered latent gap or measurement variance. Factor and level indices are stored;
user labels are not substituted for parameter identities.

The separate `bounded_typed_factor_starts_v1` policy evaluates the declared
initial vector and up to nine evenly spaced log-bound candidates for free
correlation parameters. Amplitude and noise remain at their declared initial
values for this screening. This is explicitly different from numeric-only
length-scale screening. Best screened starts and seeded random restarts enter
bounded L-BFGS-B; the best finite evaluated point is retained, including a screen
point if local steps do not improve it. Parameter-wise bounds and convergence
receipts remain visible; no global optimum is guaranteed.

Every likelihood evaluation, including the final factorization, consumes the
shared budget. A final evaluation is reserved. Timeout or evaluation exhaustion
raises an explicit error, not a partial fitted model. Thread pools remain capped
at one. Deadline checks bound evaluations, not the duration of an individual
BLAS operation; a service worker supplies any hard process timeout.

Declared but unobserved levels are not replaced or dropped. Per-level raw counts
and unobserved indices are persisted, with
`bayesian_category_unobserved_level_prior_dependent`. A single observed level also
gets `bayesian_category_correlation_unidentified`. Predictions at missing levels
are prior-policy-dependent, not learned evidence about those conditions. A
service may choose a stricter preflight policy explicitly.

## Snapshot Validation

Snapshot 2 stores exact domains/vocabularies/order, a known-kernel JSON payload,
noise policy, normalization, encoded training X, standardized targets, counts,
within-SS, Cholesky L, alpha and typed optimizer diagnostics. Arrays are finite
numeric lists only. JSON objects/strings/array lengths/depth are bounded;
unknown fields, custom objects, invalid codes and unknown policies are rejected.

Load constructs only known kernels and validates:

- domain-to-kernel positions, policies and dimensions;
- fixed/estimated/noiseless measurement variance and separate jitter;
- lower-triangular positive-diagonal L, `L L^T` versus the declared covariance,
  and covariance times alpha versus stored targets;
- the stored LML using stored targets, L and exact-repeat within-SS;
- typed parameter receipts, bounds and evaluation counts;
- mandatory prior-dependence warnings when coverage is incomplete.

Backward-error tolerances scale with machine epsilon, matrix size and arithmetic
magnitudes; they are not widened statistical reference tolerances. Optional
source-derived domains, targets and within-SS can be supplied to the reader.
The service must still verify owner/source/history/artifact hashes. Changing a
vocabulary and all associated metadata without those source hashes is not
cryptographically prevented by covariance validation alone.

Load does not call a fit, optimizer or training-likelihood routine. It checks
stored state through bounded matrix arithmetic. Original package versions stay
in the artifact; freshly evaluated `metadata()` reflects the current runtime and
must not replace a historical provenance receipt.

## Independent Checks

Authored tests compare all four numeric radial families and all three category
policies against independently assembled covariance matrices, dense Cholesky,
mean/joint covariance/LML, and predictive-minus-latent measurement variance.
Unequal-size repeats and singleton groups compare raw versus compressed state;
an independent raw Gaussian likelihood supplies finite-difference gradients.
Additional tests cover code permutations, exact label renaming, all-categorical
inputs, incomplete coverage, budgets, deterministic fits, JSON round trips,
source-bound vocabulary order and tampered covariance/targets/SS/diagnostics.

## Executed Checkpoint

2026-11-10, Windows / CPython 3.10, CPU-only, BLAS/OMP/MKL thread caps 1:

```powershell
# From backend, so imports bind this worktree rather than another editable install.
..\.venv\Scripts\python.exe -m pytest tests/unit/test_bo_mixed_surrogate.py tests/unit/test_bo_mixed_snapshot.py tests/unit/test_bo_surrogate.py tests/unit/test_bo_surrogate_snapshot.py tests/unit/test_bo_kernel_choices.py tests/unit/test_bo_fit_policy.py tests/reference/test_bo_noise_policy_reference.py -q
```

263 passed in 46.79 seconds (tool session 30047). Includes optimized snapshot
roundtrip and the unchanged numeric posterior, snapshot, fit-policy, kernel and
independent noise references. Narrow Ruff check and format check passed for
both new core files, their tests and the existing surrogate hook change.

An earlier invocation from repository root failed test collection because its
editable package resolved a different checkout. No calculation ran in that
attempt. The corrected backend invocation first passed 88 new-core tests in
13.31 seconds; the expanded run above includes the additional optimized receipt
test. The wrong-working-directory failure is not a product calculation failure.

Pure core tests do not establish the full mixed study, candidate/profile/
confirmation/report workflow. Linux, browser and archive verification for this
new mixed adapter have not run at this checkpoint.
