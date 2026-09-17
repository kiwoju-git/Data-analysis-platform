# Analysis Domain Navigation Implementation

## Dashboard and navigation update (2026-09-17)

The sidebar **Analysis** and **Graphs** labels now open `/analysis` and
`/graphs`, using the same handlers as Home. Their separately labelled chevron
buttons expand/collapse submenus without navigation. On mobile, navigation
closes the drawer and returns focus to its toggle. Domain/family/method IDs,
direct URLs, dataset query context and browser history remain unchanged.

Home reuses the eight-domain catalog below six icon-led quick actions, then
shows the existing dataset/recent-analysis/model/report resources. Root domain,
method and graph-type entries share small locally bundled Lucide icons and the
existing graph selection blue. Short purpose labels replace long domain prose
on entry cards; help and all executable/planned/contextual distinctions remain.
See `dashboard_navigation_refresh.md` for checks, dependency review and rollback.

## Refined Workbench Update (2026-09-11)

The eight-domain landing remains visible until a method is chosen. An open
method now puts the repeated catalog in the initially closed native **Change
analysis** disclosure. Only navigation is inside this disclosure; the input,
filter, result, history and export panels remain mounted outside it. Locale and
disclosure changes retain current drafts and dataset selection. Method help and
short design tags remain visible. Sidebar groups initially open only for the
active page; explicit user expansion is retained and a newly active group opens
automatically. Mobile drawer behavior and all routes are unchanged.

Selection color comes from Graph Builder (`#225AA7`). Navigation surfaces are
neutral, shared analytical sections are unframed and compact, and active controls
retain non-color state cues. See [design and validation record](refined_ui_design.md).

## Compact Selection Update (2026-09-07)

Eight domains, primary method placement, contextual methods, direct URLs,
sidebar activation and PCA/PLS/GP/DOE/Bayesian workflows are retained. Only
selection density references commit `fb07c68405e0038e2a694a35d806a1a191b2cfda`;
no old files were restored or the repository reset.

Root cards omit order badges, duplicated status counts and repeated open text.
Flat method cards use names, availability and up to three guidance tags.
Method/family grids precede a native, initially closed selection-guide details.
Planned-only families appear as compact neutral notices, not executable cards.
The regression domain retains five methods; OLS/Ridge/Lasso/Elastic Net are
options inside Fit Regression Model, not additional method cards.

## Scope and compatibility

The presentation layer keeps the eight-domain taxonomy while refining how each
domain is entered and how its methods are shown. The six backend
`AnalysisModuleId` values, method IDs, routes, request and result schemas,
method versions, saved artifacts, checksums, restore behavior, and calculation
panels are unchanged. A leaf method still opens its existing route:

`/analysis/{legacy-module}/{method-id}`

The root `/analysis` route shows the eight-domain landing page. Clicking an
inactive sidebar domain opens its landing and expands its submenu. Clicking the
already-active domain only toggles that submenu. A selected
domain uses `/analysis?domain={domain-id}`. The query is presentation state and
does not enter an analysis request or saved result.

## Presentation modes

`analysisDomains.ts` is the single source for two independent display choices:

- `flat_methods` landing/sidebar: Basic Statistics & Exploration; Correlation,
  Regression & Prediction; DOE & Optimization; AI/ML Experimental Design.
- `family_cards` landing and `family_tree` sidebar: Mean Comparison &
  Equivalence; Proportions & Categorical Data; Quality & Process Monitoring;
  Measurement Systems & Variability.

Flat domains show executable methods, planned work, and explicitly contextual
information at one level. A grouped family with exactly one executable method
and no contextual/planned siblings becomes a direct sidebar leaf. ANOVA,
Categorical Association, Time-Ordered Patterns, and Process Performance
therefore open their existing method without another disclosure level.

Basic Statistics no longer exposes Distribution & Summary or Multivariate
Exploration headings. Its four same-level cards are Descriptive Statistics,
Graphical Summary, Normality Test, and available Principal Components
Analysis. PCA uses `eda.principal_components`; the former planned-only
`eda.multivariate_review` route is replace-redirected to it.

## Domain mapping

