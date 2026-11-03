# UI Localization and Result Layout Coverage

Baseline: `fb82be61a8af85b5e4cc5e787e50ad130dc82d67`. This is the Gage six-panel / UI follow-up audit, not a reuse of earlier release evidence. All fixtures are synthetic; no user workspace was inspected.

## Evidence Levels

- **Source**: component, display helper and CSS inspected. This does not prove the built browser output is translated or non-overlapping.
- **Unit**: the current focused Vitest run exercised a pure helper or `renderToStaticMarkup`. The test-mode Vite plugin is disabled; these tests intentionally cover explicit dynamic display boundaries, not every compiled JSX string.
- **Source browser**: a real-form Playwright assertion ran through Vite's localization plugin. This does not establish packaged built-UI behavior.
- **Browser pending**: a real-form assertion exists but the listed state has not been verified. Final CI receipts include source SHA, OS, viewport and trace.
- **Unverified**: no new evidence for the listed state. Existing test files are identified as reusable coverage, not reported as current passes.

## Confirmed Changes

| Boundary | Before | Change | Current evidence |
| --- | --- | --- | --- |
| Run Chart approximate randomness cards | `.metric-card` had no grid/flex display or internal gap; label and strong value remained inline. `compact-definition-list` had no scoped pair layout. | `ResultMetricCard` uses separate label/value rows, 8px gap, tabular numbers, wrapping and content-driven height. The Run-only container uses 1/2/4 columns at 508/1028 CSS-pixel content widths. Details use separate dt/dd rows with 6px gap. | Source and51 native source-browser geometry stages verified; exact archive pending. |
| Run Chart small p-value | `maximumFractionDigits: 6` rendered a finite `1e-10` as `0` in both exact and approximate summaries. | `formatProbability` for p/alpha, `formatMeasurement` for expected runs/median, integer formatting for observed runs. No result or method calculation changed. | Reproduced in 2 KO/EN SSR red tests; fixed and unit verified. |
| Capability specification validation | Helper returned Korean `message` outside the JSX compiler boundary; English notice remained Korean. | Pure `capabilitySpecValidation` returns code/messageKey. `CapabilityPanel` translates at render time, preserving drafts, empty/one-sided policies and request values. | Reproduced in4 SSR red cases; actual source-browser input errors and KO/EN/KO passed in41668513163. Exact archive pending. |
| Run Chart warning DTOs | The first Linux source-browser English scan found seven Korean backend warning messages in the active panel. Registered JSX strings alone did not cover DTO messages. | `runChartNoticeKeys` maps the 20 current Run Chart warning codes explicitly at `ApiNoticeText`; shared exclusion codes are scoped to this panel. Stored messages, unknown escaped messages, codes and result values remain unchanged. | Browser failure reproduced; matching seven-message SSR red test added. Focused fix verification and exact-candidate browser rerun are tracked below. |
| Gage stored ANOVA/component display | Source/component names and stored enums/reasons were displayed as English/raw codes; full/final p paths differed and percent formatting could hide a small positive value. | Explicit semantic labels; stored enums remain visible as codes with translated explanations; full/final p use the same probability formatter; finite percentage values retain nonzero meaning. Locale-specific counts and translated control aria labels use stable `data-gage-control` test selectors. | Unit verifies KO/EN, `1e-10` final/full p and percent, unchanged JSON, legacy explicit/retain interpretation. Browser pending. |

The ui-ux-pro-max skill was read and its text-reflow/spacing and semantic-HTML guidance applied. Existing product colors, density and chart interaction are preserved. No new chart/design library or global metadata-card restyling was introduced.

## Inspected Layouts

