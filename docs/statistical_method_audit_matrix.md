# Statistical Method Audit Matrix

This matrix records the current implementation and QA state for the 29 stable method IDs in the six-module registry. It is an audit artifact, not a plan to make planned/disabled methods executable in this PR.

Legend: Y = covered or present, N = not present, Partial = intentionally limited coverage, N/A = not applicable because the method is not executable through that path.

| method_id | status/path | module | frontend panel | reference fixture | hand unit test | API integration | edge/failure tests | effect size / interval | CI | assumptions / warning codes | provenance | known limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `eda.descriptive` | available, generic analysis-run | exploration | `DescriptiveAnalysisPanel` | N | Y | Y | Y | N/A descriptive summary | Y | Y | Y | Numeric columns only; no inferential p-values. |
| `eda.graphical_summary` | available, generic analysis-run | exploration | `GraphicalSummaryPanel` | N | Y | Y | Y | N/A chart-data summary | Y | Y | Y | Inline chart data/UI only; no exported chart artifact. |
| `eda.normality` | available, generic analysis-run | exploration | `NormalityAnalysisPanel` | Y | Y | Y | Y | N/A diagnostic tests | Y | Y | Y | Does not automatically select downstream parametric/nonparametric methods. |
| `eda.equal_variances` | available, generic analysis-run | exploration | `EqualVariancesPanel` | Y | Y | Y | Y | N/A diagnostic tests | Y | Y | Y | Diagnostic only; does not auto-switch pooled/Welch downstream analyses. |
| `hypothesis.one_sample_t` | available, generic analysis-run | hypothesis | `OneSampleTPanel` | Y | Y | Y | Y | Y | Y | Y | Y | One-sample mean only; independence remains a design assumption. |
| `hypothesis.paired_t` | available, generic analysis-run | hypothesis | `PairedTPanel` | Y | Y | Y | Y | Y | Y | Y | Y | Wide before/after columns only; pairing keys are not implemented. |
| `hypothesis.two_sample_t` | available, generic analysis-run | hypothesis | `TwoSampleTPanel` | Y | Y | Y | Y | Y | Y | Y | Y | Defaults to Welch; pooled Student requires explicit option. |
| `hypothesis.one_way_anova` | available, generic analysis-run | hypothesis | `OneWayAnovaPanel` | Y | Y | Y | Y | Y | Y | Y | Y | Standard one-way ANOVA only; Welch ANOVA/Games-Howell are not implemented. |
| `hypothesis.equivalence_tost` | available, generic analysis-run | hypothesis | `EquivalenceTostPanel` | Y | Y | Y | Y | Y | Y | Y | Y | One-sample raw-unit TOST only; paired/two-sample TOST are not implemented. |
| `hypothesis.one_sample_wilcoxon` | available, generic analysis-run | hypothesis | `OneSampleWilcoxonPanel` | Y | Y | Y | Y | Y | Y | Y | Y | One-sample signed-rank only; not labeled as a median-difference test. |
| `hypothesis.mann_whitney` | available, generic analysis-run | hypothesis | `MannWhitneyPanel` | Y | Y | Y | Y | Y | Y | Y | Y | Two independent groups only; not a median-only interpretation. |
| `hypothesis.kruskal_wallis` | available, generic analysis-run | hypothesis | `KruskalWallisPanel` | Y | Y | Y | Y | Y | Y | Y | Y | Dunn/Holm post-hoc only after significant omnibus result. |
| `categorical.one_proportion` | available, generic analysis-run | categorical | `OneProportionPanel` | Y | Y | Y | Y | Y | Y | Y | Y | Binary response column only; aggregate event/trial input is not implemented. |
| `categorical.two_proportion` | available, generic analysis-run | categorical | `TwoProportionPanel` | Y | Y | Y | Y | Y | Y | Y | Y | Binary response plus exactly two groups; zero-cell RR/OR CI is intentionally unavailable. |
| `categorical.chi_square_association` | available, generic analysis-run | categorical | `ChiSquareAssociationPanel` | Y | Y | Y | Y | Y | Y | Y | Y | Pearson chi-square only; sparse 2x2 recommends Fisher exact but does not switch. |
| `regression.pearson` | available, generic analysis-run | regression | `PearsonCorrelationPanel` | Y | Y | Y | Y | Y | Y | Y | Y | Pairwise Pearson correlation only; correlation is not causation. |
| `regression.xy_correlation` | available, generic analysis-run | regression | `XyCorrelationPanel` | Y | Y | Y | Y | Y | Y | Y | Y | Matrix of Pearson correlations only; no partial correlation. |
| `regression.linear_model` | available, generic analysis-run | regression | `LinearModelPanel` | Y | Y | Y | Y | Y | Y | Y | Y | OLS main effects plus selected numeric quadratic/interactions; robust covariance and categorical interactions are not implemented. |
| `regression.predict` | disabled in registry; dedicated regression-model API is implemented | regression | `LinearModelPanel` prediction flow | Partial | Partial | Y | Y | Y | Y | Y | Partial | Not executable through `POST /analysis-runs`; prediction uses stored model endpoints and checksum-validated app-created manifests. |
| `regression.response_optimizer` | disabled | regression | guidance only | N | N | N/A | N | N | Y | N/A | N/A | Requires validated regression or DOE response-surface model; no optimizer result is generated. |
| `quality.attribute_control_chart` | planned | quality | guidance only | N | N | N/A | N | N | Y | N/A | N/A | Not implemented; no fake attribute-control chart payload. |
| `quality.individuals_chart` | available, generic analysis-run | quality | `IndividualsChartPanel` | Y | Y | Y | Y | N/A chart diagnostic | Y | Y | Y | I/MR-style variables chart only; no chart export artifact. |
| `quality.subgroup_chart` | available, generic analysis-run | quality | `SubgroupChartPanel` | Y | Y | Y | Y | N/A chart diagnostic | Y | Y | Y | Xbar/R and Xbar/S style summaries only; no export artifact. |
| `quality.run_chart` | available, generic analysis-run | quality | `RunChartPanel` | Y | Y | Y | Y | N/A chart diagnostic | Y | Y | Y | Run-chart rules only; no control limits or process capability conclusion. |
| `quality.capability` | available, generic analysis-run | quality | `CapabilityPanel` | N | Y | Y | Y | Y | Y | Y | Y | Normal capability only; non-normal capability and CI for indices remain out of scope. |
| `quality.gage_rr` | available, generic analysis-run | quality | `GageRrPreflightPanel` | N | Y | Y | Y | Y | Y | Y | Y | Balanced crossed ANOVA only; advanced/pooling variants and component plots are not implemented. |
| `quality.gage_run_chart` | available, generic analysis-run | quality | `GageRunChartPanel` | N | Y | Y | Y | N/A chart diagnostic | Y | Y | Y | Diagnostic chart payload only; does not replace Gage R&R variance components. |
| `doe.factorial_design` | available through dedicated DOE design API | doe | `FactorialDesignPanel` | N | Y | Y | Y | N/A design asset | Y | Y | Partial | Dedicated `doe-designs` routes create design and response entries; generic analysis-run returns `analysis_method_uses_dedicated_api`. Effects/OLS/ANOVA are not implemented. |
| `doe.response_surface` | planned | doe | guidance only | N | N | N/A | N | N | Y | N/A | N/A | RSM design/modeling is not implemented; no fake response-surface result. |

