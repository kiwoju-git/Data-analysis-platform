# Subgroup Chart Method Contract

Method ID: `quality.subgroup_chart`

Method version: `0.1.0`

Current status: available Gate D Xbar-R/Xbar-S fixed-subgroup slice

## Scope

This slice implements real Xbar-R and Xbar-S charts from confirmed dataset versions. It reads validated canonical JSONL rows through the common analysis row snapshot path and persists the result envelope with SHA-256 validation.

Included:

- one numeric measurement column
- one subgroup ID column
- canonical row first-seen subgroup order
- fixed subgroup size only
- subgroup sizes 2 through 10 only
- complete-case missing policy
- Xbar center line as the mean of subgroup means
- R center line as the average subgroup range for Xbar-R
- S center line as the average subgroup sample standard deviation for Xbar-S
- standard Xbar-R constants `A2`, `D3`, and `D4`
- standard Xbar-S constants `A3`, `B3`, and `B4`
- Xbar-R control limits from `Xbarbar +/- A2 * Rbar`
- R chart limits from `D3 * Rbar` and `D4 * Rbar`
- Xbar-S control limits from `Xbarbar +/- A3 * Sbar`
- S chart limits from `B3 * Sbar` and `B4 * Sbar`
- first-slice signals:
  - `subgroup_chart_xbar_beyond_control_limits`
  - `subgroup_chart_r_beyond_control_limits`
  - `subgroup_chart_s_beyond_control_limits`
- capped chart payload for inline frontend SVG rendering

Out of scope:

- varying subgroup-size Xbar-R limits
- varying subgroup-size Xbar-S limits
- attribute charts, capability analysis, Gage R&R
- full Nelson or full Western Electric rule sets
- baseline exclusion, phase limits, and chart export artifacts

## Request Options

Required:

- `value_column_id`: numeric measurement column ID
- `subgroup_column_id`: subgroup ID column ID

Supported defaults:

- `chart_type`: `xbar_r` or `xbar_s`, default `xbar_r`
- `missing_policy`: `complete_case`
- `point_limit`: integer from 1 to 5000, default `1000`

Unsupported options return stable API errors instead of changing method behavior silently.

## Result Payload

The result uses:

- `summary_type`: `subgroup_chart`
- `method`: `xbar_r_chart` or `xbar_s_chart`
- `chart_type`: `xbar_r` or `xbar_s`
- `order_source`: `canonical_subgroup_first_seen`
- `subgroup_size` and `subgroup_count`
- `constants`: subgroup size and selected Xbar-R or Xbar-S constants
- `control_rules`: enabled first-slice rule definitions
- `value` and `subgroup`: selected column metadata
- `n_total`, `n_used`, and exclusion counts
- `subgroup_size_distribution`
- `xbar_chart`: center line, LCL, UCL, capped points, and signal codes
- `r_chart`: center line, LCL, UCL, capped points, and signal codes for Xbar-R results
- `s_chart`: center line, LCL, UCL, capped points, and signal codes for Xbar-S results
- `signals`: detected Xbar/R or Xbar/S limit signals

Chart points expose subgroup labels, canonical row position spans, plotted values, subgroup means, subgroup ranges, subgroup N, and signal codes. S chart points also expose sample standard deviation. Source paths and internal absolute paths are not included in the result.

## Error Codes

- `dataset_version_required`
- `subgroup_chart_value_column_required`
- `subgroup_chart_value_column_not_found`
- `subgroup_chart_value_column_is_id`
- `subgroup_chart_value_column_not_numeric`
- `subgroup_chart_subgroup_column_required`
- `subgroup_chart_subgroup_column_same_as_value`
- `subgroup_chart_subgroup_column_not_found`
- `subgroup_chart_subgroup_column_unsupported_type`
- `subgroup_chart_type_unsupported`
- `subgroup_chart_missing_policy_unsupported`
- `invalid_subgroup_chart_point_limit`
- `subgroup_chart_subgroup_count_too_small`
- `subgroup_chart_subgroup_size_too_small`
- `subgroup_chart_varying_subgroup_size_unsupported`
- `subgroup_chart_subgroup_size_unsupported`
- `subgroup_chart_zero_average_range`
- `subgroup_chart_zero_average_stddev`

## Interpretation Rules

The Xbar-R limits are estimated from subgroup ranges. The Xbar-S limits are estimated from subgroup sample standard deviations using `n - 1`. The method does not prove process stability, independence, rational subgrouping, or measurement-system adequacy.

The current slice rejects varying subgroup sizes instead of silently applying approximate limits. It also rejects all-zero average subgroup range or all-zero average subgroup sample standard deviation instead of fabricating control limits.

The current signal rules are limited to one point outside the Xbar, R, or S control limits. Common multi-point rules are documented in the 6-module guide but are not implemented in this subgroup slice.
