# Response Optimizer Contract

Last updated: 2026-07-14

## Scope

`regression.response_optimizer` v0.1.0 optimizes one or more checksum-validated
`doe.response_surface` full-quadratic models over their shared declared factor
region. It is implemented through dedicated response-surface APIs and the RSM
panel; it does not execute through generic `POST /api/v1/analysis-runs` and no
independent Response Optimizer page is provided.

Implemented:

- maximize, minimize, target-is-best, and in-range objectives;
- Derringer-Suich individual desirability with lower/upper shape exponents;
- importance-weighted geometric composite desirability;
- one to eight source RSM analyses with an identical design version and factor
  space in the backend contract;
- optional narrower per-factor bounds inside the declared axial design bounds;
- optional linear `<=` or `>=` constraints in actual factor units;
- seeded candidate generation and bounded SLSQP multi-start refinement;
- explicit candidate, multi-start, iteration, evaluation, and wall-time budgets;
- stored config/result/source-bundle checksums and runtime/build provenance;
- a single-current-response objective UI in `ResponseSurfacePanel`.

Not implemented:

- a claim or proof of global optimality;
- arbitrary nonlinear, equality, integer, or categorical-factor constraints;
- prediction intervals or uncertainty-aware desirability;
- automatic model/term selection or silent fallback to another algorithm;
- an independent model catalog or multi-response objective builder in the UI;
- confirmation experiments, ridge analysis, Bayesian Optimization, or process
  control after applying a recommendation.

## Versions

| Contract | Version |
| --- | ---: |
| method | `0.1.0` |
| optimizer config | `1` |
| optimizer result | `1` |
| source RSM result | `1` |
| SQLite metadata | `9` |

`METHOD_VERSIONS["regression.response_optimizer"]` is the only method-version
source. The registry ID previously produced no result, so its first persisted
contract starts at `0.1.0`; this is not a reinterpretation of an older result.
Schema-v9 `experiment_design_analyses` already stores method ID/version,
config/result JSON, result SHA, and dependency SHA, so no migration is needed.

## Dedicated API

- `POST /api/v1/doe-designs/response-surface/{design_id}/optimizations`
- `GET /api/v1/doe-designs/response-surface/{design_id}/optimizations/{optimization_id}`

The generic method remains disabled with guidance that optimization is
available after fitting a model in the Response Surface Method screen.

## Source Validation

Every objective references a stored RSM `analysis_id`. Before calculation and
again on restore, the service validates:

- source analysis existence, method ID, registry version, and result checksum;
- source design ID/version/SHA and current response-series SHA;
- source config/result relationship and full typed result schema;
- identical ordered factor names, actual low/high bounds, and axial coding;
- a source bundle SHA containing each analysis/result/response dependency.

Changing current response data or tampering with a source, config, result, or
checksum blocks restore. Errors do not expose workspace paths or response
values beyond the aggregate model result already selected by the user.

## Desirability

Let `L`, `T`, and `U` be the unacceptable lower, fully desirable target, and
unacceptable upper values. Maximize uses `L < T`; minimize uses `T < U`;
target uses `L < T < U`; range uses `L < U`. Shape exponents must be positive.

Individual desirability is in `[0, 1]`. For multiple objectives, importance
weights `w_i > 0` produce:

```text
D = exp(sum(w_i * log(d_i)) / sum(w_i))
```

If any `d_i` is zero, `D` is zero. This follows the NIST/SEMATECH description
of the Derringer-Suich approach. In-range desirability is one inside the closed
range and zero outside it.

## Region, Constraints, And Search

Default search bounds equal the RSM declared axial actual bounds. User bounds
may only narrow that region. Linear constraints are evaluated in actual factor
units and must contain at least one nonzero finite coefficient.

The algorithm evaluates the center, region corners, and seeded random
candidates, then refines the best feasible starts with bounded SLSQP. It uses a
single process and does not add worker or parallel dependencies. The result
records seed, requested budgets, actual evaluation/iteration counts, elapsed
time, successful local starts, and one termination reason:

- `search_completed`
- `evaluation_budget`
- `time_budget`

Reaching a declared budget returns the best verified feasible point with a
persistent budget warning. It never switches algorithms silently. No result is
described as the guaranteed global optimum.

## Result And Provenance

The result stores design/search bounds, configured constraints, objective
definitions, recommended actual/coded coordinates, predicted response and
individual desirability per objective, composite desirability, constraint
slack/status, search diagnostics, and persistent warnings. The envelope stores
source analysis IDs, source bundle SHA, config SHA, design ID/version/SHA,
method/result/config versions, app/Python/platform/build/package versions, and
creation time.

Every result warns that point predictions omit uncertainty, source model
adequacy must be reviewed, a confirmation experiment is required, and global
optimality is not guaranteed.

## Stable Errors

- `response_optimizer_source_analysis_missing`
- `response_optimizer_source_analysis_invalid`
- `response_optimizer_source_analysis_duplicate`
- `response_optimizer_factor_space_mismatch`
- `response_optimizer_objective_thresholds_invalid`
- `response_optimizer_factor_bound_invalid`
- `response_optimizer_linear_constraint_invalid`
- `response_optimizer_no_feasible_point`
- `response_optimizer_search_budget_invalid`
- `response_optimizer_checksum_mismatch`
- `response_optimizer_dependency_mismatch`
- `response_optimizer_source_bundle_mismatch`
- `response_optimizer_result_config_mismatch`

## Independent Reference

`backend/tests/reference/fixtures/response_optimizer_nist_reference.json`
records the published NIST/SEMATECH four-response tire-tread example, fitted
response equations, objective limits, rounded best coded coordinates, four
individual desirabilities, and composite desirability:

<https://www.itl.nist.gov/div898/handbook/pri/section5/pri5322.htm>

The handbook publishes rounded coefficients and results, so the test uses
explicit coordinate and desirability tolerances. Separate hand tests verify
all four objective types, weighted geometric composition, a known bounded
quadratic maximum, linear constraints, invalid thresholds, infeasible regions,
and deterministic evaluation-budget termination.
