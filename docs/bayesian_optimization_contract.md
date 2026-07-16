# Bayesian Optimization Contract

Last updated: 2026-07-15

## Current Status

`doe.bayesian_optimization` is an available dedicated API/UI method at version
`0.2.0`. The application stores an immutable bounded study and observation
history, fits a Matérn 5/2 Gaussian Process to explicit completed trials, and
uses analytic Expected Improvement to create one pending confirmation-trial
candidate. It never runs the user's objective.

No generic analysis-run execution API is provided. `POST /api/v1/analysis-runs`
returns `analysis_method_uses_dedicated_api` with
`/api/v1/bayesian-studies`; the method is executed only through its dedicated
study lifecycle. A recommendation is not an observation and is not a claim of
a guaranteed global optimum.

Current routes are:

- `POST/GET /api/v1/bayesian-studies`;
- `GET /api/v1/bayesian-studies/{study_id}`;
- paged `GET .../{study_id}/trials`;
- `PUT .../{study_id}/trials/{trial_id}/observation`;
- `POST .../{study_id}/trials/{trial_id}/abandon`;
- paged immutable `GET .../{study_id}/history` and revision restore;
- `POST/GET .../{study_id}/recommendations`;
- `GET .../{study_id}/recommendations/{recommendation_id}`.

The frontend route uses the DOE module's dynamically loaded
`BayesianOptimizationPanel`. It creates/restores studies, distinguishes initial
and recommendation trials, records or abandons pending trials, and renders the
next candidate's posterior mean, posterior standard deviation, EI, warnings,
and confirmation requirement.

## Lifecycle And Inputs

1. Create one immutable study with one to six continuous factors, finite actual
   low/high bounds, one numeric minimize/maximize objective, and up to 16 known
   actual-unit linear inequalities.
2. Generate deterministic bounded initial trials with
   `sha256_counter_uniform_feasible_v1` and an explicit seed.
3. Record one finite user-observed value for each pending trial or explicitly
   abandon it. Completed and abandoned trials are terminal.
4. Append an immutable ordered observation-history revision. No completed trial
   or history revision is overwritten.
5. After all initial trials are closed and at least `max(2, factor_count + 1)`
   observations are completed, fit the versioned GP and optimize EI.
6. Persist one recommendation and its pending `origin=recommendation` trial.
   Only one pending recommendation is allowed.
7. The user performs the experiment and records the actual response, or
   abandons the trial. Completion appends a new history revision before another
   recommendation is permitted.

P0 rejects categorical, ordinal, integer, conditional, unbounded, nonlinear,
learned, probabilistic, and hidden constraints. The dedicated frontend accepts
up to 16 typed actual-unit linear inequalities, requires a stable ID/name and
at least one nonzero finite coefficient, and renders both the stored equation
and recommendation-time feasibility evaluation. Study definitions have no
update endpoint.

The app does not call equipment, external services, arbitrary Python, shell,
`eval`, pickle, or joblib. It does not fabricate, average, impute, or infer an
objective value.

## Surrogate Policy

The calculation worker imports scikit-learn only inside the spawned CPU worker
and limits numerical thread pools to one. It uses scikit-learn 1.7.2
`GaussianProcessRegressor` with:

- factor values scaled from declared bounds to `[0, 1]`;
- objective direction normalized so larger is better;
- completed observations standardized with persisted mean and scale;
- `ConstantKernel * Matérn 5/2` with one ARD length scale per factor;
- constant bounds `[1e-3, 1e3]` and length-scale bounds `[1e-2, 1e2]`;
- explicit diagonal jitter, seed, restart count, fit iteration/evaluation
  budgets, and wall-time checks;
- no kernel substitution, silent jitter escalation, or model fallback.

The model artifact records the fitted kernel string, constant, length scales,
log marginal likelihood, direction multiplier, normalization, jitter,
observation count, restart/evaluation counts, fit duration, and exact
NumPy/SciPy/scikit-learn/joblib/threadpoolctl versions. Posterior standard
deviation is model uncertainty, not a process tolerance or guaranteed
confidence interval.

## Acquisition Policy

