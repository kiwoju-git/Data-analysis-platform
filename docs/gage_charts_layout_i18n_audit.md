# Gage Charts, Result Layout and Localization Audit

## Baseline and Acceptance

- BASE_SHA: `fb82be61a8af85b5e4cc5e787e50ad130dc82d67`; local HEAD and origin/main matched after fetch.
- Isolated branch/worktree: `feat/gage-six-panel-i18n`.
- Original untracked `examples/image2.png` is protected. No user measurements are supplied.
- Root AGENTS.md, current addendum and method/runtime/chart/report contracts apply.
  `data_prd.md` and nested instruction files are absent.
- API27 advances to28; Gage method0.2.0/result2 advances to0.3.0/result3 with plot schema1.
  No SQL change is required; metadata24 remains unchanged.

Implementation order: A saved plot payload and independent numeric tests; B interactive
six panels and stored-only HTML; C scoped metric layout; D explicit dynamic localization;
E native/browser/exact-archive validation, main promotion and a new Linux prerelease.
Read-only audits and red tests may run alongside an earlier implementation stage.

Acceptance: existing full/final ANOVA and variance components remain numerically identical;
all chart summaries use every prepared valid observation; only raw display points are capped;
original part/operator/replicate identities are not newly persisted; schema1/2 bytes remain
readable unchanged; translations never modify request/data values; actual built UI and HTML
are checked, not just JSX or file existence. All existing security/product/archive gates remain.

Risks: extreme finite values/overflow, zero within variance, large-repeat c4 precision,
raw-display sampling bias, accidental label disclosure, historical coverage overclaims,
category interpolation, plot/page limit drift, untranslated dynamic errors and tight result
cards. These need explicit tests and unavailable states rather than fabricated values.

## Evidence Ledger

| Area | Source-confirmed | Reproduced | Fixed | Unit | API | Browser | Archive |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Saved six-panel summaries | confirmed missing plot payload | four red tests before implementation | fixed | numerical/strict payload tests pass | filtered54/schema3 restore and stored export pass | unverified | unverified |
| Interactive and static plots | legacy missing interaction acknowledged | new feature; malformed display guard reproduced separately | implemented | adapter/SSR and static report tests pass | stored export/checksum pass | unverified | unverified |
| Run Chart label/value and p precision | missing card layout; fixed-fraction p formatter | nonzero-to-zero SSR red test | fixed | semantic formatter/card tests pass | no calculation change | geometry unverified | unverified |
| Similar result layouts | scoped inventory completed | no blanket failure assertion | only confirmed Run cards changed | existing layout source reviewed | not applicable | see coverage inventory | unverified |
| Dynamic English system text | helper return bypassed display translation | Capability SSR red tests | fixed at UI boundary | semantic DTO/locale/user text tests pass | transport unchanged | built-English workflow unverified | unverified |

Past task results are not evidence for this source. Each run records its source, OS/Python,
fixture, actual stage and failure diagnostics. Synthetic60 observations are not user data.

## Implementation and Local Evidence

- `gage_rr.py` calls `build_gage_rr_plot_bundle` once after final components, using
  the same prepared observations. Full/final ANOVA functions are unchanged.
- New `gage_rr_plots.py` and typed `schemas/gage_rr_plots.py` preserve complete
  summaries and explicit unavailable states. A malformed negative-physical-value
  validation gap was independently found and closed; it was not an observed
  production ANOVA failure.
- New `gageRrChartModels.ts`, `GageRrResultCharts.tsx`, summary bar/vertical-box
  primitives and scoped CSS render saved values. Current components read the
  bundle; legacy components use the saved variance table. Each panel has a visible
  heading, and operator segments use separate paths. Four malformed payload
  probes initially threw or silently lost points, then passed safe rejection tests.
- Independent review caught an offset/header overlap risk and a large-cell
  `Math.min(...values)` argument-limit failure. Gage headers reserve a separate
  row; its global extrema are reduced without spreading the complete cell array.
  These are source/helper findings, not prior full-app browser reproductions.
- New `gage_rr_plot_report.py` uses stored bundle data only. All static pages
  retain global scales; six sections can contain more than six SVGs when paginated.
  Generic Gage renderer2.3.0 reports schema1/2 as summary rather than full coverage.
