# Dataset Request Context (A05)

## Scope and acceptance

This frontend-only change isolates dataset intake, activation, schema saves, cell
corrections, previews and profiles. A later request must not apply an earlier
source's response, failure, loading completion, selection callback or URL update.
The last successfully loaded dataset remains committed until its replacement has
loaded successfully. Starting a file or paste draft does not clear that dataset.

No API, metadata, analysis-result or model schema changes are introduced. Dataset
parsing, statistical calculations, persisted artifacts and backend write semantics
are unchanged. This is not a server compare-and-swap or cross-tab write solution;
server-side schema-write concurrency remains a separate A07 concern.

## Request acceptance

`sourceContextGuard.ts` maintains an immutable, monotonic source-intent epoch.
Its token records the source identity when that intent begins; each request also
captures the actual committed version ID, schema hash and canonical artifact hash
when available. Acceptance requires the same guard and token identity, not just
equal version IDs. This rejects an obsolete A response after an A -> B -> A
transition.

`useDatasetWorkflow.ts` also maintains independent latest-request lanes:
activation, intake, confirmation, schema, cell, preview and profile. A response is
applicable only while the hook is mounted, the source epoch is current, and that
lane's request is current. Success, error and finally paths use the same check.
Unmount invalidates all lanes even when no initial dataset was restored.

Epoch changes follow explicit source-changing intent: selecting a file, editing or
submitting pasted data, changing intake options, requesting dataset activation,
publishing an accepted version, or deleting a relevant source. Deleting an
unrelated dataset refreshes the catalog without invalidating current work.

An obsolete server write may nevertheless have completed successfully. A late
parsing confirmation or cell correction can refresh the catalog and global version
inventory, but cannot activate its version or call source-bound reset/column
callbacks. No frontend cancellation is described as a server transaction rollback.

## Committed selection and restoration

Activation first fetches and validates the required version response. Only that
success commits the active version, session selection and dataset query parameter.
Preview and profile then run independently. Their failure does not erase a valid
version or a successful sibling response.

When replacement B fails, committed A and its location are retained, while the
failed B remains an explicit retry target. Initial restoration without a committed
version preserves its URL/session ID on transient failures. Only the stable
`dataset_version_not_found` response clears that initial persisted selection.
Malformed stored IDs are ignored rather than fetched or rewritten.

The mounted hook observes dataset query changes, including browser history
navigation. URL writes preserve unrelated query parameters, fragments and history
state. Failed or stale requests cannot publish a different version to that URL.

## Partial reads and recovery

Preview acceptance checks version ID, requested offset and page limit. Profile
acceptance checks version ID, schema hash and canonical hash when available.
Unexpected identities produce `dataset_response_context_mismatch`; they are never
displayed as successful data for the selected source.

Preview and profile errors have separate section-level retry controls. Changing a
draft invalidates in-flight reads for the retained active dataset; those reads are
marked `dataset_request_interrupted` and remain retryable rather than leaving an
empty, silently finished section. Retry reads only the committed version and does
not submit a new upload or analysis. A successful retry does not discard the intake
draft. Stale failures cannot replace current error or loading state.

A failed upload still owns the selected file draft. Replacing it requires the
existing discard confirmation. Cancelling that confirmation restores the prior
native FileList and retains its error; accepting it clears the old error and
invalidates late responses before selecting the new file. Browser recovery tests
must explicitly approve this one expected confirmation rather than relying on
Playwright's default dialog dismissal. The Linux full E2E failure at
`verify_csv_file_upload_and_error_recovery` was this missing test action, not an
old upload response overwriting an accepted new selection.

User-facing error text is localized static text plus a validated machine code.
Arbitrary exception messages, server prose, user data and raw cell values are not
rendered as workflow errors.

The seven workflow API wrappers (upload, paste, parsing confirmation, version
fetch, schema update, preview and profile) now preserve the existing typed
`ApiRequestError`: status, stable code, correlation ID and original backend
message remain separate. Rendering still uses only the validated code, not that
message. A route-level 404 remains `api_contract_mismatch`, distinct from a
confirmed `dataset_version_not_found`. Dataset catalog listing retains its
existing error contract; no backend response schema changed.

## Draft and navigation behavior

Schema submissions capture their draft revision. Accepted responses update the
committed schema, but edits made after submission remain unsaved drafts. Cell
correction callbacks return `null` when superseded; the editor then does not show a
false saved notice or switch datasets. Successful cell notices store version IDs
as data and localize their surrounding text at render time.

Schema metadata is an in-place server write, unlike immutable-version creation.
If a new intake intent invalidated a schema-save ticket but the same version is
still active, an acknowledged schema response can reconcile that retained version
only when its committed generation, latest schema-write sequence, version/dataset
IDs and original schema hash all still match. A newer schema save or an A -> B ->
A commit prevents that application. This updates the known server-acknowledged
metadata and calls `onSchemaChanged` so dependent analysis state is invalidated.
It preserves newer schema drafts, selected files, paste text and pending intake
requests. Only schema-dependent request lanes are cancelled; preview/profile
restart using the new committed metadata snapshot. No additional fetch, fit or
server write is performed during reconciliation.

