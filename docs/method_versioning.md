# Method Versioning Policy

This policy explains when a stable `method_id` in `METHOD_VERSIONS` should
receive a method-version bump. `regression.predict` is `0.2.0`,
`doe.factorial_design` and `regression.response_optimizer` are `0.3.0`, and
`doe.response_surface` is `0.2.0`. `doe.bayesian_optimization` is `0.2.2`, and
`quality.attribute_control_chart` is `0.3.0`; the other stable IDs remain on
`0.1.0`.

## Source Of Truth

- `backend/app/analyses/registry.py` owns the `METHOD_VERSIONS` map.
- The analysis method catalog and `MethodExecutionHandler` specs must read from
  that same map.
- Dedicated services, including regression prediction, must call the registry
  accessor instead of defining a second version string.
- Tests must assert that every stable method ID has a version entry and that
  catalog, handler/service, DB run, dedicated analysis record, result envelope, and provenance versions
  agree where those records exist.

## Patch Version

Use a patch bump when the same statistical contract is preserved and existing
stored results remain comparable:

- typo or label-only metadata correction in a result field;
- warning wording change with the same machine-readable warning code;
- frontend display or panel layout change only;
- documentation clarification with no result schema or calculation change;
- test-only fixture expansion that confirms the same formulas and output fields.

Frontend-only changes do not require a method-version bump unless they alter the
request sent to the backend or reinterpret a stored result field.

Changing `regression.predict` and `regression.response_optimizer` catalog
availability from disabled to available/dedicated, adding metadata-only source
catalogs, and adding top-level ID-restorable UI entrypoints do not change either
calculation request or persisted result meaning. Their versions therefore stay
`0.2.0` and `0.3.0`; prediction schemas remain result/config/rows `2`/`3`/`2`,
and optimizer config/result/source-bundle schemas remain `2`/`2`/`2`.

The Workbench saved-result hooks (`history`, `export`, `comparison`, and
`restore`) use latest-request guards and pass their state through grouped props.
Ignoring an obsolete response, keeping loading state owned by the latest
request, or removing the duplicate field-by-field prop fallback preserves the
backend request and stored-result contracts, so this stabilization does not
require a method-version bump.

## Frontend API Type Drift

The frontend typed client now keeps manually maintained API types under
`frontend/src/api/types/`:

- `common.ts`
- `datasets.ts`
- `analyses.ts`
- `analysisResultsExploration.ts`
- `analysisResultsCategorical.ts`
- `analysisResultsRegression.ts`
- `analysisResultsQuality.ts`
- `analysisResultsHypothesis.ts`
- `analysisRuns.ts`
- `analysisExports.ts`
- `doe.ts`
- `regression.ts`

`frontend/src/api.ts` remains the public client and re-exports those types so
existing imports from `./api` continue to work. This reduces merge conflicts and
makes schema review more explicit, but it is still manual and does not replace a
generated OpenAPI contract.

`analyses.ts` keeps the method catalog, run request/filter, provenance/warning,
and the result envelope.
`analysisResultsExploration.ts` owns exploratory analysis result types
(`eda.descriptive`, `eda.graphical_summary`, `eda.normality`, and
`eda.equal_variances`). `analysisResultsCategorical.ts` owns categorical result
types (`categorical.one_proportion`, `categorical.two_proportion`, and
`categorical.chi_square_association`). `analysisResultsRegression.ts` owns
correlation and regression result types (`regression.pearson`,
`regression.xy_correlation`, and `regression.linear_model`).
`analysisResultsQuality.ts` owns quality result and preflight types
(`quality.attribute_control_chart`, `quality.individuals_chart`,
`quality.subgroup_chart`, `quality.run_chart`,
`quality.capability`, `quality.gage_rr`, `quality.gage_run_chart`, and the Gage
R&R balanced-crossed preflight contract). `analysisResultsHypothesis.ts` owns
hypothesis-test result types (`hypothesis.one_sample_t`,
`hypothesis.paired_t`, `hypothesis.two_sample_t`,
`hypothesis.one_way_anova`, `hypothesis.equivalence_tost`,
`hypothesis.one_sample_wilcoxon`, `hypothesis.mann_whitney`, and
`hypothesis.kruskal_wallis`). `analysisRuns.ts` owns saved analysis history and
comparison types. `analysisExports.ts` owns analysis result export response and
export-list types. The public re-export surface remains
`frontend/src/api.ts` and `frontend/src/api/types/index.ts`, so components can
continue importing from `./api`.

The frontend API function implementations are split by domain under
`frontend/src/api/` while `frontend/src/api.ts` remains the public facade:

