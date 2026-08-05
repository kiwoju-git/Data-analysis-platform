# Bayesian Optimization Contract

Last updated: 2026-07-30

## Current Status

`doe.bayesian_optimization` is an available dedicated API/UI method at version
`0.5.0`. New studies use study schema `4`; readers retain study schemas `1`,
`2`, and `3` and their recorded method versions without rewriting checksums.
`2`, methods `0.1.0` through `0.3.0`, and legacy single recommendations without
rewriting them. The application stores an immutable bounded study and
observation history, fits a Matérn 5/2 Gaussian Process to explicit completed
trials, and creates either one sequential candidate or a synchronous batch of
two through eight pending confirmation trials. It never runs the user's
objective.

No generic analysis-run execution API is provided. `POST /api/v1/analysis-runs`
returns `analysis_method_uses_dedicated_api` with
`/api/v1/bayesian-studies`; the method is executed only through its dedicated
study lifecycle. A recommendation is not an observation and is not a claim of
a guaranteed global optimum.

User guidance describes the current executable behavior directly: completed
manual observations are used to fit the Matérn-5/2 Gaussian Process and
Expected Improvement proposes the next confirmation experiment. It must not
refer to this method as planning-only, and it must always say that the proposal
is not an observed value, does not run the experiment, and does not guarantee a
global optimum.

Current routes are:

- `POST/GET /api/v1/bayesian-studies`;
- `GET /api/v1/bayesian-studies/{study_id}`;
- `POST /api/v1/bayesian-studies/{study_id}/close`;
- paged `GET .../{study_id}/trials`;
- `PUT .../{study_id}/trials/{trial_id}/observation`;
- `POST .../{study_id}/trials/{trial_id}/abandon`;
- paged immutable `GET .../{study_id}/history` and revision restore;
- `POST/GET .../{study_id}/recommendations`;
- `GET .../{study_id}/recommendations/latest`;
- `GET .../{study_id}/recommendations/{recommendation_id}`.
- `POST/GET .../{study_id}/recommendation-batches`;
- `GET .../{study_id}/recommendation-batches/latest`;
- `GET .../{study_id}/recommendation-batches/{batch_id}`.

The frontend route uses the DOE module's dynamically loaded thin
`BayesianOptimizationPanel` compatibility export over
`features/bayesian/BayesianOptimizationWorkspace`. Builder, catalog, trial,
recommendation, close, retention, and confirmation UI are separate components;
draft, catalog, lifecycle, recommendation, and retention state use separate
hooks and independent latest-request guards. It creates/restores studies, distinguishes initial
and recommendation trials, records or abandons pending trials through an
explicit irreversible-action confirmation, and renders the actual latest
candidate's immutable prediction snapshot separately from its current trial
state and any completed observation. It also restores closed studies read-only
and can prepare a new study definition with an explicit
`predecessor_study_id`; close is not deletion or reopen.

The metadata-only study catalog uses pages of 20 rather than a fixed first-50
fetch. An exact Study outside the current page remains selectable through
`GET /api/v1/bayesian-studies/{study_id}`. The route stores only validated UUID
query values:

```text
/analysis/doe/doe.bayesian_optimization?study_id={uuid}&batch_id={uuid}
```

Legacy `recommendation_id` direct links remain readable. `batch_id` and
`recommendation_id` together are rejected rather than assigned an ambiguous
precedence. Reload uses exact relationship-checked routes. Selecting a
different Study clears both IDs. Successor preparation preserves the predecessor
seed only visibly: the UI warns that reuse may regenerate the same initial
conditions and offers an explicit new-seed action. It never silently changes a
seed or copies observations, history, or recommendations.

Study selection is also an action boundary. Catalog, Study, and recommendation
restore are included in the action lock. A Study or recommendation is rendered only when its
`study_id` equals the current catalog selection, and selection changes immediately clear or hide
prior actions. Independent lifecycle, recommendation, and retention guards reject late responses
and reset their loading flags when selection changes.

## Lifecycle And Inputs

