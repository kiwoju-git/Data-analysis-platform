# Bayesian Optimization Contract

Last updated: 2026-07-15

## Status And Scope

`doe.bayesian_optimization` is a planning-only catalog method at version
`0.1.0`. This slice fixes the product, safety, reference, and reproducibility
contract. It does not create a study, fit a surrogate, recommend a point, store
a result, or expose an executable API. The generic analysis-run endpoint must
return `analysis_method_not_available` without a recommendation or fake value.

The first executable slice, if separately approved, will support one bounded
sequential study with:

- one numeric objective with explicit `minimize` or `maximize` direction;
- one to six continuous factors with finite actual-unit low/high bounds;
- deterministic completed trial observations entered by the user;
- optional known linear `<=` or `>=` constraints in actual factor units;
- one next-point recommendation at a time;
- explicit seed, trial, candidate, local-search, iteration, evaluation, and
  wall-time budgets.

The app will not call user code, equipment, an external service, arbitrary Python,
shell, `eval`, pickle, or joblib. It will never fabricate an objective
value. A recommendation becomes a completed trial only after the user performs
the experiment and explicitly records the observed response.

## Study Lifecycle

The proposed immutable lifecycle is:

1. Create a study definition and factor space.
2. Generate or record a seeded initial design.
3. Enter actual observations for completed trials.
4. Verify the ordered observation history and checksum.
5. Fit one surrogate from all valid completed trials.
6. optimize one acquisition function inside the feasible region and budget.
7. Persist one pending recommendation with model/acquisition provenance.
8. Accept an observation or explicitly abandon the recommendation.
9. Append a new history version; never overwrite a completed observation.

Only one pending recommendation is allowed in the localhost single-user P0
contract. A stale recommendation cannot be accepted after the factor space,
objective policy, constraints, or completed history changes.

## Input Contract

Each factor records a stable ID, name, actual-unit low/high, unit, order, and
scaling rule. Values are transformed to `[0, 1]` only for surrogate fitting and
acquisition optimization; stored recommendations include both actual and
normalized coordinates. P0 rejects categorical, ordinal, integer, conditional,
and unbounded factors.

The objective records a stable name, unit, direction, and deterministic
observation policy. P0 does not infer direction, transform an objective without
an explicit versioned rule, average replicates, or silently switch to a noisy
model. Replicates and noisy objectives require a later contract.

Known constraints are evaluated before acquisition ranking. P0 permits only
finite actual-unit linear inequalities. Equality, nonlinear, learned,
probabilistic, safety-critical, and hidden constraints remain out of scope.

## Surrogate Policy

The proposed first implementation uses the existing pinned scikit-learn
dependency and `GaussianProcessRegressor` with:

- factors scaled by their declared bounds;
- objective values direction-normalized so larger is better and standardized
  from completed history with the transformation parameters persisted;
- `ConstantKernel * Matérn 5/2` with one length scale per factor;
- explicit finite hyperparameter bounds, deterministic restart count, and seed;
- a recorded diagonal numerical jitter policy rather than silently increasing
  noise until fitting succeeds;
- Cholesky/numerical failures returned as stable errors without changing the
  kernel or falling back to another model.

Kernel specification, optimized hyperparameters, log marginal likelihood,
normalization values, jitter, scikit-learn/NumPy/SciPy versions, warnings, and
fit duration must be persisted. GP posterior standard deviation is model
uncertainty, not a process tolerance or guaranteed confidence interval.

## Acquisition Policy

P0 uses analytic Expected Improvement (EI) after objective direction
normalization. For posterior mean `mu`, standard deviation `sigma`, incumbent
`best`, and exploration parameter `xi >= 0`:

```text
I = mu - best - xi
EI = I * Phi(I / sigma) + sigma * phi(I / sigma), when sigma > 0
EI = 0, when sigma <= 0
```

The incumbent is the best feasible completed observation, not the best
surrogate prediction. Candidate generation and local acquisition refinement
must be seeded and bounded. Already completed points and a current pending point
are excluded using a versioned normalized-distance tolerance. If no novel
feasible point exists, execution fails explicitly; it does not return a
duplicate or random fallback.

The result must distinguish GP posterior mean, posterior standard deviation,
EI, incumbent objective, and observed values. It must state that neither the
acquisition maximum nor the recommendation is a guaranteed global optimum.

