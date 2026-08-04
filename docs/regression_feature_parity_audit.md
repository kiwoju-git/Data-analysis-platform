# Regression Feature Parity Audit

## Purpose And Scope

This audit compares the current `regression.linear_model` and
`regression.predict` implementation with the regression workflow documented by
Minitab and with primary statistical references. It is a scope and correctness
review, not a commitment to copy every Minitab option.

Audit date: 2026-08-04  
Baseline commit: `33d2a7d2f49b3732c4dc6e00cde96109bafff243`  
Pinned implementation: NumPy/SciPy OLS, CPU-only, Python 3.10, local workspace

Priority definitions:

- **P0**: omission can change whether a valid model can be fit, materially
  weakens interpretation, or blocks the requested end-to-end workflow.
- **P1**: useful extension that is separable from this workflow.
- **Deferred**: outside the current OLS/product/dependency boundary.

## Official Sources

1. [Minitab model summary: S, R-sq, PRESS, predicted R-sq, AICc, BIC, and Mallows' Cp](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/regression/how-to/fit-regression-model/interpret-the-results/all-statistics-and-graphs/model-summary-table/)
2. [Minitab coefficients and VIF](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/regression/how-to/fit-regression-model/interpret-the-results/all-statistics-and-graphs/coefficients-table/)
3. [Minitab regression ANOVA and lack-of-fit](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/regression/how-to/fit-regression-model/interpret-the-results/all-statistics-and-graphs/analysis-of-variance-table/)
4. [Minitab diagnostic measures](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/regression/how-to/fit-regression-model/methods-and-formulas/diagnostic-measures/)
5. [Minitab residual plots and four-in-one display](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/regression/how-to/fit-regression-model/perform-the-analysis/select-the-graphs-to-display/)
6. [Minitab stepwise and backward elimination](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/regression/how-to/fit-regression-model/perform-the-analysis/perform-stepwise-regression/)
7. [Minitab hierarchy and model-selection overview](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/regression/supporting-topics/basics/using-stepwise-regression-and-best-subsets-regression/)
8. [Minitab Response Optimizer output and optimization plot](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/using-fitted-models/how-to/response-optimizer/interpret-the-results/all-statistics-and-graphs/)
9. [Minitab prediction output](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/using-fitted-models/how-to/predict/interpret-the-results/key-results/)
10. [Minitab confidence and prediction interval distinction](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/using-fitted-models/supporting-topics/prediction/confidence-intervals-for-prediction/)
11. [NIST/SEMATECH model validation and residual analysis](https://www.itl.nist.gov/div898/handbook/pmd/section4/pmd44.htm)
12. [NIST/SEMATECH lack-of-fit and replicate requirement](https://www.itl.nist.gov/div898/handbook/pmd/section4/pmd446.htm)
13. [SciPy F distribution](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.stats.f.html)
14. [NumPy least-squares solver](https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html)

Minitab is the product-parity reference. NIST, SciPy, and NumPy are used for
the statistical and numerical implementation boundary. No blog or search-result
summary is used as an implementation authority.

## Current Capability Audit

| Feature | Current support | Minitab/reference capability | Current code | Statistical importance | Priority | This change | Version/schema impact | Official basis |
|---|---|---|---|---|---|---|---|---|
| Numeric versus categorical predictor classification | Incorrect when `role=factor`; numeric continuous/count columns can be rejected or treatment-coded | Storage type and modeling role are separate; categorical predictors are explicitly identified | `statistics/linear_model.py`, `services/analysis_runners_regression.py`, `services/regression_models.py`, `LinearModelPanel.tsx` | Can change the design matrix and make a valid fit fail | P0 | Yes: shared data-type/measurement-level rule; role is descriptive only | Method behavior fix; result schema 5 and manifest 3 for new writes | Minitab coefficients; NumPy least squares |
| Numeric linear main effects | Supported | Supported | `statistics/linear_model.py` | Core OLS | P0 | Preserve and regression-test | No semantic change | NumPy least squares |
| Categorical main effects | Supported with deterministic treatment coding and sorted reference | Supported with explicit categorical coding | `statistics/linear_model.py` | Correct design matrix and interpretation | P0 | Preserve; expose reference/coding more clearly | Manifest 3 retains coding metadata | Minitab coefficients |
| Numeric quadratic terms | Supported when explicitly selected | Supported model term | `statistics/linear_model.py`, `LinearModelPanel.tsx` | Curvature and optimizer interior solutions | P0 | Preserve through selection, equation, ANOVA, prediction, optimizer | Result 5/manifest 3 | Minitab ANOVA |
| Numeric-by-numeric interactions | Supported when explicitly selected | Supported model term | Same as above | Conditional effects and hierarchy | P0 | Preserve; enforce strong hierarchy during removal | Result 5/manifest 3 | Minitab hierarchy guidance |
| Categorical or factor-by-numeric interactions | Not supported | Supported by general regression tools | Term builder deliberately limits interactions | Important for some studies but separable and materially expands coding/hierarchy | P1 | No | None | Minitab ANOVA |
| Regression equation | Coefficients exist; no structured equation/result section | Equation is a primary fitted-model output | Coefficients and `model_specification` only | Required to verify model meaning and reuse | P0 | Yes: structured equation plus derived display text | Result 5/manifest 3 | Minitab prediction output and coefficients |
| Coefficient table | Supported: estimate, SE, t, p, CI, VIF | Supported | `statistics/linear_model.py`, `LinearModelPanel.tsx` | Core inference | P0 | Preserve and reorder around final selected model | Result 5 adds no incompatible coefficient meaning | Minitab coefficients |
| VIF | Supported per design column; `max_vif` and condition warning exist | Supported per coefficient; high values are diagnostic, not an automatic deletion rule | `_vif_values`, diagnostics | Multicollinearity sensitivity | P0 | Reuse; promote max VIF in model summary; keep intercept as unavailable | No new calculation version by itself | Minitab coefficients and diagnostic measures |
| Generalized VIF for categorical term blocks | Not supported | Some software provides term-level diagnostics | No implementation | Useful for multi-df categorical terms | P1 | No; document level-column VIF limitation | None | Minitab coefficients |
| Condition number | Supported | Complementary conditioning diagnostic | `statistics/linear_model.py` | Numerical stability | P0 | Preserve in summary/technical explanation | None | NumPy linear algebra |
| R-squared and adjusted R-squared | Supported | Supported | `fit` result | Fit summary | P0 | Preserve | None | Minitab model summary |
| PRESS | Not supported | Standard leave-one-out deleted-residual summary | Leverage/residuals already computed | Detects poor predictive performance and overfit | P0 | Yes, from all used rows, never capped points | Result 5/manifest 3 | Minitab model summary |
| Predicted R-squared | Not supported | `1 - PRESS/TSS`; Minitab UI may clamp negative values to zero | No implementation | Required predictive diagnostic | P0 | Yes; preserve valid negative values instead of hiding them | Result 5/manifest 3 | Minitab model summary |
| Model ANOVA | Only overall F statistics in `fit` | Regression, term, error, total; adjusted SS independent of term order | No table payload | Needed to distinguish overall and term tests | P0 | Yes: reduced-model partial adjusted SS by term block | Result 5 | Minitab ANOVA; SciPy F |
| Pure error and lack-of-fit | Not supported | Available only with replicated predictor settings and estimable lack-of-fit DF | No implementation | Separates replicate error from model-form lack of fit | P0 | Yes when mathematically available; otherwise typed unavailable reason | Result 5 | Minitab ANOVA; NIST lack-of-fit |
| Residual summaries, leverage, Cook's D | Supported on all rows; UI scatter points capped at 500 | Supported diagnostic measures | `_diagnostics_payload`, interactive diagnostic charts | Model adequacy and influential observations | P0 | Preserve; add structured unusual-observation candidates | Result 5 extends payload | Minitab diagnostic measures; NIST validation |
| Four-in-one residual plots | Observed/fitted, residual/fitted, leverage/Cook exist; no Q-Q, histogram, order plot, or 4-in-1 toggle | Normal probability, histogram, residuals versus fits, residuals versus order | `LinearModelPanel.tsx`, chart primitives | Required visual assumption review | P0 | Yes, raw and standardized payloads; histogram uses all rows | Result 5 residual-plots payload | Minitab residual plots; NIST validation |
| Backward elimination | Not supported | Starts at full candidate model; removes least significant eligible term subject to hierarchy and alpha-to-remove | No implementation | Requested exploratory model reduction | P0 | Yes: partial-F term-block removal, stable tie policy, strong hierarchy | Request contract, result 5, manifest 3, method 0.2.0 | Minitab stepwise/hierarchy |
| Forward/stepwise/best subsets | Not supported | Supported | No implementation | Useful alternatives but separate validation scope | P1 | No | None | Minitab stepwise overview |
| Mallows' Cp | Not supported | Full-model MSE comparison across subsets | No implementation | Useful trace diagnostic for backward steps | P0 for requested trace | Yes per step, anchored to initial full model MSE | Result 5 | Minitab model summary |
| AIC/AICc/BIC | Not supported | AICc/BIC supported for comparing models | No implementation | Useful step trace, not sole truth | P0 for trace metadata | Yes AICc/BIC per step with one documented Gaussian likelihood convention | Result 5 | Minitab model summary |
| General regression Response Optimizer | Only DOE/RSM optimizer exists | Stored regression models can drive bounded desirability optimization | `statistics/response_optimizer.py` is RSM-oriented; no OLS adapter | Requested follow-on workflow | P0 | Yes, contextual to stored general OLS model; DOE optimizer unchanged | New dedicated config/result contract; storage decision after dependency review | Minitab Response Optimizer |
| Predictor profile | Not supported for general OLS | Optimization plot varies one predictor while fixing others | No implementation | Explains a conditional model slice | P0 | Yes for numeric curves and categorical level table/points | Optimizer result contract | Minitab optimizer output |
| Dataset-version prediction | Supported with server preflight, CI/PI, persistence, paging, CSV | Supported | `services/regression_models.py`, `RegressionPredictionPanel.tsx` | Existing validated workflow | P0 | Preserve | Legacy prediction readers remain | Minitab prediction and interval docs |
| Direct/pasted prediction | Not supported | New predictor settings can be entered for prediction | Explicitly out of prior contract | Requested workflow without catalog pollution | P0 | Yes: bounded server parse/preflight, content hash, explicit mappings | `regression.predict` 0.3.0 and input/config/result extension; storage decision after schema review | Minitab prediction output |
| Prediction confidence and prediction intervals | Supported from stored OLS basis | Supported and semantically distinct | `services/regression_models.py` | Required uncertainty | P0 | Preserve for both dataset and pasted inputs | Manifest 3 remains capable; legacy manifest 2 read retained | Minitab interval distinction |
| Categorical predictor prediction | Supported for known levels; unseen levels blocked | Supported | Prediction manifest and preflight | Correct coding and safe reuse | P0 | Preserve, including pasted input | Manifest 3 retains levels | Minitab coefficients/prediction |
| Model/result restore | Result schema 4, manifest 2, prediction result 2/config 3/rows 2 | Product-specific | Result/manifest consistency services | Reproducibility and checksum compatibility | P0 | Keep all legacy readers; never rewrite stored checksums | New writes only use newer schemas | Existing project contracts |

## P0 Decisions For This Change

The implementation will:

1. classify predictor representation from `data_type` and
   `measurement_level`, never from `role=factor`;
2. keep existing OLS, explicit quadratic terms, numeric interactions,
   treatment coding, VIF, condition number, and dataset prediction behavior;
3. add a structured equation, PRESS, un-clamped predicted R-squared, adjusted
   partial-SS ANOVA, and replicate-only pure-error/lack-of-fit output;
4. add deterministic backward elimination by term block with strong hierarchy,
   alpha-to-remove, Mallows' Cp, AICc, BIC, and an explicit exploratory warning;
5. add a result-backed interactive four-in-one residual view without refitting;
6. add bounded single-response optimization from the final stored OLS model and
   conditional predictor profiles, while retaining the DOE/RSM optimizer;
7. move prediction after fit diagnostics and add bounded pasted-table
   preflight/execution without creating a dataset version.

Minitab displays zero for some negative predicted R-squared results. Statistical
Twin intentionally retains a finite negative value because it is valid and
communicates that leave-one-out prediction can be worse than predicting the
training response mean.

## P1 And Deferred Scope

P1 follow-ups:

- factor-by-numeric and categorical interactions;
- forward selection, bidirectional stepwise, and best subsets;
- categorical term-level generalized VIF;
- deleted/externally studentized residual plots and DFITS;
- weighted least squares, HC3 covariance, and Durbin-Watson controls;
- multi-response general-regression desirability;
- paste inputs without headers when multiple predictors are present, unless an
  explicit mapping can be provided without ambiguity.

Deferred from the current OLS contract:

- arbitrary formulas or executable expressions;
- automatic transformation selection, Box-Cox, nonlinear regression;
- LASSO, ridge, Elastic Net, PLS, and robust regression;
- external pickle/joblib model import;
- optimization outside the fitted training domain without a separately
  versioned extrapolation policy and explicit acknowledgment.

## Compatibility And Version Decision

The requested change alters calculation and persisted result meaning, so new
writes require:

- `regression.linear_model` method `0.2.0`;
- linear-model result schema `5`;
- regression model manifest schema `3`;
- `regression.predict` method `0.3.0` if pasted-input persistence shares the
  existing prediction method;
- an API contract bump from `8` to `9` when the typed wire contract lands.

Readers for `regression.linear_model` `0.1.0`, result schema `4`, manifest
schema `2`, and existing `regression.predict` artifacts remain unchanged.
Whether SQLite needs a migration is deliberately not decided by this audit: it
depends on whether current owned-artifact relations can represent pasted input
snapshots and general-regression optimization without nullable/foreign-key
violations. A JSON result extension alone is not a reason to migrate metadata.

## Statistical And Product Guardrails

- Stepwise selection is exploratory; final p-values and confidence intervals
  are not presented as if the model had been fixed before looking at the data.
- PRESS uses every complete-case fit row and is independent of chart point caps.
- Lack-of-fit is unavailable without replicated predictor settings and usable
  pure-error/lack-of-fit degrees of freedom.
- Optimization evaluates the stored final equation inside recorded training
  ranges, uses only known categorical levels, and does not imply causality or a
  guaranteed global optimum.
- Pasted values are parsed and validated on the server, are never evaluated as
  code, do not create dataset versions, and are not logged or echoed in errors.
