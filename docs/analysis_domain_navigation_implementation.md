# Analysis Domain Navigation Implementation

## Scope and compatibility

This Phase 1 change adds a presentation taxonomy only. The six backend
`AnalysisModuleId` values, method IDs, routes, request and result schemas,
method versions, saved artifacts, checksums, restore behavior, and calculation
panels are unchanged. A leaf method still opens its existing route:

`/analysis/{legacy-module}/{method-id}`

The root `/analysis` route shows the eight-domain landing page. A selected
domain uses `/analysis?domain={domain-id}`. The query is presentation state and
does not enter an analysis request or saved result.

## Domain mapping

| Presentation domain | Family | Existing executable methods | Contextual or planned |
| --- | --- | --- | --- |
| Basic Statistics & Exploration | Distribution & Summary | `eda.descriptive`, `eda.graphical_summary`, `eda.normality` | none |
| Basic Statistics & Exploration | Multivariate Exploration | none | planned `eda.multivariate_review` |
| Mean Comparison & Equivalence | t-Tests | `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.two_sample_t` | Two-Sample Comparison guide |
| Mean Comparison & Equivalence | ANOVA | `hypothesis.one_way_anova` | ANOVA is a family, not a duplicate method |
| Mean Comparison & Equivalence | Equivalence Tests | `hypothesis.equivalence_tost`, `hypothesis.paired_equivalence_tost`, `hypothesis.two_sample_equivalence_tost` | none |
| Mean Comparison & Equivalence | Comparability Assessment | none | planned `hypothesis.comparability_assessment` |
| Mean Comparison & Equivalence | Nonparametric Tests | `hypothesis.one_sample_wilcoxon`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis` | none |
| Proportions & Categorical Data | Proportion Tests | `categorical.one_proportion`, `categorical.two_proportion` | none |
| Proportions & Categorical Data | Categorical Association | `categorical.chi_square_association` | none |
| Correlation, Regression & Prediction | Correlation | `regression.pearson`, `regression.xy_correlation` | none |
| Correlation, Regression & Prediction | Regression Models | `regression.linear_model` | none |
| Correlation, Regression & Prediction | Prediction & Optimization | none | contextual `regression.predict` and regression optimizer |
| Correlation, Regression & Prediction | Latent Variable Regression | none | planned `regression.partial_least_squares` |
| DOE & Optimization | Factorial Designs | `doe.factorial_design` | contextual `doe.general_factorial_design` inside the existing factorial workflow |
| DOE & Optimization | Response Surface Methods | `doe.response_surface` | none |
| DOE & Optimization | Response Optimization | `doe.response_optimizer` | none |
| AI/ML Experimental Design | Space-Filling Design | `doe.latin_hypercube` | none |
| AI/ML Experimental Design | Sequential Optimization | `doe.bayesian_optimization` | none |
| AI/ML Experimental Design | Surrogate Stage | none | Gaussian Process is shown as an internal surrogate, not another method |
| Quality & Process Monitoring | Control Charts | `quality.attribute_control_chart`, `quality.subgroup_chart`, `quality.individuals_chart` | none |
| Quality & Process Monitoring | Process Behavior | `quality.run_chart` | none |
| Quality & Process Monitoring | Process Capability | `quality.capability` | none |
| Quality & Process Monitoring | Multivariate Monitoring | none | planned `quality.multivariate_monitoring` |
| Measurement Systems & Variability | Variance Comparison | `eda.equal_variances` | planned Phase 2 `quality.two_variances` |
| Measurement Systems & Variability | Measurement System Analysis | `quality.gage_rr`, `quality.gage_run_chart` | none |

Every method exposed by `backend/app/analyses/registry.py` is mapped exactly
once, including contextual catalog methods. A backend unit test compares the
registry with the frontend source so a newly exposed method cannot disappear
from navigation silently.

## Existing option inventory and parity

The following representative vertical slices were inspected before moving the
entry points. Their existing panels remain the only owners of roles, defaults,
validation, requests, and results.

| Methods | Roles and variable selection retained | Options and defaults retained | Request, result, and lifecycle retained |
| --- | --- | --- | --- |
| `eda.descriptive`, `eda.graphical_summary`, `eda.normality` | numeric analysis columns | confidence/alpha, display and graph options | existing complete-case preflight, summaries, charts, warnings, history, restore, compare, export |
| `eda.equal_variances` | response and group | alpha and stored equal-variance procedures | existing multiple-comparison and Brown-Forsythe result, interval chart, warnings, history and export |
| `hypothesis.two_sample_t` | response and two-level group | Welch default, alternative, alpha, confidence | exact existing payload and estimate/CI/effect/p-value sections |
| `hypothesis.one_way_anova` | response and group | ANOVA variant, post-hoc and multiplicity policies | exact existing preflight, omnibus/post-hoc result and restore |
| `hypothesis.two_sample_equivalence_tost` | response and group | lower/upper equivalence limits, alpha | exact TOST request, CIs, decision, warnings and export |
| `categorical.chi_square_association` | row and column categories | alpha | expected-count checks, association result, sparse-table guidance and lifecycle |
| `regression.linear_model` | response, numeric/categorical predictors and terms | confidence, hierarchy, backward-elimination controls | existing OLS request, equation, ANOVA, diagnostics, saved model, prediction and optimizer contextual actions |
| `quality.individuals_chart` | response and order | active phase/rules and baseline controls | existing chart request, limits, signals, revisions, warnings and restore |
| `quality.gage_rr` | response, part, operator, replicate | crossed-study options and preflight | existing dedicated Gage request, variance components, charts, warnings and source lifecycle |
| `doe.factorial_design` | factors, bounds/levels and response revision | design type, replicate, center, block, seed and randomization | existing factorial/general-factorial subworkflow, design/result schemas and checksum behavior |
| `doe.latin_hypercube` | factor domains | runs, seed, optimization and executable resolution | existing design payload, quality metrics, plots, response revision, restore and CSV |
| `doe.response_surface`, `doe.response_optimizer` | factor domains and saved RSM source | design family, alpha, goal and bounds | existing design/fit/optimizer contracts, charts, warnings and persistence |
| `doe.bayesian_optimization` | factor domains, objective and constraints | initial design, acquisition/exploration, seed and budgets | existing Study lifecycle, atomic observations, recommendations, uncertainty and CSV |

No Phase 1 source changes were made to the panel callback wiring in
`App.tsx`/`AnalysisShell.tsx`, API client payload builders, backend schemas, or
statistical services. Existing frontend tests continue to assert representative
request bodies and result sections after the navigation change.

## Deliberately not added

- ANOVA remains a family containing One-Way ANOVA; there is no duplicate ANOVA leaf.
- Two-Sample Comparison is guidance across existing methods, not a calculation.
- Gaussian Process remains Bayesian Optimization surrogate information.
- Comparability Assessment is planned because it must coordinate multiple CQAs and tests.
- PLS Regression and PLS-Based Monitoring are not presented as available.
- Two Variances, multivariate review, PLS, comparability, and multivariate monitoring require their own later statistical contracts and PRs.

## Version and migration decision

- API contract: unchanged.
- Statistical method versions: unchanged.
- Result schemas: unchanged.
- Metadata schema: unchanged.
- SQLite migration: none.
- Existing saved artifacts and checksums: not rewritten.
