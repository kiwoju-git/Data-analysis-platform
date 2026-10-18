# End-to-End Remediation

## Baseline and Scope

- BASE_SHA / initial local HEAD / initial origin/main:
  `f736db03fb61a3177c5a85cb0a422fbe0238a547` (fetched 2026-10-18).
- Working branch: `feat/end-to-end-reliability-remediation`.
- Existing untracked `examples/image2.png` is user-owned and is not staged.
- `data_prd.md` is absent. AGENTS.md, the addendum, implementation guide,
  task list and current method/runtime contracts govern this work.
- No existing dataset, workspace, result or model is migrated or rewritten by
  these display/state changes. All browser fixtures use an isolated workspace.
- Runtime at baseline: API 22, metadata 20. Statistical method versions are not
  incremented for display-only fixes. Schema CAS will require a coordinated API
  increment; a metadata increment requires an actual additive migration.

## Acceptance and Risks

Work proceeds A01 through A15, with narrow checks before integrated checks.
Completion requires actual state/API/file evidence, not only CSS or dispatch
registration tests. Main and release publication remain gated on validation.

- Statistical: preserve stored values, units, uncertainty meaning and reference
  fixtures; report rendering cannot refit or read source rows.
- Privacy: diagnostics contain synthetic fixtures only; no workspace, uploads,
  credentials or generated model files are committed.
- Compatibility: keep Windows 3.10, Linux 3.12 and 3.11 compatibility, LAN/local
  options, immutable artifacts and safe JSON/NPZ readers.
- Concurrency: stale success, failure and finally callbacks must all be guarded;
  schema compare-and-swap and exclusive workspace leases solve different races.
- Performance: enforce streaming upload limits, preserve CPU/time budgets and
  avoid extra result flattening or per-item catalog queries.

## Status Ledger

Allowed evidence statuses: `source_confirmed`, `reproduced`, `fixed`, `verified`,
`intentional_limitation`, `blocked`. A dash means not yet investigated, not passed.

| ID | Area | Status | Evidence / Remaining Work |
|---|---|---|---|
| A01 | Windows E2E readiness/diagnostics | fixed | Child diagnostics, explicit ready gates and exact synthetic version selection implemented; focused Windows browser run passed. Original CI cause remains unproven; Linux/CI verification pending. |
| A02 | Locale initialization | fixed | Getter SecurityError reproduced in a new regression test before the fix; safe getter, in-memory switching, startup render/import boundary added. Independent of the unresolved A01 CI cause. |
| A03 | Dependencies/uploads | source_confirmed | Current Starlette advisories and fresh npm audits inspected; upgrade/lock and upload integration not yet complete. |
| A04 | Transport/i18n | - | Pending request/response integrity tests. |
| A05 | Dataset context | - | Pending deferred-response reproduction. |
| A06 | GPR direct prediction | - | Pending snapshot/identity tests. |
| A07 | Schema CAS | - | Pending transaction/API implementation. |
| A08 | Workspace/backup | - | Pending lease and archive validation. |
| A09 | Chart formatters | - | Pending display-contract tests. |
| A10 | Report Center | - | Pending independent query-lane tests. |
| A11 | Generic reports | - | Pending method/schema/section parity. |
| A12 | Dedicated reports | - | After A01-A11; requires exact revision/hash owners. |
| A13 | Execution capabilities | - | Pending cancellation CAS and grouped counts. |
| A14 | Capability documentation | - | Pending generated registry/handler/report matrix. |
| A15 | Release installation identity | - | Pending marker/package identity validation. |

## A01 Evidence

