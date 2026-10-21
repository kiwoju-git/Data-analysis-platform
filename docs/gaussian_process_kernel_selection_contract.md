# Gaussian Process Kernel Selection Contract

Current extension: method 0.4.0/result 4/manifest 4/API 26 adds group/time validation,
past-observation lag lineage, nominal predictors and admitted extended Exact GP.
Explicit length-scale/optimizer settings continue through every shared CV fold,
selected refit and optional candidate refit. Legacy numeric seed/ranking behavior
is preserved. See `gaussian_process_optimizer_contract.md` and
`gaussian_process_regression_method_contract.md`. BO has its own policy contract.

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
final restarts stay 0..10/default 3. Existing default-profile predictor/LOO limits remain.

The default row limit remains 500; explicit extended profile permits up to 2,000
only after resource admission. Original plus lag-derived predictors remain at most
12; nominal limits are four predictors and 32 levels each. LOO stays at 200 rows.

Parse complete cases once and make splits once. Every candidate receives the
same row indices, fold-local scaling/response normalization and noise policy.
Group/time plans are computed once before candidate fitting. Time warm-up and
explicit embargo exclusions share one scored mask across all candidates; no
failed fitted fold is silently removed. Each fold learns its own category
vocabulary. Unseen validation levels are a candidate failure, not row exclusion.
Single mode retains its old seed. Compare fold seed is
`(base_seed + preset_priority*104729 + fold_index*1009) % (2**32-1)`, with zero
based stable preset priority independent of checkbox order. Full refit uses
`(base_seed + preset_priority*104729) % (2**32-1)`.

Default minimize OOF Gaussian NLPD:
`mean(log(2*pi*predictive_variance)/2 + residual**2/(2*predictive_variance))`.
Variance is observation predictive SD squared, not latent SD. The unchanged
legacy numerical floor is `numpy.finfo(float64).tiny` (about 2.225074e-308),
an implementation constant rather than an estimated observation variance.
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

The earlier kernel-selection extension wrote method 0.2/result 2/manifest 2.
Current new writes use method 0.4/result 4/manifest 4 with explicit 1/2/3 readers.
No GPR SQL migration is needed. Keep the
existing selected-model fields at the top level, adding typed kernel_selection
and kernel_candidates fields rather than duplicating a large selected result.
Manifest records selection policy, common validation-plan hash, mixed preprocessing,
lag lineage, canonical candidate-summary SHA, restart
counts and selected metrics. Schema-1 result/manifest readers remain unchanged
in meaning and never rewrite bytes. No pickle/joblib or user kernel code.

## Resource Gate

Starts = K*folds*(1+CV restarts) + final_refits*(1+final restarts).
final_refits is 1 without details, otherwise K. Validation-none single uses
zero folds. Show the exact count and reject over-budget without trimming.
The historical pre-extension measured 36-case grid used N/d = 50/2, 200/5, 500/12, K=2/4, folds=5/10,
CV restarts=0/1/5 and a 30-second subprocess limit. Seventeen completed and
nineteen timed out; the release record contains the elapsed/memory results.
The hard limit is 256 optimizer starts. This preserves legacy LOO 200 with
default final restarts (204 starts), and admits four candidates with 10 folds,
five CV restarts and four default final refits (256 starts). It rejects 284
starts rather than trimming the requested search. The benchmark shows that
start count alone does not guarantee completion: N/d and global time also
bound feasibility. A timed-out case is not a successful fit.
The current `gp_resource_budget` admission also accounts for fold N, kernel
parameter/gradient arrays, refits, retained details and prediction buffers under
a conservative 512 MiB estimate. Extended runs use an owned spawn worker; timeout
can interrupt a long BLAS call rather than relying only on optimizer callbacks.
Resource estimation/RSS observation is not an OS-enforced memory limit. The new
501/1,000/2,000 matrix is recorded separately by `benchmark_gp_resources.py` on
each actual OS; the historical grid above does not establish new-profile support.
Existing 5..600 second global budget remains. Candidate CV slices share the
remaining budget fairly while reserving final-refit time; optimizer objective
checks enforce deadlines between numerical evaluations. CPU threads remain 1.
CV receives 75% of the global time budget, shared across remaining candidates;
25% is reserved for selected/detail refits. A nonselected detail refit can fail
after its CV succeeds; retain its CV status and a separate details_failure_code.
The selected full refit must succeed; no lower-ranked fallback is substituted.

## Validation

Static independent sklearn/GPML reference scripts must not import production
helpers. Cover all four old presets/noise policies, shared splits, deterministic
ranking, partial/all failure, starts/deadlines, detailed retention, schema-1
restore, model tamper/prediction, Bayesian fixtures and KOR/ENG UI/E2E. Existing
workspace values never leave the machine or enter diagnostic logs.

### Hosted optimized-reference exception

The Windows static optimized-kernel fixture and its tolerances are unchanged.
The test-only `DATALAB_GP_REFERENCE_MODE` accepts exactly `static` or
`independent`; invalid values fail validation. Without an override, Windows
uses `static` and Linux uses `independent`. Hosted Windows CI explicitly selects
`independent` because CPU/BLAS optimization drift was also observed there.
Independent mode refits the **same frozen x/y, seed and fold row indices** using
the independent sklearn code in `scripts/generate_gp_kernel_reference.py`.
This bounded exception is a same-platform independent numerical cross-check,
not static parity or regeneration of expected values from production code.
No application module is imported by that reference implementation. Static
selected presets, fold identity, legacy results and fixed-hyperparameter
posterior references remain checked. Optimized metrics/LML use the existing
absolute/relative `1e-6`; OOF means and SD retain absolute `1e-6`.

The reason and Linux artifact provenance are recorded in
`docs/linux_numerical_reference_validation.md`. No calculation, optimizer,
kernel-selection rule, dependency pin or production budget changes follow from
this testing policy.
