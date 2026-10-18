# Report Center P0 Contract

Last updated: 2026-10-18

PLS now has a schema-1-specific renderer, not the OLS renderer. GPR includes
saved optimizer/bounds/convergence evidence. See `html_report_coverage_matrix.md`
for method-level support and remaining summary-only views. Unknown or malformed
core results cannot succeed as empty HTML. Existing reports are not rewritten.
Completed PLS point predictions may be downloaded separately as client JSON
snapshots; these are explicitly not managed Report Center artifacts.

## A11 Backend-Owned Report Coverage

- `GET /api/v1/analysis-runs/{analysis_id}/report-capability?locale=en|ko`
  is the only authority for generic HTML availability. The response binds the
  requested ID, locale, original result SHA-256, renderer/version, variant,
  `full`/`summary`/`unsupported` level and explicit section statuses/reasons.
  A method catalog `report_contract` describes registration, not proof that every
  historical result has all required sections. There is no frontend method allowlist.
- Current-result and restored-result REPORT actions both use the actual displayed
  export owner. Unknown, failed, mismatched and unsupported capability cannot create
  HTML. JSON remains available; unsupported results are not presented as complete
  user reports. Missing sections and stale status remain visible in text.
- Capability has an independent ID/locale/workspace-revision request lane. List
  filtering does not reload it or remount the selected action panel. Locale changes,
  source switches, mutation and unmount invalidate obsolete capability/HTML
  success, failure and finally handlers. StrictMode replay remains supported.
- HTML POST carries explicit `locale` and the capability's
  `expected_source_result_sha256`. Successful publication must match ID, locale and
  source hash. A source-change conflict refreshes capability, shows a recovery
  message and requires another explicit create action; it never retries POST
  automatically. Schema-4 HTML responses include report level, renderer version
  and rendered section IDs. Historical export metadata remains readable.
- `source_validation=stored_dependencies_only` is disclosed: verification does not
  reload original rows or rerun statistics. Section titles are backend-localized
  text, escaped by React; reason codes and user names are not machine-translated.
- Common Content-Disposition parsing prefers valid RFC 5987 UTF-8 `filename*`
  over `filename`, with safe fallback for malformed encoding. Path prefixes,
  controls/bidi formatting, Windows-invalid characters and device names are
  sanitized, while ordinary Unicode and private-use characters remain literal.
  Factorial downloads use the same helper after their existing byte/hash checks.
- The installed ui-ux-pro-max `error recovery retry` guidance was applied to
  adjacent retry/status feedback and progressive section disclosure. Existing
  typography, colors and data density are retained; no new dependencies or fonts.

Validation boundaries: deferred hook tests cover owner/locale/mutation ordering;
SSR tests cover localized full/summary/unsupported text and escaping. The Report
Center browser fixture covers real React interaction and downloads using mocked
synthetic HTTP. It does not substitute for backend saved-file/checksum/renderer
tests or the real-backend critical path.

## A10 Request Ownership and Recovery

- List filters/pagination and selected result/status have independent latest-request
  lanes. List refresh, method/status/stale filters and dataset changes do not reload
  the selected result or alter its URL. Explicit workspace mutation revalidates each
  affected lane once. Obsolete success, failure and finally handlers cannot publish.
- `currentDatasetOnly=true` with no active dataset blocks the list and issues no
  unfiltered HTTP request. The checkbox remains checked and can be explicitly
  cleared. A new dataset scope starts at page zero; changing an unused current
  dataset when this filter is off causes no request.
- A valid UUID `analysis_id` is recorded at selection intention, before the result
  request. Responses do not rewrite selection URLs. Query updates preserve other
  parameters, fragment and history state. Same-mount `popstate` and the existing
  app location event observe selection changes. Empty, malformed or duplicate IDs
  produce an explicit error without a result/status request or misleading old result.
- Result and status responses must match the requested analysis ID. Existing
  `GET /analysis-runs/{analysis_id}` supplies live stale metadata independently of
  list membership. Status failure is unknown, never fresh; a readable result remains
  available with an explicit warning and status-only retry. Result failures have
  a separate retry. Only current-owner `analysis_run_not_found` clears selection.
- The result panel stays mounted while filters change. Its stale warning comes
  from the independent status lane, not a missing list row. Deletion callbacks
  carry the actual deleted ID; deleting A cannot clear B. Unmount invalidates all
  owned callbacks, including deletion. StrictMode effect replay reissues a cancelled
  deep-link read rather than leaving a permanent loading state.
- Stable error/notice codes are rendered in the current locale, with explicit
  recovery actions and `role=alert`/`status`. User/transport exception text is not
  translated or echoed. The installed ui-ux-pro-max `error recovery retry` guidance
  informed these changes; existing dense colors, spacing and controls are retained.
