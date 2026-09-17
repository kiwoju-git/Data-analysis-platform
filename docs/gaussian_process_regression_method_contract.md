# Gaussian Process Regression method contract

## 1. Identity and scope

- Method ID: `regression.gaussian_process`
- Backend module: `regression`
- Method version: `0.3.0`
- Result schema: `3` (schemas 1 and 2 remain readable)
- Model manifest kind: `gaussian_process_model_manifest`
- Model manifest schema: `3` (schemas 1 and 2 remain readable)
- Execution: bounded synchronous analysis handler. The current analysis endpoint is a
  synchronous FastAPI route and therefore runs outside the async event loop. It must
  keep BLAS/OpenMP thread use at one and enforce the limits below.

This is a standalone supervised regression workflow. It is not the Gaussian Process
surrogate workflow owned by Bayesian Optimization. Both workflows may use the same
statistical family, but they have distinct user intent, configuration, results, model
assets, and version contracts. Adding this method does not change
`doe.bayesian_optimization` `0.6.0`.

The AI/ML domain labels that surrogate as `Used by Bayesian Optimization` and
does not count it as available or planned work. It has no separate route or
method ID. The optional link opens this standalone regression method rather
than creating a duplicate GP implementation.

PLS Regression remains `regression.partial_least_squares` `0.1.0`. It is already an
available method and is not reimplemented by this change.

## 2. References

The implementation is based on the installed scikit-learn `1.7.2` public API and the
following primary sources:

