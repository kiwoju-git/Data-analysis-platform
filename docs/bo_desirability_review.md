# Stage 3e: Source-Locked Desirability Recommendation

## Scope And Acceptance

Continue the approved JMP-inspired workflow without replacing scalar BO.
This gate connects the existing independently tested desirability calculation
to one-point review, explicit confirmation, measured-vector entry, restart,
exact-source restoration and managed HTML reporting. No GitHub push or Linux
publication is authorized for this gate.

Acceptance:
- Review fits one independent GP per raw response and creates no experiment.
- Confirmation uses precisely the reviewed result, never another fit.
- One atomic transaction creates one pending trial and its recommendation/item.
- Same review ID and configuration retry returns the committed bundle, including
  after cache expiry, concurrent confirmation, response loss or restart.
- Owner, definition, history, source trial count, full model/search configuration and immutable
  source hashes are checked before/after fitting and before confirmation.
  Trial count also locks the novelty/exclusion set: a new subsequently abandoned
  experiment invalidates an older review even though measured history is unchanged.
- Actual observations remain complete response vectors. Predicted response or
  composite desirability is never inserted as an observation.
- Changes to source or settings invalidate success, error and finally handlers.
- Saved result/report readers retain old scalar and vector history contracts.

## Statistical And Resource Boundary

The calculation from Stage 3b is unchanged: public Derringer-Suich linear curves,
importance-weighted geometric desirability, independent raw-response GPs,
Gaussian quadrature moments, posterior-mean incumbent at completed locations,
and moment-matched Beta expected improvement. This is not exact noisy EI/qNEI
or verified JMP numerical parity. Xi is in desirability units, not any response's
physical units. Measurement noise, latent SD, predictive SD and numerical jitter
remain separate. Raw N, unique-condition N and effective training N are stored.

Only q=1 is public for response vectors. Scalar q=1..8 retains its existing
kernel/noise/acquisition policy. Full candidate-set revisions/import/manual
selection, multiresponse batches, linked profilers, JMP augmentation strategies,
nominal/ordinal BO and actual JMP output parity remain later gates.

Existing 1..4 responses, 1..10 numeric/discrete factors, 200 raw trials and the
bounded spawn worker remain. One shared application review semaphore prevents
simultaneous scalar/vector review fits. One cache contains at most eight reviews,
4 MiB per request/result pair, with 20 minute expiry. Confirmation/report/restore
run consistency checks but never fit, CV or regenerate a recommendation.

## Contracts And Migration

- API33 / metadata27.
- BO registry0.9.0; new vector recommendation config4/result4/model5/item3.
- Scalar recommendation method0.7.0/0.8.0 dispatch is unchanged.
- Study5/history2 and measured-vector storage stay unchanged.
- New policy: `independent_latent_desirability_beta_ei_v1`.
- Review schema2 contains a calculation4 and exact source/config identity.
- `POST .../{study_id}/desirability-reviews` creates only transient review.
- `POST .../{study_id}/desirability-reviews/{review_id}/confirm` takes
  `expected_config_sha256`; review ID becomes committed batch ID.
- `GET .../{study_id}/desirability-recommendations/latest` and `/{batch_id}`
  restore exact committed results. Common batch list/read also recognizes v4.
- Runtime capability `bayesian_multiresponse_recommendation=true` means q1;
  `bayesian_multiresponse_batch=false` explicitly excludes q>1.

Migration27 widens existing batch/item CHECK constraints with one exact q1
version/policy tuple. It copies stored rows byte-for-byte; no observations,
definitions, result JSON or checksums are rewritten. Foreign-key relationships
and the atomic owner/CAS/budget writer remain in use. No new report table.

The calculation schema is now in `api/v1/schemas/bo_desirability_calculation.py`;
the old internal import path re-exports its public classes. Numerical validation
stays in the service and the pure statistical engine is unchanged.

Managed BO renderer1.5.0 uses stored vector history and selected batch attachment.
Response names/units and raw-unit predictions are separate from D moments and
Beta EI. Selected-history hashes do not silently advance to latest history.