## Budgets And Performance

The first executable contract must set conservative Windows/CPU-only limits:

- at most six factors and 200 completed observations;
- explicit initial-design size and total trial budget;
- bounded candidate pool, local starts, optimizer iterations, and evaluations;
- a wall-time budget and single-process execution;
- no silent sampling of history and no unbounded hyperparameter restarts.

Budget exhaustion may return the best fully evaluated feasible acquisition
candidate only when the termination reason and persistent warning are stored.
It must never claim search completion when the budget stopped the calculation.

## Persistence And Provenance

Future study, history, model-fit, and recommendation artifacts require separate
schema/version decisions. At minimum, persisted provenance must include:

- study/study-version/recommendation IDs and method/config/result versions;
- factor space, objective direction, constraint definitions, and their hashes;
- ordered completed trial IDs and `observation_history_sha256`;
- pending/abandoned/completed trial state transitions and timestamps;
- normalized and actual coordinates without internal paths;
- seed and every requested/consumed budget;
- kernel, hyperparameters, normalization, jitter, acquisition, `xi`, incumbent,
  duplicate tolerance, termination reason, and warnings;
- app/build/Python/platform/scikit-learn/NumPy/SciPy versions and creation time.

Raw filenames, internal absolute paths, arbitrary request bodies, and equipment
credentials must not enter provenance or logs. Storage must validate history,
config, model, recommendation, and checksum relationships on restore.

## Planned Errors

These codes are reserved for the future executable contract and are not emitted
by this planning-only slice:

- `bayesian_optimization_factor_space_invalid`
- `bayesian_optimization_objective_invalid`
- `bayesian_optimization_history_incomplete`
- `bayesian_optimization_history_stale`
- `bayesian_optimization_constraint_invalid`
- `bayesian_optimization_no_feasible_candidate`
- `bayesian_optimization_duplicate_candidate`
- `bayesian_optimization_surrogate_fit_failed`
- `bayesian_optimization_budget_exhausted`
- `bayesian_optimization_artifact_mismatch`

Until an executable route exists, the only public execution error is the
existing `analysis_method_not_available` response.

## Reference Policy

`backend/tests/reference/fixtures/doe_bayesian_optimization_reference_policy.json`
is a machine-readable planning fixture. It contains hand-checkable EI cases, a
one-dimensional quadratic, and the independently documented two-dimensional
Branin function with its three global minimizers. It also records the planned
no-objective-execution and no-global-optimum-claim policies.

The future implementation gate requires all of the following:

- GP posterior mean/variance parity against an independently generated fixture;
- EI parity for zero/positive uncertainty and both objective directions;
- deterministic identical recommendations for identical seed/history/config;
- Branin convergence behavior across several declared seeds and budgets,
  without treating one exact trajectory as a proof of global convergence;
- boundary, linear-constraint, duplicate, singular-kernel, stale-history,
  tamper, budget, and path/value-redaction tests;
- browser coverage that records observations explicitly and never displays a
  recommendation as an observed result.

Primary method references are Jones, Schonlau, and Welch's
[EGO paper](https://openturns.github.io/openturns/papers/jones1998.pdf) and
Rasmussen and Williams' [Gaussian Processes for Machine Learning](https://gaussianprocess.org/gpml/chapters/RW.pdf).
The future product API policy is tied to the
[scikit-learn Gaussian Process documentation](https://scikit-learn.org/stable/modules/gaussian_process.html),
while the independent Branin values are recorded from the
[BoTorch synthetic-function reference](https://botorch.readthedocs.io/en/latest/test_functions.html).

## Version Decision

The planned catalog entry starts at `0.1.0` because it has never produced a
stored result. No config/result/history schema number is assigned yet and no
SQLite migration is added. If the first executable implementation changes this
contract materially, its method version must be decided before any result is
persisted; documentation alone is not a silent promise of compatibility.

## Explicit Non-Goals

No executable API, UI execution control, recommendation, surrogate artifact,
or migration is added in this slice. Multiobjective/Pareto optimization, noisy
or heteroscedastic objectives, batches, asynchronous workers, categorical or
integer variables, nonlinear/learned constraints, cost-aware/multi-fidelity
optimization, Thompson sampling, knowledge gradient, guaranteed safe
optimization, and guaranteed global optimum claims remain out of scope.
