# BO Progress And JMP Comparison Audit

## Scope And Source

BASE_SHA: `1df6515a7e5e0e728633e0b1f16f42e7f23911e8`.
Branch: `feat/bo-progress-charts`. Existing isolated worktree; user workspace,
untracked training materials and examples were not changed. This is an additive
UI change, not a new GP fit, acquisition policy, API/schema or database migration.
API42 and metadata33 remain unchanged. No Linux Release publication is requested.

## Behavior

| Request | Implementation | Meaning |
| --- | --- | --- |
| Measured progress | `BayesianProgressCharts` / `buildBayesianProgress` | Completed trials by registered trial number; max/min cumulative best; target response or absolute target-distance view |
| Observed desirability | Same adapter, immutable stored response goals | Weighted geometric DS-linear or peak-one Gaussian target scores; not posterior desirability or success probability |
| Experiment locations | `projectBayesianFactors` | Actual factor coordinates; separate completed/pending/abandoned markers; no inferred Y for pending trials |
| Consistent interaction | Existing `InteractiveScatterChart` / `ChartFrame` | Hover, focus, arrows, Enter pin, Escape, full-value details and responsive SVG |
| Explicit replicates | `BayesianReplicatePanel` | Initially collapsed controls; in-flight/error/success/retry notices remain visible |
| Candidate purpose | `BayesianCandidatePurpose`, batch and review tables | Saved response goal, actual EI/ETI and conditional planning meaning; saved exploration preference where present |

Existing tables, profilers, fitted diagnostics, manual selection, augmentation,
recommendation math, source checks and immutable artifacts remain in place.
The review response does not store an exploration-profile label: it shows its
actual criterion and xi, rather than guessing a profile from the editable draft.
The confirmed batch does contain the saved profile and displays it.

Trial number is registration order, not measured clock time. Current-history
graphs are explicitly separate from historical recommendation batches. Scalar
goals without desirability limits do not receive invented limits. Repeated
conditions remain individual trials. Categorical codes identify declared levels,
not distances; long/dense levels use bounded index ticks and a full-name mapping.

## Independent Review And Red Tests

One read-only reviewer at a time, with no parallel heavy test jobs. Findings and
fixes were checked by the coordinator:

- Completed-history hashes exclude pending/abandoned changes. Factor-space source
  identity now additionally includes sorted trial IDs/states. A built-browser
  test abandons a pending trial while the completed hash stays unchanged and
  verifies the old pin clears after refresh.
- Gaussian target importance must multiply the log-decay before squaring the
  relative distance. A subnormal-weight regression formerly returned unavailable
  although the backend score is finite; shared TS/Python fixed-value tests cover it.
- Long category labels need bounded ticks. Sparse observed categories also need
  declared-category bounds, otherwise every sampled tick could fall outside the
  point-only range. A 32-level sparse-subset regression reproduces this boundary.
- The display ratio now subtracts nearby finite values before scaling; the
  `1e12 .. 1e12+5` fixture gives exactly the intended one-fifth fraction.
- Common chart reference lines already expand the domain. No duplicate target-axis
  fix or shared chart rewrite was needed.

Initial failures are retained in this audit: new-module RED tests, selector
accessible-name mismatch in the first built-browser run, missing localization
registrations, and three old review-fixture tests lacking incumbent/planning
fields. No retries or enlarged timeouts were added to conceal them.

## Validation Ledger

Fresh local environment: Windows, CPython3.10, Node24, Chromium149, CPU-only.
Synthetic data uses a separate temporary workspace and loopback port. The user's
preview workspace is not a test fixture. Backend imports explicitly use this
worktree via `PYTHONPATH=backend`.

- New policy fixture: Python passed. Shared expected values are independently
  specified, with absolute tolerance `1e-14` (including subnormal-weight rounding).
- Final full frontend suite: 160 files / 1427 tests passed. The subsequent test
  fixture typing cleanup also passed typecheck; production chart code is unchanged.
- BO acquisition/desirability/target and fixture/suite regression command: 193
  passed. This includes independent quadrature tests; it is not a full backend run.
- Backend fixture/suite/readiness/origin contracts: 105 passed.
- Ruff lint and format checks passed; mypy: 327 source files passed.
- Localization: 3013 source strings / 4693 keys passed. ESLint: zero errors,
  12 pre-existing fast-refresh warnings. Build/typecheck passed with existing
  large-chunk and localization-plugin timing warnings.
- Built-app scalar/vector/mixed graphs: KO/EN at1024/1440, exact plotted values,
  pending separation, full Korean user-label preservation, keyboard pin/Escape,
  locale/resize pin preservation, refresh restore and history checksum checks.
  View-only changes made zero POST/PUT/DELETE requests; zero pageerrors.
- Existing built BO context and workflow suites passed: q1 target, q2 MC batch,
  explicit repeat entry, raw/exact grouping, recommendation review, response-loss
  retry with the same request, saved models/reports, HTML numbers and restore.
  Saved candidate context remained unchanged after editing exploration preference.
- Full local backend suite was not run for this UI-only change; complete Windows,
  Linux and Python compatibility/security/archive coverage remains the required
  remote CI gate, not inferred from these focused results.
- New `bo_progress` journey is included in the existing context/full CI suites;
  existing workflows/context/data/prediction partitions are not merged or removed.

## JMP Evidence Boundary

The supplied training material is private input, not a redistributable fixture.
Original documents, screenshots, rows and sample-specific numeric outputs stay
local, following [the existing privacy boundary](jmp_workshop_public_findings.md).
Public evidence describes the comparison and limitations without publishing the
training data. Saved JMP output is distinguished from live JMP execution.

The current task reuses the inspected training-output locations and independent
Cholesky/quadrature checks. Starting Values are not fitted parameters; unknown
interval definitions cannot be converted into SD. A common finite candidate-pool
ranking using our acquisition is not JMP's acquisition value or a parity rate.

## Reproduction And Rollback

```powershell
$env:PYTHONPATH = Join-Path $PWD 'backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_progress_policy.py -q
npm --prefix frontend test -- --run --maxWorkers=1
npm --prefix frontend run lint
npm --prefix frontend run build
.\.venv\Scripts\python.exe tests/e2e/bo_progress.py --base-url http://127.0.0.1:8612 --output "$env:TEMP\bo-progress-evidence"
```

The last command requires a separately started synthetic backend serving the
production `frontend/dist`; it must not target the user's workspace. Native full
checks continue through `scripts/check.ps1` / `scripts/check.sh` and required CI.
This is built-UI verification, not a claim of a newly installed Linux Release.

Rollback is `git revert` of this feature's commits in reverse order. No stored
format or SQL change is introduced. Do not delete workspaces, trials, models or
results; no rollback was performed.

## Official Workflow References

- [JMP current batch](https://www.jmp.com/support/help/en/19.2/jmp/current-batch.shtml): saved reason-added context.
- [JMP candidate set](https://www.jmp.com/support/help/en/19.2/jmp/candidate-set.shtml): separate augmentation criteria, not an alias for scalar Balanced EI.
- [JMP staff introduction](https://community.jmp.com/t5/JMPer-Cable-Blog/Introducing-the-Bayesian-Optimization-platform-in-JMP-Pro/ba-p/897807): observed desirability progress workflow.

Actual-response/best and factor-space plots are additive product views. This
change does not claim to reproduce every JMP graph or its unpublished Auto rules.
