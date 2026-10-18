# Remediation Journey Matrix

This is the test contract for T01-T18, not a claim that every journey has passed
on the current commit. Executed commands, failures and platform-specific results
are recorded in [the remediation ledger](end_to_end_remediation.md). Final CI and
archive evidence must identify the exact tested source and archive digest.

## Shared Evidence Rules

- Every fixture is synthetic and uses an owned temporary workspace. Never run
  destructive or request-limit fixtures against the user's development server.
- Browser assertions check actual state, values and requests. A class name or
  screenshot alone does not establish correctness.
- `diagnosed_page` records the actual failing child context: URL, locale,
  viewport, shell/runtime state, page errors, failed asset requests, DOM,
  screenshot and trace. Parent critical-path diagnostics do not replace these.
- State-only hook tests use deferred promises; API/storage tests use real local
  SQLite/files. Route-stub browser tests prove UI behavior, not server storage.
  Real-server suites are named separately below.
- Result equality, persisted source hashes and downloaded-byte SHA-256 are
  distinct evidence. Hashing a reserialized inner JSON value is not an immutable
  artifact-file checksum. Do not label the former as the latter.
- A failed run remains failed after a correction. Record the rerun separately.
  Skipped, cancelled, not run and source-inspected are not passed.

## Intake and Current Source

| Journey | Synthetic fixture and expected state | API / forbidden changes | File evidence and implementation |
|---|---|---|---|
| T01 CSV to analysis | Small numeric CSV, explicit parsing/header and schema; select returned version ID; analysis belongs to its source/schema | Upload, confirm parsing, schema CAS if edited, one analysis POST. No selection by option index or silent source substitution | Raw-upload/canonical hashes and saved analysis provenance; `critical_path.py` upload/parser/schema/analysis stages, backend upload and schema CAS tests |
| T02 Paste/header | Tabular pasted text, change header configuration, confirm immutable version | Intake draft is separate from active dataset. A late paste response cannot reactivate a superseded draft; no hidden resubmission | `dataset_context.py` paste-clear/paste-replacement real-server cases compare uploaded bytes/hash and retained catalog owner; critical-path parser stages cover header meaning |
| T03 XLSX and paths | Multi-sheet XLSX plus UTF-8/CP949 CSV; synthetic Korean/space/long local paths | Explicit sheet/encoding selection; rejection must not erase previous active work | `critical_path.py` XLSX/sheet/encoding stages; upload/API and workspace backup long-path tests. Browser display labels do not prove filesystem path compatibility |
| T04 Source change during input | A/B datasets; delayed upload/parsing/schema responses and cancelled dirty switch | New source intent invalidates old success/catch/finally. Failed activation retains A and its result; B remains a retry target, not the active selector value | `dataset_context.py`, `analysis_completion.py`, `asyncHookState.test.ts`; real-server evidence preserves server-created A artifacts, current B context and raw/canonical hashes |
| T05 Concurrent schema | Two editors start from one schema hash; browser cases change unit/display name, backend cases also exercise schema roles | First PATCH succeeds, second returns 409 `dataset_schema_conflict`; no automatic expected-hash replacement or partial writes; explicit compare/apply/discard | `schema_concurrency.py` real-server KO/EN cases and `test_dataset_schema_cas.py`; source/canonical/result hashes unchanged, only successful dependent stale transition |
| T06 Cell correction race | A correction commits while B is selected; late failure/finally variants | Child version remains in catalog but cannot reactivate A or end B's loading. Parent canonical data is immutable | `dataset_context.py` cell case verifies actual child and parent hashes; deferred hook tests cover callback ordering |

## Prediction, Reports and Display

