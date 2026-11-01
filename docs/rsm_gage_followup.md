# RSM and Gage Follow-up

## Baseline and Acceptance

- BASE_SHA: `30422e6ae9ea9fb892c198e7c212524b7cc6bfc4` (local and origin/main after fetch).
- Implementation branch: `feat/rsm-gage-followup`, isolated worktree.
- User file `examples/image2.png` remains untouched in the original checkout.
- Root AGENTS.md, addendum, applicable method contracts and existing implementation are the requirements. `data_prd.md` is absent, not reviewed.
- No user measurements were supplied. All new fixtures are synthetic, including the 60-row Gage fixture.
- New Linux Release publication is deferred by the latest user instruction. Existing Linux checks and archive verification gates remain required; CI artifacts are not a published Release.

Acceptance: editable numeric drafts survive input and same-source rerenders; stale completions cannot replace the current draft; RSM paste is atomic and source-locked; residual views use the final model; CCC search/plot ranges do not change coding; Gage validates actual crossed cell counts and reports the selected full/reduced ANOVA consistently; legacy artifacts retain their bytes and interpretation.

Risks: numerical degeneracy and leverage; pooling changes the inferential model; axial boxes are not observed convex hulls; new defaults must not enter historical checksum payloads; request invalidation must not delete server commits; diagnostics and tests must not expose user data. No SQL change is planned (metadata remains 24).

## Evidence Ledger

| Item | Source-confirmed | Reproduced | Fixed | Unit | API | Browser | Release archive |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Optimizer deferred event access, coercion and draft reset | yes | parser/hook fixtures; original browser symptom unverified | implemented | strict draft/restore/stale success/error/finally tests | source/optimizer API tests pass | Linux workflows, below | unverified |
| RSM/optimizer trailing-zero formatter | yes | Node probe below | implemented | semantic numeric/interval tests pass | stored numeric values unchanged | Linux keyboard/result checks | unverified |
| RSM full response paste | missing connection | 31-run/invalid/source-change fixtures | implemented | parser/atomic application tests pass | immutable revision paths tested | Linux 31-run form | unverified |
| Final-model RSM residual 4-in-1 | missing view connection | independent OLS/degenerate/point-limit fixtures | implemented | 26 backend and 9 SSR tests pass | new/legacy read/report tested | Linux raw/standardized | unverified |
| CCC axial/cube/custom region and legacy semantics | yes | 4-factor 10..20 cube / 5..25 axial fixture | implemented | 11 domain tests pass | 35 plot/storage/security plus 14 existing optimizer API tests pass | Linux custom hold/view/restore | unverified |
| Gage three-column preparation/filter contract | yes | synthetic 10x3x2 and failure fixtures | implemented | included in 51 Gage tests | filtered preflight/run, restore, report tested | Linux CSV/form/filter/restore | unverified |
| Gage explicit interaction pooling | retain-only confirmed | weak/strong interaction independent reference | implemented | full/reduced SS/DF/components tests pass | legacy explicit/retain schema1 read unchanged | Linux both policies and HTML | unverified |

Source inspection is not browser reproduction. A past CI result is not evidence for this change. Native checks, new CI runs, remaining limitations and exact rollback commits will be recorded after execution.

## Implementation Boundaries

- `responseOptimizerDraft` and `useResponseOptimizerRun`: strict string-to-request boundary,
  full saved-setting restoration, draft/source ownership. `ResponseOptimizerPanel` copies
  event values synchronously and shows distinct X bounds/Y preferences. Multiple saved
  linear constraints remain in reruns instead of silently retaining only the first.
- `DoeResponsePasteDialog` / `rsmResponseDraft`: full run-order validation before one atomic
  draft update, preview source key, no automatic save. Saved revisions require explicit correction.
- `doe_residual_views` / `DoeResidualPlots`: final-model raw/standardized residuals, complete
  histogram/QQ calculation before display limits, units, unavailable reasons, stored-only HTML.
