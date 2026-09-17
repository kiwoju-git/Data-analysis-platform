# HTML Report Coverage Matrix

HTML report artifact schema 3 is generated only from the stored result envelope. It records
the requested `en` or `ko` report locale and does not
rerun analyses or read raw dataset rows. All user-provided text is escaped and all graphics are
self-contained inline SVG without scripts or external resources.

| Result family | User summary | Tables | Inline SVG | Stored payload source | Notes |
| --- | --- | --- | --- | --- | --- |
| Descriptive statistics | Yes | Column statistics | No | `result.columns` | HF6 method is shown for schema 2 |
| Graphical Summary | Yes | Distribution/statistics/CI | Histogram normal fit, boxplot, Q-Q, CI plot, ECDF | `result.columns` | Full graph coverage required |
| Normality | Summary | Test summary | No | Stored test payload | Diagnostic graph gap |
| Equal variances | Yes | Multiple comparisons, Levene, groups | Comparison intervals | Stored schema 2 payload | Schema 1 keeps legacy rows |
| Hypothesis methods | Summary | Estimates, intervals, tests/effects | No | Stored result payload | Limits below |
| Categorical methods | Summary | Counts/tests/effects | No | Stored result payload | Limits below |
| Regression | Method-specific | Separate OLS/regularized/PLS/GP tables | Method-specific | Stored result payload | Do not conflate coverage |
| Quality methods | Summary | Chart/capability/gage summaries | No | Stored result payload | Chart gaps below |
| Unknown future result | No complete HTML | None | No | JSON envelope export only | Unsupported schema/method returns a stable error |

The large path/value Result Envelope table from artifact schema 1 is removed from the default
body. A closed `details` element may expose escaped pretty JSON for audit use, after all
user-facing sections.

## Method-Level Audit (2026-09-17)

The older family table above describes intent, not full UI parity. In particular,
OLS and most hypothesis/categorical/quality renderers only emit summaries/tables,
not all interactive graphics. These now visibly identify themselves as **summary
reports** in both languages. PLS was completely missing from actual dispatch;
its dedicated renderer is added in this release. GPR gains stored settings,
optimizer evidence, OOF/residual/uncertainty/profile SVGs and a surface table.

Audit source: 37-method backend registry, eight frontend domains and actual export
routes. Every generic entry includes provenance and saved warnings. Schema below
is the current result schema; legacy accepted versions are explicit in
`report_coverage.py`. Status `supported` does not claim every option was visually
checked. `summary` means partial screen parity, not a complete user report.

Renderer shorthand: E = named EDA renderer in `analysis_run_exports.py`, H =
`_hypothesis_report_section`, C = `_categorical_report_section`, R =
`_regression_report_section`, Q = `_quality_report_section`.

