# Target Desirability Curve Preview Gate

Date: 2026-11-09 to 2026-11-10 (KST). Worktree: `feat/bo-desirability`, base HEAD
`1db522a12a4023995d52bdcdcf750f9500c47381`. Existing uncommitted Stage 3
changes are preserved. No commit, push, tag, release or user-workspace mutation
is part of this gate. Metadata remains 29; API becomes 36.

## Acceptance and Boundary

This is the first **non-persistent curve comparison** slice of workshop audit
Gate 2, not completion of Gaussian-curve BO recommendations. Existing DS-linear
study/review/batch/history/report policies and their immutable hashes are unchanged.
No new BO method/result version is needed for a preview-only endpoint.

- Peak-one two-sided Gaussian target controls, independent numerical references.
- Explicit comparison against the existing DS-linear target using the same Y axis.
- Optional, explicitly entered hypothetical Gaussian mean/SD and incumbent/xi.
- One response's unweighted `d` is compared, not weighted multiresponse `D`.
  Importance remains part of the existing study's composite recommendation policy.
- API/UI identify `preview_only=true`, `persisted=false`, and
  `applied_to_recommendations=false`; request snapshot included.
- No fit, dataset read, trial creation, history mutation, automatic retry, or export.
- Existing charts, exact number formatting, KO/EN and source/request guards reused.
- No new package, SQL, dependency upgrade, telemetry or uploaded training material.

The curve comparison is separate from the study creation payload. Next gate must
connect a versioned curve policy through study creation, review, confirmation,
restore and report before claiming it changes recommendation results. General
peak ordinate below 1, composite new-policy acquisition and maximize/minimize
nonlinear tails are not implemented here.

## Formula and Risks

Policy `two_sided_gaussian_target_peak_one_v1`:

`d(y) = exp(log(d_side) * ((y - target) / width_side)^2)`.

Require finite `L < target < H`, `0 < d_L,d_H < 1`, peak exactly 1.
Left/right widths may differ. The function continues beyond control points;
those controls are not hard specifications or probabilities of meeting them.
Peak 1 preserves the current Beta approximation support [0,1]. Allowing arbitrary
peaks would require rescaling composite support, incumbent, xi and batch scores.

