# Method Versioning Policy

This policy explains when a stable `method_id` in `METHOD_VERSIONS` should
receive a method-version bump. `regression.predict` and `doe.factorial_design`
are currently `0.2.0`; the other stable IDs remain on `0.1.0`.

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

`doe.factorial_design` receives a minor bump from `0.1.0` to `0.2.0` because
the same dedicated method now persists and restores effects, OLS/ANOVA,
pure-error/lack-of-fit, diagnostic, plot, and provenance fields. Its analysis
config and result schemas both start at `1`; SQLite metadata schema v9 stores
the relationship. Earlier v0.1 design/response assets are not rewritten into
analysis results, and no fake migration is performed.

`doe.response_surface` becomes executable for the first time at `0.1.0` through
dedicated CCD design/response/analysis routes. Its design, analysis config, and
analysis result schemas each start at `1`; existing schema-v9 DOE metadata
tables store the relationship. There is no prior executable response-surface
artifact to migrate or reinterpret.

`regression.response_optimizer` keeps its initial registry version `0.1.0`
when its first persisted dedicated optimizer contract becomes executable from
the response-surface panel. Its config and result schemas both start at `1` and
schema-v9 DOE analysis metadata stores the relationship. The generic
analysis-run page remains disabled, but it produced no earlier optimizer result
that would require a version bump or migration.

`doe.bayesian_optimization` enters the catalog as a planning-only method at
`0.1.0`. It has no executable API, config/result/history schema, migration, or
stored result. The version identifies the approved planning contract and
reference policy only. Before the first executable artifact is allowed, the
implementation must either match that contract or make an explicit method-
version decision; no stored result may be silently assigned to the planning
version after semantics change.

`quality.attribute_control_chart` becomes available with its first persisted
contract at method version `0.1.0` and result schema `1`. This is not a bump of
an older executable result: the registry ID existed only as planned guidance
and no result artifact was previously produced. Future changes to P/NP/C/U
formulas, count/denominator meaning, limit policy, signal rules, or persisted
field interpretation require a method-version decision under this policy.

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
