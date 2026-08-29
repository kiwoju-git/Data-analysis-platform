# Plackett-Burman screening design contract

Status: P0 implementation contract

Method: `doe.factorial_design`

Design type: `plackett_burman_screening`

## Purpose and scope

The Plackett-Burman option is a two-level main-effect screening design for 7-10
numeric or categorical factors. It is not a high-resolution fractional
factorial design and it does not identify two-factor interactions separately.

P0 provides one verified catalog entry:

- catalog ID: `pb-12-run-v1`
- 12 runs;
- 11 available orthogonal sign columns;
- product exposes the first 7-10 columns;
- unused columns are recorded as unused catalog columns, not user factors;
- deterministic randomization and 1-16 replicates;
- no center points in the P0 UI.

## Catalog matrix

The official 12-run generator row is:

`+ + - + + + - - - + -`

The design matrix is constructed from the 11 cyclic shifts of that row plus an
all-minus row. The committed catalog records its canonical SHA-256. Tests must
verify:

- shape 12 by 11;
- every entry is `-1` or `+1`;
- each column has six low and six high runs;
- `X'X = 12I` for all 11 design columns;
- augmented main-effect matrix `[1, X]` has rank 12;
- the canonical matrix SHA matches the catalog.

The source row is published by Minitab in [Plackett-Burman designs](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/supporting-topics/factorial-and-screening-designs/plackett-burman-designs/).

## Factor mapping

The coded matrix remains the calculation source:

- `-1` maps to numeric `low` or categorical `low_label`;
- `+1` maps to numeric `high` or categorical `high_label`.

Randomization only permutes rows. It does not change standard order, column
assignment, matrix SHA, or the random-number consumption of existing full and
regular fractional designs.

## Run count and feasibility

`total runs = 12 * replicates`

The existing 256-run hard cap remains. P0 disallows center points because the
requested screening contract is the verified 12-run corner design. Center-point
support, if added later, must reuse the categorical pseudo-center policy and
version the design contract.

## Analysis contract

P0 analysis fits an intercept and the selected main effects only. It reports:

- factor name and low/high contrast;
- coefficient and effect (`high - low`);
- fit and residual metadata when residual degrees of freedom exist;
- main-effect correlation diagnostics;
- a Pareto/effect plot sourced from the saved result;
- warning `doe_plackett_burman_main_effects_confounding`.

No interaction coefficient, interaction p-value, resolution-IV label, or
independent error term is fabricated. With ten factors, the 12-run main-effect
model has only one residual degree of freedom; that residual can contain
unmodeled interaction and process variation. The report must not present it as
clean pure error.

Minitab documents the 12-run design as partially confounding every main effect
with multiple two-factor interactions. Its Assistant white paper omits the
12-run design for ten or eleven factors due to low power. Statistical Twin
therefore adds `doe_plackett_burman_low_power_ten_factors` for ten factors and
recommends confirmation or a larger follow-up design.

## Persistence and compatibility

- Existing numeric full/fractional schema 1-2 designs restore unchanged.
- The new PB write uses the current factorial method version and a new design
  schema version.
- Stored coded levels and actual levels use the existing design JSON storage.
- No SQLite migration is required.
- Existing design checksums are never recomputed.

## Reference tests

Required tests cover the official generator row, full matrix SHA, balance,
orthogonality, rank, 7/8/9/10 factor projections, numeric/categorical mapping,
replicates, deterministic randomization, main-effects-only analysis, warnings,
CSV/export, and legacy full/fractional parity.
