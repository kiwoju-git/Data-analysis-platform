# BO Fit Quality Gate

Status: implemented locally with the scoped validation recorded below. This
gate follows the workshop audit; it is not the completion of JMP alignment.
No push or Linux publication is requested.

## Acceptance And Boundaries

- Opt-in `bounded_multiscale_starts_v1` for the desirability ordered-review path,
  q1..8. Scalar BO and request/config/result4/5 retain their original fit behavior.
- Screen nine deterministic length-scale starts, including the existing initial
  vector. Refine the best explicitly requested one through three starts, plus
  the existing separately counted seeded random restarts. Do not redefine the
  old restart count or increase any time/evaluation/thread limit implicitly.
- Count screening and local evaluations in the same response-wide fit budget.
  Retain the best evaluated feasible finite point, not only the solver's final
  point. Budget failure remains failure, not partial batch success.
- Record initialization, screened likelihoods, local starts, selected point,
  termination and parameter-bound diagnostics. These are fit diagnostics, not
  LOO/external predictive validation or a global optimum certificate.
- Expose policy selection and saved-source diagnostic tables/charts in KO/EN,
  review, restoration and no-refit HTML. Preserve original UI tokens/charts.
- New request/config/result6, aggregate model6, raw response model5, method0.11.0;
  item4 unchanged. API35, metadata29 only for the new persisted tuple CHECK.
  Preserve study/history contracts and original artifact bytes/hashes.
- Synthetic reference/API/browser fixtures; workshop samples remain private.

## Risks

Different starts can change statistical results, so this is an explicit new
policy, not a silent update to saved or legacy computations. Likelihoods are
comparable only within the same response/data/normalization/kernel policy.
Screening has nonzero CPU cost and cannot bypass the existing fit budget.
Bound hits do not by themselves prove failure or overfitting. Diagnostics must
not expose raw training rows in logs or support reports. Old and new schema
dispatch, backup and atomic confirmation require regression coverage.

Desirability curves, historical-table import, Auto/MaxPro, profiler, nominal and
mixture BO remain subsequent gates. No JMP runtime parity is claimed.

## Evidence

Tests and review outcomes are appended as they execute; prior-stage passes are
not evidence for this change.

- New narrow calculation/kernel set:58 passed after the initial red collection
  test and a duplicated floating midpoint were corrected. This is an earlier
  checkpoint, not the final total.
- Connected BO calculation/API/legacy suite:182 passed in435.20s, including
  real spawn workers, review/confirmation, partial observations, restore and
  prior request4/5 contracts.
- Independent runtime/health/OpenAPI/metadata/startup run:297 passed in189.91s.
  Migration28->29 preserves old row JSON/hash/owner bytes and accepts only the
  new coherent version tuple. Initial startup hardcoded28 assertions failed
  before their current-version expectations were corrected.
- Frontend first full run:1220 passed/1 failed (stale API34 runtime fixture).
  Corrected fixture; final single-worker full run:137 files/1221 passed in204.62s.
- Full mypy passed266 source files. Frontend build and lint passed (12 existing
  Fast Refresh warnings); localization checked3008 strings/4688 keys.
- Final narrow rerun after provenance-roundoff and HTML-dispatch fixes:26 passed
  in50.76s. Includes raw and unequal-count compressed independent LML,
  intermediate-best retention, bounded roundoff matching, tamper rejection,
  real worker save/restore/no-refit report and atomic budget failure.
- Browser red1: a new select's implicit accessible name included its options;
  added explicit label association. Browser red2: schema6 was missing from
  `bo_noise_report_section` dispatch, so the saved HTML omitted the diagnostic
  section. The source-only helper test did not catch this; a dispatch regression
  and full offline-browser check now cover it. Failure traces are preserved.
- Independent review found a missing selected-start receipt link and a possible
  cross-OS regenerated-number exact-comparison risk; both were addressed.
  The latter was a source-confirmed risk, not a reproduced Linux failure.
- Final extended focused set:102 passed in50.90s, including deterministic
  start counts1/2/3 plus two separately counted seeded random restarts and the
  existing E2E suite partition checks. This overlaps the earlier26-test set.
- Built Chromium149.0.7827.55: new-policy q1 and q2 passed actual UI review,
  stale-response rejection, whole-batch confirm, lost-response explicit replay,
  measured-vector entry, exact restore, managed-report download and offline
  HTML. KO/EN at1024/1440 retained Korean user-owned names and issued no new fit
  on locale/resize. Page errors were empty. Numeric cells were compared with
  stored API values; layout used DOM geometry plus screenshots.
- Browser red3 was a test locator selecting the hidden SVG `title` before the
  visible table header; scoped it to the header and reran the complete journey.
  This was not another application rendering failure.