For direction-normalized posterior mean `mu`, standard deviation `sigma`,
incumbent completed observation `best`, and exploration `xi >= 0`:

```text
I = mu - best - xi
EI = I * Phi(I / sigma) + sigma * phi(I / sigma), when sigma > 0
EI = 0, when sigma <= 0
```

The incumbent is the best completed trial, never a predicted value. A seeded
bounded candidate pool is filtered by actual-unit constraints and normalized
duplicate tolerance, ranked by EI, then refined with bounded SLSQP local starts.
No feasible novel point is an explicit error; the service does not return a
random point or duplicate fallback.

The persisted result keeps actual/normalized coordinates, predicted mean,
posterior standard deviation, EI, incumbent, objective direction, constraint
evaluations, model artifact, requested/consumed budgets, termination reason,
warnings, and limitations. Every result retains
`bayesian_optimization_confirmation_required` and
`bayesian_optimization_no_global_optimum_guarantee`.

## Budgets And Failures

Requests are bounded to six factors, 200 completed observations, 4,096 initial
acquisition candidates, 16 local starts, 20,000 acquisition evaluations, three
hyperparameter restarts, 2,000 model evaluations, and 60 seconds calculation
time. The parent starts a Windows spawn-safe worker, applies a startup allowance,
terminates it on timeout, and returns a redacted stable error. History is never
silently sampled.

Budget exhaustion during local refinement may retain the best fully evaluated
candidate only with an explicit termination reason and warning. Fit-budget
exhaustion fails rather than persisting a partially fitted model.

Stable execution codes are:

- `bayesian_optimization_history_incomplete`
- `bayesian_optimization_history_stale`
- `bayesian_optimization_pending_recommendation_exists`
- `bayesian_optimization_constraint_invalid`
- `bayesian_optimization_no_feasible_candidate`
- `bayesian_optimization_duplicate_candidate`
- `bayesian_optimization_surrogate_fit_failed`
- `bayesian_optimization_budget_exhausted`
- `bayesian_optimization_artifact_mismatch`

Foundation metadata, trial, and history errors retain the stable
`bayesian_study_*`, `bayesian_trial_*`, and
`bayesian_observation_history_*` families. Errors expose no objective value,
internal absolute path, traceback, SQL, or arbitrary request body.

## Persistence And Provenance

SQLite schema 12 preserves schema-11 studies and recreates `bayesian_trials`
with `initial_design` and `recommendation` origins. It adds
`bayesian_recommendations`, which relates each immutable recommendation to its
study version, pending trial, source history revision, method/config/result/model
versions, canonical config/result checksums, creation time, and app version.
Schema-11 `0.1.0` study assets remain restorable without being relabeled.

Study schema 1 and history schema 1 are unchanged.
`observation_history_sha256` hashes the definition SHA and ordered completed
trial ID, trial number, coordinate SHA, and full-precision objective. Every
completion stores `previous_history_sha256`; request-side
`expected_history_revision_id` provides optimistic locking.

Recommendation config, result, and surrogate-model schemas are each 1. The
provenance records study/study-version/recommendation/trial IDs, source history
ID/SHA, definition SHA, method and all artifact schema versions, app/build/
Python/platform metadata, exact model package versions, and creation time.
Requested/consumed algorithm budgets and transformations remain in the result
and config. Raw filenames, raw request bodies, equipment credentials, and
internal paths are prohibited.

Restore validates definition, factor, constraint, trial, history, config,
result, model, and recommendation relations plus every stored checksum. It also
cross-checks result coordinates against the pending trial and factor scaling,
the model observation count/incumbent against the source history, requested
search settings against consumed-budget metadata, constraint evaluations
against the immutable study definition, required warnings, package versions,
and finite model/result values. The
recommendation's immutable pending-trial snapshot must retain its ID, number,
origin, coordinates, coordinate SHA, and creation time. The current trial may
legitimately transition to completed or abandoned without mutating the stored
recommendation snapshot.

## Version Decision

The catalog method moves from planning `0.1.0` to dedicated executable `0.2.0`
because it now persists numerical GP/EI recommendations. There was no prior
executable result to reinterpret. Study/history schemas remain 1 because their
meaning and checksums are unchanged. Recommendation config/result/model schemas
start at 1. SQLite moves from schema 11 to 12 for the new recommendation table
and expanded trial-origin constraint.

