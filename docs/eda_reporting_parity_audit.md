# EDA Reporting Parity Audit

Status: implementation baseline for the reporting-summary-variance work.

This audit separates display changes from statistical-definition changes. Existing stored
results and HTML artifacts remain immutable and are read using their original schema and method
versions.

## Official references

- Minitab, *Methods and formulas for Graphical Summary*:
  <https://support.minitab.com/en-us/minitab/help-and-how-to/statistics/basic-statistics/how-to/graphical-summary/methods-and-formulas/methods-and-formulas/>
- Minitab, *Methods and formulas for Test for Equal Variances*:
  <https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/anova/how-to/test-for-equal-variances/methods-and-formulas/methods-and-formulas/>
- Minitab, *Multiple Comparisons Method Test for Equal Variances* white paper:
  <https://support.minitab.com/en-us/minitab/media/pdfs/translate/Multiple_Comparisons_Method_Test_for_Equal_Variances.pdf>
- NumPy, `quantile` method definitions:
  <https://numpy.org/doc/stable/reference/generated/numpy.quantile.html>
- SciPy, Levene/Brown-Forsythe implementation:
  <https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.levene.html>
- SciPy, studentized-range distribution:
  <https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.studentized_range.html>
- Hettmansperger and Sheather (1986), *Confidence Intervals Based on Interpolated
  Order Statistics*, Statistics and Probability Letters 4, 75-79.

## Definition audit

| Feature | Current definition | Required definition | Implementation decision | Version effect |
| --- | --- | --- | --- | --- |
| Descriptive Q1/Q3 | Median of halves | Position `p(N+1)`, Hyndman-Fan 6 | Shared NumPy `method="weibull"` helper | `eda.descriptive` 0.2.0, result schema 2 |
| Graphical-summary Q1/Q3 | Median of halves | Same HF6 definition | Reuse shared helper for summary, boxplot and FD IQR | `eda.graphical_summary` 0.2.0, result schema 2 |
| Sample skewness | Not returned | Minitab adjusted coefficient | `scipy.stats.skew(..., bias=False)` after independent formula test | Graphical schema 2 |
| Sample kurtosis | Not returned | Minitab adjusted excess kurtosis | `scipy.stats.kurtosis(..., fisher=True, bias=False)` after independent formula test | Graphical schema 2 |
| Mean CI | Not returned | Student t, sample SD, `N-1` df | SciPy t quantile | Graphical schema 2 |
| Median CI | Not returned | Hettmansperger-Sheather nonlinear order-statistic interpolation | Binomial coverage interpolation with explicit unavailable reason for unsupported small N | Graphical schema 2 |
| SD CI | Not returned | Normal-theory chi-square interval | `N-1` df, with normality-sensitive warning | Graphical schema 2 |
| Equal-variance Levene row | Median Brown-Forsythe labeled Brown-Forsythe | Minitab Levene is the Brown-Forsythe median-centered modification | Label as Levene (Brown-Forsythe) | `eda.equal_variances` 0.2.0, result schema 2 |
| Equal-variance second row | Mean-centered Levene labeled Levene | Minitab multiple-comparisons procedure | Implement Bonett pair tests plus Nakayama normal-range multiplicity adjustment | Equal-variance schema 2 |
| Mean-centered Levene | Default result row | Optional additional diagnostic | Preserve as `additional_tests`; never call it multiple comparisons | Equal-variance schema 2 |
| HTML report | Technical metadata and path/value envelope dominate | Human-readable stored-result report | Renderer registry, method sections, inline SVG, closed technical/raw details | artifact schema 2 |

## Statistical risks and policies

- HF6 changes IQR-dependent boxplot fences, outliers and Freedman-Diaconis bin counts. The result
  records the quantile method; schema 1 readers retain `median_of_halves`.
- Median confidence intervals are distribution-free approximations based on order statistics.
  They are not silently replaced by a normal approximation.
- Standard-deviation confidence intervals are normal-theory intervals and carry a persistent
  sensitivity warning.
- Multiple-comparison intervals are uncertainty intervals used to compare group standard
  deviations; they are not population-standard-deviation confidence intervals.
- The multiple-comparisons result is unavailable rather than fabricated when group sample sizes
  or variances do not support the Bonett/Nakayama calculation.
- Stored schema 1 equal-variance rows retain their historical labels and definitions when restored.

## Compatibility decision

- API contract moves from 11 to 12 because scatter roles and EDA request/result contracts change.
- Metadata schema remains 18 unless generic metadata for analysis/design/study assets requires a
  relational migration. Artifact bytes and checksums are never rewritten.
- Graph Preview visualization schema moves from 2 to 3. The backend accepts the legacy singular-X
  request shape and normalizes it to the canonical role lists.
- HTML report artifact schema moves from 1 to 2. Existing schema 1 artifacts remain downloadable.

