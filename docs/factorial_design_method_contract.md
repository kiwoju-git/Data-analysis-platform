# DOE Factorial Design Method Contract

Last updated: 2026-07-02

## Scope

`doe.factorial_design` is currently available only for the first Gate D1 design-asset slice.

Implemented:

- 2-level full factorial design generation.
- Continuous factors with `name`, `unit`, `low`, and `high`.
- Replicates, center points, optional block count, randomization on/off, and randomization seed.
- Preserved `standard_order` and generated `run_order`.
- Immutable design/version/run metadata in SQLite schema version `7`.
- Numeric response entry/readback stored by immutable design version and run ID in SQLite schema version `8`.
- `POST /api/v1/doe-designs/factorial`.
- `GET /api/v1/doe-designs/{design_id}`.
- `PUT /api/v1/doe-designs/{design_id}/responses`.
- `GET /api/v1/doe-designs/{design_id}/responses`.
- Minimal Workbench UI for design inputs, run-table preview, and one numeric response series entry.

Out of scope for this slice:

- Effect estimates, OLS, ANOVA, residual diagnostics, alias structure, Pareto/main-effect/interaction plots.
- Fractional factorial, Plackett-Burman, general factorial, CCD, Box-Behnken, RSM, optimizer.
- Any fake statistical result or placeholder analysis output.

## API Contract

Create:

```http
POST /api/v1/doe-designs/factorial
```

Request fields:

- `name`: design name.
- `factors`: 2 to 6 factors.
- `factors[].name`: unique, non-empty factor name.
- `factors[].low`: finite numeric low level.
- `factors[].high`: finite numeric high level, strictly greater than low.
- `factors[].unit`: optional display unit.
- `replicates`: integer 1 to 16.
- `center_points`: integer 0 to 32.
- `randomize`: boolean.
- `randomization_seed`: integer >= 0.
- `block_count`: integer 1 to 64 and not greater than total run count.

Read:

```http
GET /api/v1/doe-designs/{design_id}
```

Response includes:

- `design_id`, `design_version_id`, `version_number`.
- `method_id = "doe.factorial_design"`, `method_version`.
- `family = "two_level_full_factorial"`.
- `status`, currently `designed` before response entry and `completed` after a full response series is stored.
- factor and option payloads.
- `run_count`.
- `design_sha256`.
- ordered `runs` with `standard_order`, `run_order`, `replicate_index`, `center_point`, `block_index`, uncoded `factor_levels`, and `coded_levels`.

Save responses:

```http
PUT /api/v1/doe-designs/{design_id}/responses
```

Request fields:

- `response_name`: non-empty response label, trimmed before persistence.
- `unit`: optional display unit.
- `values`: one numeric finite value for every current design `run_order`.
- `values[].run_order`: must match the persisted design run table exactly; duplicates, missing runs, or extra runs are rejected.
- `values[].value`: finite numeric response value.

Read responses:

```http
GET /api/v1/doe-designs/{design_id}/responses
```

Response includes `design_id`, `design_version_id`, `version_number`, `status`, and response series ordered by response name and run order. The response API does not return DOE effects, p-values, ANOVA tables, or placeholder analysis output.

The generic `POST /api/v1/analysis-runs` endpoint rejects `doe.factorial_design` with `analysis_method_uses_dedicated_api`.

## Reproducibility Rules

- With the same factors, options, and seed, generated run order and `design_sha256` must be deterministic.
- The checksum is computed from canonical JSON with schema version, family, factors, options, and runs.
- Stored design metadata is checksum-verified before response.
- Response entry does not regenerate or mutate factor levels, standard order, run order, or `design_sha256`.
- No raw dataset, workspace path, or absolute local path is returned.
- Run-count limits are explicit. The app must reject over-limit designs rather than silently truncating or sampling.

## Stable Error Codes

- `analysis_method_uses_dedicated_api`
- `doe_design_not_found`
- `doe_design_family_unsupported`
- `doe_design_version_missing`
- `doe_design_run_metadata_incomplete`
- `doe_design_metadata_invalid`
- `doe_design_checksum_mismatch`
- `doe_design_already_analyzed`
- `doe_response_metadata_invalid`
- `doe_response_name_required`
- `doe_response_run_order_duplicate`
- `doe_response_run_set_mismatch`
- `doe_factorial_method_registry_mismatch`
- `doe_factorial_factor_count_out_of_range`
- `doe_factorial_factor_name_required`
- `doe_factorial_factor_names_not_unique`
- `doe_factorial_factor_range_invalid`
- `doe_factorial_replicates_invalid`
- `doe_factorial_center_points_invalid`
- `doe_factorial_block_count_invalid`
- `doe_factorial_seed_invalid`
- `doe_factorial_run_count_exceeds_limit`
- `doe_factorial_block_count_exceeds_run_count`

## Tests

Required coverage for this slice:

- Pure generator tests for standard order, center points, same-seed randomization, blocks, and invalid designs.
- SQLite migration v6 to v7, v7 to v8, experiment-design record round trip, and response record round trip.
- API contract tests for create/read, duplicate factor rejection, response save/read, incomplete response run-set rejection, and generic analysis-run rejection.
- Frontend SSR test for the Workbench DOE design panel, run preview, and response entry shell.