An incompatible algorithm, default, result field meaning, hash payload, or
provenance relationship requires a method or artifact schema decision under
`docs/method_versioning.md`. Old records are never silently assigned a new
version.

The sequential-lifecycle stabilization keeps method `0.2.0` and recommendation
config/result/model schemas 1. It adds stricter rejection of internally
inconsistent artifacts, reference/benchmark evidence, and frontend construction
of the already-versioned linear-constraint request. It does not change the GP,
EI formula, defaults, persisted field meaning, or checksum payload.

## Reference And Validation Policy

`backend/tests/reference/fixtures/doe_bayesian_optimization_reference_policy.json`
records hand-checkable EI cases, a one-dimensional quadratic, independently
documented Branin optima, and a five-seed sequential characterization. The
Branin gate starts from six declared normalized points, permits 14 recommendations
for a total 20-trial budget, and requires every simple regret to be at most
`0.20` with median regret at most `0.15`. Tests compare the production EI calculation to the
hand formula and independently reconstruct the fitted Matérn covariance,
posterior mean, and variance with direct linear algebra. They also cover both
objective directions, seed determinism, constraints, duplicate/feasibility and
fit budgets, spawn-worker API persistence, one-pending recommendation, history
staleness, trial completion, migration, checksum tamper, redaction, and typed
OpenAPI/frontend alignment.

## Local Performance Characterization

Run the CPU-only benchmark with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\benchmark-bayesian.ps1 `
  -Repetitions 3
```

The 2026-07-15 development measurement used Windows 10 Home build 19045,
CPython 3.10.11, one numerical thread, and three fresh spawned workers per
case. Times below are medians in milliseconds:

| Case | Worker round trip | Child calculation | GP fit | Non-fit calculation | Round-trip overhead |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 factor / 8 observations / 256 candidates | 3086.439 | 279.275 | 223.817 | 56.119 | 2860.770 |
| 2 factors / 20 observations / 512 candidates | 2890.613 | 259.589 | 144.691 | 114.898 | 2600.577 |
| 4 factors / 48 observations / 512 candidates | 3135.319 | 712.763 | 165.704 | 537.908 | 2409.312 |

The empty spawn/IPC median was `475.103 ms`. `Non-fit calculation` is child
total minus GP fit and therefore includes imports, validation, candidate
generation, acquisition search, and final prediction; it is not presented as a
pure acquisition-only timer. `Round-trip overhead` includes Windows process
bootstrap and IPC before/after the timed calculation. These observations are
descriptive, not a CI threshold, and actual Windows 11 release measurements
remain pending. Peak memory was not measured in this slice.

Primary method references are Jones, Schonlau, and Welch's
[EGO paper](https://openturns.github.io/openturns/papers/jones1998.pdf) and
Rasmussen and Williams'
[Gaussian Processes for Machine Learning](https://gaussianprocess.org/gpml/chapters/RW.pdf).
The product API policy is tied to the
[scikit-learn Gaussian Process documentation](https://scikit-learn.org/stable/modules/gaussian_process.html),
and Branin values are recorded from the
[BoTorch synthetic-function reference](https://botorch.readthedocs.io/en/latest/test_functions.html).

The dependency spike and 45-wheel Windows AMD64 hash lock are documented in
`docs/scikit_learn_dependency_spike.md`. The measured development host is
Windows 10 build 19045. By product-owner decision, actual Windows 11 x64,
CPython 3.10, CPU-only validation remains a mandatory release gate and does not
block this development slice. No Windows 11 evidence is inferred from Windows
Server or the current host.

## Explicit Non-Goals

Objective execution, completed-observation correction, study-definition edits,
multiobjective/Pareto optimization, noisy or heteroscedastic objectives,
batches, categorical/integer factors, nonlinear or learned constraints,
cost-aware or multi-fidelity optimization, Thompson sampling, knowledge
gradient, guaranteed safe optimization, and guaranteed global optimum claims
remain out of scope.
