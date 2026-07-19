# Beginner Usability Walkthrough

This checklist is for UX QA with users who do not know statistics well. It does
not add new methods or change calculations. Use it to verify that the role
guide, purpose helper, preflight explanation, and result panels keep users from
overclaiming.

For a complete Korean task sequence with deterministic synthetic files and
API-verified expected values, use
`docs/studio_end_to_end_tutorial_ko.md`. This checklist remains the UX QA
acceptance companion rather than the user tutorial itself.

## Spreadsheet Paste Review

User task: copy a rectangular range from Excel or another spreadsheet, review
its apparent structure, then register it for authoritative parsing.

QA pass criteria:

- The empty paste surface can receive keyboard focus and `Ctrl+V` without a
  browser Clipboard permission prompt.
- A view-only grid appears immediately with A/B/C column letters, row numbers,
  visible empty cells, ragged-row markers, truncation warnings, and a selected
  cell inspector.
- Grid and raw modes are both available. Formula-like and HTML-looking text is
  displayed literally and is never executed or rendered as markup.
- The first-row-as-header switch clearly says it changes presentation only.
  After registration, any difference from the server header suggestion is
  visible and the parsing-confirmation controls remain authoritative.
- A failed registration keeps the current draft for correction/retry. A
  successful registration clears it, and reloading the application never
  restores raw pasted text from browser storage.
- After parsing confirmation, page size 10/25/50/100, row jump, sticky headers,
  explicit missing values, and the canonical selected-cell inspector work
  without loading the whole dataset.

Fail examples:

- The request is rebuilt from preview cells, changing CRLF, quotes, trailing
  tabs, or empty cells.
- Clipboard HTML is interpreted, formula text runs, or a pasted value is sent
  to logs/storage/telemetry.
- A capped preview is presented as the complete source, or the staging header
  toggle silently confirms server parsing.

Recovery: use **원문 보기** to inspect ambiguous quotes or delimiters, **다시
붙여넣기** to replace the current transient draft, and the parsing-confirmation
panel to set the authoritative delimiter/header/missing-token options. Cell
editing is not available in P0.

## Two Group Mean Comparison

User question: Are the average measurements different between two independent
groups?

Purpose helper card: compare two group means, `hypothesis.two_sample_t`.

Needed roles: one numeric response column and one group column with exactly two
usable groups.

Easy wrong roles: putting before/after columns into Group, using an ID as Group,
or using a categorical pass/fail field as the numeric Response.

Preflight checks: group count, group sizes, missing/non-numeric exclusions,
Welch default, alpha, alternative, confidence level, and whether independence is
a study-design assumption.

Read first in results: mean difference estimate, confidence interval, Hedges g,
group sizes, exclusions, warnings, then p-value.

Cannot say: this proves causation, this proves the groups are equivalent, or the
software proved independence.

QA pass criteria:

- The purpose helper can take a beginner to the two-sample t-test without using
  statistical jargon as the only cue.
- The role guide names Response and Group, and warns that before/after columns
  are not independent groups.
- The preflight area keeps Welch, alpha, alternative, confidence level,
  group-size, exclusion, and independence-assumption context visible before run.
- The result panel makes estimate, CI, Hedges g, N/exclusions, and warnings
  visible before or alongside p-value.

Fail examples:

- A pass/fail text column can be selected as Response without a visible warning.
- A paired before/after table can be run as independent two-group data without
  corrective copy.
- The user can only see p-value and cannot find effect size or exclusions.

UX copy that must remain visible: the role guidance for Response / Group,
the preflight statement that independence is a design assumption, the Welch
default, and the warning that diagnostics do not automatically switch methods.

UI element to inspect: `MethodPurposeHelper`, `StatisticalRoleGuide`,
`PreflightExplanationPanel`, `TwoSampleTPanel`, result warnings, and
`AnalysisHistoryPanel` after saving/restoring.

Recovery from wrong role: the user should be able to return to the role guide,
switch the selected columns in the two-sample t-test panel, or choose the paired
t-test card if the data are before/after measurements. No result should be
created until the corrected roles pass preflight.

## Process Stability Check

User question: Is my process stable over collection order or time?

Purpose helper card: check process stability over order/time,
`quality.individuals_chart` or `quality.run_chart`.

Needed roles: one numeric measurement column; optional order or timestamp column
when row order is not the real collection order.

Easy wrong roles: using a nominal batch label as the measurement, using a group
column as order, or treating specification limits as control limits.

Preflight checks: row order, missing/non-numeric exclusions, constant values,
point limit, order-column parsing, and which rule families are being evaluated.

Read first in results: center line, limits or run summaries, signal list with
row indexes, N used/excluded, and warnings.