| Screen and source | Existing layout found | Decision / missing evidence |
| --- | --- | --- |
| Gage, Capability, I/MR, Subgroup, Attribute panels | Shared `.metadata-grid` has `gap: 8px 14px`; strong values have min-width/wrapping protection. | Not classified as the Run Chart missing-gap defect. Long-text/computed geometry in each live state remains unverified. |
| Linear / regularized regression | Dedicated result tables/charts and semantic `reg.*` labels; predictor representation helper localizes only system labels. | Preserve existing layout and original predictor names. Current live success/failure/prediction geometry not measured in this audit. |
| PLS / GPR | `.result-definition-grid > div` has a 12px gap; numeric dd is nowrap. | Gap exists. Very long value/label risk is not a reproduced overlap; no blanket style change. |
| DOE model selection | `.doe-selection-description` already wraps descriptive values, uses label/value rows and a full-width stop reason. | Preserve prior fix; do not repeat an already-resolved defect claim. |
| RSM stationary point | `.rsm-stationary-coordinates .metadata-pair` already has 4px/12px gaps and wrapping. | Preserve prior fix. No new browser claim. |
| Response optimizer | Existing metadata summary and scoped constraint/results table wrapping from prior task. | Preserve existing source/request guards. Current numeric-input and live geometry coverage must come from the existing optimizer journey in this candidate's CI. |
| t / ANOVA / Kruskal / Pearson / XY | Shared metadata grid; trusted system-label helpers separate from full group/variable labels. | Existing panel-boundary SSR regression rerun; complete chart/error/dialog states not newly visited. |
| Report Center | Semantic selected-report/status/capability boundaries plus saved-result display; list and selection ownership remain separate. | No global localization or state rewrite. All generic and dedicated report variants still require their own evidence. |

## Route and State Inventory

`analysisDomains.ts` and `analysisDomainMapping.ts` remain the menu inventory; API registry remains capability authority. A row naming a fixture is not a claim that fixture has run. Analysis rows refer to the existing method route `/analysis/<category>/<method_id>` (legacy category aliases are preserved); no routing behavior changed.

