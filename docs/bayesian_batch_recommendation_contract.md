# Bayesian Batch Recommendation Contract

Last updated: 2026-11-09

## Current Scalar V2 Policy

The scalar UI review workflow introduced through API30/31 first generates a
temporary candidate review. Only the explicit
confirmation command registers its entire ordered batch as pending experiments.
The existing direct-create API remains supported. Review/confirmation does not
change V2 mathematics or any saved schema; see
[review contract and evidence](bo_jmp_workflow_stages.md). Partial selection or
reordering is not exposed because later marginal scores depend on earlier ranks.

New UI requests use schema3, method0.8.0 and an explicit numeric kernel selection.
Legacy schema2/method0.7.0 retains its fixed Matern5/2 meaning and original hashes.
Both use
`greedy_mc_joint_latent_improvement_v2`. Noise/latent incumbent, exact-repeat
sufficient statistics, correlated MC planning, mixed search and version dispatch
are specified in [BO/GPR extension](bo_gpr_noise_validation_extension.md).
Kernel/result dispatch and metadata25 migration are specified in
[numeric kernel alignment](bo_kernel_alignment.md). The acquisition policy itself
is not changed by choosing a kernel family.
Default posterior sample count is64 (allowed16..256); q1 is analytic.
All q1..q8 requests share one fit/core. The optional normalized batch distance
defaults to0 and is separate from duplicate tolerance. Infeasible or over-budget
batches are rejected atomically; no partial pending trials are committed.
New result predictions use the real-data base posterior; planning conditional
uncertainty is separately labeled. Exact qNEI/JMP numerical equivalence is not claimed.

API33 also stores multiresponse q1 recommendations in the same atomic batch/item
tables under a distinct result4/model5/item3/policy tuple. They use the separate
[desirability review contract](bo_desirability_review.md), not this scalar MC
policy. Generic batch GET/list/latest responses include both versioned families;
the scalar creation API and scalar UI reject a vector result instead of casting
it to a scalar shape. API34 extends this union with method0.10.0,
config5/result5/model5/item4 ordered multiresponse batches. The distinct
conditional MC/Beta calculation, whole-batch confirmation, immutable source
cutoff, partial current-trial overlay and exact report are specified in
[Stage3h](bo_desirability_public_batch.md). It does not replace this scalar policy
or reinterpret existing q1 result4 artifacts.

The following sections specify the retained **legacy V1** mean-fantasy policy.
They are not the current UI defaults, and no old artifact is recalculated.

## Scope

Method `doe.bayesian_optimization` `0.4.0`, study schema `3`, API contract `6`,
and metadata schema `18` add synchronous recommendation batches. A request
chooses either:

- `sequential_single` with `batch_size=1`; or
- `parallel_batch` with `batch_size=2..8`.

`batch_size` is the number of real conditions proposed now.
`candidate_count_per_step` is an internal acquisition-search pool, and
`total_trial_budget` is the Study-wide cap. They are separate fields and
separate UI concepts. If the exact requested size exceeds the remaining budget
or cannot be generated, the whole operation fails. It is never truncated.

## Statistical Policy

The policy ID is `greedy_posterior_mean_fantasy_ei_v1`.

1. Fit the existing Matérn 5/2 ARD Gaussian Process once to completed real
   observations.
2. Select the best feasible, novel EI or Target-EI condition through the
   existing seeded bounded candidate and local-search policy.
3. Use that condition's posterior mean only as an in-memory fantasy value.
4. Condition a GP with the fitted kernel hyperparameters fixed and select the
   next condition.
5. Exclude completed, pending, abandoned, legacy recommendation, and earlier
   batch coordinates with the existing normalized duplicate tolerance.
6. Repeat until exactly `q` distinct conditions exist.

Fantasy values are never stored as observations, history revisions, or trial
objective values. The policy is deterministic for the persisted seed and
configuration. It is a pragmatic greedy batch approximation using the pinned
scikit-learn GP, not exact Monte-Carlo joint qEI.

For `q=1`, the existing candidate/search path is preserved and reference tests
require coordinate, predicted mean, posterior standard deviation, incumbent,
and EI parity with the legacy single calculation.

## Acquisition And Reasons

Directional goals use analytic Expected Improvement. Match-target goals use
analytic Expected Target Improvement from
`E[max(d_best - xi - |Y-target|, 0)]`. Presets resolve to standardized `xi`:

- exploitation: `0.0`;
- balanced: `0.01`;
- exploration: `0.1`;
- custom: explicit `0..10`.

Each item stores structured metrics and one stable reason code:

- `predicted_improvement_driven`;
- `uncertainty_driven`;
- `balanced_improvement_uncertainty`;
- `target_distance_reduction`;
- `batch_diversity_adjusted`.

The UI derives qualified Korean explanations from those codes and metrics. It
does not store an unsupported causal explanation, contribution percentage,
success guarantee, or global-optimum claim.

## Atomic Storage

One `BEGIN IMMEDIATE` transaction rechecks the active Study, exact history
ID/SHA, absence of a pending recommendation trial, exact remaining budget,
trial numbering, batch size, item ranks, and item-to-trial relationships. It
then inserts all `q` trials, one batch, and `q` items and verifies the item
count before commit. Any conflict rolls back every row.

Schema 18 adds:

- `bayesian_recommendation_batches`;
- `bayesian_recommendation_batch_items`.

Legacy `bayesian_recommendations` rows and hashes remain unchanged. Restore
checks canonical config/result/item hashes, source history, Study definition,
rank `1..q`, exact item count, trial coordinates/state, bounds, constraints,
finite acquisition values, and within-batch uniqueness.

## Lifecycle

Every item starts as pending `origin=recommendation`. Batch state is derived:

- `pending`;
- `partially_completed`;
- `completed`;
- `abandoned`;
- `closed_mixed`.

Each completion appends a real observation history revision. A pending item
blocks another recommendation batch and Study close. The next batch becomes
eligible only after all current items are completed or abandoned. This is
synchronous batch BO; asynchronous refill is not implemented.

## Routes And Compatibility

- `POST/GET /api/v1/bayesian-studies/{study_id}/recommendation-batches`;
- `GET .../recommendation-batches/latest`;
- `GET .../recommendation-batches/{batch_id}`.

Capability gates are `bayesian_batch_recommendation` and
`bayesian_objective_goal_modes`. Legacy Study schemas 1/2 and single
recommendation direct links remain readable and are not migrated to batch
records.

## Limitations

- continuous bounded factors only;
- one manually observed response;
- EI family only;
- no asynchronous batch refill;
- no exact qEI, UCB, PI, Thompson sampling, arbitrary objective code, equipment
  execution, or multi-response desirability;
- recommendations require real confirmation experiments and do not guarantee a
  global optimum.