- No API/schema/method version, stored report/result/model or numerical calculation
  changes. The new frontend status client uses an existing backend endpoint.

Evidence: `asyncHookState.test.ts` deferred-response regressions,
`reportCenterQuery.test.tsx` URL/EN-KO feedback checks, and
`tests/e2e/report_center_context.py` StrictMode browser transport fixture. The
fixture mocks HTTP with synthetic records and is not a backend/export-integrity test;
the existing full critical path still exercises real saved report/export APIs.

## A12 Managed Stored Sources

The existing generic analysis browser and its `analysis_id` deep links remain
unchanged. A second, explicit "Stored sources" view uses a typed six-kind source
union: `analysis_run`, `regression_prediction`, `doe_analysis`,
`doe_optimizer_result`, `lhs_design_revision`, and `bayesian_history_revision`.
Dedicated workflow IDs are never passed off as generic analysis IDs. The client
uses the complete returned immutable source reference and `source_ref_sha256`;
`open_target` is only a validated same-origin navigation link, never an identity
parser. History/recommendation attachments and response revisions retain their
own IDs and checksums.

- `GET /reports/sources` is paged and requires one source kind; the dedicated
  view defaults to `regression_prediction`. List kind/page changes preserve the
  exact selected source, capability, artifacts and action state.
- Capability, artifact listing, source selection and create/download/delete
  requests have independent guarded lanes. Source, locale, workspace revision
  and unmount invalidate obsolete callbacks. A completed obsolete export stays
  server-owned and discoverable but cannot replace a newer selection or trigger
  its browser download. A failed creation never automatically retries the POST.
- "View exact saved source" explicitly requests `POST /reports/source-snapshot`
  with that complete reference and locale. Its independently guarded lane checks
  source/hash/locale, rejects obsolete responses and never auto-loads on selection
  or filters. The returned original stored payload is escaped read-only JSON in
  an internally scrollable region, clearly not a complete HTML report. Filters
  retain it; source/locale/workspace changes invalidate it. The separate "Open
  workflow" link does not claim every workflow can restore an old exact revision.
- `POST /reports/capability` is authoritative for full/summary/unsupported
  coverage, section reasons, stale state and exact source reference. Unknown
  capability disables HTML without falsely promising a dedicated JSON endpoint.
  Creation binds `expected_source_ref_sha256`; returned descriptor identity and
  locale must match the request. The browser verifies HTML byte count and SHA-256
  before triggering a download, with the existing UTF-8 filename sanitizer.
- `/reports?report_id=<UUID>` restores the returned report descriptor and exact
  source. Invalid/duplicate IDs or source-kind parameters cause an explicit
  error without HTTP. A valid but deleted report yields a recoverable error and
  keeps the source catalog available. No raw source payload/hash enters the URL.
- Deleting a report is explicitly confirmed and sends its source plus artifact
  checksum. This removes the generated report, not its source result or model.
  The asset type is `managed_report`; normal owning-source retention rules still
  govern cascades. Existing generic export listings may also contain managed
  HTML and completed-prediction JSON, labelled distinctly.

### Completed PLS and GP Predictions

The point prediction form has a "Save completed prediction" checkbox **before**
execution, initially unchecked. `save_result` is captured with the submitted
rows, model ID and manifest checksum. Locale/draft edits do not submit a request;
changing the source resets this opt-in. The selected value is disabled while its
request owns the pending state. Only a matching successful response can expose
the optional server `saved_prediction` descriptor. Missing or mismatched saved
identity is an error, not a claimed save success.

This is separate from the existing local JSON snapshot download. The snapshot
retains the exact request/response and optional saved descriptor without fitting
or predicting again. A checkbox change after completion does not save the old
result. Completed prediction JSON is not described as an HTML report. Surface
preview requests remain unsaved unless their existing caller explicitly requests
otherwise; this change adds no automatic background prediction persistence.

The installed ui-ux-pro-max guidance for explicit confirmation and success
feedback was used within the existing dense workbench: compact source filters,
one stable detail section, progressive provenance/section disclosure, adjacent
retry controls and report-only deletion confirmation. No new visual framework,
chart library, remote font or dependency was introduced.

Validation is deliberately split: deferred hook and snapshot tests verify
ownership, source validation and opt-in capture; `tests/e2e/managed_reports.py`
uses real React/Chromium with **synthetic mocked HTTP** for six kinds, held
responses, deep links, downloads and EN/KO viewport checks. It does not establish
backend persistence/rendering correctness. Backend storage/export and live-app
integration tests must validate those separately.

## Original P0 Scope

