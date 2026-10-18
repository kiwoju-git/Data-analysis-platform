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
| A01 | Windows E2E readiness/diagnostics | verified | Child diagnostics, explicit ready gates and exact synthetic version selection passed local focused and hosted Windows/Linux full E2E. Original CI cause remains unproven. |
| A02 | Locale initialization | reproduced / verified | Getter SecurityError reproduced before the fix; safe getter, in-memory switching and startup boundary passed both platforms. Independent of the unresolved original A01 cause. |
| A03 | Dependencies/uploads | reproduced / verified | Native security locks, streaming/multipart limits, worker ownership and visible intake limits passed full local checks and all native CI jobs at 1213457. See dependency_upload_security.md. |
| A04 | Transport/i18n | reproduced / fixed (integration rerun pending) | Request bytes and response objects remain untouched; explicit display boundaries replace compiler tokens. Frozen Windows full browser/frontend checks passed. Integrated CI exposed a missing documentation step marker; corrected locally, native CI rerun pending. |
| A05 | Dataset context | reproduced / fixed (native integration pending) | 101 focused tests and all 16 real-server en/ko browser scenarios passed, including same-active schema, native file-cancel and replacement paste ownership. Whole native checkpoint CI remains required. |
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
| Same focused command with `-DiagnosticsRoot .tmp/e2e-remediation-focused-3` | A01 review-fix rerun | Passed: blocked storage, held/failed App chunk, initial render failure, pending runtime/catalog, child diagnostic capture, exact dataset selection, both locales and four viewports. |
| `npm --prefix frontend test -- --run` | A01/A02 | 56 files / 401 tests passed. |
| `npm --prefix frontend run build` | A01/A02 | Passed; existing large-chunk warning retained. |
| `npm --prefix frontend run lint` | A01/A02 | No errors; 9 existing refresh warnings, plus 1 new entry-point warning subsequently removed by extracting ApplicationContent. Targeted ESLint then passed without warnings. |
| `.venv\Scripts\python.exe -m pytest backend/tests/unit/test_openapi_frontend_contract.py backend/tests/unit/test_dev_startup_contract.py` | A01/A02 first run | 226 passed / 1 failed: new E2E stage names missing in the coverage document. Document synchronized; focused failed test rerun passed. |
| Same backend command after document synchronization | A01/A02 rerun | 227 passed. |
| `powershell -ExecutionPolicy Bypass -File scripts/check.ps1` | A01/A02 integrated | Exit 0: backend 1371 passed / 2 skipped; frontend 401 passed; typecheck/build/localization passed; lint 0 errors / 9 existing warnings. New diagnostic tests separately run. `.tmp/remediation-a01-a02-check.log`. |
| `.venv\Scripts\python.exe -m pytest backend/tests/unit/test_e2e_diagnostics.py -q` | A01 review fixes | 5 passed. |
| `powershell -ExecutionPolicy Bypass -File scripts/e2e.ps1 -BackendPort 8031 -FrontendPort 5231 -DiagnosticsRoot .tmp/e2e-remediation-a01-final -KeepWorkspace` | A01/A02 local E2E | Failed in the new catalog-pending negative test: readiness correctly rejected the missing landing, but the test assumed Playwright's error text included the attribute name. It includes the locator/expected value instead. Corrected the assertion and always release held requests; no product timeout increase. Full suite is not counted as passed. |
| Focused E2E command with `-RefinedUiOnly -DiagnosticsRoot .tmp/e2e-remediation-focused-3` | A01/A02 corrected negative test | Passed, including pending catalog, slow/failed chunk, storage cases, both locales and viewport checks. |
| `npm test -- --run` from isolated A03 frontend | A03 | Vitest 4.1.12: 57 files / 404 tests passed. |
| `powershell -ExecutionPolicy Bypass -File scripts/e2e.ps1 -BackendPort 8033 -FrontendPort 5233 -DiagnosticsRoot ../e2e-remediation-a03 -KeepWorkspace` from isolated A03 worktree | A03 | Exit 0, full critical path passed including refined UI/intake policy, startup readiness and Two Variances. |
| `npm --prefix frontend audit --omit=dev --json` | A03 baseline | Exit 0; no reported runtime advisories at lookup time. |
| `npm --prefix frontend audit --json` | A03 baseline | Exit 1; 14 affected package entries (12 high, 2 moderate), including indirect impact. Not 14 independent vulnerabilities. |

