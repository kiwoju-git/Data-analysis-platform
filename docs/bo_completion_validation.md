# BO Completion Validation

## Baseline

- Date: 2026-11-13.
- BASE_SHA/local main/origin main: `e36d40a7569bad311c08f294edbfa51f76cac82b` after fetch.
- Isolated branch: `feat/bo-completion43`.
- Protected untracked originals: `docs/jmp/`, `examples/image2.png`.
- User request: mandatory fixes and remaining feature strengthening, then main push. Linux publication is deferred.
- No user data or existing artifacts are changed by this audit.

## Integration Checkpoint

Locally verified implementation commits:

- `f3fc56d`: advanced existing-X/Y options and interactive response diagnostics.
- `2658b19`: canonical regression GPR navigation without the AI duplicate.
- `d2c4da9`: historical acquisition receipt read compatibility and strict new
  calculation/commit boundaries.

The following documentation commit records the current evidence. Main integration
and native PR CI are pending at this checkpoint; no Linux Release is published.
Mixture/pseudocomponent support, a full all-factor profiler matrix, JMP's private
Auto/tail rules and exact JMP fit-output parity are not claimed complete here.

Rollback, only when explicitly requested: revert this task's commits newest
first (or revert its eventual merge commit with the correct mainline). Code
rollback does not roll back a workspace or undo completed experiments. No user
workspace, dataset, model or result needs deletion; no stored schema or metadata
migration was introduced by this change.

