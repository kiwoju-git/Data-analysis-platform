# Regularized Linear Model Contract

Status: implementation contract; verification results are recorded separately.
Base: `019c73f66fc177cf5de303dedd920a45048739b1`, 2026-09-07.

## Scope And Acceptance Gates

One `regression.linear_model` run fits one selected estimator: `ols` (default),
`ridge`, `lasso`, or `elastic_net`. No additional method IDs or sidebar leaves
are introduced. Existing OLS numerical calculations, backward elimination,
inference, saved-result readers, prediction intervals, and optimizer remain.
New penalized fits must support safe model persistence, point prediction,
training-domain optimization, localized reports, and accessible diagnostics.
The eight presentation domains retain their mappings; only selection-screen
density changes, with cards before a closed selection-guide disclosure.
Historical commit `fb07c68405e0038e2a694a35d806a1a191b2cfda` is a visual-density
reference, not a source replacement or repository rollback.

Acceptance requires independent numerical fixtures, OLS compatibility tests,
fold-scaling and nested-validation tests, manifest tampering tests, frontend
tests, strict typecheck, build, and desktop/mobile Chromium verification.
An implemented option without calculation/storage/prediction is not complete.

## Official Sources And Installed Environment

Verified locally: CPython 3.10.11, scikit-learn 1.7.2, NumPy 2.2.6, SciPy 1.15.3.
No production dependency is added.

