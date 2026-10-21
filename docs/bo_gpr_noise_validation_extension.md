# Noise-aware BO and GPR Extension

## Baseline and Acceptance

BASE_SHA: `3284a359c31ccfb738ddf16078440f674d52f42f`.
Branch: `feat/noise-aware-bo-gpr`; isolated worktree. The untracked
`examples/image2.png` in the original checkout is untouched. `data_prd.md`
does not exist. AGENTS, current addendum, module guide and relevant method,
storage/runtime contracts take precedence over historical to-do entries.

Implement A through L in the owner's order. Acceptance requires independent
posterior/LML/acquisition checks, exact replicate lifecycle and provenance,
deterministic joint-latent batch search, mixed executable coordinates,
fold-local group/time/category processing, immutable legacy model readers,
resource enforcement and measurements, and the actual UI/API/report/archive
journeys. API26 is the integrated contract. Metadata24 is an additive migration
for explicit replicate provenance and versioned BO batch records. No main push or publication with
an unresolved required gate.

Risks: physical noise versus numerical jitter; latent versus predictive
uncertainty; loss of within-replicate variation; post-selection uncertainty;
time/lag information leakage; unknown categories; repeated-query covariance
memory; source/request races; old checksum/version meanings; worker cleanup.
BO keeps ddof0 and standalone GPR keeps ddof1. Neither policy imports defaults
from the other. No new ML framework, external service or data transfer.

## Progress and Evidence

| Stage | Implementation | Verification |
| --- | --- | --- |
| A BO surrogate/noise | Implemented core/API/UI | Independent Cholesky, noise/jitter, optimizer/gradient and native BO browser stage passed |
| B Incumbent/single target | Implemented V2 core and versioned wrappers | q1 analytic/direction/target and actual API passed |
| C Exact replicate view/lifecycle | Implemented sufficient statistics and atomic explicit replication | Unequal counts/LML/gradient, API retry/restore/close/delete passed |
| D Joint-latent MC batch | Implemented V2; legacy V1 reader retained | Joint integration, fixed samples, xi, near-singular covariance passed |
| E Mixed acquisition search | Implemented executable-level search | 18 new tests; 33 including legacy calculations passed |
| F Group CV | Implemented backend/UI | Full group identity, disjoint groups, API and actual Linux browser form/save/restore passed |
| G Time/lag | Implemented backend/UI | Warm-up null, shared plans, explicit lag prediction, embargo and native browser journey passed |
| H Categorical GP | Implemented pure layer/backend/UI | Pure checks, mixed fit/restore API and actual browser prediction passed |
| I Surface views | Existing selectors extended; explicit saved request view | Complete-grid validation, managed report and native applied-view browser checks passed |
| J Extended exact resources | Admission estimator, owned spawn worker, chunk prediction | Clean Windows/Linux matrices each passed 27 fit/restore/prediction cases and rejected 9 at admission |
| K Integration/UI/report/legacy | Implemented; final rerun in progress | Python3.11 2994 passed; prior full Linux/Windows runs exposed failures preserved below |
| L Native CI/main/prerelease | Pending final gates | No main push or new Release yet; exact-archive journeys strengthened but not yet executed |

The prior release's test counts are not evidence for this work. Append actual
commands, failures and corrected runs as each stage completes. Synthetic-only
test workspaces remain separate from user data. Actual JMP numeric parity is
unverified; see `jmp_gp_bo_alignment.md`.

## BO Computation and Storage

- `bo_surrogate.py` fits the signal and observation-noise variance separately.
  Estimate mode starts at 0.01 scaled variance with bounds 1e-6 to 1. Fixed
  mode accepts raw response SD. Near-noiseless mode has zero physical noise.
  Jitter remains numerical only and is excluded from future observation SD.
- Latent posterior uses the signal cross-covariance and stored Cholesky factor.
  Predictive variance minus latent variance equals physical measurement variance.
  The model stores direction-normalized mean/scale and its direction multiplier,
  while the observation view retains the raw-response mean/scale. Both use ddof0.
  It also records kernel components, bounds, optimizer
  traces, physical SD and both raw/effective training counts.
- Directional EI uses the best posterior mean at completed locations. Target
  improvement fits the original response and uses its standardized target.
  Observed best and latent incumbent have separate provenance and labels.
- Exact compression uses raw-observation normalization, group means, counts and
  within-group SS. Its marginal likelihood includes the full within-group
  correction. Nearby complete-link diagnostics never change training rows.
  The raw 200-observation budget is checked before aggregation. The minimum
  unique-condition count is the product policy `max(2, factor_count + 1)`.
  The UI does not collect a separate process/time-state identity for a trial.
  Exact compression therefore assumes that identical coordinates within one
  study describe the same homoscedastic condition. Distinct process states must
  be represented by the study/factors rather than silently treated as repeats.