- After stopping/restarting only the owned8678 server, q2 restore retained
  result SHA256 `7f778a33b0d38ef3dcd4f1fa9bb5a54830bcb86b93dfe2caa43c8082b5ac9efa`
  and exact best-visited likelihoods, with zero mutation/refit requests.
  The downloaded offline HTML SHA256 was
  `771d27d29cc26ab364570f91c81c29973ced08543cf41ec7222f8075d5dc3c37`.
- The preserved q1 legacy desirability journey passed separately. The scalar
  BO built-UI journey also passed target/q1, joint batch, actual observations,
  explicit replicates, exact aggregation(raw9/effective7), numeric kernel
  selection, restore, KO/EN resize and managed report. These are new runs,
  not the prior Stage3h results.
- The integrated vector-history context helper then passed stored-history and
  response-entry checks followed sequentially by legacy q1, legacy q2 and
  new-policy q2 journeys. Its first attempt failed an obsolete Stage3e notice
  expectation; the test now asserts the actual whole-batch/no-write semantics.
  No application wording or behavior was changed to satisfy that assertion.
  Separate diagnostic screenshots at1024/1440 in KO/EN were inspected.
- Final mypy passed266 files. Capability matrix check,11 capability metadata
  AST tests,18 tutorial result blocks and localization verification passed.
  An added test needed Ruff formatting; it was formatted without a logic change.
- Complete backend run: **3699 passed / 2 failed / 10 skipped**,140 warnings,
  4296.38s. The failures were current-version assertions in
  `test_bo_kernel_api.py::test_populated_metadata24_migration_preserves_legacy_hashes`
  and `test_rsm_plot_storage.py::test_schema22_upgrade_preserves_all_existing_doe_asset_bytes_and_hashes`:
  both expected28 after a valid migration to29. Only those two expected values
  were corrected; original schema22/24 inputs, exact bytes/hashes, foreign keys,
  restoration and post-migration operations remain asserted. This first full
  run remains a nonzero result, not a clean pass.
- The full process started before the final report-dispatch/provenance-roundoff
  corrections and three additional start-count tests. The later focused runs
  and built-browser journeys exercise those final changes; they do not change
  the identity or outcome of the earlier full process.
- The ten skips are explicit: six Windows symlink-privilege limitations and
  four POSIX/Linux-only cases (stream pipe framing, symlinked venv, TCP TIME_WAIT,
  flock). They were not treated as passes. Existing deprecation warnings and
  the intentionally duplicated ZIP-entry fixture warning were not suppressed.
- Final correction run: **60 passed**,4 warnings,in211.29s. It reran the entire
  `test_bo_kernel_api.py` and `test_rsm_plot_storage.py` files, both previously
  failing migration tests through their remaining hash/operation assertions,
  the new migration29 tests, real-worker fit API/report and all fit-policy tests.
  No calculation, data-preservation assertion or numeric tolerance was changed
  for those two failures. The71-minute full suite was not rerun after this
  test-only correction; its original2-failure outcome remains above.
- Final Ruff check passed and format check covered504 backend/E2E files.
  The final read-only independent review found no additional P1/P2 in the
  regenerated-number/receipt validation, schema6 report dispatch or capability
  claims. This review did not run Linux/JMP or replace the executed tests.

## Execution Environment And Commands

Native Windows10 Home10.0.19045, CPython3.10.11,8GiB-class RAM, CPU-only.
The installed environment is not claimed to be Windows11. NumPy2.2.6,
SciPy1.15.3 and scikit-learn1.7.2 are unchanged. One full backend test process
and one browser at a time were used, with BLAS/OpenMP threads1 and frontend
tests limited to one worker. An independent reviewer was used without parallel
fit workloads. All workspaces, browser traces, HTML and private workshop probes
are outside Git. The built UI uses a separate synthetic workspace on8678.

Representative executed PowerShell commands, from this worktree:

```powershell
$env:PYTHONPATH=(Resolve-Path .\backend).Path
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_fit_policy.py backend/tests/unit/test_bo_fit_quality_api.py backend/tests/unit/test_e2e_suite_partition.py -q --tb=short
.\.venv\Scripts\python.exe -m pytest backend/tests -q --durations=25 --tb=short --junitxml="$env:TEMP\bo-fit-quality-20261109\backend-full.xml"
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_kernel_api.py backend/tests/unit/test_rsm_plot_storage.py backend/tests/unit/test_bo_fit_quality_metadata_migration.py backend/tests/unit/test_bo_fit_quality_api.py backend/tests/unit/test_bo_fit_policy.py -q --tb=short --durations=8 --junitxml="$env:TEMP\bo-fit-quality-20261109\final-corrections.xml"
.\.venv\Scripts\python.exe -m mypy backend/app
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe scripts/generate_capability_matrix.py --check
.\.venv\Scripts\python.exe scripts/render_tutorial_results.py --check
node --test scripts/read_frontend_capability_metadata.test.mjs
node scripts/check_frontend_localization.mjs
npm --prefix frontend run test -- --run --maxWorkers=1
npm --prefix frontend run lint
npm --prefix frontend run build
.\.venv\Scripts\python.exe tests/e2e/bo_desirability_review.py --base-url http://127.0.0.1:8678 --batch-size 2 --fit-quality --output "$env:TEMP\bo-fit-quality-20261109\browser-q2-final-verified"
```

