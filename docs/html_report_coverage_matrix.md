# HTML Report Coverage Matrix

Current method/version, canonical navigation, execution prerequisites and declared
reader schemas are joined in the [generated capability matrix](generated/analysis_capability_matrix.md).
It is source-declaration evidence, not a replacement for per-source report checks
or the executed [journey matrix](remediation_journey_matrix.md).

## Pilot Follow-up Output Versions

The current DOE expansion contract is API **25**, metadata **23**. Full group identity
readers accept equal-variance schemas 1/2/3 and two-sample-t/Kruskal-Wallis
schemas 1/2. New generic reports identify renderer **2.1.0**; completed/stored
prediction and dedicated workflow reports identify **1.1.0**. These renderer
changes add precision-aware axes/tables and full saved group names, not new
statistical estimates. Existing export files and checksums are unchanged.
Column context preserves differences between float values; paired interval
columns share precision, including a one-row prediction. Legacy truncated group
labels remain readable with an explicit full-name limitation.
See [numeric display](numeric_display_contract.md),
[group identity](group_identity_contract.md) and the
[execution ledger](pilot_followup_0849aaa.md) for scope and actual evidence.

## Historical A11 Contract

Generic HTML artifact schema **4** records locale, exact source SHA-256, renderer
version, rendered section IDs and `full`/`summary` level. Existing files are not
rewritten. A11 introduced API contract 23 for that integrated remediation; method/result
versions and metadata schema 20 are unchanged by report display changes.

A12 is a separate managed-source extension under API 23 with metadata 21. Its
source-specific capability is `POST /api/v1/reports/capability`; the explicit
snapshot view is not a claim that JSON alone is a full report.

| Exact dedicated source | Saved report sections | Honest limit |
| --- | --- | --- |
| Completed PLS/GP prediction | Exact request rows, response/model/hash, all saved means and available latent/observation intervals, warnings | PLS has point predictions only; unsaved browser-only JSON cannot become a server source |
| Legacy dataset/pasted regression prediction | Full saved prediction rows, actual intervals/warnings; pasted inputs | Dataset-prediction legacy inputs were not stored, so that report is summary; no raw-data reconstruction |
| Factorial/general/RSM analysis | Source design/revision, config, model/ANOVA/coefficient/diagnostic tables, estimability/selection/LoF, stored diagnostics | RSM renderer 1.4.0 additionally preserves stored conditional curves and contour geometry; legacy missing sections remain unavailable |
| RSM/regression optimizer | Exact model dependencies/objectives/constraints, saved optimum/predictions/desirability/profiles, confirmation warning | Profiles preserved as saved tables; no new optimum search |
| LHS design/revision | Complete saved design/factor bounds/seed/settings/quality, explicit response revisions | Empty response list is design-only, not implicit latest responses |
| BO history/recommendation/batch revision | Exact study/history observations and optional exact saved pending recommendation/batch, uncertainty/acquisition, history SVG | No live-trial overlay or fantasy values relabelled as observations |

All dedicated sections are capability-checked against their saved payload. An old
source can be readable and stale simultaneously. A missing required section is
not silently labelled full. Model/source checksums are unchanged by export.

`report_coverage.report_definitions()` and renderer-owned section declarations are
the source of truth. `GET /api/v1/analysis-runs/{id}/report-capability?locale=en|ko`
describes the particular stored payload. The catalog exposes the same schema and
variant declarations. There is no separate frontend HTML method allowlist.
HTML POST can bind `expected_source_result_sha256`; mismatch returns 409 without
creating an artifact. Unsupported schema, variant or empty core returns 422.

- `full`: every declared applicable section rendered from stored values.
- `summary`: readable core, with named optional sections unavailable.
- `unsupported`: no valid core/known schema or renderer-contract mismatch.
- `not_applicable`: explicitly unrequested/inapplicable, distinct from missing
  legacy fields. It does not authorize invented values.

These are renderer completeness levels, not claims that every historical file or
option was visually tested. The capability and visible HTML both list actual
sections and reasons. The escaped JSON appendix is not output-coverage evidence.
Stored plot limits stay intact and saved/calculation N is stated; frontend
pagination never restricts report rows/components.

`analysis_report_source` checks ownership/result SHA, row-selection snapshot
identity/SHA and frozen Phase II dependencies without canonical-row reads.
`source_validation=stored_dependencies_only` does not claim to revalidate current
raw data. Stale results carry a visible warning; normal restore/calculation
readers keep their existing freshness policies. Legacy general config has no
independent full-config digest, so this is not arbitrary DB-tamper authentication.

HTML uses escaped text and inline SVG/CSS under the existing CSP. No fit, CV,
prediction, raw-row reload, external resource or full-result CSV flattening occurs.
CSV export is separate. Unknown warning codes retain their code and original
meaning; known messages have explicit translations rather than generic replacement.

