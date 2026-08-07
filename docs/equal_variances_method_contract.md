# Equal Variances Method Contract

Status: implemented. Current method version: `eda.equal_variances` `0.2.0`.

Primary references:

- Minitab, *Methods and formulas for Test for Equal Variances*:
  https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/anova/how-to/test-for-equal-variances/methods-and-formulas/methods-and-formulas/
- Minitab, *Multiple Comparisons Method for Equal Variances* white paper:
  https://support.minitab.com/en-us/minitab/media/pdfs/translate/Multiple_Comparisons_Method_Test_for_Equal_Variances.pdf

## Scope

`POST /api/v1/analysis-runs` accepts one numeric response, one non-ID group,
`0 < alpha < 1`, and complete-case handling. Calculation reads only confirmed
canonical rows and records all missing/non-numeric exclusions.

Schema 2 has two primary results:

1. `multiple_comparisons`: Bonett pair comparisons with the Minitab-described
   trimmed-center pooled fourth-moment scale and Nakayama/Tukey-Kramer normal
   range adjustment. For two groups the normal critical value and two-group
   interval allocation are used; for more than two groups the infinite-df
   studentized-range critical value and group allocations are used.
2. `levene`: median-centered Brown-Forsythe modification of Levene's test,
   exposed as `levene_brown_forsythe`.

The classical mean-centered Levene result remains under `additional_tests` as
`levene_mean`; it is never labeled or interpreted as the multiple-comparisons
procedure.

## Multiple Comparisons Result

The payload contains the overall adjusted p-value, each group's sample standard
deviation, its multiple-comparison interval, pairwise adjusted p-values, and
non-overlapping pairs. The overall p-value is the minimum family-adjusted pair
p-value. A `computed=false` result stores a stable warning rather than a fake
zero, infinity, or p-value.

The Minitab trimming proportion `1 / (2 sqrt(n) - 4)` is used. Because that
procedure and the reference method are not supported for very small groups,
the implementation requires at least 10 usable observations per group for the
multiple-comparisons result. Brown-Forsythe Levene remains separately
available when its own minimum conditions are met.

Intervals are comparison intervals, not ordinary confidence intervals for one
population standard deviation. When the multiple-comparisons method is the
chosen basis, non-overlap identifies a significant pair. When Levene is the
chosen basis for small, skewed, or heavy-tailed samples, these intervals must
not be used to infer significant individual pairs.

## Result Schemas And Compatibility

- schema 2: `multiple_comparisons`, `levene`, `additional_tests`, group
  summaries, exclusions, package versions, and stable warnings;
- schema 1: the original `brown_forsythe` plus mean-centered `levene_mean`
  rows remain readable with their original names and meaning.

Existing schema-1 files, method versions, and checksums are not rewritten.
Schema 2 includes a compatibility `tests` list for existing generic report and
comparison readers, but its primary user interface reads the named fields.

## UI And Interpretation

The default table shows `다중 비교` with no fabricated test statistic and
`Levene 검정 (Brown-Forsythe)` with F statistic and p-value. The interactive
interval chart uses the stored group intervals and supports roving keyboard
focus, persistent detail, and non-overlap metadata. No result automatically
switches a later t-test or ANOVA method.

## Verification

- `backend/tests/unit/test_equal_variances.py` verifies SciPy Brown-Forsythe
  and mean-centered Levene, two- and multi-group Bonett references, failure
  policies, and the supplied `studio_process_training.csv` Minitab fixture.
- `frontend/src/EqualVariancesPanel.test.tsx` verifies method naming, the blank
  multiple-comparison statistic cell, the interval SVG, and keyboard entry.
- schema-1 restore remains covered by existing analysis result tests.
