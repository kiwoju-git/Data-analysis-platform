# Mixed Study Source Boundary

Schema 7 extends the existing Bayesian study/version/trial/history owner store.
It does not create a second workspace or owner table. Source creation and reading
are separate from the mixed planning/confirmation gate and must not be advertised
as a completed BO workflow until that integration has passed.

## Request And Response

`MixedStudyCreateRequest` requires explicit schema_version 7 and an existing
complete-response-vector desirability objective. Both existing DS curves and
versioned per-response Gaussian/DS curves retain their own declared policies.
Scalar study requests are not silently converted.

Factors are tagged by domain_kind. Numeric fields retain the existing numeric
request and response contracts. Nominal/ordinal factors contain exact strings,
declared level order, and the explicit correlation policy from the mixed-kernel
contract. No sorting, trimming, case folding, numeric-string conversion, or
normalization of category identities occurs. Duplicate levels and invalid
policy/kind combinations fail before persistence.

Public mixed trials carry `actual_coordinates` (finite numeric values or exact
category strings) and `encoded_coordinates` (numeric normalized values or integer
category lookup indices), with an explicit encoding policy. Category index 2 is
not normalized to 1 and is not a distance. The old SQL column name
`normalized_coordinates_json` is retained only as an internal storage name under
the schema-7 reader. Its public projection never calls mixed codes normalized
numeric coordinates.

Pending/abandoned response_values is null. Completed response_values contains one
finite real measurement for every declared response. Objective_value stays null;
desirability scores and model predictions are never written as observations.

## Initial Design

`sha256_counter_mixed_uniform_feasible_v1` is deterministic bounded uniform
sampling, not LHS. SHA-256 counter words use seed, attempt and factor index. The
continuous draw uses 53 bits; finite categorical/discrete levels use an explicit
256-bit integer partition. Numeric discrete values are reconstructed from the
original Decimal anchor and step, not a newly selected minimum.

Initial size uses the existing product minimum max(2, factor_count+1), at most 64.
Generation attempts are at most requested_size times 1,000. Exact duplicate
conditions and infeasible points are rejected. Finite all-discrete space smaller
than the requested unique size fails before sampling; budget exhaustion never
stores a partial design. Full declared-level counts, uncovered indices and an
explicit coverage warning are stored. Sampling does not promise level balance.

Linear constraints are actual-unit numeric-only constraints. Category coefficients
are rejected rather than applied to level codes. Each final point is checked
against bounds, executable lattice and constraints. The relative numerical
tolerance is the existing numeric policy, 1e-12 times max(1, |lhs|, |bound|), and
nonfinite arithmetic is rejected.

## Immutable Identity And Readers

The new definition hash covers the exact schema-7 factors, objective, constraints,
method version and generated-design metadata. Trial coordinate hashes explicitly
cover the new coordinate encoding, full actual identities, encoded map, trial
number and origin. Replicate parent identity is included only for replicate
trials. No default field is added to any schema-1-to-6 hash input.

`load_validated_mixed_study` validates the owner/version, definition hash,
deterministic initial points, all coordinate hashes, complete response vectors,
replicate provenance, history-2 chain and lifecycle receipts. The shared history
validator and vector storage accept schema 7/history 2; SQL shape is unchanged.

`project_mixed_trial` is the typed parent-planning boundary. It verifies full
actual identities before returning actual values, encoded values, response
values and the exact coordinate hash. `new_mixed_trial_record` constructs future
pending trial records with the same hash contract. It does not write a record.

At this source checkpoint, unknown mixed recommendation batches are explicitly
rejected with `bayesian_mixed_saved_batch_contract_unavailable`. The planning
gate must replace that guard with its versioned batch validator before mixed
confirmation is exposed. The source response marks automatic numeric
recommendation_available false and names the fixed-candidate workflow requirement.

## Route Integration

Parent integration owns shared routes. Intended wiring:

- POST `/api/v1/bayesian-studies/mixed`: `create_mixed_study`, request and response
  above; register the literal route before dynamic study paths.
- GET existing study path: `get_any_bayesian_study`, explicit numeric-or-mixed
  response union.
- Existing catalogue summary and initial-design CSV already dispatch by stored
  schema. Mixed CSV escapes formula-leading category strings through the common
  export helper without modifying stored strings.

Other lifecycle/trial APIs must explicitly dispatch mixed source contracts; do
not feed mixed factors through old numeric analysis/optimization helpers.

## Checkpoint Evidence

2026-11-10, Windows/Python 3.10, synthetic separate workspace including spaces and
Korean characters. Core generation plus direct-service/source tests: 28 passed
in 24.28 seconds (tool session 60841). This covers deterministic actual coordinates,
Decimal lattice, typed exact labels, numeric-only constraints, budget failures,
creation/read/catalogue, vector observation storage/history 2, unchanged source
hashes, CSV escaping and tampered-coordinate rejection.

First run: 19 passed / 8 failed because the new test fixture omitted required
study objective fields. The fixture was corrected, not the production contract;
negative schema tests now validate the unmodified baseline before mutating it.

Existing numeric/vector storage, Bayesian study API and versioned-curve
regressions: 58 passed in 125.17 seconds (session 6120). Existing Starlette
deprecation warnings remain. Narrow Ruff and mypy checks passed for the three
new source modules; no existing artifact hash fixture was rewritten.

These are pure and direct-service/storage checks, not a real browser journey or
the production API route test. Mixed planning, confirmation, close/replicate UI,
report/backup/archive and final native suite evidence belong to subsequent gates.