- `client.ts` for base URL, fetch/error helpers, and browser download helpers.
- `health.ts` for the health endpoint.
- `datasets.ts` for dataset upload/paste/parsing/schema/preview/profile calls.
- `analyses.ts` for analysis method catalog, runs, history, comparison,
  result restore, and export calls.
- `doe.ts` for factorial design calls.
- `regression.ts` for regression model prediction calls.
- `quality.ts` for quality preflight calls.
- `routes.ts` for centralized `/api/v1` endpoint paths, query-key ordering,
  and encoded path IDs. Domain clients call this route map instead of
  constructing endpoint strings inline, which reduces endpoint drift while the
  project still uses manual frontend types.

The backend test `backend/tests/unit/test_openapi_frontend_contract.py` now
checks the `frontend/src/api/routes.ts` surface against the generated FastAPI
OpenAPI schema. It verifies the expected path, HTTP method, path/query
parameters, request media type, success status, and response schema component
for every route currently used by the typed frontend client.

When `frontend/src/api/routes.ts` adds a route, the same change must update
`FRONTEND_ROUTE_CONTRACTS` in
`backend/tests/unit/test_openapi_frontend_contract.py`. This keeps new frontend
API calls from bypassing backend OpenAPI coverage while the project still avoids
introducing a generated TypeScript client.

The contract test also extracts the route function names from
`frontend/src/api/routes.ts` and requires an exact match with
`FRONTEND_ROUTE_CONTRACTS`. If a frontend route helper is added without a
backend OpenAPI operation contract, backend pytest fails. A companion boundary
guard checks that frontend API domain modules do not embed direct `/api/v1`
endpoint literals outside the centralized route map.

The same test also checks a high-value subset of schema component fields used by
the frontend typed client: required field subsets, enum values, const values,
direct schema refs, and array item refs for health, dataset preview/version,
analysis method catalog, analysis history, stored result envelope, provenance,
warnings, and export list schemas.

The contract test also reads the frontend result type files and checks that
their `summary_type` string literals match the backend
`MethodExecutionHandlerSpec.result_summary_type` values. The guard is
file-owned by result family, so moving or adding result payload types requires
updating the corresponding expected summary-type set. `quality.gage_rr`
preflight is tracked as a non-analysis-run result summary type because it uses
the quality preflight endpoint rather than the generic analysis-run endpoint.

This is a drift guard, not full type generation. It does not prove that every
field inside each TypeScript interface matches Pydantic exactly, and it permits
backend schema additions that do not remove or rename frontend-used fields. Next
schema-stability work should add OpenAPI type generation or a deeper schema
diff that compares the full FastAPI response/request field shapes with
`frontend/src/api/types/*`. A frontend label/layout-only change does not require
a method-version bump; changing request payload semantics, summary-type
semantics, or stored result field interpretation does.

Earlier paged row retrieval and the dedicated
`regression_prediction_csv_export` format were additive storage/access changes
that preserved the `0.1.0` result interpretation. The 2026-07-14 dependency
stabilization changes required persisted provenance and cross-artifact identity
fields, so `regression.predict` receives a minor bump to `0.2.0` under the rule
below. Its prediction result schema is `2`, config schema is `3`, and rows
artifact/header schema is `2`; the unchanged CSV format remains schema `1`.
Older prediction artifacts are not silently migrated.

`doe.factorial_design` received a minor bump from `0.1.0` to `0.2.0` because
the same dedicated method now persists and restores effects, OLS/ANOVA,
pure-error/lack-of-fit, diagnostic, plot, and provenance fields. Its analysis
config and result schemas both start at `1`; SQLite metadata schema v9 stores
the relationship. Earlier v0.1 design/response assets are not rewritten into
analysis results, and no fake migration is performed.

`doe.response_surface` originally remained at `0.1.0` because its design
generation and analysis formulas/results did not change. New design payloads use schema `2`
and generic family `central_composite`, with geometry carried by `alpha_mode`.
Legacy schema `1`/`central_composite_inscribed` payloads retain their original
SHA and are restored verbatim, including face-centered `alpha_mode`; they are
not rewritten. Analysis config/result schemas remain `1`.

`regression.response_optimizer` received a minor bump from `0.1.0` to `0.2.0`.
Source-model eligibility severity, required acknowledgment codes, and their
persistence change the request and stored result contract. Config/result schema
both move from `1` to `2`; v0.1 records are not silently migrated. Schema-v9 DOE
analysis metadata still stores the relationship, so no SQLite migration is
required. The generic analysis-run page remains disabled.

