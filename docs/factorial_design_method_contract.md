# DOE Factorial Design and Analysis Contract

Last updated: 2026-07-15

## Scope and Versions

`doe.factorial_design` is available through dedicated DOE APIs rather than the
generic analysis-run endpoint.

- Method version: `0.3.0`.
- Design manifest schema: `1`.
- Analysis envelope schema: `2`.
- Analysis config schema: `2`.
- Analysis result schema: `1`.
- Response revision schema: `1`.
- SQLite metadata schema: `10`.

Version `0.3.0` keeps the v0.2.0 calculations/result schema and adds an exact
immutable response revision ID/number/SHA dependency to analysis config,
envelope, DB relation, restore, report, and UI. The
method version is read from `METHOD_VERSIONS`; the design service, analysis
service, catalog, stored record, API envelope, UI, and this document must agree.

Implemented:

- 2-level full factorial design generation for 2 to 6 continuous factors.
- Replicates, center points, fixed blocks, deterministic randomization seed,
  standard order, and run order.
- Immutable design/version/run metadata and canonical `design_sha256`.
- Complete numeric response revisions stored against immutable run IDs, with
  current/history identity and no in-place overwrite.
- `-1/+1` factorial coding and center-point coding at `0`.
- Main effects and interactions through the selected maximum order, with all
  lower-order terms retained to enforce hierarchy.
- OLS coefficients, factorial effects (`effect = 2 * coefficient`), confidence
  intervals, partial drop-one sums of squares, model ANOVA, and ranked effects.
- Center-point curvature and block fixed effects when present.
- Pure-error and lack-of-fit decomposition when replication permits it.
- Residual, leverage, Cook's distance, Durbin-Watson, Shapiro-Wilk, Q-Q,
  main-effect, and interaction plot payloads.
- Persisted checksum-validated analysis restore and an HTML report containing
  the verified design, response, effects, ANOVA, diagnostics, warnings, and
  runtime/build provenance.
- Workbench response entry, analysis controls, effect/main-effect charts,
  term/ANOVA tables, and diagnostic summary. The response lock policy is shown
  before analysis; analyzed and historical revisions are read-only until the
  user explicitly starts `새 revision으로 수정`.

Out of scope:

- Automatic term selection or a quiet switch to another model.
- Fractional factorial alias analysis, Plackett-Burman, and general factorial.
- CCD, Box-Behnken, RSM, contour/surface plots, and response optimization.
- Chart image export and any claim of causal effects or a guaranteed optimum.

## Dedicated API

Design and response routes:

```http
POST /api/v1/doe-designs/factorial
GET  /api/v1/doe-designs/{design_id}
PUT  /api/v1/doe-designs/{design_id}/responses
GET  /api/v1/doe-designs/{design_id}/responses
POST /api/v1/doe-designs/{design_id}/response-revisions
GET  /api/v1/doe-designs/{design_id}/response-revisions
GET  /api/v1/doe-designs/{design_id}/response-revisions/{response_revision_id}
POST /api/v1/doe-designs/{design_id}/response-revisions/{response_revision_id}/abandon
GET  /api/v1/doe-designs/{design_id}/report.html
```

The design request accepts `name`, 2 to 6 `factors`, `replicates`,
`center_points`, `randomize`, `randomization_seed`, and `block_count`. A response
upsert must provide exactly one finite numeric value for every persisted
`run_order`. Once a successful analysis marks the design `analyzed`, response
mutation through `PUT` is rejected. Corrections use an explicit new revision
whose `supersedes_response_revision_id` must equal the current revision. Older
revisions and analyses remain immutable.

Analysis routes:

```http
POST /api/v1/doe-designs/{design_id}/analyses
GET  /api/v1/doe-designs/{design_id}/analyses/{analysis_id}
```

Create request:

- `response_name`: an existing complete response stream.
- `response_revision_id`: optional current-selection shortcut for backward
  compatibility; the resolved completed revision is always persisted.
- `max_interaction_order`: `1` to `min(3, factor_count)`.
- `confidence_level`: finite value strictly between 0 and 1, default `0.95`.
- `point_limit`: diagnostic point cap from 1 to 256.

The generic `POST /api/v1/analysis-runs` endpoint continues to reject this
method with `analysis_method_uses_dedicated_api`.

## Calculation Policy

- The intercept and every factorial term through `max_interaction_order` are
  fitted together. Hierarchy is mandatory and automatic term selection is off.
