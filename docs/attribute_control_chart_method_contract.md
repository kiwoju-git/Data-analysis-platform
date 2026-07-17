# Attribute Control Chart Method Contract

Last updated: 2026-07-16

## Scope And Version

- Method ID: `quality.attribute_control_chart`
- Method version: `0.2.0`
- Result schema: `2` for new Phase I and Phase II runs; stored `0.1.0`/schema-1
  Phase I results restore without relabeling
- Execution: generic inline `POST /api/v1/analysis-runs`
- Storage/export: checksum-validated stored result, row snapshot, JSON, long CSV,
  and HTML through the common analysis-run paths
- UI: Quality Control > Control Chart, rendered by
  `AttributeControlChartPanel`

Phase I estimates the center line and three-sigma limits from all valid rows
remaining after the explicit analysis filter. Phase II applies a separately
verified, app-created immutable limit-set asset to compatible monitoring rows.
Neither phase silently changes chart type, adjusts limits for dispersion,
removes signaled points, or refits a monitoring target.

The panel requires an explicit Phase I/Phase II choice. Phase II requires a
verified limit set and a ready target compatibility preflight; it never accepts
user-entered naked limits. The immutable dependency, compatibility, frozen
calculation, restore/export, and error contracts are defined in
`docs/attribute_control_chart_phase_2_contract.md`.

## Input Contract

One canonical row represents one ordered inspection subgroup. Canonical row
order is the chart order.

| Chart | Count definition | Required denominator | Runtime gate |
| --- | --- | --- | --- |
| P | defective units | positive integer sample size | defective count <= sample size |
| NP | defective units | positive integer sample size | every valid sample size must match |
| C | defects/nonconformities | none | user confirms equal inspection opportunity |
| U | defects/nonconformities | positive finite opportunity/area/exposure | opportunity may vary |

Options are closed by `AttributeControlChartOptions`:

- `phase`: `phase_1` or `phase_2`
- `limit_set_id`: forbidden for Phase I and required for Phase II
- `chart_type`: `p`, `np`, `c`, or `u`
- `count_definition`: `defectives` for P/NP, `defects` for C/U
- `count_column_id`
- `denominator_column_id`: required for P/NP/U and forbidden for C
- `constant_opportunity_confirmed`: required as `true` for C
- `missing_policy`: `complete_case`
- `point_limit`: integer `1..5000`; limits only the inline point payload

Missing and nonnumeric count/denominator rows are excluded with separate
counts and persistent warnings. Numeric counts must be finite, nonnegative
integers. Invalid numeric denominators, count-definition mismatch, varying NP
sample size, and defective counts above sample size stop the run explicitly.

## Calculations

Let `d_i` be the count and `n_i` the sample size or inspection opportunity.
All limits use a three-sigma multiplier and signal only values strictly outside
the limits.

- P: `pbar = sum(d_i) / sum(n_i)`, point `p_i = d_i/n_i`, and
  `pbar +/- 3*sqrt(pbar*(1-pbar)/n_i)`. Limits are bounded to `[0, 1]`.
- NP: fixed `n`, `pbar = sum(d_i)/sum(n_i)`, center `n*pbar`, and
  `n*pbar +/- 3*sqrt(n*pbar*(1-pbar))`. Limits are bounded to `[0, n]`.
- C: `cbar = sum(d_i)/m` and `cbar +/- 3*sqrt(cbar)`. LCL is bounded at zero.
- U: `ubar = sum(d_i)/sum(n_i)`, point `u_i=d_i/n_i`, and
  `ubar +/- 3*sqrt(ubar/n_i)`. LCL is bounded at zero.

An all-zero defect baseline or an all-conforming/all-defective binomial
baseline has zero estimated variance and is rejected instead of producing a
fake chart. The result records every point's count, denominator, statistic,
LCL/UCL, natural-bound truncation flags, canonical position, and signal codes.

The diagnostic Pearson dispersion ratio is `sum((observed-expected)^2 /
variance)/(m-1)`. A ratio above `2` creates a warning but never changes the
limits or chart type. Binomial expected successes/failures below `5`, Poisson
expected counts below `5`, and fewer than `20` Phase I points also create
interpretation warnings.

