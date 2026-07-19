# Response Optimizer Contract

Last updated: 2026-07-18

## Scope

`regression.response_optimizer` v0.3.0 optimizes one or more checksum-validated
`doe.response_surface` full-quadratic models over their shared declared factor
region. It is catalog-available with `execution_mode=dedicated` through both
the RSM panel and `/analysis/regression/regression.response_optimizer`. It does
not execute through generic `POST /api/v1/analysis-runs`.

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
- typed source-model eligibility with blocking, acknowledgment-required, and
  informational issues;
- exact acknowledgment-code persistence in request, config, result, and result
  envelope when an advisory model diagnostic is accepted;
- a single-current-response objective UI shared by `ResponseSurfacePanel` and
  the top-level dedicated workspace;
- a paged metadata-only stored RSM analysis catalog with eligibility summaries.

Not implemented:

- a claim or proof of global optimality;
- arbitrary nonlinear, equality, integer, or categorical-factor constraints;
- prediction intervals or uncertainty-aware desirability;
- automatic model/term selection or silent fallback to another algorithm;
- a multi-response objective builder in the UI;
- confirmation experiments, ridge analysis, Bayesian Optimization, or process
  control after applying a recommendation.

## Versions

| Contract | Version |
| --- | ---: |
| method | `0.3.0` |
| optimizer config | `2` |
| optimizer result | `2` |
| source RSM result | `1` |
| source bundle | `2` |
| SQLite metadata | `10` |

`METHOD_VERSIONS["regression.response_optimizer"]` is the only method-version
source. The first persisted contract was v0.1.0/schema 1. Typed eligibility and
acknowledgment fields change persisted semantics, so the current contract is
v0.2.0 with config/result schema 2. Version 0.3.0 keeps those optimizer schemas
and calculations, but source bundle schema 2 now includes each RSM analysis's
explicit response revision ID/number/SHA. Older optimizer records are not
silently assigned the new version or migrated. Schema 10 stores the source RSM
analysis-to-revision relation; optimizer records remain keyed by source
analysis IDs and a source bundle SHA.

## Dedicated API

- `POST /api/v1/doe-designs/response-surface/{design_id}/optimizations`
- `GET /api/v1/doe-designs/response-surface/{design_id}/optimizations/{optimization_id}`
- `GET /api/v1/doe-designs/response-surface-analyses?limit=20&offset=0`

The catalog method is available/dedicated. Generic analysis-run requests return
`analysis_method_uses_dedicated_api` and cannot create a fake run. Catalog rows
exclude response/run values and paths; selecting one uses the existing full
design/analysis GETs before rendering `ResponseOptimizerPanel`. ID-only
`design_id` and `analysis_id` query fields restore source selection.

This entrypoint/catalog-only change keeps method `0.3.0`, config/result schema
`2`, and source-bundle schema `2`; optimizer calculation and stored semantics
are unchanged.

## Source Validation

Every objective references a stored RSM `analysis_id`. Before calculation and
again on restore, the service validates:

- source analysis existence, method ID, registry version, and result checksum;
- source design ID/version/SHA and the exact historical response revision
  ID/number/SHA used by that analysis;
- source config/result relationship and full typed result schema;
- identical ordered factor names, actual low/high bounds, and axial coding;
- a source bundle SHA containing each analysis/result/response dependency.

Creating a newer current response revision does not mutate or invalidate an
older source analysis/optimizer. Tampering with the selected historical
revision, relation, source, config, result, or checksum blocks restore. Errors
do not expose workspace paths or unrelated response values.

## Source-Model Eligibility

Eligibility is evaluated from the checksum-validated RSM result before search
and recomputed during restore.

- Blocking: dependency/checksum failure, invalid rank, saturated/no-residual-
  inference model, zero or unusable residual variance, significant lack of fit
  when the test is available, or an invalid/incomplete response dependency.
- Acknowledgment required: residual df below 5, influential runs, high leverage,
  large standardized residuals, or severe residual-normality diagnostics.
- Informational: associational model interpretation, contour-slice limitations,
  confirmation-run requirement, and absence of a global-optimum guarantee.

Blocking issues return `response_optimizer_source_model_ineligible` and no
recommendation. Advisory issues require the request to contain exactly the
current acknowledgment-required codes. Missing or unknown acknowledgments are
rejected; accepted codes and the complete typed issue list are stored in the
config/result/envelope. The frontend mirrors the classification for early UX,
but backend validation remains authoritative.

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

## Dedicated Restore And Catalog Policy

The shared `ResponseOptimizerPanel` is used by both the RSM parent and the
top-level dedicated optimizer. After execution the top-level route stores only
`design_id`, `analysis_id`, and `optimization_id` in the URL. Reload uses the
existing checksum-validated optimization GET and accepts the result only when
its design/version and single source analysis match the selected RSM source.
It never reruns the optimizer. Dedicated optimizer routes omit unrelated
dataset-scoped generic history/export controls.

The RSM catalog uses pages of 20 and currently restores/verifies each item to
derive eligibility. This is intentionally conservative. A future measured
slice may add a lightweight verified summary/index, search/filter, exact-ID
lookup, and hundreds-item benchmarks, but full dependency/checksum validation
remains mandatory when a source is selected.

These restore and navigation changes retain method `0.3.0`, config/result
schemas 2/2, and source-bundle schema 2.

## Stable Errors

- `response_optimizer_source_analysis_missing`
- `response_optimizer_source_analysis_invalid`
- `response_optimizer_source_analysis_duplicate`
- `response_optimizer_source_model_ineligible`
- `response_optimizer_source_model_acknowledgment_required`
- `response_optimizer_source_acknowledgment_invalid`
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
