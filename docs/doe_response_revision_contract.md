# DOE Response Revision And History Contract

Last updated: 2026-07-15

## Status And Scope

Implemented in the current working tree for `doe.factorial_design` and
`doe.response_surface`. SQLite schema 10 stores immutable completed/abandoned
response revisions, their ordered values, one current head per response-name
stream, and the exact revision relationship used by each new DOE analysis.

The legacy response `PUT` remains available before analysis and now creates a
new immutable revision instead of overwriting history. It still returns 409
after analysis. Explicit correction uses the revision API, creates a new
completed revision, and never updates an older revision's values or SHA.

No draft revision or response overwrite is implemented. Abandon is limited to
completed historical revisions that are neither current nor referenced by an
analysis.

## Versions

| Contract | Version |
| --- | ---: |
| response revision schema | `1` |
| SQLite metadata | `10` |
| Factorial method / analysis envelope / config | `0.3.0` / `2` / `2` |
| RSM method / analysis envelope / config | `0.2.0` / `2` / `2` |
| Factorial/RSM calculation result | `1` |
| Response Optimizer method / config / result | `0.3.0` / `2` / `2` |

The statistical formulas and calculation-result schemas remain unchanged. The
method minor bumps identify the new persisted response-revision dependency
semantics. Older method-version records are not silently assigned the new
version.

## Identity And State

Each response revision records:

- stable `response_revision_id` and monotonic `revision_number` within one
  design-version/response-name stream;
- immutable `design_id`, `design_version_id`, ordered run set, response name,
  optional unit, and finite numeric values;
- `response_revision_schema_version` and canonical
  `response_revision_sha256`;
- `created_at` and nullable `closed_at` timestamps;
- state `completed` or `abandoned`; draft/pending input, if implemented, is not
  an analyzable revision and must never be returned as completed;
- optional `supersedes_response_revision_id`, which links history without
  changing the older revision.

The canonical SHA covers schema version, design version ID, response name,
unit, and values ordered by the design's immutable `run_order`. It must not
contain a workspace path, original filename, or unrelated response value.

## Analysis And Optimizer Dependencies

Every new DOE/RSM analysis stores the exact `response_revision_id` and
`response_revision_sha256` it used. Restore verifies the design version,
revision identity, ordered run/value SHA, method/config/result relationship,
and current artifact checksum. An analysis remains pinned to its historical
revision when a newer correction exists; it is never recalculated silently.

Response Optimizer remains pinned to the source RSM analysis and therefore to
that analysis's design version and response revision. A newer response revision
does not mutate an older optimizer result. Users must fit a new RSM analysis and
create a new optimizer result to use corrected observations.

## Correction Workflow

1. Open the current response and its immutable history.
2. Choose `새 revision으로 수정` and start from the current values or an empty
   draft; the old revision remains read-only.
3. Keep the response-stream name fixed, edit unit/values, and review the
   affected run count. A different response name starts a separate stream and
   is not a correction of the old stream.
4. Validate a complete exact run set and finite values.
5. Close the new completed revision atomically and mark it current for future
   analyses. A cancelled correction becomes abandoned or is removed only if it
   never became an immutable completed revision.
6. Run a new analysis explicitly. Historical analyses continue to show their
   original revision number/SHA.

No endpoint may update the values, name, unit, SHA, or design dependency of a
completed or abandoned revision in place.

## Current And History API

Implemented typed endpoints:

```http
POST /api/v1/doe-designs/{design_id}/response-revisions
GET  /api/v1/doe-designs/{design_id}/response-revisions
GET  /api/v1/doe-designs/{design_id}/response-revisions/{response_revision_id}
POST /api/v1/doe-designs/{design_id}/response-revisions/{response_revision_id}/abandon
```

They can:

- create a new response revision for a design version;
- retrieve the current completed revision by response name;
- page response revision history newest-first without raw workspace metadata;
- retrieve one checksum-validated historical revision;
- abandon an unconsumed revision through an explicit state transition;
- create Factorial/RSM analyses only from a selected completed revision. For
  backward request compatibility, omitting `response_revision_id` resolves the
  current completed revision and persists that resolved ID explicitly.

Responses must distinguish `current` from historical records. The UI must show
revision number, state, timestamps, SHA prefix, response name/unit, and which
revision each analysis used. Analyzed revisions and all historical revisions
are read-only. The UI must not imply that editing the current draft changes an
older result.

## Multi-Response Policy

One design version may have multiple response-name streams. Each stream has its
own monotonic revisions and one current completed revision. Response names are
the stream identity and remain fixed across a superseding correction. A new
name creates a separate stream rather than mutating historical identity.
Analyses select one completed response revision. A future multi-response
optimizer selects explicit source RSM analysis IDs, not mutable response names.

All planned response streams should be completed before the first analysis when
using the current lock workflow. The revision foundation may permit adding a
new response stream after another response was analyzed only if it cannot alter
the prior run table, design version, response revision, or analysis dependency.

## SQLite Migration

Schema 10 adds normalized immutable records:

- `experiment_response_revisions`: revision identity, design version,
  response name/unit, revision number, state, timestamps, supersedes ID, SHA;
- `experiment_response_revision_values`: revision ID, run order, numeric value,
  with a unique `(response_revision_id, run_order)` constraint;
- `experiment_response_heads`, one current revision per design-version/name;
- `experiment_design_analysis_response_revisions`, containing analysis ID,
  revision ID, and revision SHA.

Migration preserves each schema-v9 current response stream as a deterministic
legacy/imported revision 1 with the same canonical response SHA. Existing
analysis JSON and checksums are never rewritten. An old analysis relationship
is backfilled only when its recorded response SHA exactly equals that imported
revision; the migration does not invent overwritten history.

## Validation

- migration from schema v9 with existing response rows, including a Windows
  path with spaces and Korean characters;
- deterministic ordered run/value SHA and Windows-safe restore;
- new correction creates a new ID/number/SHA and leaves the old revision bytes
  and metadata unchanged;
- current/history pagination and independent multi-response streams;
- completed/abandoned state transitions and invalid transition rejection;
- incomplete/duplicate/missing run sets and non-finite values rejected;
- analysis config/result pinned to exact revision ID/SHA;
- old analysis and optimizer restore after a newer revision is current;
- revision/config/result/design tamper and stale dependency rejection;
- analyzed/historical UI read-only state, explicit correction workflow, and
  newest-first history rendering;
- no path, filename, raw request logging, or unrelated response value exposure.

## Stable Errors

- `doe_response_revision_not_found`
- `doe_response_revision_state_invalid`
- `doe_response_revision_run_order_duplicate`
- `doe_response_revision_run_set_mismatch`
- `doe_response_revision_checksum_mismatch`
- `doe_response_revision_dependency_mismatch`
- `doe_response_revision_conflict`
- `doe_response_revision_already_closed`

Missing, state, run-set, checksum, conflict, and cross-artifact relationship
failures remain distinct.
