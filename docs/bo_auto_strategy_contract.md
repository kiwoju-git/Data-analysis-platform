# Conditional LOO Auto Strategy Advice

## Scope

This document preserves the API41 advice checkpoint and its tests. API42 now
persists explicitly attached evidence for numeric and mixed selections/batches;
see [evidence contract](bo_auto_evidence_contract.md) and
[final delivery ledger](bo_final_validation_20261111.md). Advice/Apply still never
confirms pending trials automatically.

Local follow-up on `52f567091aab347f29aec5b8e1f7b6c052b88e3d` (HEAD and fetched
origin/main, 2026-11-10). API41 adds read-only advice to numeric and mixed saved
planning models. Metadata32, statistical method versions, snapshots, existing
selection/batch schemas, and historical checksums are unchanged.

This is a decision aid, not automatic batch generation or a persisted Auto
selection. Applying it changes the strategy draft only. Existing candidate
review and atomic confirmation remain separate explicit actions. Existing
manual strategies, including Confirm, remain available.

## Evidence and Policy

[JMP19.2 launch options](https://www.jmp.com/support/help/en/19.2/jmp/launch-the-bayesian-optimization-platform.shtml)
give the model R-square threshold a default of 0.25. The
[official example](https://www.jmp.com/support/help/en/19.2/jmp/example-of-bayesian-optimization.shtml)
describes space-filling when an individual response's LOO R-square is below
the threshold. The
[candidate-set documentation](https://www.jmp.com/support/help/en/19.2/jmp/candidate-set.shtml)
does not specify a complete automatic Refine/Confirm decision rule.

Policy `conditional_loo_any_low_explore_else_refine_v1`:

- Validate all 1-4 response metrics with exact unique response identities.
- Any unavailable R-square blocks advice, even if another is low.
- Any finite R-square strictly below threshold recommends exploration.
- All scores at or above threshold recommend Refine v2. This and the equality
  boundary are product choices, not verified JMP rules.
- Continuous-only exploration uses existing incremental MaxPro; discrete or
  categorical exploration uses explicit mixed maximin, not mixed MaxPro.
- Ordinal rank distance is never enabled implicitly. The existing candidate
  revision's hamming/rank-distance choice remains authoritative.
- Confirm is never inferred from iteration count or goodness of fit.
- Threshold must be numeric, finite, in [0,1], default 0.25. The supported input
  interval is a product constraint, not an asserted JMP limit.

Negative R-square is preserved; averaging/importance weighting cannot mask a
poor response. No refit occurs. Diagnostics reuse conditional individual-trial
LOO with full-fit normalization/kernel/noise/category parameters, not external
validation or new-group CV. See [LOO contract](bo_loo_diagnostic_contract.md).

## Source and Storage

POST routes, requiring expected model/history SHA-256:

```text
/api/v1/bayesian-studies/{study_id}/planning-models/{model_id}/auto-strategy
/api/v1/bayesian-studies/{study_id}/mixed-planning-models/{model_id}/auto-strategy
```

Additional field: `r_squared_threshold`. Calculation reuses the single owned
planning worker and its existing 200-observation/four-response limits.
No dependency or worker concurrency is added.

The schema1 receipt contains the exact LOO diagnostic, threshold, strategy,
reason, warnings, model/config/history identities and a binding digest. The
digest excludes changing currentness so historical calculations retain their
identity. `decision_only=true`, `selection_created=false`; embedded LOO retains
`auto_routing_applied=false`.

Historical sources remain inspectable but cannot be applied. Currentness is
checked after calculation. Apply reads the model and study again: failure,
pending trials, closed study or changed history prevents application. This
read is not a transaction lock; review/confirm CAS remains the final authority
if the workspace advances afterward.

Threshold edits invalidate success/error/finally immediately. Source/model,
candidate revision and selection-draft changes remount the request owner.
Mixed manual row selection/order is included. Locale/viewport never trigger
calculation. Applying advice invalidates the reviewed selection via the
existing controller.

The parent workflow's disabled/busy transition also invalidates advice. A late
Apply GET must not cancel a newly started candidate evaluation through the
parent's draft-invalidation function. The built mixed journey includes this
competing-operation regression in addition to manual selection changes.
Request ownership resets on that transition while the threshold draft is
preserved; changing the actual source/selection context resets both.

JSON download is a local convenience receipt, **not** a managed report.
At the API41 checkpoint, selections stored only the effective strategy. Model-free selection
correctly has `model_id=null` even though advice used a model. Auto receipt
persistence/report attachment was a follow-up, now implemented in the API42
evidence contract. No past artifact is rewritten.

## Verification Record

Synthetic fixtures only; no private JMP data is committed or uploaded.

- Pure-policy red test failed collection before the module existed; 20 passed
  after implementation.
- Real owned-worker HTTP/restart/no-write tests for both source types plus
  pure tests: 22 passed in 75.54 s.
- Frontend focused test initially had a missing `const` in its loop; five
  passed after fixing the test. This was not a product defect.
- A build caught a missing runtime capability TypeScript declaration; the
  client contract and runtime fixture were updated.
- Independent reviewer found mixed manual selection absent from the Auto apply
  source key. Fixed and delayed-GET browser coverage added.
- The first broader backend run had 204 passes and two runtime-info failures:
  the backend `RuntimeCapabilities` DTO lacked the new flag. The DTO was fixed;
  that failed XML and server log remain in the local evidence directory.
- First mixed E2E reached and applied the strategy, but the exact label locator
  did not find the existing strategy select. The accessibility snapshot showed
  the correct combobox/value; the assertion was corrected to use that role and
  accessible name, without extending timeouts or removing the value check.
- The full backend run caught a missing explicit `Origin` in the preceding
  LOO E2E helper's synthetic model-creation request. A focused rerun reproduced
  one failure/two passes. The helper now derives the exact origin with
  `urllib.parse.urlsplit`; the unchanged origin-contract tests passed (3/3).
  No application Host/Origin protection was weakened. The original full-run
  failure is retained, not described as a clean first pass.
- Final source review separated request ownership from the threshold draft:
  competing operations cancel advice without resetting that input. The
  reviewer found no further P1/P2 in this narrow change; browser verification
  is recorded separately below.
- First full frontend run: 1,381 passed / 4 failed (155 files, 151.11 s).
  Two assertions expected the model selector to be hidden for model-free
  strategies; it now remains available for optional Auto diagnostics. Both
  states now assert its accessible name. Model-free selection still requires
  null model provenance and zero prediction evaluations in API/browser tests.
  Two other failures were a stale runtime fixture missing the new capability;
  the fixture was synchronized and an explicit missing-Auto-capability block
  assertion was added. Neither runtime blocking nor source validation was
  relaxed. The initial XML is retained separately from the final run.

### Initial Built UI Evidence

Windows10 Home19045, CPython3.10.11, Chromium149.0.7827.55, CPU-only with BLAS
and OpenMP threads1. The then-current built source UI/API served a new synthetic
workspace on loopback8681. Numeric and mixed journeys passed, pageerrors empty.

- Numeric synthetic response: conditional LOO R2 approximately -1.96327e-9;
  default0.25 proposed MaxPro. Mixed response: R2 0.9995938003220215;
  default0.25 proposed Refine. An explicit threshold1 then exercised the
  mixed-maximin apply/review path; this is not a changed fit or degraded score.
- Both: UI score equals API value; KO/EN at1024/1440; no overflow or extra POST
  on locale/resize; downloaded receipt exactly equals the response.
- Both: threshold A-B-A held success/error responses cannot overwrite a newer
  request or clear its loading state. Historical apply-time GET prevents edits.
- Mixed: a manual row selection during a held Apply GET cancels the prior
  apply; late success cannot change manual selection to augmentation.
- Both: explicit Apply causes only source GET checks, not selection/confirm
  POST. A separate Review saves the selected policy and exact candidate rows;
  model-free provenance stays null; retrieval preserves the same JSON values.
- Subsequent existing manual planning flows confirm batches, restore exact
  sources and produce checksum-verified offline HTML reports. Those reports
  do not include the Auto advice receipt; no managed Auto export is claimed.
- Study and model API receipts are unchanged by advice/apply/review. Screenshots
  were also visually inspected (numeric EN1440, mixed KO1024).

Evidence: `%TEMP%/bo-auto-20261110/numeric` and `mixed-final`; the initial mixed
failure remains under `mixed`. Numeric decision digest:
`75c3b8f66f98756ba7823da79c9d8f68f56237423b49839e9ca2dff18c20aa56`.
Mixed decision digest:
`dbed26ef9a1c8056bb7266a5fee8efe4a3997271008ebff189e1debe7f213b14`.

Reproduction commands (server uses only a separate synthetic workspace):

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_auto_strategy.py backend/tests/unit/test_bo_auto_strategy_api.py -q
.\.venv\Scripts\python.exe tests/e2e/bo_persistent_planning.py --base-url http://127.0.0.1:8681 --output "$env:TEMP/bo-auto-numeric"
.\.venv\Scripts\python.exe tests/e2e/bo_mixed_workflow.py --base-url http://127.0.0.1:8681 --output "$env:TEMP/bo-auto-mixed"
npm --prefix frontend run test -- --run --maxWorkers=1
```

### Final Regression Execution (2026-11-11)

- Full Windows/Python3.10 backend: **4,353 passed, 10 skipped, 1 failed**,
  4,790.66 s. The only failure was the explicit-Origin fixture guard above.
  After correction, its complete file passed (3 tests), then the full run's
  `--lf --last-failed-no-failures none` rerun passed (1 test, 9.02 s). This is
  full coverage plus a focused correction, not a clean second full-suite run.
- Skips: six actual symlink cases require unavailable Windows account privileges;
  four are POSIX pipe frames, Linux symlinked venv, Linux TIME_WAIT, and POSIX
  flock. No privilege elevation, skip modification, or test removal was used.
- Full backend Ruff check/format check passed (596 formatted files), mypy
  passed (324 source files), final frontend typecheck passed. `pip check`,
  generated capability check, localization check, tutorial render check and
  capability AST tests also passed during this turn.
- Evidence XML: `%TEMP%/bo-auto-20261110-backend-full.xml`,
  `bo-auto-20261110-origin.xml`, `bo-auto-20261110-backend-rerun.xml`.
- Final complete frontend rerun: **155 files / 1,385 tests passed**, 149.08 s,
  with one worker. Initial and final XML are respectively
  `%TEMP%/bo-auto-20261110-frontend.xml` and
  `bo-auto-20261110-frontend-final.xml`.
- Final lint: zero errors / 12 pre-existing Fast Refresh warnings. Final
  `npm --prefix frontend run build` passed, including TypeScript; 2,267 modules,
  Vite build 4.37 s. Existing chunk-size/localization-plugin timing warnings
  remain. No warning threshold was increased.
- Existing warnings remain: Starlette deprecations, synthetic duplicate ZIP
  member warning, and unrelated distribution/variance-chart SSR title-child
  warnings. These were not suppressed or fixed through unrelated dependency
  changes.

### Final Built UI Evidence (2026-11-11)

After the threshold/request-owner separation and explicit-Origin correction,
the final production build passed both complete journeys again on Chromium
149.0.7827.55, Windows/Python3.10, separate synthetic workspace, loopback8681:

- `numeric-final`: UI advice/apply/selection, actual model fit, batch confirmation,
  exact-source restoration and offline HTML checks passed; pageerrors empty.
  Auto receipt digest:
  `1ff7deea47e45cb2f11b304abed86aa2c9a332eec517243c5b71ee16419361e9`.
- `mixed-lock-final`: same end-to-end coverage passed, plus delayed Apply GET
  during a new Evaluate-page operation. The late response cannot change manual
  mode or unlock/cancel the new evaluation; threshold `0.4` survives the lock
  transition. Manual-row source changes also invalidate the pending apply.
  Pageerrors empty; Auto receipt digest:
  `b0b616785a969e9b3d1a4adcae6e31a6db7d3a8836219643a19439feca1ba0c6`.
- Both run the KO/EN, 1024/1440, precise score, JSON receipt, late success/error,
  explicit apply, separate review, null model-free provenance and unchanged
  study/model assertions described above. Final numeric KO/EN1024 and mixed
  EN1440 screenshots were visually inspected.
- Evidence remains under `%TEMP%/bo-auto-20261110/`; neither user workspaces nor
  private training documents were used. This is a source build, not an installed
  Linux archive. The final runtime endpoint reports API41/metadata32; its local
  `build_commit=unknown` is not presented as a released binary identity.

Not claimed: exact JMP parity, inferred Confirm policy, permanent Auto receipts,
Linux archive, Python3.11/3.12 native execution, dependency advisory audit,
remote CI, or GitHub push.

## Implementation Map

- `backend/app/statistics/bo_auto_strategy.py::suggest_augmentation`: complete
  response validation and explicit versioned decision policy.
- `backend/app/services/bo_auto_strategy.py::get_auto_strategy`: verified LOO
  reader, currentness check, decision digest; no writes or refit.
- `backend/app/api/v1/schemas/bo_auto_strategy.py` and the existing numeric/mixed
  route modules: typed source-locked request and decision receipt.
- `frontend/src/api/boAutoStrategy.ts`: request, receipt validation and exact
  apply-time model/study checks.
- `BayesianAutoStrategyPanel.tsx`: source-owned draft/request state, localized
  decision display, explicit apply and local JSON download. Existing numeric
  and mixed planning panels supply context and retain review/confirmation.
- `test_bo_auto_strategy*.py`, `BayesianAutoStrategyPanel.test.tsx`, and
  `tests/e2e/bo_auto_strategy.py`: pure policy, real API/worker/restart, frontend
  contract and built-UI race verification. Runtime fixtures and the earlier
  LOO browser helper were synchronized without weakening their guards.

## Rollback Boundary

No commit is created for this checkpoint. Later integration should revert only
its exact commits, newest first, never a broad range. Revert API/runtime/UI
together. No DB migration or artifact conversion exists; do not delete any
workspace/model/history files for rollback.
