# Current Analysis Request Contract

## Scope

The generic analysis actions in `App.tsx` share `useCurrentAnalysisExecution`.
Each action retains its method-specific validation and request options. This is
execution ownership and presentation protection, not a statistical method change.
Dedicated DOE/BO workflows and completed prediction snapshots keep their existing
independent contracts.

## Ownership

An execution captures a cloned request, dataset version, schema hash, method ID
and version, workspace context, monotonic input epoch, and request token.
Accepted dataset activation, actual schema-save intent, filters, model inputs,
method navigation, historical restore, and source deletion invalidate obsolete
publication synchronously. A source-key comparison also protects externally
changed context. Returning A -> B -> A cannot revive the original request.

Success, error, and finally are all guarded. Invalidating browser ownership does
not cancel server computation or delete a saved run. Re-running the same input
may retain the previous accepted result while waiting; editing input clears the
current result. An invalidated current result cannot reveal an old restored
result through a null-coalescing fallback.

Accepted source-switch or parsing intent invalidates pending publication but
retains the last completed current/restored result while the old dataset is
still committed. A failed switch therefore does not erase completed work.
After a failed switch, the dataset selector shows the committed active version,
not the retained retry target. Initial restore with no committed version keeps
its requested identity, and retry still uses the failed target.
Actual dataset/schema publication clears the old current result; ordinary model
configuration edits retain their explicit clear-result policy.

Staged uploads/pasted text, rejected replacement confirmations, preview paging,
locale, viewport resize, plot selections, candidate result tabs, loading pages,
model labels, and prediction input/save controls are not model-input changes.
PCA/PLS/GPR, Two Variances, regularization, graphical-summary confidence, ANOVA,
Mann-Whitney, and two-sample equivalence explicitly notify App when local run
inputs change. Saved-result hydration is not treated as a user edit.

The quick-graph lane remains independent. Its cache key includes dataset version,
schema hash, column, method version, and filter snapshot. Gage R&R preflight has
its own guarded busy state and cannot finish a main analysis's busy state.

## Completion Verification

Before publication, the immutable completion envelope and provenance must match
the captured dataset, method/version, and schema hash. New current executions do
not infer omitted provenance. The existing status endpoint is then read under
the same request token. Its owner must match and it must report `succeeded`,
`result_available=true`, and `stale=false`.

This second check catches cross-tab schema commits even when the result's
immutable source hash still matches the client's originally captured hash.
It is a point-in-time check, not a continuous cross-tab subscription.

`analysis_completion_source_changed` prevents applying an obsolete result;
successfully saved runs remain available through explicit history. The related
server codes `analysis_completion_source_missing` and
`analysis_completion_dependency_invalid` use the same safe recovery guidance.
`analysis_completion_verification_failed` offers an explicit status-only retry.
Retry never issues another analysis POST, refit, or prediction.

The create/status transport retains `ApiRequestError` code, HTTP status,
correlation ID, and backend message. The hook retains the original cause;
display uses trusted code-based guidance and a correlation ID, not raw exception
text. Unknown exceptions do not become user-facing error codes.

Historical restore is explicitly separate and still reads legacy envelopes.
Neither validation nor restore rewrites stored result/model artifacts.
Restore intent only cancels pending publication. A matching saved result must be
read successfully before the previous current result is retired. Failed restore
preserves the last completed current or historical result, and a subsequent
export-list failure cannot undo a successful result restore.
The restore lane exposes pending-only cancellation for accepted navigation/source
intent. Returning to the same route/source does not revive an old history read.
Successful restore navigation may cancel that lane after commit, but cannot
discard its accepted payload or suppress its independently guarded export refresh.

Dataset deletion invalidation belongs to the dataset workflow's exact active
version/root ownership check. Removing an unrelated dataset refreshes catalog
and asset state without clearing the current analysis or its inputs.

## Validation Boundary

Deferred Node hook tests cover late create/status success, catch/finally,
configuration and source changes, ABA, status-only retry, mismatched provenance,
stale status, unmount, and StrictMode effect replay. Panel tests verify explicit
local input notifications without triggering execution on mounting/rerendering.
An App wiring test prevents bypassing the shared main-run boundary.

Real-browser response-delay tests and backend publication-barrier tests verify
different race boundaries. A delayed HTTP response alone does not establish
atomic storage publication. Numerical reference tests remain unchanged.

UI guidance: installed ui-ux-pro-max's targeted Error Recovery and accessible
Error Messages guidance is applied through the existing dense workbench notice
and button styles, preserved focus/layout, explicit verification retry, and
Korean/English code-based messages. No design system or runtime dependency was
added.
