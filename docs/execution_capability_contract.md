# Execution Capability and Interrupted Runs

## Scope

All currently available methods execute within a synchronous HTTP request.
`execution_mode` retains its existing route distinction (`inline` or
`dedicated`); a dedicated DOE/model endpoint is not a background queue. A bounded
regularized-model subprocess is also awaited by its request and does not
implement an externally cancellable job.

Each method descriptor now contains `execution_capability`:

```json
{
  "lifecycle": "synchronous_request",
  "cancellation_support": "none",
  "progress_support": "none"
}
```

Planned/disabled methods use `lifecycle: "unavailable"`. The typed cancellation
contract reserves `cooperative` and `process`, and progress reserves `polling`,
but no present method advertises them. Existing method IDs, versions, numerical
budgets, API contract 23 and report capability remain unchanged.

Browser request abortion stops waiting only. It does not confirm server
cancellation. Existing request-loading feedback is not live algorithm progress.
No fake queue, persistent worker, or cancellation acknowledgement is added.

## Audited Resource Limits

Execution capability does not imply an unlimited budget. Resource limits stay
method/option-specific, and are not normalized into a fabricated common budget.
The catalog's nullable `resource_limits` contains audited name/value/unit/variant
items for GPR, PLS, Two Variances and the regularized linear-model option.
Undeclared methods return null, not an empty unlimited-budget claim. Tests bind
the displayed values to enforcing constants/Pydantic bounds/worker slots.
The sources below document these entries and remaining option-specific details.
An unlisted limit is undeclared here, not unlimited.

| Method or option | Actual bound | Enforcing source |
| --- | --- | --- |
| Standalone GPR | 12 predictors, 500 usable rows, LOO 200 rows, 256 optimizer starts | `statistics/gaussian_process_regression.py` MAX_GP constants |
| Standalone GPR options | Final restarts 0-10, CV restarts 0-5, total time 5-600 seconds | `GaussianProcessRegressionOptions` and calculation validation |
| PLS | 100 predictors, 30 components, 20,000 usable rows, LOO 500 rows | `statistics/pls_regression.py` MAX_PLS constants |
| Two Variances | 20,000 usable rows; 500 stored display points per group | `statistics/two_variances.py` MAX_ROWS/MAX_PLOT_POINTS |
| `regression.linear_model` regularized option | One spawned worker slot; user time budget greater than zero and at most 300 seconds, plus 20 seconds transport/startup allowance; result transport at most 64 MiB | `RegularizationCvOptions` / `services/regularized_model_worker.py` |

The regularized option is not a separate advertised method called
`regression.regularized`; it shares the linear-model request. Display-point
limits are distinct from computation row limits. This stage changes none of
these constants, validation rules, concurrency limits or numerical behavior.

## Cancellation Boundaries

Existing DELETE cancellation routes remain, but an existing run/job returns
409 `analysis_run_cancellation_unsupported` / `job_cancellation_unsupported`
without a write. Missing owners return the existing 404 codes. This applies to
terminal and nonterminal synthetic/historical records alike.

The storage-only `request_analysis_run_cancellation_record` and
`request_job_cancellation_record` are conditional primitives for a future owning
executor. They use `BEGIN IMMEDIATE`, read current state, then a guarded UPDATE
from queued/running only. Outcomes are `requested`, `already_requested`,
`terminal`, or `missing`, with the current record, never a stale pre-read copy.
Repeated requests do not advance timestamps. Terminal states and completion
fields cannot be reverted by cancellation. These primitives do not stop a worker
and are not called by the unsupported public routes.

## Restart Recovery and Metadata 22

Migration 22 adds nullable `analysis_runs.failure_code`. It uses an explicit
transaction so ALTER and migration bookkeeping commit together. Existing rows,
immutable configs/results, artifacts and hashes are not rewritten; old runs
read with `failure_code: null`.

Application startup acquires the workspace lease, validates restore state and
metadata compatibility, applies migrations, then recovers interrupted execution
metadata before serving requests. One transaction changes only queued, running,
and cancel_requested jobs/runs to failed, with
`execution_interrupted_on_restart` in jobs.error_code / runs.failure_code.
One timestamp becomes updated_at/completed_at. Progress and cancellation request
flags remain recorded; a restart is not proof of successful cancellation.

Completed states, stale flags, result paths, checksums and file bytes are retained.
Recovery does not kill processes, load source rows, recompute statistics, delete
partial files indiscriminately, or replace corrupt/future-schema workspaces.
Another active workspace lease prevents migration/recovery. A second startup is
idempotent. The recovery count is recorded in
`app.state.interrupted_execution_recovery`.

Run status/history DTOs expose nullable `failure_code`. History shows the
localized restart explanation beside the persisted status and stable code, not
only a disappearing toast. Unknown codes remain escaped literal text. This
targeted change follows installed ui-ux-pro-max feedback/accessibility guidance;
it does not introduce a new visual system or make every row a live region.

## History Query Cost

The history page retains filtering, stable order, offset and limit+1 has_more.
One SQLite read transaction/connection obtains the page and one GROUP BY artifact
count query for only visible IDs (at most 100). Empty pages do not query counts;
missing groups mean zero. Concurrent artifact deletion cannot mix count data
from a newer snapshot into an older page. No artifact files are opened.

## Verification Boundary

Focused tests cover two independent-connection terminal races, idempotence and
deletion, public unsupported cancellation without mutation, real application
lifespan restart recovery, terminal/file preservation, recovery rollback,
migration-22 rollback and legacy rows, fixed page query counts and a concurrent
delete with WAL snapshot isolation. Existing API history tests verify filters
and pagination. Frontend tests verify Korean/English reason text and escaping.

Execution results and any remaining integration failures are recorded in the
work log; this document is a contract, not a claim that unexecuted Linux/full
suite/real-browser checks passed. Backup readers and runtime metadata reporting
must explicitly support schema 22 before release; schema 20/21 archives remain
versioned inputs, not rewritten archives.
