# PLS Regression Method Contract

Status: P0 implementation contract  
Method ID: `regression.partial_least_squares`  
Method version: `0.1.0`  
Result schema: `1`  
Model manifest kind/schema: `pls_model_manifest` / `1`

## 1. Purpose and scope

Partial Least Squares (PLS) regression builds supervised latent components that
use covariance between numeric predictors (`X`) and one numeric response (`y`).
It is intended for prediction when predictors are numerous or highly
collinear. It does not establish causal effects.

P0 implements PLS1 only:

- one numeric response;
- two or more numeric predictors;
- complete-case missing-value handling;
- optional predictor and response scaling;
- fixed component count or cross-validated component selection;
- K-fold or leave-one-out cross-validation;
- JSON model persistence and point prediction.

P0 does not implement PLS2, categorical predictors, interactions, polynomial
terms, sample weights, coefficient tests, OLS ANOVA, VIF, response
optimization, bootstrap intervals, permutation tests, prediction intervals, or
PLS-based process monitoring. PCA remains a separate planned unsupervised
workflow because it summarizes `X` variance without using a response.

## 2. Reference basis

The implementation is based on these primary sources:

- [scikit-learn PLSRegression API](https://scikit-learn.org/stable/modules/generated/sklearn.cross_decomposition.PLSRegression.html)
- [scikit-learn cross-decomposition guide](https://scikit-learn.org/stable/modules/cross_decomposition.html)
- [scikit-learn common pitfalls and data leakage](https://scikit-learn.org/stable/common_pitfalls.html)
- [Minitab PLS model-selection table](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/regression/how-to/partial-least-squares/interpret-the-results/all-statistics-and-graphs/model-selection-table/)
- [Minitab PLS model-selection formulas](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/regression/how-to/partial-least-squares/methods-and-formulas/model-selection/)
- [Minitab PLS cross-validation](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/regression/supporting-topics/partial-least-squares-regression/cross-validation-in-pls-regression/)
- [Minitab PLS graphs](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/regression/how-to/partial-least-squares/interpret-the-results/all-statistics-and-graphs/graphs/)

The installed scikit-learn version is recorded in provenance and the manifest.
The implementation uses public `PLSRegression` attributes. It does not persist
a pickle or joblib object.

## 3. Input contract

Options use this canonical shape:

```json
{
  "response_column_id": "uuid",
  "predictor_column_ids": ["uuid", "uuid"],
  "missing_policy": "complete_case",
  "scale": true,
  "component_selection": "automatic_cv",
  "n_components": null,
  "max_components": 10,
  "cv": {
    "method": "k_fold",
    "folds": 5,
    "shuffle": true,
    "seed": 20260820
  },
  "max_iter": 500,
  "tol": 0.000001,
  "plot_point_limit": 2000
}
```

`component_selection` is `automatic_cv` or `fixed`. Fixed mode requires
`n_components`. K-fold supports 2 through 10 folds. Leave-one-out ignores
`folds`, `shuffle`, and `seed`. Grouped CV is a P1 extension point and is not
advertised as available in P0.

Limits:

- predictors: 2 through 100;
- usable rows: at least 4 and at most 20,000;
- evaluated components: at most
  `min(30, predictor_count, minimum_cv_training_rows)`;
- leave-one-out: at most 500 usable rows;
- plot points: 100 through 5,000.

The service rejects requests over a limit; it never silently samples rows.
Plot point limiting affects chart payload only and is recorded explicitly.

## 4. Missing values and validation

Rows with a missing, non-finite, or non-numeric selected value are excluded as
complete cases and reported in `n_total`, `n_used`, and `n_excluded`. The
response and every predictor must vary on the usable sample. The response may
not also be a predictor and predictor IDs must be unique.

Stable validation errors include:

- `pls_response_required`
- `pls_predictors_too_few`
- `pls_predictor_type_unsupported`
- `pls_response_type_unsupported`
- `pls_usable_rows_too_few`
- `pls_usable_rows_limit`
- `pls_constant_response`
- `pls_constant_predictor`
- `pls_component_count_invalid`
- `pls_cv_fold_count_invalid`
- `pls_leave_one_out_limit`
- `pls_model_fit_failed`
- `pls_model_not_converged`
- `pls_cross_validation_failed`
- `pls_model_manifest_checksum_mismatch`
- `pls_prediction_model_stale`

Errors do not include raw rows or absolute paths.

## 5. Scaling and leakage prevention

`scale=true` uses the sample standard deviation convention implemented by the
installed `PLSRegression`. Every cross-validation fold creates and fits a new
PLS estimator on that fold's training rows. Centering and scaling are therefore
learned from training rows only; validation rows are transformed only with that
fitted estimator. Scaling is never fitted on the full sample before CV.

The final model is fitted once on all usable rows after component selection.
The safe JSON manifest records predictor means, standard deviations, response
mean and standard deviation, coefficients, and an effective intercept for
point prediction without a serialized estimator.

## 6. Component selection and metrics

Candidates run from 1 through `max_components`. For each candidate the service
stores:

- cumulative X variance;
- training error SSE;
- training R-squared;
- PRESS from out-of-fold predictions;
- predicted R-squared `1 - PRESS / TSS_y`;
- CV RMSE `sqrt(PRESS / n_used)`;
- estimator iteration counts.

Automatic selection chooses the largest predicted R-squared. Values tied
within `1e-12` select the smaller component count. A consistency check confirms
that the same choice does not have greater PRESS when TSS is shared. Negative
predicted R-squared values remain negative; unlike some Minitab display tables,
they are not truncated to zero.

For fixed mode, the requested component count determines the final model. The
selection table is still calculated so training and CV performance remain
visible.

## 7. Cumulative X variance

For candidate `a`, the centered/scaled training matrix used by the estimator is
reconstructed from the first `a` public scores and loadings:

`X_hat_a = T_a P_a'`

`X variance_a = 1 - SSE(X_scaled - X_hat_a) / SST(X_scaled)`

The result records whether this is the standardized or centered scale. Tiny
floating-point excursions are tolerated only within `1e-12`; the statistic is
not changed merely for display parity.

## 8. Result schema 1

The result uses `summary_type = "partial_least_squares_regression"` and includes:

1. method and sample metadata;
2. component-selection table;
3. selected-model summary;
4. raw-scale and standardized coefficients;
5. observed, fitted, cross-validated fitted, and residual plot points;
6. public X/Y scores, weights, loadings, and rotations;
7. score and loading plot payloads;
8. stable warnings;
9. model manifest identity.

It never reports OLS coefficient p-values, t statistics, VIF, or ANOVA. Key
warnings include negative predicted R-squared, selection at the component
ceiling, a large training/CV performance gap, non-convergence, predictive-not-
causal limitations, and the absence of classical coefficient p-values.

## 9. Model persistence and prediction

PLS models use the existing regression-model catalog storage with
`method_id = "regression.partial_least_squares"`; no SQLite relation is added.
The manifest includes model/source identities, predictor order, selected
components, scaling metadata, prediction coefficients and effective intercept,
training ranges, loadings/rotations, model-selection metrics, package versions,
limitations, and a SHA-256 checksum held by metadata.

Point prediction accepts one or more rows keyed by predictor column ID. Every
row must be valid or the request fails. Values outside training ranges generate
warnings. P0 returns point estimates only and explicitly returns no mean or
individual prediction interval. OLS prediction behavior and manifests are not
changed.

## 10. Execution and compatibility

The current generic analysis-run infrastructure has no worker that executes
arbitrary analysis jobs. FastAPI synchronous routes already run outside the
async event loop, so P0 uses bounded inline execution with the limits above. It
is registered as `inline`, not falsely advertised as `job`. A later worker
contract can change the execution mode without changing statistical meaning.

Adding the method, model manifest, and point-prediction route increments the API
contract by one. Metadata schema 19 remains unchanged because the existing
generic regression-model record stores method identity and a manifest path.
Existing OLS results, manifests, predictions, IDs, versions, and checksums are
never rewritten.

## 11. Independent verification

Tests must include a hand-checkable one-component fixture, a collinear fixture,
a `p > n` fixture, deterministic CV/tie behavior, scaling on/off, and a static
external reference fixture produced outside the production implementation.
The committed fixture records tool/package version, inputs, expected
coefficients, intercept, scores, loadings, fitted/CV values, PRESS, predicted
R-squared, cumulative X variance, and prediction values with explicit
tolerances.