Linux/Python3.11/3.12, Windows11 native CI, dependency advisory refresh,
release-ready, offline archive installation and actual JMP execution are not
verified by this local gate. No dependency changed. No Linux archive or Release
was built/published, as requested. q8 new-policy UI, browser zoom and native
cross-platform stored-fit replay are unverified; existing API/numerical coverage
must not be relabeled as those browser/platform tests.

## Calculation And Storage Contract

The nine screens keep the original signal amplitude and specified noise initial
value, and vary all numeric length scales together through nine evenly spaced
log-bound fractions. The old unit-scale initial vector is first; its numerically
identical midpoint is deduplicated. This is not an exhaustive ARD parameter grid.
The top one to three screens (NLL then stable index) are refined using the same
L-BFGS-B bounds, tolerances and iteration cap. Seeded random restarts remain a
separate zero-to-three setting. All evaluations, including screening, consume
the shared response-model evaluation budget; no limit is silently increased.

Every local start records its initial LML, terminal solver state and best visited
point/evaluation index. The selected point may be an intermediate evaluation or
an unrefined screening point. Source validation binds the selection to that
saved receipt, checks parameter bounds and the regenerated start plan, and
does not recompute likelihood or fit. This is consistency/integrity checking,
not a cryptographic certificate against an administrator rewriting all files.
Regenerated log-space numbers allow only16 machine-epsilon times max(1,abs(x));
raw bound values allow16 epsilon times their magnitude. Same-artifact receipt
links remain exact. This is a serialization/platform arithmetic allowance, not
a relaxed statistical reference tolerance. Native cross-OS replay is unverified.

The existing latent/predictive distinction, raw-unit noise SD, ddof0 response
normalization, jitter, EI/MC/Beta policy, candidate search, trial limits and
atomic whole-batch confirmation are unchanged. New optimizer choices can change
fitted hyperparameters and recommendations; original policy remains selectable.
Stored old results are not recomputed or supplemented with invented diagnostics.

Migration29 rebuilds only the recommendation-batch CHECK constraint, retaining
old table rows and hashes. The new version tuple is method0.11.0/config6/result6/
aggregate-model6/item4. The per-response model is schema5. The study/history
contracts remain unchanged. API35 adds `bayesian_fit_quality`. New BO HTML
exports use renderer1.7.0; existing export bytes are not overwritten.

## Workshop Comparison

Private read-only probes motivated the bounded multiscale policy. Sample-specific
inputs, predictions and comparison numbers remain in a local evidence copy and
are excluded from publication. Synthetic independent Cholesky and best-evaluation
tests above provide the redistributable regression evidence. Improved fitted
likelihood is not a claim of globally better prediction or JMP numerical parity.
See the [public workshop summary](jmp_workshop_public_findings.md).

## Files And Compatibility

- `bo_fit_policy.py` owns screening and best-evaluation retention;
  `bo_surrogate.py::fit_bo_surrogate` opts in without changing legacy fitting.
- `bo_fit_quality.py`, public desirability schemas, batch core/worker and
  `bo_fit_quality_contract.py` carry and validate the new immutable contract.
- `BayesianFitDiagnostics.tsx` uses the existing keyboard/pin/tooltip scatter
  chart and a full-precision table. The plot compares starts, not iterations.
- `bo_fit_quality_report.py` renders those same stored start values in offline
  inline SVG/tables. It never accesses raw observations or refits.
- `bayesianDesirabilityDraft.ts` preserves string drafts and validates explicit
  starts/restarts; the existing request context invalidates stale reviews.

## Rollback Boundary

Worktree branch `feat/bo-desirability`, unchanged HEAD
`1db522a12a4023995d52bdcdcf750f9500c47381`. The gate is uncommitted and sits on
pre-existing local Stage3h changes, which were preserved. A diff against HEAD
contains multiple local stages and must not be represented as only this gate.

No commit, push, Release or rollback is performed in this gate. After eventual
commits, revert only this gate's commits in reverse order, preserving earlier
BO work. A code revert does not downgrade metadata29 or convert result6 into
result4/5. An older binary requires a verified pre-upgrade offline backup restored
to a new empty destination. Never delete a workspace/model/history to roll back.
