# Analysis completion consistency

## Scope and acceptance

A13 closes a metadata race without changing an analysis algorithm, request,
result envelope, model manifest, stored prediction, or numerical tolerance.
The backend must capture one coherent source schema and must not publish a
completed result as current when its captured source changed during execution.
This implements the immutable-source and stale-result requirements in
`AGENTS.md` sections 7, 8, 11 and 14 and the source-change policy in the PRD
addendum. It does not add a SQLite migration; A13's separate execution-status
migration is independent of this change.

## Coherent input metadata

`get_dataset_rows_metadata_snapshot` reads the dataset version, owning upload,
ordered column metadata, and canonical-row artifact registration in one
explicit SQLite read transaction. `get_dataset_rows_context` consumes that
snapshot and retains its existing parsing, ownership and path validation.

The transaction ends before raw-row iteration, fitting or statistics. A schema
save cannot cause an A-version schema hash to be paired with B-version column
labels or units. Neither a database read transaction nor a write lock is held
through numerical execution.

## Atomic completion

All new production insertions pass immutable `AnalysisCompletionDependencies`:
captured dataset-version/schema-hash pairs and, for model-derived workflows,
the exact model ID, owning analysis ID, source version, manifest hash and fit
schema hash. Duplicate identical dataset dependencies are permitted when the
prediction source and target are the same version; contradictory hashes are
rejected rather than silently choosing one.

The three analysis insertion entry points obtain `BEGIN IMMEDIATE`, validate
the captured owners, compare dependency hashes, and insert run/artifact/model
metadata in that same transaction:

- A changed schema or stale source model produces `succeeded` with metadata
  `stale=true`; it does not rewrite the completed artifact.
- If completion wins the write lock first, the later schema CAS marks the new
  result stale. If the schema CAS wins first, completion itself stores stale.
- Source-model schema changes also invalidate existing dataset predictions,
  pasted predictions and regression response optimizations whose target
  dataset differs from the model's source dataset.
- A no-op schema save does not invalidate a pending or completed result.
- A missing required owner or changed model identity aborts registration.
  Existing writer cleanup removes only the new result/snapshot/model files
  owned by that attempted completion. Original source files are preserved.

Stable HTTP 409 errors are `analysis_completion_source_missing`,
`analysis_completion_source_changed`, and `analysis_completion_dependency_invalid`.
Their public message contains no file path, SQL, source values or traceback.
Other exceptions keep their existing behavior; they are not converted to
successful or stale results.

| Completion writer | Captured dependencies |
| --- | --- |
| `analysis_run_execution.store_succeeded_analysis_result` | Source dataset version and schema; shared classical statistics, PCA and Two Variances |
| `analysis_runners_regression._store_succeeded_linear_model_result` | Fitted source version/schema; OLS and regularized regression |
| `analysis_runner_pls._store_result_and_model` | Fitted source version/schema |
| `analysis_runner_gaussian_process._store_result_and_model` | Fitted source version/schema |
| `regression_models._persist_prediction_response` | Target version/schema plus captured model/source identity |
| `regression_pasted_predictions._persist` | Validated pasted-prediction model/source identity |
| `regression_response_optimizer._persist` | Model/source identity captured before optimization |

The low-level insertion compatibility path still accepts omitted
dependencies for synthetic or historical registration. A source-level test
requires the explicit argument at every production service completion call.
This is not a runtime inference from arbitrary legacy result JSON.

## Verification

`test_analysis_completion_consistency.py` exercises both transaction orderings,
coherent WAL read snapshots, a deterministic two-thread write-lock boundary,
no-op saves, source-only and target-only schema changes, retained stale state,
deleted owners, model identity changes and invalid captured dependencies.
Events and explicit transaction boundaries are used rather than timing sleeps.

`test_analysis_completion_writers.py` runs API-created synthetic descriptive,
OLS, ridge, PLS and GPR analyses and real dataset prediction, pasted prediction
and regression optimizer requests. Each interleaving occurs after the existing
calculation and before metadata publication. Tests compare the exact result,
snapshot, manifest and NPZ bytes around publication, retain original schema
provenance, and verify cleanup following ownership deletion. There is no
second fit or prediction at publication.

The focused commands and final integrated run evidence are recorded in
`docs/end_to_end_remediation.md`; counts there must come from actual completed
runs. Windows, Linux and browser validation are separate evidence categories.

## Boundaries and compatibility

- Freshness is mutable metadata. Archived result/model bytes and checksums are
  immutable, including legacy schemas and previously completed analyses.
- No method version or statistical result-schema bump is required for this
  metadata-only correction. Numerical reference tests remain applicable.
- This boundary covers the seven generic analysis completion writers, not an
  inferred graph of every dedicated DOE/BO revision or Phase II baseline.
  Those workflows retain their explicit existing source contracts.
- Client request ownership and cancellation are separate. A stale browser
  request must not replace current UI state; this database guard does not
  claim to cancel computation or infer changes unseen by another browser tab.
- The workspace lease and normal application mutation paths define the
  cooperating-process threat model. Direct hostile edits to SQLite or files
  outside these paths are not made safe by a freshness flag.
- SQLite write locking is limited to metadata validation and registration;
  large result files are not read or hashed again while holding that lock.
