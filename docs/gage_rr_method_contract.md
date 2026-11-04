# Gage R&R Method Contract

Updated: 2026-11-05. Method `quality.gage_rr` 0.3.1, result schema 4.
API29 corrects saved part identity/order (plot bundle2); metadata24 is unchanged.
The schema-2 full/final ANOVA, pooling and variance-component calculations are unchanged.

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
coercion or display truncation is used for grouping. Original part IDs are now
saved deliberately in new result/report plot summaries. Operator/replicate IDs
remain redacted, as do all original IDs in preflight, errors and support diagnostics.
Complete-case exclusions and counts
are recorded. Structural `balanced` and overall `ready_for_anova` are distinct;
duplicate replicate IDs or constant measurements do not falsely imply unequal
cell counts.

Nested/unbalanced REML, one-operator studies, the Xbar-R Gage variance-estimation
method, tolerance/process variation and component confidence intervals are not implemented.
The new R/S and Xbar panels are diagnostics of the existing ANOVA study, not an
alternative Xbar-R Gage estimation method or process-stability assessment.
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

## Saved Six-Panel Bundle

`gage_rr_plots.build_gage_rr_plot_bundle` runs once after selection of the final
ANOVA/components, using the same `PreparedGageData` observations. It does not refit,
replace measurements, reread source rows, or alter selected ANOVA values.
`plot_bundle.schema_version=2` is validated by `GageRrPlotBundle` and by the saved
result envelope. Numeric fields are finite or explicitly null with an unavailable
reason. Each part summary preserves a required unique full string `part_id`.
The plot builder, not statistical preparation, sorts parts by ASCII digit runs
with a full-string tie-break: 1,2,...,10 and P1,P2,P10. IDs remain categorical:
`1` and `01` are distinct. No int/float grouping, case folding or new trimming.
Zero-based plot indices refer to this same mapping across every panel. Operator
indices retain the prior sorted order; operator/replicate strings remain absent.
Policy: `natural_ascii_digit_runs_full_identity_v1` and
`part_ids_preserved_operator_replicate_redacted`. Measurement name/unit
and original `source_row_number` remain available; these indices are not time.

The six panels are:

- Components: total GRR, repeatability, reproducibility and part-to-part. Adjacent
  %Contribution/%StudyVar series copy the selected components' existing percentages;
  they are not multiplied by100 again or normalized to sum to100.
- Within-cell dispersion: r2..8 uses each cell's max-minus-min, pooled mean range,
  and the existing three-decimal D3/D4 constants. Policy is
  `within_cell_range_d3_d4_v1`; r2 has D3=0 and D4=3.267. r>=9 uses ddof1 cell SD,
  mean of all cell SDs and c4 computed with log-gamma. B3=max(0,1-3*sqrt(1-c4^2)/c4),
  B4=1+3*sqrt(1-c4^2)/c4. The c4 domain is(0,1]; only an excess of up to64
  machine epsilons above1 is treated as roundoff. Invalid constants make the
  dispersion plot unavailable without hiding ANOVA. Zero within-cell variation keeps real zero limits and
  adds `within_cell_variation_zero`, not an invented positive range.
- Xbar: actual cell means, overall grand mean and limits
  grand mean +/-3*selected final repeatability SD/sqrt(r). The source is
  `selected_anova_repeatability`; flags are `outside_repeatability_limits`,
  not process signals. Pooling can change these limits without changing cell means.
- Response by part: actual individual measurements and whole-data part means.
- Response by operator: all individual measurements contribute to type7 linear
  quartiles, mean, 1.5-IQR fences and observed in-fence whiskers. Outlier counts
  cover all values, not cell averages. For very small samples an observed whisker
  may lie inside an interpolated quartile; it is not replaced with a fabricated value.
- Interaction: actual part-by-operator cell means remain visible even when
  interaction was pooled out of the selected ANOVA model.

All cell counts/means/ranges/sample SDs, part/operator summaries, measurement extrema,
limits, box summaries and full outlier counts use all used observations before any
display limit. The raw-point cap is5000 with deterministic cell-stratified quotas
and evenly spaced original-row selections within each cell. Counts, truncation,
limit and selection policy are saved. Box outlier markers use the same selected raw
view; full outlier counts remain separate from displayed counts. This cap does not
change analysis N, ANOVA, summaries or Y-axis extrema. Plot-only overflow becomes
an explicit unavailable plot, not non-finite JSON or a replacement ANOVA failure.