| Journey | Synthetic fixture and expected state | API / forbidden changes | File evidence and implementation |
|---|---|---|---|
| T07 GPR prediction race | Saved synthetic GP; delayed predictions, input/row/model changes, reversed rows, duplicate/missing/foreign IDs | Snapshot model/hash/input before POST; match `client_row_id`; reject stale success/error/finally; locale/resize cannot predict | `gp_prediction_context.py` actual models plus controlled response delivery; `gpPredictionContext` tests. JSON snapshot unavailable after input changes; model payload/manifest remain unchanged |
| T08 Restored prediction | Existing OLS/PLS/GP model and exact manifest; reload then predict identical rows | Use validated saved model reader, never refit; differentiate mean/latent/new-observation quantities | Regression-model/prediction API tests, critical-path model flows and archive restart journey. Compare original/restored means and uncertainties at documented tolerance and verify manifest hashes |
| T09 Report Center state | Open A result, change method/status/stale/page filters, no current dataset, invalid/deleted owner | List requests cannot trigger detail refetch or clear accepted result; null current-dataset filter makes no all-dataset request; only confirmed deletion clears owner | `report_center_context.py` controlled browser request-count evidence plus `asyncHookState.test.ts`; server report API tests separately verify ownership/hash. Stubs alone do not prove deletion lifecycle |
| T10 Report completeness | Stored variants/schemas with full, summary, unsupported and not-applicable sections; long labels, >100 points, all PLS loadings, GP surfaces | Read saved result only. Fit/CV/raw-row reads are forbidden. Capability and rendered body agree; no invented CI/VIP/OOF | Renderer parity tests inspect visible tables/SVG and escaping, not embedded JSON. `managed_reports_live.py` verifies real saved prediction reports, downloaded-byte hashes and offline body; report tests preserve source/model checksums |
| T11 Owner deletion | Synthetic analyses/models/reports with dependencies and a last-page owner | Preflight/cascade is exact-owner; unrelated deletions cannot clear current analysis. Old list/detail responses cannot restore a deleted owner | Managed report retention/workspace API tests and critical-path deletion stages compare metadata/files and download status. Deferred hook tests plus the actual Report Center with mocked transport verify last-page deletion, fallback to offset 0, URL preservation and no detail refetch; this fixture is not filesystem deletion evidence |
| T12 Locale/storage | Getter/getItem/setItem failures; KO/EN cold starts, persisted locale, slow/failed JS chunk | App ready comes from mounted shell/runtime/locale/route, not networkidle. In-memory locale survives failed storage; user data and request bytes unchanged | `startup_readiness.py`, `refined_ui.py`, `app_readiness.py`, locale/transport tests; actual child diagnostics. Dev `/src/App.tsx` interception is not an archive chunk test. Fixing storage exception alone does not prove the cause of the historic Windows E2E failure |
| T13 Resize/chart | One loaded result, 1920 through narrow desktop and back; chart formatter/pin/component selections | No analysis/prediction API call; data coordinates and input/dataset unchanged; wide layout releases drawer focus trap | `desktop_resize.py`, result-chart and formatter browser stages; true browser-zoom checks are separate from deviceScaleFactor. Screenshots support, not replace, DOM/value/request assertions |

## Workspace and Release

| Journey | Synthetic fixture and expected state | API / forbidden changes | File evidence and implementation |
|---|---|---|---|
| T14 Exclusive workspace | Two real processes, same canonical workspace with different ports; independent workspaces; crash/restart | Second same-workspace process fails before migration/recovery. No PID-based process kill or deleting live lock file | `test_workspace_lease.py`, `test_workspace_lifespan.py`, `test_workspace_server_lease.py`; OS-owned descriptor lock and file preservation. Native Windows/Linux both required |
| T15 Backup/restore | Closed synthetic workspace with dataset, analysis, model, reports; restore to a new path | CLI acquires lease, validates referenced files and DB; never overwrite existing destination or alter original; malicious small archives refused | `test_workspace_backup.py` and managed-report backup tests verify manifests, byte hashes, DB rows, reopen/download and Korean/space paths. Schema migration happens only at later normal startup |
| T16 Mixed installation | Missing/wrong marker, old venv/new web, changed package build identity, damaged wheelhouse, successful reinstall | Release-owned guard must run before installed application import; refuse inconsistent identity without server startup or workspace mutation | A15 release identity tests and native archive smoke are required. Existing payload checksum tests alone do not verify installed application identity |
| T17 Offline Linux | Final tar.gz extracted to fresh folder without Git/Node, new venv, installation network blocked, external synthetic workspace | Install only hashed wheelhouse; execute data input, analysis, direct prediction, save/restore/report, restart, second installation with same external workspace | `verify_linux_release.py` + `tests/e2e/linux_release.py`; archive/installed-code identity, runtime source/API/schema, persisted result/model/report hashes. API-only fitting smoke must not be described as a complete UI journey |
| T18 Publication | Final source and version/tag, exact previously validated archive | All required jobs success, not skipped/cancelled/pending; no existing tag overwrite; normal main push; same archive bytes uploaded | `release-ready` and publication evidence must name Windows/E2E/Linux/3.11/security/archive results, tag target and downloaded Release SHA-256. CI artifact availability is not a published Release |

## Status Ownership

T16-T18 remain incomplete until A15 and the final aggregate gate execute. Earlier
successful native checkpoints verify their recorded source only. A13's initial
actual-server completion run exposed a failed-activation selector mismatch; its
diagnostics and subsequent correction/rerun belong in the remediation ledger.

This matrix does not silently broaden statistical support, weaken assertions,
or convert an absent test into a success. The capability generator establishes
declaration consistency; it is not evidence that these journeys ran.

Independent source review also distinguishes combined evidence from a single
end-to-end assertion: T01's parser/schema stages do not by themselves prove every
request count and hash in one journey; T03's long backup path is not a long-path
browser upload; T07's model manifest reference is not a fresh model-file hash
check; T13's synthetic drawer fixture is separate from actual PCA resize; T15's
managed report backup fixture covers LHS/BO/factorial/pasted prediction, not every
completed GP/PLS snapshot variant. These boundaries must remain explicit in the
final verification report unless further executed tests close them.
