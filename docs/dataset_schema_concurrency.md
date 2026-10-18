# Dataset Schema Concurrency

## Contract

Schema edits use compare-and-swap, not last-writer-wins. Each PATCH includes
`expected_schema_hash`, the lowercase 64-hex SHA-256 of the immutable schema
base from which the visible draft was made. API contract 23 adds this required
field; metadata schema remains unchanged. A mismatch returns HTTP 409 with
`dataset_schema_conflict`. A no-op still requires the expected hash to match.
The backend transaction and API enforce this contract; a browser check alone
cannot prevent another tab from saving between a read and a write.

## Three Separate States

- Known committed metadata: the last acknowledged schema, used for roles,
  profile invalidation, and marking analysis results stale.
- Draft base: the original immutable editable fields and schema hash.
- Draft: the current user input, including edits made while a save was pending.

A successful earlier save updates committed metadata. If the draft changed
while that request was pending, its newer text **and its original base** remain
unchanged. This intentionally can cause a subsequent 409; it is not silently
rebased onto the acknowledged write.

A successful no-op whose version, dataset, hash, and every column field match
the known committed schema only acknowledges draft cleanup. It does not replace
the committed version object, invalidate analysis inputs/results, restart reads,
or cancel pending preview/profile requests. Newer draft edits still keep their
original base. This is a UI optimization after a successful server response,
not a bypass of the server CAS check: a stale expected hash still returns 409.

## Conflict Recovery

The existing version GET obtains the latest saved schema after a 409. Loading,
ready, and failed comparison states are explicit. A valid latest read updates
known committed roles and invalidates dependent analysis/profile state, while
preserving the draft and its base. A failed read offers retry without repeating
the write. Raw backend messages are not rendered.

The comparison is field-level for display name, measurement level, role, and
unit. Columns match by exact `column_id`, never display name or position.
Duplicate, missing, extra, or mismatched identities reject the comparison.
User names, units, and private-use characters remain literal text.

- **Apply my changes to latest** overlays only fields changed by the user
  relative to the original base onto the displayed latest schema. Remote-only
  changes survive. This stages a new draft with the displayed latest hash and
  performs **no PATCH**. A separate Save is required. If the server changes
  again before Save, another 409 is expected.
- **Discard draft and use latest** requires confirmation, loads the displayed
  latest values as a clean draft/base, and performs no PATCH.
- **Re-edit draft** preserves the base and draft, focuses the schema editor,
  and performs no request. The comparison remains visible.

No recovery action overwrites an analysis, canonical dataset, or saved model.
The workflow preserves A05 intake drafts and independent preview/profile reads.
Comparison requests have their own guard: newer saves, source activation,
active deletion, unmount, and A-to-B-to-A transitions invalidate obsolete reads.
A newer intake draft alone does not prevent reconciliation of the same active
dataset's known committed schema and is not cancelled by that reconciliation.

## Presentation and Verification

The installed `ui-ux-pro-max` skill was consulted using its local UX search for
`error recovery preserve input`. The existing dense schema table and button
styles are retained; recovery appears as an inline section, not a modal or a
new design system. Both Korean and English are provided. Semantic test hooks:
`data-schema-conflict`, `data-conflict-state`, and
`data-schema-conflict-action=apply|discard|edit|retry`. A staged draft has
`data-schema-staged=true`.

Pre-fix evidence: `.tmp/a07-schema-before.log`, three focused HookRunner tests
failed because PATCH omitted the base hash and a 409 did not fetch a comparison.
Pure helper, transport, Node HookRunner, and static-render tests cover immutable
bases, field-level overlays, repeated conflicts, explicit actions, invalid
identities, stale responses, and user-text preservation. Browser two-tab
verification and backend transaction tests are separate integration gates;
Node tests do not constitute evidence of those gates passing.

An additional pre-fix no-op regression run failed two tests
(`.tmp/a07-schema-noop-before.log`): a no-op incorrectly invoked the analysis
reset callback and restarted/cancelled pending auxiliary reads.