## Storage And Reports

New results record replicate mode, sample/design diagnostics, requested and
effective policy, alpha, interaction p, pooling reason, full ANOVA, optional
reduced ANOVA, and final ANOVA in the existing `anova_table` field.
Schema1/2/3 results remain readable using their original policy and stored bytes.
Missing plot bundles are not rebuilt from today's dataset or filled with current
defaults. The reader checks the original artifact checksum and validates schema3/4
bundle identity/count/component/policy relationships without mutating the result.
Reports read stored plot values and identify full versus final ANOVA and the saved
policy. Schema1/2 can show stored components but retain unavailable notices for
the five raw-observation-dependent panels. Export does not reload rows or compute ANOVA.

HTML renderer 2.3.1 displays the six saved sections in row-pair order: components /
response by part; R or S / response by operator; Xbar / interaction. Larger
studies use explicit print pages with unchanged global ranges and limits; all
cell summaries remain available in tables. A well-formed schema3/4 result with
all six available panels is `full`; legitimate unavailable summaries yield
`summary`, and malformed bundles are `unsupported`, not blank full reports.
Legacy missing-panel reason is `gage_plot_bundle_not_stored_reanalysis_required`.
All visible text, SVG titles, units and names are escaped and localized; exports
remain offline inline SVG without a script, CDN or calculation dependency.

Result3/plot1 has no original part IDs. Its charts say Display N / 표시번호 N,
explain that these are not the original IDs, and offer reanalysis guidance.
Do not infer an ID from an index or reload current source rows to modify a saved
result. New missing/duplicate part IDs are invalid, not a legacy fallback.
Long IDs remain available in a full-ID table and point details even when axis
labels are shortened. Operator identity privacy is not broadened by this change.

## Verification

- Original hand/reference no-pooling fixtures remain applicable.
- `test_gage_rr_three_columns.py`: independent NumPy balanced-array SS/DF/F and
  component calculations on deterministic 60-row weak/strong interaction data;
  inference versus explicit IDs, shuffle/relabel/long IDs, duplicates, missing
  cells, unequal counts, single repeats and unavailable zero-error tests.
- `test_gage_rr_followup_api.py`: real upload, filtered preflight and execution,
  immutable schema1/2/3 restore, filtered original-row identity, Korean/English
  report policy and full/final tables.
- `test_gage_rr_plots.py`: independent60-row additive reference (Rbar0.2,
  R-UCL0.6534, grand mean59, full MSE0.02 and pooled MSE0.0125), strong interaction,
  r3/r9 constants, raw operator quantiles/outliers, zero variation, shuffle and
  explicit/inferred parity, long-label privacy,6000-row display cap invariance,
  finite-only extreme summaries and malformed bundle rejection.
- `tests/fixtures/gage_rr_six_panel.json` is an application-generated synthetic
  UI/report fixture, not an independent numerical reference. The hand expectations
  above are asserted separately from that file.
- `test_gage_rr_plot_report.py`: six visible HTML sections, saved SVG point/limit/
  whisker geometry, pooled actual cell means, R/S and zero-limit semantics,
  whole-summary pagination beyond the raw display cap, Korean/English escaping,
  legacy/malformed capability and unchanged source checksum. Forbidden fit and
  source-row reads are patched to fail during export.
- `GageRrPreflightPanel.test.tsx`: three-column execution enabled, explicit-mode
  fourth-column and filter validation. Browser journeys are in
  `tests/e2e/gage_followup.py`; execution status belongs to the follow-up log.

Official input and pooling policy were checked against
[Minitab input documentation](https://support.minitab.com/en-us/minitab/help-and-how-to/quality-and-process-improvement/measurement-system-analysis/how-to/gage-study/crossed-gage-r-r-study/perform-the-analysis/enter-your-data/)
and [Minitab method documentation](https://support.minitab.com/en-us/minitab/help-and-how-to/quality-and-process-improvement/measurement-system-analysis/how-to/gage-study/crossed-gage-r-r-study/methods-and-formulas/method-of-analysis/).
No same-data Minitab run was supplied or executed for this change. Existing
published rounded full-model summaries are reference evidence only; this is not
a claim of complete Minitab numerical parity or unsupported output coverage.
