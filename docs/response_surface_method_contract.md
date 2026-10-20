# Response Surface Method Contract

Last updated: 2026-10-21

## Scope

`doe.response_surface` v0.4.0 is an available dedicated-API method for a
Central Composite Design and hierarchical ordinary least-squares response
surface. It does not execute through the generic analysis-run endpoint.

Implemented:

- two to five continuous factors with declared finite `low < high` bounds;
- explicit CCC, CCI and CCF geometry with stored center/scale and bound roles;
  legacy `alpha_mode=rotatable` still means CCI;
- deterministic standard order and optional seeded run-order randomization;
- factorial, axial, and replicated center points;
- immutable design/run persistence and complete immutable response revisions;
- read-only analyzed/history controls, explicit correction to a new revision,
  and a pre-analysis warning that every planned response should be saved;
- linear, linear+squares, linear+two-factor interactions, and full-quadratic
  presets; full quadratic remains the default;
- candidate/forced/excluded policies and explicit strong-hierarchy backward;
- coefficient inference, partial drop-one sums of squares, model ANOVA,
  pure error, lack of fit, and residual/influence diagnostics;
- stationary-point solution and Hessian eigenvalue classification;
- stored default contour geometry and conditional main/interaction bundles;
- source-locked custom plot views from the final basis, with explicit save and
  exact-view managed reports;
- checksum-validated result restore and runtime/build/package provenance;
- a Workbench design, response-entry, model, contour, diagnostics, and bounded
  Response Optimizer UI.

Not implemented in this slice:

- forward/stepwise selection and factorial-style saturated initial pooling;
- independent multi-response objective-builder UI, nonlinear/equality/integer
  constraints, or guaranteed global optimization;
- Box-Behnken, fractional CCD, orthogonal blocking, or sequential augmentation;
- prediction intervals on contour cells;
- refitting, model selection, raw-data loading or CV during plot/report export.

## Versions

| Contract | Version |
| --- | ---: |
| method | `0.4.0` |
| explicit CCD design payload | `3` |
| legacy design payload | `1`, `2` |
| analysis envelope | `3` |
| analysis config | `3` |
| analysis result | `2` |
| response revision | `1` |
| API contract | `25` |
| plot view / geometry schema | `1` |
| SQLite metadata (plot-view asset kind migration) | `23` |

The registry `METHOD_VERSIONS["doe.response_surface"]` is the method-version
source of truth. The reader explicitly dispatches v0.3.0/v0.3.1 to the old
envelope2/result1/config2 and v0.4.0 to envelope3/result2/config3. Existing
artifacts are read without rewriting their bytes or checksums. This does not
claim support for earlier method versions not accepted by the current reader.
Design payload schema 2 corrects only family metadata: new designs store family
`central_composite`, while `alpha_mode=rotatable` or `face_centered` records the
geometry. Because the canonical design payload and SHA include the schema and
family, the design schema was bumped without changing the statistical method.

Legacy schema-1 designs keep family `central_composite_inscribed` and their
original design SHA. Restore accepts that exact legacy pair and preserves its
stored `alpha_mode`, including legacy face-centered records; it does not rewrite
or silently reinterpret them as schema 2. Unknown schema/family combinations
fail with `doe_rsm_design_family_mismatch`.

## Dedicated API

- `POST /api/v1/doe-designs/response-surface`
- `GET /api/v1/doe-designs/response-surface/{design_id}`
- `GET /api/v1/doe-designs/response-surface/{design_id}/term-catalog?term_preset=...`
- `PUT /api/v1/doe-designs/response-surface/{design_id}/responses`
- `GET /api/v1/doe-designs/response-surface/{design_id}/responses`
- `POST /api/v1/doe-designs/response-surface/{design_id}/analyses`
- `GET /api/v1/doe-designs/response-surface/{design_id}/analyses/{analysis_id}`
- `POST /api/v1/doe-designs/response-surface/{design_id}/optimizations`
- `GET /api/v1/doe-designs/response-surface/{design_id}/optimizations/{optimization_id}`
- `POST /api/v1/doe-designs/{design_id}/response-revisions`
- `GET /api/v1/doe-designs/{design_id}/response-revisions`
- `GET /api/v1/doe-designs/{design_id}/response-revisions/{response_revision_id}`
- `POST /api/v1/doe-designs/{design_id}/response-revisions/{response_revision_id}/abandon`
- `GET /api/v1/doe-designs/{design_id}/response-surface-analyses/{analysis_id}/plot-source`
- `POST /api/v1/doe-designs/{design_id}/response-surface-analyses/{analysis_id}/plot-view`
- `GET/POST /api/v1/doe-designs/{design_id}/response-surface-analyses/{analysis_id}/plot-views`
- `GET/DELETE /api/v1/doe-designs/{design_id}/response-surface-analyses/{analysis_id}/plot-views/{asset_id}`

