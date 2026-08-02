# Equivalence Test Contract

Last updated: 2026-08-02

## Methods

| Method ID | Version | Design |
| --- | --- | --- |
| `hypothesis.equivalence_tost` | new writes `0.2.0`; legacy `0.1.0` readable | one-sample mean minus reference |
| `hypothesis.two_sample_equivalence_tost` | `0.1.0` | independent test mean minus reference mean |
| `hypothesis.paired_equivalence_tost` | `0.1.0` | paired test measurement minus reference measurement |

All new results use schema `2`, raw difference units, explicit lower and upper
bounds, and `confidence_level = 1 - 2 alpha`. Both one-sided null hypotheses
must be rejected at alpha before the UI says `동등성 근거 있음`.
Non-significance in an ordinary difference test is never treated as evidence
of equivalence.

## Independent Two-Sample Policy

Long-format input must contain exactly two usable groups. Users select the test
and reference group; the sign is always test minus reference. Welch is the
default and uses the Satterthwaite df. Pooled variance is available only as an
explicit user choice. Group levels come from the bounded, filtered preflight.

## Paired Policy

P0 uses two wide numeric columns. Each row defines a pair and the difference is
test minus reference. A row with either value missing is excluded as an
incomplete pair, and total, complete, incomplete, test-missing, and
reference-missing counts are reported.

## Result Contract

Schema `2` records the design and estimate definition, alpha and confidence
level, bounds, sample summaries, estimate/SE/df, lower and upper one-sided
tests, TOST p-value/decision, confidence interval and whether it is inside the
bounds, exclusions, warnings, and package provenance. Two-sample results also
record the variance model and group direction; paired results record both
source columns and complete-pair counts.

The accessible Equivalence Plot shows the two bounds, zero reference, point
estimate, and TOST confidence interval. Its text description carries the same
numbers and decision, so color is not the only cue.

## Excluded P1 Scope

Ratio/log-ratio margins, noninferiority/superiority-only interfaces, power and
sample size, summarized-data input, long-format pair IDs, crossover designs,
and nonparametric equivalence remain separately versioned future work. Bounds
are never estimated from the observed result.

Numerical and API tests are in `backend/tests/unit/test_equivalence_tost.py`
and `backend/tests/unit/test_api_contracts.py`; frontend coverage is in
`frontend/src/equivalenceDesigns.test.tsx`.
