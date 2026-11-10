# Stored Target-Curve Recommendation Gate

Date: 2026-11-10. Worktree `feat/bo-desirability`, HEAD
`1db522a12a4023995d52bdcdcf750f9500c47381`. Earlier uncommitted stages remain intact.
Commit, push and Linux release remain deferred by the owner.

## Acceptance and Risks

Connect explicit peak-one Gaussian target curves to the real immutable study,
q1/q2-q8 review, atomic confirmation, actual response entry, restore and report.
Existing DS-linear curves remain the default; maximize/minimize are unchanged.
No preview assumptions become GP predictions or recommendation inputs.

Statistical risk: apply importance before exponentiation of Gaussian tails;
the unweighted value can underflow while its weighted payoff is representable.
Use the same curve dispatch for observed payoff, incumbent, marginal and
conditional moments, and sampled batch payoff. Beta moment matching and
independent response posteriors remain approximations, not exact joint EI or
JMP numerical equivalence. Preserve CPU/time/moment budgets and spawn admission.

Compatibility risk: old DS objects must not acquire new fields/defaults during
serialization. New study6 requires at least one explicit Gaussian target;
legacy study5 accepts old request4/5/6, new study6 accepts request7 only.
Schema mismatch is an error, never a downgrade. User workspaces/data and private
JMP training files are not modified or copied into fixtures.

## Contracts

- API37, BO method0.12.0; new study6 with existing vector history2.
- Request/config/result7, review5, shared model7, unchanged item4.
- Raw GP model4 or5 remains governed by optional fit policy, not curve choice.
- `curve_policy=per_response_target_gaussian_or_ds_v1`; each Gaussian target
  carries policy and explicit left/right ordinates in (0,1), with implicit peak1.
- Immutable study controls are copied into result objective. No refit at
  confirmation, reopen or report generation.
- Metadata30 adds only the new valid recommendation tuple to the batch CHECK.
  Existing rows, JSON bytes/hashes and foreign-key ownership are preserved.
- Bayesian HTML renderer1.8.0 includes saved per-response controls and policy.

