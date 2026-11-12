# Measured X/Y BO, Numeric Repair And Graph Review

## Scope And Source

- Base: `0070640d8bab3ae8aa2218fea7165cfe229562ee`, fetched origin/main.
- Isolated branch/worktree: `feat/bo-xy-start`; user preview/workspace untouched.
- API43, metadata34. Migration34 adds imported-study dataset ownership and
  request-idempotency records; no historical observation/result is rewritten.
- No dependency changes, Linux package/publication, or external data transmission.
- User screenshots are JMP reference workflows, not application error captures.
  No live JMP license/output was used in this change.

## Recommendation Precision

The synthetic default estimated-noise 3-observation, two-response q2 case
previously returned `bayesian_desirability_beta_precision_unsupported`. At one
candidate, mean=.5154451791162806, variance=2.4973594698037663e-6 and
threshold=.5755140304746322 produce EI log approximately -746.0088854781562.
The two survival products round to the same subnormal number. Their difference
is not a sound cancellation diagnostic: the positive EI itself rounds to zero.
An independent positive integral confirms the value lies below the half-smallest
binary64 subnormal log boundary (-745.1332191019412).

`bo_desirability_acquisition.beta_expected_improvement` retains the original
moment-matched Beta EI definition. `bo_beta_tail` integrates its positive density
in a width-scaled coordinate. It is not exact transformed-Gaussian EI, qNEI,
Gaussian fallback, or a claimed JMP internal algorithm. Signal/noise fitting,
normalization, observation history, candidate feasibility and atomic confirmation
are not changed. Zero-variance and endpoint-Bernoulli policies remain distinct.

Concentrated shapes use standard-library Decimal60 only for scalar centering
and reflection preparation, not during each quadrature evaluation. This avoids
loss from rounding a/b's exact ratio before computing a narrow tail. The original
coordinate precision assessment is preserved when reflecting near zero.
Shapes below100 and unresolved widths retain explicit failure. The quadrature
uses bounded subdivisions and checks numerical error and omitted-tail bounds.
Far-tail zero uses a log-concave density tangent bound plus a conservative
floating-point allowance; this is tested numeric engineering, not interval-
arithmetic certification of every possible binary64 input.

Independent review found three additional cases before completion:

| Mean | Variance | Threshold | Reference EI | Earlier behavior |
|---|---|---|---|---|
| 1e-12 | 1e-28 | 9.9e-13 | 1.0825062186803883e-14 | Reflection rejected |
| .123456789 | 3e-24 | .1234567890173205 | 1.2946222314123248e-36 | Relative error1.88e-5 |
| .9 | 1e-9 | .9000316227766018 | 2.6339494963754832e-6 | Relative error5.05e-5 |