- Blocks use treatment-coded fixed effects. A center indicator estimates
  curvature when center points exist.
- Rank-deficient or constant-response models fail explicitly. There is no
  automatic factor removal, pooling, method substitution, or fabricated result.
- A saturated model returns estimable coefficients/effects but reports null
  standard errors, confidence intervals, F statistics, and p-values with a
  stable warning.
- Pure error groups observations at identical coded factor points and blocks.
  Lack-of-fit inference is returned only when both pure-error and lack-of-fit
  degrees of freedom exist.
- Plot payload limits affect displayed diagnostic points only; fit and summary
  statistics always use the full stored response series.

## Persistence and Integrity

SQLite schema v10 adds immutable revision/value/head tables and the
analysis-to-revision relation. Each new analysis stores:

- analysis ID and immutable design-version dependency;
- response revision ID/number/name and canonical response revision SHA-256;
- method ID/version, config JSON, result JSON, and result SHA-256;
- created time and app version.

Restore and report paths verify the design checksum, stored result checksum,
method/version, design/version IDs, revision ID/number/name/SHA, config
dependencies, relation SHA, and the historical revision's ordered values. A
newer current revision does not invalidate an older analysis. A mismatch
returns an explicit 409 error.
No absolute path, original filename, raw workspace location, or external data
transfer is part of this contract.

The result envelope also records Python version, platform, optional build commit,
and NumPy/SciPy versions through the common runtime/build provenance helper.

## Reference Validation

- `doe_factorial_design_reference.json` directly checks the official
  NIST/SEMATECH `2^3` Yates standard order and coded/actual levels. Seeded
  randomization, blocks, and the app checksum remain documented app conventions.
- `doe_factorial_analysis_nist_reference.json` checks the NIST published eight
  responses and all saturated `2^3` coefficients. Factorial effects are twice
  the corresponding coefficients. The saturated reference deliberately has no
  residual inference.
- Hand-check tests cover hierarchy, effect scaling, reduced-model lack of fit,
  plot/diagnostic limits, constant response, and invalid center coding.
- API tests cover persistence/restore, method-version alignment, runtime/package
  provenance, response dependency hashing, result/config relationship tamper,
  report rendering, and internal-path non-exposure.

Primary references:

- NIST/SEMATECH Yates order:
  <https://www.itl.nist.gov/div898/handbook/eda/section3/eda35i.htm>
- NIST factorial effects example:
  <https://www.itl.nist.gov/div898/handbook/pri/section6/pri615.htm>
- NIST lack-of-fit decomposition:
  <https://www.itl.nist.gov/div898/handbook/pmd/section4/pmd446.htm>

## Stable Errors and Warnings

Design/response errors retain the existing `doe_design_*`, `doe_response_*`,
and `doe_factorial_*` codes. Analysis adds:

- `doe_response_revision_not_found`
- `doe_response_revision_state_invalid`
- `doe_response_revision_run_set_mismatch`
- `doe_response_revision_checksum_mismatch`
- `doe_response_revision_dependency_mismatch`
- `doe_response_revision_conflict`
- `doe_response_revision_already_closed`

- `doe_factorial_analysis_not_found`
- `doe_factorial_analysis_response_not_found`
- `doe_factorial_analysis_response_incomplete`
- `doe_factorial_analysis_response_metadata_invalid`
- `doe_factorial_analysis_method_mismatch`
- `doe_factorial_analysis_checksum_mismatch`
- `doe_factorial_analysis_metadata_invalid`
- `doe_factorial_analysis_dependency_mismatch`
- `doe_factorial_analysis_response_mismatch`
- `doe_factorial_analysis_factors_invalid`
- `doe_factorial_interaction_order_invalid`
- `doe_factorial_response_variance_zero`
- `doe_factorial_model_rank_deficient`

Warnings include saturated inference unavailable, small residual degrees of
freedom, excluded higher-order interactions, unavailable pure error/lack of fit,
included block fixed effects, and influential points.

## Validation Requirements

- Migration tests cover v8-to-v9 and v9-to-v10 response backfill/round trips.
- Domain and independent-reference tests must use explicit tolerances.
- API/OpenAPI/frontend contract tests must keep method and schema versions aligned.
- Browser E2E must retain design creation, response entry, analysis execution,
  effect/ANOVA rendering, and report download without fake values.
