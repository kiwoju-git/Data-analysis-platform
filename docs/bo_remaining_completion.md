# BO Remaining Work: Implementation And Verification

## Scope And Status

This audit covers the approved November 14 scope: whole-factor Profiler,
immutable diagnostic views and reports, explicit renewal of unconfirmed legacy
EI recommendations, and one bounded mixture group. It does not claim native JMP
numeric parity. The owner will perform that comparison. No Linux Release is
published by this task.

Baseline origin/main: `a9abb4bac0f6104b8fd6ac270edcc80a5bc32050`.
Implementation baseline: `41143beeb4f1935201717e5ff8e9f18ae266f4fe`.
Integration contract: API44, metadata37, BO method0.17.0.
Feature source: `1937e72526512241158669d05e5c863dc0d7b29f`, on
[draft PR10](https://github.com/kiwoju-git/Data-analysis-platform/pull/10).
[CI43553019942](https://github.com/kiwoju-git/Data-analysis-platform/actions/runs/43553019942)
is the first native gate run for that feature commit. Final integration and gate
outcomes are pending, not verified; main has not been updated.

| Deliverable | Implementation | Verification still required |
|---|---|---|
| Whole-factor Profiler | Source-locked numeric/mixed response and desirability matrix, shared response scales, separate latent/predictive SD, categorical points, paging | Full regression and native gates |
| Saved diagnostics/reports | Bounded server receipt, explicit immutable save, restore, source catalog, offline HTML, owner retention and backup | Final enhanced backup/report regression and native gates |
| Legacy recommendation renewal | Historical GET/report values preserved; explicit new review uses exact old model/candidates/options and records parent digests | Final full compatibility and native gates |
| Mixture study | Explicit study8, import2, fit, feasible candidates, manual/maximin review, atomic trials, observations, replicas, next cycle | Full regression and native CI |

Implementation is not deployment evidence. Tests listed below are task-local
evidence; they do not substitute for final-commit native gates.

## Statistical And Display Contracts

`BayesianProfileMatrix` uses existing interactive scatter, tooltip, keyboard and
pin behavior. It does not fit a new model when changing displayed quantity,
page, locale or viewport. Every curve retains the applied model, history and
holds. A later draft must be evaluated before becoming the applied view.

The server evaluates complete view requests with bounded sequential chunks.
Receipts are app-owned, memory-bounded and short-lived. Save accepts a receipt
identity and expected digests, not client-supplied numerical results. Saved
views have no trial-confirmation/novelty permission. Historical views remain
readable after newer observations. Reports render stored values without fitting,
CV, re-importing data or replacing the source with the latest history.

Conditional LOO holds full-fit parameters fixed. It is not independently tuned
fold-local validation. Mean, latent SD and new-observation predictive SD retain
their existing definitions; jitter is not presented as physical noise.

An absent-policy historical EI selection is readable without recomputing its
stored scores. If it has not already been confirmed, confirmation requires an
explicit renewal. Renewal creates a new selection and sidecar parent hashes
under `positive_beta_integral_v2`; it does not overwrite the original, refit,
use current UI draft options, or create pending trials automatically. Previously
confirmed requests replay their exact committed batch.

Mixture support is specified in [the backend contract](bo_mixture_backend_contract.md).
There is one continuous group of 2-8 components, at most10 original factors in
total and1-4 desirability responses. Lower/upper pseudocomponent coding is
separate from actual-coordinate spacing. Raw amounts are never normalized to
force closure. Numeric-only mixtures do not invent a categorical predictor.
Nominal/ordinal process factors retain their existing semantics.

Component profiles co-vary the other components along declared excess/deficit
ratios. They are not independent component effects. Fixed components and zero
balancing mass have explicit unavailable states. Actual bounds, closure and
process constraints still apply to every point. Candidate sampling is bounded
and seeded, not claimed exactly uniform or globally optimal. Supported mixture
selection is manual base-posterior review or greedy maximin; unverified scalar
EI/ETI, mixture MaxPro and multiple mixture groups are not advertised.

## Compatibility And Privacy

- Metadata35 adds renewal lineage;36 adds saved diagnostic views;37 extends
  constrained study/model/candidate/selection/import contracts. Existing JSON
  documents are not reserialized or given new default fields.
- New numeric affine state2 and mixed domain/kernel codec2 are explicit opt-ins
  for mixture transforms. Ordinary historical numeric/mixed codec1 readers
  retain their original bounds and interpretation.
- Mixture batch13 reports read the exact selected model/history/candidates. A
  later trial's status is not overlaid onto an old report.
- Synthetic fixtures only. No private JMP training files, user datasets,
  workspaces, models or screenshots enter the Git change.
- Existing GPR menu, BO scalar/mixed paths, DOE/RSM, LAN warnings, thread/time
  budgets, safe JSON/NPZ loading and offline release checks are retained.

## Evidence Log

Local environment observed: Windows10 build19045, CPython3.10.11, CPU-only,
8GB RAM. This is not evidence of native Windows11 or Linux execution. Heavy
tests/builds/model jobs are serialized; at most two auxiliary agents are active.

| Check | Fresh task-local evidence |
|---|---|
| Domain/closure mathematics |44 tests passed with independent algebra and hand-checkable fixtures; scoped independent review passed |
| Diagnostic receipts and ownership |103-test combined run passed, including10 view tests and49 historical-reader tests |
| Saved-view report regression |4 passed; review found lost warnings/coverage metadata, corrected with failing then passing tests |
| Matrix request fences |15 focused frontend tests passed, including queued stale request rejection |
| Mixture backend lifecycle |220 focused tests passed before two independent boundary-review findings |
| Mixture boundary fixes |3 failures reproduced: two decimal path endpoints and numeric training snapshot boundary; all3 passed after explicit codec/profile fixes |
| Mixture UI/import |56 focused tests passed; additional draft invalidation/collapsed replica regressions8 passed; typecheck and scoped ESLint passed |
| Independent UI review fixes |20 tests passed after reproducing missing applied settings, budget labels and exact-response guards; scoped re-review passed |
| Historical mixture report integrity |2 API regressions passed; final byte-corruption/direct-reader rerun1 passed. Byte corruption is rejected without repair; later mutable observations do not replace historical report source |
| Profiler pagination |2 KO/EN failures reproduced;13 covering frontend tests passed after scoped fixed-size icon control repair; browser geometry check added |
| Final process-axis review fixes |8 failures reproduced;65 domain/design/API/view/save/report tests passed in173.35s. Independent scoped review passed; a further EN/KO coverage-wording regression passed2 tests |
| Runtime and E2E wiring |Runtime entrypoint2 tests and suite partition96 tests passed; old stages retained |
| Full backend type check |`python -m mypy backend/app` passed for356 source files after resolving the earlier20 typing errors, without skip-import or ignore overrides |
| Localization boundary |`node scripts/check_frontend_localization.mjs` passed:3,047 source strings and4,727 keys; synthetic Korean user labels remain test data, not translated system strings |
| Frontend production build |Fresh build passed after UI review fixes; existing large-chunk warning remains |
| Populated migration/restore |5-test run passed before additional backup/report assertions; final enhanced rerun remains to be recorded |
| Built mixture cycle |Fresh synthetic run `bo44-built-20261114-122341` passed import8 -> fit -> matrix/save/offline HTML -> candidate review/confirm2 -> observed10 -> next fit/candidates -> exact historical view restore |
| Built numeric and legacy renewal |Fresh synthetic run `bo44-built-20261114-122607` passed matrix values/metrics, KO/EN 1024/1440, icon geometry, pin/keyboard, stored offline HTML and explicit old-review renewal/confirm/replay with old bytes unchanged and no renewal refit |
| Archive coverage wiring |Source review found missing new BO journeys in the archive harness. Added mandatory initial/two-restart/server-stopped roundtrip checks; root reran212 pure contract/controlled-runner tests, all passed in2.85s. This is not actual archive execution |
| Native full CI / archive |Not yet verified in this audit |

Failed built attempts are retained in local synthetic diagnostics. They exposed
three fixture assumptions: a single-curve locator became ambiguous after adding
the matrix control; the fit response wait matched the existing model-list GET;
and exact URL matching omitted the preserved selected dataset. A fourth fixture
compared typed API JSON to stored raw bytes despite the existing response-only
`response_uncertainty: null` projection. The corrected fixture still verifies
actual stored hashes and uses an exact original-byte CAS for its historical seed.
No production hash validation was relaxed to make these tests pass.

A subsequent source-only archive review found that the new BO journeys were
wired to source/built-UI E2E but not the completed archive harness. That is a
coverage gap, not a reproduced product failure. The same helpers are now
connected to archive initial/restart/second-install verification, with a
mandatory source/hash/phase validator. Actual archive execution remains pending.
The task-local
saved-report tests above opened HTML with browser networking disabled while the
server remained running. They must not be described as server-stopped checks;
the archive harness separately stops the original server before reopening HTML.

Final whole-branch review found two additional mixture process-profile boundary
issues: a conditionally fixed continuous interval generated duplicate points,
and discrete axes ignored the requested display count above100 levels. Both were
fixed with failing then passing tests and independent scoped re-review. A fixed
interval now retains one actual point; a discrete path uses at most the requested
count of executable, endpoint-inclusive levels and reports feasible coverage.
The shared two-point API minimum is supported. Reports say "all available levels"
when every feasible level is displayed, not all originally declared levels.
These defects were not classified as JMP parity differences or waived because
the main browser journey passed.

The first full check stopped on two overlong SQL literals in new tests. Those
were wrapped without changing their queries; full backend Ruff and format checks
then passed (653 files). Full check attempt2 is running, with4,653 backend tests
collected. No full-suite or CI pass is claimed until its process completes.

The review caught real boundary failures, not alleged JMP disagreements. A
representable transformed coordinate slightly above1 is preserved in the new
affine domain, not clipped or accepted by weakening historical readers. Decimal
Profiler endpoints are generated without changing user-entered amounts.

## Reproduction And Rollback

Use an isolated synthetic workspace and the existing PowerShell entry points:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -Suite workflows -KeepWorkspace
powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -Suite context -KeepWorkspace
powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -Suite data -KeepWorkspace
powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -Suite prediction -KeepWorkspace
```

Rollback is only by reverting this task's recorded commits in reverse order.
Do not reset main or delete workspace/model/result files. Reverting code does
not reverse metadata35-37 or convert new study8/view/batch13 artifacts into older
schemas. Before upgrading a valuable workspace, use the documented offline
backup procedure with the server stopped. Older code may require a separate
pre-upgrade backup; never downgrade the live database by editing schema markers.
No rollback has been executed.