All three were recorded as failing tests, then passed at relative tolerance2e-7
after compensated centering and using the positive integral before the old1e8
concentration threshold. No response values or tolerance widening was used.
Reference construction is independent high-precision density integration.
Formula sources: [NIST incomplete Beta](https://dlmf.nist.gov/8.17) and
[NIST log-Gamma expansion/remainder](https://dlmf.nist.gov/5.11).

New acquisitions and conditional samplers record
`numerical_policy=positive_beta_integral_v2`. Historical records without this
field dispatch to BASE0070640's frozen arithmetic. Nested serialization keeps
the field absent, preserving old hash inputs. New worker outputs must carry v2;
stored readers remain compatible with absent-policy records. See
`bo_beta_numerical_compatibility.md`. An ordinary survival-function case just
below the new integral cutoff retains relative error3.65e-7; the change does not
claim universal2e-7 accuracy or cross-platform bitwise identity.

## Existing Data Workflow

The header-selected version/filter supplies X/Y. The BO form maps columns,
declares executable factor domains and scalar or desirability response goals.
It does not add another upload/dataset selector. Preflight verifies the full
canonical source, displays counts/warnings and freezes the source digest.
Commit creates completed trials with exact measured values, including repeated
coordinates with distinct responses. It never averages or generates measurements.
No GP fit occurs during import; normal BO recommendation fits afterward.
The first UI uses the existing default category correlation policies. It does
not expose a new linear-constraint editor in the import form; the typed import
API accepts the already supported linear constraints. Bounds/levels are explicit
user inputs, not inferred process limits from the observed sample extrema.

The typed API supports numeric scalar, numeric vector and existing mixed-vector
contracts. Mixed scalar uses a one-response desirability objective explicitly.
Dataset schema/filter/draft changes invalidate review and outstanding UI work.
Network failures do not automatically retry POST. Explicit retry reuses identical
payload/request ID; successful server artifacts are never deleted for stale UI.
Long column names can use explicit BO display aliases without changing original
column identity. Dataset deletion remains blocked while imported studies own it.

Imported initialization has its own `dataset_observations_v1` receipt, not LHS
metadata or an invented seed. Generated-design successor reuse is unavailable
for imported studies; ordinary new-study creation remains available. Existing
generated receipts and numeric/mixed history readers remain supported.

## Graphs And GPR

- Fixed a confirmed presentation problem: opaque cumulative-best squares hid
  measured circles at coincident values. Hollow squares retain both identities,
  original X/Y, source selection, keyboard focus, pinning and tooltip values.
- Observation/desirability run charts and factor-coordinate projections already
  existed. Repeated coordinates may legitimately overlap; no data jitter added.
- BO LOO plots and all-response conditional Profiler already exist. LOO uses
  fixed full-fit hyperparameters, not nested tuned external validation.
- Screenshot2's regression/RSM residual and 3D-surface example does not establish
  a missing BO calculation. No fabricated residual/surface values were added.
- AI landing now links to the existing standalone GPR method. Regression remains
  its canonical route. Dataset selection and the same X/Y form are preserved.

## Execution Ledger

This ledger is updated with actual executions, not prior-commit evidence.

| Check | Current evidence |
|---|---|
| Acquisition/batch/public API | 79 passed before final Decimal boundary repair |
| Final acquisition unit | 38 passed including3 review RED/GREEN cases |
| Import/backend narrow | 19 passed; atomicity/source race/migration/backup/legacy |
| Surrounding backend regression | 101 passed,1 old migration expectation failed; corrected and narrow rerun passed |
| Full frontend unit | Official final check:164files,1473tests passed in94.00s, repository maxWorkers2; earlier constrained run maxWorkers1 also passed |
| Import ownership hook | 6 passed; one omitted/null-filter RED then GREEN |
| Full frontend ESLint | Final0errors,12existing Fast Refresh warnings; preceding7 new mock-type errors fixed with actual API types |
| Built GPR navigation | EN/KO,1440/390px, selected8-rowfixture, keyboard, zero fit/writes |
| Built GPR calculation | One real default8-row fit;5-fold CV scores all8 rows; saved result/model hashes verified; undercoverage warning retained |
| Built import/recommendation | Final v2-policy build: import3 measured rows, q2 review/confirm/observe, next q1 review, refresh restore passed; both review HTTP200 |
| Import ownership/browser | A-B-A stale preflight discarded; KO/EN and1024/1440px preserve drafts without POST |
| Import layout/browser | 11label/control pairs per viewport, measured gap6.15625..7.390625px, no page overflow; full-page screenshots inspected |
| Graph built-app | Scalar/vector/mixed progress: KO/EN1024/1440px; hollow coincident markers, keyboard/pin/Escape/source hashes, no view-induced writes passed |
| Beta compatibility/no-fit | 109 passed including nested legacy JSON/hash, all-item policy matching, strict new-worker gate, independent Decimal reference |
| Review API probes | Gaussian numeric import already passed before production edits; combined category-budget overflow RED then controlled409 GREEN;2 passed |
| Imported scalar/mixed recommendations | 2real-worker API tests passed56.38s: target q1 and mixed Refine q1; confirm/read/restart, immutable initial rows/receipt/history preserved |
| Imported managed report | RED7failed/3passed; GREEN10passed plus3existing no-fit report regressions; no raw-dataset/latest-study reads/refit |
| Built managed report | Final post-check browser rerun: real Report Center create/download and offline file open passed; source history unchanged; SHA256 `0d2fc28620b797b4e133ef36c124fa5e5e86a56884ae476e53f0afdcb1b92b50` |
| Backend static final | Ruff check/format617files; mypy334files passed |
| Docs/localization sync | 18 tutorial blocks,11capability AST tests, capability matrix;3013source strings/4693keys passed |
| npm runtime/dev audit | Both current audit profiles passed |
| Python security | Clean Windows3.10 hash-locked dev environment: pip check and pip-audit2.10.1 passed; initial editable target correctly rejected by exact-lock policy |
| Augmentation regression repair | Full run exposed2 stale test assumptions; narrow RED2failed/49passed then GREEN51passed. Active dispatcher patch and explicit evaluator failure preserve Confirm's no-EI coverage; independent source review found no weakened assertion |
| Full backend | Official final check:4443passed/10skipped/154warnings in4896.77s. Earlier incomplete and failed runs are retained below, not counted as passes |
| Integration repair regression | E2E/OpenAPI/capability346passed; metadata23passed plus1real kernel migration/restore; Windows launcher/runtime31passed |
| Official full project check | `scripts/check.ps1` exit0: tutorial/capability, Ruff/format/mypy, full backend, localization/lint/typecheck, full frontend and build |
| Linux/native archive/CI | Linux publication deferred; remote CI is not counted as passed by these local results |

All browser fixtures are synthetic in a separate temporary workspace. Traces,
screenshots and failure diagnostics are outside Git. Failed attempts remain
separate from successful reruns. No claim of full JMP numerical parity is made.

The independent integration reviewer raised a suspected Gaussian-objective
import incompatibility. The existing type is an alias of the versioned union;
an actual API preflight/commit/GET/idempotent replay passed before any production
change, so that finding was withdrawn. The separate combined-category-budget
finding was reproduced and fixed at the domain error boundary. Review suggestions
were verified, not treated as evidence of a bug by themselves.
Root's additional reader audit found generated-initial-design-only parsing in
two managed-report readers. The repaired dispatch verifies the bounded initial
receipt and only the requested history. Follow-up independent source review
found no further report-reader or unguarded generated-seed consumers. One browser
attempt immediately after an isolated-server restart failed before upload with
connection refused; the rerun starts after an observed ready health response.

The first completed full run exposed additional integration contracts: current
migration lists/table ownership, Windows launcher API/minimum-metadata versions,
GPR capability cross-link expectations, E2E stage registration/coverage and the
initial-design OpenAPI union. New import fixture writes also require explicit
same-origin headers under the existing static E2E security check. Two launcher
tests stopped before their intended port checks because the isolated worktree
did not yet have its own `.venv`; this is an environment failure, not evidence
that port ownership protection failed. The repository bootstrap is used to
create the real hash-locked worktree environment; no test is skipped or replaced
with a fabricated interpreter file.

Run chronology is preserved: an initial4440-test run stopped at5% for the report
reader repair; the next4452-test run stopped at18% after two stale augmentation
test failures. The next completed run had4415passed/27failed/10skipped in5462.32s.
After integration fixes, the official full check completed with zero failures.
Its10 skips cover platform-specific POSIX behavior and Windows symlink privilege
limitations, not ignored statistical failures. Existing deprecation warnings and
the Vite large-chunk warning remain; no dependency upgrades were used to hide them.
One agent's initial narrow run imported an older editable checkout and produced
32failures/314passes; rerunning with explicit current-worktree `PYTHONPATH`
produced346passes. That environment mistake is not evidence about this product.

## Commands And Environment

Executed locally on Windows with CPython3.10.11, NumPy2.2.6, SciPy1.15.3 and
scikit-learn1.7.2. `$python` denotes the verified existing Python3.10 environment;
`$evidence` denotes an external synthetic temporary directory. Commands ran from
the isolated worktree with `PYTHONPATH` set to its `backend` directory. BLAS/OMP
threads were limited to one. The final official check uses the repository's two
frontend workers; an earlier frontend run used one. Heavyweight fit suites were
not run concurrently. The final official check uses the worktree's own hash-locked
`.venv`, created by the existing `scripts/bootstrap.ps1`.

```powershell
$env:PYTHONPATH = "$PWD\backend"
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:DATALAB_GP_REFERENCE_MODE = 'independent'
& $python -m ruff check backend
& $python -m ruff format --check backend
& $python -m mypy backend/app
& $python -m pytest backend/tests --durations=25 --junitxml="$evidence\backend-final-tests.xml"
npm --prefix frontend run test -- --run --maxWorkers=1
npm --prefix frontend run lint
npm --prefix frontend run build
& $python tests/e2e/bo_dataset_import.py --base-url http://127.0.0.1:8614 --output "$evidence\import-ui-report-ready" --isolated-workspace
& $python tests/e2e/bo_progress.py --base-url http://127.0.0.1:8614 --output "$evidence\progress-final"
& $python tests/e2e/bo_xy_gpr_navigation.py --base-url http://127.0.0.1:8614 --output "$evidence\gpr-fit-evidence" --isolated-workspace --fit
git diff --check
```

The final end-to-end project command (exit0) was:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
$env:PYTEST_ADDOPTS = '--tb=short'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

The E2E commands deliberately create synthetic datasets/studies. Run them only
against a separate synthetic workspace, never a user's workspace. Progress/GPR
evidence was captured before the final report-reader-only repair; the import
and managed-report workflow was rerun after that repair. Built UI verification
is not a Linux release-archive verification. The existing full native CI suites
and release-ready gate are preserved, not replaced by these focused tests.
After the official full check, `bo_dataset_import.py` was rerun once more using
the new worktree `.venv` and explicit same-origin helper, with output directory
`import-ui-final`: both recommendation reviews returned200, completed trials
increased3 to5, restored state/report checks passed and pageerrors was empty.
The original observations SHA256 remained
`986df333f53042eeb1d67aaf138a7d99d5e9508dcb76dd95e78c5dd6753d2680`.

## Integration

Immediately before integration, `git fetch origin` confirmed origin/main still
at BASE0070640. The original main worktree's untracked `docs/jmp/` and
`examples/image2.png` are preserved and excluded from this change. Publication
uses a normal fast-forward/push, without force or protection changes. Resolve
this verification snapshot's commit with
`git log -1 --format=%H -- docs/bo_xy_start_validation.md`;
GitHub's commit checks are the source of truth
for subsequent remote CI status. No release/tag/archive is published here.

## Rollback Boundary

Only revert this change's commits in reverse order after explicit approval.
Never delete a workspace, dataset, study, model or result to roll back code.
Older code does not know the imported initialization receipt/metadata34.
Use a verified pre-upgrade offline backup for an older-code workspace; code
revert alone does not downgrade metadata or convert imported observations to LHS.