- Run metric cards and Capability validation DTO are independent display changes.
  [Localization/layout inventory](ui_localization_coverage.md) distinguishes
  source review, isolated SSR tests and still-unverified menu states.

Runs so far (2026-11-03/04, Windows CPython3.10.11 and Node22.23.2):

| Command/scope | Observed result |
| --- | --- |
| Focused Gage calculation/schema/API tests | 43 passed initially; 32 plot/API tests rerun after stricter physical-value validation passed |
| Stored Gage/family report and coverage tests | 80 passed; latest Gage report18 passed |
| `test_gage_rr_followup_api.py`, `test_analysis_report_source.py`, `test_managed_report_api.py` | 44 passed, 2 Windows symlink-privilege skips |
| Tutorial/capability regression | 35 passed; existing Gage numeric reference unchanged |
| Focused Run/Capability/Gage display-boundary tests | 30 passed |
| Gage chart adapter/SSR plus existing panel tests | 17 passed before final guard/performance additions |
| Frontend production build | passed; existing large-chunk/plugin-time warnings remain |
| First full Vitest run | 1052 passed, 7 failed: old runtime fixture, intentionally localized Gage labels, SVG attribute-order-dependent assertions; fixes applied |
| Failed-file and Gage adapter rerun | 5 files / 324 tests passed after fixes; not a replacement claim for a fresh full run |
| First full ESLint | 2 new unknown-template errors plus warnings; new errors fixed, rerun required |
| Release receipt negative tests | 235 related release/driver tests plus 8 UI receipt tests passed; actual archive still unverified |
| Root backend/source Ruff check | passed |

Counts above overlap; they are not an aggregate unique-test count. Browser and
archive evidence must come from the new run, not earlier successful releases.
New E2E modules are wired into the existing separated suites and exact-archive
journey; their presence alone is not a pass. Final native CI and archive reports
will be attached to the candidate release and bound to its source SHA.

## Candidate Release

Next unused candidate: `linux-gage-ui-2026.10.7`. Existing releases/tags are not
replaced. README installation commands target that candidate and explicitly
require the published exact-source validation/checksum assets. Until gates and
publication finish, main push and release are pending. No source self-SHA is
committed after final archive creation; final evidence belongs in release assets.

## Numerical Policy

The existing selected ANOVA remains authoritative. Components use saved percentages without
renormalization; R diagnostics use cell ranges and existing three-decimal D3/D4 constants
for repeats2..8. Repeats9+ use sample SD and log-gamma c4/B3/B4. Xbar limits use selected
ANOVA repeatability SD, not Rbar-derived SD. Operator boxes use all individual values and
type7 quartiles/observed 1.5-IQR whiskers. Interaction always shows actual cell means,
including pooled interaction results. Index aliases are generated at the display boundary.

Reference sources reviewed on2026-11-03:
- [Minitab graph definitions](https://support.minitab.com/en-us/minitab/help-and-how-to/quality-and-process-improvement/measurement-system-analysis/how-to/gage-study/crossed-gage-r-r-study/interpret-the-results/all-statistics-and-graphs/)
- [Minitab interpretation](https://support.minitab.com/en-us/minitab/help-and-how-to/quality-and-process-improvement/measurement-system-analysis/how-to/gage-study/crossed-gage-r-r-study/interpret-the-results/key-results/)
- [NIST Xbar/R/S formulas](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc321.htm)

The requested Minitab example page was unavailable on the initial fetch. No actual same-data
Minitab execution has been supplied. Similar diagnostic workflow is not exact numeric parity.
The repeats9+ S switch and selected-ANOVA Xbar sigma are explicit product policies.

## Rollback Boundary

Only this task's commits may be reverted, explicitly newest first, after checking intervening
work. No reset/force push or workspace/result/model deletion. Code rollback is not artifact
rollback; previous code may not understand schema3. UI-only rollback must preserve compatible
readers and API28. Actual rollback requires a separate user request.

Implementation commits already recorded before native execution:
`816c0a1` (saved Gage plots/report/API contract) and `c10d07c` (interactive plots,
metric layout and localization). Subsequent verification fixes are listed by the
final release receipt; never revert a broad range containing somebody else's work.
UI-only rollback targets the UI commit and its later UI fixes, retaining API28
readers. Full rollback explicitly reverts this task's commits newest first; old
API27 code may reject new Gage result3, but no result files are deleted or rewritten.
