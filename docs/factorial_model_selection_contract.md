# Factorial Model Selection Contract

Status: implementation contract, updated 2026-10-20. Official sources and baseline
inventory: `factorial_model_reduction_prediction_plots_audit.md`.

## Scope and Options

Two-level full, General Full and catalogue-backed regular fractions support
selection. Regular fractions support main and two-factor interaction requests;
PB remains main-only and rejects backward with
`doe_factorial_model_selection_unsupported_for_aliased_design`.
Defaults: method `none`, alpha-to-remove 0.05 (finite, strictly 0..1), hierarchy
`strong`, saturated policy `pool_smallest_adjusted_ss`, step details true.
Unknown options are rejected; omitted options preserve the original full fit.

## Blocks and Hierarchy

Each two-level main/interaction is a 1-DF block. Each General Full term comprises
all its treatment dummy products; individual category coefficients never leave
alone. Intercept and block columns are structural and fixed. Center curvature
is an independent candidate by default, optionally forced or excluded. It is
never a factor-subset hierarchy parent. Explicit candidate/forced/excluded
term policies and the server catalog are defined in
`factorial_manual_term_selection_contract.md`. A factorial term is
removable only when no remaining higher-order term contains its factor set.
Validate initial hierarchy and exact column coverage. Rank-deficient initial
matrices fail after the explicit regular-fraction representative preflight.
Selection never treats duplicate alias columns as independently estimated.

## Regular-Fraction Representative Preflight

Method 0.10.0 writes result 4/config 5 for regular fractions (full and PB retain
result 3/config 4). API 25 adds POST `analysis-term-preflight` alongside the
existing design-owned catalog. Historical methods/configs/results remain readable
without rewriting their hashes.

Build the actual run matrix including centers and blocks. Before using response
values, select whole independent term blocks in this order: structural, forced
and their parents, main effects, then canonical interactions. Unit-column-norm
SVD uses a fixed full-request-matrix tolerance for every candidate rank check.
Record requested parameter count (after manual exclusions), independent rank,
residual DF, tolerance, representatives, signed exact aliases and other rank
dependencies. Positive residual DF, saturation and rank deficiency are distinct.
Conflicting forced terms fail rather than silently dropping a forced effect.

Only representatives enter the unchanged selection engine. Alias/rank exclusions
are not backward removals. Manual exclusions, initial adjusted-SS pooling,
backward removals and final retained terms remain separate. No alternative alias
representative re-enters during backward. Inference is conditional on this model;
it does not establish that unrepresented/high-order aliases have zero effects.
Requested and effective representative interaction orders are stored separately.

## Saturated Start

Let m be the initial number of nonstructural term blocks. If residual DF=0,
target=min(9,max(1,floor(m/4+0.5))). Repeatedly evaluate currently removable
blocks using `max(0,SSE_reduced-SSE_current)` and remove the smallest adjusted
SS, recomputing after each removal. Stop pooling only after target removals and
positive residual DF, or an explicit structural/rank stop. No p-value is used
or stored for pooling. Multi-DF blocks leave whole. Removed blocks never return.
Tie tolerance is relative 1e-12 for SS; prefer higher order, later initial
position, then stable ID. Pooling assumes omitted effects are negligible; it
does not demonstrate zero effects or supply independently observed pure error.

## Backward Phase

For each hierarchy-eligible block, fit its reduced model. Let r be rank loss:
F=((SSE_reduced-SSE_current)/r)/(SSE_current/DF_current).
Remove the largest-p candidate only when p>alpha. Absolute p ties within 1e-12
prefer higher order, later initial position, then stable ID. Refit after every
removal; never re-enter. If MSE is numerically zero, stop with an explicit
variance-unavailable reason rather than invent p-values. At most the initial
number of eligible blocks can leave. No stochastic decisions or sampling.

Trace includes initial/full, pooling and backward phases, active IDs,
coefficients, removed ID/DF/SS/p, residual DF, SSE, S, R-squared, adjusted
R-squared, PRESS and predicted R-squared. Suppressing detail drops only steps,
not initial/final/pooled/removed IDs, policy or stop reason. Post-selection
inference is marked exploratory in results, UI, predictions and reports.

Each detailed step additionally records current-model term DF/p-values,
coefficient labels/values and Mallows Cp relative to the initial specified
model's MSE (null when unavailable). Internal step 0 displays as Step 1.
User exclusions, forced terms and automatic removals are separate collections.
On p ties, interactions precede independent Center, then main effects; order,
original position and stable ID complete the deterministic policy.

## Final Fit

Reuse the original coding and fit functions with the final columns. Recalculate
all coefficient inference, partial-F ANOVA, pure error/lack of fit, residual,
influence, plots and prediction basis from that matrix. Never mix initial fit
metrics with final coefficients. Grouped ANOVA uses joint drop-block SS, not
the sum of nonadditive partial SS. Preserve old fields when `none` is selected.

PRESS=sum((e/(1-h))**2), using every observation. If any 1-h<=1e-10, return null
and `doe_factorial_press_unavailable_high_leverage`. Predicted R-squared is
1-PRESS/TSS, not clipped at zero. VIF uses each nonintercept final column's
centered SST times the corresponding diagonal of inverse(X'X); null for
unavailable/degenerate columns. General Full VIF is coefficient-level, not GVIF.

No automatic removal of structural terms, Lenth PSE, studentized deleted
residuals, arbitrary generators or response transformations. PB alias-aware
selection remains unsupported. OLS regression selection is not refactored.

## Validation Gate

Independent fixed fixtures, brute-force deleted-observation PRESS, full-model
parity, multi-DF block removal, ABC lower-term retention, deterministic ties,
pool count/cap, structural terms, regular-fraction representatives and PB rejection
are required.
All numerical comparisons declare tolerances. No stored legacy payload rewrite.
