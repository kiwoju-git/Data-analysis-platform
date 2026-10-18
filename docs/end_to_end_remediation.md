# End-to-End Remediation

## Baseline and Scope

- BASE_SHA / initial local HEAD / initial origin/main:
  `f736db03fb61a3177c5a85cb0a422fbe0238a547` (fetched 2026-10-18).
- Working branch: `feat/end-to-end-reliability-remediation`.
- Existing untracked `examples/image2.png` is user-owned and is not staged.
- `data_prd.md` is absent. AGENTS.md, the addendum, implementation guide,
  task list and current method/runtime contracts govern this work.
- Existing dataset/result/model bytes are not rewritten. A12 adds metadata
  migration 21 for managed ownership; historical report BLOB/hash values are
  preserved. All browser fixtures use an isolated workspace.
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
| A04 | Transport/i18n | reproduced / fixed / verified | Body preservation and explicit display boundaries; subsequent native checkpoint A09 passed every job. Earlier failures remain below. |
| A05 | Dataset context | reproduced / fixed / verified | 101 focused/16 real-server en/ko scenarios; integrated native A09 Windows/Linux passed after the explicit replacement-confirmation fixture correction. |
| A06 | GPR direct prediction | reproduced / fixed / verified | Five pre-fix regressions, 80 focused/18 real-model browser cases; native A09 passed. Snapshots are not managed reports. |
| A07 | Schema CAS | reproduced / fixed / verified | Atomic CAS/no-op/conflict UI; 299 broad backend/18 final backend/119 frontend/six real two-editor browser cases and native A09 passed. |
| A08 | Workspace/backup | source_confirmed / reproduced / fixed / verified | Exclusive lease/offline archive, actual asset round-trip/CLI; native A09 passed after platform-neutral fault injection fix. |
| A09 | Chart formatters | source_confirmed / reproduced / fixed / verified (focused) | Axis/legacy/locale precedence wired; coordinates/pin preserved in browser. Whole-check gate remains separate. |
| A10 | Report Center | source_confirmed / reproduced / fixed / verified (focused) | Independent list/detail/status and exact-owner guards; real-component browser passed. A10 checkpoint was cancelled by a later dispatch; final native gate remains separate. |
| A11 | Generic reports | source_confirmed / reproduced / fixed / verified (local focused) | Stored-only readers, actual HTML parity and UI guards passed; two checkpoint failures and their corrections are retained below. Final native gate pending. |
| A12 | Dedicated reports | source_confirmed / reproduced / fixed / verified (local focused) | Six exact source kinds, opt-in server predictions, ownership/retention/backup and actual EN/KO offline-report browser flow passed. Native gate pending. |
| A13 | Execution capabilities | source_confirmed / reproduced / fixed / verified (local focused/browser) | Unsupported cancellation, atomic terminal protection, grouped counts, lease-owned recovery and transactional completion dependencies passed focused checks. Twelve real-server KO/EN current-result cases passed after fixing a reproduced failed-activation selector mismatch; final native gates remain pending. |
| A14 | Capability documentation | source_confirmed | Guidance drift found; generated registry/handler/report matrix pending. |
| A15 | Release installation identity | source_confirmed | Existing marker content/installed-code mismatch can be missed; pre-import release-owned identity guard pending. |

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

### A05 Native Checkpoint

At `053a789`, CI run `39095990487` passed Python 3.11 (1402 passed, 11 skipped,
97 warnings) and all five exact-install Python security profiles plus npm
runtime/all audits (zero advisories and zero skipped packages). Linux backend
also passed 1402 tests with 11 skips, then localization rejected five unused
source mappings left by A05's semantic error/message replacements. Only those
obsolete `sourceToKey` entries were removed; historical translation keys remain.
The root localization rerun passed with 2900 source strings / 3968 keys, including
A06. This does not make the failed checkpoint green; a new native run is required.

## A06 Evidence

GPR prediction now captures analysis/model/manifest/response identity, exact
predictor order, request row IDs/values and input revision. Edits, row changes,
source changes and new requests revoke old success/error/finally ownership.
Completion validates the complete response before publishing; row order may
change, but missing/duplicate/foreign IDs and wrong model identity are rejected.
The separate JSON download is not a managed Report Center artifact. PLS's
existing snapshot validation now precedes display, and both workflows retain
unknown warning codes as escaped text. Training/model artifacts are unchanged.

Five component regressions failed before the fix. The post-fix focused suite
passed 80 tests in six files; scoped ESLint (11 files), strict TypeScript and
diff checks passed. The pure/node tests do not substitute for browser evidence.

The real-model browser run exited zero with nine scenarios per locale:
edit, delete, replacement request, model replacement, reordered rows, duplicate
IDs, missing IDs, foreign IDs and foreign model identity. It uses two genuinely
saved synthetic GP models and holds completed server responses. Locale/resize
does not issue another prediction. Exported means/intervals are compared at full
JSON precision; visible table rounding uses the existing three-decimal policy.
Both original analysis envelopes and stored model hashes remain unchanged.

```powershell
.\.tmp\remediation-a04-source\.venv\Scripts\python.exe tests\e2e\critical_path.py --backend-port 8036 --frontend-port 5236 --gp-prediction-context-only --diagnostics-root .tmp/e2e-remediation-a06-prediction-1 --keep-workspace
```

Evidence: `.tmp/remediation-a06-prediction-e2e-1.log` and the 18 per-case
trace/screenshot/evidence records under that diagnostics root. The completed
reordered-response screenshot was inspected. These are synthetic and untracked.
The E2E step-inventory test passed (one test / 216 deselected); an initial command
pointed at the wrong test module and selected no tests, not a pass. Full Windows/
Linux and whole-product checks remain separate gates before main/Release.

Native A06 run `39096843917` at `a5f1dbd` passed Linux full checks: 1402 backend
tests / 11 skips / 97 warnings, 75 frontend files / 612 tests, localization,
typecheck/build/lint and source-runner loopback/LAN lifecycle. Python 3.11 and
dependency-security also succeeded. Linux browser E2E passed the new transport,
dataset and GP stages, then failed an old Report Center assumption: it expected
two global results, but the new GP fixture correctly retained two additional
saved models/analyses. The test now explicitly selects the current-dataset filter
before asserting that dataset's two results. No saved fixture is deleted to hide
the difference. The corrected whole browser flow still requires rerun.
Log: `.tmp/remediation-a06-ci-linux.log`; failed-page artifact:
`39096843917/artifacts/12125436449`. Windows was still running when recorded.