Cannot say: the product meets customer specification, the process is capable, or
the root cause of a signal is known from the chart alone.

QA pass criteria:

- The purpose helper separates process stability from specification capability.
- The role guide makes Measurement and optional Order visible.
- The preflight copy tells the user whether row order or the chosen order column
  will be used.
- Results show signal rows, N/exclusions, and warnings without exposing raw
  private records in the checklist.

Fail examples:

- A batch/category column is treated as the measured value without warning.
- The user confuses LSL/USL with control limits because the copy does not
  distinguish them.
- A chart signal is described as a root cause.

UX copy that must remain visible: order/time guidance, control-limit versus
specification-limit distinction, and the limitation that charts do not prove root
cause.

UI element to inspect: `MethodPurposeHelper`, `StatisticalRoleGuide`,
`PreflightExplanationPanel`, `IndividualsChartPanel`, `RunChartPanel`, and
signal/warning rows in the result panel.

Recovery from wrong role: the user should be able to change the measurement or
order column in the chart panel, return to the purpose helper for capability if
they actually mean LSL/USL, and rerun only after the preflight copy matches the
question.

## Specification Capability Check

User question: Does the process output fit within LSL/USL requirements?

Purpose helper card: check specification capability, `quality.capability`.

Needed roles: one numeric measurement column and at least one explicit LSL or
USL; optional target.

Easy wrong roles: entering control limits as LSL/USL, choosing a text status
field as the measurement, or leaving units ambiguous.

Preflight checks: complete-case N, missing/non-numeric exclusions, one-sided vs
two-sided spec, target inside spec, zero variance, stability warnings, and
normal-capability limitation.

Read first in results: observed nonconformance, expected nonconformance,
Cp/Cpk/Pp/Ppk where available, histogram/spec-line context, N/exclusions, and
warnings.

Cannot say: non-normal capability is covered, capability indices have
confidence intervals, or the process is stable unless stability was checked
separately.

QA pass criteria:

- The purpose helper points to `quality.capability`, not a control chart, for
  LSL/USL questions.
- The role guide keeps Measurement and specification limits separate from
  control limits.
- The preflight area blocks or warns on missing specs, invalid numeric specs,
  target outside spec, zero variance, and normal-capability limitations.
- The result panel shows observed and expected nonconformance, indices,
  N/exclusions, and warnings before any broad accept/reject language.

Fail examples:

- A user can type nonnumeric LSL/USL and still run without a clear correction.
- Capability output implies process stability without a separate stability
  check.
- The UI claims non-normal capability or confidence intervals that are not
  implemented.

UX copy that must remain visible: "LSL/USL/Target", normal capability
limitation, target warning copy, and the statement that stability should be
checked separately.

UI element to inspect: `MethodPurposeHelper`, `StatisticalRoleGuide`,
`PreflightExplanationPanel`, `CapabilityPanel`, histogram/spec-line result
context, warnings, and export panel after a saved result.

Recovery from wrong role: the user should be able to reselect the measurement,
clear or correct LSL/USL/Target, move to a process-stability card when they used
control limits, and rerun only after corrected numeric specs pass preflight.

## Measurement System Reliability Check

User question: Can I trust the measurement system compared with part and
operator variation?

Purpose helper card: assess measurement-system variation, `quality.gage_rr`.

Needed roles: numeric measurement, part ID, operator ID, and replicate ID in a
balanced crossed design.

Easy wrong roles: using row order as replicate when it is not a replicate ID,
using measurement as part ID, mixing nested and crossed designs, or using
unbalanced observations.

Preflight checks: balanced crossed cell counts, duplicate/missing identifiers,
replicate count, complete-case exclusions, numeric measurement, and redacted
label handling.

Read first in results: preflight issues, ANOVA table, variance components,
percent contribution, percent study variation, ndc, N/exclusions, and warnings.

Cannot say: nested/unbalanced Gage R&R is supported, operator labels reveal
people, or the chart alone replaces variance-component analysis.

QA pass criteria:

- The purpose helper and role guide make Measurement, Part ID, Operator ID, and
  Replicate ID distinct.
- The Gage R&R preflight visibly rejects unbalanced crossed data before running.
- Result copy keeps ANOVA table, variance components, percent study variation,
  ndc, N/exclusions, and warnings visible.
- Operator/part labels remain redacted where the current UI promises redaction.

Fail examples:

- A row number can be mistaken for replicate ID without visible recovery copy.
- The UI suggests nested or unbalanced Gage R&R is supported.
- Operator names appear in a diagnostic area that should be redacted.

UX copy that must remain visible: balanced crossed design requirement,
Measurement / Part / Operator / Replicate role labels, preflight issue copy, and
the limitation that nested/unbalanced Gage R&R is out of scope.

