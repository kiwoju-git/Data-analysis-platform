# BO Completion Gates

Owner scope confirmed2026-11-10: continue through persistent candidate tables,
manual ordered selection, profiler, explicit augmentation and nominal/ordinal BO,
then integrate into main after validation. Linux publication remains deferred.
BASE_SHA and fetched origin/main: `1db522a12a4023995d52bdcdcf750f9500c47381`.

## Acceptance

1. Finish the current stored-target-curve regression checkpoint (API37/meta30).
2. Persist a bounded, versioned fitted-state snapshot and candidate-set revisions.
   Generate/import complete candidate rows, evaluate manual conditions and
   conditional profiles without refitting, paginate the comparison table,
   preserve ordered selection, and re-evaluate conditional scores after edits.
   Confirm all selected trials atomically, idempotently and against exact source
   history/model/candidate hashes. Restore and report that exact saved selection.
3. Add separately named space-filling, model-refinement and optimum-confirmation
   policies with explicit criteria, budgets, tie breaks and reason traces.
   Keep existing MC EI available; never relabel it as a different strategy.
4. Add nominal/ordinal factor identities, explicit correlation policy, executable
   level selection, safe fitted-state restoration, profiles, observations and
   reports. Category codes cannot enter a numeric distance implicitly. Validate
   PSD/gradients and category-renaming invariance independently.
5. Review source/privacy/backward compatibility, run narrow through full native
   and browser checks, then commit and run the existing remote product gates
   before normal main integration. No force push or release-gate weakening.

## Work Boundaries

The current review cache is transient and is not a candidate repository.
Current shared-model metadata alone is not reusable fitted state. New state must
be bounded JSON/numeric arrays with explicit constructors, no pickle or refit.
Immutable original studies, histories, results and old schema/hash readers remain.
One heavy computation suite at a time; one implementation agent and one read-only
review agent at most alongside the orchestrator. Agent tests require an explicit
compute slot. No user workspace is used for validation.

Risks: conditional batch scores become invalid on reorder/subset edits; source
mutation during fitting or confirmation; category encoding as distance; optimizer
budgets and large candidate tables; SQLite migration/retention/backup ownership;
accidentally publishing supplied workshop data. Each gate must close these risks
with specific tests before it is advertised as available.

Private workshop originals, extracted rows, screenshots and derived numeric
comparison ledgers remain local, outside the commit allowlist. The public
summary is `jmp_workshop_public_findings.md`. Public documentation establishes
workflow meaning, not recovered proprietary optimizer behavior or numeric parity.

## Earlier Checkpoints

- Stored Gaussian target policy: focused math/API/built-browser checks passed.
  Full checkpoint: 3,766 passed, 9 failed, 10 skipped. Eight failures asserted
  the old report-renderer version and one asserted the old sklearn module
  allowlist. Expectations updated; current rerun remains required. This is not
  a full-suite pass or evidence for the newer planning integration.
- Persistent candidate/profiler gate: backend wired; 30 focused storage,
  migration, worker, model and real API tests passed on Windows/Python3.10.11.
  Includes exact confirm/replay, stored reports and offline workspace restore.
  Exact saved-view frontend integration and built-browser validation subsequently
  passed on Chromium149.0.7827.55: one fit, candidate pagination/order/undo,
  profiler mean/latent/predictive values, source-locked confirmation, exact URL
  restore, KO/EN1024/1440, managed report checksum and offline HTML. The first
  browser attempt found an ambiguous profiler label; explicit aria-labels fixed
  it. No analysis POST occurred on locale/viewport changes. This is built-app
  evidence, not a release archive test.
- Follow-up native check: 63 passed (metadata upgrades, runtime/health,
  PowerShell launcher contract, legacy kernel artifact hashes, exact planning
  report descriptor, catalog without loading GP arrays, backup/restore and
  explicit closed-study deletion including two reports). Backend mypy passed
  for 287 source files. These precede the later augmentation adapter.
- Pure snapshot/candidate/augmentation/category-core checkpoint: 249 tests
  passed. A later discrete canonical-coordinate review fix needs its own rerun.
  Core tests do not establish complete categorical or augmentation workflows.
- Augmentation: source-owned candidate schema2 and metadata31-to32 migration
  preserve old JSON bytes. Three real API tests passed after confirmation storage
  was extended to schema9. Bounded receipt validation:36 passed; existing pure
  augmentation/view/candidate/planning:118 passed. A real fitted-model API journey
  passed Refine v2 and Confirm, exact confirmation, actual observations, en/ko
  reports with output SHA-256 and immutable source checks, and offline workspace
  backup/restore. Initial test attempts requested three Confirm rows without
  enough competitive candidates and used an invalid synthetic row index; those
  failures were not production fallback changes. Augmentation frontend checkpoint:
  66 tests in eight files, TypeScript and targeted ESLint passed. Built-browser
  and full-suite checks for this gate remain pending.