- `rsm_region` / `rsm_regions` / `rsmRegion`: separate input, cube, axial, observed and selected
  bounds; unchanged center/scale and original discrete lattice. Hull membership is separate
  from requested-box/linear-constraint feasibility.
- `gage_rr_data`: one preparation path for preflight/calculation, full identities and source
  rows, filtered snapshot, structural balance separate from readiness. Cell counts determine r;
  explicit replicate IDs need be unique within each cell, not globally identical between cells.
- Gage full ANOVA is computed first; `auto_pool` only pools an available interaction p >= alpha.
  The selected final table, components, percentages and NDC use the same denominator model.
  New UI sends auto_pool explicitly; omitted legacy policy remains retain.
- API27; RSM/optimizer method0.5.0; Gage0.2.0. Metadata24 and existing design hashes stay unchanged.
  Readers dispatch historical schemas without injecting new defaults into old hash payloads.

## Local Check Record

- Windows CPython3.10.11, Node22.23.2, CPU-only; shared installed virtualenv with this worktree's
  backend on PYTHONPATH. No user workspace used. Local commands mirror scripts/check.ps1;
  the isolated worktree does not have a separately bootstrapped `.venv`.
- Full backend Ruff check/format and mypy239 source files passed. Frontend production build
  passed (existing large-chunk warning); full ESLint passed with12 existing refresh warnings.
- Initial full Vitest:1013 passed/2 failed. One fixture omitted required design options;
  one expected editable saved responses contrary to the new explicit-correction contract.
  Corrected tests and relevant135 tests passed. Two concurrent-worker full reruns
  hit existing module-import timeouts (one also read a helper while it was being
  edited). With the source frozen and one worker, all118 files/1,031 tests passed
  using unchanged timeouts. Native default-worker checks remain separate evidence.
- Initial tutorial version assertions failed as expected after method changes. Actual API
  reruns retained all numeric expectations/tolerance1e-8; only3 method-version fields changed.
  Tutorial suite11 passed, including optimizer and explicit-retain Gage reference execution.
- Full localization initially reported13 unregistered Gage labels; explicit KO/EN keys
  fixed them. Checker verified2,955 source strings/4,457 keys;22 i18n tests passed.
  Browser suite code review is not an executed browser pass.
- The long local backend full run was stopped at28% in favor of exact-commit native CI;
  it is **not** a full pass. Its initial tutorial version failure and an in-flight
  lock-maintenance fixture mismatch are retained as failures, not hidden by this stop.
  The final source must pass the complete native checks below.

## Initial Native CI Evidence

