# Pasted Data Grid Contract

Last updated: 2026-07-17

## Scope

This contract separates a browser-only staging preview from authoritative
dataset parsing and immutable dataset versions. The current implementation is
P0 and reuses `POST /api/v1/datasets/paste` without changing its request,
response, size limit, raw-byte preservation, or parsing-confirmation behavior.

## P0: View-Only Staging Preview

- The focusable paste surface reads only `clipboardData.getData("text/plain")`.
  Clipboard HTML is neither read nor rendered, and no Clipboard permission API
  is required.
- The exact clipboard string is held only in an in-memory ref and the fallback
  textarea DOM node. It is not kept in `localStorage`, `sessionStorage`, logs,
  telemetry, or URL state.
- The preview parser never becomes the submission source. Registration sends
  the original string, including CRLF/LF, quotes, embedded newlines, trailing
  tabs, and trailing empty cells, directly to the existing paste API.
- Successful registration clears the raw ref, textarea, preview cells, and
  selection. A failed request keeps the draft in the current page so the user
  can review or retry it. Reload never restores that raw draft.
- The grid is view-only. It starts at A1, displays spreadsheet column letters,
  row numbers, empty cells, structural gaps, ragged-row markers, and a selected
  cell inspector. Formula-like strings are rendered as text and never run.
- The first-row-as-header toggle affects staging presentation only. The server
  suggestion is shown after registration, and the parsing-confirmation panel is
  the final authoritative control.

## Parser And Rendering Limits

The named browser caps are:

- first 200 rows;
- first 100 columns;
- at most 20,000 materialized preview cells;
- at most 2,000,000 characters scanned for browser-side structure metadata.

If the scan cap is reached, row/column/empty/ragged counts are labeled as lower
bounds. The exact full string is still submitted within the backend's existing
upload-size limit. This bounded synchronous parser avoids materializing the
whole paste as DOM cells, but a Web Worker and chunked full-input scanner remain
future performance work for very large pastes.

Supported staging interpretation includes Excel TSV, CRLF/LF/CR, conservative
tab/comma/semicolon/pipe detection, interior and trailing empty cells, quoted
fields, escaped double quotes, and quoted embedded delimiters/newlines. An
unbalanced quote switches the display to raw mode with a warning. Server
parsing can legitimately differ and is always revalidated at confirmation.

## Canonical Preview

After parsing confirmation, canonical rows continue to come only from the
checksum-validated paged backend endpoint. The browser may request 10, 25, 50,
or 100 rows, jump to a bounded row offset, and inspect one selected value. It
does not load all canonical rows. Page changes reset the selected-cell state.
Missing values and empty strings have separate visible labels.

## Security And Privacy

- No `dangerouslySetInnerHTML`, formula engine, arbitrary code, or clipboard
  HTML path exists.
- Preview strings are React text nodes. Formula prefixes `=`, `+`, `-`, and `@`
  are not evaluated.
- Raw pasted content is not written to browser storage or application logs.
- Client errors retain stable codes and do not include raw cells, original
  content, internal paths, or tracebacks.
- The backend remains responsible for final size, encoding, delimiter, row,
  and canonical artifact validation.

## P1: Editable Registration Staging

P1 is not implemented. A future reviewed slice must add all of the following
as one explicit contract:

- editable dirty state and accessible undo/redo;
- insert/delete row and column plus clear-cell operations;
- deterministic final submitted-text serialization;
- separate SHA-256 values for the original clipboard string and submitted
  edited string;
- an edit summary with affected coordinates and counts;
- confirmation before discarding dirty edits;
- regression tests for quotes, newlines, trailing empties, formula-injection
  text, and exact submitted bytes.

P1 must not claim that edited staging text is the original clipboard source.

## P2: Confirmed Dataset Cell Correction

P2 is not implemented. Confirmed versions can never be edited in place. A cell
correction must create a new immutable dataset version with:

- parent version ID;
- deterministic transformation record and creation timestamp;
- edited cell coordinates plus before/after hashes without logging raw values;
- new canonical artifact and schema/dependency hashes;
- stale propagation for analyses that depend on the prior version where the
  product contract requires it;
- restore access to the unchanged old version;
- migration, tamper, crash-recovery, and lineage tests.

## P0 Acceptance Evidence

P0 tests must cover parser fixtures for TSV/CRLF/LF/Korean text, empty/trailing
cells, ragged rows, quoted delimiters/newlines, escaped quotes, formula-like
text, truncation, empty input, and unbalanced quotes. Frontend tests must cover
safe escaped rendering and exact original-string API submission. Chromium E2E
must dispatch a real `text/plain` paste event, inspect cells before
registration, exercise keyboard selection, prove failure retains the current
draft, prove reload does not restore it, confirm parsing, inspect canonical
rows, change page size, and retain all existing upload/analysis flows.