- V2 batch policy is `greedy_mc_joint_latent_improvement_v2`, not qNEI. A real
  model is fitted once; correlated latent selected-point draws condition each
  candidate's analytic marginal EI/ETI. Defaults: 64 draws, range 16-256.
  q1 is analytic. Common draws and SHA-derived seeds are fixed per step.
  Displayed mean/SD always come from the real-data posterior.
- Acquisition budget counts a candidate or up to 64 conditional samples as one
  unit; larger sample settings charge `ceil(samples/64)` units after q1.
  Raw evaluations and conditional sample evaluations are recorded separately.
- Mixed search fixes exact discrete levels and optimizes only continuous
  coordinates. Small discrete spaces are enumerated; larger spaces use a
  bounded seeded/neighborhood search. Final canonical coordinates are rescored.
  No global-optimum or guaranteed-distance claim is made.
- New batch config/result/item schemas are 2; surrogate model schema is 3;
  recommendation method version is 0.7.0. Legacy calculation wrappers retain
  their old policy unless a new schema/policy is explicitly requested.

## Replicate Lifecycle and Migration

`POST /api/v1/bayesian-studies/{study_id}/trials/{trial_id}/replicates`
requires a completed parent, current history ID/hash, UUID request ID, explicit
intent, count 1-8 and total trial budget. Each child is a separate pending trial
with `origin=replicate` and a parent ID. Pending trials block another synchronous
recommendation/replicate bundle. Observations remain one actual value per trial.

One SQLite transaction checks the source, pending state and budget, then creates
the whole bundle. The same request ID/payload returns the same trial IDs; reuse
with different content is a conflict. No automatic POST retry is introduced.

Migration24 rebuilds constrained BO tables transactionally, preserves existing
records, adds the parent relationship and an idempotency/provenance table, and
checks foreign keys before commit. Legacy coordinate hashes omit the new field;
replicate hashes include it. Populated schema23 migration was tested with an
existing V1 batch: study/batch restoration and JSON file checksums are unchanged.
Close/delete preflight counts the new request records and removes the exact graph.
Backup/restore now admits exact metadata24 and verifies replicate-request JSON
hashes. The first current-schema backup test failed because the explicit version
allowlist still ended at23; after extension, 73 backup/replicate tests passed,
including schema20..23 restoration and a populated repeat graph's idempotent retry.

## GPR Validation, Categories and Resources

See `gp_validation_extension_evidence.md` and `gp_mixed_kernel_evidence.md` for
fixtures and independently checked formulas. Group CV evaluates unseen groups;
time CV evaluates later time blocks. Lag evaluation is one-step rolling with
previously observed outcomes, not fixed-origin recursive forecasting. Warm-up
rows have null OOF values and are excluded from every scored metric denominator.

Mixed kernels use category equality, not numeric distance. Training-fold
vocabulary/scaling is independent of validation data. Unknown categories fail
explicitly. Nominal profiles are discrete and numeric surfaces require two
numeric predictors. Model manifest/result4 readers retain numeric legacy1-3.

`standard_exact` remains 500 rows; explicit `extended_exact` permits up to 2,000
only when the 512MiB estimate admits the exact configuration. The estimator
includes fold sizes, kernel parameters/gradient temporaries, retained candidates,
restarts/refits, chunked prediction and result transfer. Some valid 2,000-row
configurations are intentionally rejected. No rows/options are silently reduced.
This is admission control, not an OS-enforced memory limit.

Extended work runs in an owned spawn process, with a deadline including startup.
The parent drains bounded IPC before joining. Numeric state travels in a hashed,
bounded temporary NPZ, loaded without pickle; timeout/cancellation cleans only
the owned child/files. The public method still does not advertise universal
interactive cancellation. Prediction chunks are limited to 256 rows.

Custom surface saves use the existing completed-prediction artifact and managed
report ownership. The request carries applied numeric axes, exact held values,
grid size and mean/latent-SD/predictive-SD mode. The server validates the complete
grid. Export renders that saved view without predicting, fitting or reading rows.

## Current Execution Evidence

Local environment: Windows 10 build19045, CPython3.10.11, CPU-only, NumPy2.2.6,
SciPy1.15.3, scikit-learn1.7.2. This is not Windows11 device verification.
Commands use the installed Python with `PYTHONPATH` pointing at this isolated
worktree; no baseline environment's editable code is used accidentally.

