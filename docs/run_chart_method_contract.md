# Run Chart Method Contract

Method ID: `quality.run_chart`

Method version: `0.1.0`

Current status: available Gate D slice with exact run-count signals

## Scope

This slice implements a real median run chart from confirmed dataset versions. It reads validated canonical JSONL rows through the common analysis row snapshot path and persists the result envelope with SHA-256 validation.

Included:

- one numeric measurement column
- canonical row order as the default x-axis
- optional numeric order column sorted ascending
- optional datetime order column sorted ascending
- stable order ties by canonical row position
- median center line
- complete-case missing policy
- tie-to-median policy recorded as `exclude_from_runs`
- run count above/below the median
- strictly monotonic trend signal with a default minimum length of 6 points
- strictly alternating oscillation signal with a default minimum length of 14 points
- exact conditional run-count test for clustering and mixture signals, default alpha `0.05`
- capped chart payload for inline frontend SVG rendering

Out of scope:

- control limits
- Nelson or Western Electric control-chart rules
- chart image/export artifact generation
- capability analysis, I-MR, Xbar-R, Xbar-S, attribute charts, Gage R&R

## Request Options

Required:

- `value_column_id`: numeric measurement column ID

Supported defaults:

- `order_column_id`: optional numeric or datetime order column ID; omitted or empty uses canonical row order
- `center_method`: `median`
- `missing_policy`: `complete_case`
- `trend_min_length`: integer from 3 to 20, default `6`
- `oscillation_min_length`: integer from 4 to 30, default `14`
- `runs_test_alpha`: number where `0 < alpha < 0.5`, default `0.05`
- `point_limit`: integer from 1 to 5000, default `1000`

Unsupported options return stable API errors instead of changing method behavior silently.

## Result Payload

The result uses:

- `summary_type`: `run_chart`
- `method`: `median_run_chart`
- `order_source`: `canonical_row_order`, `numeric_order_column_ascending`, or `datetime_order_column_ascending`
- `order`: selected order column metadata, or `null` when canonical row order is used
- `order_tie_breaker`: `canonical_row_position` when an order column is selected
- `order_timezone`: `timezone_naive`, `timezone_aware_utc`, or `null`
- `center_line`: median of used numeric values
- `n_excluded_missing_order` and `n_excluded_non_numeric_order`: complete-case exclusions from the order column
- `order_duplicate_count`: count of order-column ties after exclusions
- `runs`: run count, above/below/tie counts, longest run length, and run definition
- `runs_test`: exact conditional run-count test summary with observed run count, above/below/tie counts, expected run count, variance, low/high tail p-values, interpretation, and explicit skip reason when unavailable
- `signals`: currently `run_chart_trend`, `run_chart_oscillation`, `run_chart_clustering`, and `run_chart_mixture`
- `chart`: capped points with x-axis position, numeric value, relative-to-center label, and signal codes

When an order column is selected, chart points expose only order rank plus canonical row position for deterministic tie tracing. Raw order values, source paths, and internal absolute paths are not included in the result.

## Error Codes

- `dataset_version_required`
- `run_chart_value_column_required`
- `run_chart_value_column_not_found`
- `run_chart_value_column_is_id`
- `run_chart_value_column_not_numeric`
- `invalid_run_chart_order_column`
- `run_chart_order_column_same_as_value`
- `run_chart_order_column_not_found`
- `run_chart_order_column_not_numeric`
- `run_chart_order_mixed_timezone_awareness`
- `invalid_run_chart_center_method`
- `run_chart_missing_policy_unsupported`
- `invalid_run_chart_tie_policy`
- `invalid_run_chart_trend_min_length`
- `invalid_run_chart_oscillation_min_length`
- `invalid_run_chart_runs_test_alpha`
- `invalid_run_chart_point_limit`
- `run_chart_n_too_small`
- `run_chart_all_values_tied_to_center`

## Interpretation Rules

Run chart signals are not control-chart out-of-control signals. This method does not compute control limits. The result and UI must keep that distinction visible.

`run_chart_oscillation` means consecutive point-to-point directions strictly alternate between increasing and decreasing for at least the configured minimum number of points. Equal adjacent values break the sequence.

`run_chart_clustering` means the observed median above/below run count is unusually low under the exact conditional distribution given the observed `n_above` and `n_below`.

`run_chart_mixture` means the observed median above/below run count is unusually high under the same exact conditional distribution.

The exact run-count test excludes points tied to the median. If above or below is absent, or if the non-tie count exceeds the current exact calculation limit of 5000, the result records `available=false` and no clustering/mixture signal is emitted. No normal approximation or fallback signal is used.

Canonical row order is only valid when the dataset row order represents the process/run order. If a numeric or datetime run/order column exists, users can select it and the method sorts ascending with canonical row position as a stable tie-breaker.
Datetime order columns support ISO 8601 and the same common date/time formats used by dataset profile preflight. Timezone-aware datetime values are compared after UTC normalization. Mixing timezone-aware and timezone-naive values is rejected with `run_chart_order_mixed_timezone_awareness` instead of silently imposing an ambiguous order. Raw datetime values are not included in the result payload.
