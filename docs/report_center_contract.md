# Report Center P0 Contract

Last updated: 2026-07-23

## Purpose

`/reports` is the central discovery and export surface for persisted analysis results. It reuses
the existing checksum-validated analysis-run result and export APIs. It does not introduce a new
result renderer, reinterpret stored artifacts, or imply that every dedicated workflow has an HTML
report.

Selecting a stored run renders its result/export/delete action panel immediately
after that list item. The selection is represented by the ID-only
`analysis_id` query parameter and is restored by exact result lookup after
reload. Long lists and pagination no longer place selected controls at the end
of the page. The selection button and inline action panel are siblings, so
interactive controls are never nested.

The inline panel distinguishes deleting one generated export artifact, which
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
- escaped, self-contained static HTML report;
- existing export listing, checksum-validated download, and deletion preflight/deletion;
- visible stale status and method/dataset/version metadata.

Existing endpoints remain authoritative. Report Center must not duplicate HTML rendering or bypass
download `ETag`, `nosniff`, content type, checksum, CSV formula-injection, or path-redaction policy.
The loopback CORS policy exposes only `Content-Disposition` and `ETag` to the local frontend so
download names can retain their generated extension and checksum metadata remains readable. The
generated filename is ID-derived and contains no original filename or workspace path.

## Dedicated workflow capability matrix

| Workflow | Stored result | CSV | HTML |
| --- | --- | --- | --- |
| Regression Predict | Dedicated workflow restore | Full prediction CSV in Predict | Not supported |
| Response Optimizer | Dedicated workflow restore | Not supported | Not supported |
| Factorial DOE | Dedicated design/analysis restore | Not a generic export | Design HTML in Factorial workflow |
| RSM | Dedicated workflow restore | Not supported | Not supported |
| Bayesian Optimization | Study/recommendation restore | Not supported | Not supported |

Unsupported formats are rendered as `현재 지원되지 않음` with a link to the owning workflow. A
generic HTML fallback must not serialize arbitrary dedicated result bodies, raw predictor values,
run-level response values, filenames, or internal paths. HTML, PDF, and Word are distinct formats;
the UI must not label one as another.

## Accessibility and state

- The left navigation exposes `리포트` as a keyboard-operable button and `/reports` is reload-safe.
- Filters, list rows, paging, creation, download, and deletion have visible loading/error states.
- Format and stale state are communicated in text, not color alone.
- Latest-request guards prevent older list/result responses from replacing the current selection.
- Empty lists and unavailable stored results are explicit, not successful empty reports.

## Security and privacy

- List responses contain metadata only; the page never renders the selected raw result body.
- Client errors show stable codes, never traceback, SQL, raw cells, filenames, or absolute paths.
- Existing backend HTML escaping and CSP remain mandatory.
- The page stores no raw data in browser storage and performs no external request.

## Follow-up boundary

Predict, Response Optimizer, RSM, and Bayesian HTML reports require separate typed contracts,
redaction tests, restore/tamper tests, and E2E coverage. PDF/Word engines, multi-analysis report
editing, chart-image export, and arbitrary report HTML are outside P0.