Independent quadrature checks the explicit product formula above, not a fitted
JMP posterior. See `jmp_workshop_public_findings.md` for the evidence boundary.
[JMP target controls](https://www.jmp.com/support/help/en/19.2/jmp/how-to-use-the-desirability-function.shtml)
and [JMP Desirability function](https://www.jmp.com/support/help/en/19.2/jmp/optimization-functions.shtml)
confirm the three-point workflow. Exact JMP runtime equivalence is unverified.
Original private material and extracted sample rows are not copied into tests.

`target_moments` integrates each half-normal product analytically in log space.
For nearly equal first/second moments it uses a centered, bounded quadrature
of relative changes to avoid cancellation. A positive but unrepresentable
variance is explicitly unavailable, not a deterministic zero. Actual SD=0
remains a point mass. Numeric overflow/precision failure affects the metrics,
not the valid curve plot; no fallback to a different method.
Gaussian tail nodes below floating-point range are counted and explicitly
labelled as underflow in the UI, not exact zero preferences.

Moment matching uses existing Beta EI, **not** exact transformed-Gaussian EI,
qNEI or specification probability. Concentration/precision restrictions remain.
The preview exposes quadrature error and normal-tail bound; these do not measure
Beta approximation error. Non-finite/boolean/string numeric input is rejected.

## API and UI

`POST /api/v1/bayesian-studies/target-curve-preview`, schema 1:
controls, explicit plot range containing controls, optional assumed distribution.
Maximum 164 distinct plot nodes, no user-supplied expressions or paths.
Runs as a sync route in the worker-thread boundary. Quadrature evaluations are
bounded to 20,000 per curve (40,000 for the comparison request). No persistent source identity is invented for a hypothetical
distribution. Assumption fields start blank and are opt-in.

Entry: BO new-study response goals, target-response curve comparison. Existing
goal thresholds provide control Y values; side desirability is a separate preview
draft. All changes invalidate pending success/error/finally; A-B-A changes cannot
restore an older result. Locale/resize only change presentation. No preview
request is sent until the explicit Compare button is used.

An obsolete creation notice saying multiresponse recommendations were unavailable
was also replaced by the existing saved-history/review/confirm explanation.
The actual q1-q8 recommendation implementation is preserved.

## Verification Ledger

This section records this gate's executions only. Prior gate successes are not
substituted for current evidence.

- Red: new math test collection failed because `bo_target_curve` did not exist.
- Initial math: 28 passed, including asymmetry, narrow peaks, tiny positive
  variance and an independent raw-normal quadrature reference.
- Review agent (read-only, one agent): found positive variance underflow and
  finite-coordinate subtraction overflow. Both received regression tests/fixes.
- Initial API run: 36 passed, 2 test-harness failures: Windows locked lease file
  cannot be hashed; existing curve policy is required, not a Pydantic default.
  Test corrected to exclude only `.workspace.lock` and assert the literal contract.
- Typecheck first run: new test called `buildVectorObjective` without name;
  corrected the test signature, not production behavior.
- Subsequent math/API/DS regression: 109 passed before the final additional
  numeric-edge tests. Separate current-contract checks are recorded below.
- Final-source frontend rerun: **138 files / 1,232 tests passed**, maxWorkers=1,
  139.74 seconds. Includes final input row alignment, underflow notice and
  accurate creation-state wording. Final built preview browser run also passed.
- Built-browser first attempt: implicit select label included option text;
  added explicit accessible name. Saved actual child-page DOM/screenshot/trace.
- Built Chromium149.0.7827.55 final run: KO/EN, viewport1024/1440, content
  width980..1106px, independent E[d]=0.5773502691896257 and
  Var[d]=0.11388026216662457, original SVG control coordinates, keyboard pin/
  Escape, source A-B-A late-response rejection, explicit network failure without
  retry, no fit/study/experiment POST, no pageerror. Locale/resize made no POST.
  A final extra browser case confirms tail underflow is visible and counted.
  These are local built-UI checks, not an installed archive or actual JMP run.
- Agent's final read-only review found one further grid intermediate overflow;
  fraction-first multiplication, explicit endpoints and a regression were added.
- Localization: 3,007 source mappings / 4,687 keys, passed. Removed exactly one
  orphan entry for the obsolete unavailable-stage notice.
- Lint: 0 errors, 12 pre-existing fast-refresh warnings. Build passes with the
  existing large-chunk warning. Ruff/mypy pass.
- Focused math/API/current runtime contracts: **319 passed, 1 skipped**,
  145.43 seconds. The skip requires unavailable Windows symlink privilege.
- **Final-source full backend: 3,749 passed, 10 skipped, 0 failed/errors**,
  147 warnings, 3,988.44 seconds. Includes new target math/API tests, existing
  q1/q2/q8 DS lifecycle, fit-quality review/confirm/restart/report, scalar BO,
  GPR/DOE/RSM and the remaining repository regression tests. No production code
  changed during this full run.
- Ten skips: six unavailable Windows symlink-creation cases; four POSIX/Linux
  pipe, venv-symlink, TCP TIME_WAIT and flock cases. They are not passes.
- Full-run environment rechecked: Python3.10.11, Windows10.0.19045, NumPy2.2.6,
  SciPy1.15.3, sklearn1.7.2. CPU threads1. No dependency changes.
- Final agent read-only review: all three reported numerical boundaries fixed;
  no additional blocking P1/P2 found. This is source review, not runtime proof.
- Integrated built-browser `bo_vector_history.py` passed on the final source:
  new target preview, actual UI vector-study creation/measurement entry, read-only
  exact history restore, q1/q2 legacy DS recommendations, q2 multiscale-fit review,
  stale response rejection, explicit idempotent lost-confirmation retry, partial
  measurements, managed-report save/download/reopen and offline HTML. KO/EN,
  1024/1440px, unchanged stored histories and zero pageerrors. This is a focused
  local browser journey, not all four native CI browser shards.
- Final static checks: Ruff check, 509-file format check (including the two E2E
  files), mypy269 source files, localization, capability generation and
  `git diff --check` passed. The line-ending warning is informational.

Private synthetic evidence is under the system temporary directory
`bo-target-curve-20261110`; no diagnostics or training material are committed.

## Changed Boundaries and Commands

New calculation: `statistics/bo_target_curve.py` (`TargetCurve`,
`target_desirability`, `target_moments`). New DTO/service:
`schemas/bo_curve_preview.py`, `services/bo_curve_preview.py::preview_target_curve`.
`api/v1/bayesian_studies.py` adds the independent preview route.

New UI: `BayesianTargetCurvePreview.tsx`, `boCurvePreviewDraft.ts`,
`boCurvePreview.css`, typed API request/response and explicit KO/EN messages.
Existing `BayesianResponseGoals.tsx` provides the entry and correct creation-state
notice. Runtime contract/capability, frontend types, Windows launcher and their
contract tests move together to API36. No existing DS math is modified.

Executed command families (PowerShell, active worktree, `PYTHONPATH=backend`,
CPU math threads1; exact counts/status in the ledger):

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_target_curve.py backend/tests/unit/test_bo_curve_preview_api.py -q
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe -m ruff format --check backend
.\.venv\Scripts\python.exe -m mypy backend/app
.\.venv\Scripts\python.exe scripts/render_tutorial_results.py --check
node --test scripts/read_frontend_capability_metadata.test.mjs
.\.venv\Scripts\python.exe scripts/generate_capability_matrix.py --check
node scripts/check_frontend_localization.mjs
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test -- --run --maxWorkers=1
npm --prefix frontend run build
.\.venv\Scripts\python.exe tests/e2e/bo_target_curve_preview.py --base-url http://127.0.0.1:8678 --output "$env:TEMP\bo-target-curve-20261110\browser-verified"
.\.venv\Scripts\python.exe tests/e2e/bo_vector_history.py --base-url http://127.0.0.1:8678 --output "$env:TEMP\bo-target-curve-20261110\vector-regression"
.\.venv\Scripts\python.exe -m pytest backend/tests -q --durations=25 --junitxml="$env:TEMP\bo-target-curve-20261110\backend-full.xml"
```

The full backend command completed successfully; its JUnit XML records 3,759
collected cases, 3,749 passed and 10 skipped, with zero failures/errors.
The focused runtime batch additionally covered health, dev startup, runtime
entrypoint versions, OpenAPI/frontend contract and built-web serving. Native
Windows10 Home10.0.19045 / Python3.10.11 was used; Windows11 was not tested.

## Rollback Boundary

This gate has no SQL migration and changes no saved recommendation or study.
When the staged work is eventually committed, revert only this gate's commits
in reverse order, including matching frontend/backend runtime contract changes.
Do not use a broad diff against HEAD: it includes earlier uncommitted stages.
Do not remove workspaces, models, results, or history. The earlier metadata29
compatibility/backup limits remain those documented in the fit-quality gate.

Not yet verified: JMP runtime, Linux/Python3.11/3.12, remote CI, archive, true
new-curve recommendation lifecycle. No claims of complete JMP alignment.