Official CI log inspected: [Windows E2E failure](https://github.com/kiwoju-git/Data-analysis-platform/actions/runs/38832233414/job/116764063103).
The assertion failed at 2026-10-16 01:39:50 UTC. The reported parent URL was a
Bayesian analysis page; `verify_refined_ui` owns another context/page. Its
`context.close()` was on the success path only. `networkidle` was followed by
`html.lang` without first checking mount/runtime/route readiness. Dataset selection
used option index 1. These are source-confirmed defects; they do not prove why
that particular child document was empty.

Read-only sub-agent review identified two weaknesses in the first remediation:
diagnostic cleanup could mask the original failure, and the route title existed
before the method catalog loaded. Both were corrected. Five diagnostic unit
tests cover setup/capture/cleanup failures; the browser catalog-pending case
holds the API response and requires the actual domain landing, not just a title.
The second source review found no further blocking issue; it was not a test run.

## UI Guidance

Installed skill inspected: `ui-ux-pro-max/SKILL.md`. Targeted UX query:
`error recovery loading feedback accessible status`. Applied direction: preserve
the dense workbench, provide explicit recovery, distinguish loading/error/ready,
and keep keyboard focus and accessible feedback. No new design system or charts.

## Validation Ledger

Local environment: Windows 10 Home build 19045, CPython 3.10.11, Node 22.23.2.
This is not a physical Windows 11 or Linux execution claim.

| Command | Stage | Result |
|---|---|---|
| `npm --prefix frontend test -- --run src/i18n/localization.test.tsx src/runtimeCompatibility.test.ts` (Node 22.23.2) | Baseline | 2 files / 9 tests passed |
| `.venv\Scripts\python.exe tests/e2e/critical_path.py --backend-port 8031 --frontend-port 5231 --diagnostics-root .tmp/e2e-remediation-baseline --keep-workspace` | Baseline attempt | Invalid whole-suite evidence: after refined UI finished, a late import read edited E2E source. No app source was changed during the run, but the late-import failure was introduced by the concurrent test-file edits. A detached BASE_SHA worktree is used for the corrected baseline. |
| Same Python runner from detached BASE_SHA worktree, ports 8032/5232, diagnostics `.tmp/e2e-remediation-baseline-fixed-source` | Corrected baseline | Full critical path passed, including refined UI and Two Variances. |
| `npm --prefix frontend test -- --run src/i18n/localization.test.tsx` | New regression, before fix | 1 failed / 6 passed; localStorage getter SecurityError escaped render. |
| `npm --prefix frontend test -- --run src/i18n/localization.test.tsx src/ApplicationBoundary.test.tsx src/runtimeCompatibility.test.ts` | A01/A02 | 3 files / 13 tests passed. |
| `npm --prefix frontend run typecheck` | A01/A02 | Passed. |
| `node scripts/check_frontend_localization.mjs` | A01/A02 | Passed: 2934 source strings / 3940 keys. |
| `powershell -ExecutionPolicy Bypass -File scripts/e2e.ps1 -BackendPort 8031 -FrontendPort 5231 -RefinedUiOnly -DiagnosticsRoot .tmp/e2e-remediation-focused-1 -KeepWorkspace` | A01/A02 | Startup scenarios passed; fixture creation then failed with dev_origin_not_allowed because the test API client omitted Origin. Fixed the fixture's same-origin header, not the LAN guard. Rerun pending. |
| Same focused command with `-DiagnosticsRoot .tmp/e2e-remediation-focused-2` | A01/A02 | Passed, including startup scenarios and both locales/four viewports; subsequent boundary extraction/diagnostic metadata refinements still require the final whole-suite run. |
| `npm --prefix frontend test -- --run` | A01/A02 | 56 files / 401 tests passed. |
| `npm --prefix frontend run build` | A01/A02 | Passed; existing large-chunk warning retained. |
| `npm --prefix frontend run lint` | A01/A02 | No errors; 9 existing refresh warnings, plus 1 new entry-point warning subsequently removed by extracting ApplicationContent. Targeted ESLint then passed without warnings. |
| `.venv\Scripts\python.exe -m pytest backend/tests/unit/test_openapi_frontend_contract.py backend/tests/unit/test_dev_startup_contract.py` | A01/A02 first run | 226 passed / 1 failed: new E2E stage names missing in the coverage document. Document synchronized; focused failed test rerun passed. |
| Same backend command after document synchronization | A01/A02 rerun | 227 passed. |
| `powershell -ExecutionPolicy Bypass -File scripts/check.ps1` | A01/A02 integrated | In progress; `.tmp/remediation-a01-a02-check.log`. |
| `.venv\Scripts\python.exe -m pytest backend/tests/unit/test_e2e_diagnostics.py -q` | A01 review fixes | 5 passed. |
| `powershell -ExecutionPolicy Bypass -File scripts/e2e.ps1 -BackendPort 8031 -FrontendPort 5231 -DiagnosticsRoot .tmp/e2e-remediation-a01-final -KeepWorkspace` | A01/A02 final local E2E | In progress; `.tmp/remediation-a01-e2e-final.log`. |
| `npm --prefix frontend audit --omit=dev --json` | A03 baseline | Exit 0; no reported runtime advisories at lookup time. |
| `npm --prefix frontend audit --json` | A03 baseline | Exit 1; 14 affected package entries (12 high, 2 moderate), including indirect impact. Not 14 independent vulnerabilities. |

UI comparison evidence stays outside Git under `.tmp/e2e-remediation-focused-2`:
startup error/recovery images and refined-ui route images; unchanged source images
are under `.tmp/e2e-remediation-baseline/refined-ui`. The latter is only partial
baseline evidence, as explained above. The root error screenshot was inspected:
existing workbench tokens, readable recovery text, no raw exception/stack.

No Linux checks, new CI, release publication or main push has completed for this
remediation. Historical successes are not validation evidence for these changes.