`POST /api/v1/analysis-runs` returns
`analysis_method_uses_dedicated_api` for this method.

## CCD Geometry

For `k` factors, the design contains:

- `2^k` factorial points per factorial replicate;
- `2k` axial points per axial replicate;
- the requested number of center points.

For explicit rotatable CCD, `alpha = (2^k * factorial_replicates /
axial_replicates)^(1/4)` matches the fourth-moment condition. Basic repeats
are one each. CCF uses alpha=1 and is not advertised as rotatable.
All new transforms use `actual = center + scale * coded`:

| Type | Input low/high role | Scale (h = input half-range) |
| --- | --- | --- |
| CCC / circumscribed | factorial cube | h |
| CCI / inscribed | axial | h/alpha |
| CCF / face_centered | cube and axial | h |

CCC preview shows the actual axial extent before explicit confirmation.
Discrete-domain feasibility is checked, never rounded/clamped. No separate
process-limit field is introduced; input bounds must not be mistaken for a
second set of process limits in CCC. Optimizer default search bounds remain
the declared input bounds, not an automatic CCC axial-box expansion.

Legacy schema1/2 generation and checksums retain the original formula:

```text
actual = midpoint + (coded / alpha) * half_range
```

In legacy CCI, axial coded levels `-alpha` and `+alpha` equal the declared actual
bounds. Rotatable factorial points at coded `-1/+1` remain inside those bounds.
This is a central composite inscribed policy and avoids silently generating
runs beyond the declared process region.

Full-cube, one-block, equal single-repeat recommended centers are k=2/3/4/5:
5/6/7/10. They are product recommendations, not statistical minimums. Manual
counts survive factor-count changes; applying the recommendation is explicit.
Historical center counts/runs are never changed on read.

## Response Lifecycle

Responses may be entered while the design is `completed`; each successful
legacy `PUT` creates a completed immutable revision. Running an analysis sets
the design to `analyzed`, and `PUT` continues to reject with 409. The UI keeps
the analyzed revision read-only and exposes `새 revision으로 수정`, which
copies the current values into an editable correction and creates a new
completed revision. The old revision and analysis remain unchanged. Current
and newest-first history show number/state/current/timestamp/SHA metadata.
Selecting a completed historical revision is read-only; fitting a different
model to the same stored revision is allowed. Draft/source edits immediately
invalidate pending completions. Save success is independent of history refresh.

## Quadratic Model

The full-quadratic preset is fit in coded units:

```text
y = b0 + sum(bi*xi) + sum(bij*xi*xj) + sum(bii*xi^2) + error
```

For k=4, parameter counts including intercept are 5/9/11/15 for the four
presets. Optional explicit policies apply before fitting. Backward uses the
shared nested-model partial SS/F engine, but requires positive initial residual
DF and does not pool. A square depends on its main effect; a two-factor product
depends on both mains. Missing/cyclic/duplicate dependencies and conflicting
forced/excluded policies fail. Removed terms do not re-enter. Ties prefer
second-order terms, then later canonical order; trace records the policy.

`none` keeps the specified preset/policies. A rank-deficient matrix is
rejected with `doe_rsm_model_rank_deficient`. A constant response is rejected
with `doe_rsm_response_variance_zero`.

The result reports N, parameter count, matrix rank, residual degrees of freedom,
SSE, model/total SS, residual standard error, R-squared, adjusted R-squared,
overall F/p, coefficient SE/t/p/95% CI, and partial drop-one term SS/F/p. Partial
term sums of squares are not claimed to add to the model sum of squares.
The stored final basis includes ordered factor names, term IDs, exponent
vectors, coefficients/covariance, residual DF/MSE and coding. Selection trace,
PRESS and predicted R-squared describe that final basis. The source envelope
records response revision/hash. Prediction evaluation never parses a label.
Stationary points use absent term coefficients as zero; a singular Hessian
returns unavailable with reason, not a pseudo-inverse optimum. Bounded
optimization remains a separate operation. No RSM `effect=2*coefficient`
interpretation is introduced. Post-selection inference is exploratory.

## Pure Error And Diagnostics

Pure error groups identical coded design points. Lack-of-fit degrees of freedom
are `unique design points - model rank`. Lack-of-fit inference is returned only
when both lack-of-fit and replicated pure-error degrees of freedom exist; no
statistic is fabricated when the pure-error mean square is zero.
Physical replication uses all design settings (and blocks where supported),
not just retained terms. SS/DF decomposition and valid F/p availability are
separate. Reasons include no replicated points, no LoF DF, zero pure-error
variance and numerical decomposition failure. Only roundoff-scale negative
SSE-minus-PE SS is clamped; material negative differences fail decomposition.

Diagnostics include residual/fitted values, standardized residuals, leverage,
Cook's distance, Durbin-Watson, Shapiro-Wilk where supported, and Q-Q points.
Randomization and independence remain design assumptions the application cannot
prove.