The immutable DOE response revision foundation then requires new minor method
versions: `doe.factorial_design` v0.3.0 and `doe.response_surface` v0.2.0.
Their calculation result schemas remain 1, while analysis envelope/config move
to schema 2 because each record now persists response revision ID, number, and
SHA. `regression.response_optimizer` moves to v0.3.0 with unchanged config/
result schema 2 but source bundle schema 2, because its source dependency now
includes the RSM analysis's exact historical response revision. SQLite schema
10 stores immutable revision/value/head tables plus the analysis-revision
relation. Schema-v9 current response streams are backfilled as deterministic
revision 1 assets without rewriting existing analysis JSON/checksums. Older
method-version records are not silently assigned these versions.

`doe.bayesian_optimization` entered the catalog as planning-only `0.1.0` with
study payload schema 1, observation-history schema 1, and SQLite schema 11.
Those assets had no numerical method result and remain restorable as `0.1.0`;
they are not relabeled.

The first dedicated GP/EI execution slice moves the method to `0.2.0` because
it adds a versioned Matérn-5/2 Gaussian Process calculation, Expected
Improvement search, immutable pending recommendation, and numerical result.
Recommendation config, result, and surrogate-model schemas each start at 1.
SQLite schema 12 adds the recommendation relation and extends trial origin with
`recommendation`. Study/history schemas remain 1 because their payload and hash
semantics are unchanged. The generic analysis-run endpoint remains unavailable
for calculation and directs clients to the dedicated study API.

The following sequential-lifecycle stabilization retains method `0.2.0` and
recommendation config/result/model schemas 1. Rehashed relationship tamper is
rejected more strictly, the reference fixture adds declared multi-seed Branin
regret thresholds, the UI constructs the existing actual-unit linear-constraint
request, and an external benchmark measures the existing worker. None of these
changes alters the GP kernel, EI formula, numerical defaults, persisted field
meaning, canonical hash payload, or compatibility of valid `0.2.0` records.

The lifecycle-correctness stabilization uses patch version `0.2.1` because it
enforces the existing no-duplicate/no-random-fallback contract for abandoned
trial coordinates. It also aligns the backend initial-design minimum, 200
completed/201-history boundary, stranded-study abandonment guard, latest/current
view, request trial budget UI, and public time-budget error. Study/history and
recommendation config/result/model schemas remain 1, SQLite remains schema 13,
and no existing checksum payload is rewritten. Valid `0.2.0` recommendations
remain restorable with their recorded method version; they are not relabeled.
Changing the GP kernel, EI formula, duplicate tolerance, stored coordinate
meaning, or artifact hash payload would require a new minor/schema decision.

The explicit study-close lifecycle uses patch version `0.2.2`. The GP/EI
algorithm, defaults, duplicate policy, study/history schema 1, and
recommendation config/result/model schemas 1 are unchanged. SQLite advances
from schema 13 to 14 to store lifecycle event schema 1 and nullable successor
`predecessor_study_id`. A lifecycle event pins the exact final history and
counts but does not rewrite any earlier checksum payload. Legacy active studies
receive no invented close event, and valid `0.2.0`/`0.2.1` recommendation
artifacts retain their recorded method versions.

The closed-study metadata-deletion slice keeps method `0.2.2`, SQLite schema
14, and every existing Bayesian artifact schema unchanged. Deletion does not
rewrite or reinterpret a surviving statistical artifact. Its preflight and
response are operational API schemas starting at 1, and the canonical deletion
manifest is a confirmation token rather than a stored recommendation/result
schema. A future change that adds file ownership, cascade semantics, retention
timestamps, or restorable trash metadata must make a separate storage/API
schema decision; it does not automatically imply a statistical method bump.

The individual analysis-export deletion slice also keeps every statistical
method version, existing JSON/CSV/HTML/prediction-export schema, and SQLite
schema 14 unchanged. It removes one verified app-created file and its one
metadata ownership row without rewriting the parent result or another export.
Deletion preflight and response are operational schema 1; the manifest and
startup quarantine recovery describe mutation safety, not statistical output
meaning. Full analysis/dataset ownership-graph deletion or restorable trash
would require a separate storage/API schema review.

The earlier scikit-learn spike and dependency-promotion evidence schema is an
external TEMP validation artifact and does not change these method or asset
versions. Windows 11 client validation remains a release gate; it is not a
reason to label the current Windows 10 development evidence as Windows 11.

Evidence schema 2 supersedes schema 1 because OS approval semantics and
candidate-wheel/download-manifest relationship checks changed. This evidence
schema bump does not change a method, study, history, config, or result schema.

