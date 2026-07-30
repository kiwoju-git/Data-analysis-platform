# Latin Hypercube Design Contract

Last updated: 2026-07-29

## Method And Purpose

`doe.latin_hypercube` version `0.1.0` is a dedicated, dataset-independent
space-filling design method. It uses the installed SciPy 1.15.3
`scipy.stats.qmc.LatinHypercube`, `qmc.scale`, and `qmc.discrepancy`; it adds no
production dependency.

LHS stratifies each continuous factor range to explore a rectangular design
space. It is not a two-level factorial contrast design and does not
automatically estimate factorial main effects, interactions, an optimum, or an
observed response.

## P0 Input Policy

- one to six continuous factors;
- finite `low < high` bounds;
- two to 200 runs;
- explicit design seed;
- `scramble=true`, `strength=1`;
- optimization `random_cd` (default) or `none`;
- optional deterministic run-order randomization with its own seed.

Categorical, integer, mixture, conditional, repeated-center, and arbitrary
linear-constraint designs are not supported in P0. Rejecting infeasible points
after LHS generation would not preserve the one-point-per-marginal-stratum
contract, so constrained space filling requires a future versioned method.

The UI default `min(64, max(8, 3 * factor_count))` is a budget-balancing product
heuristic, not a statistical guarantee. `d+1` is only a bare GP fitting
minimum; a roughly `10d` computer-experiment rule is shown only as context and
is not imposed on wet-lab work.

The corporate form uses a four-column core settings grid for name, run count,
design seed, and run-order seed. Optimization and a full labeled run-order
randomization card form the secondary grid. Disabling randomization disables
the run-order seed and states that standard and run order are identical.

## Stored Result And Validation

The design stores actual and normalized coordinates, standard order, run
order, factor order/bounds/units, seeds, policy, optimization, package versions,
and a canonical design SHA-256. Restore validates stored points rather than
depending solely on regenerating them with a future SciPy release.

Quality metadata includes:

- centered discrepancy;
- minimum normalized pairwise Euclidean distance;
- maximum absolute normalized factor correlation;
- per-factor stratum occupancy and `strata_valid`;
- NumPy and SciPy versions.

These are diagnostics, not proof of an optimal design. The response-revision
API reuses the DOE immutable revision contract. CSV export includes standard
and run order, actual and normalized factor columns, and an optional current
response. Existing formula-injection escaping applies.

## Routes

- `POST /api/v1/doe-designs/latin-hypercube`
- `GET /api/v1/doe-designs/latin-hypercube/{design_id}`
- `PUT/GET /api/v1/doe-designs/latin-hypercube/{design_id}/responses`
- `GET /api/v1/doe-designs/latin-hypercube/{design_id}/export.csv`

## References

- McKay, Beckman, and Conover (1979), *A Comparison of Three Methods for
  Selecting Values of Input Variables in the Analysis of Output from a
  Computer Code*.
- SciPy 1.15.3 documentation for `scipy.stats.qmc.LatinHypercube`.
- Loeppky, Sacks, and Welch (2009), *Choosing the Sample Size of a Computer
  Experiment*.