Narrow executed suites (counts overlap; do not sum as unique coverage):

- BO baseline: 76 passed; GPR baseline: 71 calculation/reference and 32 API/report.
- BO surrogate: 23 passed; observation view: 38 passed; acquisition/batch: 39 passed.
- BO core + acquisition/batch: 46 passed; V2 API: 19 passed; wrapper/legacy/Branin: 21 passed.
- F/G existing plus new backend checks: 123 passed, then 24 expanded new tests passed.
- GP category/preprocessing: 29 passed. Mixed backend/API and extended 501-row
  spawn/restore checks are recorded in their dedicated evidence files.
- `pytest ...test_gp_resource_budget.py`: 15 passed.
- `pytest ...test_gp_worker.py`: 7 passed, including actual owned-spawn timeout.
- `pytest ...test_gp_extension_report.py ...test_gp_surface_views.py
  ...test_completed_predictions.py ...test_gaussian_process_report_contract.py`:
  28 passed, 3 existing Starlette deprecation warnings.
- BO target report/replicate/lifecycle + GP report/view/worker combined:35 passed.
- Backup/restore and populated replicate retry:73 passed.
- Frontend BO hooks/presentation:206 passed; GP settings/snapshot/model/panel/hooks:
  237 passed (overlapping suites). Targeted ESLint and full TypeScript checks passed.
- Release gate tests: initial3 failures for missing native resource admission;
  after adding Windows3.10/Linux3.12 `gp-resources` as a required gate,59 passed.

The local resource benchmark runs concurrently with development checks and is
diagnostic evidence, not an isolated performance baseline. Native CI runs the
same501/1000/2000 synthetic configuration matrix in its own job. Admission
rejection and successful fit/restore are different statuses. Worker and parent
RSS peaks are measured separately; their sum is not claimed as a simultaneous peak.
Final source CI and exact-archive evidence remain pending until recorded below.

Commit-candidate checks: backend Ruff passed;427 backend files passed format
check; whole backend mypy passed235 source files. Frontend lint passed with12
existing Fast Refresh warnings; production build passed with the existing large
bundle warning. The first full frontend run was966 passed/1 failed: the old
batch UI test still required the obsolete mean-fantasy explanation. Its corrected
policy assertions passed in the5-test targeted suite; this is not recorded as a
fresh full-suite pass. Capability/migration/release-gate checks:102 passed.

Independent audit red/green corrections: minimize normalized-mean sign in the
V2 storage validator (2 failures to4 API passes including response rescaling),
overflow of finite fixed-noise SD before the explicit error boundary, valid
GroupKFold with folds equal to distinct rows/groups, and terminal-state
idempotent replicate replay in the UI. See `bo_noise_audit_evidence.md`.

Worker/resource audit:35 passed, including a marker-confirmed running spawned
child terminated on deadline, bounded NPZ headers and post-serialization peak
receipt. An actual2000-row/12-predictor request was rejected by memory admission
with unchanged source checksums and no partial analysis/model/artifact/NPZ.
The64MiB estimator baseline is an allowance, not verified total imported-process
RSS; the512MiB estimate is not an OS RSS cap. Native measurements are required.

Local concurrent-load benchmark progress: all12 configurations at501 and1000
rows passed. At2000 rows, numeric single-kernel row/group CV hit the180-second
budget; time CV passed. These failures are retained and require isolated native
validation, not a relaxed timeout or an unconditional2000-row support claim.

Failures are retained as evidence: missing-module red tests preceded new modules;
replicate pending state initially did not block recommendations and was corrected;
schema23 fixture initially hit an open SQLite file on Windows, then was rebuilt
in a separate fixture workspace; GP manifest4 initially entered an OLS schema4
validator and was corrected with method-specific dispatch. Native benchmark
startup first exposed an incomplete capability-unit enum update; no performance
result is claimed from that failed run.

Full source checks, browser journeys, native CI, performance matrix, exact Linux
archive installation/restart and publication remain pending at this record point.

## First Native CI Follow-up

Branch run39613148814 used1c178d33444d185625418f5bb71270d39d1aa1df.
It is not a passing release gate. Linux type checking found a Windows ctypes
attribute boundary; Python3.11 completed2939 tests with20 failures and13 skips.
Failures exposed outdated explicit migration/table/OpenAPI/tutorial/report
expectations. The unchanged legacy tutorial still exercises BO0.6, not the new
noise-aware0.7 policy, and must retain its actual method identity.
Updated metadata/managed-report fixtures passed45 tests with1 existing skip;
previous migration/checksum assertions remain. No stored artifact was rewritten.

