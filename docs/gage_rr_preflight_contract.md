# Gage R&R Preflight Contract

Updated: 2026-11-01. Response schema 2, executable method 0.2.0.

`POST /api/v1/quality/gage-rr/preflight` validates a balanced crossed design
without creating an analysis, computing ANOVA or writing a persistent snapshot.

## Request

Required: dataset_version_id, measurement_column_id, part_column_id,
operator_column_id. Optional replicate_column_id and replicate_mode:
`infer_from_rows` or `explicit_column`. The latter requires a distinct fourth
column; omitted mode plus a supplied column preserves old explicit semantics.
Missing policy remains complete_case. Optional filter_snapshot uses the same
versioned conditions and frozen-row selection as execution.

## Response And Ownership

The response includes dataset version/schema hash, canonical artifact hash,
filter snapshot hash, resolved role metadata and repeat mode, total/usable/
excluded counts, crossing/cell-count distribution, structural balance, readiness,
issues and next step. It never returns original part/operator/replicate values.

Counts are based on valid measurements per cell. Distinct repeat-ID sets across
cells are informational, not a balance requirement. Duplicates within a cell
remain errors. Automatic ordinals have no time/round interpretation.

A ready result is descriptive, not authorization to bypass validation. Execution
revalidates the exact current dataset/filter/options. The UI's Compute command
performs a fresh preflight internally; the explicit preflight button remains for
inspection. Source, role and filter changes invalidate the previous response,
including pending success/catch/finally work.

## Stable Failures

Structural/data codes include gage_rr_no_usable_measurements,
gage_rr_part_count_too_small, gage_rr_operator_count_too_small,
gage_rr_replicate_count_too_small, gage_rr_crossed_cells_missing,
gage_rr_unbalanced_crossed_design, gage_rr_duplicate_replicates_per_cell,
gage_rr_zero_total_variation. Unsupported mode/column combinations fail request
validation. Measurement types and distinct selected columns remain validated.

Temporary snapshot files are not needed: preflight uses the shared
`freeze_row_indices` selection plus the verified canonical iterator directly.
The full calculation, pooling, legacy and report contracts are in
[gage_rr_method_contract.md](gage_rr_method_contract.md).
