# Saved BO Conditional LOO Diagnostics

## Scope

This document retains the API40 implementation/checkpoint history. The current
API42 integration also supports explicit Auto advice and saved Auto evidence;
see [final delivery ledger](bo_final_validation_20261111.md) and
[evidence contract](bo_auto_evidence_contract.md). The diagnostic math below is
unchanged. A standalone managed LOO-only report is not implemented.

API40 adds an explicit read-only diagnostic for saved numeric planning snapshots1
and mixed planning snapshots2. Metadata remains32; BO method0.15.0, original
model/config/history bytes, checksums and readers are unchanged. Existing scalar
recommendation artifacts are not silently converted into planning models.

The view is requested with both expected model and historical observation hashes:

- `POST /api/v1/bayesian-studies/{study_id}/planning-models/{model_id}/loo`
- `POST /api/v1/bayesian-studies/{study_id}/mixed-planning-models/{model_id}/loo`

Both use `LooRequest` and `LooView` schema1. The service verifies ownership and the
stored source contract before the existing admission-controlled, single-thread,
owned spawn worker restores the model. No source dataset is read and no fit,
recommendation, history append, model rewrite or SQL migration is performed.
The current-history status is rechecked after calculation without replacing the
historical source. A concurrently deleted source fails explicitly.

## Statistical Definition

Policy: `fixed_full_fit_parameters_row_loo_v1`.

Kernel, noise, numerical jitter, response mean/scale and category structure are
fixed at their saved full-fit values. This is conditional row-LOO, not fold-local
preprocessing, full hyperparameter-refit CV, a holdout estimate or external
validation. A category occurring only in the held-out row still has its full-fit
parameters. No new-category generalization claim follows.

For raw standardized observations, construct `K = K_signal + (noise + jitter) I`.
With `alpha = solve(K, y_scaled)` and `q = diag(inverse(K))`, the held-out residual
is `alpha_i / q_i`. The implementation obtains these values with Cholesky solves,
not an explicit matrix inverse. Raw-unit predictions use the saved normalization.
The new API does not report LOO predictive intervals or measurement SD.

Evaluation always leaves out **one actual observed trial**, including when fitting
used exact-repeat compression. All raw observations retained in the saved request
are used, at most200 per response and at most4 responses. Unequal repeat counts
and singleton conditions are not reweighted or averaged for scoring. Other
measurements at the same setting remain in the training information. This is not
leave-one-condition-out or GroupKFold.

`R2 = 1 - PRESS / sum((y - mean(y))**2)`, using all raw observed trials;
negative scores are preserved. Constant observed response returns null R2 with
`constant_observations`. RMSE uses all rows in original response units. Stable
norm ratios avoid squaring tiny values into zero. Nonfinite/unsupported numerical
results fail the whole diagnostic rather than silently excluding difficult rows.
Raw N, effective fitted N, scored N, trial IDs and original order are explicit.

## JMP Alignment And Limits