Branch commit `aeca1b34d15a4ca0c3aacffbe41b573fcf21dec9`,
[run41290140121](https://github.com/kiwoju-git/Data-analysis-platform/actions/runs/41290140121):
early Linux context and prediction browser suites passed. Workflows initially
failed in the new residual assertion: the DOM contained4 chart SVGs plus3
decorative legend-key SVGs. No child-page JS or asset error was recorded. The
test now counts `svg.chart-frame-svg` and still requires exactly4 charts; this
is a harness correction, not evidence of a product chart failure. Main is not
promoted on this partial run.

The same run passed npm security but failed Python security for the newly
reported setuptools advisory below. All initial failures remain in CI history.

Python3.11 completed with3,092 passed/13 skipped/7 failed: missing Gage stage/mock
registration and stale result-schema expectations. Commit435bd47 fixes the
registrations and aligns declared/actual RSM->zoom->Gage ordering without removing
stages;307 affected contract tests passed locally.

Linux additionally exposed a newly added tutorial assertion requiring an exact
optimizer coordinate on a nonunique desirability=1 plateau (pressure differed
by approximately1.75e-7 from the recorded Windows output). Commit750a2a7 keeps
the golden JSON and1e-8 tolerances intact, and verifies bounds/constraints,
source hashes and returned prediction with independent literal quadratic OLS.
It establishes more than one feasible point with desirability1 rather than
claiming a unique coordinate. Existing unique-optimum CCC fixtures are unchanged.

[Browser-only run41290583204](https://github.com/kiwoju-git/Data-analysis-platform/actions/runs/41290583204)
passed context/prediction again. RSM paste, stored raw/standardized residuals,
optimizer typing/caret/locale/1024-1440px and stale committed-request checks ran
before a genuine390px page-overflow failure. Captures also showed the long first
factor name painting into the next optimizer cell. Scoped name/notice wrapping
and painted-text assertions address these; their browser effect requires the
next run. This diagnostic-only run is not a release-ready pass.

## Combined Native Evidence

[Run41291514419](https://github.com/kiwoju-git/Data-analysis-platform/actions/runs/41291514419)
uses committed source `cddc36af00a2fb90e9c13bfe828dc225761c1731`.
The completed early workflows/context/prediction suites ran on Ubuntu24.04,
Python3.12.15, Chromium149. They are browser evidence, not Windows or archive evidence.

- RSM: invalid30/valid31-run paste, saved revision read-only state, backward final model,
  raw/standardized4-in-1, hold outside cube but inside axial bounds, source-locked custom
  view/report/restore and original stored-byte comparisons passed.
- Optimizer: KO/EN1024/1280/1440px typing, intermediate drafts, caret/focus/mount retention,
  no navigation, weights retained, stale response rejection and committed artifact preservation
  passed. Long factor names now wrap within their own cell; no cross-cell painting is asserted.
- Live widths1920/1440/1280/1024/900/768/390/1440 passed page-overflow and compact4/3/2/1
  checks. Real Chromium tab zoom1/1.25/1.5/1 passed in KO/EN (inner widths1440/1152/960/1440),
  with zero analysis POSTs and unchanged draft/plot coordinates/committed source.
  This is browser zoom, not deviceScaleFactor.
- Gage: synthetic60 rows,10 parts x3 operators x2 measurements, CSV ingestion and actual
  three-select form execution passed. Auto-pool with alpha0.1 pooled interaction
  (p=0.9999999999893081); retain with alpha0.05 kept it. KO/EN1024/1280/1440px,
  filtered imbalance with no analysis POST, saved alpha/policy restoration, downloaded
  HTML full/final ANOVA and offline HTML opening passed. Report/source hashes were compared.
  Gage report coverage remains summary because the payload lacks interaction-means plots.
- Python3.11.17 completed3,100 passed/13 skipped/116 warnings in464.44s.
- Linux Python3.12.15 completed3,100 passed/13 skipped/116 warnings in379.56s;
  Ruff/format, mypy239 files, lint/typecheck/build and default-worker Vitest118 files/
  1,031 tests passed. Full Linux critical-path browser E2E also passed.
- Dependency-security passed all five Python inventories and npm runtime/development audits.
  Setuptools84.1.0 was installed. No advisories were reported by this execution.

An independent review of Gage preparation, ANOVA denominators, filtered snapshots,
legacy defaults, redaction and frontend restore found no additional concrete defect.
This is source-review evidence, not a separate execution of the tests above.
Immediate narrow-window Gage screenshots could capture the existing drawer mid-transition;
the harness now waits on actual animation completion and verifies drawer/main geometry
before capturing. Its settled-state assertions require a subsequent browser run.

Direct screenshot review also found Korean warning prose on the English Gage screen.
The existing presenter did not map Gage warning codes. A Gage-scoped display dictionary
now localizes known codes while keeping the code visible, preserving unknown escaped
messages and leaving stored DTOs unchanged. Scope/data labels get separate rows with
a scoped gap. KO/EN notice/payload-preservation tests and browser assertions cover this
follow-up; actual settled captures belong to the subsequent exact-source run.

The initial Windows GP resource run failed its existing1e-9 restored/fitted prediction
comparison at the first2,000-row numeric/single/KFold case. The original log did not
record the error magnitude;24 smaller cases had passed. Independent local investigation
found identical kernel rows but query-batch-dependent floating-point mean accumulation.
That finding is distinct from claiming the exact original hosted residual was reproduced.
The tolerance is not increased. Full native checks, including this resource gate and
the completed archive, remain required for the final source; these partial results
alone do not authorize main promotion.

The follow-up mean fix uses per-row compensated summation of the same kernel/dual products;
normalization, fitted hyperparameters and noise policy are unchanged. Independent Decimal
and query-batch invariance tests plus141 relevant GP/reference/API/worker tests passed locally.
The existing1e-9 restore tolerance was not widened. See
[the detailed numerical investigation](gp_resource_benchmark_contract.md#posterior-mean-follow-up-2026-11-01).

Final acceptance is the `release-ready` job for the exact source being promoted,
not this earlier run. Its JSON receipt and the exact-source archive validation report
are CI artifacts. Keeping the evidence there avoids committing a source SHA into its
own source after packaging. No tag or Release is published in this follow-up.

## Native Setuptools Maintenance

Candidate security CI reported
[GHSA-xmj3-9gf7-h52w](https://github.com/pypa/setuptools/security/advisories/GHSA-xmj3-9gf7-h52w)
in setuptools83.0.0. The patch is84.1.0, not a change to NumPy/SciPy/sklearn.
Native maintenance [41290641290](https://github.com/kiwoju-git/Data-analysis-platform/actions/runs/41290641290)
passed Windows3.10 and Linux3.11/3.12 generation, all5 profiles' fresh offline
hash-locked installs and pip check. Commitscb4a117/e6358a2 preserve every other
package version/hash. The advisory audit on the imported final locks is a
separate required gate. See [security receipts](dependency_upload_security.md).

## Limitations and Rollback

Gage remains balanced crossed ANOVA (at least2 parts,2 operators,2 valid measurements per cell).
No nested/unbalanced REML, Xbar-R, new CI/%Tolerance, or actual Minitab output parity is claimed.
Legacy incomplete residual payloads report their limitation instead of being refit.
Axial boxes include extrapolative combinations; verification experiments are still required.
Physical intranet PCs/firewalls and the original user's unprovided measurements are not tested.

Revert only this task's explicit commits in reverse order after checking intervening user work.
Do not reset/force-push or delete workspace/model/result files. No DB migration needs reversal;
old code may not read new RSM/Gage/optimizer result schemas, so code rollback is not artifact rollback.
UI-only rollback must retain API27 types and schema readers and requires a separately tested patch;
blindly reverting the integrated contract commit is a full feature rollback, not UI-only.

## Numerical and Input Evidence

The baseline formatter was executed in Node22.23.2: `100000 -> "1"`,
`1e-10 -> "1.00000e-1"`, `1e10 -> "1.00000e+1"`. This is a display
defect, not evidence of a fitting error. Both RSM/optimizer now call the existing
semantic formatter without changing numeric data. Initial optimizer/paste/source
tests are tracked separately from actual browser reproduction.

## Security Gate Follow-up

Fresh npm audit on 2026-11-01 reported 12 moderate affected package paths from
one newly published advisory, [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249).
The dependency is minimatch in ESLint/typescript-eslint development tooling,
not the built application runtime. The official advisory identifies pattern
amplification and patched version11.0.1. No audit exception/severity downgrade
or `audit fix --force` is used.

Scoped overrides select11.0.1 for the four existing consumers. Their actual
call sites use `Minimatch` or the named `minimatch` API; no application kernel
or numerical dependency changes. Package metadata supports Node18/20/>=22;
the project uses22.23.2. The package and nonrecursive-glob-match dependency
use permissive BlueOak-1.0.0, and brace-expansion/balanced-match use MIT.
They are development-only, CPU-only, require no network at runtime, and add no
native build prerequisite. A clean install audits zero advisories; full lint,
test/build and native CI remain necessary to verify the major-version override.
Lock review confirms only the minimatch dependency subtree changed.