`quality.attribute_control_chart` becomes available with its first persisted
contract at method version `0.1.0` and result schema `1`. This is not a bump of
an older executable result: the registry ID existed only as planned guidance
and no result artifact was previously produced. Future changes to P/NP/C/U
formulas, count/denominator meaning, limit policy, signal rules, or persisted
field interpretation require a method-version decision under this policy.

The executable Phase II frozen-limit slice moves the method to version `0.2.0`
and result schema `2`, while immutable limit-set asset schema remains `1`. This is a
minor bump because the stable method family remains P/NP/C/U while request
options, persisted dependencies, limit source, and result interpretation are
extended. Existing `0.1.0` results remain Phase I and are never reinterpreted
or migrated to Phase II. New `0.2.0` Phase I results use schema `2` with an
explicit `phase_1` marker; limit-set promotion explicitly supports both
`0.1.0`/schema `1` and `0.2.0`/schema `2` sources.

Limit-set asset schema `1` remains executable storage metadata in SQLite schema
`13`. Its canonical field meaning is unchanged; expanding the source-version
enum to include the new Phase I representation does not rewrite an existing
asset or source result. Any change to
the asset's canonical fields, eligibility meaning, or checksum interpretation
requires an asset-schema decision. The common analysis config remains schema
`2`, and SQLite remains schema `13`, because both already persist arbitrary
typed analysis options and asset relationships.

The Phase II single-point stabilization moves the method to `0.3.0` and new
results to schema `3`. This is a minor bump because a previously rejected
one-point monitoring target now produces a persisted result and dispersion
changes from always numeric to a typed availability contract with nullable
ratio and reason code. Phase I still needs two points and limit-set promotion
still needs 20. Existing `0.1.0`/schema `1` and `0.2.0`/schema `2` results
restore verbatim. Limit-set asset schema `1`, calculation policy, canonical
checksum meaning, common config schema `2`, and SQLite schema `14` do not
change. Old `0.2.0` limit sets remain valid inputs; new assets record the
current `0.3.0` execution version.

## Minor Version

Use a minor bump when the method remains the same broad analysis but a stored
result contract or numerical output can change:

- adding a new persisted result field, CI, effect size, assumption diagnostic,
  or warning code;
- changing default missing-data handling, alpha, alternative, correction, or
  post-hoc policy;
- changing p-value, confidence interval, effect size, or degrees-of-freedom
  formulas;
- changing the definition of a chart-data payload or diagnostic statistic;
- adding supported request options that change persisted outputs.

Reference fixture updates that change expected statistics, intervals, effect
sizes, warnings, or payload shape must be reviewed as a method-version bump
candidate.

## Major Version

Use a major bump when stored results from the previous version should not be
treated as comparable without an explicit migration or user-visible note:

- replacing the statistical method family;
- changing the null/alternative hypothesis semantics;
- changing the default test from one method to another;
- removing or renaming persisted result fields;
- changing data inclusion rules in a way that changes `n_used` for the same
  request and dataset;
- changing DOE design-generation semantics or run-order determinism.

## No Silent Migration

Stored analysis result envelopes keep their original `method_version`. A catalog
version bump must not rewrite existing result files. If the UI compares old and
new results, it must show the version difference.

## PR Checklist

- Update `METHOD_VERSIONS` when the policy requires it.
- Update method contract docs and audit matrix entries.
- Add or update reference fixtures and explicit tolerance tests.
- Confirm catalog and handler version alignment tests still pass.
- Record the version rationale in `docs/progress_gate_b.md` or the PR summary.

## Analysis-Run Retention Decision

Analysis-run deletion preflight, exact confirmation, file quarantine, metadata
removal, and startup recovery are operational lifecycle behavior. They do not
change a statistical calculation, request default, result/config meaning,
artifact checksum payload, or comparison semantics. Therefore this slice does
not bump any method version or stored statistical schema. SQLite remains schema
14, while the new deletion preflight and response contracts start at schema 1.

## Model And Limit-Set Retention Decision

Regression-model and attribute-control-limit-set deletion add operational
preflight/delete schemas 1 only. They do not change model fitting, prediction,
Phase I/II calculations, persisted result/config meaning, model manifest schema
2, or limit-set asset schema 1. Therefore that deletion slice left
`regression.linear_model`, `regression.predict`, and the then-current
`quality.attribute_control_chart` version unchanged. The later single-point
monitoring contract independently bumps only the attribute chart as described
above. SQLite remains schema 14.