- Nominal/ordinal: mixed surrogate/snapshot regression263 passed, mixed study
  source28 and existing numeric/vector58 passed. API lifecycle, planning and UI
  integration are in progress; these core checks are not workflow completion.
  Later mixed API model/candidate/profiler and snapshot regression:35 passed.
  The first API attempt exposed strict equality between saved log parameters
  and reconstructed `log(exp(theta))` (delta2.77555756e-17). The reader now allows
  only scale-aware codec roundoff, retaining hash/likelihood checks. No fitted
  value, numerical reference tolerance or optimizer setting was changed.
  Mixed ordered-selection plus numeric MC regression:89 passed; mixed kernel
  and snapshot checkpoint:189 passed. Atomic confirmation/report and final UI
  remain separate unverified gates at this checkpoint.
- Main integration: pending all gates. No new commit/push/release yet.

### Integrated Mixed Workflow Checkpoint

- Runtime contract39 / metadata32 / BO method0.15.0. Numeric augmentation
  is batch9; typed mixed planning is batch10. Old JSON/hash readers remain.
- Mixed worker/contracts and numeric MC regression:138 passed using the
  worktree Python3.10 environment. Real mixed API:3 passed, including ordered
  q2 confirmation/replay, partial actual measurements, stored en/ko HTML,
  restart, q8 atomic rollback/retry and tamper rejection.
- A source review found historical mixed reports depended on the current
  whole-study loader. The exact historical reader now resolves only the saved
  source and its dependencies. New API/report regression:1 passed; existing
  mixed batch API:3 passed again. This was source-confirmed before correction,
  not a recorded pre-fix runtime reproduction.
- A later runtime/migration/numeric-vector checkpoint was173 passed/1 failed.
  The failure expected mixed planning to remain permanently unavailable. That
  obsolete expectation was corrected only after the fixed-candidate workflow
  was implemented; a final rerun is still required.
- New built-app scripts `bo_augmentation.py` and `bo_mixed_workflow.py` are
  connected to the existing context suite. At this checkpoint they are authored,
  not yet executed. No browser or archive pass is inferred from API tests.
- Final source review found no additional confirmed P1/P2 in the inspected
  owner/hash/CAS/atomic retention boundaries. This does not substitute for the
  remaining complete native, browser and remote CI gates.

### Final Integration Validation In Progress

Native environment: Windows10 Home19045, CPython3.10.11, single-thread BLAS,
Chromium149.0.7827.55. These are synthetic isolated workspaces, not user data.
The final source uses API39/metadata32/BO0.15.0 and report renderer1.10.0.

- Full frontend after the label fixes:153 files/1,356 tests passed in153.22s
  with one worker. After the final marker fix:153 files/1,357 tests passed in
  147.92s. Full ESLint:0 errors and12 existing fast-refresh
  warnings; localization:3,005 strings/4,685 keys; TypeScript/build passed.
- Backend mypy:318 source files passed. Final Ruff checks passed; format-check
  passed for588 backend and newly integrated browser-script files.
- Final E2E-registration/runtime/dependency-boundary tests:82 passed in10.79s.
  The first run was81 passed/1 failed because two new mixed statistical modules
  were absent from the explicit sklearn reference allowlist. After verifying
  their worker-only use, the list was updated; the separate subprocess assertion
  that application startup does not import sklearn remained and passed.
- A focused backend run was111 passed/1 failed in213.43s. The failing historical
  metadata24 migration test expected31 instead of32; its legacy payload/hash
  assertions had passed. The expected version was corrected, not the old bytes.
  The focused rerun passed14 tests in190.44s, including mixed Refine/Confirm
  without refitting, original legacy hashes, backup/restore and explicit deletion
  of a closed synthetic study with its planning dependencies and reports.
- Mixed built-app journey passed: explicit UI mixed study creation and invalid
  input rejection; actual response entry; one fit;60 candidates/page2; ordered
  manual selection/undo; nominal Profiler values; atomic q2 confirmation; exact
  URL restore; KO/EN at1024/1440; managed HTML SHA-256/offline opening. Study
  history stayed unchanged during planning and locale/resize caused no writes.
  The first attempt exposed a real POST/PUT mismatch for mixed observations;
  the next exposed missing explicit select names. Both failures were retained,
  fixed and regression-tested. No numerical tolerance was widened.
