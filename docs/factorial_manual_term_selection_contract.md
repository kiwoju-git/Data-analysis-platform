# Factorial Manual Term Selection Contract

Pre-implementation contract, 2026-09-16. See the center-curvature audit for
official sources, supplied fixture and immutable-history boundaries.

## Catalog and Policies

A server-generated, schema-1 term catalog uses the exact calculation term IDs,
labels, kinds, factor IDs, dependency IDs and block widths. It is keyed by
design ID and maximum interaction order. No frontend-derived IDs. Full and
General Full support candidate/forced/excluded policies; fractional/PB retain
their original full-model path and reject automatic selection.

Intercept and blocks are structural and forced. Center is independent,
candidate by default, optionally forced or excluded. Main effects and
interactions participate in factorial hierarchy even when forced. Unknown or
duplicate policies and structural exclusion are typed errors. With `none`,
candidate and forced are included without automatic elimination. Excluded
terms never enter the initial matrix and are reported separately from removals.

Hierarchy validates every subset of each included interaction. An included
interaction blocks exclusion of a parent. Adding an interaction explicitly
restores its needed dependencies with a visible notice; the server never
silently restores an excluded term. Changing maximum order preserves policies
for surviving IDs and makes changes explicit. No stale catalog may submit.

## Selection Engine

`hierarchy_role` is factorial_term, independent_term or structural_term.
Only factorial_term pairs participate in subset comparisons. Forced terms
remain in every fit. Saturated pooling includes eligible independent Center
without priority over actual SS. Quarter-count, half-up/minimum-one/maximum-nine
pooling remains, using candidate blocks; no unavailable p-values are fabricated.
Partial-F backward and no re-entry remain unchanged.

Within p tolerance 1e-12, prefer interactions (higher order first), independent
Center, then main effects; then later original order and stable ID. SS ties use
the existing scale-aware tolerance. Fixed structural blocks cannot be removed.

## Steps and Summaries

Internal step 0 is displayed as Step 1. Each step stores freshly recomputed
term-block partial F p-values, DF, label, status and individual coefficients.
A multi-DF block has coefficient=null and explicit level-coefficient details,
never a fabricated scalar. Removed terms have empty subsequent values.
Detailed UI uses desktop column groups and a mobile step selector; summary-only
requests still persist candidate/forced/excluded/removed/final policy metadata.

Mallows Cp = SSE_step / MSE_initial - (n - 2*p_step). The reference is the
user-specified initial matrix after manual exclusions. If its residual DF/MSE
is unavailable, Cp is null with `reference_full_model_mse_unavailable`.
PRESS uses all observations and is null at leverage singularities. Selection
p-values and intervals are exploratory, not independent confirmatory inference.

## Versions and Legacy Reads

Planned new writes: API 20; Factorial method .9/config 4/result 3/envelope 2;
General Full method .4/config 3/result 3/envelope 1. Design/revision/prediction/
report storage schemas and metadata 20 remain. Legacy config reconstruction
must omit new default fields when validating old hashes. Reading never refits
or rewrites results. Existing prediction/report assets remain source-bound.
