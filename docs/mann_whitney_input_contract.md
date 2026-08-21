# Mann-Whitney U Input Contract

## Scope and versions

- Method ID: `hypothesis.mann_whitney`
- Current method version: `0.2.0`
- Current result schema: `2`
- Legacy method/result: `0.1.0` / schema `1` remains readable without rewrite.

Version 0.2.0 changes data selection, not the rank-test statistic. Both input layouts feed the same rank, tie, U, p-value, rank-biserial, and common-language-probability calculation.

## Input layouts

### Stacked

`input_layout = "stacked"` uses one numeric response column and one group column. The user selects two distinct group levels after the current analysis filter is applied. If exactly two usable levels exist, the UI selects them in the preflight order and identifies that automatic choice. With three or more levels, no pair is inferred: the user must choose both levels.

Rows in unselected levels are excluded and counted separately. Within the selected levels, missing group values, missing responses, and nonnumeric responses are recorded. The stored policy is `complete_case_selected_groups`.

Legacy requests that omit `input_layout` but contain `response_column_id` and `group_column_id` normalize to stacked input.

### Unstacked

`input_layout = "unstacked"` uses two distinct numeric sample columns. The dataset filter is applied to rows first. Values are then extracted independently from each column:

- a missing or nonnumeric value in sample 1 does not remove the sample 2 value in the same row;
- a missing or nonnumeric value in sample 2 does not remove the sample 1 value in the same row;
- the two usable sample sizes may differ.

The stored policy is `available_case_by_sample`. Column display names are the sample labels and are not translated.

## Calculation invariant

The shared sample core:

1. validates finite observations and minimum sample sizes;
2. assigns average ranks to ties;
3. computes SciPy `mannwhitneyu` with the requested alternative and resolved exact/asymptotic method;
4. reports U for sample 1;
5. reports common-language probability as `U / (n1 * n2)` and rank-biserial correlation as `2 * probability - 1`;
6. retains negative or positive direction relative to the selected sample order.

`auto` uses exact calculation only when the smaller sample has at most 8 observations and there are no ties; otherwise it uses the asymptotic calculation with continuity correction. An explicit exact request with ties is rejected rather than silently changed.

## Result schema 2

Schema 2 adds:

- `input_layout`;
- `samples`, including source column, selected group value when applicable, total/used/missing/nonnumeric counts;
- selected group values and unselected-level row count for stacked input;
- the explicit missing policy.

The existing `groups` and `test` objects remain the common presentation contract. Schema 1 stored results remain restored through the generic result reader and their checksums are not recalculated.

## References

- [Minitab: Enter your data for Mann-Whitney Test](https://support.minitab.com/en-us/minitab/help-and-how-to/statistics/nonparametrics/how-to/mann-whitney-test/perform-the-analysis/enter-your-data/)
- [Minitab: Mann-Whitney methods and formulas](https://support.minitab.com/en-us/minitab/help-and-how-to/statistics/nonparametrics/how-to/mann-whitney-test/methods-and-formulas/methods-and-formulas/)
- [SciPy `mannwhitneyu`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html)
- [NIST: Mann-Whitney test](https://www.itl.nist.gov/div898/handbook/prc/section3/prc35.htm)