- [GaussianProcessRegressor API](https://scikit-learn.org/stable/modules/generated/sklearn.gaussian_process.GaussianProcessRegressor.html)
- [scikit-learn Gaussian Processes guide](https://scikit-learn.org/stable/modules/gaussian_process.html)
- [scikit-learn kernel API](https://scikit-learn.org/stable/api/sklearn.gaussian_process.html#kernels)
- [scikit-learn noisy-target GPR example](https://scikit-learn.org/stable/auto_examples/gaussian_process/plot_gpr_noisy_targets.html)
- Rasmussen and Williams, [Gaussian Processes for Machine Learning, Chapter 2](https://gaussianprocess.org/gpml/chapters/RW2.pdf), especially Algorithm 2.1 and the predictive distribution.

scikit-learn documents `alpha` as diagonal regularization or known observation-noise
variance, and `WhiteKernel.noise_level` as an estimable independent observation-noise
variance. The product UI therefore keeps observation noise separate from numerical
jitter.

## 3. Supported inputs

- One numeric response with nonzero finite sample variance.
- One through twelve distinct numeric predictors with nonzero finite sample variance.
- Integer and decimal columns are accepted unless their role is `id` or their
  measurement level is nominal.
- Missing policy: `complete_case`. The result records total, used, missing-excluded,
  and nonnumeric-excluded row counts.
- Minimum usable rows: `max(5, predictor_count + 2)`.
- Maximum usable rows: 500. No sampling or silent truncation is permitted.
- Leave-One-Out maximum: 200 usable rows.
- Diagnostic point limit: 100 through 2,000.
- Conditional profile grid: at most 80 points per predictor.
- Two-predictor surface: at most 40 by 40 points.
- Stored-model prediction requests: at most 2,000 atomic rows, which includes a
  40 by 40 conditional surface without changing the analysis result.

P0 does not support classification, multiple responses, categorical or datetime
predictors, custom kernel expressions, periodic-kernel search, sparse/variational GP,
heteroscedastic noise, derivative observations, MCMC hyperparameter inference,
process monitoring, or response optimization.

## 4. Preprocessing and leakage boundary

Predictor standardization and response normalization are independent options and are
enabled by default. A standard deviation of zero is an error; no epsilon-based fake
variation is introduced.

For every validation fold, predictor means/scales, response mean/scale, kernel
hyperparameters, observation noise, and Cholesky state are learned only from that
fold's training rows. Validation rows are transformed with training-fold parameters.
The final stored model is refitted on all usable rows after validation. A validation
model is never persisted as the final model.

## 5. Kernel presets

Every preset contains a bounded constant signal amplitude and a base kernel:

| ID | Base kernel | Initial policy |
|---|---|---|
| `matern_5_2_ard` | Matérn, `nu=2.5` | one length scale per standardized predictor |
| `matern_3_2_ard` | Matérn, `nu=1.5` | one length scale per standardized predictor |
| `rbf_ard` | RBF | one length scale per standardized predictor |
| `rational_quadratic` | Rational Quadratic | one shared length scale plus alpha |

User-provided Python, callable optimizers, and arbitrary kernel strings are rejected.
The default preset is `matern_5_2_ard`.

Default standardized-scale bounds are:

- amplitude: `1e-3` through `1e3`
- length scale: new scaled-X UI proposal `0.5` through `100`, initial `1`;
  legacy omitted API settings/preset `0.01` through `100`. Explicit positive finite
  bounds and initial value are configurable. Raw-X values use original units.
- estimated noise variance: `1e-8` through `1e1`
- Rational Quadratic alpha: `1e-2` through `1e2`

## 6. Noise and jitter

Noise modes are:

1. `estimate`: `WhiteKernel` estimates a single homoscedastic observation-noise
   variance. Numerical jitter is supplied separately through `alpha`.
2. `fixed`: the UI accepts observation-noise standard deviation in response units.
   The backend squares it and transforms it to normalized-response variance before
   adding it to the covariance diagonal. It is not optimized.
3. `near_noiseless`: no observation-noise component is added. Numerical jitter still
   stabilizes the covariance matrix and does not prove the observations are noiseless.

Default jitter is `1e-8`; allowed range is `1e-12` through `1e-3` on the normalized
response scale.

## 7. Hyperparameter optimization

The default uses the existing bounded L-BFGS-B log-marginal-likelihood optimizer.
BFGS is an explicit advanced option with logistic-transformed log bounds and
chain-rule gradients, not SciPy's unsupported BFGS box-bounds argument. See
`gaussian_process_optimizer_contract.md` for units, strict-interior initialization,
convergence evidence and independent reproduction tests. No ADAM is used.
Default final restarts are 3; allowed range is 0 through 10. Cross-validation defaults
to zero restarts and allows at most five. A deterministic integer
seed is stored.

The result records the initial policy, fitted kernel, amplitude, predictor length
scales, noise variance and standard deviation, Rational Quadratic alpha when relevant,
log marginal likelihood, restart counts, convergence warnings, elapsed time, and
scikit-learn version. Values at or within one percent of a finite optimization bound
produce a stable bound warning. A short ARD length scale means the fitted response
changes more quickly in that standardized predictor direction; it is not causal
feature importance.

## 8. Cross-validation and metrics

Validation choices are `k_fold`, `leave_one_out`, and `none`. K-Fold accepts two
through ten folds, with shuffle enabled and seed `20260829` by default.

For validation predictions, the result stores or derives:

- out-of-fold mean and predictive standard deviation;
- residual and standardized predictive residual;
- PRESS;
- Predicted R-squared, `1 - PRESS / TSS`, without clipping negative values;
- RMSE and MAE;
- Gaussian negative log predictive density;
- empirical coverage of the nominal 95% predictive interval;
- mean predictive interval width.

Training metrics include R-squared, RMSE, and MAE. This method does not report
coefficient p-values, VIF, OLS ANOVA, adjusted R-squared, or causal importance.

## 9. Predictive uncertainty

The implementation reports two explicitly named quantities when the noise model is
identifiable:

- **Latent function uncertainty** uses the fitted signal kernel and excludes
  observation-noise variance.
- **New-observation predictive uncertainty** adds the fitted or fixed homoscedastic
  observation-noise variance to latent variance.

Numerical jitter is used in the training covariance but is not added as observation
noise in a new-observation interval. For `near_noiseless`, predictive and latent
standard deviations are equal. A 95% interval is `mean +/- 1.959963984540054 * std`.
These are conditional intervals under the selected kernel, bounds, and fitted
hyperparameters; they are not unconditional guarantees.

## 10. Result sections

Schema 2 preserves these schema-1 selected-model fields and adds
`kernel_selection` and `kernel_candidates`. The strict request union, common
CV splits, probabilistic selection, candidate failure/details and resource
budgets are defined in `gaussian_process_kernel_selection_contract.md`.
WhiteKernel estimates IID observation variance; it is never a signal candidate.
Comparison CV scores are selection scores, not independent test estimates.

Selected-model fields:

1. method and preprocessing policy;
2. sample counts and model summary;
3. fitted kernel and hyperparameter table;
4. cross-validation metrics;
5. observed/fitted and observed/out-of-fold diagnostic points;
6. residual, standardized predictive residual, and coverage diagnostics;
7. conditional profiles varying one predictor over its training range while all other
   predictors remain at training medians;
8. an optional two-predictor mean and uncertainty surface, also at training medians for
   other predictors;
9. training ranges and stable warning codes;
10. a model-manifest pointer.

Profiles and surfaces are conditional slices, not partial causal effects. User column
names and values are never localized.

## 11. Safe persistence and prediction

The regression-model catalog stores the normal model record plus:

- a checksummed JSON manifest;
- a model-owned checksummed NumPy `.npz` numeric artifact written atomically.

The artifact permits only numeric arrays and is loaded with `allow_pickle=False`.
The manifest records every array's name, shape, dtype, file checksum, predictor order,
response, source dataset/version/schema hashes, scaling, kernel parameters, noise
policy, training ranges, validation metrics, package versions, and limitations.
Loading rejects object dtypes, unexpected arrays, shapes, non-finite values, checksum
mismatches, stale sources, or paths outside the workspace. No sklearn object is
serialized.

Prediction reconstructs the documented GP posterior from the fitted signal kernel,
scaled training coordinates, stored Cholesky factor, and dual coefficients. It returns
mean, latent standard deviation/interval, new-observation predictive standard
deviation/interval, and extrapolation warnings for every atomic input row. Existing
OLS and PLS prediction contracts are unchanged.

Deleting a GP model through regression-model retention deletes the manifest and numeric
artifact in the same validated lifecycle. Existing artifacts and checksums are not
rewritten.

## 12. Stable failures and warnings

Stable failures include missing/unsupported roles, duplicate predictors, overlap with
the response, insufficient or excessive rows, predictor-count and LOO limits, constant
columns, invalid kernel/noise/jitter/CV configuration, non-positive-definite covariance,
fit or optimization failure, time-budget exhaustion, stale source, manifest/artifact
checksum failure, and invalid prediction input.

Stable warnings cover hyperparameters near bounds, covariance conditioning, negative
Predicted R-squared, interval undercoverage, a large training-validation gap, high
predictive uncertainty, extrapolation, the exact-GP resource limit, non-causal
interpretation, conditional uncertainty, and absence of a global optimum guarantee.
Raw sklearn exception messages are never sent to users.

## 13. Reference and compatibility gates

Tests must include:

- a one-dimensional fixed-kernel posterior independently calculated from the GPML
  equations;
- static expected output based on the official scikit-learn noisy-target example;
- estimated-noise and multivariate ARD fixtures;
- deterministic K-Fold/LOO and fold-local preprocessing checks;
- manifest, NPZ, checksum, tamper, stale-source, extrapolation, and deletion tests;
- unchanged PLS reference fixtures;
- unchanged Bayesian single/batch recommendation reference fixtures.

If sharing low-level kernel utilities changes any existing Bayesian fitted kernel,
prediction, acquisition, or recommended point outside its recorded tolerance, the
Bayesian code path remains unchanged and consolidation is deferred.

## 14. P1 roadmap

Separate contracts and method versions are required for categorical kernels, periodic
models, sparse/variational GP, heteroscedastic noise, multi-output GP, classification,
MCMC hyperparameter uncertainty, GP-based process monitoring, and GP response
optimization. None is advertised as available in P0.
