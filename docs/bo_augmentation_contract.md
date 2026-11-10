# Fixed-Candidate BO Augmentation

## Scope and Status

This contract describes `backend/app/statistics/bo_augmentation.py`. It selects
exact rows from a verified immutable candidate revision. It does not generate
coordinates, fit a model, condition a posterior, write observations, or create
pending trials. Existing conditional Monte Carlo acquisition remains a separate
policy. Service/API/UI integration is a separate completion gate.

The pure policy tests passed as part of a 249-test core checkpoint on native
Windows/Python3.10.11. Later 108-test and 118-test focused runs covered augmentation,
the saved-model/model-free adapter, candidate validation, and the existing
planning model on the same native target. The latter includes typed response-context
and extreme-unit tests. These checkpoints do not
establish service/UI completion, installed-package validation, or JMP parity.

## Official Evidence and Product Choices

The JMP 19.2 Candidate Set documentation identifies model-free MaxPro exploration,
model refinement starting with expected improvement, and optimum confirmation
starting with Bayesian desirability. Its refinement description additionally
uses multimodel uncertainty; its confirmation description limits later choices
to a competitive subset. The publication does not specify every numerical
implementation detail. See [JMP Candidate Set](https://www.jmp.com/support/help/en/19.2/jmp/candidate-set.shtml).

The MaxPro paper defines the criterion below and explains its singularity when
two points share a coordinate. Our fixed-candidate greedy augmentation is not
the paper's full design-construction optimizer. See Joseph, Gul and Ba (2015),
equation (5), [Maximum projection designs for computer experiments](https://doi.org/10.1093/biomet/asv002)
([author paper copy](https://www.asc.ohio-state.edu/statistics/comp_exp/jour.club/max_projection_designs_roshan2015.pdf)).

All policies emit `bayesian_augmentation_not_verified_jmp_parity`. This records
the absence of matched JMP output validation, not a numerical failure. Labels
must describe the implemented policy, not claim a recovered proprietary
algorithm, global optimum, or probability that a setting is optimal.

The public, unversioned [JMP Scripting Index](https://jsl.jmp.com/All%20Categories/Objects/Bayesian%20Optimization.html#maximize-multimodel-std-dev)
describes multimodel uncertainty in terms of predictions of multiple responses.
It does not provide the scalar aggregation or scheduling formula used below.
Our version 2 uses one saved GP per response, not an ensemble of kernel fits.

## Source and Input Boundary

`select_augmentation(rows, ..., source=...)` receives the row structure emitted
by the read-only planning evaluator. The service must verify candidate, model,
and history ownership/hashes before calling it. The pure function validates the
identity format; it cannot authenticate bytes it did not receive.

Required source fields:

- `candidate_revision_id`: canonical UUID.
- `candidate_revision_sha256` and `history_sha256`: lowercase SHA-256 strings.
- `model_snapshot_id` and `model_snapshot_sha256`: both present for model-based
  policies, or both null for model-free selection.

Each row has a unique 64-character hex `row_id`, complete normalized coordinates,
and boolean `eligible`, `novel`, and `constraints_satisfied` flags. Eligibility
must equal novelty AND constraint feasibility. The verified service supplies
executable factor values and constraint evaluations; this policy engine does
not invent levels, round coordinates, or re-evaluate unknown constraints.

Numeric coordinates lie in `[0, 1]`. Nominal identities are equality tokens,
not distances between codes. Ordinal coordinates are normalized ranks only
when the caller explicitly opts into that distance assumption. Unknown kinds,
missing coordinates, non-finite/coerced numbers, duplicate row IDs, duplicate
candidate coordinates, and inconsistent flags fail atomically.

Reference coordinates include completed, pending, and abandoned locations under
the existing novelty policy. The service supplies one canonical representation
per trial. At most 400 reference representations are accepted, allowing the
existing 200-trial reader's original/re-normalized compatibility representations;
this does not raise the trial limit. Exact duplicate references are removed for
spatial geometry only, with both original and unique counts reported. No history
or training view is altered.

## Distance and Eligibility

All selections independently recheck novelty against the supplied references.
The distance is the square root of summed squared normalized numeric differences
plus one for each nominal mismatch. Ordinal rank differences contribute only
under the explicit equal-rank-spacing assumption. This is a documented product
distance, not mixed MaxPro or a model-derived category correlation.

`duplicate_tolerance` is separate from `min_batch_distance_normalized`. The first
rejects old/selected locations within tolerance; the second optionally separates
selected batch rows. A requested separation cannot be achieved by moving a row.
Insufficient candidates cause an error, never a partial successful batch.

## Policies

### Greedy Incremental MaxPro

Policy: `greedy_incremental_maxpro_v1`, continuous factors only.

For a full design with `n` points and `p` factors, the published criterion is

```text
psi(D) = [ (1 / choose(n, 2))
           * sum(i < j) 1 / product(k) (x[i,k] - x[j,k])^2 ]^(1/p).
```

For fixed reference points `R` and already selected rows `S`, the implemented
greedy step minimizes the candidate-dependent increment

```text
cost(x | R,S) = sum(z in R union S) 1 / product(k) (x[k] - z[k])^2.
```

The fixed reference-reference contribution is omitted. The positive
normalization and root do not change the candidate ordering at a fixed step.
When reference projections are already tied, the full-design objective is
infinite; the code explicitly reports that condition and uses only the named
incremental policy, not a claim that the full objective has become finite.

Costs are compared in log space. A new shared projected coordinate is an
unscorable candidate: the trace records `score: null` and
`status: projection_collision`, never JSON Infinity. No arbitrary epsilon is
added. If no finite candidate remains, selection fails. Discrete, nominal, and
ordinal requests cannot silently fall back to a different method.

### Explicit Mixed Maximin

Policy: `greedy_mixed_maximin_v1`, selected explicitly by the caller.

At each step maximize the nearest distance to reference and selected points
using the distance above. This permits nominal equality and, only with an
explicit opt-in, ordinal rank spacing. It is neither the continuous MaxPro
formula nor a claimed implementation of JMP's mixed-factor criterion. Model
means, variances, and snapshots are unnecessary for this path.

### Refine with Desirability SD

Policy: `refine_ei_then_desirability_sd_v1`.

Select the largest saved base-posterior desirability EI first. Select later rows
by the largest saved desirability SD, respecting novelty and distance. Inputs
are the existing bounded beta-moment desirability EI and base posterior moments;
no posterior mean fantasy or conditional variance is substituted.

Multimodel SD is not implemented here. The explicit warning
`bayesian_refine_multimodel_sd_not_implemented` must remain visible. This is the
D-SD-only policy, not a complete replica of JMP's Refine Model calculation.

### Refine with Alternating Response Uncertainty

Policy: `refine_ei_alternating_desirability_response_sd_v2`.

The first row maximizes the same base-posterior Beta EI. Ranks 2/4/6/8 maximize
base desirability SD; ranks 3/5/7 maximize the following dimensionless aggregate:

```text
w[j] = importance[j] / sum(importance)
response_sd(x) = sqrt(sum(j) w[j] * (latent_sd_raw[j](x) / y_scale[j])^2)
```

Weights use max-scaled normalization to avoid overflowing the importance sum.
`y_scale` is each saved response model's actual normalization scale, including
its recorded constant-response policy. It is not recalculated from candidates.
Positive unit changes applied to both the raw SD and that response scale leave
the criterion unchanged. Stable `hypot` evaluation avoids squaring overflow or
underflow; an unrepresentable nonzero normalized contribution is an explicit
numeric error, not zero.

The metric uses latent uncertainty, excludes future observation noise, and is
not the SD of a sum of responses. The scalar aggregation, goal-importance
weights, and alternating schedule are explicit product choices, not recovered
JMP formulas. The version 2 warning records this distinction. The existing
version 1 policy and its historical meaning remain unchanged.

Version 2 results add `response_uncertainty` with the exact response IDs, saved
scales, normalized weights, variance kind, and schedule. Every row must supply
one finite nonnegative latent SD per declared response; unknown, duplicate or
missing response IDs fail. Version 1 results do not gain default fields when
read or serialized. No additional GP fit or fantasy conditioning occurs.

### Confirm with a Competitive Subset

Policy: `confirm_mean_then_competitive_sd_v1`.

Select the largest expected desirability first. For each later selection retain
rows with expected desirability at least the supplied `latent_incumbent`, then
maximize their base desirability SD. The incumbent is the maximum expected
desirability at completed observed locations, supplied from the verified model
snapshot. It is not the largest observed response, a globally optimized
prediction, or a probability of optimality. Equality at the threshold is allowed.

Confirm does not require or calculate EI: its returned prediction rows contain
`acquisition: null`. Thus a valid mean/SD comparison is not rejected merely
because a concentrated Beta approximation cannot be evaluated. Other moment,
source, and numeric validations remain; the absence of EI is never reported as
a computed zero. Refine retains the existing explicit Beta precision limits.

Neither model-based policy refits or changes the posterior after selection.
`bayesian_augmentation_base_posterior_not_conditioned_by_selection` distinguishes
these scores from the existing conditional MC policy. Selection does not turn
predicted responses into experimental observations.

## Reproducibility, Limits, and Result

- At most 10 factors, 10,000 rows, and 8 selected rows.
- At most 100,000 candidate-step evaluations and 60,000 ms. A caller may reduce
  these explicit budgets; no hidden truncation is used.
- An evaluation is one considered candidate at one greedy step, including rows
  subsequently excluded by selected-distance or competitiveness conditions.
  Pairwise distance/projection comparisons are separately counted. Row validation
  and reference-distance checks also honor the deadline.
- Stable ties use `row_id` ascending. No random number generator, Python hash,
  input-row-order tie break, optimizer, or sampling fallback is used.
- Results preserve detached source IDs/hashes, ordered exact row IDs, criterion,
  score scale/direction, nearest distances, competitive threshold, counts,
  exclusions, budgets, and explicit no-refit/no-fantasy flags.
- Every returned number is finite or explicit null. No raw response, category
  label, source path, or coordinates are included in exception messages.

The view adapter shares one absolute deadline across canonical candidate
validation, saved-state restoration, prediction, and selection. Validation checks
the deadline between rows rather than finishing the full table before rejecting.
The allowed 1000 ms minimum does not impose a second 1000 ms minimum on each stage.
The owned worker remains responsible for hard timeout during an indivisible
native numeric operation. Candidate-step and candidate-prediction counts are
distinct; model validation and incumbent moments also consume the existing
planning moment budget.

The function does not create a transaction. The owning service must atomically
persist a complete selected batch against the exact source revision and apply
its existing idempotency, lifecycle, retention, and stale-source rules.

## Verification Plan

`backend/tests/unit/test_bo_augmentation.py` covers a hand-calculable one-factor
MaxPro case, independent direct product scores in two factors, projection
collisions/log overflow, model-free execution, source immutability, deterministic
tie breaks, EI/SD sequencing, observed-location competitiveness, nominal label
renaming, explicit ordinal assumptions, novelty/constraints/minimum distance,
timeouts/evaluation budgets, and strict invalid-input rejection.

These tests use synthetic already-evaluated candidate rows to isolate selection
semantics. They do not stand in for fit quality, service/source-hash integration,
UI/manual editing, transaction rollback, browser, or installed-archive tests.

## Focused Execution Evidence

On Windows/Python 3.10.11 with BLAS/OpenMP threads 1 and the worktree backend on
`PYTHONPATH`:

- Three new adapter regressions first failed: deadline-expired validation still
  processed all four rows; Confirm unnecessarily raised Beta precision error;
  version 2 was not recognized by the adapter.
- The same three tests passed after the focused changes.
- `test_bo_augmentation.py`, `test_bo_augmentation_view.py`,
  `test_bo_candidate_points.py`, and `test_bo_planning_model.py` then passed:
  108 tests in 7.01 s, process exit 0. The planning tests include an actual synthetic
  fitted snapshot, but are not HTTP/browser verification.
- Final focused run of the same four files: 118 passed in 6.06 s, process exit 0.
  Includes typed version 1/version 2 exact serialization, four response models,
  global importance rescaling, and extreme representable/unrepresentable
  response-unit ratios.
- Ruff check and format-check passed on the seven touched Python files.
  Focused mypy passed on five source files after fixing one context-list type
  inference error. Full service, browser and archive checks are separate.

The hand reference for response uncertainty uses scales 2/10, weights .25/.75,
and raw latent SD 4/30: the independent expected value is `sqrt(7.75)`. Tests also
cover response-order/unit changes, malformed identities/scales/weights, and
unchanged version 1 behavior. No private workshop observations are used.
