# Bayesian Study Lifecycle Contract

Last updated: 2026-07-16

## Scope And Current State

This contract defines the implemented bounded lifecycle for closing an
immutable Bayesian Optimization study. Method `0.2.2` provides an explicit
status-transition API and read-only restore UI. Trial completion and trial
abandonment remain separate terminal trial transitions; close never changes a
trial implicitly.

The study definition, completed observations, history revisions, recommendation
snapshots, and checksums remain immutable. Closing a study must never execute an
objective, create a recommendation, change a completed observation, or rewrite
an earlier artifact.

## States

- `active`: observations and recommendations may be accepted subject to the
  existing pending-trial, minimum-observation, budget, and checksum gates.
- `completed`: the user explicitly declares that the experimental objective is
  complete. No further observation, abandonment, or recommendation is allowed.
- `abandoned`: the user explicitly stops the study before normal completion.
  No further observation, abandonment, or recommendation is allowed.

Only `active -> completed` and `active -> abandoned` are valid. Reopen is
forbidden in lifecycle schema 1. Continuing later requires a new study with a
new ID and explicit `predecessor_study_id`; old artifacts are not copied or
relabeled.

## Transition Preconditions

1. The client supplies the current `study_version` and current history revision
   ID/SHA for optimistic locking.
2. The service reloads and checksum-validates the complete study, trials,
   histories, and recommendations before the transition. The storage
   transaction then reacquires a write lock and rechecks active status, current
   version/history ID/SHA, final counts, and latest recommendation before it
   writes the event.
3. No pending trial may exist. Users must first complete or abandon each
   pending trial through the existing terminal trial workflow. A close endpoint
   must not silently abandon pending trials.
4. `completed` requires at least `max(2, factor_count + 1)` completed
   observations and at least one persisted recommendation result. This denotes
   workflow completion, not statistical convergence or a global optimum.
5. `abandoned` does not require the minimum completed-observation count, but it
   requires a nonempty user-selected reason code and may include a bounded
   user note that is stored as text metadata, never logged.
6. A repeated identical request may be idempotent only when target status,
   expected version/history, reason code, and request ID match. Any other
   second transition returns a conflict.

## Close Metadata

SQLite schema 14 stores:

- `study_id`, prior and resulting status;
- monotonic lifecycle revision;
- close reason code and optional bounded note;
- `closed_at` and audit `created_at` timestamps in UTC;
- final study version, history revision ID/SHA, trial count, completed count,
  abandoned count, and latest recommendation ID when present;
- definition SHA and a canonical lifecycle-event SHA;
- app version and build commit;
- request correlation ID or idempotency key, without raw objective values,
  filenames, credentials, paths, or request bodies.

Suggested reason codes include `objective_satisfied`, `budget_reached`,
`confirmation_complete`, `unsafe_or_infeasible`, `resources_unavailable`, and
`study_cancelled`. Free-form text never replaces the stable code.

## API Acceptance Criteria

The implemented action route is
`POST /api/v1/bayesian-studies/{study_id}/close`, with a typed request for
`completed` or `abandoned`. It:

- return the refreshed typed study plus immutable close metadata;
- reject an invalid transition with stable codes such as
  `bayesian_study_close_pending_trials`,
  `bayesian_study_completion_requirements_not_met`,
  `bayesian_study_close_conflict`, and `bayesian_study_closed`;
- block observation completion, trial abandonment, and recommendation creation
  after close in both the service and storage transaction;
- preserve list/get/history/recommendation restore for closed studies;
- expose no traceback, SQL, absolute path, coordinate, or objective value in an
  error;
- update OpenAPI/frontend field guards and avoid a generic analysis-run route.

## UI Acceptance Criteria

- Show `active`, `completed`, and `abandoned` with text, not color alone.
- Require an accessible inline confirmation showing the study ID/name, final
  counts, target status, and irreversible effect.
- Disable close while a trial is pending and explain which terminal action is
  required first.
- Require a stable reason selection and show that completion is not proof of a
  global optimum.
- Render closed studies read-only while retaining history, recommendations,
  predicted values, actual observations, warnings, and provenance.
- Never present a reopen button. A `Create successor study` command must create
  a new definition after showing what is and is not carried forward.

## Retention And Deletion

Close is not deletion. Closed studies remain restorable until a separate
deletion action is confirmed. The first retention slice now provides a typed
preflight and confirmed atomic deletion for a closed Bayesian metadata graph.
It blocks active studies and predecessor studies referenced by successors,
shows exact metadata/file counts, and requires the current canonical deletion
manifest SHA. It never cascades into a successor.

The Bayesian graph currently owns no workspace file. Broader dataset,
analysis/export, DOE, model, and limit-set cleanup remains governed by
`docs/workspace_retention_contract.md` and is not implemented by the Bayesian
route.

## Migration And Tests

The implementation uses a forward-only SQLite schema-14 migration for lifecycle
events/close metadata and nullable successor `predecessor_study_id`. Upgrade tests start from schema 13 and prove
that existing studies remain `active` without invented close timestamps or
reasons. Required tests cover:

- valid completed and abandoned transitions;
- insufficient observations and no-recommendation completion rejection;
- pending initial and recommendation trial rejection;
- optimistic-lock and concurrent-close conflicts;
- idempotent retry and incompatible second transition;
- all post-close mutation endpoints blocked;
- closed study/history/recommendation restore and paging;
- lifecycle-event SHA and DB relationship tamper;
- legacy active-study upgrade;
- no raw objective value, coordinate, traceback, SQL, or internal path leakage;
- frontend confirmation, disabled/read-only states, stale-response protection,
  and reload restore.
- active/referenced deletion rejection, exact manifest confirmation, atomic
  graph removal, rollback on graph change, redaction, frontend impact review,
  and browser removal after reload.

Method `0.2.2` is a patch release because it adds lifecycle orchestration and
immutable audit metadata without changing the GP kernel, EI calculation,
duplicate policy, numerical defaults, or the meaning/checksum of existing
study, history, recommendation config/result, and model schema-1 artifacts.
Lifecycle event schema starts at 1 and SQLite advances from 13 to 14. Existing
`0.1.0`, `0.2.0`, and `0.2.1` assets retain their recorded versions; no close
event is invented for a legacy active study.