- Separate augmentation's first built-browser attempt reached the candidate
  page but failed the exact select-name check. The final build adds explicit
  accessible labels; component red4/green26 passed. Its subsequent actual
  built-browser journey passed: independent60-row table, paging, mixed-maximin
  selection, confirmation, exact restore, KO/EN and verified offline HTML.
- The first complete integrated run reached mixed-model fitting, then its test
  watcher captured a catalog GET instead of the same-URL POST. The watcher now
  matches HTTP method and URL. This was a test synchronization failure, not an
  inferred fitting failure. An independent review found no additional confirmed
  same-endpoint ambiguity in the other connected BO scripts.
- The corrected complete `bo_vector_history.py` run exited0. It exercised
  vector creation/input/conflict/replay, q1/q2 review and measured entry,
  fit-quality receipts, target-curve preview and stored q1/q2 curves, persistent
  candidates/manual order/Profiler, separate augmentation and mixed planning.
  All journeys retained empty pageerror lists and checked exact report checksums.
  Nominal and ordinal profile points retained their typed levels and raw values.
- Subsequent screenshot inspection found mixed Profiler endpoint markers partly
  clipped by exact min/max domains. A geometry regression failed before the
  existing padded-range helper was connected; its green file has5 tests. Only
  display bounds changed, not points/model data. The full frontend rerun passed
  as recorded above. The final rebuilt mixed browser journey also exited0,
  including actual marker/clip bounding boxes, typed ordinal points, one fit,
  unchanged source history, exact batch restore and offline report SHA-256.
  Screenshot inspection confirmed complete endpoint markers after the fix.
- Fresh npm runtime/development audits and pip check passed. Remote native
  Python/security/archive gates have not yet run for a final commit.
- Independent publication review found an outdated README fractional-selection
  statement; it now distinguishes regular-fraction support from PB limitations.
  No additional confirmed P1/P2 or private-fixture production import was found
  in the inspected paths. This source review is not execution evidence.

Private workshop ledgers are excluded locally and are not tracked. The original
training material, supplied sample rows and sample-specific derived comparisons
are not part of the public change. This local pre-commit checkpoint does not
claim remote CI or main integration; those are tied to the resulting source
commit's GitHub checks. Linux Release publication remains explicitly deferred.

Representative executed commands (browser URLs must point to an isolated
synthetic workspace; never run these write journeys against a user workspace):

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_mixed_batches_api.py backend/tests/unit/test_bo_kernel_api.py -q --durations=5
npm --prefix frontend run test -- --run --maxWorkers=1 --no-file-parallelism
node scripts/check_frontend_localization.mjs
npm --prefix frontend run lint
npm --prefix frontend run build
.\.venv\Scripts\python.exe tests/e2e/bo_vector_history.py --base-url $SyntheticPreviewUrl --output $SyntheticDiagnostics
```

The existing remote CI runs the full native product checks on the committed
source, including Windows browser partitions, Linux/Python3.11, dependency
security, GP resource checks and offline archive verification. Its final status
must be read from the resulting commit/PR checks, not inferred from this
pre-commit local ledger. CI archive artifacts are not GitHub Release publication.

The owner explicitly requested all of these remaining gates, not only a release
of the current target-curve checkpoint. Do not mark this plan complete while
candidate/profiler/augmentation/category work is still missing.

## Upgrade and Rollback Boundary

Stop the application before an offline backup. Keep the archive outside the
workspace and keep the original workspace intact. Example PowerShell commands
use operator-selected paths, not a developer or test workspace:

```powershell
.\.venv\Scripts\python.exe scripts\backup_workspace.py --workspace $Workspace --output $BackupArchive
.\.venv\Scripts\python.exe scripts\restore_workspace.py --archive $BackupArchive --workspace $NewEmptyWorkspace
```

Take the pre-upgrade backup with the previously installed compatible code.
The integration migrates existing metadata25 through32 and preserves stored
legacy payload bytes. A metadata32 backup is not a downgrade to25. Old code
cannot read the new planning/mixed schemas or open the newer database simply
because its files were restored. To run old code, restore the verified
pre-upgrade backup to a separate empty destination; retain the newer workspace.

The final delivery identifies the exact new commits. Revert only those commits,
newest first, using ordinary `git revert <exact-commit>` and normal push after
verification. Do not use a broad range containing other contributors' work,
`reset --hard`, force push, or workspace/model/result deletion. Frontend/API39
and the backend request contracts form one compatible unit; an arbitrary
UI-only rollback across API versions is not supported. No rollback is performed
without an explicit owner request. Linux Release/tag/assets remain unchanged.
