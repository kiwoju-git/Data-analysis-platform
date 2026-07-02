# Gage R&R Preflight Contract

Status: Gate C3 companion preflight API, not a statistical result.

## Scope

`POST /api/v1/quality/gage-rr/preflight` checks whether a dataset version is ready for the executable `quality.gage_rr` balanced crossed ANOVA slice.

It does not create an `analysis_run`, does not write result artifacts, and does not calculate ANOVA tables, variance components, %GRR, ndc, or plots. Execute `quality.gage_rr` through `POST /api/v1/analysis-runs` after the preflight is ready.

## Request

```json
{
  "dataset_version_id": "uuid",
  "measurement_column_id": "column-id",
  "part_column_id": "column-id",
  "operator_column_id": "column-id",
  "replicate_column_id": "column-id",
  "missing_policy": "complete_case"
}
```

Rules:

- `measurement_column_id` must be a numeric column.
- part, operator, and replicate columns may be text, integer, decimal, or boolean.
- the four role columns must be distinct.
- rows are read only from the canonical dataset artifact.
- filter snapshots are not applied in this shell.

## Response

The endpoint returns a deterministic summary with:

- dataset version and schema hash
- selected role-column metadata
- total/usable/excluded row counts
- part count, operator count, replicate level count
- expected and observed part-operator cell counts
- missing cell count
- min/max replicates per cell
- cell replicate-count distribution
- `ready_for_anova`
- `issues`
- `next_step`

Raw part/operator/replicate cell values are not returned.

## Issue Codes

Info:

- `gage_rr_preflight_only_no_variance_components`
- `gage_rr_requires_balanced_crossed_design`
- `gage_rr_independence_not_proven`
- `gage_rr_labels_redacted`

Errors in the response body:

- `gage_rr_no_usable_measurements`
- `gage_rr_part_count_too_small`
- `gage_rr_operator_count_too_small`
- `gage_rr_replicate_count_too_small`
- `gage_rr_crossed_cells_missing`
- `gage_rr_unbalanced_crossed_design`
- `gage_rr_duplicate_replicates_per_cell`

Warnings in the response body:

- `missing_values_excluded`
- `non_numeric_values_excluded`
- `gage_rr_identifier_missing_excluded`

HTTP errors:

- `gage_rr_missing_policy_unsupported`
- `gage_rr_distinct_columns_required`
- `gage_rr_measurement_column_not_found`
- `gage_rr_measurement_column_not_numeric`
- `gage_rr_measurement_column_is_id`
- `gage_rr_part_column_not_found`
- `gage_rr_part_column_not_supported`
- `gage_rr_operator_column_not_found`
- `gage_rr_operator_column_not_supported`
- `gage_rr_replicate_column_not_found`
- `gage_rr_replicate_column_not_supported`

## Related Execution Contract

The executable method contract is documented in `docs/gage_rr_method_contract.md`. The preflight remains useful because it reports balance and duplicate/missing-cell issues before an analysis run is created.
