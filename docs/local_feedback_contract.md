# Local Feedback Contract

The top-bar feedback dialog is a local convenience feature, not a crash reporter
or a claim that previous failures have been fixed. It does not contact GitHub,
email, telemetry, or any feedback endpoint. No new backend API or metadata table
is introduced. Opening it and copying/downloading its preview remain possible
after the app has loaded and the server becomes unreachable. The same entry is
available on the initial runtime checking/blocked page. When no backend identity
has been received, its versions remain null; a valid frontend build identity may
still be recorded. Startup failure does not enable otherwise blocked operations.

## Explicit Boundaries

`supportDiagnostics.ts` constructs a new automatic-diagnostics object. Its only
fields are schema version, capture time, validated application/build/API/metadata
versions, locale, viewport dimensions, current catalog-validated method ID,
last observed validated error code/correlation UUID, and last observed server
connection status. Unknown values are null or `unknown`, not inferred from URLs.

The connection value records the last API observation, not continuous monitoring.
The last error may precede the current method selection. Opening the dialog does
not check the server or reload results. Capture time and viewport describe dialog
opening; changing window size does not rebuild or mutate the captured diagnostic.

Error observations use fields already parsed by `apiRequestError`; they do not
read another response body, raw messages, console output, stack traces, headers,
URL/query strings, or request bodies. `fetchApi` network failure records only the
fixed code `api_unreachable`. Abort exceptions retain their existing behavior.
There is one bounded in-memory observation, no localStorage, disk log, or history.

Validation rules are deliberately narrow: lower-case machine error codes of at
most 80 ASCII characters with underscore-separated segments, canonical
lower-case UUID correlation IDs with a valid version/variant, semantic numeric
application versions, 40-hex Git commits or archive SHA-256 identities, positive
bounded integer schema/viewport values, and method-ID syntax plus membership in
the loaded backend catalog. Unknown formats are omitted rather than truncated.

Raw cells, column/group/file names, paths, model coefficients, prediction inputs,
user IDs, internal IP addresses, full URLs, screenshots, email, and authentication
information are never automatic fields. No blacklist-based whole-object export
or recursive result serialization is used.

## User-Controlled Export

The separate `user_feedback` section contains only the five visible fields:
problem type, reproduction, expected behavior, actual behavior, and repeatability.
Free text is intentionally preserved, including Unicode and special characters.
It can contain sensitive information; the dialog warns the author before export.
The three free-text controls allow at most 4,000 characters each. Nothing is
silently obtained from a dataset or result to fill these fields.

The complete JSON document is always available in a read-only selectable preview.
Copy, JSON download, and plain-text download export that same reviewed text only
after an explicit action. Clipboard absence/rejection exposes manual selection;
raw clipboard/download exceptions are never displayed. Closing discards the
dialog draft. Native modal semantics constrain focus; Escape/close returns focus
to the opener. Existing tokens and Lucide icons are reused without a redesign.

## Verification

Pure tests cover strict automatic allowlisting, malformed metadata, raw-message
non-observation, one-body-read transport preservation, fixed network errors,
bounded last-observation state, user-text preservation and clipboard fallbacks.
SSR tests cover Korean/English labels and the complete preview. The dedicated
`tests/e2e/pilot_feedback.py` targets the actual source or built app in both locales,
offline operation, clipboard absence/rejection, exact JSON/text downloads,
special-character preservation, modal keyboard focus, and 1440/390px layouts.
Execution results must be reported separately; the presence of this scenario is
not evidence that it was run.