### Current Method-Level Sections

Versions and accepted stored schemas are declared in the live catalog and
`INLINE_REPORT_CONTRACTS`; the historical matrix below is not the current contract.

| Method ID | Actual renderer / saved sections | Important limit |
| --- | --- | --- |
| eda.descriptive | Basic EDA: settings/all column statistics | Quick chart is not an additional stored statistical payload |
| eda.graphical_summary | Basic EDA: statistics/AD/CI, histogram/normal fit/box/Q-Q/ECDF | Missing legacy plots are not regenerated |
| eda.normality | normality_report: tests and Q-Q | Missing legacy Q-Q becomes summary |
| eda.principal_components | principal_components_report: eigenanalysis/loadings/scree/score/loading/biplot/D-squared | Raw loadings separate from display scale; no fake PC2 |
| hypothesis.one_sample_t | hypothesis_report: sample/test/effect/estimate/CI plot | Stored one-sided endpoint semantics |
| hypothesis.paired_t | hypothesis_report: pairing/difference/test/effect/CI | Difference definition retained |
| hypothesis.two_sample_t | hypothesis_report: groups/difference/test/effect/CI | No automatic Welch/pooled reselection |
| hypothesis.one_way_anova | hypothesis_report: standard/Welch groups/ANOVA/post-hoc/effects | Current payload lacks residual diagnostics: summary |
| hypothesis.equivalence_tost | hypothesis_report: one-sample margins/CI/two tests/plot | Method-specific variant |
| hypothesis.two_sample_equivalence_tost | hypothesis_report: two-sample TOST and sample summaries | Shared summary_type does not authorize a different design |
| hypothesis.paired_equivalence_tost | hypothesis_report: paired TOST and differences | Same variant/interval constraints |
| hypothesis.one_sample_wilcoxon | hypothesis_report: ranks/test/effect/available estimate | No invented CI |
| hypothesis.mann_whitney | hypothesis_report: groups/ranks/test/effects/available estimate | Not automatically a median difference |
| hypothesis.kruskal_wallis | hypothesis_report: groups/ranks/test/effect/post-hoc | No unsupported interval |
| categorical.one_proportion | categorical_report: counts/test/proportion/interval | Event/trial and one-sided bounds retained |
| categorical.two_proportion | categorical_report: groups/counts/difference/test/interval | Actual sample inputs preserved |
| categorical.chi_square_association | categorical_report: actual/expected counts/residual/effect/association view | Actual and expected labelled separately |
| regression.pearson | correlation_report: correlation/test/CI/scatter | Saved row identity and units |
| regression.xy_correlation | correlation_report: all pair rows/heatmap | Failed cells never become zero |
| regression.linear_model, OLS | linear_model_report: fit/equation/coefs/ANOVA/selection/influence/raw+standardized diagnostics | Missing legacy sections become summary |
| regression.linear_model, Ridge/Lasso/EN | regularized_model_report + residual distribution: tuning/CV/all coefficient paths | No OLS inference |
| regression.partial_least_squares | pls_regression_report: settings/components/coefs/train+OOF/score/all loadings/residuals | No UI pagination limit, invented VIP or p-values |
| regression.gaussian_process | GP core + gaussian_process_report: settings/optimizer/train+CV/residual, named latent/predictive uncertainty, numeric/nominal profiles, stored surface tables/heatmaps, comparison and validation/resource/lineage evidence | Method 0.4/result 4; schemas 1/2/3 readable; missing legacy sections reduce level; exact saved custom surface uses completed-prediction report source |
| quality.individuals_chart | quality_report: I/MR summaries/charts/signals | Shapes and zero limits preserved |
| quality.subgroup_chart | quality_report: Xbar/R/S summaries/charts/signals | Actual subgroup counts/statistics |
| quality.attribute_control_chart | quality_report: p/np/c/u summaries/charts/signals | Point-varying limits and frozen Phase II dependency |
| quality.run_chart | quality_report: runs/randomness/signals | Median only, no invented LCL/UCL |
| quality.capability | quality_report: capability/nonconformance/histogram/specifications | Stored bins, zero LSL/target retained |
| quality.gage_rr | quality_report: ANOVA/variance components/design | Current payload lacks interaction: summary |
| quality.gage_run_chart | quality_report: part/operator/replicate and separate run series | No cross-operator joins or invented timestamps |
| quality.two_variances | two_variances_report: settings/groups/ratio/test/conditional interval/plots | BF intentionally has no ratio CI; Bonett deferred |
| eda.equal_variances | Basic EDA: groups/tests/multiple-comparison intervals/pairs | Distinct from Two Variances ratio CI |

