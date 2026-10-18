# API and Translation Boundary (A04)

## Contract

`fetchApi` is transport only. It adds `Accept-Language` while retaining Request
headers, forwards BodyInit unchanged and returns the original Response. It never
resolves text tokens, parses/reserializes request JSON or replaces `response.json`.
The response/result remains the stored numeric and textual source of truth.

`ApiRequestError` retains status, code, correlation ID and original backend message.
UI error state retains codes; presentation uses the current locale. Explicit
`ApiNoticeText` accepts a warning/issue DTO, not arbitrary result objects. Known
code or exact static-message translations are presentation only. Unknown messages
and their codes remain visible as escaped text, rather than a generic warning.

## Compiler and Static Catalogs

The compiler translates static JSX text, declared display attributes and narrowly
declared presentation collections (`DoeSettingsTable.fields` labels and
`DefinitionRows.rows` labels). It emits `t(key)` calls, not private-use tokens.
It does not translate request objects, keys, enum values, regular expressions,
comparisons, arbitrary function arguments or input values. React's JSX runtime is
a pass-through: user text containing U+E000/U+E001 is ordinary data.

Existing trusted system catalogs remain static. Their getters/renderers translate
explicit label/description fields at display time, preserving IDs, paths, options,
regex and original catalog objects. `translateSystemText` is only for these
trusted literals/catalogs. Never pass a user name, cell, group, response payload,
or a completed string interpolating user data to it. Compose translated static
fragments with unchanged dynamic values instead.

System-created defaults such as the initial LHS design name call `t` before being
placed in input state and before JSON serialization. Once edited, an input is
user data and locale changes do not rewrite it. No saved artifact is rewritten.

## Evidence and Remaining Verification

The pre-fix transport regression had five failures: both locale request bodies
changed private-use user data, Request headers were lost, the original backend
message was replaced, and rendered user text was interpreted as a token. After
the transport/runtime fix all six transport tests passed. The pre-fix compiler
test also reproduced changes to request object values and comparison operands.

Narrow transport/compiler/locale tests subsequently passed (16 tests before the
additional collection-label test). Explicit warning rendering passed seven SSR
tests and 35 tests with related views. Static catalog getter tests are separate
from production browser tests: no full browser parity claim is made yet.

Actual Windows Chromium validation used `scripts/e2e.ps1 -BackendPort 8034
-FrontendPort 5234 -ApiTranslationOnly -DiagnosticsRoot
.tmp/e2e-remediation-a04-transport -KeepWorkspace` (exit 0). All four synthetic
cases (paste/upload, en/ko) passed: JSON bytes/decoded request, Accept-Language,
file SHA/size, original headers, stored cells and schema hash after locale changes.
Each child context retains stage, trace and `boundary-evidence.json`. Raw source
SHA for the shared CSV fixture is
`f781fc8e6f4dcc8e0b645939577895f654212222ab34f57f44ccc9017489f9df`.
Existing backend display-name sanitation removes nonprintable characters; this
is distinct from original_name/raw cells, which are preserved exactly. A04 does
not change that pre-existing sanitation policy.

First full frontend run: 480 passed, 1 failed (health test compared a Headers
instance to a plain object). The assertion now inspects actual header values and
absence of Cache-Control. Typecheck separately found an invalid test-fixture role;
the fixture now uses the real dataset role enum, rather than a type assertion.
These failures are not omitted from the record.

The first full A04 browser run passed upload, parsing, schema, chart navigation,
report creation/download, saved-result restoration and stale-schema checks, then
failed to find the Korean manual-prediction input label `1행 afucose`: the migration
had inserted a space (`1 행 afucose`). Its value was still `1`. Parameterized row
labels restore the original Korean accessibility contract and preserve predictor
names without interpreting tokens; English uses `Row {row}: {predictor}`.

A subsequent unit run during concurrent work is not a frozen A04 acceptance run:
it included A05's deliberately failing, pre-fix race tests. An isolated source
checkpoint is used for the next integrated A04 run. No timeout was increased to
hide the two lazy-import timeouts observed under concurrent local checks.
That run finished with 486 passing tests and exactly the nine expected A05
failures. The four final transport/compiler/panel files passed 24 tests separately.
Production build (including strict TypeScript) passed; lint had zero errors and
nine pre-existing Fast Refresh warnings. The staged A04 checkpoint excludes the
A05 test/guard changes. Review also caught asset-deletion prose frozen in state;
it now stores a typed notice/count snapshot and renders in the current locale
(six focused deletion/error tests passed, no delete request or hash changes).

Required final checks: production-build en/ko rendering, full-suite rerun and
integration with A03 dependencies. A04 remains in progress until those checks are
recorded in `end_to_end_remediation.md`.
