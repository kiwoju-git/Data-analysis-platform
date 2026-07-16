# Attribute Control Chart Phase II Limits Contract

Last updated: 2026-07-16

## Status And Scope

The immutable limit-set storage/API foundation in this document is implemented,
but Phase II monitoring is not executable. The current
`quality.attribute_control_chart` implementation remains method version
`0.1.0`, result schema `1`, and Phase I only. Its closed analysis request model
does not accept a phase or limit-set identifier.

The first executable Phase II slice will retain the stable method ID and use:

- method version `0.2.0`;
- result schema `2`;
- immutable control-limit-set asset schema `1`; and
- an explicit Phase II request that references an app-created `limit_set_id`.

The minor method/result bump is required because the source of the center and
limits, the dependency graph, request options, result fields, and statistical
meaning change. Existing `0.1.0` results remain Phase I results and must never
be migrated or displayed as Phase II. The common analysis-run config envelope
will record the new per-method option shape when implementation begins; this
foundation does not change its current schema or stored records.

WECO/Nelson pattern rules, Laney P'/U', exact probability limits, user-entered
numeric limits, and new chart families are outside this contract.

## Immutable Limit-Set Asset

Phase II will accept only a checksum-validated limit set created by this app.
A user cannot supply naked center/LCL/UCL numbers in the first slice. Limit-set
schema `1` contains at least:

- `limit_set_id`, asset schema, method ID/version, chart type, and count
  definition;
- baseline dataset version ID, schema hash, canonical artifact SHA-256,
  filter snapshot hash, ordered row snapshot hash, and included point count;
- count-column and denominator-column IDs and their confirmed measurement
  semantics without raw values or display names;
- baseline total count and total denominator where applicable;
- frozen center, three-sigma multiplier, natural-bound policy, and the exact
  calculation policy identifier;
- fixed sample size for NP, or the recorded equal-opportunity assertion for C;
- creator app/build/runtime/package provenance, `created_at`, `closed_at`, and
  a canonical payload SHA-256.

The asset is closed and immutable after creation. Correcting the baseline,
filter, roles, or count meaning creates a new limit set with a new ID and SHA.
Existing monitoring analyses remain pinned to the prior asset. Deletion or
replacement of a referenced asset is forbidden; retention follows the same
dependency rules as stored analysis artifacts.

No original filename, internal path, raw cell value, or arbitrary row label is
stored in the asset or returned by an error.

### Implemented Storage And API Foundation

SQLite schema `13` adds `attribute_control_limit_sets`. The table pins the
source analysis/dataset, source method/result/config/schema/canonical/row
snapshot hashes, P/NP/C/U meaning, frozen center, eligibility metadata, JSON
asset path/SHA, and close time. The path remains internal and is never returned
by the API.

- `POST /api/v1/quality/attribute-control-limit-sets` promotes one eligible
  app-created Phase I analysis. Repeating the same source analysis returns the
  same verified immutable asset.
- `GET /api/v1/quality/attribute-control-limit-sets/{limit_set_id}` restores
  after file checksum, DB/file relationship, and live source dependency checks.
- `GET /api/v1/quality/attribute-control-limit-sets` lists verified assets with
  optional source dataset and chart-type filters plus pagination.
- No PUT, PATCH, or DELETE route exists. No monitoring/execution route exists.

Promotion policy `phase_2_baseline_eligibility_v1` requires at least 20 complete
points, a complete untruncated point payload, no Phase I limit signal, usable
binomial/Poisson normal-approximation counts, and Pearson dispersion no greater
than 2. Center, point values/limits, dispersion, strict signal status, totals,
and fixed NP sample size are independently recomputed from the stored point
payload before promotion. These conservative gates avoid freezing a visibly
unstable or statistically weak baseline without an acknowledgment contract.

Restore also revalidates the source result/config/row snapshot/schema/canonical
relationships. Consequently list/restore perform full canonical artifact
verification and may be I/O-bound for large baselines; no unsafe verified-cache
is introduced in this slice.

## Monitoring Request And Dependency Gates

An executable Phase II request will explicitly select Phase II and provide a
`limit_set_id`. Before calculation, the service validates the asset checksum,
method/version, chart/count semantics, baseline dataset dependency, column
IDs, and target dataset schema/canonical artifact dependency. It never falls
back to estimating limits from monitoring rows.

The monitoring analysis persists both the limit-set ID and SHA plus the target
dataset version/schema/canonical SHA and row/filter snapshot. Restore and
export revalidate the same relationships.

Stable storage error meanings implemented by the limit-set APIs are:

- `attribute_control_chart_limit_set_missing`
- `attribute_control_chart_limit_set_invalid`
- `attribute_control_chart_limit_set_checksum_mismatch`
- `attribute_control_chart_limit_set_source_schema_mismatch`
- `attribute_control_chart_limit_set_source_analysis_missing`
- `attribute_control_chart_limit_set_source_analysis_invalid`
- `attribute_control_chart_limit_set_source_analysis_stale`
- `attribute_control_chart_limit_set_source_ineligible`
- `attribute_control_chart_limit_set_source_artifact_mismatch`
- `attribute_control_chart_limit_set_metadata_invalid`
- `attribute_control_chart_limit_set_source_dependency_mismatch`

Monitoring-specific meanings reserved for the executable slice are:

- `attribute_control_chart_limit_set_method_version_mismatch`
- `attribute_control_chart_limit_set_chart_type_mismatch`
- `attribute_control_chart_limit_set_count_definition_mismatch`
- `attribute_control_chart_phase_2_target_schema_mismatch`
- `attribute_control_chart_phase_2_np_sample_size_mismatch`
- `attribute_control_chart_phase_2_c_opportunity_confirmation_required`

The current Phase I analysis endpoint still has no Phase II request shape.
Storage-specific codes are exposed only by the implemented limit-set APIs;
monitoring-specific codes remain reserved until the executable Phase II slice.

## Frozen-Limit Calculations

Let the immutable baseline provide frozen `pbar`, `npbar`, `cbar`, or `ubar`.
Monitoring points are evaluated in canonical target-row order. A signal occurs
only when the value is strictly outside its limits; equality is not a signal.
The baseline is never refit and signaled monitoring points are never removed.

- P: reuse frozen `pbar`; for each current positive integer sample size `n_i`,
  use `pbar +/- 3*sqrt(pbar*(1-pbar)/n_i)`, bounded to `[0, 1]`.
- NP: reuse frozen `npbar` and its frozen fixed sample size `n`. Every current
  sample size must equal `n`, otherwise reject the run. Limits remain
  `npbar +/- 3*sqrt(n*pbar*(1-pbar))`, bounded to `[0, n]`.
- C: reuse frozen `cbar` and fixed limits `cbar +/- 3*sqrt(cbar)`, with LCL
  bounded at zero. The user must confirm that current inspection opportunity
  matches the baseline definition; software cannot prove this from counts.
- U: reuse frozen `ubar`; for each current positive finite opportunity `n_i`,
  use `ubar +/- 3*sqrt(ubar/n_i)`, with LCL bounded at zero.

A baseline with zero or unusable estimated variance is invalid and cannot be
promoted to a limit set. Dispersion diagnostics remain warnings and do not
silently switch chart family or adjust limits.

## Result And UI Contract

Result schema `2` will distinguish `phase_1_estimated_three_sigma` from
`phase_2_frozen_three_sigma` and include a typed limit-set dependency block.
The UI will show Phase I/Phase II as an explicit mode, identify the frozen
limit-set source and baseline close time, and distinguish current monitoring
data from baseline history. Phase II execution must require a deliberate asset
selection and show incompatibility before the run button is enabled.

Until that slice exists, the current panel must say that it executes Phase I
only, estimates limits from all filtered valid observations, and does not apply
stored Phase II limits.

## Reference And Acceptance Criteria

`quality_attribute_control_chart_phase_2_reference_policy.json` is a synthetic,
hand-checkable policy fixture. It independently evaluates P/NP/C/U frozen-limit
formulas and strict signal behavior from the NIST definitions. It is
policy-adjusted formula parity, not a claim of direct published output parity.

The storage/API foundation has completed items 1-3, controlled frontend client
types for the asset API, and its own full local validation. The monitoring
vertical slice remains responsible for items 4-7 and must rerun item 7 after
adding executable behavior:

1. a SQLite migration and immutable limit-set create/get/list contract;
2. schema/hash/relation tamper tests and previous-schema upgrade coverage;
3. Phase I baseline promotion with explicit eligibility and no overwrite;
4. typed Phase II monitoring request/result/frontend types and OpenAPI alignment;
5. P/NP/C/U reference, boundary, mismatch, restore, export, and redaction tests;
6. a UI current/history selector with preflight incompatibility feedback;
7. full `scripts/check.ps1`, browser E2E, and Windows 11 release-gate evidence.

Primary formula references:

- NIST counts charts: <https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc331.htm>
- NIST proportions charts: <https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc332.htm>
- NIST P/NP/C/U definitions: <https://www.itl.nist.gov/div898/software/dataplot/refman1/auxillar/contchar.htm>