| Domain | Method ID / version | summary_type / schema | Actual renderer and core | Status / gaps | Fixture/test |
| --- | --- | --- | --- | --- | --- |
| Basic | eda.descriptive 0.2.0 | descriptive_statistics / 2 | E: column statistics | supported; quick chart is not a stored report | API EDA exports |
| Basic | eda.graphical_summary 0.2.0 | graphical_summary / 2 | E v2: stats/CI, histogram, box, Q-Q, ECDF | supported | API + E2E |
| Basic | eda.normality 0.2.0 | normality_test / 2 | E: per-column tests | summary; diagnostic plots absent | API EDA exports |
| Basic | eda.principal_components 0.1.0 | principal_components_analysis / 1 | PCA eigenanalysis/loadings and 5 SVG views | supported; bounded saved points | PCA API/report |
| Means | hypothesis.one_sample_t 0.1.0 | one_sample_t_test / 1 | H: estimates/test/CI | summary; plots absent | API hypothesis exports |
| Means | hypothesis.paired_t 0.1.0 | paired_t_test / 1 | H: difference/test | summary; plots absent | API hypothesis exports |
| Means | hypothesis.two_sample_t 0.1.0 | two_sample_t_test / 1 | H: groups/difference/test | summary | API hypothesis exports |
| Means | hypothesis.one_way_anova 0.2.0 | one_way_anova / 2 | H: groups/test/post-hoc | summary; plots absent | API hypothesis exports |
| Means | hypothesis.equivalence_tost 0.2.0 | equivalence_tost / 2 | H: bounds/TOST | summary | API hypothesis exports |
| Means | hypothesis.two_sample_equivalence_tost 0.1.0 | equivalence_tost / 2 | H: groups/bounds/TOST | summary; every mode not visually checked | dispatch + method tests |
| Means | hypothesis.paired_equivalence_tost 0.1.0 | equivalence_tost / 2 | H: paired TOST | summary; every mode not visually checked | dispatch + method tests |
| Means | hypothesis.one_sample_wilcoxon 0.1.0 | one_sample_wilcoxon_signed_rank_test / 1 | H: rank/test | summary | API hypothesis exports |
| Means | hypothesis.mann_whitney 0.2.0 | mann_whitney_u_test / 2 | H: groups/rank/test | summary | API hypothesis exports |
| Means | hypothesis.kruskal_wallis 0.1.0 | kruskal_wallis_test / 1 | H: groups/test/post-hoc | summary | API hypothesis exports |
| Categorical | categorical.one_proportion 0.1.0 | one_proportion_test / 1 | C: counts/proportion/test | summary | API categorical exports |
| Categorical | categorical.two_proportion 0.1.0 | two_proportion_test / 1 | C: groups/difference/test | summary | API categorical exports |
| Categorical | categorical.chi_square_association 0.1.0 | chi_square_association / 1 | C: contingency/test/effects | summary; mosaic absent | API categorical exports |
| Regression | regression.pearson 0.1.0 | pearson_correlation / 1 | R: correlation/CI/test | summary; scatter absent | API regression exports |
| Regression | regression.xy_correlation 0.1.0 | xy_correlation_matrix / 1 | R: pair table | summary; heatmap absent | API regression exports |
| Regression | regression.linear_model 0.3.0 OLS | linear_model / 6 | R: fit/coefficient tables | summary; full ANOVA/selection/diagnostic UI absent | API + OLS tests |
| Regression | regression.linear_model 0.3.0 Ridge/Lasso/EN | linear_model / 6 | regularized_model_report: tuning/CV/coefs/path | summary; no OLS inference | regularized API/report |
| Regression | regression.partial_least_squares 0.1.0 | partial_least_squares_regression / 1 | pls_regression_report: settings/components/coefs/response/score/all loadings/residuals | fixed; all saved points, no invented inference | test_pls_report + E2E |
| Regression | regression.gaussian_process 0.3.0 | gaussian_process_regression / 3 | GP renderer + gaussian_process_report | fixed; surface table, not heatmap | GP API/reference + E2E |
| Regression contextual | regression.predict 0.3.0 | dedicated prediction / 3 | own CSV/restore | unsupported HTML | prediction API/E2E |
| DOE | doe.factorial_design 0.9.0 | factorial analysis / 3 | factorial_analysis_report | supported; separate legacy design report | factorial exports/E2E |
| DOE | doe.general_factorial_design 0.4.0 | general factorial analysis / 3 | dedicated workflow renderer | supported; cube inapplicable | factorial exports/E2E |
| DOE | doe.response_surface 0.3.0 | dedicated RSM | own workflow | unsupported HTML | capability tests |
| DOE contextual | doe.response_optimizer 0.4.0 | dedicated optimizer | own workflow | unsupported HTML | capability tests |
| AI/ML | doe.latin_hypercube 0.3.0 | dedicated LHS | design CSV | unsupported HTML | LHS API/E2E |
| AI/ML | doe.bayesian_optimization 0.6.0 | dedicated study/recommendation | study/initial-design export | unsupported HTML | BO API/reference/E2E |
| Quality | quality.attribute_control_chart 0.3.0 | attribute_control_chart / 3 | Q: chart summaries/signals | summary; chart SVG absent | API quality exports |
| Quality | quality.subgroup_chart 0.1.0 | subgroup_chart / 1 | Q: Xbar/R/S summaries | summary | API quality exports |
| Quality | quality.individuals_chart 0.1.0 | individuals_chart / 1 | Q: I/MR summaries | summary | API quality exports |
| Quality | quality.run_chart 0.2.0 | run_chart / 2 | Q: runs/tests | summary | API quality exports |
| Quality | quality.capability 0.1.0 | capability_analysis / 1 | Q: capability/nonconformance | summary; histogram absent | API capability/gage exports |
| Measurement | eda.equal_variances 0.2.0 | equal_variances_test / 2 | E v2: tests/groups/interval SVG | supported | API + E2E |
| Measurement | quality.gage_rr 0.1.0 | gage_rr / 1 | Q: variance components | summary; full ANOVA/interaction views absent | API capability/gage exports |
| Measurement | quality.gage_run_chart 0.1.0 | gage_run_chart / 1 | Q: design/run summary | summary | API capability/gage exports |

Planned Comparability, multivariate monitoring and two-variance items are not
executable and have no report. BO's surrogate is contextual, not a second GP.
The contextual regression optimizer retains its own non-HTML workflow.

### PLS Screen Correspondence

`method`/`sample`: inputs/settings/exclusions. `component_selection.rows`: all
selection rows and marked curve. `model_summary`: selected summary.
`coefficients`: original and standardized coefficients. `diagnostics.points`:
training/OOF/residual SVG and all saved diagnostic rows. `latent_components`:
score plot/table and every saved loading/weight/rotation component, not only the
UI-selected loading. One-component scores use observation order versus component
1, never an invented component 2. Stored/total/point-limit counts are explicit;
the frontend's first-100 preview does not restrict HTML.

PLS point predictions are separate stateless responses, not in the analysis
envelope. Completed predictions now download a separate JSON snapshot with source
analysis ID, model ID/SHA, exact request/response and client receipt time. This is
explicitly not a managed Report Center artifact. Editing rows/source invalidates
the snapshot and late requests are ignored. No original result is overwritten.

### Automated Evidence and Limits

`test_report_coverage.py` checks all 30 inline methods against explicit contracts
and actual dispatch, mismatched/unknown schemas and empty-payload rejection.
Dispatch mocks verify registration, not numerical/visual parity.
`test_api_contracts.py -k html_report` exercises synthetic stored method-family
exports. `test_pls_report.py` checks body tables/SVGs/values, one/multiple components,
escaping, >100 stored points, locales, no refit/source access and SHA invariance.
See `gpr_ui_report_parity_validation.md` for commands actually run.
Every historical schema and every option combination has not been visually checked.