## A07 Evidence

Frontend pre-fix tests reproduced three failures: missing expected hash and no
latest-schema comparison after a conflict. Backend pre-fix testing confirmed
that an omitted expected hash incorrectly succeeded (one failure). The CAS now
checks owner/hash/no-op/columns/stale flags under one `BEGIN IMMEDIATE` boundary.
Review additionally required no-op preservation of an existing opaque schema
hash even when the current hash function would produce a different value.

Runtime 23 checks passed locally: backend health/startup/web-serving checks,
19 passed / one platform-permission skip / three deprecation warnings, and
frontend runtime compatibility, four passed. Backend command used root
`PYTHONPATH` with the integrated locked environment; log
`.tmp/remediation-a07-runtime.log`. These are runtime checks, not completed CAS
or browser acceptance. Metadata remains 20 and methods are unchanged.

The backend CAS-focused suite passed 299 tests; final CAS/API rechecks passed
18 tests. The first real two-editor browser run failed after the successful
merge save: its fixture expected private-use characters in the saved display
label, whereas the existing schema-label policy removes non-printable characters.
The corrected test separately checks unchanged request text and the normalized
stored label. No production label policy was changed. Child-page diagnostics
now include the actual exception location as well as page/context evidence.
This failed run is retained at `.tmp/e2e-remediation-a07-schema-1`.

The frozen local A05 full check at `053a789` passed Ruff, mypy and 1410 backend
tests / three skips / 97 warnings (1862.22 seconds), then failed on the same five
obsolete localization source mappings already fixed in A06. Windows CI at that
checkpoint passed 1411 backend tests / two skips / 97 warnings before the same
localization failure. Neither run reached frontend tests or browser E2E.

The corrected A07 browser run passed all six cases (apply/discard/late comparison
in Korean and English). A second concurrent write after accepting the comparison
is rejected again; only the explicit final save commits. Canonical/source hashes
and previously saved result bytes remain unchanged, and its stale flag is true.
Resize/locale change issues no PATCH. Evidence is in
`.tmp/e2e-remediation-a07-schema-2`; command:

```powershell
.\.tmp\remediation-a04-source\.venv\Scripts\python.exe tests\e2e\critical_path.py --backend-port 8037 --frontend-port 5237 --schema-concurrency-only --diagnostics-root .tmp/e2e-remediation-a07-schema-2 --keep-workspace
```

The no-op UI regression failed two tests before correction; its final focused
suite passed 119 tests in five files. Full frontend Vitest passed 641 tests in
77 files. Localization passed 2900 source strings / 3993 keys. Scoped frontend
lint, strict typecheck, E2E Ruff and the documentation step-inventory test passed.
An initial inventory command selected no tests in the wrong module; it was not
counted as a pass. The successful test is in `test_openapi_frontend_contract.py`.
Independent source review found no new blocking issue; it is not execution
evidence. Late analysis completion after a schema change remains the separate
A13 persistence review, not a solved property of the current schema transaction.

The A05 dataset-context browser suite was rerun against A07 and all 16 cases
passed (`.tmp/e2e-remediation-a07-dataset-regression`, ports 8035/5235,
`--dataset-context-only`). Production build also passed; its existing large-chunk
warning remains a performance advisory, not a suppressed failure. This checkpoint
is ready for whole-product/native integration, not for main or Release publication.

Native A07 CI `39098275942` passed Linux full checks (1418 backend tests / 11
skips / 104 warnings; 641 frontend tests), source-runner lifecycle, Python 3.11
and dependency security. Its full browser flow then failed upload error recovery:
the new file replacement confirmation was implicitly dismissed by Playwright.
The application correctly retained the cancelled file/error. Three Node
regressions verify reject/approve/late-failure behavior without production changes;
the browser fixture now explicitly approves and checks that exact confirmation.
This is a failed CI checkpoint, not a full native pass. Log:
`.tmp/remediation-a07-ci-linux.log`.

## A08 In-Progress Evidence

The exclusive OS lease precedes every app initialization/recovery operation;
future metadata versions and incomplete restore publication are rejected before
mutation. On local Windows/Python 3.10, lease/lifespan/startup/migration/CAS checks
passed 70 tests / one symlink-permission skip. Final lease/lifespan rechecks passed
28 tests / one skip. Real Uvicorn servers on distinct ports also verified shared
workspace refusal and independent workspace success (one test, 40.02 seconds;
`.tmp/remediation-a08-real-server-lease.log`). Native Linux remains a separate gate.

The first actual-asset backup integration failed in verification staging: Windows
rejected a path beyond its non-prefixed path limit although the original API-owned
file path was short enough. The fixture is retained; shortening it would conceal
the product defect. Validated internal extended-path I/O now fixes that failure,
without persisting platform prefixes in metadata or archive member paths.
Log: `.tmp/remediation-a08-backup-api.log`. Archive/security unit passes alone do
not establish successful model/report backup and restore.

The second integration attempt reached restore/reopen, then hit an overly broad
test guard: the existing attribute-limit-set reader intentionally checks its
canonical source integrity. That reader alone may use its original verification
iterator; backup, verify, restore, report reads, and model prediction still run
under no-refit/no-source-row-load guards. The third attempt passed both integration
tests (30.66 seconds, three existing deprecation warnings): real GP/PLS/OLS models,
saved predictions, HTML exports, control limits, Factorial/LHS/BO stored assets,
and an unconfirmed upload. Logical DB rows and external file hashes match before
and after restoration; reopened model predictions match over two app restarts.
The second test invokes the real CLI in separate Python processes with Korean/
space paths and verifies existing-output refusal without changing its hash.

```powershell
$env:PYTHONPATH = "$PWD\backend"
.\.tmp\remediation-a04-source\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_workspace_backup_api.py -q
.\.tmp\remediation-a04-source\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_workspace_server_lease.py -q
```

The temporary environment is the native Windows hash-locked environment; source
imports point explicitly to the current root. Logs:
`.tmp/remediation-a08-backup-api-2.log` (failed test guard),
`.tmp/remediation-a08-backup-api-3.log` (two passed), and
`.tmp/remediation-a08-real-server-lease.log` (one passed).

