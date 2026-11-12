# Bayesian Initial Observation Import Contract

Last updated: 2026-11-12

## Supported Source

The dataset selected in the common application header is the only dataset input.
The existing upload/paste, parsing confirmation, schema, and immutable canonical
rows are reused. BO does not upload again, generate replacement X coordinates,
attach measured Y to an LHS design, average repeats, or fit a GP during import.
Import from an app-created LHS response revision remains unsupported.

## API

- `POST /api/v1/bayesian-studies/import-preflight`
- `POST /api/v1/bayesian-studies/from-dataset`

Both use contract `schema_version: 1`. Preflight requires `name`,
`dataset_version_id`, `expected_schema_hash`, `factor_mappings`, `objective`,
`response_mappings`, `filter_snapshot`, and `missing_policy`. Optional
`constraints` defaults to an empty list.

Each factor mapping has a source `column_id` and `factor` with the existing
explicit numeric bounds/domain or nominal/ordinal levels and correlation policy.
Each response mapping has `column_id` and an optional `response_id`. Scalar
objectives require exactly one response with null/omitted response ID; vector
objectives require every declared response ID exactly once. X and Y columns
cannot overlap. Numeric factors/responses require a confirmed numeric source
column and finite values. Mixed domains reuse schema-7 vector-objective BO;
scalar mixed-factor BO is not introduced by import.

The filter is the existing version-1 `AnalysisFilterSnapshot`. Missing policy is
explicit: `reject` blocks missing mapped cells; `complete_case` excludes a row
when any mapped X/Y cell is missing and records every affected count. Invalid
numeric values, non-finite values, undeclared category levels, off-grid numeric
values, out-of-bounds points, and constraint violations are rejected, not repaired.

Preflight returns:

- `source`: dataset/version IDs, `schema_hash`, `canonical_sha256`, `raw_sha256`,
  and `filter_sha256`;
- `n_total`, `n_filtered` (excluded by filter), `n_missing` (mapped missing rows
  after filtering), and `n_used`;
- `unique_coordinate_count`, `repeated_coordinate_count` (rows beyond the first
  at identical X), and `conflicting_coordinate_count` (coordinate groups with
  unequal observed Y), plus persistent warning codes;
- `preflight_sha256`, binding the complete normalized request, source identity,
  counts, original zero-based row indices, and full-precision measured values.

The hard limit is 200 retained raw observations after the explicit filter and
missing policy, not 200 unique coordinates. There is no silent truncation.
The canonical iterator always reaches EOF and verifies its recorded hash, size,
row count, and dimensions before successful preflight or creation. At most 200
observation rows are retained in memory; all source rows are streamed.

Commit repeats the same request plus a UUID `request_id` and
`expected_preflight_sha256`. It returns the normal numeric or mixed study
response with HTTP 201. Source metadata and canonical content are revalidated
under the metadata write transaction. Changed source/schema/filter/configuration
rejects commit with a stable conflict code. Duplicate confirmation with the same
request ID and payload returns the same study; changed payload with that ID is
`bayesian_import_request_id_conflict`. A replay returns that study's current
state and does not recreate or modify observations.

## Persistence And Compatibility

Imported initialization has a distinct `dataset_observations_v1` receipt,
`import_schema_version: 1`. It has no generated-design seed, optimizer, LHS
quality, or rejection-attempt fields. It records original row indices, mappings,
filter/missing policy, counts/warnings, source hashes, observations hash, request
identity, and runtime provenance. The stored definition hash covers this receipt.
Numeric study schemas 4/5/6 and mixed schema 7 retain their factor/objective
meaning; receipt policy dispatch distinguishes import from generation.

Every retained row is a completed `initial_design` trial, including repeated X
with equal or unequal Y. The first immutable history revision contains all
imported observations. Existing surrogate, unique-condition readiness, raw trial
budget, recommendation, observation, lifecycle, and report workflows remain in
force. Repeated coordinates are permitted only for imported initial trials or
the existing explicit replicate workflow. Raw measurements remain unchanged.

Metadata migration 34 adds `bayesian_dataset_imports` with a unique request ID,
a study-version owner, source dataset-version foreign key, source/preflight
hashes, and receipt schema version. Study/history/trial/reference writes commit
together or all roll back. Dataset deletion and import serialize with
`BEGIN IMMEDIATE`; foreign keys protect the reference even in direct storage
operations. Normal and cascade dataset deletion are blocked while the imported
study exists. Explicit study deletion cascades its source reference, not its
source dataset. Later dataset schema edits do not rewrite a study's frozen
measured snapshot.

Generated-design readers and their hash definitions are unchanged. Backup accepts
metadata 34 and includes the new table; old supported metadata versions remain
supported. Restore never reserializes stored study artifacts. No new production
dependency, upload route, external transfer, or model artifact loader is added.

Managed scalar/vector/mixed reports dispatch on the same initialization receipt
policy. They validate imported receipt ownership and its observation hash using
only the first `generated_size` stored trials, then read the explicitly requested
history and optional attachment. They do not load the latest study, reread the
source dataset, regenerate a design, or refit a model. Unrelated later trial or
batch corruption is not a dependency of an earlier report. Changed imported
ownership or initial observation content returns `report_source_changed`.

## Validation

`test_bo_dataset_import_api.py` covers exact scalar/vector/mixed X/Y, repeats,
finite/domain checks, explicit missing/filter counts and the 200-row cap, stale
schema/filter/source races, canonical tampering, rollback, concurrent retry,
ownership/deletion, and archive restore with unchanged legacy bytes.
`test_bo_dataset_import_migration.py` verifies the additive 33-to-34 upgrade and
continued readability of generated studies. GP recommendation checks are
separate from these no-fit import tests.
`test_bo_dataset_import_reports.py` exercises managed report creation/download,
exact historical scope, receipt tampering, and unchanged generated-design readers
without GP fitting or dataset rereads.
