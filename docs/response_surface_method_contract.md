# Response Surface Method Contract

Last updated: 2026-07-15

## Scope

`doe.response_surface` v0.2.0 is an available dedicated-API method for a
Central Composite Design and a full quadratic ordinary least-squares response
surface. It does not execute through the generic analysis-run endpoint.

Implemented:

- two to five continuous factors with declared finite `low < high` bounds;
- rotatable central composite inscribed geometry and face-centered CCD geometry,
  represented by the common `central_composite` family plus `alpha_mode`;
- deterministic standard order and optional seeded run-order randomization;
- factorial, axial, and replicated center points;
- immutable design/run persistence and complete immutable response revisions;
- read-only analyzed/history controls, explicit correction to a new revision,
  and a pre-analysis warning that every planned response should be saved;
- full quadratic OLS with all main, two-factor interaction, and squared terms;
- coefficient inference, partial drop-one sums of squares, model ANOVA,
  pure error, lack of fit, and residual/influence diagnostics;
- stationary-point solution and Hessian eigenvalue classification;
- a 21x21 two-factor contour payload over the factorial cube;
- checksum-validated result restore and runtime/build/package provenance;
- a Workbench design, response-entry, model, contour, diagnostics, and bounded
  Response Optimizer UI.

Not implemented in this slice:

- automatic/stepwise term selection;
- independent multi-response objective-builder UI, nonlinear/equality/integer
  constraints, or guaranteed global optimization;
- Box-Behnken, fractional CCD, orthogonal blocking, or sequential augmentation;
- prediction intervals on contour cells;
- contour/surface image export or a response-surface HTML report.

## Versions

| Contract | Version |
| --- | ---: |
| method | `0.2.0` |
| current design payload | `2` |
| legacy design payload | `1` |
| analysis envelope | `2` |
| analysis config | `2` |
| analysis result | `1` |
| response revision | `1` |
| SQLite metadata | `10` |

The registry `METHOD_VERSIONS["doe.response_surface"]` is the method-version
source of truth. The calculation and analysis result remain schema 1. Method
v0.2.0 identifies the new persisted response revision ID/number/SHA dependency;
it does not change the quadratic formulas.
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

`POST /api/v1/analysis-runs` returns
`analysis_method_uses_dedicated_api` for this method.

## CCD Geometry

For `k` factors, the design contains:

- `2^k` factorial points per factorial replicate;
- `2k` axial points per axial replicate;
- the requested number of center points.

The rotatable distance is `alpha = (2^k)^(1/4)`. Face-centered CCD uses
`alpha = 1`. The request `low` and `high` values are hard actual design bounds,
not the coded factorial levels. Conversion is:

```text
actual = midpoint + (coded / alpha) * half_range
```

Therefore axial coded levels `-alpha` and `+alpha` equal the declared actual
bounds. Rotatable factorial points at coded `-1/+1` remain inside those bounds.
This is a central composite inscribed policy and avoids silently generating
runs beyond the declared process region.

## Response Lifecycle

Responses may be entered while the design is `completed`; each successful
legacy `PUT` creates a completed immutable revision. Running an analysis sets
the design to `analyzed`, and `PUT` continues to reject with 409. The UI keeps
the analyzed revision read-only and exposes `새 revision으로 수정`, which
copies the current values into an editable correction and creates a new
completed revision. The old revision and analysis remain unchanged. Current
and newest-first history show number/state/current/timestamp/SHA metadata.

## Quadratic Model

The stored response is fit in coded units with the complete hierarchy-fixed
second-order model:

```text
y = b0 + sum(bi*xi) + sum(bij*xi*xj) + sum(bii*xi^2) + error
```

No term is silently selected, removed, or replaced. A rank-deficient matrix is
rejected with `doe_rsm_model_rank_deficient`. A constant response is rejected
with `doe_rsm_response_variance_zero`.

The result reports N, parameter count, matrix rank, residual degrees of freedom,
SSE, model/total SS, residual standard error, R-squared, adjusted R-squared,
overall F/p, coefficient SE/t/p/95% CI, and partial drop-one term SS/F/p. Partial
term sums of squares are not claimed to add to the model sum of squares.

## Pure Error And Diagnostics

Pure error groups identical coded design points. Lack-of-fit degrees of freedom
are `unique design points - model rank`. Lack-of-fit inference is returned only
when both lack-of-fit and replicated pure-error degrees of freedom exist; no
statistic is fabricated when the pure-error mean square is zero.

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

The contour payload uses the first two factors over the factorial cube. For
three or more factors, all remaining coded factors are fixed at zero and a
persistent warning records that slice policy.

After a verified RSM fit, the same panel can run
`regression.response_optimizer` with maximize/minimize/target/range
desirability, narrower factor bounds, optional linear constraints, and explicit
search budgets. The optimizer is a separate method/result contract documented
in `docs/response_optimizer_contract.md`; it does not change RSM v0.2.0
coefficients or reinterpret its stored result.

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
