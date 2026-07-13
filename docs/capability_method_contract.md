# Capability Analysis Method Contract

Method ID: `quality.capability`

Method version: `0.1.0`

Current status: available Gate D normal capability first slice

## Scope

This slice implements real normal capability analysis from confirmed dataset versions. It reads validated canonical JSONL rows through the common analysis row snapshot path and persists the result envelope with SHA-256 validation.

Included:

- one numeric measurement column
- LSL and/or USL, with optional target
- complete-case missing policy
- normal-model capability point estimates
- within sigma from canonical adjacent moving ranges: `MRbar / d2`, with `d2=1.128`
- overall sigma from sample standard deviation with `ddof=1`
- Cp/Cpk side indices from within sigma
- Pp/Ppk side indices from overall sigma
- observed below/above/total nonconformance counts and ppm
- expected normal-model below/above/total nonconformance probability and ppm
- histogram payload with fitted normal density and spec lines for inline frontend SVG rendering

Out of scope:

- non-normal capability
- Box-Cox or Johnson transformation
- Cpm
- bootstrap or analytic confidence intervals for capability indices
- subgroup pooled within sigma
- automatic stability, normality, or measurement-system approval
- chart export artifacts

## Request Options

Required:

- `value_column_id`: numeric measurement column ID
- at least one of `lsl` or `usl`: finite JSON number

Supported defaults:

- `target`: optional finite JSON number inside the provided spec limits
- `missing_policy`: `complete_case`
- `histogram_bin_limit`: integer from 1 to 30, default `30`

Unsupported options return stable API errors instead of changing method behavior silently.

## Result Payload

The result uses:

- `summary_type`: `capability_analysis`
- `method`: `normal_capability`
- `distribution`: `normal`
- `sigma_estimators`: overall sample SD and within `MRbar/d2`
- `spec_limits`: LSL, USL, and optional target
- `sample`: mean, overall SD, within SD, min, and max
- `capability.within`: Cp-style two-sided, lower, upper, and min-side indices
- `capability.overall`: Pp-style two-sided, lower, upper, and min-side indices
- `observed_nonconformance`: below/above/total observed counts, proportions, and ppm
- `expected_nonconformance_normal`: below/above/total normal-model probabilities and ppm
- `histogram`: capped bin payload with observed density and fitted normal density

Two-sided Cp/Pp values are `null` when only one spec limit is provided. Cpk/Ppk-style `min_side` uses the available side when analysis is one-sided.

## Error Codes

- `dataset_version_required`
- `capability_value_column_required`
- `capability_value_column_not_found`
- `capability_value_column_is_id`
- `capability_value_column_not_numeric`
- `capability_missing_policy_unsupported`
- `capability_spec_limit_required`
- `capability_spec_limits_invalid`
- `capability_target_outside_spec`
- `capability_n_too_small`
- `capability_zero_overall_sigma`
- `capability_zero_within_sigma`
- `invalid_capability_histogram_bin_limit`

## Interpretation Rules

Spec limits are not control limits. The first slice always warns that process stability, normal-model suitability, and measurement-system adequacy are not proven by this calculation.

This slice returns point estimates only. It records `capability_point_estimates_without_ci` until confidence intervals are implemented and validated.

## Reference Validation

`backend/tests/reference/fixtures/quality_capability_normal_reference.json`
cross-checks the overall sample-standard-deviation indices against the official
NIST/SEMATECH e-Handbook section 6.1.6 capability example:
`https://www.itl.nist.gov/div898/handbook/pmc/section1/pmc16.htm`.

The published example provides LSL 8, USL 20, mean 16, sample standard
deviation 2, Cp 1.0, Cpk/Cpu 0.6667, and Cpl 1.3333. The fixture uses synthetic
rows `[14, 16, 18]` to reproduce that mean and sample standard deviation. The
application's overall fields match those formulas numerically, although this
product labels sample-SD indices as overall Pp/Ppk-style fields. The within
fields use the separate `MRbar/d2` contract and are hand-checked rather than
attributed to NIST.

This three-row fixture validates formulas only. It must not be interpreted as
evidence of process stability, normality, measurement-system adequacy, or an
adequate capability-study sample size. No method version or runtime calculation
changes as a result of this reference-only slice.