1. Create one immutable study with one to six continuous or fixed-step numeric
   factors, finite actual
   low/high bounds, one numeric maximize, minimize, or match-target objective,
   and up to 16 known
   actual-unit linear inequalities.
2. Select an explicit initial design policy. An unconstrained study defaults
   to `latin_hypercube_random_cd_v1`; a constrained study uses
   `sha256_counter_uniform_feasible_v1`. LHS plus linear constraints is rejected
   rather than silently changing policy. `initial_design_size` must be at least
   `max(2, factor_count + 1)`; the stable rejection code is
   `bayesian_study_initial_design_too_small`.
3. Generate pending initial trials. A trial has coordinates but no objective
   value until the user performs the real experiment and records it.
4. Complete or explicitly abandon every required initial trial. GP/EI remains
   unavailable while a required initial trial is pending or while fewer than
   `max(2, factor_count + 1)` completed observations exist.
5. Fit the GP and create one sequential recommendation or one synchronous
   batch only after the above conditions, exact remaining budget, active-study,
   current-history, and no-pending-recommendation checks pass.

The UI presents this as initial conditions, real experiment, response input,
GP availability, one next-condition recommendation, another real experiment,
and GP update. A GP surrogate does not require the raw response column to pass
a normality test as a gate. Its predicted standard deviation is not a
specification limit or a confidence interval, and a recommendation is never
stored as an observation.

Standalone LHS is not automatically imported into a Bayesian Study. The
future atomic import contract is documented in
`docs/bayesian_initial_observation_import_contract.md`.
6. Record one finite user-observed value for each pending trial or explicitly
   abandon it. Completed and abandoned trials are terminal.
7. Append an immutable ordered observation-history revision. No completed trial
   or history revision is overwritten.
8. After all initial trials are closed and at least `max(2, factor_count + 1)`
   observations are completed, fit the versioned GP and optimize EI.
9. Persist exactly `batch_size` pending `origin=recommendation` trials in one
   transaction. A partial batch is never committed.
10. The user records or abandons each real experiment. Every completion appends
   a history revision, but another batch remains blocked until every item in
   the current batch is completed or abandoned.

An initial-design trial cannot be abandoned when the remaining completable
initial trials would be fewer than `max(2, factor_count + 1)`. That transition
returns `bayesian_trial_abandon_would_strand_study`; a larger initial design may
abandon a surplus trial, and a recommendation-origin trial may still be
abandoned. Abandon never creates a completed-observation history revision.
Completed and abandoned trials cannot be reopened or completed again.

