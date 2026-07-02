# Individuals Chart Method Contract

Method ID: `quality.individuals_chart`

Method version: `0.1.0`

Current status: available Gate D I-MR slice with explicit I-chart rule coverage

## Scope

This slice implements a real I-MR chart from confirmed dataset versions. It reads validated canonical JSONL rows through the common analysis row snapshot path and persists the result envelope with SHA-256 validation.

Included:

- one numeric measurement column
- canonical row order as the default x-axis
- optional numeric or datetime order column sorted ascending
- canonical row position as the stable tie-breaker for duplicate order values
- timezone-aware datetime order values compared in UTC; mixed timezone-aware and timezone-naive values rejected
- complete-case missing policy
- I chart center line as the arithmetic mean
- moving ranges of adjacent values with length 2
- sigma estimate as `MRbar / d2` with `d2 = 1.128`
- I chart 3-sigma limits
- MR chart limits using `D3 = 0` and `D4 = 3.267`
- P0 signals:
  - `individuals_chart_i_beyond_3_sigma`
  - `individuals_chart_mr_beyond_ucl`
  - `individuals_chart_i_same_side_centerline`
  - `individuals_chart_i_trend`
  - `individuals_chart_i_alternating`
  - `individuals_chart_i_two_of_three_beyond_2_sigma`
  - `individuals_chart_i_four_of_five_beyond_1_sigma`
  - `individuals_chart_i_fifteen_within_1_sigma`
  - `individuals_chart_i_eight_outside_1_sigma`
- capped chart payload for inline frontend SVG rendering

Out of scope:

- full Nelson or full Western Electric rule sets
- rule windows beyond the explicitly listed I chart same-side, trend, alternating, and zone rules
- Xbar-R, Xbar-S, attribute charts, capability analysis, Gage R&R
- chart image/export artifact generation

## Request Options

Required:

- `value_column_id`: numeric measurement column ID

Supported defaults:

- `order_column_id`: optional numeric or datetime order column ID
- `missing_policy`: `complete_case`
- `same_side_min_length`: integer from 3 to 30, default `9`
- `trend_min_length`: integer from 3 to 20, default `6`
- `point_limit`: integer from 1 to 5000, default `1000`

Unsupported options return stable API errors instead of changing method behavior silently.

## Result Payload

The result uses:

- `summary_type`: `individuals_chart`
- `method`: `i_mr_chart`
- `order_source`: `canonical_row_order`, `numeric_order_column_ascending`, or `datetime_order_column_ascending`
- `order_tie_breaker`: `canonical_row_position` when an order column is selected
- `order_timezone`: timezone policy for datetime order columns
- `sigma_estimator`: method, moving range length, constants, `MRbar`, and sigma estimate
- `control_rules`: enabled first-slice rule definitions
- `order`: selected order column metadata, or `null`
- `n_excluded_missing_order`, `n_excluded_non_numeric_order`, and `order_duplicate_count`
- `individuals_chart`: center line, LCL, UCL, capped points, and signal codes
- `moving_range_chart`: center line, LCL, UCL, constants, capped points, and signal codes
- `signals`: detected I/MR limit, I same-side, I trend, I alternating, or I zone signals

Chart points expose only canonical/order positions and numeric plotted values. Source paths and internal absolute paths are not included in the result.

## Error Codes

- `dataset_version_required`
- `individuals_chart_value_column_required`
- `individuals_chart_value_column_not_found`
- `individuals_chart_value_column_is_id`
- `individuals_chart_value_column_not_numeric`
- `invalid_individuals_chart_order_column`
- `individuals_chart_order_column_same_as_value`
- `individuals_chart_order_column_not_found`
- `individuals_chart_order_column_not_numeric`
- `individuals_chart_order_mixed_timezone_awareness`
- `individuals_chart_missing_policy_unsupported`
- `invalid_individuals_chart_point_limit`
- `invalid_individuals_chart_same_side_min_length`
- `invalid_individuals_chart_trend_min_length`
- `individuals_chart_n_too_small`
- `individuals_chart_zero_moving_range`

## Interpretation Rules

The I-MR limits are estimated from adjacent moving ranges. The method does not prove process stability, independence, rational ordering, or measurement-system adequacy.

The same-side rule emits `individuals_chart_i_same_side_centerline` for an uninterrupted run of at least `same_side_min_length` I-chart points strictly above or strictly below the center line. Points exactly on the center line break the run.

The trend rule emits `individuals_chart_i_trend` for at least `trend_min_length` consecutive I-chart points that are strictly increasing or strictly decreasing. Equal adjacent values break the trend.

The alternating rule emits `individuals_chart_i_alternating` for 14 consecutive I-chart points whose adjacent directions strictly alternate up/down. Equal adjacent values break the alternating run.

The first zone rules are fixed:

- `individuals_chart_i_two_of_three_beyond_2_sigma`: at least two of three consecutive I-chart points beyond 2 sigma on the same side of the center line.
- `individuals_chart_i_four_of_five_beyond_1_sigma`: at least four of five consecutive I-chart points beyond 1 sigma on the same side of the center line.
- `individuals_chart_i_fifteen_within_1_sigma`: fifteen consecutive I-chart points within 1 sigma of the center line, inclusive.
- `individuals_chart_i_eight_outside_1_sigma`: eight consecutive I-chart points outside 1 sigma of the center line on either side.

The 2-of-3 and 4-of-5 zone-rule chart markers are attached only to the points in the window that actually cross the relevant sigma threshold. The within/outside pattern-rule markers are attached to every point in the qualifying pattern window. The result records the full evaluated window start and end positions.

`individuals_chart_zero_moving_range` is returned when all moving ranges are zero. The app does not fabricate control limits for a constant series.

Canonical row order is only valid when the dataset row order represents the process/run order. If a numeric or datetime order column is selected, the app sorts ascending and uses canonical row position only as a deterministic tie-breaker.