## Current Audit Notes

- Generic analysis-run results now include runtime/build provenance fields: `python_version`, `platform`, `build_commit`, and `package_versions`; these fields are built through a shared analysis-run provenance helper.
- EDA, categorical, hypothesis, quality, and simple generic regression analysis-run methods now persist successful result envelopes through the shared `store_succeeded_analysis_result` helper, including result checksum calculation and result-file cleanup if metadata insertion fails. `regression.linear_model` uses a regression-specific manifest-aware persistence wrapper for the result envelope plus `regression_model_manifest` artifact.
- API contract tests now check that result-only runner modules do not regain direct low-level metadata insert or file-write primitives, and that `regression.linear_model` remains on the manifest-aware persistence boundary.
- `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, `eda.equal_variances`, all eight hypothesis methods, all three categorical methods, the three generic regression analysis-run methods, and all six current quality analysis-run methods now execute through the `MethodExecutionHandler` registry foundation. Handler metadata and missing-runner validation are centralized in `services/analysis_method_handlers.py`; the four EDA runners are split into `services/analysis_runners_eda.py`; the eight hypothesis runners are split into `services/analysis_runners_hypothesis.py`; the three categorical runners are split into `services/analysis_runners_categorical.py`; the three generic regression runners, including `regression.linear_model` plus its safe JSON model-manifest persistence, are split into `services/analysis_runners_regression.py`; and the six current quality runners are split into `services/analysis_runners_quality.py`.
- `build_commit` is read from `DATALAB_GIT_COMMIT` when set; otherwise it may be null.
- `regression.predict` is intentionally disabled in the generic registry because it depends on an app-created stored model. Its working execution path is the dedicated regression-model prediction API.
- `doe.factorial_design` is registry-available but uses dedicated DOE design routes, not the generic analysis-run endpoint.
- Methods marked planned/disabled must continue to reject without result envelopes or mock statistics.
- The highest-risk statistical regression tests currently emphasize ANOVA post-hoc/effect sizes, TOST one-sided logic, zero-cell categorical effects, expected-count diagnostics, OLS singular/rank cases, capability zero-sigma/one-sided specs, and balanced crossed Gage R&R assumptions.