Study close permits only `active -> completed|abandoned`, requires optimistic
study-version and history ID/SHA fields, and rejects any pending trial. A
completed close also requires the minimum completed-observation count and at
least one persisted recommendation. An abandoned close may occur below the
minimum only after pending trials are explicitly abandoned with
`intent=close_study`. Identical retries are idempotent by request ID and exact
payload; incompatible second closes conflict. After close, observation,
abandonment, and recommendation writes return `bayesian_study_closed`, while
study/history/recommendation restore remains available.

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
EI = max(I, 0), when sigma <= 0
```

The incumbent is the best completed trial, never a predicted value. A seeded
bounded candidate pool is filtered by actual-unit constraints and normalized
duplicate tolerance, ranked by EI, then refined with bounded SLSQP local starts.
Coordinates from every existing trial state, including completed, pending, and
abandoned, are duplicate exclusions. Abandon may mean unsafe, infeasible, or
too costly, so the same point or a point within the declared duplicate tolerance
is not silently recommended again. No feasible novel point is an explicit
error; the service does not return a random point or duplicate fallback.

The persisted result keeps actual/normalized coordinates, predicted mean,
posterior standard deviation, EI, incumbent, objective direction, constraint
evaluations, model artifact, requested/consumed budgets, termination reason,
warnings, and limitations. Every result retains
`bayesian_optimization_confirmation_required` and
`bayesian_optimization_no_global_optimum_guarantee`.

For `match_target`, classic directional EI is not reused. The implementation
uses analytic Expected Target Improvement over
`max(d_best - xi - |Y - target|, 0)` for a normal GP posterior. It stores the
target, current closest observed distance, predicted target distance, and ETI
separately from directional EI. The optional target tolerance is explanatory
and never auto-closes a Study.

Exploration profiles resolve to standardized, dimensionless `xi` values:
exploitation `0.0`, balanced `0.01`, exploration `0.1`, or an explicit custom
value from `0` through `10`. A larger value generally raises exploration
pressure but does not guarantee a farther candidate for every dataset.

The synchronous batch calculation and lifecycle are specified in
`docs/bayesian_batch_recommendation_contract.md`. It is not exact joint qEI.

## Budgets And Failures

Requests are bounded to six factors, 200 total trials, 200 completed
observations, 201 observation-history revisions including the initial empty
revision, 4,096 initial acquisition candidates, 16 local starts, 20,000
acquisition evaluations, three
hyperparameter restarts, 2,000 model evaluations, and 60 seconds calculation
time. The parent starts a Windows spawn-safe worker, applies a startup allowance,
terminates it on timeout, and returns a redacted stable error. History is never
silently sampled.

The recommendation request's effective total-trial budget defaults to 50 and
cannot exceed the hard 200-trial limit. The frontend displays this budget,
restores the latest recommendation request's value, and disables recommendation
when the current trial count reaches it. The backend remains authoritative and
returns `bayesian_optimization_budget_exhausted` for request-trial, model-fit,
acquisition, or parent-worker time exhaustion. Time exhaustion is never
relabeled as surrogate-fit failure. A successful best-candidate result that
stops after a time budget records `termination_reason=time_budget` and a
specific persistent warning; no partial fitted model is persisted.

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

Lifecycle-correctness codes added or made public are:

- `bayesian_study_initial_design_too_small`
- `bayesian_trial_abandon_would_strand_study`
- `bayesian_observation_limit_reached`
- `bayesian_optimization_budget_exhausted`
- `bayesian_study_close_pending_trials`
- `bayesian_study_completion_requirements_not_met`
- `bayesian_study_close_conflict`
- `bayesian_study_closed`
- `bayesian_study_predecessor_invalid`
- `bayesian_study_deletion_active`
- `bayesian_study_deletion_referenced`
- `bayesian_study_deletion_confirmation_mismatch`
- `bayesian_study_deletion_conflict`

## Persistence And Provenance

SQLite schema 12 preserves schema-11 studies and recreates `bayesian_trials`
with `initial_design` and `recommendation` origins. It adds
`bayesian_recommendations`, which relates each immutable recommendation to its
study version, pending trial, source history revision, method/config/result/model
versions, canonical config/result checksums, creation time, and app version.
Schema-11 `0.1.0` study assets remain restorable without being relabeled.
SQLite schema 14 adds the immutable `bayesian_study_lifecycle_events` relation
and nullable self-referencing `predecessor_study_id`. Lifecycle event schema 1
pins final trial counts, history ID/SHA, latest recommendation, definition SHA,
reason, timestamps, app/build provenance, request ID, and its canonical event
SHA. Schema-13 active studies upgrade without an invented event or status.

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
recommendation snapshot. The latest endpoint and list/get responses therefore
add a transient `current_trial` view and `is_latest` flag after validating the
stored artifact; these view fields are not written into the checksummed result.

## Closed Study Deletion

A closed `completed` or `abandoned` study may be deleted only after
`GET /api/v1/bayesian-studies/{study_id}/deletion-preflight` validates the full
study graph and returns exact metadata/file counts plus a canonical manifest
SHA. `DELETE /api/v1/bayesian-studies/{study_id}` requires that SHA and the
exact study ID, then reacquires a SQLite write lock and rechecks the graph before
one atomic metadata transaction.

Active studies and predecessor studies referenced by a successor are blocked.
There is no cascade into successors. The immutable recommendation snapshot is
not edited as part of deletion; it is removed only with its complete owning
closed graph. The current graph owns no files, so schema-1 preflight reports
zero files and bytes. Dataset/analysis/DOE/export cleanup is a later file-aware
slice defined in `docs/workspace_retention_contract.md`.

## Version Decision

Method `0.5.0` and study schema `4` add executable factor domains, mixed LHS
initial design, grid-aware acquisition candidates, atomic multi-observation
completion, and initial-design CSV. `discrete_numeric` candidates are selected
from legal levels before constraints and duplicate checks; continuous-search
results are never merely rounded afterward. The Study summary exposes factor
bounds, units, step/level count, objective, initial policy/quality, and initial
trials without an additional data request.

`PUT /api/v1/bayesian-studies/{study_id}/observations/batch` validates the
entire trial/value set before one `BEGIN IMMEDIATE` transaction. It changes all
selected pending trials, writes exactly one history revision, and advances one
head or rolls back everything. The request UUID is a durable revision ID:
identical replay returns the recorded batch even after later history advances,
while a different payload conflicts. The single-observation endpoint and
individual immutable abandon transition remain supported.

`GET /api/v1/bayesian-studies/{study_id}/initial-design.csv` exports only
`origin=initial_design` trials in definition factor order as UTF-8-SIG. Actual
coordinates honor display precision; normalized coordinates are not mixed into
the basic export. Formula-like text headers are escaped.

No relational field is required: study definitions and histories already use
versioned JSON plus existing tables. SQLite remains schema 18.

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

The first sequential-lifecycle stabilization kept method `0.2.0` and recommendation
config/result/model schemas 1. It adds stricter rejection of internally
inconsistent artifacts, reference/benchmark evidence, and frontend construction
of the already-versioned linear-constraint request. It does not change the GP,
EI formula, defaults, persisted field meaning, or checksum payload.

The lifecycle-correctness stabilization moves the method to patch version
`0.2.1`. Excluding abandoned coordinates closes a duplicate-recommendation
gap in the already-declared no-duplicate/no-fallback contract; it does not
change the Matern kernel, EI formula, objective meaning, numerical defaults, or
stored schema. Study/history and recommendation config/result/model schemas
remain 1, SQLite remains schema 13, and no migration is required. Valid stored
`0.2.0` recommendations retain their recorded method version and restore
without relabeling. Planning-only `0.1.0` studies remain restorable, but a
forged `0.1.0` recommendation is rejected because that version never produced
numerical recommendation artifacts. The initial-design minimum, 200/201 bounds,
latest/current view, and public budget error are validation/access corrections
under the same persisted field meanings.

The study-close lifecycle slice moves the method to patch version `0.2.2`.
It adds explicit close orchestration, immutable lifecycle event schema 1,
successor lineage, post-close storage gates, and read-only UI restore. Existing
study/history and recommendation config/result/model schemas remain 1 because
their payload and checksum meanings do not change. SQLite moves from schema 13
to 14 for the new relation and predecessor column. Valid `0.2.0` and `0.2.1`
recommendations restore with their recorded versions and are never relabeled.

The closed-study deletion slice keeps method `0.2.2`, SQLite schema 14, and all
existing artifact schemas unchanged. Preflight and deletion-response schemas
start at 1. The deletion manifest is an operational confirmation hash and does
not change the meaning or checksum of any stored recommendation.

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
staleness, 200 completed observations plus 201 histories, stranded-study
abandon rejection, abandoned-coordinate exclusion, 21-plus recommendation
latest retrieval, current trial reconciliation, trial/time budgets, terminal
transition confirmation, migration, checksum tamper, redaction, and typed
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

Catalog graph-validation latency is measured separately for 20, 100, and 500 Study catalogs,
including a real 100-trial/101-history/36-recommendation graph. See
[Bayesian catalog performance](bayesian_catalog_performance.md). The catalog continues to fully
validate every item; a lightweight verified summary/index remains separately scoped.

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

Study-level completion and abandonment transitions are executable under
`docs/bayesian_study_lifecycle_contract.md`. Retention/deletion, ownership-graph
cleanup, and storage reclamation remain out of scope; close never removes an
artifact.