This is the same last-observed server-commit meaning as a normal schema response;
it does not make simultaneous writes across tabs atomic or replace A07 CAS.

Paste submission captures its local revision. Its completion clears only that
exact revision, preserving newer text, including literal private-use characters.
No completed user-interpolated string is sent through a translation resolver.
The draft callback distinguishes user mutation from programmatic reset. A user
clearing the text is still a new intent and invalidates a pending paste; clearing
an acknowledged successful submission does not invalidate its staged upload.
`usePastedDatasetSubmission.ts` owns the panel's request guard and local busy
state. User edits also release that local busy state, allowing a newer submission
without waiting for the obsolete request to settle. Its late success/finally
cannot clear the newer submission's text or busy state.

The file picker keeps a snapshot of the accepted native selection. Rejecting a
replacement restores that selection, rather than leaving the browser displaying
file B while the upload handler still holds file A. In browsers the snapshot is a
separate `DataTransfer.files` list. Clearing committed intake also clears the
native input. No file content is logged or transformed for this synchronization.

Dataset replacement and navigation away from dataset preparation confirm dirty
schema, cell, paste and intake state. Rejecting the confirmation leaves draft,
source, URL and requests unchanged. Accepted navigation discards only transient
draft state and invalidates pending requests; it does not delete stored versions.
The browser's unload protection is used when drafts remain dirty.

Deletion uses only the actual `DatasetVersionDeleteResponse` identity and scope.
The current API has no deleted-version-ID array; no such array is inferred.
Explicit active-version deletion or matching dataset-root deletion clears active
state. The backend separately rejects deletion of referenced child versions.

## UI guidance

The installed `ui-ux-pro-max` skill was read, and its UX search for
`error recovery preserve input` recommended visible recovery actions and retry
controls instead of dead-end errors. This implementation reuses existing compact
error, selector and button styles. It does not introduce a design system, global
layout change or dependency.

## Verification evidence

Before implementation, the existing Node HookRunner reproduced nine failures:
draft selection cleared the committed dataset; obsolete upload/paste/confirmation
results published; old schema/cell writes switched the source; newer schema draft
edits were overwritten; profile failure lost a valid restore; and a late response
after unmount persisted selection. The targeted baseline exited 1 with 9 failed
and 44 skipped tests (`.tmp/a05-dataset-baseline-tests.log`). These are controlled
hook tests, not browser reproduction claims.

The pure source guard initially passed 6 tests. Further focused hook, SSR and
consumer checks cover independent retry, stale failure/finally, A-B-A identity,
dirty rejection, same-mount URL navigation, mismatched payload identity, related
and unrelated deletion, raw paste revision safety, transient initial restore and
interrupted-read recovery. Full-project and actual browser results are recorded
in the parent remediation validation record, separately from these controlled
tests. Logs and synthetic screenshots remain outside tracked source.

A subsequent transport-boundary test reproduced 8 failures and 1 pass before
the seven wrappers were migrated (`.tmp/a05-dataset-api-before.log`): the legacy
wrappers threw plain `Error(code)` and therefore lost typed error fields. The
earlier missing-version hook test used a typed mock and did not by itself prove
the real transport boundary. The dedicated API tests now cover that distinction.

A further same-active-schema regression reproduced the acknowledged server hash
remaining stale after a new intake draft invalidated its original request. Its
pre-fix run had 1 failure, 1 pass and 69 skipped tests
(`.tmp/a05-schema-reconcile-before.log`). The focused coverage distinguishes this
case from switching to B or returning to A, and checks that later unsaved schema
text plus an in-flight replacement upload both survive reconciliation.

The final focused run after typed API, same-active-schema, draft-intent and
submission-controller corrections passed 6 files / 101 tests (exit 0, 6.32 seconds;
`.tmp/a05-dataset-submission-focused.log`). Actual browser and full-project results
are recorded separately in the remediation validation record; they must not be
inferred from the controlled hook/transport tests.

Focused commands (Node 22 from the repository's ignored tool directory):

```powershell
npm --prefix frontend test -- --run src/api/datasets.test.ts src/asyncHookState.test.ts src/sourceContextGuard.test.ts src/datasetRequestErrors.test.tsx src/ActiveDatasetVersionSelector.test.tsx src/datasetCorrectionLhsUsability.test.tsx
```

## Limits

- Requests are invalidated for UI application; already sent server writes are not
  forcibly aborted or rolled back.
- No backend CAS or new cancellation endpoint is introduced.
- The frontend checks response identities already present in the API; it does not
  claim a schema hash exists in a preview DTO that has no such field.
- Invalid session IDs are ignored without destructive storage cleanup.
- This change does not redesign analysis-run cancellation or other independent
  domain workflows.