| Route / method | State / fixture | Display boundary reviewed | Current evidence and unverified reason |
| --- | --- | --- | --- |
| `/home`, `/datasets` | empty, loading, error, selected version; `refined_ui.py`, `dataset_context.py` | Existing catalog/JSX and user-owned data labels | Inventory only; no new whole-page English scan here. |
| `eda.descriptive`, `eda.graphical_summary` | success, empty, quick-chart; existing critical path | Common charts/catalog | Inventory only; all warning/tooltip variants unverified. |
| `eda.normality` | saved Q-Q / failed assumptions | Stored result + chart labels | Inventory only; no new built scan. |
| `eda.principal_components` | success, component switch, saved result | Existing PCA adapters and semantic keys | Inventory only; existing resize fixture is not counted until current CI runs. |
| `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.two_sample_t` | success, CI unavailable, group labels | Trusted system helper vs user label boundary | Existing panel-boundary tests rerun for covered helpers; full live methods unverified here. |
| `hypothesis.one_way_anova` | post-hoc run/skipped/unsupported | Explicit trusted post-hoc helper labels | Source and existing SSR helpers; no new browser error-state scan. |
| `hypothesis.equivalence_tost`, `hypothesis.two_sample_equivalence_tost`, `hypothesis.paired_equivalence_tost` | independent/paired/one-sample display | Equivalence result helper boundary | Existing SSR helper regression only; form/dialog states unverified. |
| `hypothesis.one_sample_wilcoxon`, `hypothesis.mann_whitney` | success/unavailable | Existing result tables | Menu inventory only; no new display-boundary execution. |
| `hypothesis.kruskal_wallis` | grouped result/Dunn | Full group identity separate from labels | Existing SSR result helper regression; full browser unverified here. |
| `categorical.one_proportion`, `categorical.two_proportion`, `categorical.chi_square_association` | counts, CI, expected counts, warnings | Existing categorical result tables | Inventory only; warning/dialog/tooltip permutations unverified. |
| `regression.pearson`, `regression.xy_correlation` | saved result and unavailable CI | Trusted system helper + original variable names | Source and existing SSR regression; full chart browser unverified here. |
| `regression.linear_model` | OLS/regularized/saved prediction | `reg.*`, coefficient/user-label boundary | Source and existing SSR predictor labels; full workflow not newly executed. |
| `regression.partial_least_squares` | result/loading pages/prediction | `pls.*`, stored values | Source only; all restored component/prediction states unverified here. |
| `regression.gaussian_process` | numeric/mixed/group/time result, surface and prediction | `gp.*`, source-locked model/view | Source only; extension fixture exists but not a new English scan of every combination. |
| `regression.predict`, contextual regression optimizer | model-required/valid/invalid rows | Existing model-source UI | Inventory only; not hidden or marked available without prerequisite. |
| `doe.factorial_design`, `doe.general_factorial_design` | none/backward/alias/LoF | Existing semantic selection keys and scoped description layout | Source only; prior browser success is not reused as current evidence. |
| `doe.response_surface` | CCC/CCI/CCF, stationary unavailable, residuals | Existing saved view/residual labels and scoped coordinate layout | Source only; current RSM journey/zoom receipts required. |
| `doe.response_optimizer` | draft errors, saved objectives, constraints | Existing semantic/JSX display, immutable numeric strings | Source only; existing optimizer journey is reusable, not claimed executed here. |
| `doe.latin_hypercube`, `doe.bayesian_optimization` | design/study/pending/batch/replicate | Existing dedicated workflow | Inventory only; do not present generic analysis coverage as dedicated workflow coverage. |
| `quality.individuals_chart` | result/signals | Existing translated signal summary + metadata grid | Source and existing SSR signal interpretation; no new browser complete-state scan. |
| `quality.subgroup_chart` | Xbar-R / Xbar-S | Existing metadata grid and shared charts | Source only; all group/count/error variants unverified. |
| `quality.attribute_control_chart` | p/np/c/u, Phase I/II | Existing explicit purpose/denominator display helpers | Source and SSR helpers; frozen-limit/current-result states not newly exercised. |
| `quality.run_chart` | success, unavailable legacy tests, all four randomness cards | New semantic `runChart.randomness.*` and metric card | Red/green unit evidence; focused English/geometry source-browser suites passed41668513163. Final archive pending; not all legacy/error variants exercised. |
| `quality.capability` | invalid numeric, reversed limits, target below/above, one-sided/empty | New semantic validation DTO + render `t` | Red/green unit evidence; actual four invalid-input cases and KO/EN/KO passed41668513163. Full result/report states not newly exercised. |
| `eda.equal_variances`, `quality.two_variances` | full group names / BF/F | Existing saved-group identity / interval labels | Equal-variance SSR helper regression; full browser/report scan unverified here. |
| `quality.gage_rr` | retain/pooled, v1/v2 legacy, v3 six-panel | Semantic stored-policy/source/component labels; persisted chart bundle | New display unit evidence plus separate A/B numeric/report tests. Gage browser/archive evidence belongs to the orchestrator's exact-candidate receipts. |
| `quality.gage_run_chart` | grouped saved runs | Existing group/title display helpers | Existing SSR helper regression; no new live full-route scan. |
| `/reports` | filters, selection, full/summary, download/delete | Existing semantic capability/managed-source labels | Source only; all owner/schema/renderer states require existing report suites. |
| `/help`, management / settings | empty/error/confirmation | Existing static/semantic catalog | Inventory only; no new global dialog audit. |
| Comparability / multivariate monitoring | roadmap-only | Capability/menu notices | Intentional limitation, not a localization failure or implemented analysis. |
| GP surrogate / model-dependent prediction/optimizer | contextual | Existing prerequisites | Intentional contextual entry, not removed or promoted to unconditional availability. |

## Regression Gates and Boundaries

