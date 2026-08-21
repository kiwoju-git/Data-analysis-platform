# Factorial DOE And Mann-Whitney Parity Audit

Last reviewed: 2026-08-21

## Scope and decision

This audit compares Statistical Twin with the current official Minitab
workflows that are relevant to two-sample Mann-Whitney input and factorial DOE.
It is a planning and compatibility record, not a claim of complete Minitab
parity. Existing method contracts, stored artifacts, and reference tests remain
authoritative for calculations already implemented.

The current change implements only these P0 items:

- stacked Mann-Whitney with explicit selection of two levels, and unstacked
  independent sample columns;
- one canonical General Full Factorial entry inside Create Factorial Design;
- numeric and two-level categorical factors in full and catalog-backed regular
  fractional designs;
- Minitab-style pseudo-center expansion for mixed numeric/text factors;
- an explicit 2-to-10-level General Full Factorial editor and a three-level
  convenience preset.

Replicate blocking is not included in this change. Minitab treats blocks as a
model term, so adding only a display column would be statistically incomplete.
It remains P1 with a separate design/analysis contract and reference fixture.

## Official sources reviewed

- [Minitab: Enter your data for Mann-Whitney Test](https://support.minitab.com/en-us/minitab/help-and-how-to/statistics/nonparametrics/how-to/mann-whitney-test/perform-the-analysis/enter-your-data/)
- [Minitab: Mann-Whitney methods and formulas](https://support.minitab.com/en-us/minitab/help-and-how-to/statistics/nonparametrics/how-to/mann-whitney-test/methods-and-formulas/methods-and-formulas/)
- [SciPy: `scipy.stats.mannwhitneyu`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html)
- [NIST/SEMATECH: Mann-Whitney U procedure](https://www.itl.nist.gov/div898/handbook/prc/section3/prc35.htm)
- [Minitab: Select a factorial design](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/create-factorial-design/select-a-factorial-design/)
- [Minitab: Specify factors for a 2-level design](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/create-factorial-design/create-2-level-factorial-specify-generators/create-the-design/specify-the-factors/)
- [Minitab: Specify a 2-level design](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/create-factorial-design/create-2-level-factorial-specify-generators/create-the-design/specify-the-design/)
- [Minitab: Available 2-level factorial designs](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/supporting-topics/factorial-and-screening-designs/available-2-level-factorial-designs/)
- [Minitab: Design generators](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/supporting-topics/factorial-and-screening-designs/what-is-a-design-generator/)
- [Minitab: Center and pseudo-center points](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/supporting-topics/factorial-and-screening-designs/how-minitab-adds-center-points/)
- [Minitab: Create General Full Factorial example](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/create-factorial-design/create-general-full-factorial/before-you-start/example/)
- [Minitab: Specify General Full Factorial design](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/create-factorial-design/create-general-full-factorial/create-the-design/specify-the-design/)
- [Minitab: Analyze Factorial design matrix](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/analyze-factorial-design/methods-and-formulas/model-information/)
- [Minitab: Fold Design](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/display-and-modify-design/perform-the-analysis/fold-design/)
- [Minitab: Definitive screening designs](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/supporting-topics/factorial-and-screening-designs/definitive-screening-designs/)
- [Minitab: General Full Factorial power and sample size](https://support.minitab.com/en-us/minitab/help-and-how-to/statistics/power-and-sample-size/how-to/linear-models/power-and-sample-size-for-general-full-factorial-design/before-you-start/overview/)
- [NIST/SEMATECH: Process Improvement / factorial DOE](https://www.itl.nist.gov/div898/handbook/pri/pri.htm)

## Parity matrix

| Capability | Minitab support | Statistical Twin before this change | Gap and statistical effect | Priority | Implement now | Version/schema impact | Reference test |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Mann-Whitney sample columns | First Sample and Second Sample are independent numeric columns | Stacked response plus group only | Users with natural unstacked worksheets cannot run the test; pairing rows would incorrectly discard independent observations | P0 | Yes; independent available-case extraction per sample | method 0.2.0, result schema 2, API 15 | stacked/unstacked parity and unequal usable N |
| Mann-Whitney stacked data | Native dialog is column-per-sample; stacked data can be represented by worksheet transformation | One response and one group, but exactly two usable levels required | Three-level groups cannot choose a planned pair | P0 | Yes; explicit two-level selection and excluded-row count | same as above | A/C from A/B/C |
| Mann-Whitney p-value | Normal approximation with tie adjustment and continuity correction | SciPy auto/exact/asymptotic; exact is rejected with ties | Current calculation deliberately offers a broader SciPy contract than Minitab | P0 preserve | Preserve; do not claim exact Minitab parity | documented only | existing SciPy reference |
| Mann-Whitney location estimate/CI | Hodges-Lehmann style pairwise-difference estimate and McKean-Ryan CI | Rank effect sizes and group summaries only | No location-shift estimate/CI | P1 | No | future method/result contract | independent published fixture |
| Two-level full factorial | Numeric/text factors, low/high levels, replicates, center points, blocks, randomization | Numeric factors only, 2 to 6 | Text factors and pseudo-centers missing | P0 | Yes for text factors and pseudo-centers | method 0.6.0, design schema 2 | full/mixed/text fixtures |
| Two-level regular fractional | Default and custom generators, resolution, alias, fractions | Tested default catalog for 3 to 6 factors | Text factor mapping missing; custom generators/foldover absent | P0/P1 | P0 text mapping; P1 custom/foldover | method/design bump for text payload only | alias parity unchanged |
| Center points | Numeric midpoint; for q text factors, all 2^q text combinations at numeric midpoints; unavailable for all-text designs; count applies per block | One all-numeric midpoint row per requested point | Run count and curvature interpretation are wrong for text factors | P0 | Yes | design schema 2 | q=1, q=2, all-text, blocks |
| Blocks in 2-level designs | Center points per block; block generators can change alias/resolution | Fixed block assignment already modeled | Existing application block policy remains narrower than Minitab generator catalog | P0 preserve/P1 | Preserve current assignment; document narrower scope | no additional change | existing block regression plus pseudo-center count |
| General Full Factorial | Different level counts; numeric/text levels; replicates; optional replicate blocks; randomization | 2 to 6 factors, 2 to 10 numeric/text levels, replicates, seed, up to 256 runs, treatment-coded ANOVA | Backend is capable but comma-separated UI obscures level count/type; no replicate blocks | P0/P1 | P0 editor/preset; P1 block model | UI-only keeps method 0.1.0/schema 1 | 2/3/4/10 and 2x3x5 |
| Three-level factorial | General Full Factorial with three levels per factor | Available through General Full but easy to miss | Product terminology can imply a separate method | P0 | Yes; preset and guidance, no new method ID | no statistical version change | 3^3 = 27 |
| General factorial interactions | Full interaction model chosen by order | Treatment-coded term blocks and partial SS through order 3 | Current maximum order is lower than factor maximum; deliberate run/complexity bound | P0 preserve | Preserve current contract | none | existing ANOVA fixture |
| Replicate blocking in General Full | Each replicate can be its own block and block DF is included in modeling | Not supported | A block column without a model term would bias error partitioning | P1 | No | future method 0.2.0/design+analysis schema 2 | blocked ANOVA fixture |
| Available-design catalog | Default 2-level designs for 2 to 15 factors | Catalog for 3 to 6 factors | Fewer factor/run choices | P1 | No | separate catalog contract | official table fixtures |
| Custom generators/principal fraction | User-selected generators and fraction choices | Validated fixed catalog, principal fractions | Cannot target a particular alias pattern | P1 | No | separate generator parser/schema | generator/defining-word fixtures |
| Foldover/augment/modify | Full or selected-factor fold, design replication and modification | Not supported | Cannot de-alias a completed screening design | P1 | No | immutable successor-design contract | alias before/after fixtures |
| Plackett-Burman | 2 to 47 two-level screening factors, commonly resolution III | Not supported | High-factor main-effect screening absent | P1 | No | proposed `doe.plackett_burman_design` | official run matrix/alias fixtures |
| Power and sample size | 2-level, PB, and General Full calculations | Not supported | No prospective power sizing | P1 | No | proposed `doe.factorial_power` | noncentral-F references |
| Define custom design | Existing worksheet columns can be registered as DOE | Not supported | External designs cannot enter the immutable DOE lifecycle | P1 | No | custom design provenance contract | tamper/order fixtures |
| Split-plot | Hard-to-change factors and restricted randomization | Not supported | Whole-plot error structure unavailable | P2 | No | separate mixed-model project | independent split-plot fixture |
| Definitive screening | Resolution-IV screening with continuous-factor middle runs and square terms | Not supported | Efficient curvature-aware screening absent | P2 | No | separate method/analysis contract | official design matrices |
| Optimal design | Algorithmic design for constrained candidate spaces | Not supported | Requires criterion/search/budget contracts | P2 | No | separate optimization project | multi-tool reference |
| Binary/Poisson factorial response | Generalized response models | Numeric continuous response OLS only | Wrong likelihood if reused, so no fallback is allowed | P2 | No | distinct GLM methods/results | binomial/Poisson references |
| Mixture designs | Specialized constrained-composition designs | Not supported | Standard factorial coding is invalid for mixtures | P2 | No | separate mixture DOE project | simplex design references |

## P0 implementation invariants

1. Unstacked Mann-Whitney applies the analysis row filter first, then removes
   missing/non-numeric values independently in each sample column. The sample
   arrays may have different lengths.
2. Stacked mode analyzes only the two explicitly selected levels. It reports
   all rows from other non-missing levels as unselected exclusions.
3. Two-level categorical levels remain user text in actual run settings. The
   coded matrix remains `-1/+1`; generator, resolution, and alias calculations
   do not depend on the display value type.
4. A mixed design pseudo-center is the numeric midpoint crossed with every
   categorical low/high combination. For q categorical factors, each requested
   center per block expands to `2^q` actual runs.
5. An all-categorical design cannot estimate curvature from center points and
   therefore requires `center_points = 0`.
6. General Full numeric levels are categorical treatment levels, not continuous
   polynomial coding. Input order is preserved and the first level remains the
   reference under the current analysis contract.

## Follow-up contract order

1. `docs/general_factorial_blocking_contract.md`: block-on-replicates creation,
   persistence, model term, ANOVA DF/SS, restore and power implications.
2. `docs/factorial_generator_and_foldover_contract.md`: expanded catalog,
   custom generators, fraction selection, foldover and immutable successors.
3. `docs/plackett_burman_method_contract.md`: run catalog, alias warnings,
   response analysis and power.
4. `docs/factorial_power_method_contract.md`: effect definition, sigma,
   interaction order, blocks, noncentral-F calculations and plots.
5. `docs/custom_factorial_design_contract.md`: imported design validation,
   standard/run order, blocks, center flags and provenance.
6. Separate P2 contracts for split-plot, definitive screening, optimal,
   generalized-response factorial, and mixture designs.