Independent review found and prompted fixes for actual ZIP central-directory
counting before allocation, concatenated-directory offsets, bounded SQLite
metadata hydration, and atomic no-replace Linux restore publication. Final Windows
backup unit tests passed 66 cases (76.90 seconds, one intentional malformed-ZIP
fixture warning), including an oversized integer limit's typed refusal. Scoped
Ruff/format and mypy passed (root mypy: five production files). Linux
`renameat2(RENAME_NOREPLACE)` and native offline restoration still require CI;
Windows passes are not evidence of Linux execution.

The CSV recovery focused runner initially failed its own `/` versus `/home`
readiness assertion. After correcting that test route, the actual browser passed
empty-file error, explicit replacement approval, native FileList change, cleared
error, valid upload and parsing. Production code was not changed. Evidence:
`.tmp/remediation-upload-recovery-e2e-retry.log` and
`.tmp/e2e-remediation-upload-recovery-retry/screenshots/csv-upload-error-recovery.png`.
Hook tests passed 95 cases, and the step-inventory test passed one case. This
follow-up is commit `5be3d64`, not a claim of a completed whole E2E run.

Native A08 checkpoint `07074f7` / run `39099846083` failed Python 3.11 with
1515 passed / 11 skipped / 105 warnings / one failure (244.89 seconds).
The failing rollback test patched `Path.rename`, while Linux correctly uses
`renameat2`; no interruption was injected. Its replacement patches the shared
publication boundary and asserts the actual injection/call order. The separate
real-platform no-replace test remains intact. The corrected narrow Windows run
passed two tests / 64 deselected (3.01 seconds); native rerun is still required.
The failed native run did pass actual backup/restore/CLI and lease tests, but is
not a successful whole gate. Logs: `.tmp/remediation-a08-ci-py311.log` and
`.tmp/remediation-a08-publication-crossplatform.log`.

## A09 Evidence

The original Scatter accepted but ignored `formatValue`; seven pre-fix formatter
tests failed. A separate two-observation test exposed fractional row labels.
The fix separates numeric tick positions from labels, wires per-axis/legacy
formatters, and uses explicit integer tick labels only for known row/order axes.
No stored coordinate, analysis method, interval, pin/source identity or artifact
is changed. Focused checks passed 29 tests in five files and 29 consumer tests in
six files, plus scoped lint, Python checks and the step-inventory assertion.

The standalone browser first passed six EN/KO viewport cases. The integrated
rerun also included 1280 x 800, so all eight locale/viewport cases passed together
with existing interaction and PCA/PLS/GP chart-model suites. Each checks raw
coordinate invariance, selection retention, explicit source reset and zero API
requests. Synthetic diagnostics/screenshots are in
`.tmp/e2e-remediation-a09-charts`; log `.tmp/remediation-a09-charts-e2e.log`.

```powershell
.\.tmp\remediation-a04-source\.venv\Scripts\python.exe tests\e2e\critical_path.py --backend-port 8040 --frontend-port 5240 --chart-formatting-only --diagnostics-root .tmp/e2e-remediation-a09-charts --keep-workspace
npm --prefix frontend test -- --run
```

The first full Vitest run passed 654 tests and failed the existing lazy-workspace
module import at its 5-second timeout while the browser suite was also running.
Without source or timeout changes, the isolated test passed all three cases
(2.32 seconds of test execution). This does not prove a product defect or erase
the first failure. The complete frontend rerun is recorded separately; no timeout
increase or test removal is used. Logs: `.tmp/remediation-a09-frontend.log` and
`.tmp/remediation-a09-lazy-isolated.log`.

The complete rerun passed 655 tests in 78 files (72.48 seconds), without a
concurrent browser suite. TypeScript strict checking, production build, and
localization (2900 source strings / 3993 keys) passed. ESLint exited successfully
with nine pre-existing React fast-refresh warnings and no errors. The production
build retains its large-chunk advisory. Logs: `.tmp/remediation-a09-frontend-2.log`
and `.tmp/remediation-a09-build.log`. The frozen A08 whole Windows check and the
next native CI remain separate, unfinished gates; these results do not authorize
main or Release publication.

The same A08 fault-injection failure also occurred on Linux/Python 3.12:
1515 passed / 11 skipped / 105 warnings / one failure (254.86 seconds).
Its log is `.tmp/remediation-a08-ci-linux.log`; the correction is `ab6a5da`.

A09 checkpoint `3eb3e57a1e1950013a0e1e13907a738e573957a9` was pushed only to
the feature branch. CI run `39101069921` is the native rerun, not a completed
release gate at this point.

## A10 In-Progress Evidence

Before implementation, deferred hook tests reproduced eight failures and passed
three existing related cases (92 deselected): list/detail callback coupling,
late URL selection, dataset-null filter broadening, invalid/duplicate link
requests, missing same-mount navigation handling, and an unmounted deletion
callback. Log: `.tmp/a10-report-red.log`. These are synthetic client-state
reproductions, not assertions about a user's workspace.

## A11 Baseline

Before report changes, the current contract/PLS/Two Variances/export-retention
tests passed 48 tests with three existing deprecation warnings (48.94 seconds).
This baseline includes existing dispatch-only checks and does not prove missing
report sections are implemented. Log: `.tmp/remediation-a11-report-baseline.log`.

```powershell
$env:PYTHONPATH = "$PWD\backend"
.\.tmp\remediation-a04-source\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_report_coverage.py backend/tests/unit/test_pls_report.py backend/tests/unit/test_two_variances_report.py backend/tests/unit/test_analysis_export_retention_api.py -q
```

The existing HTML API checks also passed before implementation: eight passed /
226 deselected / four deprecation warnings (46.06 seconds), using
`-m pytest backend/tests/unit/test_api_contracts.py -k analysis_result_html_report -q`.
Log: `.tmp/remediation-a11-html-api-baseline.log`. Existing textual assertions are
not evidence of visible plot/section parity; the new A11 checks must inspect the
rendered body and exclude the raw JSON appendix.

## Native Checkpoint Updates

A08 Windows hosted CI job `117593692320` passed: 1525 backend tests, two skips,
105 warnings (1355.49 seconds), 644 frontend tests / 77 files, strict typing,
production build, lint (nine existing warnings), and localization. This is a
Windows hosted runner, not a physical Windows 11 validation. The separate E2E
job `117597883752` was still running at this observation.

A09 Python 3.11 job `117597273651` passed 1516 tests / 11 skips / 105 warnings
(248.71 seconds), including the corrected platform-neutral restore interruption
test. The subsequent numerical diagnostic probe is explicitly not acceptance
evidence; its deliberate smaller BO budget failure is not a passed calculation.
Logs: `.tmp/remediation-a08-ci-windows.log`, `.tmp/remediation-a09-ci-py311.log`.

