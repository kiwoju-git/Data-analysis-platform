# Gage R&R Method Contract

Updated: 2026-11-01. Method `quality.gage_rr` 0.2.0, result schema 2.
API 27 integrates this change; no SQL migration is required.

## Supported Design

Balanced crossed random-effects ANOVA requires at least two parts, two
operators and two valid measurements in every part-by-operator cell.
All cells must exist and have the same count r; N = parts * operators * r.
A 10 * 3 * 2 synthetic fixture is a test, not an assumption about user data.

Required columns are measurement, part and operator. New UI requests explicitly
use `replicate_mode=infer_from_rows` and a null replicate column. Each existing
measurement row is an observation; none is copied, averaged, interpolated or
deduplicated. The optional within-cell ordinal is not time, experimental round
or a covariance factor.

Advanced `explicit_column` requires a fourth distinct column. IDs must be unique
within each cell, but different cells may use different ID sets. Replication is
the cell observation count, not the number of global replicate labels.
Omitted mode resolves to explicit when a column is present, otherwise inferred;
an explicit contradictory mode/column pair is rejected.

Identifiers retain their full stripped strings. No case folding, numerical
coercion or display truncation is used for grouping. Original IDs are not
returned in diagnostic payloads or errors. Complete-case exclusions and counts
are recorded. Structural `balanced` and overall `ready_for_anova` are distinct;
duplicate replicate IDs or constant measurements do not falsely imply unequal
cell counts.

Nested/unbalanced REML, one-operator studies, Xbar-R, tolerance/process variation,
component confidence intervals and interaction-mean plots are not implemented.
Gage Run Chart retains its separate explicit-repeat/order contract.

## Common Preparation And Filters

`gage_rr_data.prepare_gage_data` owns measurement/identifier parsing, original
row identity, cell counts, crossing, balance and duplicate checks for both
preflight and calculation. Neither trusts a prior browser preflight.
Both use the confirmed version, schema and canonical artifact, with the same
frozen filter predicate semantics. Preflight does not create an analysis or
persistent row snapshot; it records canonical and filter hashes. Execution
preserves its normal immutable row snapshot. Role/filter/source edits invalidate
pending preflight responses.

## Interaction Policy

The API default remains `retain` for old callers that omit policy. The new UI
explicitly sends `auto_pool` and `alpha_to_remove_interaction=0.05`.
Alpha must be finite and strictly between zero and one.

The full model is always computed first. For a parts, b operators, r repeats:

| Source | DF | Raw variance |
| --- | --- | --- |
| Repeatability | ab(r-1) | MS_error |
| Part x operator | (a-1)(b-1) | (MS_interaction - MS_error)/r |
| Operator | b-1 | (MS_operator - MS_interaction)/(ar) |
| Part | a-1 | (MS_part - MS_interaction)/(br) |

With auto-pool and a finite interaction p >= alpha, interaction SS and DF are
added to error. The reduced error MS replaces the denominator for the final
part/operator F tests and their component estimates. Interaction is zero because
it was removed from the model, not because a negative estimate was clamped.
An unavailable test never triggers automatic pooling.

Raw negative component estimates remain visible; final components clamp at zero
with a persistent warning. Derived reproducibility, total GRR, total variation,
%Contribution, %StudyVar and NDC all use the same selected final components.
Zero denominators yield unavailable tests, not invented p-values.

## Storage And Reports

New results record replicate mode, sample/design diagnostics, requested and
effective policy, alpha, interaction p, pooling reason, full ANOVA, optional
reduced ANOVA, and final ANOVA in the existing `anova_table` field.
Schema 1 results remain readable as explicit-repeat/full-retain historical
results. No new defaults are injected into old stored checksum bytes.
The generic reader checks the original artifact; report coverage accepts schemas
1 and 2. Renderer 2.2.0 reads stored tables/components only and visibly identifies
full versus final ANOVA and the saved policy. It never reloads rows or recomputes
ANOVA during export. Missing interaction-mean plots remain summary limitations.

## Verification

- Original hand/reference no-pooling fixtures remain applicable.
- `test_gage_rr_three_columns.py`: independent NumPy balanced-array SS/DF/F and
  component calculations on deterministic 60-row weak/strong interaction data;
  inference versus explicit IDs, shuffle/relabel/long IDs, duplicates, missing
  cells, unequal counts, single repeats and unavailable zero-error tests.
- `test_gage_rr_followup_api.py`: real upload, filtered preflight and execution,
  immutable restore, Korean/English report policy and full/final tables.
- `GageRrPreflightPanel.test.tsx`: three-column execution enabled, explicit-mode
  fourth-column and filter validation. Browser journeys are in
  `tests/e2e/gage_followup.py`; execution status belongs to the follow-up log.

Official input and pooling policy were checked against
[Minitab input documentation](https://support.minitab.com/en-us/minitab/help-and-how-to/quality-and-process-improvement/measurement-system-analysis/how-to/gage-study/crossed-gage-r-r-study/perform-the-analysis/enter-your-data/)
and [Minitab method documentation](https://support.minitab.com/en-us/minitab/help-and-how-to/quality-and-process-improvement/measurement-system-analysis/how-to/gage-study/crossed-gage-r-r-study/methods-and-formulas/method-of-analysis/).
No same-data Minitab run was supplied or executed for this change. Existing
published rounded full-model summaries are reference evidence only; this is not
a claim of complete Minitab numerical parity or unsupported output coverage.