- Initial red: 2 Run Chart SSR cases (`1e-10` incorrectly shown as zero), 4 Capability error cases (English displayed Korean). These are display reproductions, not statistical failures.
- Current focused green: 6 files / 30 tests: `RunChartMetricDisplay`, `CapabilitySpecValidation`, `panelDisplayBoundaries`, `semanticValidationBoundary`, `GageRrPreflightPanel`, `gageRrMessages`. TypeScript typecheck passed after replacing a test-only unsupported `String.replaceAll` with the repository-target-compatible split/join.
- The localization checker now checks the Capability semantic error contract in addition to the existing string inventory. A registered Korean string returned by a validator is deliberately a failing negative case. JSX/compiler transformation scope and API transport remain unchanged.
- English browser scanning visits visible text plus `aria-label`, `aria-description`, title and placeholder in the active panel/SVG/tooltip. The only user-owned exception is an exact, named synthetic column label, not an entire subtree or an arbitrary Hangul whitelist.
- `english_system_text.py` performs real Run Chart execution, actual Capability input errors and KO/EN/KO changes; it asserts draft/selection/source-byte hash preservation and no locale-triggered analysis POST.
- `result_metric_layout.py` uses actual `chrome.tabs.setZoom/getZoom`, not CSS scaling or `deviceScaleFactor`. It records content width, columns, label/value and dt/dd rectangles, overflow and unchanged inputs/source hash at 1024/1280/1440 with 100/125/150% zoom. 390px is a separate 100% breakage guard, not a mobile redesign.
- Focused source-browser evidence is recorded above and in `gage_charts_layout_i18n_audit.md`. Exact release-archive assertions remain unverified until the final archive journey passes; unvisited methods/states remain unverified even when focused gates pass.

Unknown backend warning codes retain escaped original meaning through the established notice boundary. User column/group names and numeric/state/request values are never sent through generic translation. No source/result checksum or statistical method version is changed by stages C/D.

## Native Browser Follow-up

The Linux context suite in [run 41660887417, job 126003486081](https://github.com/kiwoju-git/Data-analysis-platform/actions/runs/41660887417/job/126003486081) failed the unchanged `english_system_text.py` active-panel scan. Seven Run Chart messages remained Korean: no-control-limits, canonical order, trend/oscillation rule definitions, exact-run definition, and detected trend/clustering warnings. This is actual browser evidence through the Vite localization plugin, not inferred from source or a screenshot. These source E2E jobs run Vite's development server, not the completed release bundle. The separate archive journey must run the same checks against the packaged built UI before claiming archive verification.

The fix stays at the explicit warning-code display boundary; no warning text, result payload, method version or request is rewritten. It also covers the current order/exclusion/tie/truncation and other detected-signal codes so known Run Chart notices follow the same policy. Trend/oscillation translations refer to the stored specified minimum length rather than hardcoding 6/14 for nondefault saved options. The original backend message remains untouched. Unknown codes retain their escaped original message and code.

`RunChartMetricDisplay.test.tsx` reproduces the seven actual messages; `runChartMessages.test.tsx` checks KO/EN/KO, all 20 known codes, scope isolation, exact-versus-approximate semantics, unknown/prototype-like code safety and unchanged source JSON. Passing these unit tests does not by itself prove that the next built-browser candidate passes. The original English scan is not weakened or whitelisted; the next exact-source CI result remains the browser completion gate.

Visual inspection of the same failure screenshot also confirmed inline label/value collisions in the four Run Chart setting notes (center line, trend, oscillation and exact runs). A Run-only `.run-chart-panel .option-note` grid now separates label/value rows with a 7px gap and wrapping. `result_metric_layout.py` additionally checks all four setting-note rectangles and overflow at every tested width/zoom; the surrounding global option grid is unchanged. The visible compact-history `확인 전` badge is a separate dynamic helper defect tracked by the orchestrator, not a Run warning exception.

Native Linux context job126030253156 in run41668513163 passed after these fixes.
Its receipt records914 Run Chart and104 Capability checks, exact Korean user-label
preservation, no locale-triggered analysis POST and unchanged source hash. The51
geometry steps covered real100/125/150% tab zoom,1024/1280/1440px, plus390px at100%,
with1/2/4-column states and zero overflow. Nonblank150% viewport PNGs were inspected.
The source-browser fixture uses the localization plugin but is not the packaged
application; archive verification and all unvisited menu states remain separate.