## Risks And Current Evidence

Statistical risk: Beta approximation and response independence remain explicit.
Privacy: no external calls, telemetry, user workspace fixtures or raw logs.
Compatibility: metadata27 is not readable by older binaries; migrations must
not be reversed by deleting rows or rewriting old checksums.
Performance: no fit during confirm/restore/export; real worker is single-thread
bounded and tests avoid parallel model fits on this machine.

- Reproduced: initial new real HTTP journey returned404 before route wiring.
- Fixed/source-confirmed: versioned review/confirm/read routes, shared bounded
  cache, atomic pending bundle and vector immutable-reader dispatch.
- First real Windows/Python3.10 owned-spawn API journey passed: review without
  trial creation, confirm, repeated confirm, restart, measured response entry
  and unchanged past recommendation checksum. Subsequent expanded tests are
  recorded below once run; this first pass is not full-suite evidence.
- Browser/native evidence is recorded below. Linux/archive publication remains
  intentionally deferred, not implicitly covered by Windows source checks.
- Actual JMP application/output parity: unverified, not installed/provided.

## Current Execution Ledger (2026-11-08)

Base/HEAD: `1db522a12a4023995d52bdcdcf750f9500c47381`, branch
`feat/bo-desirability`. Stage3a..3e remain local, uncommitted changes.
Actual host: Windows10 Home19045, CPython3.10.11, Node24.17.0, Chromium149.0.7827.55;
CPU-only and one heavy validation process at a time. This is not a native
Windows11 or Linux execution claim. All API/browser/backup fixtures are synthetic.

| Boundary | Current execution evidence |
| --- | --- |
| New HTTP lifecycle | 8 tests passed in the focused combined run: real owned spawn review, no-refit confirmation, concurrent replay, transaction rollback, expiry/owner/hash checks, source-count invalidation, restart, exact report and offline backup/restore |
| Related BO/runtime regression, first run | 822 passed / 4 failed / 1 skipped in774.36s. Four failures were OpenAPI union/route fixtures; scalar POST annotation was also narrowed to its actual scalar contract |
| OpenAPI after repair | 241 passed in11.27s. An intermediate rerun retained one stale nullable-union count assertion; it was corrected, not hidden |
| Frontend | Final full single-worker suite:135 files /1189 passed in128.72s; typecheck and lint passed. Lint retains12 existing Fast Refresh warnings. An intermediate1188-pass/1-fail run exposed an old exact-help-copy assertion; it now checks the current actual-measurement and non-guarantee wording |
| Production build/localization | Final build passed;3008 source strings/4688 keys. Existing large-chunk and localization-plugin timing warnings remain. Scoped BO help now states current kernel/noise/q1 multiresponse support instead of the old deterministic fixed-kernel-only boundary |
| Built UI, vector workflow | Goal creation, measured-vector preview/confirmation, incomplete vector rejection, response-loss idempotency, stale error discard, conflict draft retention, exact history restoration passed |
| Built UI, q1 review | Real review/confirm/measurement/reload passed; delayed stale review ignored; committed response loss followed by same-ID explicit retry created no extra trial |
| Locale/layout | KO/EN,1024/1440; same values/source retained and no fit POST on resize/locale. DOM checks cover panel overflow, control height, separate metric label/value rows. Screenshots were inspected; missing existing input/button classes and a narrow long option were corrected and rebuilt/rechecked |
| Scalar built UI regression | q1 target, numeric kernel selection, q2 joint batch, explicit replicate, individual observation, exact aggregation, source restore and managed report paths passed |
| Static/document checks | Ruff check/format, mypy258 modules,18 tutorial blocks,11 capability AST tests and generated capability matrix passed |
| Full backend, first run | 3547 passed /11 failed /10 skipped in3538.41s. All11 failures were stale expected metadata/migration contracts:3 Windows launcher assertions and8 complete migration-list assertions, not numerical output failures |
| Full-backend failure repair | Expected metadata boundary updated to27, explicit migration27 added to expected lists; launcher now also requires the multiresponse recommendation capability. All54 tests across startup contracts, metadata store, runtime entrypoint versions and new q1 API passed in158.19s. The full hour-long suite was not repeated after these fixture/launcher changes; this is focused repair evidence, not a second all-green full run |
| Report Center vector controls | Final built-app journey passed: source selection, exact saved snapshot displayed, HTML creation, actual browser download with checksum verification, report-ID deep-link restoration and offline HTML with stored SVGs. Page errors:0. This supersedes the earlier API-only report creation evidence |
| Remote CI/Linux/archive | Not executed/published, intentionally deferred by owner |
| Dependency audit | No dependencies changed. A new pip/npm advisory audit was not run during this gate; prior audit results are not substituted for current evidence |