The frozen A08 local Windows whole check finished successfully: 1523 backend
tests / four skips / 105 warnings (1885.11 seconds), 644 frontend tests / 77
files, Ruff, formatting, mypy, strict TypeScript, localization and production
build. ESLint retained nine existing warnings. Log:
`.tmp/remediation-a08-whole-check.log`. This validates that frozen checkpoint,
not the later A10/A11 worktree.

A09 native Linux/Python 3.12 job `117597273507` passed 1516 tests / 11 skips /
105 warnings (215.96 seconds), 655 frontend tests / 78 files, full checks,
the complete synthetic Chromium critical path and the LAN guard checks.
Log: `.tmp/remediation-a09-ci-linux.log`. Other jobs and later commits still
require their own release gate.

## A09 Small-Value Follow-Up

Independent call-site review found that honoring previously ignored formatters
exposed old three/six-decimal formatting: distinct small nonzero values could
all display as zero. Six actual consumer SSR tests failed before the correction.
Pearson, gage and prediction charts now use scientific-capable axis formatting
and significant-digit details. Fixed-decimal consumers retain ordinary-value
rounding and use a narrow nonzero fallback only when rounding would erase a
nonzero value. No coordinate or statistic changes. Focused tests passed 34 cases;
scoped lint and strict TypeScript passed. Logs:
`.tmp/remediation-a09-small-values-before.log` and
`.tmp/remediation-a09-small-values-after.log`.

The combined frozen A09 follow-up/A10 frontend suite passed 688 tests in 80 files
(54.04 seconds), with no concurrent browser suite. Root strict TypeScript passed.
Log: `.tmp/remediation-a10-frontend-full.log`.

## A10 Verification

List, selected result and selected status now have independent identities and
guards. A single stable selected panel preserves export state/focus across list
filters. Missing dataset scope blocks a current-dataset request until explicitly
changed. Invalid/duplicate UUID queries never request a result; actual missing
owners clear selection, while transient errors preserve the requested identity.
StrictMode replay, same-mount navigation and all late-response branches are
covered. Stored-result and dataset bytes are not modified by this client change.

Focused Vitest passed 221 tests; API route/step contracts passed 219 tests with
two existing warnings. Strict TypeScript, scoped ESLint, localization (2897
source strings / 4003 keys), Python checks and diff whitespace passed. Real
Chromium, with a mocked synthetic transport and actual Report Center components,
passed KO/EN at 1440, 1280, 1024 and 390 widths, delayed list/detail/status/delete
responses, filters, null dataset scope, retries, invalid links, unmount/remount
and exact-owner removal. This is browser state evidence, not a real backend
mutation test. Diagnostics: `.tmp/e2e-a10-report-center-final/`; logs:
`.tmp/a10-report-final-focused.log`, `.tmp/a10-openapi-final.log`,
`.tmp/a10-report-browser-final.log`. Earlier browser fixture failures (asserting
an unrendered export ID and a misplaced new test block) remain recorded; the
final assertions inspect visible checksum/state and correct scenario order.

Root frozen frontend verification also passed the full ESLint run (zero errors,
nine existing warnings), production build (existing chunk-size advisory),
localization and `git diff --check`. Logs: `.tmp/remediation-a10-lint.log`,
`.tmp/remediation-a10-build.log`. No main/Release publication is implied.

## A11 Implementation and Evidence

Report definitions now declare accepted schemas, estimator/design variants,
renderer version and required/optional sections. The same stored-payload
assessment drives the catalog/capability API, frontend controls and HTML body.
HTML schema 4 adds level/renderer/section metadata; old files are untouched.
Unsupported core fails before an artifact is created; a source SHA mismatch is
409. HTML no longer flattens the result into CSV path/value rows.

Method-specific pure renderers add stored diagnostics, PCA loading/biplot/D-squared,
inference intervals/TOST/post-hoc, categorical tables/association, Pearson/XY,
OLS selection/ANOVA/residuals, regularized residual distribution and every stored
coefficient path, GP mean/observation-SD surfaces, and quality/gage charts.
PLS retains every saved component and point. Missing historical sections lower
coverage rather than refitting; ANOVA residuals and gage interactions absent from
current payloads remain explicit limitations. See `html_report_coverage_matrix.md`.

The source reader is separate from normal restore freshness checks: result,
snapshot and frozen Phase II assets are verified without raw-row reloading.
Read-before-path-validation and Phase II label/config disagreement were corrected.
The latter was reproduced as two actual capability requests incorrectly returning
200/full before the fix (`.tmp/a11-phase-label-prefixed.log`). General legacy
config has no independent full-config digest; this limitation is not concealed.

Executed narrow evidence (synthetic only):

- Source/family checks: 56 passed, two Windows real-symlink privilege skips,
  three existing warnings, 83.56 seconds (`.tmp/a11-source-family-final.log`).
- Updated shared geometry + EDA/Pearson/quality API: 31 passed / 230 deselected,
  20.64 seconds (`.tmp/a11-family-api-final.log`).
- Hypothesis/categorical/warnings: 139 passed / 18.60 seconds; actual-family API
  two passed / 232 deselected / three warnings. Initial API run used the old root
  venv and failed before upload parsing; current-lock rerun passed, not suppressed.
- Actual HTML API families: eight passed / 226 deselected / four warnings
  (`.tmp/remediation-a11-html-api-2.log`).
- Capability API: six passed / three warnings / 20.48 seconds; contract/dispatch
  checks 47 passed. Dispatch-only checks are not numerical parity evidence.
- GP/OLS contract plus GP HTML API: 27 passed / five deselected / three warnings
  (`.tmp/remediation-a11-gp-linear-contract-3.log`). Earlier two test failures used
  a transient NumPy prediction basis in a saved-payload equality check; the fixture
  now mirrors the runner's separate basis storage. A later assertion still used
  the old training-plot title and was replaced with actual visible section checks.
- Frontend focused 233 passed; OpenAPI 220 passed; strict typing, scoped lint,
  localization (2889 sources / 4025 keys), and diff whitespace passed.
- Full frontend 700 passed in 82 files / 71.17 seconds, with no concurrent browser
  suite (`.tmp/remediation-a11-frontend-full.log`). Mypy passed 184 source files
  at the preceding report checkpoint (`.tmp/remediation-a11-mypy-2.log`).