`/reports` is the central discovery and export surface for persisted analysis results. It reuses
the existing checksum-validated analysis-run result and export APIs. It does not introduce a new
result renderer, reinterpret stored artifacts, or imply that every dedicated workflow has an HTML
report.

Selecting a stored run renders one stable result/export/delete action panel below
the list. Filtering a selected run out of the list does not remount the panel,
reset pending export/delete controls, or move focus. The selection is represented by the ID-only
`analysis_id` query parameter and is restored by exact result lookup after
reload. The selection controls have one stable location after the paged list,
independent of whether the selected row matches the active filters. Interactive
controls are never nested inside the selection buttons.

The selected panel distinguishes deleting one generated export artifact, which
preserves the analysis result, from deleting the stored analysis run. Stored-run
deletion reuses the checksum-bound analysis-run preflight and quarantine
contract and removes its owned result, row snapshot, and exports only when no
blocker exists.

The analysis Workbench shows a closed-by-default `저장된 분석 이력` summary.
Opening it fetches only the selected dataset/method's three most recent runs;
the collapsed state does not issue the full-history request. `전체 이력 관리`
opens `/reports?tab=history&dataset_version_id=...&method_id=...` with IDs only.

The Report Center `분석 이력` tab reuses the full existing history component,
including filters, paging, checksum-validated restore, same-method comparison,
deletion preflight, and irreversible deletion. The `보고서` tab retains report
discovery and export creation/download. No history or export capability was
removed from dedicated owning workflows.

## Generic analysis-run support

The list uses paged `GET /api/v1/analysis-runs` requests with explicit method, status, stale,
result-availability, and optional current-dataset filters. The default is `succeeded` plus
`result_available=true`. Selecting a run uses the stored-result endpoint, which validates the
persisted result checksum before any export action is enabled.

For a generic analysis run, Report Center supports:

- JSON result envelope export;
- method-defined long-form CSV export;
- escaped, self-contained static HTML when the selected result's backend
  capability permits it, with its declared full or summary coverage;
- existing export listing, checksum-validated download, and deletion preflight/deletion;
- visible stale status and method/dataset/version metadata.

Existing endpoints remain authoritative. Report Center must not duplicate HTML rendering or bypass
download `ETag`, `nosniff`, content type, checksum, CSV formula-injection, or path-redaction policy.
The loopback CORS policy exposes only `Content-Disposition` and `ETag` to the local frontend so
download names can retain their generated extension and checksum metadata remains readable. The
generated filename is ID-derived and contains no original filename or workspace path.

## Original P0 Dedicated Workflow Matrix

This table records the earlier P0 boundary. A12's managed-source API above
supersedes it for new managed exports; current support and coverage come from the
exact stored source's backend capability, not this historical table.

| Workflow | Stored result | CSV | HTML |
| --- | --- | --- | --- |
| Regression Predict | Dedicated workflow restore | Full prediction CSV in Predict | Not supported |
| Response Optimizer | Dedicated workflow restore | Not supported | Not supported |
| Factorial / General Full DOE | Dedicated design/analysis restore | Not a generic export | Managed analysis HTML and separate legacy design/response HTML in owning workflow |
| RSM | Dedicated workflow restore | Not supported | Not supported |
| Bayesian Optimization | Study/recommendation restore | Not supported | Not supported |

The table documents dedicated owning workflows; it is not a client-side generic
HTML allowlist. Unsupported formats show an explicit capability explanation. A
generic HTML fallback must not serialize arbitrary dedicated result bodies, raw predictor values,
run-level response values, filenames, or internal paths. HTML, PDF, and Word are distinct formats;
the UI must not label one as another.

## Accessibility and state

- The left navigation exposes `리포트` as a keyboard-operable button and `/reports` is reload-safe.
- Filters, list rows, paging, creation, download, and deletion have visible loading/error states.
- Format and stale state are communicated in text, not color alone.
- Latest-request guards prevent older list/result responses from replacing the current selection.
- Re-selecting the same exact managed source/hash preserves its pending detail requests,
  completed snapshot, and action state; it does not cancel them without restarting a lane.
- Empty lists and unavailable stored results are explicit, not successful empty reports.

## Security and privacy

- List responses contain metadata only. A12's explicit exact-source inspection can
  render the verified stored payload as escaped, read-only JSON; it never reads raw
  dataset files and is not represented as an HTML analysis report.
- Client errors show stable codes, never traceback, SQL, raw cells, filenames, or absolute paths.
- Existing backend HTML escaping and CSP remain mandatory.
- The page stores no raw data in browser storage and performs no external request.

## Follow-up boundary

The original dedicated HTML follow-up now uses A12's separate typed contracts,
redaction tests, restore/tamper tests, and E2E coverage. PDF/Word engines, multi-analysis report
editing, chart-image export, and arbitrary report HTML are outside P0.