Evidence directories are outside Git under `$env:TEMP\bo-stage3e-20261108`:
`browser-complete`, `browser-report-final`, `scalar-browser` and `backend-full.txt`.
They contain synthetic data only. A screenshot alone is not counted as a
numerical or source-identity check. Report Center navigation is not automatic
exact-source selection: the operator selects the desired versioned source there.

Key implementation locations:
- `api/v1/schemas/bo_desirability_calculation.py` and
  `bayesian_desirability_recommendations.py`: typed calculation/review/result contracts.
- `services/bayesian_desirability_recommendations.py`: `_source`,
  `create_desirability_review`, `confirm_desirability_review`, `_commit`,
  `validate_desirability_record`; shared cache in `bayesian_review.py`.
- `storage/metadata.py`: migration27; existing atomic batch writer is reused.
- `dedicated_report_readers.py::_batch_snapshot` and
  `bo_desirability_report.py::desirability_report_section`: exact saved source only.
- `BayesianDesirabilityRecommendationPanel.tsx`, `bayesianDesirabilityDraft.ts`,
  `useBayesianDesirabilityRecommendation.ts`: per-response settings, explicit
  review/confirm, stable source/draft guards and current-versus-saved presentation.
- `api/bayesian.ts` and scalar recommendation hook: typed generic read union
  and explicit vector-result rejection in the scalar renderer.

Saved result validation checks structured identity, moments, configuration and
provenance. It does not re-fit or independently reconstruct a GP posterior during
every GET. Current-trial state is a read-only response overlay; the result hash
belongs to the immutable saved recommendation, not that dynamic overlay.

## Local Commands And Rollback

```powershell
$env:PYTHONPATH = Join-Path $PWD 'backend'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_desirability_review_api.py -q
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test -- --run --maxWorkers=1
npm --prefix frontend run build
node scripts/check_frontend_localization.mjs
.\.venv\Scripts\python.exe tests/e2e/bo_vector_history.py --base-url http://127.0.0.1:8676 --output "$env:TEMP\bo-stage3e-browser"
.\.venv\Scripts\python.exe tests/e2e/bo_desirability_review.py --base-url http://127.0.0.1:8676 --output "$env:TEMP\bo-stage3e-report"
.\.venv\Scripts\python.exe -m pytest backend/tests -q --durations=25
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_dev_startup_contract.py backend/tests/unit/test_metadata_store.py backend/tests/unit/test_bo_desirability_review_api.py backend/tests/unit/test_runtime_entrypoint_versions.py -q -ra
.\.venv\Scripts\python.exe -m ruff check backend tests/e2e/bo_desirability_review.py tests/e2e/bo_vector_history.py
.\.venv\Scripts\python.exe -m ruff format --check backend tests/e2e/bo_desirability_review.py tests/e2e/bo_vector_history.py
.\.venv\Scripts\python.exe -m mypy backend/app
.\.venv\Scripts\python.exe scripts/render_tutorial_results.py --check
.\.venv\Scripts\python.exe scripts/generate_capability_matrix.py --check
git diff --check
```

Changes remain local/uncommitted by instruction. After an eventual feature
commit, revert only that feature's commits newest-first, not a broad range.
Code revert does not undo metadata27 or new v4 recommendations. Use a verified
offline backup made before upgrading when running an older binary, restoring
to a new empty location; do not delete workspace/trials/models/results. No
rollback is executed without an explicit request.