UI element to inspect: `MethodPurposeHelper`, `StatisticalRoleGuide`,
`PreflightExplanationPanel`, `GageRrPreflightPanel`, `GageRrPanel` result table,
and warnings.

Recovery from wrong role: the user should be able to return to role selection,
replace the mistaken ID column, rerun preflight, and see the run action remain
blocked until the balanced crossed design requirement is satisfied.

## Experiment Condition Table

User question: What experiment runs should I perform for a two-level factorial
screening design, and which factors affect the response?

Purpose helper card: create and analyze a two-level factorial design,
`doe.factorial_design`.

Needed roles: factor names, low/high levels, optional repeats, center points,
blocks, randomization seed, and one complete numeric response series.

Easy wrong roles: treating response columns as factors, using unreviewed factor
units, confusing run order with standard order, or treating an outcome as a
controllable factor.

Preflight checks: unique factor names, valid low/high levels, run count,
randomization seed, block/repeat settings, response completeness, interaction
order, model rank, and residual degrees of freedom.

Read first in results: generated run table and checksum, effect ranking, model
and residual degrees of freedom, ANOVA/pure-error/lack-of-fit availability,
warnings, and residual diagnostics.

Cannot say: an effect proves causation outside the randomized design, an absent
p-value means no effect, or fractional alias analysis and optimization are
available from the factorial panel.

QA pass criteria:

- The purpose helper routes design-and-effect questions to
  `doe.factorial_design` and distinguishes it from the dedicated RSM panel.
- Factor name, low/high level, unit, repeat, center point, block, randomization,
  and seed inputs are visible and recoverable before generation.
- The generated table clearly distinguishes standard order from randomized run
  order and displays a stable design checksum.
- Response-entry status, interaction-order policy, effect ranking, ANOVA,
  diagnostics, and persistent warnings are visible.

Fail examples:

- The UI suggests optimization can be run from the current factorial model, or
  fabricates p-values for a saturated model.
- Duplicate factor names or invalid low/high levels produce unclear errors.
- The user cannot tell whether randomization was enabled or which seed was used.

UX copy that must remain visible: "2-level full factorial", run order versus
standard order language, design checksum, seed/randomization copy, response
entry status, -1/+1 coding, hierarchy, effect/ANOVA/diagnostic labels, and the
separate-RSM/optimization boundary.

UI element to inspect: `MethodPurposeHelper`, `StatisticalRoleGuide`,
`PreflightExplanationPanel`, `FactorialDesignPanel`, run table preview, response
entry section, effect/main-effect charts, ANOVA table, diagnostics, and design
report/export affordances.

Recovery from wrong role: the user should be able to rename factors, correct
low/high values and units, toggle randomization or seed, regenerate the design,
save a complete response, choose an interaction order, and rerun analysis only
on a new immutable design version when observations must change.

## Response Surface Process Window

User question: How does a curved process response change across two or more
continuous factors, and is the fitted stationary point inside the tested region?

Purpose helper card: model a curved process response, `doe.response_surface`.

Needed roles: two to five continuous factor names and actual safe low/high
bounds, seeded run order, and a complete numeric response for every CCD run.

Read first in results: CCD type and axial distance, factorial/axial/center run
labels, residual degrees of freedom, full-quadratic coefficients, lack-of-fit,
stationary classification and design-region flag, contour slice policy, and
persistent diagnostics warnings.

Cannot say: the stationary point is an approved optimum, the model is causal,
or predictions outside the declared design region are supported.

QA pass criteria:

- `localhost:5173` and `127.0.0.1:5173` both show `API ready` while the backend
  remains loopback-only.
- Rotatable CCI states that axial points equal the declared low/high bounds.
- All generated run responses must be present before analysis is enabled.
- The result exposes full-quadratic/no-automatic-selection policy, contour,
  stationary point, design-region status, fit, term, and diagnostic sections.
- Response optimization is available only after a verified RSM fit and remains
  separate from the stationary-point diagnostic.
- The optimizer exposes objective limits, factor bounds, constraints, search
  budgets, individual/composite desirability, and persistent limitations.
- The recommendation explicitly denies a global-optimum guarantee and requires
  model review plus a confirmation experiment.

UI element to inspect: `MethodPurposeHelper`, `StatisticalRoleGuide`,
`ResponseSurfacePanel`, `ResponseOptimizerPanel`, CCD run table, contour SVG,
term table, stationary-point summary, optimizer bounds/objective controls,
recommended settings, desirability table, and residual diagnostic summary.

Recovery from wrong role: correct factor names/bounds before generating a new
immutable CCD, then enter the complete response series and refit the model.
Invalid optimizer thresholds, bounds, or linear constraints should leave the
verified RSM result intact so the user can correct only the optimizer request.
