# Gage R&R Method Contract

Status: Gate C3 balanced crossed ANOVA first slice.

## Scope

`quality.gage_rr` runs through `POST /api/v1/analysis-runs` and returns a stored analysis result envelope. It reads rows from the confirmed canonical dataset artifact, applies the optional Workbench filter snapshot through the common row-snapshot path, and then validates a balanced crossed design.

This first slice supports:

- one numeric measurement column
- one part column
- one operator column
- one replicate column
- complete-case missing handling
- balanced crossed ANOVA
- raw and final variance components
- percent contribution
- percent study variation
- ndc

This first slice does not support nested, unbalanced, expanded, or crossed-with-missing-cell designs. It also does not support tolerance/process variation inputs, interaction pooling options, component/interaction plots, Gage Run Chart, or exported chart artifacts.

## Request Options

```json
{
  "method_id": "quality.gage_rr",
  "method_version": "0.1.0",
  "dataset_version_id": "uuid",
  "roles": {
    "measurement": "column-id",
    "part": "column-id",
    "operator": "column-id",
    "replicate": "column-id"
  },
  "options": {
    "measurement_column_id": "column-id",
    "part_column_id": "column-id",
    "operator_column_id": "column-id",
    "replicate_column_id": "column-id",
    "missing_policy": "complete_case"
  }
}
```

Rules:

- the measurement column must be numeric;
- part, operator, and replicate columns may be text, integer, decimal, or boolean;
- the four role columns must be distinct;
- only `complete_case` is supported;
- raw part/operator/replicate labels are not returned in the result payload.

## Result Payload

The result envelope `result` field has:

- `summary_type: "gage_rr"`
- `method: "balanced_crossed_anova"`
- selected column metadata
- sample counts and exclusion counts
- design counts without raw labels
- ANOVA table for part, operator, part-operator interaction, repeatability, and total
- variance components for repeatability, operator, part-operator, reproducibility, total Gage R&R, part-to-part, and total variation
- raw variance, final variance, standard deviation, study variation, clamped-to-zero flag, percent contribution, and percent study variation for each component
- `ndc`
- `negative_component_policy`
- `interaction_policy`
- deterministic warnings and notes

Negative raw variance components are reported as raw estimates and final variance is clamped to zero. This policy is visible in the component row and warning list; it is not silently hidden.

## Stable Error Codes

Request or column validation:

- `dataset_version_required`
- `gage_rr_measurement_column_required`
- `gage_rr_part_column_required`
- `gage_rr_operator_column_required`
- `gage_rr_replicate_column_required`
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

Design or calculation validation:

- `gage_rr_no_usable_measurements`
- `gage_rr_part_count_too_small`
- `gage_rr_operator_count_too_small`
- `gage_rr_replicate_count_too_small`
- `gage_rr_crossed_cells_missing`
- `gage_rr_unbalanced_crossed_design`
- `gage_rr_duplicate_replicates_per_cell`
- `gage_rr_zero_total_variation`

## Persistent Warnings

- `gage_rr_balanced_crossed_anova_assumed`
- `gage_rr_interaction_not_pooled`
- `gage_rr_independence_not_proven`
- `gage_rr_labels_redacted`
- `gage_rr_negative_variance_component_clamped`
- `missing_values_excluded`
- `non_numeric_values_excluded`
- `gage_rr_identifier_missing_excluded`

## Test Coverage

The current slice includes:

- hand-checkable balanced crossed ANOVA fixture;
- negative raw variance component fixture with clamp-policy assertions;
- unbalanced design and zero total variation rejection;
- API execution from a confirmed dataset version;
- API rejection for unbalanced data without a result payload;
- stored result retrieval through the common checksum-validated result API.
