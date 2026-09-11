# Factorial Model Workflow Audit

Status: pre-implementation review, 2026-09-12.
Base: `7e9a8147c8fa963e497179192177fc62ed081194` (fresh origin/main fetch).
Branch: `feat/factorial-model-selection-prediction-plots`.

## Acceptance Gates and Risks

Complete both full-factorial workflows: explicit backward selection, strong
hierarchy, disclosed saturated pooling, immutable response paste/save, final
model diagnostics, stored-model prediction, fitted factorial plots and managed
localized HTML. Preserve legacy readers, direct links and stored hashes.
Never enable selection for aliased fractions or PB. Never invent residual
inference or treat a center indicator as a continuous quadratic surface.
Full checks and Chromium E2E must pass after synchronization with origin/main
before a non-force fast-forward push. Existing untracked `examples/image2.png`
is user-owned and outside this change. `data_prd.md` is absent.

Main risks: post-selection inference, hierarchy/whole-block removal, pure-error
partitioning, diagnostic limits versus full-sample summaries, source integrity,
retention races and English fragment mistranslation. Statistical functions stay
independent of FastAPI. No new production dependency or external data transfer.

## Baseline Inventory

| Capability | Calculation | Persistence/API | UI | Legacy HTML | Decision |
|---|---|---|---|---|---|
| Effect, coefficient, SE/t/p/CI | factorial_analysis `_term_results` | typed result schema 1 | partial table | coefficient/effect/SE/p | preserve; expose final model |
| VIF/equation/PRESS | not present | absent | absent | absent | add versioned fields |
| Backward/pooling | absent | absent | absent | absent | DOE term-block selector |
| Residual/leverage/Cook/Q-Q | `_diagnostics` | persisted, bounded | summary only | diagnostic summary | interactive raw/standardized 4-in-1 |
| Main/interaction means | observed corner means | `plots` | mainly main effects | absent | keep data means; add final fitted means |
| General Full | treatment dummy blocks, partial F | generic result dictionary | term ANOVA | no dedicated report | whole-block selection, final inference |
| Response revision | complete immutable run series | revision/head/relation tables | explicit correction in two-level UI | current responses | paste only to draft; extend general correction UI |
| Legacy report | no refit | on demand, latest saved analysis | API available | design + response + latest analysis | preserve actual behavior |
| Prediction | absent | absent | absent | absent | source-analysis-owned immutable result |
| Analysis-specific export | absent | absent | absent | absent | analysis-owned artifact |

`get_factorial_design_html_report` calls `get_latest_factorial_analysis` and
renders `_factorial_analysis_html_markup`: effects, ANOVA, diagnostics and
provenance already appear. `docs/storage.md` saying the endpoint contains no
analysis is stale. The endpoint does not calculate/refit or persist an export.
Its latest-analysis behavior is not equivalent to an immutable analysis report.

The current General Full reader checks its result SHA but lacks the two-level
reader's complete response/config relationship validation. Prediction must not
inherit that gap; strengthen restore validation without rewriting old bytes.

## Reuse Review

OLS `_select_linear_model` shares partial-F concepts but is coupled to regression
design records and only protects main effects beneath quadratic/two-way terms.
DOE also needs three-way hierarchy, structural blocks, curvature and saturated
starts. Leave OLS code untouched; introduce a neutral, independently tested
term-block engine used by the two DOE adapters. Existing fits, coding and
pure-error functions remain calculation sources, not duplicate implementations.

Reuse interactive SVG scatter/histogram primitives and current DOE tables,
settings/action bars and revision services. Bayesian paste is intentionally
partial/pending-trial based; its truncation/mapping semantics are unsuitable for
Factorial complete-run revisions. Use a strict bounded tabular parser and
preview shared by the two Factorial panels instead.

## Official Findings and Product Differences

Minitab supports term-order selection, fixed blocks and center indicators;
strong hierarchy includes every subset of an interaction. Statistical Twin
keeps hierarchy mandatory and exposes no arbitrary formula or user code.
[Model terms](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/analyze-factorial-design/perform-the-analysis/specify-the-model-terms/),
[Hierarchy](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/analyze-factorial-design/perform-the-analysis/non-hierarchical-model/).

