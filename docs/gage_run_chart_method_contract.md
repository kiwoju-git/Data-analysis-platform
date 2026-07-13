# Gage Run Chart Method Contract

Method ID: `quality.gage_run_chart`

Status: available first slice

## Purpose

`quality.gage_run_chart` renders a measurement-system diagnostic run chart for a balanced crossed Gage study. It is a visual diagnostic of measurement patterns across part, operator, and replicate context. It does not calculate variance components and does not replace `quality.gage_rr`.

## Required Inputs

- `dataset_version_id`
- `roles.measurement_column_id`: numeric measurement column
- `roles.part_column_id`: part identifier column
- `roles.operator_column_id`: operator identifier column
- `roles.replicate_column_id`: replicate identifier column
- `roles.order_column_id`: optional numeric or datetime order column
- `options.missing_policy`: currently `complete_case`
- `options.point_limit`: optional positive integer, capped by the service limit

The measurement, part, operator, replicate, and order columns must be distinct when provided.

## Data Source And Provenance

- The method reads validated canonical JSONL rows only.
- The method creates an `analysis_row_snapshot` before calculation.
- The result envelope is persisted under the workspace and returned by checksum-validated `GET /api/v1/analysis-runs/{analysis_id}/result`.
- The response must not expose workspace paths or raw source paths.

## Design Validation

The first slice supports balanced crossed designs only:

- at least two parts;
- at least two operators;
- at least two replicates per part/operator cell;
- every part/operator cell must exist;
- every cell must have the same replicate identifier set;
- duplicate replicate identifiers within a part/operator cell are rejected.

Unsupported designs fail with stable errors instead of being downgraded to a generic run chart.

## Result Payload

The result payload contains:

- `summary_type: "gage_run_chart"`;
- method and column metadata;
- sample counts and exclusion counts;
- balanced design counts;
- overall measurement summary;
- per-part-index summary;
- per-operator-index summary;
- capped `chart.points` array with value, canonical position, display position, part index, operator index, and replicate index;
- warning codes and notes explaining diagnostic-only interpretation.

Raw part, operator, and replicate labels are redacted from the result. The chart payload uses stable integer indices only.

## Reference Validation

- `backend/tests/reference/fixtures/quality_gage_run_chart_ordering_reference.json`
  is an internally hand-reviewed, fully synthetic diagnostic fixture. An
  external statistical package is not required because this result is
  deterministic chart-data preparation rather than an inferential estimate.
- The reference case fixes numeric order-column sorting and canonical row
  position as the stable tie-breaker. It asserts every displayed point's value,
  canonical position, and part/operator/replicate index.
- Missing measurements, nonnumeric measurements, missing identifiers, missing
  order values, and invalid order values are excluded visibly with exact sample
  counts and persistent warning codes.
- The chart point limit truncates only the inline point array. Design counts,
  sample counts, and measurement summaries continue to describe all valid
  observations.
- Synthetic raw part, operator, and replicate labels are checked against the
  complete serialized result so the fixture cannot pass while leaking a label
  outside `chart.points`.
- A paired failure case rejects a duplicate replicate within a part/operator
  cell. No empty or fabricated chart result is returned.
- The fixture does not validate visual rendering, exported chart artifacts, or
  measurement-system acceptability. Gage R&R remains the variance-component
  analysis.

## Stable Error Codes

- `gage_run_chart_distinct_columns_required`
- `gage_run_chart_measurement_column_not_found`
- `gage_run_chart_measurement_column_not_numeric`
- `gage_run_chart_measurement_column_is_id`
- `gage_run_chart_part_column_not_found`
- `gage_run_chart_part_column_not_supported`
- `gage_run_chart_operator_column_not_found`
- `gage_run_chart_operator_column_not_supported`
- `gage_run_chart_replicate_column_not_found`
- `gage_run_chart_replicate_column_not_supported`
- `invalid_gage_run_chart_order_column`
- `gage_run_chart_order_column_conflicts_with_role`
- `gage_run_chart_order_column_not_found`
- `gage_run_chart_order_column_unsupported_type`
- `gage_run_chart_missing_policy_unsupported`
- `invalid_gage_run_chart_point_limit`
- `gage_run_chart_no_usable_measurements`
- `gage_run_chart_part_count_too_small`
- `gage_run_chart_operator_count_too_small`
- `gage_run_chart_replicate_count_too_small`
- `gage_run_chart_crossed_cells_missing`
- `gage_run_chart_unbalanced_crossed_design`
- `gage_run_chart_duplicate_replicates_per_cell`

## Current Limitations

- Component plots, interaction plots, faceting, and exported chart artifacts are not implemented.
- The method does not produce variance components, %GRR, or ndc.
- Datetime order columns are accepted by service-level schema validation, but this first calculation slice sorts order values by their canonical string representation.
- Chart points are capped inline; separate paged chart payload retrieval is not implemented.