UI comparison evidence stays outside Git under `.tmp/e2e-remediation-focused-2`:
startup error/recovery images and refined-ui route images; unchanged source images
are under `.tmp/e2e-remediation-baseline/refined-ui`. The latter is only partial
baseline evidence, as explained above. The root error screenshot was inspected:
existing workbench tokens, readable recovery text, no raw exception/stack.

A01/A02 checkpoint `456695365f493cbb2572236b0270c6a68d565500` was pushed to
the feature branch, not main. [Checkpoint CI](https://github.com/kiwoju-git/Data-analysis-platform/actions/runs/39087043940)
reproduced the negative-test assertion on Linux. Corrected in `3a65b68`;
[run 39087911267](https://github.com/kiwoju-git/Data-analysis-platform/actions/runs/39087911267)
completed successfully: Windows full checks, Windows E2E, Linux full checks/E2E,
Python 3.11 checks and Linux archive/offline smoke. The archive is a CI artifact,
not a published Release. This run predates A03 dependency/upload changes and
does not validate them. A03 is isolated in its own worktree for verification.
No release publication or main push has completed for this remediation.
Historical successes are not validation evidence for these changes.

## A03/A04 Integration Checkpoint

A04 transport/display checkpoint: `e7f2f77`. A03 security and native-venv fixes
were integrated as `9f295a5` and `d036d8c`, preserving both sets of translation
keys. The feature branch was pushed; main and Release were not changed.

Native A03 run `39092099520`, source `1213457`, passed Linux 3.12 full checks
(1402 passed, 11 skipped), Python 3.11 checks (1402 passed, 11 skipped), all five
Python security profiles and npm runtime/all audits. The Linux archive job also
passed. Hosted Windows passed 1411 tests with two skips and its full E2E passed.
The local A03 full check exited zero (1410 passed / three skipped, frontend 404
passed, typecheck/build/localization/lint passed). Different privilege-dependent
skips are reported separately, not combined into one platform total.
This is A03 evidence, not validation of the integrated A04 source.

A04's new browser transport suite passed all four en/ko paste/upload cases,
including quotes, backslashes, newlines and private-use token characters.
Original upload SHA, byte count, stored cells, headers and schema identity were
checked across locale changes. A later whole browser run reached linear-model
prediction and failed because an accessible row label acquired an extra space.
An explicit parameterized translation fixed that label. The frozen whole-suite
rerun passed, including all transport and existing analysis workflows. No timeout
was increased to conceal the failure.

An earlier non-frozen frontend run included A05's nine intentionally failing
pre-fix race tests. It produced 486 passes and nine failures, not an all-green
A04 result. Integrated source `d036d8c` is frozen in a separate worktree with its
own dependencies for clean full checks while A05 is developed separately.

Frozen A04 Windows frontend checks passed: 70 files / 494 Vitest tests,
typecheck/production build, localization (2905 source strings / 3954 keys), and
lint (zero errors / nine existing refresh warnings). These ran from the
checkpoint's own hash-locked dependencies, not the in-progress A05 tree.

Integrated CI run `39093367838` at `d036d8c` failed the backend documentation
contract: the new transport E2E stage was described above the step inventory but
not added to the inventory itself. Python 3.11 reported 1401 passes, 11 skips and
this one failure; Linux also stopped at this contract. The stage inventory is
being synchronized, including the new A05 stage. A skipped downstream archive
job is not a successful packaging check. Whole CI must run again on a new
checkpoint. The corrected step-inventory test passed locally (one test, 216
deselected).

Frozen A04 browser command, from its own worktree and virtual environment:
`python tests/e2e/critical_path.py --backend-port 8034 --frontend-port 5234
--diagnostics-root ../e2e-remediation-a04-frozen --keep-workspace`.
Exit zero; log `.tmp/remediation-a04-frozen-e2e.log` and synthetic diagnostics
`.tmp/e2e-remediation-a04-frozen` are local evidence, not committed data.

## A05 In-Progress Evidence

The original nine deferred-response regressions failed before the hook change.
The focused post-change suite passed 95 tests across six files. A separate API
error regression first failed eight tests because dataset wrappers discarded
typed error metadata; the wrappers now preserve code/status/correlation/message.

Real browser tests let schema/cell writes commit on the synthetic backend and
hold the response until another dataset is active. Both locales also exercise
independent profile failure/retry and cancellation of a dirty schema switch.
The first run passed the schema scenario then failed because the cell fixture
selected the group column instead of the numeric column; its selector was
corrected. The second run passed all eight scenarios (exit zero), recording
source/child hashes and URL/session selection. Evidence:
`.tmp/e2e-remediation-a05-context-2` and `.tmp/remediation-a05-context-e2e-2.log`.
This run logged a Playwright `Response.finished()` cleanup-task warning at
context close; the fixture now waits for and validates the delivered JSON body
instead. The final rerun must verify that change too.

Review then reproduced another case: an acknowledged schema write can be
discarded when only a new intake draft changes, leaving the same active version
with old metadata. One targeted regression failed and one passed before its
fix (`.tmp/a05-schema-reconcile-before.log`). Reconciliation is scoped to the
unchanged committed version/generation, latest schema-write sequence and matching
base hash; it must not replace the new intake draft or reactivate an old dataset.

That reconciliation passed the next focused suite (97 tests) and ten browser
cases (`context-3`, exit zero). Review then added explicit empty-paste intent,
native file-cancel restoration and independent paste-submission ownership. The
final focused controller/transport suite passed 101 tests across six files;
scoped ESLint passed. Original user files are never changed by these tests.

Browser runs `context-4`, `context-5` and `context-6` did not pass. They exposed
test-fixture issues while extending coverage: raw editing switches back to grid
preview, removing a route handler released a held request, and the single-column
paste required an explicit delimiter/encoding before confirmation. The fixture
now selects raw mode, holds only the first request without unregistering it, and
confirms parsing options explicitly. No product wait timeout was increased.
The corresponding logs are `.tmp/remediation-a05-context-e2e-{4,5,6}.log`.

The first typecheck caught a paste-display test fixture missing the new draft
revision accessor; that fixture was corrected. A concurrent follow-up typecheck
caught a narrowing error in the not-yet-integrated A06 helper, subsequently fixed
and checked with `node node_modules/typescript/bin/tsc --noEmit` (exit zero).
A06's five pre-fix component regressions are intentionally red until its own
implementation and are not included in the A05 checkpoint.

Final A05 browser run `context-7` exited zero with all 16 cases (eight per
locale), no failed page errors or the earlier response-finished cleanup warning.
Command from the root checkout, using the integrated hash-locked environment:

```powershell
.\.tmp\remediation-a04-source\.venv\Scripts\python.exe tests\e2e\critical_path.py --backend-port 8035 --frontend-port 5235 --dataset-context-only --diagnostics-root .tmp/e2e-remediation-a05-context-7 --keep-workspace
```

Log: `.tmp/remediation-a05-context-e2e-7.log`. Each synthetic case records exact
server identities/hashes, a screenshot and a trace under that diagnostics root.
The profile-retry screenshot was visually inspected; this confirms recovery and
preserved dataset content, not a complete English-copy audit. Existing awkward
English profile labels and untranslated warning prose remain A11/A14 display
work, distinct from the protected API transport boundary.
