# Graphical Summary Method Contract

Current method: `eda.graphical_summary` `0.2.0`, result schema 2.

Primary references:

- Minitab Graphical Summary methods and formulas:
  https://support.minitab.com/en-us/minitab/help-and-how-to/statistics/basic-statistics/how-to/graphical-summary/methods-and-formulas/methods-and-formulas/
- NumPy `quantile` method definitions:
  https://numpy.org/doc/stable/reference/generated/numpy.quantile.html
- SciPy skew and kurtosis definitions:
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.skew.html

## Stored Result

For each selected numeric column schema 2 stores full-sample N/exclusions,
mean, sample standard deviation, sample variance, bias-corrected sample
skewness and excess kurtosis, five-number summary, Anderson-Darling statistic/
adjusted statistic/approximate p-value, histogram, normal-fit expected counts,
boxplot, bounded Q-Q/ECDF points, and confidence intervals.

The fitted normal curve is `normal_pdf(x; sample mean, sample SD) * N * bin
width`. It is omitted for insufficient or constant data and is a visual
comparison, never proof of normality. Histogram bin counts and boxplot fences
use the same HF6 IQR.

Confidence intervals are:

- mean: Student t interval;
- median: Hettmansperger-Sheather sign interval with nonlinear interpolation;
- sample standard deviation: chi-square interval under a normal-population
  assumption, with a user-visible normality-sensitive warning.

The UI places histogram/normal fit beside the statistics panel, then boxplot
and Q-Q, then separate-scale interval panels. ECDF remains available in an
additional-graphs disclosure. The descriptive quick graph keeps only histogram
and boxplot.

## Quantiles

`eda.descriptive` and `eda.graphical_summary` use Hyndman-Fan Method 6,
implemented by NumPy `method="weibull"`, with plotting position `p(N+1)` and
bounded endpoint behavior. Metadata is:

- `quantile_method="hyndman_fan_6_weibull"`
- `quantile_position="p_times_n_plus_1"`

This definition also feeds the Graphical Summary IQR, Tukey fences/whiskers,
outlier count, and Freedman-Diaconis bin width. Existing schema-1 stored results
retain `median_of_halves`; files and checksums are not rewritten.

## Verification

`test_sample_quantiles.py` checks both Minitab examples (`Q1=2.25` and
`Q1=14.25, median=42, Q3=46.50`) and NumPy parity, including N=1/2/3 and
boundaries. `test_sample_distribution.py` independently cross-checks moments
with SciPy and fixes reference t, nonlinear median, and chi-square intervals.
`test_graphical_summary.py` verifies the shared quantile, boxplot, histogram,
normal-curve, bounded-point, constant, and exclusion policies.
