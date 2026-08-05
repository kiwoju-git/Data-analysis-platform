# General Regression Response Optimizer Contract

Last updated: 2026-08-04

## Scope

`regression.linear_model_optimizer` is a hidden dedicated follow-on method for
an app-created `regression.linear_model` manifest. It is opened contextually
from the fitted-model result. It does not replace or alter
`doe.response_optimizer`, whose source remains a stored RSM analysis.

P0 supports one response and these goals:

- maximize;
- minimize;
- match a target; and
- stay in a user-specified acceptable range.

The optimizer evaluates the stored final equation. A backward-selected model
therefore uses only its final retained term blocks. It never refits the model,
records an observation, or represents the recommendation as a measured value.

## Domain And Coding

- Numeric bounds default to the complete-case training minimum and maximum and
  may only be narrowed by the user.
- Count predictors are rounded and evaluated as integer candidates.
- Categorical predictors use only levels stored in the manifest. A fixed level
  may be requested; otherwise bounded combinations are enumerated up to 256.
- Linear constraints use explicit coefficient maps; no expression string,
  Python, JavaScript, or `eval` is accepted.
- Quadratic, numeric interaction, and categorical treatment-coded terms use the
  same design-vector implementation as stored-model prediction.

The result is a bounded model recommendation, not a causal conclusion or a
guaranteed global optimum. A confirmation experiment remains required.

## Search And Profiles

The CPU-only deterministic policy combines seeded random candidates with
bounded SciPy SLSQP multi-start refinement. Search budgets, seed, termination,
candidate feasibility, selected settings, predicted response, desirability,
and warnings are persisted.

Each numeric predictor profile varies that predictor over its training-domain
slice while holding the remaining predictors at the selected setting. With
interactions, this is explicitly a conditional slice. Categorical profiles
report level-wise predictions and desirability rather than pretending levels
form a continuous line.

The UI renders profiles in a dedicated auto-fit grid with `min-width: 0` on
grid items and cards. Every categorical profile table is contained by its own
`table-wrap`, uses fixed table layout, wraps long level labels, and keeps
numeric cells aligned. Overflow is local to that wrapper and cannot overlap an
adjacent profile card or escape the optimizer result.

## API And Persistence

```text
POST /api/v1/regression-models/{model_id}/response-optimizations
GET  /api/v1/regression-models/{model_id}/response-optimizations
GET  /api/v1/regression-models/{model_id}/response-optimizations/{optimization_id}
```

Creation requires `expected_model_manifest_sha256`. Restore revalidates the
analysis/config/result relationship and the current model manifest SHA-256.
The optimization is persisted as a generic owned analysis result using:

- method `regression.linear_model_optimizer` `0.1.0`;
- config schema `1`; and
- result schema `1`.

The method is deliberately absent from the visible method catalog. Model
deletion preflight reports dependent optimizer results and blocks deletion;
the user must delete those generic analyses first. Existing model and RSM
optimizer artifacts are never rewritten.

## Limitations

- one response only;
- no optimization outside the recorded training domain;
- no arbitrary nonlinear constraints;
- no categorical-combination search above the configured cap;
- no claim that the numerical search found the global optimum; and
- no automatic confirmation-experiment result.

