# BO 500 Capacity

Date: 2026-11-14. Base: `0a4f6ec5fd94217210a7b4ec11b37e611fe667ae`.
Isolated branch: `feat/bo-500-observations`. Synthetic workspaces were used for
testing; the owner-approved local preview was subsequently upgraded after backup.

Follow-up (2026-11-15): API46 supports six desirability responses, with a bounded
24MiB planning transfer/document limit. The original four-response measurements
below remain historical evidence; see `bo_six_responses.md` for new measurements.

## Contract

- Maximum 500 total trials in numeric, multiresponse, mixed and mixture BO.
  Imported measurements plus all later completed/pending/abandoned trials count.
- Raw observations remain distinct, including exact repeats. Explicit filters
  and complete-case policy remain recorded; no automatic sampling or truncation.
- A 240-row import can continue recommending; a 500-row import can be read/fitted
  but cannot append trial 501. A 499-row study cannot partially commit a 2-row batch.
- New UI drafts suggest room for up to 8 further trials, capped at 500; saved
  request budgets remain exact. Users explicitly choose their total budget.
- Shared capacity constants cover import receipts, posterior snapshots, model
  readers, recommendations, candidate/augmentation flows, lifecycle and reports.
- API 44 becomes 45; metadata 37 becomes 38 because existing SQL count constraints
  really require migration. Existing artifact/result/method schemas, numerical
  algorithms and checksum inputs are unchanged. New API errors optionally carry
  only validated aggregate count metadata for `bayesian_import_trial_limit`.

## Resource Boundaries

Exact GP is still CPU-only and cubic in training rows. A 500-row maximum is not a
promise that every 4-response/high-parameter configuration fits every deadline.
Existing thread, time, optimizer restart/evaluation, initial LHS, query chunk and
candidate limits remain. Standalone GPR limits are unrelated and unchanged.
Mixed-kernel gradient preflight uses a conservative memory estimate rather than
silently refusing every matrix over 200 rows. This is not an OS-enforced memory
limit. Saved numeric arrays and JSON remain bounded and validated; no pickle.

## Verification Ledger

| Stage | Evidence/status |
| --- | --- |
| Source confirmed | Import, UI receipt/budget, fit/snapshot and SQL constraints had 200 limits |
| Reproduced | 201-row real import rejected; valid 200 baseline accepted |
| UI RED | 10 capacity assertions failed / 3 passed before UI changes |
| Scalar draft RED | 240-row source still suggested 50 before owner-scoped correction |
| Unit/API | 200/201/240/500 real imports, 501 atomic rejection, mixed/mixture capacity, snapshot and migration tests passed; full suite incomplete at its 90-minute limit |
| Backup/restore | Real 240/500 fit, prediction, report, close, backup and restore: 2 passed in 257.737s; snapshot bytes/hash and predictions unchanged |
| Frontend | Full 182 files / 1,588 tests passed; subsequent localized error regressions: 40 passed; lint and build passed |
| Built UI | Fresh isolated 240-row / 4-X / 2-Y import, recommendation, 241st observation, reload, offline report and atomic 501-row rejection all passed; no page errors |
| Windows | Windows 10 build 19045, Python 3.10.11, Node 24.17, 8 GB RAM; one heavy job at a time, BLAS threads 1 |
| Linux/archive | Not run; Linux release deferred by owner |
| User dataset | Not used as test input; owner-approved preview upgraded after verified backup, with saved files and business-table contents unchanged |

The new `tests/e2e/bo_capacity.py` is connected to the existing workflows suite.
It validates import/preflight, actual desirability fit/review, pending confirmation,
real observation entry, reload, unchanged original rows/hash, managed report and
offline HTML; 501 rejects atomically with localized count and recovery text.

## Catalog Latency Limitation

The existing catalog fully validates each returned Study graph, rather than
trusting unvalidated metadata summaries. Selected-study, saved recommendation,
candidate and planning requests perform their own integrity checks. This policy
is preserved; no GP refit is added to readers and no global unchecked cache is
introduced. See `bayesian_catalog_performance.md` for the existing contract.

During repeated E2E runs in the same synthetic workspace, a catalog containing
three approximately 240-observation studies took 20.370s during concurrent UI
restore requests, exceeding the existing 15s readiness assertion. The server
returned HTTP 200; there were no page errors or failed UI assets. Earlier 240-row
restore/report steps had passed. The timing failure and traces are retained;
timeouts and validation are not weakened. A direct read-only profile subsequently
measured 3.341s for one Study and 9.481s for three Studies. Of the latter, 7.301s
was spent constructing 3,364 identical Pydantic adapters in `_trial_observation`.
The narrow remediation reuses the fixed validation schema, not user values or
results; all row parsing and validation remain. Fourteen adapter regression
tests passed, including malformed values, duplicate keys and fresh output
objects. The same direct profile then measured 0.887s for one Study and 2.320s
for three. On the original accumulated three-Study workspace, built UI readiness
completed in 3.219s and reload in 2.096s, without increasing the readiness timeout.
The subsequent fresh-workspace full capacity E2E passed.
The 500 limit does not guarantee fast browsing of many large study histories.

## Measured Resource Scope

- Public two-response fit journeys: 240 rows 18.450s; 500 rows 40.525s.
  Saved snapshots were 1,762,453 and 6,869,511 bytes respectively.
- The real four-response 500-row worker envelope was 12,355,197 bytes after
  removing an identical duplicated transport snapshot, below the unchanged
  16 MiB limit. The original request and stored artifacts remain unchanged.
- Test-process lifetime peak RSS was 310,145,024 bytes for the two-response
  journey and 367,071,232 bytes for the four-response check. These are not
  aggregate parent-plus-worker memory peaks and are not hard memory guarantees.