- Real Chromium KO/EN capability/export races, hash conflict, exact owner,
  locale/mutation and Unicode filename download passed at 1440/1280/1024/390.
  Diagnostics `.tmp/e2e-a11-report-capability-final` contain 16 PNGs, four traces,
  two synthetic downloads and two evidence JSON files. HTTP is mocked in this
  component-state suite, not a claimed live backend run. Both earlier fixture
  failures selecting an already-active filter remain in prior logs.

Independent review reproduced a malformed GP kernel-selection list causing an
uncaught AttributeError. Explicit nested-object validation and negative fixtures
now reject this as unsupported; the final expanded report suite is still pending.
No main or Release publication has occurred.

### Native Checkpoint Boundary

Run `39101069921` at `3eb3e57a1e1950013a0e1e13907a738e573957a9`
completed successfully across Windows, Windows E2E, Linux, Python 3.11,
dependency-security and Linux archive verification. This proves that checkpoint,
not the later A09 small-value follow-up/A10/A11 changes. Run `39102592691` at
`36e50949f2317ea2805e2331c88c9f3f1b64f006` had Linux/Python 3.11/security/archive
success while Windows was still running at this observation. A CI archive is not
a published GitHub Release or evidence for unimplemented A12-A15.

### A11 Frozen Integration

The final combined report-focused run passed **334 tests**, with two Windows
symlink-privilege skips and three existing warnings (169.19 seconds). Log:
`.tmp/remediation-a11-focused-integrated.log`. The command used the current-lock
Python with `PYTHONPATH=$PWD/backend` and these files after `-m pytest ... -q`:

```text
backend/tests/unit/test_report_contract.py
backend/tests/unit/test_report_coverage.py
backend/tests/unit/test_analysis_report_capabilities.py
backend/tests/unit/test_analysis_report_source.py
backend/tests/unit/test_basic_eda_report.py
backend/tests/unit/test_hypothesis_report.py
backend/tests/unit/test_categorical_report.py
backend/tests/unit/test_report_warnings.py
backend/tests/unit/test_linear_model_report.py
backend/tests/unit/test_stored_family_reports.py
backend/tests/unit/test_gaussian_process_report_contract.py
backend/tests/unit/test_pls_report.py
backend/tests/unit/test_two_variances_report.py
backend/tests/unit/test_analysis_export_retention_api.py
```

The first integrated Basic EDA API run had two old-heading assertion failures
(70 passed). Both now inspect visible section IDs/tables/SVG and saved values;
the exact two reran successfully (21.48 seconds, four existing warnings).
No numeric tolerance or calculation was changed. Logs:
`.tmp/remediation-a11-dispatch-integrated.log`, `.tmp/remediation-a11-basic-eda-api.log`.

Real-server Chromium verification also passed, including PLS analysis, completed
prediction snapshot, KO/EN HTML creation/download, offline file navigation and
Report Center redownload, plus GPR settings/kernel comparison and chart/layout
checks. This used a synthetic temporary workspace, not the user's server/data:

```powershell
$env:PYTHONPATH = "$PWD\backend"
.\.tmp\remediation-a04-source\.venv\Scripts\python.exe tests/e2e/critical_path.py --backend-port 8027 --frontend-port 5257 --gpr-report-only --diagnostics-root .tmp/e2e-a11-real-reports
```

Exit 0, diagnostics `.tmp/e2e-a11-real-reports`, log
`.tmp/remediation-a11-real-report-e2e.log`; test-created servers were terminated
by the runner. Full frontend: 700/82, strict TypeScript, production build,
localization 2889/4025 and ESLint passed (nine existing warnings). Backend Ruff
and format check passed 316 files; mypy passed 185 source files after integration.
Whole-backend/native A11 checkpoint and later A12-A15 gates remain separate.

Final actual HTML API rerun (`-m pytest backend/tests/unit/test_api_contracts.py
-k analysis_result_html_report -q`) passed eight tests / 226 deselected / four
existing warnings in 31.30 seconds. Log `.tmp/remediation-a11-html-api-final.log`.

### A11 Whole-Suite Catalog Assertion Correction

Native Linux run `39105316544` at `4825511` reported 1 failed, 1805 passed,
11 skipped, 105 warnings (267.58 seconds). The catalog test prohibited the
substring `statistic` anywhere in serialized metadata, including the legitimate
`descriptive_statistics` report summary type. It now recursively rejects actual
`statistic`, `p_value`, or `result` fields instead of banning text in descriptors.
This preserves the no-fabricated-result gate; no production/numerical change was
made for the failure. Log: `.tmp/remediation-a11-ci-linux.log`.
A10 run `39102592691` was cancelled by the branch concurrency policy after the
A11 dispatch; its successful Linux/Python311/security/package jobs are not an
all-platform completed gate.

Retry `39106093827` at `ecfb5fa` passed Python 3.11 calculation/API and all
dependency-security jobs, but Windows/Linux Check stopped at Ruff format for
the corrected catalog test. This omitted formatting step is recorded as a real
failed gate, not a statistical failure. The single test file was formatted and
its Ruff lint/format checks rerun. Full checkpoint validation remains pending.

### A12 In Progress: Exact Stored Sources

Six typed source kinds now bind their real workflow owner, revision and hashes.
Generic prediction sources remain distinct from dedicated DOE sources. PLS/GP
completed predictions are opt-in server-produced artifacts; browser JSON
snapshots are not accepted as report sources. Export does not refit or reread
canonical dataset rows. The request contract remains API 23; additive managed
LHS/BO ownership records require metadata 21. Existing stored numerical method
versions/results are not rewritten.

Initial checks (not final A12 verification):
- Completed PLS/GP prediction persistence/report tests: 3 passed, 3 warnings,
  27.27 seconds (`.tmp/remediation-a12-completed-predictions.log`). This includes
  a synthetic direct metadata removal case, not a claim of owner-delete API
  coverage; actual retention tests are separate.
- Backup tests: 69 passed, one existing warning, 154.95 seconds
  (`.tmp/remediation-a12-backup.log`). Schema 20 backups restore unchanged and
  migrate to 21 only through normal initialization; unsupported 19/22 rejected.
- Actual-source report roundtrip first run: 4 failed / 4 passed / 3 warnings,
  81.85 seconds (`.tmp/remediation-a12-api-roundtrip.log`). DOE inserts revealed
  the existing asset CHECK restricted all schemas to 1. Migration tests now
  explicitly preserve legacy BLOB/hash bytes while permitting the new report
  schema. This failure is not yet counted as fixed/verified.
