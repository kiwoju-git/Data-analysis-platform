# Factorial Design Extension Audit

## Scope and decision

This audit compares the current `doe.factorial_design` implementation with
official DOE references before extending the stored design contract. The
current implementation is a two-level full factorial for 2-6 factors. It is
not a "two-factor" design: factor count and per-factor level count are separate
concepts.

The implementation boundary for this change is:

- preserve existing two-level full-factorial results and readers;
- add a catalog of validated regular two-level fractional designs;
- store generators, defining relation, resolution, estimable terms, and alias
  groups instead of treating a selected fraction as an arbitrary subset;
- add general full factorial as a separate method and analysis contract;
- cap general full-factorial designs at 256 runs;
- keep response-surface designs separate from three-level categorical designs.

## Official findings

Minitab selects a regular fraction by choosing independent base factors and
forming generated columns. Its results expose the generators, defining
relation, design resolution, and alias structure. The principal fraction is
the default fraction. NIST describes the same construction as a
`2^(k-p)` design and defines resolution by the shortest word in the defining
relation.

Resolution has a direct interpretation that must be visible to the user:

- Resolution III: main effects can be aliased with two-factor interactions.
- Resolution IV: main effects are clear of two-factor interactions, while
  two-factor interactions may be aliased with each other.
- Resolution V: main effects and two-factor interactions are clear of each
  other, while two-factor interactions may be aliased with three-factor
  interactions.

General full factorial designs contain every combination of the declared
factor levels. A numeric three-level factor is analyzed as a categorical
factor level in this workflow. It must not reuse the two-level `-1/+1` effect
definition. Users seeking a continuous curvature model should use response
surface methodology instead.

## Method matrix

| Design family | Factor/level scope | Run count | Estimation and aliasing | Current support | This change | Contract decision | User warning |
|---|---|---:|---|---|---|---|---|
| Two-level full factorial | 2-6 factors, low/high | `2^k * replicates + centers` | Main effects and requested interactions are not fractionally aliased | Yes | Preserve | Legacy `doe.factorial_design` reader remains | Run count grows exponentially |
| Two-level regular fractional factorial | Validated catalog for 3-6 factors | `2^(k-p) * replicates + centers` | Regular alias groups determined by generators | No | P0 | `doe.factorial_design` new write version; schema records fraction metadata | Aliased effects are not independently estimable |
| General full factorial | Mixed factor level lists, at least 2 levels each | product of level counts times replicates | Categorical main effects and selected interactions with term DF | No | P0 | New `doe.general_factorial_design` method | Numeric levels are categorical in this workflow |
| Three-level full factorial | General factorial specialization | `3^k * replicates` | Categorical term tests; no two-level effect formula | No | P0 | Uses general factorial contract | For continuous curvature, review RSM |
| Response surface | Continuous factors with factorial, center, and axial points | Design-specific | Polynomial response model | Yes, separate | Preserve | No merge with general factorial | Axial points and rotatability have different meaning |
| Screening design | Usually a fraction selected for economical main-effect screening | Catalog-specific | Depends on resolution and assumed negligible higher-order interactions | Partial label only | Clarify | Fraction catalog reports resolution | Screening assumptions are required |
| Foldover | Complementary fraction used to break selected aliases | Additional fraction | Alias reduction depends on foldover policy | No | Deferred | Follow-up method version | Not implied by choosing an alternative fraction |
| Custom generator | User-supplied regular generator | User-defined | Requires generator independence and alias validation | No | Deferred | Do not accept arbitrary strings in P0 | Invalid generators can duplicate or confound terms |

## Validated P0 fractional catalog

The initial catalog follows the standard useful regular designs described by
NIST and Minitab. Factor letters follow the user factor order. Generated
columns are products of base columns.

| Factors | Runs | Fraction | Resolution | Generator policy |
|---:|---:|---:|:---:|---|
| 3 | 4 | 1/2 | III | `C = AB` |
| 4 | 8 | 1/2 | IV | `D = ABC` |
| 5 | 16 | 1/2 | V | `E = ABCD` |
| 5 | 8 | 1/4 | III | `D = AB`, `E = AC` |
| 6 | 32 | 1/2 | VI | `F = ABCDE` |
| 6 | 16 | 1/4 | IV | `E = ABC`, `F = BCD` |
| 6 | 8 | 1/8 | III | `D = AB`, `E = AC`, `F = BC` |

Only the principal fraction is generated in P0. Randomization changes run
order, never the selected fraction or standard-order design matrix.

## Statistical and compatibility risks

- A fractional analysis must operate on term blocks and the reported alias
  structure. Rank deficiency must not be resolved by silently dropping terms.
- Center points do not add information for estimating factorial effects; they
  support curvature/pure-error checks under the existing policy.
- General factorial term sums of squares require reduced-model comparisons and
  categorical contrast coding. They cannot use `effect = 2 * coefficient`.
- Existing design JSON and SHA-256 values remain immutable. Missing fractional
  or general fields in legacy records mean two-level full factorial.
- The generic experiment-design tables can store factors, options, and runs as
  JSON, so no SQLite migration is required for the design payload itself.

## Sources

1. Minitab Support, *Specify the Design for Create 2-Level Factorial Design
   (Default Generators)*: https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/create-factorial-design/create-2-level-factorial-default-generators/create-the-design/specify-the-design/
2. Minitab Support, *All statistics for Create 2-Level Factorial Design
   (Specify Generators)*: https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/create-factorial-design/create-2-level-factorial-specify-generators/examine-the-design/all-statistics/
3. Minitab Support, *Select a factorial design*: https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/create-factorial-design/before-you-start/select-a-factorial-design/
4. NIST/SEMATECH, *Fractional factorial designs*: https://itl.nist.gov/div898/handbook/pri/section3/pri334.htm
5. NIST/SEMATECH, *Confounding (also called aliasing)*: https://itl.nist.gov/div898/handbook/pri/section3/pri3343.htm
6. NIST/SEMATECH, *Design resolution*: https://www.itl.nist.gov/div898/handbook/pri/section3/pri3324.htm
7. NIST/SEMATECH, *Useful fractional factorial designs*: https://www.itl.nist.gov/div898/handbook/pri/section3/pri3347.htm
8. JMP Help, *Display and Modify Design*: https://www.jmp.com/support/help/en/19.0/jmp/display-and-modify-design.shtml
9. JMP Help, *Example of a Full Factorial Design*: https://www.jmp.com/support/help/en/19.1/jmp/example-of-a-full-factorial-design.shtml
