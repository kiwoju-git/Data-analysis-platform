# Hypothesis Method Parity Audit

Last reviewed: 2026-08-02

## Purpose

This audit compares the current hypothesis-test surface with official
statistical software and library documentation before extending the product.
It is not a commitment to copy every Minitab option. The priority is to close
gaps that can change the validity or interpretation of an analysis while
preserving explicit user choice and stored-result compatibility.

Priority definitions:

- **P0**: needed for a valid method/design choice or materially correct result.
- **P1**: useful extension that can be delivered independently.
- **Deferred**: outside the current data model, dependency policy, or product
  scope.

No diagnostic p-value may silently change a selected method. Equivalence
limits and comparison families must be selected before inspecting the result.

## Official Sources

Sources were reviewed in this order: Minitab Help, SciPy 1.15.3, NIST/SEMATECH,
then primary literature. The audit records links and paraphrases only; it does
not copy vendor tables or examples into fixtures.

- Minitab, [One-Way ANOVA analysis options](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/anova/how-to/one-way-anova/perform-the-analysis/select-the-analysis-options/)
- Minitab, [One-Way ANOVA group comparisons](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/anova/how-to/one-way-anova/perform-the-analysis/select-the-group-comparisons/)
- Minitab, [multiple-comparison formulas](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/anova/how-to/one-way-anova/methods-and-formulas/multiple-comparisons/)
- Minitab, [equivalence-test families](https://support.minitab.com/en-us/minitab/help-and-how-to/statistics/equivalence-tests/supporting-topics/equivalence-tests-in-minitab/)
- Minitab, [2-sample equivalence inputs](https://support.minitab.com/en-us/minitab/help-and-how-to/statistics/equivalence-tests/how-to/2-sample-equivalence-test/perform-the-analysis/enter-your-data/)
- Minitab, [paired equivalence overview](https://support.minitab.com/en-us/minitab/help-and-how-to/statistics/equivalence-tests/how-to/equivalence-test-with-paired-data/before-you-start/overview/)
- Minitab, [1-sample equivalence formulas](https://support.minitab.com/en-us/minitab/help-and-how-to/statistics/equivalence-tests/how-to/1-sample-equivalence-test/methods-and-formulas/methods-and-formulas/)
- Minitab, [why equivalence is not a nonsignificant difference test](https://support.minitab.com/en-us/minitab/help-and-how-to/statistics/equivalence-tests/supporting-topics/why-use-an-equivalence-test/)
- Minitab, [1-sample t options](https://support.minitab.com/en-us/minitab/help-and-how-to/statistics/basic-statistics/how-to/1-sample-t/perform-the-analysis/select-the-analysis-options/)
- Minitab, [1-sample Wilcoxon overview](https://support.minitab.com/en-us/minitab/help-and-how-to/statistics/nonparametrics/how-to/1-sample-wilcoxon/before-you-start/overview/)
- Minitab, [Mann-Whitney formulas](https://support.minitab.com/en-us/minitab/help-and-how-to/statistics/nonparametrics/how-to/mann-whitney-test/methods-and-formulas/methods-and-formulas/)
- Minitab, [Kruskal-Wallis interpretation](https://support.minitab.com/en-us/minitab/help-and-how-to/statistics/nonparametrics/how-to/kruskal-wallis-test/interpret-the-results/key-results/)
- Minitab, [2-proportion methods](https://support.minitab.com/en-us/minitab/help-and-how-to/statistics/basic-statistics/supporting-topics/tests-of-proportions-and-variances/methods-that-minitab-uses-to-perform-a-2-proportions-test/)
- Minitab, [chi-square association formulas](https://support.minitab.com/en-us/minitab/help-and-how-to/statistics/tables/how-to/chi-square-test-for-association/methods-and-formulas/methods-and-formulas/)
- SciPy 1.15.3, [`f_oneway`](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.stats.f_oneway.html)
- SciPy 1.15.3, [`dunnett`](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.stats.dunnett.html)
- SciPy 1.15.3, [`studentized_range`](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.stats.studentized_range.html)
- SciPy 1.15.3, [`mannwhitneyu`](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.stats.mannwhitneyu.html)
- SciPy 1.15.3, [`wilcoxon`](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.stats.wilcoxon.html)
- SciPy 1.15.3, [`kruskal`](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.stats.kruskal.html)
- NIST/SEMATECH, [one-way ANOVA model and assumptions](https://www.itl.nist.gov/div898/handbook/prc/section4/prc432.htm)
- Welch (1951), [On the Comparison of Several Mean Values](https://doi.org/10.2307/2332579)
- Dunnett (1955), [A Multiple Comparison Procedure](https://doi.org/10.1080/01621459.1955.10501294)
- Games and Howell (1976), [Pairwise Multiple Comparison Procedures with Unequal N's and/or Variances](https://doi.org/10.1080/00401706.1976.10489471)
- Schuirmann (1987), [Two one-sided tests for average bioavailability](https://pubmed.ncbi.nlm.nih.gov/3450848/)

## Method Inventory

| Current method ID | Current design and options | Current statistic / post-hoc | Major official options | SciPy 1.15.3 support | Gap and statistical impact | Priority | This change | Version impact |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `hypothesis.one_sample_t` | One numeric column; null mean; two-sided/greater/less; alpha; confidence level; complete cases | One-sample t, CI, Cohen dz, Hedges correction | Minitab also accepts summarized data and provides power/sample-size workflows | `ttest_1samp` directly supports alternatives | Raw-data inference is complete. Summarized input and power do not change the current raw-data result | P1 | No | None |
| `hypothesis.paired_t` | Wide before/after columns; explicit difference direction; null difference; alternatives; complete pairs | Paired-difference t, CI, pair counts, Cohen dz | Minitab supports summarized differences and graph options; long paired data can be represented after reshaping | `ttest_rel` supports alternatives | Long format plus pair ID would improve ingestion and pairing diagnostics, but wide complete-pair calculation is valid | P1 | No | None |
| `hypothesis.two_sample_t` | Long response/group; exactly two groups; Welch default or explicit pooled; alternatives; null difference; CI | Welch or pooled t, CI, Cohen d/Hedges g | Minitab supports separate columns, summarized data, and pooled choice | `ttest_ind(equal_var=...)` | Core variance choice is already present. Explicit test/reference ordering would improve directional UX but is not required by this request | P1 | Reuse variance wording in 2-sample TOST | None |
| `hypothesis.one_way_anova` | One response/group; standard equal-variance only; Tukey-Kramer or none; comparisons only after significant omnibus | Pooled one-way F; eta/omega squared; Tukey-Kramer | Equal-variance standard ANOVA with Tukey/Fisher/Dunnett/Hsu MCB; unequal-variance Welch with Games-Howell | `f_oneway` in 1.15.3 has no `equal_var`; `dunnett` and `studentized_range` are available | The forced common variance can materially alter F, df, and comparisons. Omnibus gating can silently remove a requested comparison family | **P0** | **Yes: standard/Welch, Tukey-Kramer, Dunnett/control, Games-Howell, requested-policy** | `0.1.0` to `0.2.0`; result schema 1 to 2; schema-1 reader retained |
| `hypothesis.equivalence_tost` | One-sample mean only; target and raw difference bounds fixed before run; alpha | Two one-sided t tests; 1-2alpha CI; Cohen dz/Hedges correction | Minitab separates 1-sample, independent 2-sample, paired, and 2x2 crossover; offers raw difference, ratio/log-ratio, superiority/noninferiority, power | SciPy has t distributions but no single TOST API | Independent and paired designs answer different sampling questions and cannot be approximated by the one-sample UI. Failure to reject a difference test is not equivalence | **P0** for three mean-difference designs; P1 for other scales | **Yes: explicit one-sample, independent Welch/pooled, paired complete-pair TOST** | Existing ID writes `0.2.0` schema 2; two new IDs start `0.1.0` schema 2; legacy `0.1.0` unchanged |
| `hypothesis.one_sample_wilcoxon` | Null location; alternatives; auto/exact/asymptotic; Wilcox/Pratt/zsplit zero policy | Signed ranks, tie/zero diagnostics, rank-biserial effect | Minitab reports Hodges-Lehmann/Walsh estimate and CI and emphasizes symmetry | `wilcoxon` supports alternatives/method/zero policies; exact restrictions require explicit handling | Current testing choice and caveats are strong. A location estimate and CI would improve estimation reporting | P1 | No | None |
| `hypothesis.mann_whitney` | Two independent groups; alternatives; auto/exact/asymptotic; explicit tie handling | U, p, rank summaries, rank-biserial, common-language probability | Minitab uses tie-adjusted normal inference and adds a location estimate/CI | `mannwhitneyu` supports alternatives and exact/asymptotic; exact does not correct ties | Current output avoids the false generic-median interpretation. Location shift CI is useful but requires a defined shape/shift contract | P1 | No | None |
| `hypothesis.kruskal_wallis` | Three or more independent groups; tie correction; Dunn-Holm or none; after-significant policy | H, epsilon squared, Dunn raw/Holm p | Minitab reports tie-adjusted and unadjusted H/p and group rank summaries; other tools commonly provide planned Dunn comparisons | `kruskal` supplies omnibus only | Current tie-corrected omnibus and Dunn-Holm are valid. A requested-comparison policy should eventually align with the ANOVA decision, but it is separable | P1 | No; document follow-up | None |
| `categorical.one_proportion` | Binary raw column; explicit event; exact binomial test; Wilson or Clopper-Pearson CI; alternatives | Exact binomial p, proportion/difference/odds, Cohen h | Minitab offers multiple exact/score methods, summarized counts, and power | `binomtest` supports exact tests and intervals | Core exact test and explicit event are present. Summarized input and additional CI families are extensions | P1 | No | None |
| `categorical.two_proportion` | Binary response and exactly two groups; explicit event; alternatives; Fisher exact; Newcombe-Wilson difference CI; RR/OR when finite | Fisher p, risk difference, RR, OR and expected counts | Minitab reports normal methods and Fisher exact when null difference is zero; supports summarized counts | `fisher_exact` is available; normal methods require explicit implementation | Exact inference and major effect measures are already present. User-selectable normal-vs-exact and nonzero null difference are useful but not required here | P1 | No | None |
| `categorical.chi_square_association` | Two raw categorical columns; Pearson chi-square; expected-count warnings; no Yates; Cramer's V | Pearson chi-square, observed/expected/percent/residuals; sparse 2x2 Fisher recommendation | Minitab additionally shows likelihood-ratio chi-square and summarized-table input; does not use Yates | `chi2_contingency` and `fisher_exact` exist | Expected-count diagnostics and no automatic fallback are correct. An explicit Fisher execution choice for sparse 2x2 is valuable but should not be automatic | P1 | No | None |

## P0 Decisions For This Work

### One-way ANOVA

- Preserve standard pooled ANOVA exactly for `variance_model="equal"`.
- Add Welch's test for `variance_model="unequal"`. SciPy 1.15.3 does not
  expose the later `f_oneway(equal_var=False)` API, so the published Welch
  formula is implemented as a pure function and cross-checked independently.
- Use sample **variances** in the Welch weights: `w_i = n_i / s_i^2`. Terms in
  the Welch and Satterthwaite denominators are squared as defined by the cited
  formulas. A zero within-group variance is blocked rather than allowed to
  create an infinite weight.
- Equal variance permits none, Tukey-Kramer, or Dunnett. Unequal variance
  permits none or Games-Howell. Invalid combinations fail at both API and UI
  boundaries.
- Dunnett requires a user-selected control level from a bounded, filtered level
  preflight. SciPy's `dunnett` is used with an explicit stored RNG seed.
- A requested family is calculated even when the omnibus p-value is not
  significant. The omnibus and planned/control comparisons answer related but
  distinct questions. Legacy schema-1 results retain `after_significant`.
- Welch output does not fabricate pooled sums of squares or pooled eta/omega
  squared. Unsupported effect size fields are null with a stable warning.

### Grouped graphs and I-MR

This is a visualization/statistical-computation contract rather than a new
hypothesis method. Existing group-aware Box Plot and Individual Value Plot
calculation paths are reused and surfaced as an explicit `one_value_by_group`
mode. Group order is first canonical occurrence after filtering; missing group
rows are excluded and reported.

Grouped I-MR is calculated independently per group. No moving range may join
the last observation of one group to the first observation of another. A
failed small group is represented as a failed panel while valid groups remain
available, with a top-level partial-result warning. Ungrouped calculations are
unchanged.

### Equivalence designs

- Keep the one-sample estimate as `mean - reference_mean`.
- Add independent two-sample raw mean-difference TOST with an explicit test and
  reference group. Welch is the default; pooled variance requires explicit
  selection. The estimate is always `mean(test) - mean(reference)`.
- Add wide paired TOST using complete pairs and `test - reference` differences.
- Use the standard `1 - 2*alpha` confidence interval and require both one-sided
  tests to reject. A nonsignificant difference test never establishes
  equivalence.
- All three methods use bounds chosen before execution and the qualified
  decisions `equivalence evidence` / `insufficient equivalence evidence` in
  user-facing language.

## P1 And Deferred Backlog

P1 items deliberately excluded from this change:

- Fisher LSD and Hsu MCB; a common-variance planned-contrast framework;
- Kruskal-Wallis comparison timing choices beyond the current Dunn-Holm flow;
- long-format paired tests with pair ID;
- equivalence ratio/log-ratio, noninferiority/superiority screens, power and
  sample-size planning, summarized input, and import into a study workflow;
- multiple grouping variables, multiple responses crossed with groups, and
  grouped Run Chart;
- explicit Fisher execution in the chi-square screen and selectable
  normal/exact two-proportion inference.

Deferred items:

- 2x2 crossover bioequivalence and mixed/repeated-measures models;
- arbitrary user formulas or executable objectives;
- automatic diagnostic-driven method switching;
- general constrained or model-selected comparison families.

## Compatibility And Migration

- One-way ANOVA receives method `0.2.0` and result schema `2`; valid v0.1.0 /
  schema-1 artifacts remain readable and are never rehashed.
- The existing one-sample equivalence ID receives method `0.2.0` for new schema
  2 writes. Two new stable IDs start at `0.1.0`; legacy one-sample records keep
  their original method version and checksum.
- Graph Preview moves from visualization schema 1 to 2 and remains
  non-persistent.
- The typed wire contract increments from API contract 7 to 8. SQLite metadata
  remains schema 18 because generic analysis configs/results are immutable JSON
  artifacts and Graph Preview creates no stored analysis.