- Integration review found locale artifact lists mixed EN/KO reports. The
  source-and-locale filter is corrected with actual API regression coverage.
  A deferred A-B-A browser action test also found an old busy-state presentation
  issue; the frontend correction and recheck are still in progress.

No main push or Release publication has occurred. A13-A15 and final aggregate
gates remain outstanding.

### A11 Frozen Windows Completion

The frozen `4825511` Windows/Python 3.10 check completed with 1 failed, 1810 passed,
6 skipped and 105 warnings in 2817.97 seconds. The sole failure is the old catalog
substring assertion already corrected in `ecfb5fa` and formatted in `dc72bb4`.
`check.ps1` correctly stopped at that backend failure and did not run its later
frontend gates. This run is not reported as passing or as validation of A12.
Log: `.tmp/remediation-a11-whole-check.log`.

### A12 Focused Integration Evidence

The fresh-workspace API rerun passed 13 tests / 3 existing warnings in 143.26
seconds (`.tmp/remediation-a12-api-roundtrip3.log`):

```powershell
$env:PYTHONPATH = "$PWD\backend"
.\.tmp\remediation-a04-source\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_managed_report_api.py backend/tests/unit/test_completed_predictions.py -q
```

It covers actual source creation, both report locales, exact snapshot identity,
HTML create/list/download/delete, hashes and visible tables/SVG, legacy DOE export
list compatibility, and offline backup/restore of LHS/BO/DOE/pasted-prediction
reports to another workspace. Legacy dataset predictions correctly report missing
stored input values as summary rather than rereading data. The first dataset
fixture asserted HTTP 201 although that established endpoint returns 200; the
corrected fixture passed without changing the endpoint (`old-prediction2.log`).

Dedicated reader/render tests passed 15 cases / 3 warnings / 134.22 seconds,
plus two actual BO attachment cases after the final metadata-stale refinement.
No-recompute sentinels cover stored design/quality/optimizer/recommendation reads.
The parser retains saved fitted-cell/profile tables rather than computing new
marginal/cube/contour plots. Logs: `.tmp/a12-dedicated-source-tests6.log`,
`.tmp/a12-dedicated-attachment-tests.log`.

Source-bound journal/retention/migration checks passed 21 cases, one Windows
symlink privilege skip, 22 deselected, 143.18 seconds. Real child processes cover
crash before/after commit; GP/PLS model-delete then owner-cascade, snapshot-only
deletion with immutable historical HTML and source capability conflict, NPZ
manifest mismatch, and legacy DOE BLOB/schema preservation are exercised.
The earlier missing-snapshot 404/409 failure remains recorded in
`.tmp/a12-source-bound-final.log`; final `.tmp/a12-source-bound-verified.log` passed.

Independent review also reproduced an out-of-bound header-open ordering defect
in the legacy prediction reader. The report path now validates its exact owned
path before calling that loader. The negative test failed before the fix and
passed afterward (12.66 seconds): `.tmp/a12-prediction-preopen-before.log` and
`.tmp/a12-prediction-preopen-after.log`.

Frontend full run initially had 725 passes and two existing lazy-import timeouts.
Unchanged isolated suites passed 6/6, and the unchanged full rerun passed 727/85
in 70.49 seconds; timeouts were not increased. Logs `.tmp/a12-front-all.log`,
`.tmp/a12-lazy-isolated.log`, `.tmp/a12-front-all-rerun.log`. A later strict check
found two new test-only locale literal inference errors; their correction and
strict rerun are still pending at this ledger entry. Browser mocks passed six
source kinds, guarded snapshots and four viewport widths in KO/EN; they are not
substituted for the newly added real-server helper's pending execution.

Further A12 verification:
- Current runtime/startup, legacy prediction path-safety and offline backup tests:
  86 passed / 4 existing warnings / 203.79 seconds
  (`.tmp/remediation-a12-runtime-backup-final.log`).
- Owner-deleted-between-read regression now returns the stable source-change 409,
  rather than an internal assertion. Actual PLS/GP snapshot tests passed 3 cases /
  3 warnings / 19.32 seconds (`.tmp/remediation-a12-owner-race-final.log`).
- Backend Ruff lint and format passed (335 files). The prior all-backend mypy
  passed 198 modules; it will be rerun by the checkpoint gate.
- The final frontend state before the LAN digest correction passed 728 tests in
  85 files, strict types, build and localization. Same-source re-selection had a
  real deferred failing test before its no-op correction, not a timeout increase.
- Review identified `crypto.subtle` availability as an HTTP LAN download issue.
  A local, pinned hash-library fallback is being verified; no header-only digest
  bypass is accepted. These earlier frontend checks do not yet cover that change.

HTTP LAN digest correction: pinned MIT `@noble/hashes` 2.4.0 supplies a locally
bundled fallback only when native SubtleCrypto is absent. Actual received bytes
and descriptor size/hash are still compared; native operational failures are not
silently bypassed. Final frontend Vitest passed 738 tests / 86 files / 77.61
seconds (`.tmp/a12-front-all-digest.log`), followed by strict types, production
build and localization checks (each exit 0). The SHA implementation is a lazy
5.33 kB / 2.64 kB gzip chunk. Dependency rationale, independent vectors, malformed
download tests and measured 16 MiB cost are in
`docs/download_checksum_compatibility.md`. Linux packaging already inventories
runtime notices; its verifier now also requires the new library's MIT notice.

Final A12 source-deletion checks: 3 passed / 7 deselected / 35.34 seconds for
actual generic/DOE report download races, and 1 passed / 9 deselected / 17.54
seconds for the DOE list/read deletion boundary. Logs:
`.tmp/remediation-a12-report-delete-race.log`,
`.tmp/remediation-a12-report-list-race.log`. Repeated backend Ruff lint/format
passed, and all-backend mypy passed 198 modules
(`.tmp/remediation-a12-mypy-final.log`).

The first real-server browser run failed before opening the managed source:
the new test helper tried to read a Playwright prediction response body after a
page navigation, when Chromium had discarded its response resource. The test
now captures request/response immediately after prediction, before navigation.
No application or timeout change was made for this failure. Original diagnostics
remain in `.tmp/e2e-a12-real-managed` and
`.tmp/remediation-a12-real-managed-e2e.log`; the corrected run is separate.