Dedicated workflows still use their own readers/exports. Factorial/general
factorial retain managed analysis HTML and separate legacy design reports.
Managed prediction/RSM/optimizer/LHS/BO reports use the separate **A12 managed-source
implementation**, not generic dispatch. Completed PLS/GPR predictions explicitly
persisted through that API are Report Center sources. Unsaved browser-only JSON
snapshots are not server sources. Neither path overwrites the original analysis.
Comparability and multivariate monitoring stay roadmap-only; Two Variances is
implemented; GP surrogate and model-dependent optimization remain contextual.

### Evidence and Limits

`test_report_coverage` checks registry/dispatch/schema/variant/empty-core contracts;
dispatch mocks are not numerical proof. `test_analysis_report_capabilities` and
`test_analysis_report_source` test actual capability/HTML section parity, source
hash binding, owned paths/snapshots, frozen Phase II dependencies, no raw reads/
CSV flattening and unchanged dependency bytes. Family report tests inspect visible
tables/SVG values, locales, escaping, large stored tables and legacy gaps.
Actual-producer fixtures prove display parity, not independent numerical accuracy.

The A11 browser suite uses actual components with mocked synthetic HTTP for
KO/EN, delayed capability/export, 409, mutation, widths and Unicode downloads.
Real backend API tests separately exercise create/download. These are not the
final all-platform Release gate. Exact checks/failures are in
`end_to_end_remediation.md`; unexecuted combinations are not claimed as verified.

## Historical Audit (Superseded by A11 Above)

The following records the earlier schema-3 baseline and its then-missing sections.
It is retained as audit history, not as the current menu/report support list.

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

Audit source: 38-method backend registry, eight frontend domains and actual export
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
| Basic | eda.principal_components 0.1.0 | principal_components_analysis / 1 | PCA eigenanalysis/loadings, scree and score SVG | supported; bounded saved points; D-squared remains exploratory | PCA API/report |
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
| Regression | regression.gaussian_process 0.4.0 | gaussian_process_regression / 4 (read 1/2/3) | GP renderer + gaussian_process_report; exact completed-prediction surface views | Stored-only numeric/nominal profiles and surface heatmaps; validation coverage/lag/resource notices; old absent fields explicitly limited | GP API/reference/mixed/restore tests executed; new form/archive E2E written, native execution recorded separately |
| Regression contextual | regression.predict 0.3.0 | dedicated prediction / 3 | own CSV/restore | unsupported HTML | prediction API/E2E |
| DOE | doe.factorial_design 0.9.0 | factorial analysis / 3 | factorial_analysis_report | supported; separate legacy design report | factorial exports/E2E |
| DOE | doe.general_factorial_design 0.4.0 | general factorial analysis / 3 | dedicated workflow renderer | supported; cube inapplicable | factorial exports/E2E |
| DOE | doe.response_surface 0.3.0 | dedicated RSM | own workflow | unsupported HTML | capability tests |
| DOE contextual | doe.response_optimizer 0.4.0 | dedicated optimizer | own workflow | unsupported HTML | capability tests |
| AI/ML | doe.latin_hypercube 0.3.0 | dedicated LHS | design CSV | unsupported HTML | LHS API/E2E |
| AI/ML | doe.bayesian_optimization 0.6.0 | dedicated study/recommendation | study/initial-design export | unsupported HTML | BO API/reference/E2E |
| Quality | quality.attribute_control_chart 0.3.0 | attribute_control_chart / 3 | Q: chart summaries/signals | summary; chart SVG absent | API quality exports |
| Measurement | quality.two_variances 0.1.0 | two_variances_test / 1 | two_variances_report: settings/groups/ratio/test/conditional CI, group plot and F ratio interval SVG | supported; BF deliberately has no ratio CI; Bonett deferred | test_two_variances_report + browser E2E |
| Quality | quality.subgroup_chart 0.1.0 | subgroup_chart / 1 | Q: Xbar/R/S summaries | summary | API quality exports |
| Quality | quality.individuals_chart 0.1.0 | individuals_chart / 1 | Q: I/MR summaries | summary | API quality exports |
| Quality | quality.run_chart 0.2.0 | run_chart / 2 | Q: runs/tests | summary | API quality exports |
| Quality | quality.capability 0.1.0 | capability_analysis / 1 | Q: capability/nonconformance | summary; histogram absent | API capability/gage exports |
| Measurement | eda.equal_variances 0.2.0 | equal_variances_test / 2 | E v2: tests/groups/interval SVG | supported | API + E2E |
| Measurement | quality.gage_rr 0.1.0 | gage_rr / 1 | Q: variance components | summary; full ANOVA/interaction views absent | API capability/gage exports |
| Measurement | quality.gage_run_chart 0.1.0 | gage_run_chart / 1 | Q: design/run summary | summary | API capability/gage exports |

Comparability and multivariate monitoring were planned and have no report.
Two Variances is now implemented (the former planned label was obsolete).
BO's surrogate is contextual, not a second GP.
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