Early browser diagnostics stopped at a stale GP Generate selector and an absent
Origin header in the synthetic BO setup request. The product Host/Origin guard
was retained. Named action selection and exact-origin fixture requests have
focused regressions; browser re-execution is still required. Early diagnostic
CI now also runs the prediction suite while all normal product gates remain.

The new mixed-kernel import initially broke the lightweight startup contract.
Loading the sklearn-based class only at fit/read execution boundaries restores
that contract; the actual fresh-process startup regression remains enabled.
Security failures and exact native lock remediation are recorded separately in
`bo_gpr_security_followup.md`; no audit exception was added.

## Resource and Browser Follow-up

The first Linux resource matrix passed 30 fit/restore/prediction cases and rejected
six 2000-row mixed requests at admission. The first Windows matrix exceeded its
unchanged outer deadline at a 1000-row comparison case; its stage was not recorded
by that older supervisor. Neither result establishes all-platform performance.

The estimate is now `exact_gp_peak_v2`, with measured worker allowance, separate
fit/transfer phases, a comparison allocator reserve and training-diagnostic query
costs. The 512 MiB budget is unchanged. Some 2000-row numeric single-kernel
settings pass admission, while the benchmark's mixed/comparison settings do not.
`gp_resource_benchmark_contract.md` records the formula, calibration, original
failed measurements and source-provenance requirements. The old concurrent local
run is diagnostic only, not evidence for its ending commit. A native rerun of the
new estimate is required.

Early Linux browser run39616780776 completed the BO context suite and the new BO
workflow stage. The complete workflows suite and GPR prediction suite still
failed on ambiguous or missing accessible select names. These are separately
tracked browser failures, not passing product or release gates. The detailed BO
assertions and retained diagnostics are in `bo_frontend_noise_evidence.md`.

## Prepublication Checkpoint

At source `6fe0b509a726a43be340450b4f0faf47a3ec5927`, native run39619608275
passed Python3.11 (2994 tests, 13 skips), all runtime/dev dependency audits,
the Linux context/prediction browser suites and both clean resource matrices.
The browser evidence includes real group/time/lag form execution, mixed model
restore/manual prediction and an applied latent-SD surface with categorical hold.
It is not a full passing CI run: Linux stopped at 91 missing localization
registrations, and workflows found 84px overflow in the BO settings at 390px.
Those failures were fixed without altering statistical values, request bodies,
translations or suppressing page overflow. The superseded run was explicitly
cancelled during its Windows job; that job is not recorded as passed.

Source `16fbaf3447622c4ab1f2ae602000aab7107038ac` is under full native
re-execution in run39622753726. Its source also strengthens the exact Linux
archive verifier: BO/GP identities and checksums must survive two restarts,
another installation using the same external workspace, managed report reopen
and offline HTML inspection. See `bo_gpr_archive_roundtrip_contract.md`.
Unit tests of this verifier are not evidence that an archive has passed it.

That source passed the context/prediction browser jobs, including settled layout
bounds at 1024/1440px in both languages. A fresh full frontend run passed 977
tests across 113 files. The new BO managed-report journey then exposed a fixture
problem: its context init script forced Korean on every navigation, overriding
the explicit English choice before the report deep-link assertion. Actual child
trace/DOM showed a mounted compatible application, successful report POST and
download, and no page errors or failed assets. Only the BO fixture now seeds
the locale when absent and additionally verifies English persistence on reload;
the product LocaleProvider and shared forced-locale fixture behavior are unchanged.
This corrected journey still requires native re-execution.

The new V2 noisy mixed q2 benchmark is a bounded characterization, not a claim
that the new policy always improves regret or beats another product. Its MC
sample-stability, objective/constraint/reproducibility results and the initially
failed arbitrary 50-percent improvement criterion are retained in
`bo_noise_policy_benchmark.md`. The legacy Branin test remains legacy-policy
evidence; it is not repurposed as proof of V2 performance superiority.

The initial Windows native run39613148814 completed with 2949 passes, 20
failures and 3 skips. The same obsolete explicit version/fixture expectations
were corrected before the passing Python3.11 rerun. A concurrent local full
backend run finished with 2921 passes, 27 failures and 9 skips while source
changed; it is diagnostic only, not final-source evidence. Current narrow
reruns passed the affected legacy BO, owned-worker and 501-row API tests without
increasing their deadlines. Two local startup failures used an external venv
instead of the expected worktree venv; native setup remains the release gate.

Final publication evidence belongs to the Release validation asset, so recording
the final source SHA does not require a self-referential source commit. Until
that exact-source aggregate gate and archive verification pass, the intended
2026.10.6 tag and README commands are a publication target, not a release claim.