[JMP BO report](https://www.jmp.com/support/help/en/19.2/jmp/the-bayesian-optimization-report.shtml)
documents per-response LOO R-square. Its
[GP jackknife description](https://www.jmp.com/support/help/en/19.2/jmp/actual-by-predicted-plot-2.shtml)
retains the full-fit correlation parameters. This supports a conditional diagnostic
workflow, but does not establish identical BO normalization, mean treatment or
R-square denominator. The independent formula reference is
[GPML section5.4.2, equation5.12](https://gaussianprocess.org/gpml/chapters/RW5.pdf).

No live JMP fit receipt or LOO output was available for numerical parity here.
The diagnostic alone does not enable Auto augmentation routing or change
acquisition/fitted parameters. The later explicit Auto workflow consumes this
score under its separately documented product policy.

## Display And Export

Both planning screens offer explicit calculation, response-wise R2/RMSE and an
observed-versus-predicted chart with identity line, full-precision details and all
rows. Original response names/units are not translated. KO/EN messages state the
frozen-parameter and repeat-evaluation limits. Model/source changes unmount the
old request lane; late success, failure and finally cannot populate a new source.
Locale and resize do not request another calculation.

The API43 graph follow-up adds a second chart for each response using the same
completed diagnostic: X is its conditional LOO prediction and Y is the stored
raw-unit residual (observed minus that prediction), with a zero reference line.
This is not an in-sample residual, standardized/studentized diagnostic or new
external validation. All raw trial identities remain inspectable. No additional
fit, diagnostic request, schema version or stored model mutation is involved.
The JSON export continues to contain the same completed view, not an invented
managed HTML residual report. Current-run evidence is recorded separately in
[completion validation](bo_completion_validation.md).

JSON download captures only the completed displayed response, including exact
model/config/history and calculation hashes. It is a **local convenience snapshot**,
not a managed Report Center artifact. Users should treat the exported observation
values as potentially sensitive. Nothing is transmitted externally. Managed LOO
HTML/report persistence is not provided as a standalone export. The later Auto
evidence workflow includes its saved diagnostic in that selected-batch report;
other historical reports are not modified or claimed to include it.

## Verification Record

Source confirmed: no BO LOO diagnostic existed in saved planning views before this
change. New tests compare row deletion with an independently assembled Matern
covariance and individual reduced Cholesky solves, not the production prediction
helper. Initial failures included absent module (red), an incorrect trial-ID schema
and a missing worker operation allowlist entry; each was corrected, not bypassed.
Independent read-only review identified concurrent-currentness and underflow
issues, now covered by focused regression tests. The reviewer did not execute tests.

Executed on 2026-11-10 in the separate `fix/bo-search-option-alignment` worktree,
base/HEAD `52f567091aab347f29aec5b8e1f7b6c052b88e3d` plus local changes. Actual host:
Windows10 Home19045, CPython3.10.11, CPU-only, Node24.17.0, Chromium149.0.7827.55.
No Windows11 or Linux execution is inferred. One heavy test/fit suite ran at a
time with BLAS/OpenMP threads capped at1.

| Level | Executed result |
| --- | --- |
| Independent math and source guards | Explicit deleted-row Cholesky, unequal-repeat compression, constant/negative R2, tiny nonzero response, numeric/mixed no-refit snapshot preservation |
| Related backend regression | 233 passed / 1 skipped; includes the new real owned-worker HTTP path, restart, wrong hashes, no writes, and simulated history advance during the worker |
| Skip | Existing static symlink traversal fixture: this Windows account lacks symlink creation permission; not a pass |
| Full frontend | 154 files / 1,380 tests passed, one worker |
| Static/type/build | Backend ruff/format591 files, mypy321 modules; frontend lint/typecheck/build passed. Existing12 Fast Refresh warnings and large-chunk build warnings remain |
| Repository contracts | Localization3005 source strings/4685 keys, capability AST11 tests, generated matrix sync and18 tutorial blocks passed |
| Built numeric workflow | Real fit, LOO, exact JSON, actual plot coordinates, keyboard pin/Escape, KO/EN1024/1440px, A-to-B-to-A delayed success/error/finally, candidate/manual batch/report/restore; no pageerror |
| Built mixed workflow | Real typed-factor fit, LOO, same display/export/locale checks, existing observation/profile/candidate/batch/report/restore workflow; no pageerror |
| Unexecuted | Full backend suite for this checkpoint, all unrelated E2E suites, native Linux/Python3.11/3.12, archive/offline installation, dependency audit, remote CI, live JMP parity |

Browser fixtures are synthetic. Model and history records before/after LOO are
equal; JSON download equals the completed API view. Locale/resize requests do not
fit or calculate again. Numeric source-lane tests create one additional synthetic
saved model through the API, then return to the original; this setup fit is not
misreported as a user action. The existing report tests cover original managed
batch reports, **not a new LOO report**.

After both browser journeys, a real observation PUT completed one pending
synthetic trial in each study. Requests against the original saved model/history
still returned the original calculation hashes, while `source_is_current` became
false in both. The numeric calculation hash remained
`9bce49c66bd5b8f0f37c3a846955b45816fbafd143561a41b7f5f1e421805a1e`;
the mixed calculation hash remained
`c00038f24993b5c894e300e4a19b7fac24498bf5543b3f92d65359a11f682a49`.
This was an additional direct API check on synthetic fixtures, not a claim that
the browser entered those final measurements.

The first numeric browser attempt failed a test assertion requiring a collapsed
source-details hash to be visible. The test now checks the selected model ID and
attached exact hash; the delayed response assertions remain. The rerun passed.
No timeout increase, removed guard, statistical tolerance change or product
visibility change was used to bypass that failure.

Local receipts/screenshots/traces: `%LOCALAPPDATA%\Temp\bo-loo-20261110`, with
`numeric` preserving the first failed run, `numeric-final` the passing rerun and
`mixed` the passing typed-factor workflow. JUnit receipts are adjacent
`bo-loo-20261110-backend.xml` and `bo-loo-20261110-frontend.xml`. These are not
committed and contain synthetic data only.

Reproduction from the worktree root (built server must use a separate synthetic
workspace; these browser commands create synthetic records):

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_loo.py backend/tests/unit/test_bo_loo_api.py backend/tests/unit/test_bo_planning_worker.py backend/tests/unit/test_bo_planning_model.py backend/tests/unit/test_bo_surrogate_snapshot.py backend/tests/unit/test_bo_mixed_snapshot.py backend/tests/unit/test_bo_mixed_planning.py backend/tests/unit/test_bo_mixed_surrogate.py backend/tests/unit/test_runtime_entrypoint_versions.py backend/tests/unit/test_health.py backend/tests/unit/test_web_ui.py -q
npm --prefix frontend run test -- --run --maxWorkers=1
npm --prefix frontend run lint
npm --prefix frontend run build
.\.venv\Scripts\python.exe tests/e2e/bo_persistent_planning.py --base-url http://127.0.0.1:8681 --output "$env:TEMP\bo-loo-numeric"
.\.venv\Scripts\python.exe tests/e2e/bo_mixed_workflow.py --base-url http://127.0.0.1:8681 --output "$env:TEMP\bo-loo-mixed"
```

## Rollback

This local step adds no migration and does not alter saved artifacts. Reverting its
code/API/frontend changes together restores API39, while metadata32 and original
planning models remain intact. Do not remove a workspace, model or result. The
downloaded diagnostic JSON is not an importable model and older UI has no LOO view.
No commit, push, Release, or actual rollback is performed for this checkpoint.
