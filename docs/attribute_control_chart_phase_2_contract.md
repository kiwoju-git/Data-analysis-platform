# Attribute Control Chart Phase II Limits Contract

Last updated: 2026-07-17

## Status And Scope

The immutable limit-set storage/API foundation and first Phase II monitoring
vertical slice are implemented. `quality.attribute_control_chart` retains its
stable method ID and uses:

- method version `0.3.0`;
- result schema `3`;
- immutable control-limit-set asset schema `1`; and
- an explicit Phase II request that references an app-created `limit_set_id`.

The current minor bump from `0.2.0`/schema `2` to `0.3.0`/schema `3` adds a
typed unavailable-dispersion state and permits one valid Phase II monitoring
point. Existing `0.1.0`/schema `1` Phase I and `0.2.0`/schema `2` Phase I/II
results restore without relabeling or rewriting. Limit-set asset schema `1`,
its checksum meaning, the common analysis-run config schema `2`, and SQLite
schema `14` are unchanged. New Phase I executions use `0.3.0`/schema `3`, and
promotion accepts the corresponding source in addition to both older forms.

WECO/Nelson pattern rules, Laney P'/U', exact probability limits, user-entered
numeric limits, and new chart families are outside this contract.

## Immutable Limit-Set Asset

Phase II accepts only a checksum-validated limit set created by this app.
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
- `POST /api/v1/quality/attribute-control-limit-sets/{limit_set_id}/monitoring-preflight`
  verifies target dataset and column compatibility before execution.
- Phase II executes through `POST /api/v1/analysis-runs` with an explicit
  `phase=phase_2` and verified `limit_set_id`.
- No PUT or PATCH route exists. Checksum-validated deletion preflight and
  exact-confirmation DELETE routes are implemented; deletion is blocked while
  any Phase II analysis references the limit set.

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

An executable Phase II request explicitly selects Phase II and provides a
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

Monitoring-specific stable meanings are:

- `attribute_control_chart_limit_set_method_version_mismatch`
- `attribute_control_chart_limit_set_chart_type_mismatch`
- `attribute_control_chart_limit_set_count_definition_mismatch`
- `attribute_control_chart_phase_2_target_schema_mismatch`
- `attribute_control_chart_phase_2_np_sample_size_mismatch`
- `attribute_control_chart_phase_2_c_opportunity_confirmation_required`
- `attribute_control_chart_phase_2_dependency_mismatch`
- `attribute_control_chart_phase_2_no_usable_points`

Preflight returns compatibility issues without creating an analysis. Execution
returns the same stable codes and never falls back to Phase I estimation.
Preflight schema `2` explicitly reports
`validation_scope=schema_and_dependency_only` and `row_data_validated=false`.
`ready=true` means the asset, target schema, canonical dependency, and selected
columns are structurally compatible; it does not promise calculation success.
Execution always revalidates NP sample-size equality, integer/count bounds,
denominators, C opportunity confirmation, exclusions, filters, and usable N.

## Frozen-Limit Calculations

Let the immutable baseline provide frozen `pbar`, `npbar`, `cbar`, or `ubar`.
Monitoring points are evaluated in canonical target-row order. Phase II needs
at least one valid monitoring point; Phase I estimation still needs at least
two, and limit-set promotion still needs at least 20. A signal occurs
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
promoted to a limit set. With one Phase II point, frozen limits and strict
signals are stored while dispersion is `available=false`, has zero degrees of
freedom, a null ratio, and reason
`attribute_control_chart_dispersion_insufficient_points`. No zero, NaN,
infinity, or fabricated ratio is used. At two or more points the existing
Pearson calculation remains available. Dispersion never changes the limits.

## Result And UI Contract

Result schema `3` distinguishes `phase_1_estimated_three_sigma` from
`phase_2_frozen_three_sigma` and includes typed limit-set and target dependency
blocks. Restore and every JSON/CSV/HTML export revalidate those relationships.
The UI shows Phase I/Phase II as an explicit mode, identifies the frozen
limit-set source and baseline close time, and distinguishes current monitoring
data from baseline history. Phase II execution must require a deliberate asset
selection and show incompatibility before the run button is enabled.
The UI always states that preflight covers structure/dependencies only and
renders the one-point dispersion state as unavailable rather than a number.

## Reference And Acceptance Criteria

`quality_attribute_control_chart_phase_2_reference_policy.json` is a synthetic,
hand-checkable policy fixture. It independently evaluates P/NP/C/U frozen-limit
formulas and strict signal behavior from the NIST definitions. It is
policy-adjusted formula parity, not a claim of direct published output parity.

The storage/API foundation and monitoring vertical slice complete items 1-6.
For item 7, local `scripts/check.ps1` and browser E2E are complete; the actual
Windows 11/Python 3.10/Node 22 evidence remains a mandatory release gate and
remote Actions remain independently unverified. Exact evidence is recorded in
`docs/ci_status.md` for each validated commit/worktree:

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