The second browser run verified both locales' exact prediction snapshots,
managed HTML creation/download and offline visible input/prediction values, plus
the WebCrypto-unavailable KO download. It then failed the EN deep-link locale
check: the existing main E2E context's init script forcibly wrote KO on every
new document. That fixture now seeds KO only when no locale has been stored,
so a real in-app choice survives reload. This is not evidence that LocaleProvider
caused the historical A01 failure. The failed run and page are preserved under
`.tmp/e2e-a12-real-managed2`; the next run validates the corrected fixture.

The corrected actual-server browser run exited 0:

```powershell
$env:PYTHONPATH = "$PWD\backend"
.\.tmp\remediation-a04-source\.venv\Scripts\python.exe tests/e2e/critical_path.py --backend-port 8027 --frontend-port 5257 --gpr-report-only --diagnostics-root .tmp/e2e-a12-real-managed3
```

It covers PLS analysis/prediction persistence, exact source snapshot, EN/KO HTML
creation/download, SHA and visible table values, network-offline HTML, report-ID
deep-link restore, and the forced-absent WebCrypto fallback. HTML ten-significant-
digit rounding is checked separately from full-precision stored JSON. Existing
GPR single/compare/settings, chart-formatting, responsive navigation checks in
that focused runner also passed. The user dev server was not stopped or reused.
The parent inspected actual center/offline report screenshots and the mocked
390px layout; this is not a second physical LAN-device test.

Evidence: `.tmp/remediation-a12-real-managed-e2e3.log`,
`.tmp/e2e-a12-real-managed3/screenshots/managed-prediction-*`,
`.tmp/e2e-a12-real-managed3/html/managed-prediction-*.html`.
Mocked four-viewport source-lane testing remains separately recorded. Final
OpenAPI checks passed 231 tests / 2 warnings (`.tmp/a12-openapi-final.log`).

### A12 Native Checkpoint Findings

Feature checkpoint `fa80a22a5b65d2e37e7e43b23830b8d79e695eb5` was dispatched
as CI run `39110538617`. Its Python 3.11 job failed: 6 failed, 1888 passed,
11 skipped, 105 warnings in 203.16 seconds. The failed assertions concern
legacy metadata fixtures: schema-14 pseudo-downgrade retained current indices;
schema-19 upgrade expected version 20; future-schema/read-only tests still
treated version 21 as unsupported/current 20. This is not a passing native gate.
Log: `.tmp/remediation-a12-ci-python311.log`. The dependency-security aggregate
passed for this checkpoint, including the newly pinned browser digest library.

The schema-14 and schema-19 fixtures now create actual migration-prefix DDL,
rather than dropping selected tables from a current database. The latter copies
synthetic stored DOE rows into schema 19 and checks config/result/SHA bytes and
foreign-key integrity after upgrade. The first local correction had an incorrect
constant import and failed collection; corrected use of `SCHEMA_VERSION` passed
both tests (18.68 seconds, 3 deprecation warnings). Logs:
`.tmp/remediation-a12-legacy-migration-correction.log` and
`.tmp/remediation-a12-legacy-migration-correction2.log`. Future-schema tests are
being updated with the A13 migration; all required gates remain pending.

## A13 In Progress: Execution And Completion Ownership

Source inspection confirmed that present analysis routes synchronously return
completed results, including the regularized subprocess runner. A jobs/cancel
endpoint alone does not establish a cancellable executor. A13 makes that
capability explicit, preserves terminal states under cancellation CAS, settles
abandoned nonterminal metadata after acquiring the workspace lease, and batches
history artifact counts. Metadata 22 adds only nullable analysis-run failure
reason storage; statistical results/models are not rewritten. API remains 23.

An adjacent completion race is addressed in the same ownership boundary:
schema mutation may commit before a late analysis INSERT, so an earlier stale
UPDATE cannot mark that new row. Dataset read metadata must be coherent and
completion publication must recheck dependencies inside its own transaction.
The UI must also verify the saved status and current request/source ownership
before presenting completion. This is currently implementation/source evidence,
not a claim that all deferred/browser/database race tests passed.

Local focused checks during A13 (Windows 10 build 19045, CPython 3.10.11,
current locked environment, synthetic temporary workspaces):

```powershell
$env:PYTHONPATH = "$PWD\backend"
.\.tmp\remediation-a04-source\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_workspace_backup.py backend/tests/unit/test_dev_startup_contract.py backend/tests/unit/test_health.py -q
npm --prefix frontend test -- --run src/runtimeCompatibility.test.tsx src/analysisCatalogDisplay.test.tsx src/analysisDomains.test.tsx src/analysisMethodFamilies.test.ts src/sidebarNavigationModel.test.ts
```

The backend selection passed 87 tests / 4 warnings / 267.31 seconds
(`.tmp/remediation-a13-runtime-backup.log`). Exact schema-20/21 archives restore
without migration; normal startup then upgrades to 22. The current schema-22
round-trip, unsupported 19/23 refusal and frontend/PowerShell handshake boundary
are tested separately. The five frontend files passed 26 tests / 7.74 seconds
under Node 22.23.2 (`.tmp/remediation-a13-catalog-runtime-frontend.log`). The
intermediate strict typecheck failed on newly required capability/status fixture
fields; fixtures were updated explicitly without relaxing production types.

Native Linux 3.12 at A12 checkpoint `fa80a22` reproduced the same six outdated
migration-fixture failures as Python 3.11: 1888 passed, 11 skipped, 105 warnings,
306.49 seconds (`.tmp/remediation-a12-ci-linux.log`). Release packaging was skipped
by its dependency gate; it was not validated or published from that checkpoint.

The same checkpoint's Windows hosted job `117625552527` completed with the same
six fixture failures: 1897 passed, 2 skipped, 105 warnings in 2371.23 seconds
(`.tmp/remediation-a12-ci-windows.log`). It was not a timeout. Ruff/format/mypy
passed; the check script stopped at pytest, so its frontend stages and dependent
Windows E2E did not run. No statistical reference failure was reported in this
run. The repaired fixtures require a new native gate rather than relabelling
this checkpoint successful.

Managed-report compatibility after metadata 22 was checked with:

```powershell
.\.tmp\remediation-a04-source\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_managed_report_artifacts.py backend/tests/unit/test_managed_report_api.py -q
```

Result: 32 passed, 1 skipped, 3 warnings, 197.07 seconds
(`.tmp/remediation-a13-managed-migration-regression.log`). The skipped case
requires symbolic-link privileges unavailable to this Windows account; native
Linux validation remains required. This run includes actual report ownership,
legacy DOE BLOB migration, restored managed-report download and source checksum
checks, not just API dispatch mocks.