Minitab documents a saturated-start removal phase using small adjusted SS,
hierarchy and a quarter-term target capped at nine; removed terms do not return.
Our explicit half-up tie/count policy and multi-DF extension are product
decisions, not a claim of binary-identical proprietary output.
[Stepwise formulas](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/analyze-factorial-design/methods-and-formulas/stepwise/).

Adjusted SS is a reduced-versus-current model comparison. Standard-error,
VIF and PRESS summaries are conditional on the fitted specification. We retain
negative predicted R-squared, and do not implement Lenth PSE or invent an error
term for screening. [ANOVA](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/analyze-factorial-design/methods-and-formulas/analysis-of-variance/),
[Coefficients](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/analyze-factorial-design/interpret-the-results/all-statistics-and-graphs/coefficients-table/),
[Model summary](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/analyze-factorial-design/interpret-the-results/all-statistics-and-graphs/model-summary-table/).

Residual plots distinguish raw and standardized residuals and full-sample
aggregates from displayed points. [Residual formulas](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/analyze-factorial-design/methods-and-formulas/fits-and-residuals/),
[Plot options](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/analyze-factorial-design/perform-the-analysis/select-the-graphs-to-display/).

Stored-model predictions use a coefficient vector and covariance, with distinct
mean CI and individual PI. A center-indicator fit is not a single continuous
surface; we restrict it to corners or actual centers.
[Prediction formulas](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/using-fitted-models/how-to/predict/methods-and-formulas/methods-and-formulas/),
[Center-point limitations](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/supporting-topics/factorial-and-screening-designs/how-minitab-handles-center-points-in-a-2-level-factorial-design/).

Fitted plots use a stored final model; data means are a distinct view. Our
equal-weight marginalization over declared levels/blocks is explicit. Cubes
display a selected two/three-factor corner slice, not a three-dimensional
response surface. [Factorial plots](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/using-fitted-models/how-to/factorial-plots/before-you-start/overview/),
[Plot settings](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/using-fitted-models/how-to/factorial-plots/perform-the-analysis/enter-your-data/),
[Cube](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/using-fitted-models/how-to/cube-plot/before-you-start/overview/).

Existing public NIST fixtures remain numerical references; add an independent
QR-based synthetic selection/prediction fixture rather than call production
helpers to create expected results. [NIST effects](https://www.itl.nist.gov/div898/handbook/pri/section6/pri615.htm),
[NIST lack of fit](https://www.itl.nist.gov/div898/handbook/pmd/section4/pmd446.htm).

## Version and Storage Decision

Planned new writes: API 19; Factorial 0.8.0, config 3, result 2, envelope 2;
General Full 0.3.0, config/result 2, envelope 1. Design schemas and response
revision schema do not change. Old config/result bytes stay immutable.
Generic `analysis_artifacts` has an analysis-run foreign key and cannot safely
own dedicated DOE assets. Metadata 20 adds an analysis-owned relation for
bounded prediction JSON and HTML bytes. SQLite BLOB storage (maximum 16 MiB per
artifact) permits transactional SHA-checked writes/deletion without orphan-file
races. No raw paths, pickle or extra model registry are required.

## UI Direction

Continue the compact blue workbench: white #FFFFFF, neutral #F4F6F9,
selection #225AA7, text #172033, borders #CCD6E3, warning #8A5B00.
Use existing local Segoe UI/Malgun Gothic and left-aligned settings/tables.
Layout: settings -> selection/equation/summary -> coefficients/ANOVA -> effects
-> residual disclosure -> factorial plots -> prediction -> reports.
No decorative nested cards; charts 2 columns desktop and 1 mobile, tables
scroll internally, destructive actions preview impact and restore focus.
Review against brief: retain the recently shipped compact shell rather than
introduce another design system. Short summaries remain visible; detailed
selection traces and technical provenance are disclosures.

## Verification Record

Baseline commands are running before calculation edits. Results, exact commands,
independent fixture provenance, screenshots and final gate results will be
recorded as each completes. This document does not assert implementation or
passing tests in advance.