## Stationary Point And Contour

The stationary point solves the fitted gradient using the quadratic Hessian.
Positive Hessian eigenvalues classify a minimum, negative eigenvalues a maximum,
and mixed signs a saddle. A singular Hessian produces `indeterminate` with no
invented coordinates.

The result separately states whether the stationary point is inside the axial
design bounds and inside the `[-1, +1]` factorial cube. The point is a model
diagnostic, not an optimizer recommendation.

The legacy `contour` payload remains readable with its first-pair/cube/center
policy. New `plot_bundle` is the separately identified default first-pair view
over declared actual input bounds, with other factors held at their centers.
`plot_overview` stores every main and pair conditional curve. Neither is a
factorial marginal mean. Actual/coded coordinates use the saved center/scale.

Custom settings select contour/main/interaction, factor identities, all remaining
actual hold values, actual/coded axes, odd grid11..51 and 2..11 ordered finite
thresholds (or count). ContourPy1.3.2 serial Separate/OuterOffset geometry preserves
outer rings and holes. JSON contains no Infinity or library arrays. A constant
surface has one filled region, no artificial isolines. Vertex budget is200,000.
The full design convex hull is intersected with the held slice; outside regions
are hatched. Overlay distinguishes actual on-slice points from projections.

Source requests contain the exact analysis result SHA and response revision/SHA.
Explicit save also requires the view SHA seen by the user. The server evaluates
the verified final basis, never accepts client HTML/geometry. Stored views are
immutable `plot_view` assets in existing DOE storage; descriptors are listed
without geometry, and selected geometry is fetched by ID. Managed report source
references include the view ID/hash. Export reads stored geometry only, with
default versus custom view identified visibly. Existing absent-view source hashes
are unchanged. Asset insertion/deletion is atomic with owner/hash dependencies.

No source dataset, response or old model is rewritten. Migration23 preserves all
existing asset BLOBs/hashes while adding the new kind constraint. A previous
metadata22 binary must not open a migrated23 workspace. Restore a verified old
backup to a new location when reverting code; keep the current workspace intact.

After a verified RSM fit, the same panel can run
`doe.response_optimizer` with maximize/minimize/target/range
desirability, narrower factor bounds, optional linear constraints, and explicit
search budgets. The optimizer is a separate method/result contract documented
in `docs/response_optimizer_contract.md`; it does not change stored RSM
coefficients or reinterpret its stored result.

The top-level optimizer is listed directly after RSM in the DOE module. The
same `ResponseOptimizerPanel` and typed DOE API are used from both entrypoints.
Stored `regression.response_optimizer` v0.3.0 results remain restorable without
changing their method ID or checksum.

## Persistence And Provenance

Schema-v10 DOE tables store design/runs, normalized immutable response
revisions/values/current heads, analysis records, and analysis-revision
relations. Restore verifies:

- method ID and registry method version;
- design family, current version, run count, and design checksum;
- config/result design IDs, design version ID, design SHA, response revision
  ID/number/name/SHA, and relation SHA;
- result checksum and the selected historical revision's ordered-value SHA.

The result envelope records app, Python, platform, build commit, NumPy, SciPy,
design ID/version/SHA, response revision ID/number/SHA/name, method ID/version,
and creation time.
No workspace path, original filename, or unrelated row value is exposed.

## Stable Errors

- `doe_rsm_factor_count_out_of_range`
- `doe_rsm_factor_names_not_unique`
- `doe_rsm_factor_range_invalid`
- `doe_rsm_center_points_invalid`
- `doe_rsm_run_count_exceeds_limit`
- `doe_rsm_design_checksum_mismatch`
- `doe_rsm_design_family_mismatch`
- `doe_rsm_response_run_set_mismatch`
- `doe_rsm_analysis_response_not_found`
- `doe_rsm_contour_grid_size_invalid`
- `doe_rsm_response_variance_zero`
- `doe_rsm_model_rank_deficient`
- `doe_rsm_analysis_checksum_mismatch`
- `doe_rsm_analysis_dependency_mismatch`
- `doe_rsm_analysis_response_mismatch`

## Independent Reference

`backend/tests/reference/fixtures/doe_response_surface_nist_reference.json`
records the small published NIST/SEMATECH CCI Uniformity example and its full
quadratic coefficient, residual standard error, R-squared, adjusted R-squared,
F, and p-value outputs:

<https://www.itl.nist.gov/div898/handbook/pri/section4/pri473.htm>

The rotatable alpha formula is independently checked against the NIST CCD
definition:

<https://www.itl.nist.gov/div898/handbook/pri/section3/pri3361.htm>

Application-specific bounded CCI scaling, checksum, persistence, randomization,
stationary-point, and contour policies are explicitly tested but are not
attributed to NIST.