Public target-control workflow reference:
[JMP target desirability controls](https://www.jmp.com/support/help/en/19.2/jmp/how-to-use-the-desirability-function.shtml).
The formula audit and explicit non-parity boundary remain in
`jmp_workshop_public_findings.md` and `bo_target_curve_preview_gate.md`.

## Current Verification Ledger

This ledger records only this gate; earlier successes are not current evidence.

- New red test: GaussianTargetGoal import did not exist.
- Math regression: 85 passed before additional extreme-weight test.
- New core tests: 7 passed, including independent quadrature, weighted tails,
  q1/first-batch candidate equality and unchanged input definition.
- Initial API integration caught circular import and missing study6 history2
  dispatch. Fixed without relaxing integrity validation.
- Initial API/owned-worker synthetic lifecycle: 1 passed, q2 review/confirm replay,
  partial actual observation, restart, common batch GET, static report and
  immutable JSON/hash comparison. This initial pass did not cover the managed endpoint.
- Broad focused run: 300 passed/7 failed because OpenAPI union expectations
  omitted the new types. Updated expectations plus explicit strict curve fields;
  the subsequent math/API/migration/OpenAPI/suite-partition run passed363 tests.
- One read-only agent reviewed direction/contracts and flagged weighted-decay
  and composite-product underflow plus an absorbing DS-zero ordering edge.
  Added explicit precision errors and all24 response permutations for the exact
  zero case. No statistical tolerance was increased. Review is not runtime evidence.
- Managed report red test returned409: `read_bayesian` still excluded study6.
  Extended the versioned guard, preserving exact-history checks. A subsequent
  test failed because the report-only no-current-source mock remained active
  during restart; scoped that test guard without changing product readers.
- Frontend full run: 139 files/1247 tests passed,163.51s, one worker. After the
  final scoped control styling,29 targeted tests passed. Typecheck/build passed.
- Ruff lint and format passed (512 backend files); mypy passed271 sources.
  Localization checked3005 source strings/4685 keys;11 capability AST tests,
  capability matrix and18 tutorial result blocks passed. Lint has zero errors
  and12 existing fast-refresh warnings; build retains its large-chunk warning.
- Built Chromium149.0.7827.55: legacy DS vector creation, q1/q2, opt-in fit quality,
  preview, and new Gaussian study creation/q1/q2-fit passed. KO/EN1024/1440,
  stale response, lost response/idempotent retry, reverse partial actual entry,
  exact restore, Report Center create/download/reopen and offline HTML were checked.
  Pageerror arrays were empty. Original Korean user text remained unchanged.
- Screenshot inspection found undersized new controls. Reused the existing
  option-grid styling, rebuilt, and reran the new study/q1/q2-fit journey with
  >=34px input-height and visible stored d(L)/d(T)/d(H) checks. Passed; screenshots
  re-inspected. No model calculation was changed by this presentation adjustment.
- The old preview receipt hardcoded API36 even though runtime was37. Changed
  receipt generation to read `/runtime-info`; older receipt metadata is not
  evidence of a different running contract. Actual runtime37/metadata30 was checked.
- Final full backend and server-restart browser result pending below.

## Implementation Map

| Boundary | Files and responsibility |
| --- | --- |
| Numeric curves | `statistics/bo_target_curve.py`: `GaussianTargetGoal`, weighted log payoff and Gaussian moments; `bo_desirability.py`: explicit dispatch and composite moments |
| Typed contracts | New `schemas/bo_curve_policy.py`, `bo_curve_calculation.py`; versioned public review/batch unions preserve old definitions |
| Core/validation | `bo_desirability_core`, `bo_desirability_batch_core`, both calculation validators and owned worker use the same committed curves |
| Persistence | `bayesian_studies`, `bayesian_desirability_recommendations`, `storage/bayesian_studies`, metadata migration30; study6/history2 and tuple7 dispatch |
| Reports | `dedicated_report_readers`, `bo_noise_report`, `bo_desirability_report`; exact saved definition, no latest-history substitution/refit |
| UI | New `BayesianCurvePolicy.tsx`, explicit locale messages; vector draft, review draft/guard, snapshot and recommendation panels; preview reads controls but never supplies fitting assumptions |
| Verification | New versioned-curve math/API/migration tests, frontend control/guard tests and `bo_target_curve_recommendation.py` within the existing context suite |

## Limitations and Environment

Native Windows10 Home10.0.19045, CPython3.10.11, CPU math threads1; resource-limited
machine, one read-only agent, no parallel fit suites. Browser artifacts and
synthetic workspaces live under the OS temporary directory, not Git.
The new curve is target-only with peak1. Arbitrary peak values, non-linear
maximize/minimize policies, persistent editable candidate sets, and JMP named
augmentation strategies remain outside this gate. Public formulas and supplied
workshop interpretation are not a same-input JMP runtime comparison.
Linux/Python3.11/3.12, Windows11, remote CI and installed archive are unverified
for this gate. No dependency upgrade, commit, push or release was performed.

Focused reproduction (PowerShell, repository venv):

```powershell
$env:PYTHONPATH = Join-Path $PWD 'backend'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_versioned_curves.py backend/tests/unit/test_bo_curve_policy_api.py backend/tests/unit/test_bo_curve_metadata_migration.py -q
npm --prefix frontend run test -- --run --maxWorkers=1
.\.venv\Scripts\python.exe tests/e2e/bo_target_curve_recommendation.py --base-url http://127.0.0.1:8678 --output "$env:TEMP\bo-target-policy-20261110\browser-final"
```

The browser command requires the built app and a synthetic test workspace.
It creates studies/trials/reports and must not target a user's real workspace.

## Rollback

No rollback executed. Once committed, revert only this gate's commits in reverse
order. Older code may not read study6/result7 or metadata30. Code revert does not
undo observations or database migration; use a verified pre-upgrade offline
backup restored to a separate destination when needed. Never delete workspaces,
models, results or the previous local implementation stages.