## Errors And Warnings

Stable errors include:

- `invalid_attribute_control_chart_options`
- `attribute_control_chart_count_definition_mismatch`
- `attribute_control_chart_denominator_required`
- `attribute_control_chart_c_constant_opportunity_required`
- `attribute_control_chart_negative_count`
- `attribute_control_chart_non_integer_count`
- `attribute_control_chart_count_not_finite`
- `attribute_control_chart_denominator_not_positive`
- `attribute_control_chart_denominator_not_finite`
- `attribute_control_chart_sample_size_not_integer`
- `attribute_control_chart_defectives_exceed_sample_size`
- `attribute_control_chart_np_varying_sample_size`
- `attribute_control_chart_point_count_too_small`
- `attribute_control_chart_zero_variation`

Persistent warnings cover Phase I estimation, canonical order, unprovable
process assumptions, small baselines, weak normal approximation,
overdispersion, natural-bound truncation, exclusions, point truncation, and
control-limit signals. API errors do not include raw cell values, filenames,
absolute paths, SQL, or tracebacks.

## Provenance And Privacy

The common analysis-run execution layer records method/version, dataset
version and schema hash, canonical artifact SHA-256, filter and row snapshot,
included/total row counts, app/build/runtime/package versions, and timestamps.
The result adds chart/count/denominator semantics and all calculation-policy
flags. Raw filenames, storage paths, and arbitrary row labels are not stored in
the chart payload.

## Reference Validation

`quality_attribute_control_chart_nist_reference.json` records source URLs,
conventions, and full-precision expectations. Tests verify:

- the published NIST C-chart example (`cbar=16`, `LCL=4`, `UCL=28`), including
  strict boundary behavior at 28 and the signal at count 31;
- the published NIST P-chart proportions example and the corresponding NP
  transformation at fixed sample size 50;
- independently evaluated U-chart limits for unequal opportunity values;
- hand-checkable weighted P limits, exclusions, truncation, dispersion policy,
  and every contract failure class.

The separate policy-adjusted
`quality_attribute_control_chart_phase_2_reference_policy.json` independently
checks frozen P/NP/C/U formula and strict-boundary semantics. It is classified
as policy-adjusted formula parity, not direct published-output parity, and is
is executed against the production Phase II calculator without fabricated
observations or expected results.

Primary references:

- NIST counts charts: <https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc331.htm>
- NIST proportions charts: <https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc332.htm>
- NIST Dataplot P/NP/C/U definitions: <https://www.itl.nist.gov/div898/software/dataplot/refman1/auxillar/contchar.htm>

The initial executable slice validation on 2026-07-14 passed the 17-test
Phase I method/reference suite. The contract foundation validation on
2026-07-16 passed the combined 22-test Phase I/Phase II-policy reference suite.
The subsequent immutable limit-set storage/API foundation passed full backend
pytest with 663 tests, frontend Vitest with 95 tests, the targeted 116-test
OpenAPI/frontend contract suite, production build, and Chromium critical-path
E2E including the explicit Phase I notice and a real P-chart run. Current
details are recorded in `docs/ci_status.md`. These are local Windows 10
working-tree results, not remote Actions or Windows 11 release evidence.

The executable Phase II slice passed full backend pytest with 702 tests,
frontend Vitest with 100 tests, the 120-test OpenAPI/frontend contract suite,
production build, and Chromium E2E that promotes a Phase I baseline and applies
its verified frozen limits to a separate target dataset. Current details are in
`docs/ci_status.md`.

## Limitations

- User-supplied historical or naked limits are not supported; Phase II accepts
  only verified app-created immutable limit sets.
- Only the one-point-outside-three-sigma rule is enabled; WECO/Nelson pattern
  rules are not claimed.
- Exact binomial/Poisson probability limits, Laney P'/U', rare-event charts,
  transformations, and automatic overdispersion correction are not included.
- C-chart equal opportunity is a recorded user assertion; software cannot
  infer it from a count column alone.
- The common JSON/CSV/HTML result exports are available. A separate chart image
  export artifact is not implemented.
