# Bayesian Initial Observation Import Contract

Last updated: 2026-07-29

## Status

This is a next-step contract. The current product does not import a standalone
LHS response revision or arbitrary dataset rows into a Bayesian Study. No
frontend-only handoff button or silent point regeneration is provided.

## Future Sources

1. A completed app-created LHS design plus an immutable response revision.
2. An immutable dataset version with explicit factor and objective mappings.

Preflight must validate source artifact checksums, source revision immutability,
factor IDs/names/types/bounds/units, the objective mapping, finite values,
missing rows, duplicate coordinates, conflicting responses at identical
coordinates, linear-constraint feasibility, observation count, and current
Bayesian factor/trial limits.

## Atomic Import Result

A successful future import will create one Bayesian Study and completed
`initial_design` trials with source lineage IDs and SHA-256 values. It will not
rewrite the source design, response revision, dataset, or raw data. Imported
observations enter the first immutable Bayesian history revision. Recommendation
is allowed only when the normal completed-observation, pending-trial, budget,
status, and history checks pass.

Proposed routes, not currently implemented:

- `POST /api/v1/bayesian-studies/import-preflight`
- `POST /api/v1/bayesian-studies/from-lhs-design`
- `POST /api/v1/bayesian-studies/from-dataset`

These routes require a separately versioned typed contract, exact source
snapshot validation, atomic persistence, and backend/frontend tests before UI
exposure.
