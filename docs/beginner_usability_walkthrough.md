# Beginner Usability Walkthrough

This checklist is for UX QA with users who do not know statistics well. It does
not add new methods or change calculations. Use it to verify that the role
guide, purpose helper, preflight explanation, and result panels keep users from
overclaiming.

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

## Experiment Condition Table

User question: What experiment runs should I perform for a two-level factorial
screening design?

Purpose helper card: create a two-level factorial design,
`doe.factorial_design`.

Needed roles: factor names, low/high levels, optional repeats, center points,
blocks, and randomization seed.

Easy wrong roles: treating response columns as factors, using unreviewed factor
units, confusing run order with standard order, or assuming response analysis is
already implemented.

Preflight checks: unique factor names, valid low/high levels, run count,
randomization seed, block/repeat settings, and whether response entry matches
all generated runs.

Read first in results: generated run table, standard order, randomized run
order, factor settings, design checksum, seed, and response-entry status.

Cannot say: effects, ANOVA, alias structure, diagnostics, RSM, or optimization
are available from the current design table alone.