- [Linear models](https://scikit-learn.org/1.7/modules/linear_model.html)
- [LinearRegression](https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.LinearRegression.html)
- [Ridge](https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.Ridge.html),
  [RidgeCV](https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.RidgeCV.html)
- [Lasso](https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.Lasso.html),
  [LassoCV](https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.LassoCV.html)
- [ElasticNet](https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.ElasticNet.html),
  [ElasticNetCV](https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.ElasticNetCV.html)
- [StandardScaler](https://scikit-learn.org/1.7/modules/generated/sklearn.preprocessing.StandardScaler.html)
- [Pipeline](https://scikit-learn.org/1.7/modules/generated/sklearn.pipeline.Pipeline.html)
- [GridSearchCV](https://scikit-learn.org/1.7/modules/generated/sklearn.model_selection.GridSearchCV.html)
- [KFold](https://scikit-learn.org/1.7/modules/generated/sklearn.model_selection.KFold.html)
- [Cross-validation](https://scikit-learn.org/1.7/modules/cross_validation.html)
- [Minitab model-selection formulas](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/regression/how-to/fit-regression-model/methods-and-formulas/stepwise/)
- [Minitab stepwise options](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/regression/how-to/fit-regression-model/perform-the-analysis/perform-stepwise-regression/)

Minitab's term selection and hierarchical backward elimination inform the
existing OLS contract. They are not evidence for classical inference after
penalized fitting. Internal CV estimators are not placed behind a scaler fit
on all rows: scaling must be inside each candidate's training fold.

| Property | OLS | Ridge | Lasso | Elastic Net |
| --- | --- | --- | --- | --- |
| Loss | SSE | SSE + L2 | SSE/(2N) + L1 | SSE/(2N) + L1/L2 |
| Shrinkage | None | Coefficients shrink | Exact zeros possible | Shrinkage and exact zeros |
| Collinearity | Can be unstable | L2 stabilization | Selection can be unstable | L2 can stabilize correlated features |
| Penalty alpha | None | Required, positive | Required, positive | Required, positive |
| l1_ratio | N/A | N/A | Implicitly 1 | Strictly between 0 and 1 |
| Feature scaling | Existing policy | Required | Required | Required |
| Classical p-values | Existing OLS | Unavailable | Unavailable | Unavailable |
| OLS ANOVA | Existing OLS | Unavailable | Unavailable | Unavailable |
| CV tuning | Not required | Default | Default | Default |
| Prediction intervals | Existing OLS | P0 unavailable | P0 unavailable | P0 unavailable |

## Input And Shared Design

Options are discriminated by `estimator`; omitted discriminator normalizes to
legacy OLS. Unknown or incompatible fields fail typed validation. Common input
is one supported numeric response, 1-20 supported predictors, explicit numeric
quadratics/interactions, intercept, filter, and complete-case policy.
Existing role-independent numeric/category classification, deterministic sorted
treatment levels and first reference, feature order/names, parsing, exclusions,
row identity, and training domains are reused. No arbitrary formula is accepted.

The feature map is a declared, response-independent treatment contrast map;
all levels and the reference are recorded, including levels absent in a fold.
This is not target encoding or learned feature selection. A training-fold
constant column has scale 1, no estimable variation, and a persisted warning;
its presence does not allow validation responses into training. Globally
constant source/derived features still fail preflight. Predictor/category
selection must be prespecified; CV does not validate data-driven selection
performed by the user before this run.

OLS uses the existing NumPy least-squares implementation unchanged. Its rank,
residual degrees-of-freedom and inference checks are not imposed on penalized
fits. The shared intermediate representation includes original feature matrix,
response, row indices, coefficient metadata, model terms, levels/reference,
source columns and training ranges.

## Estimators And Scaling

For each training fold, `Pipeline(StandardScaler, estimator)` centers and
scales every non-intercept feature, including dummy, quadratic and interaction
columns, using population SD (`ddof=0`). The response remains in original units.
The fitted intercept is unpenalized. With scaled coefficients `w`, feature mean
`m`, scale `s`, and fitted intercept `a`, persisted original coefficients are
`b = w / s`, with intercept `b0 = a - dot(m, b)`.

- Ridge uses deterministic dense SVD and minimizes `SSE + alpha * sum(b^2)`
  on the standardized-feature scale.
- Lasso uses cyclic coordinate descent and minimizes
  `SSE/(2N) + alpha * sum(abs(b))`.
- Elastic Net uses cyclic coordinate descent and minimizes
  `SSE/(2N) + alpha*r*sum(abs(b)) + alpha*(1-r)*sum(b^2)/2`.
- Alpha must be finite and positive. Zero means choose OLS. Elastic Net
  endpoints mean choose Ridge/Lasso, not a silently substituted estimator.
- Alpha magnitudes are not directly comparable between Ridge and Lasso/EN,
  and depend on response units. Iterations, tolerance, dual gap and convergence
  are recorded. Nonconverged output is never silently declared converged.

## Tuning, Validation And Budgets

Automatic tuning defaults to shuffled five-fold outer and five-fold inner CV,
seed `20260907`. Every inner fit gets a fresh pipeline. Outer test responses
are used only for evaluation; final-model tuning is a separate inner search
on all usable data, followed by full-data refit. Every usable row has exactly
one OOF prediction. Fixed mode uses the fixed parameters for every OOF fit;
no hyperparameter search occurs. Optional no-validation is fixed-mode only.
LOO outer validation is limited to 200 usable rows and the same fit budget;
inner selection remains explicit K-fold.

Defaults: Ridge log10 alpha -6..6 (49 candidates); Lasso/EN -6..1
(50 candidates). EN ratios: 0.10, 0.50, 0.70, 0.90, 0.95, 0.99.
Candidate counts/ranges, folds, ratios, seed and resolved grids are stored.
Minimum-CV-MSE ties within `1e-12 * max(1, abs(best_error))` prefer larger
alpha, then smaller l1_ratio; ties do not use outer test data.

Initial safety limits: 5-10,000 usable rows, 200 design features, 10,000 total
fits (including inner search, outer refits, final search/refit, and coefficient
path), 120-second requested calculation budget (maximum 300 seconds), one
numerical thread. No row sampling or silent grid reduction. Estimate the exact
fit count before allocation; reject excessive search with a stable error.
Calculation runs in a spawn-safe bounded process outside the FastAPI event
loop, using the existing synchronous analysis-run lifecycle rather than
claiming a nonexistent generic job worker. Timeout must terminate computation
and leave no successful model/result or abandoned owned artifacts.
Limits remain subject to measured verification, recorded with exact commands.

OOF metrics: PRESS=sum(residual^2), predicted R-squared=1-PRESS/TSS (negative
retained), RMSE=sqrt(PRESS/N), MAE=mean(abs(residual)). Training metrics are
separate. CV curve fold variability is SD, not a confidence interval. The
full-data inner curve is tuning evidence, not an independent performance claim.

## Results, Diagnostics And Interpretation

New results identify estimator and penalty, sample/exclusions, original design,
equation, training metrics, validation metrics/config/fold membership,
regularization candidates/selection/convergence/scaler, coefficients,
bounded diagnostics, model manifest identity and stable warnings.
OLS retains every current inference and diagnostic section.

Penalized results have original/scaled coefficients and zero indicators, CV
error curve, coefficient path, observed/fitted and observed/OOF plots, residual
vs fitted/order, histogram and Q-Q. They do not contain OLS coefficient SE/t/p/CI,
ANOVA, VIF, adjusted R-squared, leverage or Cook's D presented as penalized
inference. At most 500 diagnostic observations are displayed deterministically;
the fit uses all usable rows. The interactive path defaults to one feature,
with a selector covering every feature and a full path table. This avoids
overlapping lines on mobile without dropping any fitted features. HTML embeds
up to 20 feature paths and retains the full numeric path table.

Lasso/EN do not enforce strong hierarchy. Each treatment-coded category level
is penalized separately, not as a whole factor. Zero coefficients do not imply
causality, significance, or whole-factor selection. All-zero models are valid
intercept-only predictions with an explicit warning, not fabricated failures.
Negative predicted R-squared, training/CV gaps, convergence, extreme shrinkage,
constant-fold features, extrapolation, and predictive-not-causal limitations
remain in stored results and reports.

## Persistence, Prediction And Optimization

Model manifest schema 4 discriminates `ols/ridge/lasso/elastic_net` and stores
source identities/hashes, feature coding/order, original coefficients/intercept,
training ranges, selected alpha/ratio, scaler means/scales, validation summary,
convergence, package versions, and limitations. OLS prediction covariance
remains OLS-only. JSON is sufficient; pickle/joblib are forbidden.
Existing manifest schemas 2/3 and result schemas 4/5 are read without rewriting
bytes or checksums. Model ownership, mutable metadata, deletion blockers and
atomic result/manifest persistence use the current regression-model catalog.

The manual grid and dataset prediction retain current validation, atomic manual
input policy, category checks, source freshness, and manifest SHA checks.
Regularized prediction returns point estimates; interval fields are null with
`prediction_uncertainty_kind=point_only` and a localized unavailability reason.
OLS mean-response CI and individual prediction intervals retain their meaning.
The existing optimizer evaluates the same original-scale design vector and
coefficients, with no refit, within training bounds/known levels. It records
estimator/tuning metadata and warns that zero coefficients can give flat
profiles. No optimizer uncertainty or global guarantee is invented.

## Versions And Compatibility

New writes: API 18; `regression.linear_model` 0.3.0/result 6;
regression manifest 4; `regression.predict` 0.3.0/result 3/config 4/rows 2;
`regression.predict_pasted` 0.2.0/response 2 (owned input artifacts remain 1);
`regression.linear_model_optimizer` 0.2.0/result 2/config 2. The unchanged
optimizer calculation core still emits schema 1 internally; the service adds
model-kind and selected-penalty metadata to the schema-2 stored envelope.
Runtime, startup script, typed schemas, frontend readers and tests are synchronized.
Metadata stays 19: existing JSON artifacts/ownership cover this extension.
PCA/PLS/GP/DOE/Bayesian calculations, IDs, routes and checksums are untouched.

Schema-4 model metadata is validated as a Pydantic discriminated union on write
and read. Read validation does not serialize or rewrite the stored JSON. The
regularized prediction basis has no covariance matrix or residual degrees of
freedom. Legacy manifest 2/3 and dataset-prediction 0.2.0/result 2/config 3/rows 2
use the existing validation path.

Input scan is bounded at 100,000 rows, with 5-10,000 complete usable rows and
at most 200 derived features. No row is silently sampled for fitting. The
existing synchronous FastAPI route dispatches regularized CPU work to a
spawned, single-capacity process with a parent deadline and cleanup. It remains
catalog `inline`, not a fictitious queued job. Results travel as bounded JSON;
no sklearn object is serialized. Hard limits are 10,000 solver fits and 300
seconds, with a default 120-second budget plus 20-second process startup allowance.

## Verification And Deferred Scope

Static fixtures are generated independently of production helpers: Ridge
closed-form normal equations; hand-checkable orthogonal Lasso/EN shrinkage;
separate sklearn reference scripts for correlated, categorical/derived-feature,
and nested-CV cases, with versions, seed, expected OOF values and tolerances.
Tests assert scaling per training fold, exact OOF coverage, final refit,
back-transformed prediction, convergence, search/time limits and manifest
tamper rejection. Existing OLS reference/selection/prediction/optimizer tests
must remain numerically unchanged.

P1: group/hierarchical penalties, conformal or bootstrap intervals, group/time
splits, estimator-comparison workflow. These need separate statistical
contracts and coverage/reference fixtures; none is presented as available.
