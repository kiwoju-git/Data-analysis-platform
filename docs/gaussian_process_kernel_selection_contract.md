# Gaussian Process Kernel Selection Contract

Pre-implementation review: 2026-09-16, scikit-learn 1.7.2, NumPy 2.2.6,
SciPy 1.15.3. Standalone GP only; Bayesian paths are not refactored.

## Primary Sources

- [GPR API 1.7](https://scikit-learn.org/1.7/modules/generated/sklearn.gaussian_process.GaussianProcessRegressor.html)
- [Gaussian Process guide 1.7](https://scikit-learn.org/1.7/modules/gaussian_process.html)
- [WhiteKernel](https://scikit-learn.org/1.7/modules/generated/sklearn.gaussian_process.kernels.WhiteKernel.html)
- [RBF](https://scikit-learn.org/1.7/modules/generated/sklearn.gaussian_process.kernels.RBF.html)
- [Matern](https://scikit-learn.org/1.7/modules/generated/sklearn.gaussian_process.kernels.Matern.html)
- [RationalQuadratic](https://scikit-learn.org/1.7/modules/generated/sklearn.gaussian_process.kernels.RationalQuadratic.html)
- [GPML predictive distributions](https://gaussianprocess.org/gpml/chapters/RW2.pdf)

Installed source confirms L-BFGS-B uses scipy.optimize.minimize with analytic
gradients. Restart count excludes the initial start and requires finite bounds.
The new deadline-aware optimizer must use the same defaults and preserve old
single-mode numerical results, seeds and splits.

## Signal, Noise and Jitter

Four signal IDs only: matern_5_2_ard, matern_3_2_ard, rbf_ard,
rational_quadratic. All include Constant amplitude. `estimate` adds WhiteKernel
to every candidate; its noise_level is IID observation-noise variance, not a
smooth signal. `fixed` squares the supplied response-unit SD and scales that
variance onto the training diagonal. `near_noiseless` has only numerical jitter.
Jitter is not new-observation noise. No extra RBF+White signal ID is created.

## Request and Selection

Kernel selection is a strict discriminated union: single/preset (default) or
compare/2..4 unique presets/criterion/retain-details. Legacy top-level preset
normalizes to single. Compare requires validation. CV restarts 0..5, default 0;
final restarts stay 0..10/default 3. Existing row/predictor/LOO limits remain.

Parse complete cases once and make splits once. Every candidate receives the
same row indices, fold-local scaling/response normalization and noise policy.
Single mode retains its old seed. Compare fold seed is
`(base_seed + preset_priority*104729 + fold_index*1009) % (2**32-1)`, with zero
based stable preset priority independent of checkbox order. Full refit uses
`(base_seed + preset_priority*104729) % (2**32-1)`.

Default minimize OOF Gaussian NLPD:
`mean(log(2*pi*predictive_variance)/2 + residual**2/(2*predictive_variance))`.
Variance is observation predictive SD squared, not latent SD, and a recorded
numerical variance floor is used consistently with legacy metric policy.
The request's abbreviated sigma expression is not the Gaussian density formula.
RMSE or MAE can be selected instead. LML is descriptive, not selection evidence.
Ties within relative/absolute 1e-10 use secondary RMSE (NLPD primary) or NLPD,
then closeness of coverage to .95, then stable preset priority listed above.

Failed candidates have null metrics and stable error codes and cannot win.
If all fail, fail the run. A global timeout cannot be disguised as success.
Full-data refit occurs only after selection. Report selection bias: the chosen
CV score is not an independent external test. Nested kernel-family selection
is P1, not claimed in P0.

## Details and Persistence

Without details, nonselected candidates retain CV summaries/warnings only.
With details, successful candidates are refitted on all rows and retain bounded
diagnostics, parameters, training/CV metrics and convergence. They receive no
profiles, surfaces, numeric model artifacts or separate model assets. Only the
selected model uses the existing safe NPZ/JSON lifecycle and prediction API.

New writes: GP .2/result 2/manifest 2, API 20, metadata 20 unchanged. Keep the
existing selected-model fields at the top level, adding typed kernel_selection
and kernel_candidates fields rather than duplicating a large selected result.
Manifest records selection policy, canonical candidate-summary SHA, restart
counts and selected metrics. Schema-1 result/manifest readers remain unchanged
in meaning and never rewrite bytes. No pickle/joblib or user kernel code.

## Resource Gate

Starts = K*folds*(1+CV restarts) + final_refits*(1+final restarts).
final_refits is 1 without details, otherwise K. Validation-none single uses
zero folds. Show the exact count and reject over-budget without trimming.
Before fixing the hard start limit, benchmark N/d = 50/2, 200/5, 500/12 with
K=2/4, folds=5/10 and CV restarts=0/1/5. Record elapsed, peak memory, convergence
and timeout; bounded benchmark timeouts are results, not successful fits.
Existing 5..600 second global budget remains. Candidate CV slices share the
remaining budget fairly while reserving final-refit time; optimizer objective
checks enforce deadlines between numerical evaluations. CPU threads remain 1.

## Validation

Static independent sklearn/GPML reference scripts must not import production
helpers. Cover all four old presets/noise policies, shared splits, deterministic
ranking, partial/all failure, starts/deadlines, detailed retention, schema-1
restore, model tamper/prediction, Bayesian fixtures and KOR/ENG UI/E2E. Existing
workspace values never leave the machine or enter diagnostic logs.