Native validation is tracked in [PR 9](https://github.com/kiwoju-git/Data-analysis-platform/pull/9).
The first PR head was `0d5d96c2e1c491975283bd70f6ba441ec6805bc1`, CI run
[43418755313](https://github.com/kiwoju-git/Data-analysis-platform/actions/runs/43418755313).
A fresh static final reviewer identified two new strict-rejection tests that
incorrectly assumed the fixed historical Linux EI differed from local replay.
Controlled Linux-matching replay reproduced both failures locally (2 failed,
2 passed); this was a test portability defect, not a production math change.
The correction retains the fixed historical read fixture and instead changes a
locally valid strict baseline by 1%, with all score links kept consistent. Both
native and simulated matching-replay paths must reject that deliberate mismatch.
No production arithmetic, receipt value or validation tolerance is changed by
this follow-up. The first CI attempt is retained, not treated as the final pass.
The corrected four parameter cases passed; the related compatibility/policy/
augmentation set passed 101 tests. Native full CI must still validate the exact
updated PR head; the controlled case is not called a native Linux execution.

The next head, `579585abb1566c80d934cb405bfe770ddfc1d69d`, ran in
[43419661817](https://github.com/kiwoju-git/Data-analysis-platform/actions/runs/43419661817).
Its Linux/Python 3.12 backend run finished with 4,474 passed, 29 skipped and one
failed documentation-contract test (740.25 seconds). The coverage document still
listed the removed AI-to-GPR link while the executable E2E stage correctly used
canonical regression navigation. A focused Windows run reproduced that exact
single mismatch before the one-line document correction. Neither the assertion
nor navigation behavior was weakened. This failed run remains evidence, not a
passing full suite; the corrected head requires a fresh native CI run.
After correction, the entire OpenAPI/frontend/document contract test file passed
locally: 244 tests, two existing Starlette warnings, 19.89 seconds. Command:
`python -B -m pytest backend/tests/unit/test_openapi_frontend_contract.py -q -p no:cacheprovider`.

## Confirmed Failures

CI [43285568827](https://github.com/kiwoju-git/Data-analysis-platform/actions/runs/43285568827), source BASE_SHA:

| Item | Evidence | Current status |
| --- | --- | --- |
| Frozen legacy Beta dispatch test | Linux 3.12 and 3.11 compute `2.633949561237081e-6`; test hardcodes Windows `2.6340823912618383e-6` | source-confirmed / CI reproduced; test repaired and locally verified; native CI pending |
| Windows workflows GPR navigation | E2E expects obsolete `.is-contextual` surrogate card; current landing provides executable GPR cross-link | source-confirmed / CI reproduced; helper repaired and bounded KO/EN navigation verified; full workflow pending |
| Release-ready | Failed upstream jobs; archive job skipped | failed baseline, not a release |

These are current-run failures, not evidence that all BO calculations are incorrect. Tests must retain policy dispatch and actual executable navigation coverage.

## New Work Evidence

2026-11-13 bounded CI repair, no production arithmetic changes:

- `test_bo_beta_numerical_policy.py`: 16 tests passed using CPython 3.10.11 /
  SciPy 1.15.3 on Windows build 19045. The compatibility oracle preserves the
  frozen operation order with installed special functions; the saved Windows
  receipt still has exact serialization/hash checks. This is not an independent
  accuracy reference or proof of cross-platform bitwise equality.
- At the first checkpoint, `critical_path.py` checked the executable AI-to-GPR
  link rather than the obsolete contextual information card. The later owner
  request below supersedes that duplicate placement.
- The new helper passed KO and EN navigation against the existing BASE built
  preview, each in a fresh BrowserContext: source dataset/schema and three exact
  numeric column options preserved; GPR route/panel visible; no API writes or fit.
  This does not replace the full Windows workflow or new-build validation.
- Focused Ruff, helper/unit formatting, in-memory compilation and
  `git diff --check` passed. Linux/Python 3.11 and full project checks not rerun.
- Separate source-confirmed risk: `bo_desirability_contract.py` compares stored
  EI with a platform recomputation exactly. Cross-OS restoration of a historical
  receipt remains unverified; changing the test oracle does not resolve it.

Evidence is outside Git under the local temporary `bo-completion-20261113`
directory, including `ci-repair-report.md` and KO/EN receipts/screenshots.

## Graph And Navigation Follow-up

The owner confirmed that standalone GPR is already available in the regression
module and must not also be added to AI/ML. The canonical executable GPR route,
model and prediction capabilities are unchanged. Only the AI cross-link metadata
is removed. `gpr_navigation.py`, the existing context/workflow suites and generated
capability metadata now expect canonical regression navigation. A correct red
test reproduced the duplicate in KO/EN; after removal 11 navigation tests and 24
capability tests passed. An earlier red attempt had a test-only wrapper-field
mistake, corrected before the meaningful red/green run. Independent static
review found no actionable navigation defect; real built navigation is a separate
pending gate at this checkpoint.

Graph audit distinguished existing features from new work: observed progress,
composite desirability, trial locations, selected-response profiler and actual
versus conditional LOO prediction were already present. New work adds the stored
LOO residual-versus-prediction plot and simultaneous response-mean plots for the
single applied profiler axis. Each response retains its unit; composite expected
desirability has a separate plot. Uncomputed axes are not invented. The prior
selected-response mean/latent-SD/predictive-SD detail remains available.

The mixed profiler used `desirability` both as its composite selector and as an
allowed response ID. A focused failing test reproduced that collision; response
selector values are now namespaced, without changing saved IDs or artifacts.
No statistical calculation, API43, metadata34, model bytes or dependency changes
are required for these display additions. Shared interactive chart primitives,
source keys, numeric precision and KO/EN boundaries are retained.

### Additional Compatibility Finding

A separate read-only audit traced actual saved numeric single/batch desirability
readers to exact legacy EI replay, and numeric augmentation readers to a 16-ULP
comparison. A bounded no-fit probe serialized a synthetic augmentation row with
the recorded Linux value and a valid checksum: local Windows control was accepted,
while that other-platform value was rejected. Difference was about `1.3283e-10`
absolute (`5.04e-5` relative). This is a saved-reader primitive reproduction,
not native Linux or complete persisted-API verification. Numeric manual and mixed
stored selection paths instead use strict artifact/source bindings and were not
found to have this replay defect.

No broad tolerance relaxation or checksum bypass has been applied. Separating
historical receipt validation from new-calculation accuracy is an explicit
compatibility-policy decision, approved by the owner on 2026-11-13. The repair
will preserve historical stored acquisition values after strict artifact/source
validation, without weakening new-calculation checks. Implementation and actual
reader regression are separate from the portable CI test above.

The first full backend run collected 4,455 tests and was intentionally
interrupted at approximately 11% when this additional backend change was
approved. No failure had appeared; two skips had appeared. This is an
**interrupted pre-change run**, not a passing suite. The preceding tutorial
sync (18 blocks), metadata AST tests (11) and mypy (334 files) completed.
Only the identified task-owned pytest process and its worker were stopped;
existing user preview servers were not stopped. Final-code checks must be
recorded separately below.

Fresh integrated frontend validation after the graph/navigation changes:
166 files / 1,499 tests passed with one worker (172.36 seconds), TypeScript
passed, and the production build exited successfully. Existing chunk-size and
plugin-timing warnings remain. The current npm runtime and development security
audits passed; this does not substitute for the Python/native security gate.

Independent review of the proposed historical receipt guard raised an endpoint
roundoff concern. A bounded compatibility grid reproduced it: 432 Windows cases,
367 accepted by frozen legacy arithmetic, 65 explicitly rejected by that legacy
implementation, and one accepted legacy value rejected by the draft theoretical
payoff bound. At `mean=1-1e-10`, variance `0.9*mean*(1-mean)` and threshold equal
to mean, the legacy value exceeds the ideal upper bound by `1.1102230246251565e-16`.
The guard therefore needs the original subtraction arithmetic budget, not a
new globally relaxed EI comparison. This is a compatibility check against frozen
code, not an independent statistical accuracy reference or native Linux proof.

After the guard correction, all 367 legacy-returned values were accepted
unchanged; the same 65 cases retained their explicit legacy precision error.
Final focused legacy/policy/augmentation validation passed 99 tests (24.63 s,
three existing Starlette deprecation warnings). Changed-file Ruff (8 files) and
mypy (7 production files) passed. The real SQLite q1/ordered result GET and
confirmed replay tests preserve original bytes/hashes; the augmentation reader
fixture retains real typed/hash/contract checks but substitutes its storage and
source lookup seams. First confirmation of an unconfirmed legacy candidate is
still strict and can remain platform-sensitive. This limitation is not hidden
by the restored read path.

### Built Graph Workflows

The integrated production build was served from a separate synthetic workspace
on an ephemeral loopback port. Run 1 passed canonical GPR navigation/real fitting
and the two-response numeric BO workflow, then failed in the mixed study builder:
the E2E still searched for the old `Constraint name` accessible name. The reused
editor now distinguishes rows as `Constraint name constraint_1`. The failing
child-page DOM/screenshot showed the input present, runtime compatible and no
page errors. The selector and related coefficient/bound/relation assertions were
updated to the actual unique names; no timeout was increased or assertion removed.

Run 2 passed all three workflows on a fresh workspace:

- Canonical GPR: 8 synthetic rows, real fitting, exact X/Y labels/values and source
  hashes; KO/EN at 390 and 1440 px; selected header dataset retained; no GPR link
  under AI/ML. Existing fit options were retained.
- Numeric BO: two response units (`%` and `USD`), exact per-response/composite
  profiler coordinates, conditional LOO observed/residual points and zero lines,
  keyboard pin/clear/navigation, A-to-B-to-A response ownership, candidate
  confirmation, exact-source restore and offline report verification.
- Mixed BO: real UI builder, nominal/ordinal policies, numeric-only constraints,
  original Korean/special-character levels, a response literally identified as
  `desirability` distinct from the composite choice, fit/profile/review/confirm/
  restore/report. Category graphs use discrete points, not interpolated lines.

Graph checks used KO/EN at 1024/1440 px, actual DOM item/tick bounds, payload
values and screenshots, not screenshots alone. Root visually inspected numeric,
nominal and LOO screenshots, including the visible offset on the narrow LOO
prediction axis. Language/resize/display changes issued no fitting writes.
No page errors occurred. These are built Windows/Chromium 149.0.7827.55 checks,
not native Linux or archive evidence. Both test-owned servers were closed and
the original user previews were preserved. Failure evidence remains in
`graphs-built-run1`; successful receipts/screenshots are in `graphs-built-run2`,
outside Git. No real user dataset was used or uploaded.

### Final Local Contract Regression

Root reran the changed legacy receipt tests together with numerical-policy,
augmentation contract/API, desirability contract/review/public-batch tests:
**175 passed**, 16 existing Starlette deprecation warnings, 237.13 seconds.
Whole-backend Ruff passed, 619 Python files passed format checking, mypy passed
335 application files, and `pip check` found no broken requirements.

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_legacy_stored_readers.py backend/tests/unit/test_bo_beta_numerical_policy.py backend/tests/unit/test_bo_augmentation_contract.py backend/tests/unit/test_bo_augmentation_api.py backend/tests/unit/test_bo_desirability_contract.py backend/tests/unit/test_bo_desirability_review_api.py backend/tests/unit/test_bo_desirability_public_batch.py -q -p no:cacheprovider --basetemp "$env:TEMP\bo-completion-20261113\pytest-final-focused"
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe -m ruff format --check backend
.\.venv\Scripts\python.exe -m mypy backend/app
.\.venv\Scripts\python.exe -m pip check
npm --prefix frontend run test -- --run --maxWorkers=1
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Single-thread BLAS/bytecode/cache settings remained as documented above. The
interrupted full local backend run is not promoted to a pass. Full native
Windows/Linux/Python compatibility, security and archive gates are to run in PR
CI before main integration. Linux Release publication remains out of scope.

## Advanced Import Checkpoint

The existing import UI now exposes actual-unit numeric constraints and explicit
nominal/ordinal correlation policies under a collapsed advanced section.
Shared editors reuse the same request parser as mixed-study creation. Referenced
factor mapping/type/removal is blocked until its coefficients are explicitly
cleared. Invalid numeric text remains a draft; an incompatible ordinal policy is
visible and blocks preflight. No new backend contract, numerical method, API,
metadata schema or dependency is introduced.

- Focused frontend red/green: the initial run failed at five missing controls;
  a later red exposed two missing error-display boundaries. Final focused suite:
  40 tests in six files passed, with at most two Vitest workers.
- Scoped ESLint and TypeScript passed. An initial lint command used the wrong
  working directory; the corrected command exposed two test typing errors,
  fixed before the successful rerun.
- Integrated `npm --prefix frontend run build` passed. Existing large-chunk
  and localization-plugin timing warnings remain; no size limits were relaxed.
- Native Windows/Python 3.10.11 focused backend regression: 47 passed, three
  existing Starlette deprecation warnings, 142.76 seconds. Files: Beta numerical
  policy plus dataset import API/migration/reports/real recommendations. This
  includes source ownership, backup/restore, actual scalar target and mixed q1
  recommendations; it is not the full backend suite.
- Built Chromium 149 workflow: exact imported measurements, numeric constraint,
  q2 recommendation, actual observation submission, next q1 review, reopen,
  managed HTML checksum/download/offline opening, and saved category policy
  passed on a separate synthetic workspace. KO/EN and 1024/1440 numeric-form
  layout checks preserved drafts without POSTs; category identities remained
  Korean. Invalid nominal/ordinal policy sent no POST. No page errors occurred.
- First browser attempt failed because the new test's nested `has` locator was
  scoped incorrectly, not because the advanced control was missing. Corrected
  locator passed in run 2; diagnostics from the first attempt were retained.
- Read-only independent review found no production-code issue. It identified a
  missing assert for restored constraint equality in the added E2E; the boolean
  was true in run 2, and an explicit regression assertion has now been added.
- Run 3 passed after that assertion was added, using another fresh synthetic
  workspace. The test-owned server terminated; original preview processes on
  ports 8000/8614 remained healthy. No user preview was stopped to run checks.
- Full frontend regression: 165 files / 1,490 tests passed with two workers
  (110.83 seconds). Backend Ruff passed and all 617 Python files satisfied the
  existing formatter. No dependency or reference tolerance was changed.
- Full frontend lint exited successfully with zero errors and 12 existing
  Fast Refresh export warnings in unchanged GPR/regularization/DOE components.
  Integrated TypeScript and localization checks passed (3,013 source strings,
  4,693 translation keys).

Commands executed for the checkpoint, from the isolated repository root:

```powershell
.\.venv\Scripts\python.exe -B -m pytest backend/tests/unit/test_bo_beta_numerical_policy.py backend/tests/unit/test_bo_dataset_import_api.py backend/tests/unit/test_bo_dataset_import_migration.py backend/tests/unit/test_bo_dataset_import_reports.py backend/tests/unit/test_bo_dataset_import_recommendation.py -q
npm --prefix frontend run test -- --run --maxWorkers=2
npm --prefix frontend run build
npm --prefix frontend run lint
npm --prefix frontend run typecheck
node scripts/check_frontend_localization.mjs
.\.venv\Scripts\python.exe -B -m ruff check backend
.\.venv\Scripts\python.exe -B -m ruff format --check backend
git diff --check
```

These checks used the isolated worktree environment, with bytecode disabled,
single-thread BLAS settings and pytest/cache outputs on C: outside Git.
The E2E helper is `tests/e2e/bo_dataset_import.py --base-url <isolated-built-url>
--output <synthetic-diagnostics> --isolated-workspace`. The task-owned runner
served the built frontend and API from that worktree, and closed only its own
server process tree after each attempt. Evidence is in `import-built-run1/2/3`;
the original failed attempt was not overwritten by the reruns.

Full project checks, native remote CI, mixture domain work and main integration
remain separate gates. No Linux release is requested here.

## Disk-Space Interruption

The new isolated bootstrap failed with `No space left on device`; D: had
700,416 free bytes. The failed environment is generated installation output,
not a user workspace. User authorized reviewing/removing unnecessary D: data.
Automatic cleanup of the exact checked directory was nevertheless rejected by
tool policy. No automatic deletion was performed or attempted via another tool.

Superseded assessment: a preview-only run inventoried ten generated
dependency/cache directories totaling about 2.0 GiB. Its claim to exclude all
running-preview dependencies was incorrect because it missed junction aliases;
see the incident and recovery below. This inventory is not proof that those
directories were unused. No broad drive purge or worktree deletion was proposed.

Only bounded source/test edits resumed; diagnostics were written to C: and the
existing interpreter was reused without bytecode/pytest cache writes. Advanced
import UI, mixture support, full validation and main push remain unfinished.

### Cleanup Incident and Recovery

Correction to the cleanup assessment above: the process-path check missed
junction aliases. `bo-desirability/.venv` and `bo-kernel-alignment/.venv` point
to `gage-part-id-source/.venv`; two running preview processes had its ContourPy
extension loaded through the alias. That environment was incorrectly classified
as unused. This was an error in the cleanup script, not a user data error.

The user's explicit `-Apply` run deleted the incomplete new environment and two
old remediation environments, then stopped at the loaded ContourPy file in the
shared environment. The later node_modules/cache directories were not deleted.
The cleanup script is now disabled for `-Apply`; no forced deletion or process
termination was performed.

Recovery used the intact `bo-xy42-source` environment. Both environments have
Python 3.10.11 and identical dependency lock SHA-256
`6caa3430d153d935ba18340ae604c7402967fced6ccb4be1c2330f72d9a40ac8`.
Only missing third-party package files were copied, excluding application
editable metadata and bytecode; existing loaded files were not overwritten.
All 147 restored files passed SHA-256 equality with the intact environment.
`pip check`, fresh-process import/native Cholesky/ContourPy smoke checks passed.
Existing APIs on ports 8000 and 8614 each returned HTTP 200 with status `ready`.
Free D: space after recovery: 1,183,842,304 bytes (about 1.10 GiB).
Source, dataset, workspace, model and result directories were not cleanup targets.
This recovery check is not a full product regression or new release validation.

A follow-up installed `RECORD` audit found one additional missing development
header (`greenlet.h`), restored without overwriting existing files and verified
against the donor SHA-256. The final audit inspected 50 distribution records:
7,494 hashed files, 50 unhashed entries, and 4,195 regenerable bytecode entries;
no remaining missing-file, size, or hash issues were reported. Bytecode was
excluded only where its corresponding Python source exists. This is installed
record coverage, not a claim that two environments are byte-for-byte identical.

The cleanup script contains no deletion loop and explicitly states that its
inventory does not establish non-use. Re-running `-Apply` raises a disabled
operation error. Active aliases must be resolved to their physical target before
any future cleanup is reviewed.

The isolated task environment was subsequently bootstrapped successfully using
`scripts/bootstrap.ps1`, with bytecode generation disabled. Exact hash-locked
Python installation, `pip check`, and `npm ci` completed; the npm installation
reported zero known vulnerabilities. These installation checks do not replace
the dependency-security CI gate or application regression tests.