| Presentation domain | Family | Existing executable methods | Contextual or planned |
| --- | --- | --- | --- |
| Basic Statistics & Exploration | Flat methods | `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, `eda.principal_components` | none |
| Mean Comparison & Equivalence | t-Tests | `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.two_sample_t` | Two-Sample Comparison guide |
| Mean Comparison & Equivalence | ANOVA | `hypothesis.one_way_anova` | ANOVA is a family, not a duplicate method |
| Mean Comparison & Equivalence | Equivalence Tests | `hypothesis.equivalence_tost`, `hypothesis.paired_equivalence_tost`, `hypothesis.two_sample_equivalence_tost` | none |
| Mean Comparison & Equivalence | Comparability Assessment | none | planned `hypothesis.comparability_assessment` |
| Mean Comparison & Equivalence | Nonparametric Tests | `hypothesis.one_sample_wilcoxon`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis` | none |
| Proportions & Categorical Data | Proportion Tests | `categorical.one_proportion`, `categorical.two_proportion` | none |
| Proportions & Categorical Data | Categorical Association | `categorical.chi_square_association` | none |
| Correlation, Regression & Prediction | Flat methods | `regression.pearson`, `regression.xy_correlation`, `regression.linear_model`, `regression.partial_least_squares`, `regression.gaussian_process` | contextual OLS prediction/optimizer; PLS point prediction and GP probabilistic prediction are available from fitted results |
| DOE & Optimization | Flat methods | `doe.factorial_design`, `doe.response_surface`, `doe.response_optimizer` | contextual `doe.general_factorial_design` opens inside the factorial workspace |
| AI/ML Experimental Design | Flat methods | `doe.latin_hypercube`, `doe.bayesian_optimization` | Gaussian Process Surrogate shown as non-executable `Used by Bayesian Optimization` context |
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

The selected-method heading now uses a two-row grid: title and non-wrapping
actions on the first row, followed by a full-width compact input/design tag
strip. This is presentation-only and leaves guidance tags and panel state
unchanged.

The later API-contract-15 refinement removes the duplicate standalone General
Full Factorial leaf from ordinary navigation. `doe.factorial_design` is the
canonical workspace for two-level full, regular two-level fractional, and
general full factorial creation. The `doe.general_factorial_design` method ID,
dedicated APIs, saved designs, and readers remain registered as contextual
compatibility surfaces. A legacy direct URL is replace-redirected to the
factorial workspace with `design_kind=general` and its `design_id` preserved.

## Deliberately not added

- ANOVA remains a family containing One-Way ANOVA; there is no duplicate ANOVA leaf.
- Two-Sample Comparison is guidance across existing methods, not a calculation.
- Gaussian Process Surrogate remains contextual Bayesian Optimization
  information. Standalone `regression.gaussian_process` is one executable
  method in Correlation, Regression & Prediction and is not duplicated in the
  AI/ML domain.
- Comparability Assessment is planned because it must coordinate multiple CQAs and tests.
- PLS Regression is available as a distinct PLS1 regression method. PLS-Based
  Monitoring remains planned and is not presented as the same calculation.
- Two Variances, comparability, and multivariate
  monitoring require their own later statistical contracts and PRs.

## Version and migration decision

- The ten-factor DOE/PCA update advances API contract `16` to `17` for PCA and
  expanded typed DOE limits.
- Existing statistical method versions are unchanged. New
  `regression.partial_least_squares` writes use method version `0.1.0`.
- Existing result schemas are unchanged. PLS result schema and safe JSON model
  manifest schema both start at `1`. Standalone GP uses result schema 1 and a
  checksummed JSON manifest plus model-owned non-object NPZ state. The existing
  Bayesian recommendation calculation path remains numerically compatible;
  its factor-definition contract is v0.6.0.
- Metadata schema: unchanged.
- SQLite migration: none.
- Existing saved artifacts and checksums: not rewritten.
# Unified landing presentation (2026-09)

`landingCatalogMethods` projects direct and family method IDs into one ordered
presentation list without changing canonical placement. All eight domains use
`AnalysisDomainMethodCard`; the four family domains add a small family caption
instead of nested family boxes. Planned/contextual family items remain separate
non-executable rows below the collapsed guide. Sidebar taxonomy is unchanged.

Sidebar items carry semantic `kind` metadata (domain/family/method/workflow).
Active ancestors have a quiet text emphasis; the active method retains the blue
fill, weight and leading border. Expansion and navigation state are unchanged.
Tests assert identical method sets/order with a reversed API catalog, common
card counts, retained planned items, and semantic hierarchy/active leaf markup.

## Mean-domain grouping (2026-09-18)

The mean/equivalence domain alone now groups its unchanged ten cards into
t-tests (3), ANOVA (1), equivalence (3), and nonparametric comparison (3).
These are flat pale-gray section bands with labelled h3 headings and separators,
not additional clickable family cards. The shared method card, blue selected
state, icons, route/state ownership and canonical order stay unchanged.
Repeated per-card family captions are omitted inside these labelled sections.
Comparability remains a separate planned row and guidance remains collapsed.
Wide screens place ANOVA alongside t-tests; mobile stacks methods without
clipping. Other seven domains and sidebar taxonomy are untouched.

The installed ui-ux-pro-max skill was read and its `navigation grouping
hierarchy` UX search supplied heading-hierarchy/accessibility guidance. The
narrower proximity search had no relevant grouping match; the gray bands use
the existing design tokens and the user's request, not a claimed skill preset.
No new palette, font, icon or chart library was introduced.