### A13 Backend Verification

The completion ownership suite ran against actual synthetic PLS/GPR/regression
writers, in addition to storage-level transactions. Command:

```powershell
$env:PYTHONPATH = "$PWD\backend"
.\.tmp\remediation-a03-source\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_analysis_completion_consistency.py backend/tests/unit/test_analysis_completion_writers.py backend/tests/unit/test_dataset_schema_cas.py backend/tests/unit/test_pls_regression_api.py backend/tests/unit/test_gaussian_process_regression_api.py backend/tests/unit/test_regression_workflow_extensions_api.py -q --basetemp=.tmp/a13-completion-related-cases
```

Result: 82 passed / 12 existing warnings / 376.52 seconds
(`.tmp/a13-completion-related.log`). Seven production completion writers pass
captured dependencies into the atomic INSERT boundary. A changed schema marks
the preserved result stale; deleted owners or replaced model identities reject
publication with stable 409 codes and remove only newly created files. This is
not a new universal dependency graph for all dedicated DOE/BO/Phase II work.

Execution lifecycle/metadata/lifespan tests passed 74 cases / 3 warnings /
252.07 seconds (`.tmp/remediation-a13-backend-focused.log`). Additional actual
resource-limit drift, catalog/history/status/cancellation/OpenAPI checks passed
85 cases / 417 deselected / 3 warnings / 50.24 seconds
(`.tmp/remediation-a13-api-contracts.log`). The UI history reason tests passed
4 cases (`.tmp/remediation-a13-history-display.log`). Migration 22 is additive
and transactional; existing immutable artifact bytes remain unchanged.

The root's full OpenAPI/frontend contract selection passed 233 tests / 2 warnings
in 13.00 seconds (`.tmp/remediation-a13-openapi.log`). All-backend Ruff lint and
format checks passed (339 files), and mypy passed all 199 modules
(`.tmp/remediation-a13-mypy-all.log`). These are focused/static checks, not a
substitute for the final Windows/Linux product and release gates.

Independent UI source review found that switching/restoring intent could clear
a previous completed result before a replacement succeeds. The frontend patch
separates pending-request invalidation from successful source/result replacement;
deferred tests and browser checks are being recorded separately. A failed
auxiliary export-list request must not erase a successfully restored result.

The final frontend focused checks passed 195 tests in seven files (7.70 seconds,
`.tmp/a13-focused-final.log`). A new unrelated-owner deletion assertion first
failed before removing App's duplicate global result reset; the dataset hook
already owns exact-source deletion. Its corrected tests distinguish unrelated
deletion from actual current-source deletion. Read-only TypeScript AST comparison
found all 32 analysis request argument constructions unchanged from `fa80a22`;
that is request parity evidence, not an independent numerical reference run.

The root's full frontend run passed 782 tests in 88 files (62.32 seconds,
`.tmp/remediation-a13-frontend-all.log`). Whole frontend lint exited 0 with nine
pre-existing refresh warnings; localization verified 2889 source strings and
4087 translation keys. Production build and the real-server completion browser
stage remain separately gated, not implied by these unit results.

The additional pending-history cancellation regression passed 199 focused tests
and strict types/scoped lint. The next whole frontend run failed one existing
five-route lazy-import test at its unchanged 5-second deadline: 785 passed,
1 failed (`.tmp/remediation-a13-frontend-all-final.log`). Its isolated run passed
3 tests in 4.74 seconds (`.tmp/remediation-a13-lazy-isolated.log`). This does not
prove that the failure was only host contention.

Two unchanged full runs with `npm --prefix frontend test -- --run --maxWorkers=2`
each passed 786 tests / 88 files (78.28 and 77.87 seconds), recorded in
`.tmp/remediation-a13-frontend-bounded.log` and
`.tmp/remediation-a13-frontend-bounded-repeat.log`. Vitest now declares that same
two-worker file-level resource budget for local and CI checks. No assertions,
test deadlines, intra-test concurrent imports, or test files were removed.
This limits transform/memory contention on the 8 GiB reference host; subsequent
native and browser checks remain required.

The first actual-server completion browser run failed at `failed-activation-ko`
after the configuration, dataset A/B/A, cross-tab schema and verification-retry
cases passed. The server returned the intentional 503 and the UI completed its
error state, but the active selector still named the failed target B while the
retained result belonged to A. This is a product mismatch, not a timing-only
assertion: the retry button and selector were enabled before checking their
values. Evidence: `.tmp/remediation-a13-analysis-completion-e2e.log` and the
actual child page's HTML/screenshot/trace under
`.tmp/e2e-a13-analysis-completion/analysis-completion/failed-activation-ko`.
The whole browser run is failed; correcting the selector must preserve the
separate retry target and requires another run in both locales.

`ActiveDatasetVersionSelector` now prefers the committed version when idle,
while keeping the pending identity for retry and for an initial restore without
a committed version. Two new KO/EN regressions first failed on the old code
(`.tmp/a13-selector-red.log`); all 177 focused selector/workflow tests and strict
types then passed. The retry behavior was not removed or disabled.

The unchanged browser assertions then passed all 12 real-server KO/EN cases:

```powershell
$env:PYTHONPATH = "$PWD\backend"
.\.tmp\remediation-a04-source\.venv\Scripts\python.exe tests/e2e/critical_path.py --backend-port 8027 --frontend-port 5257 --analysis-completion-only --diagnostics-root .tmp/e2e-a13-analysis-completion2
```

Exit 0, `.tmp/remediation-a13-analysis-completion-e2e2.log`. Each case compares
the server's immutable result with the genuinely committed, delayed response
and asserts exactly one analysis POST. Cases cover configuration edits, A/B/A
source intent, another editor's schema update, GET-only completion verification
retry, failed source activation and locale/live resize. The failed-activation
completed screenshot was visually inspected: committed source/result retained,
explicit safe error and retry shown. This is local Chromium/Windows evidence;
it is not the full native product or final archive gate.

The default full frontend command, now using the declared two-worker budget,
passed 789 tests / 88 files in 70.51 seconds after the selector correction
(`.tmp/remediation-a13-frontend-default-final.log`). The latest origin/main fetch
still resolved to the original BASE_SHA. No user image or generated diagnostics
are included in the feature checkpoint.

The final A13 production build (including strict TypeScript) exited 0,
`.tmp/remediation-a13-build-final.log`; Vite completed in 4.69 seconds with the
existing >500 kB chunk warning. No chunk threshold was raised to hide it.