- Required plain `mypy backend/app` passed (358 sources), backend Ruff check and
  format check passed (660 files after the adapter regression). An additional stricter-config experiment
  reported 182 diagnostics in 52 files. None overlap newly added lines; the
  stricter baseline was not executed, so this is not called a baseline pass.

## Commands And Test Artifacts

Commands were run from the isolated source worktree using the existing native
Python 3.10 environment; numerical runs used one BLAS thread and no xdist.

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
# $Python is the existing .venv\Scripts\python.exe, not a new environment.
& $Python -m ruff check backend
& $Python -m ruff format --check backend
& $Python -m mypy backend/app
& $Python scripts/render_tutorial_results.py --check
node --test scripts/read_frontend_capability_metadata.test.mjs
& $Python scripts/generate_capability_matrix.py --check
node scripts/check_frontend_localization.mjs
npm --prefix frontend run lint
npm --prefix frontend run test -- --run --maxWorkers=1
npm --prefix frontend run build
& $Python tests/e2e/bo_capacity.py --base-url http://127.0.0.1:8622 `
  --output <external-synthetic-diagnostics> --isolated-workspace
```

Tutorial synchronization: 18 result blocks. Capability AST checks: 11 passed.
Capability matrix synchronization passed. Localization: 3,047 source strings /
4,727 keys. Frontend lint: zero errors, 12 react-refresh warnings. Build includes
successful TypeScript compilation; existing bundle-size/plugin-time warnings
remain. The new E2E file passes Ruff formatting; the legacy `critical_path.py`
has broad existing formatting differences and was not reformatted wholesale.

All screenshots, traces, synthetic workspaces, JUnit and downloaded reports are
outside Git. The first two browser attempts exposed test-only response-ID and
locale-locator assumptions, which were corrected. The third attempt exposed the
catalog delay described above; none of these failed attempts were hidden or
automatically retried. Final receipt: 240 imported, 241 after observation,
unchanged original history, zero page errors, atomic 501 rejection.

The independent reviewer checked source and observed diagnostic artifacts, not
an additional test execution. Linux,
release archive, remote CI and dependency-security jobs were not executed here;
no dependencies were changed.

### Full Native Attempt And Follow-up

The serial full backend command was:

```powershell
& $Python -m pytest backend/tests -q --durations=25 `
  --basetemp <isolated-full-test-directory> `
  --junitxml <external-full-results.xml>
```

The run started at 21:19:22 KST and was stopped at 22:49:23 KST on 2026-11-14,
at a 90-minute local execution cap matching the existing Windows CI time budget.
This is an incomplete run, not a pass. It collected 4,723 tests; the retained
terminal log contains 2,549 completion markers, including eight failures and
four skips, without a finalized JUnit summary. The process and its verified
owned descendants were stopped; no user application process was stopped.

A separate explicit rerun reproduced all eight failures, with 122 other tests
passing in 73.40s:

- Two developer-startup tests failed before port checks because this isolated
  worktree lacked the `.venv` required by `dev.ps1`. Numerical tests had used the
  existing parent checkout environment. A genuine local Python 3.10.11 venv was
  then created, reusing the existing dependency directory through an ignored
  local `.pth` file. No junction, symlink, package upgrade or production bypass
  was introduced. Imports resolve to this worktree and `pip check` passed.
- Six E2E partition tests lacked the new `bo_capacity` stage in their explicit
  order, built-mode and mock-dispatch contracts. The tests now assert that stage
  explicitly, including its isolated-workspace flag and built URL. No production
  stage was removed and no partition assertion weakened. All 97 partition tests
  subsequently passed in 4.81s.

The remaining 13 changed test files were explicitly rerun: **281 passed, one
skipped, zero failures/errors**, in 478.57s. The skip is the Windows account's
inability to create a symlink in `test_static_symlink_outside_dist_rejected`,
not a capacity test. Both previously failing developer-startup cases passed.
Final backend Ruff check and formatting check passed. All eight observed
failures are resolved, but this follow-up does not turn the interrupted full
suite into a complete full-project pass. All failures and reruns remain
recorded outside Git.

## Local Preview Application

The owner explicitly approved updating preview port 8620 after verification.
Only its verified old frontend/API processes were stopped. An offline metadata
37 backup was created and independently verified before startup with schema 38.
The existing data was not used to generate a test recommendation or new Study.

Read-only checks after startup confirmed:

- API contract 45, metadata schema 38 and compatible built UI.
- Served OpenAPI total BO trial maximum is 500; previously it was 200.
- No browser initialization errors; no user screenshots, DOM dumps or traces
  were saved during the real-preview readiness check.
- All 43 business tables retain identical row-content fingerprints, excluding
  the intentionally extended migration ledger. All four stored data assets
  retain their original byte checksums.

The preview is loopback-only at `http://127.0.0.1:8620`. It runs this isolated
worktree's built frontend and backend, not a newly published main commit. The
backup and preservation record are outside Git beside the existing preview
workspace. No user result, model, observation or source dataset was recomputed.

## Compatibility And Rollback

Historical <=200 results are read with original policy/budget/hash. Existing
artifacts are never reserialized for migration. Metadata 38 cannot be opened by
older code; code-only rollback does not reverse this migration. Use the existing
offline backup/restore workflow for an explicitly selected pre-upgrade snapshot.
No rollback, main merge, GitHub push, tag or Linux release was performed. HEAD
remains the recorded base with uncommitted task changes; there is no new final
commit SHA or release checksum to report. Full native suite completion and
remote product/security/archive gates remain outstanding before publication.
