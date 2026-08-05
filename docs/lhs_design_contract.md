# Latin Hypercube Design Contract

Last updated: 2026-08-05

## Method And Purpose

`doe.latin_hypercube` version `0.2.0` is a dedicated, dataset-independent
space-filling design method. Continuous-only designs retain the installed
SciPy 1.15.3 `LatinHypercube(random-cd)` numerical path. Mixed designs use the
versioned `mixed_lhs_balanced_discrete_v1` policy and design schema `2`.

LHS explores a declared factor region. It does not automatically estimate
factorial effects, an optimum, or an observed response.

## Factor Domains

Each of one to six factors stores `low`, `high`, optional `unit`,
`domain_kind`, `step`, and optional `display_decimals`.

- `continuous`: any finite value within `low < high`; `step` must be null.
- `discrete_numeric`: executable values are exactly `low + k * step`;
  `step > 0`, `high` must lie on the Decimal-validated grid, and the level
  count is bounded to 10,001.
- `display_decimals` changes screen and actual-coordinate CSV formatting only;
  it never changes stored coordinates, normalized values, or calculations.

Nonuniform explicit numeric levels, categorical factors, mixture factors, and
arbitrary constrained LHS remain outside this contract.

## Generation

Inputs are two to 200 runs, explicit design and run-order seeds,
`scramble=true`, strength 1, and `random_cd` or `none` optimization.

Continuous dimensions use the existing SciPy strata. A discrete dimension is
assigned from its LHS rank to legal levels so per-level counts differ by at
most one. The generator validates executable coordinates and complete-row
duplicates and deterministically regenerates up to a bounded attempt limit.
It fails with `lhs_executable_unique_design_impossible` rather than silently
returning fewer or duplicate runs. This mixed policy is not described as a
classical continuous LHS in every dimension.

## Stored Result And Quality

The immutable result stores actual and normalized coordinates, standard/run
order, factor order/domain/unit, seeds, policy, package versions, and canonical
SHA-256. Legacy continuous schema-1 results and method `0.1.0` restore without
rewriting bytes or checksums.

Quality includes centered discrepancy, minimum normalized pairwise distance,
maximum absolute correlation, per-factor strata, `continuous_strata_valid`,
discrete level counts, duplicate count, and executable point count. These are
diagnostics, not proof of an optimal design.

CSV export contains actual values formatted with `display_decimals`, full
normalized coordinates, order columns, and saved responses. Formatting does
not mutate the stored design.

## Interactive Views

The result UI presents quality, then design visualization, the experiment
table, and response entry. The visualization uses only stored result data:

- an accessible parallel-coordinate SVG containing every run, with normalized
  and actual-unit modes, roving keyboard selection, and discrete-level labels;
- a selectable two-factor projection using the existing interactive scatter
  foundation; and
- shared selected-run state across both plots and the run table.

The pairwise projection is not a complete assessment of high-dimensional
space filling. No chart library or network asset is required.

## Routes

- `POST /api/v1/doe-designs/latin-hypercube`
- `GET /api/v1/doe-designs/latin-hypercube/{design_id}`
- `PUT/GET /api/v1/doe-designs/latin-hypercube/{design_id}/responses`
- `GET /api/v1/doe-designs/latin-hypercube/{design_id}/export.csv`

## References

- SciPy 1.15.3 `scipy.stats.qmc.LatinHypercube` documentation.
- McKay, Beckman, and Conover (1979), *A Comparison of Three Methods for
  Selecting Values of Input Variables in the Analysis of Output from a
  Computer Code*.
- The executable-domain decision and official JMP/Minitab references are in
  `docs/doe_factor_domain_resolution_audit.md`.
