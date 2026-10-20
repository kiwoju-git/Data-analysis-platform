# DOE Fractional and RSM Expansion

## Baseline and Acceptance

BASE_SHA: `391539438c1b80e6c615dc99a0f56cd7fc45c7b6`.
Branch: `feat/doe-fractional-rsm-contours`.
`origin/main` and local HEAD matched after fetch. User-owned
`examples/image2.png` is untracked and excluded. `data_prd.md` is absent.

Implement A through L in the requested order. Acceptance includes actual
regular-fraction second-order matrices and disclosed alias representatives,
hierarchy-safe selection, explicit lack-of-fit inference availability, shared
CCC/CCI/CCF coding, final-model-only prediction/plots/optimizer, immutable legacy
readers, and exact-source Linux release validation. No existing workspace or
artifact is rewritten. API 25 is reserved for the completed integrated contract;
metadata advances from 22 to 23 for the actual additive plot-view asset migration.

Risks: response/source races; alias versus rank/saturation confusion; zero pure
error; post-selection inference; legacy CCI coding; optimizer/model divergence;
contour holes/axis orientation; dependency wheels on every supported platform.
No main push or prerelease publication until required checks succeed.

## Evidence Ledger

| Stage | Code inspection | Implementation | Verification |
| --- | --- | --- | --- |
| A response/context | Blank response uses `Number`; edits do not invalidate; history failure shares save catch | strict shared parser, source epochs/request lanes, independent history retry | 37 focused frontend tests, typecheck, targeted lint; browser pending |
| B alias | Existing labels depend on display names | structured catalogue view, compact/full UI and HTML | focused tests passed; browser pending |
| C fractional estimability | Historical main-only restriction confirmed | actual-matrix representative preflight, second order, backward, result4/config5 | 42 focused tests; API restore/report; browser pending |
| D selection summary | numeric-card nowrap cause confirmed | scoped explanatory rows and clipboard fallback | unit/SSR passed; browser pending |
| E lack of fit | zero-pure-error availability reproduced | shared decomposition and explicit reasons | unit/API/report passed |
| F compact plots | existing interaction/frame preserved | compact shared-scale/status/pagination | unit/SSR passed; browser pending |
| G CCC/coding | current CCI-only transform contract reviewed | shared explicit transform and optimizer | native unit/API and legacy literal hash passed |
| H center recommendation | conditional product default specified | recommended/manual UI and metadata | unit/API passed |
| I RSM terms/selection | full-quadratic-only contract reviewed | four exponent presets/dependencies/final basis | unit/API/reference passed |
| J contour | official ContourPy API checked | serial geometry, source-locked views, static report | geometry/API/storage/SSR passed; browser pending |
| K integration/legacy/report | current ownership contracts reviewed | migration23/owned views/legacy dispatch | full checks in progress |
| L CI/main/release | no publication yet | pending | not run |

## Baseline Checks (Windows, 2026-10-20)

Use current locked Python environment with `PYTHONPATH=<repo>/backend` and
OMP/OpenBLAS/MKL threads set to 1.

- `pytest backend/tests/unit/test_response_surface.py
  backend/tests/unit/test_factorial_analysis.py
  backend/tests/unit/test_factorial_model_workflow.py
  backend/tests/unit/test_term_block_model_selection.py -q`: **41 passed**.
- `npm --prefix frontend test -- --run src/doe/doeResponsePaste.test.ts
  src/FactorialModelWorkflow.test.tsx src/GeneralFactorialDesignPanel.test.tsx`:
  **30 passed**, 3 files.

These are narrow baseline tests, not whole-product or archive verification.

## A Implementation and Checks

`parseDoeResponseNumber` reuses the paste parser's decimal/scientific syntax;
`parseRsmResponseDraft` requires the exact complete run identity set. It rejects
empty/whitespace/nonfinite/partial numeric text while preserving genuine zero.
`createRsmRequestContext` composes existing source and latest-request guards.
Design/response edit handlers invalidate synchronously; create/save/analyze
snapshot their payload/source identities. Stale success/error/finally handlers
cannot apply. History has a separate lane, loading/error state and retry action.
Saved revision identities survive history failures. No API or calculation changes.

- New test file initially failed to import its not-yet-implemented helper. This
  is test-first evidence, not an actual browser reproduction of the old defect.
- Focused response parser/context/paste tests: **37 passed**, 3 files.
- `npm --prefix frontend run typecheck`: passed.
- Targeted ESLint for the six changed/new TS/TSX files: passed. An earlier
  invocation used an incorrect relative Node path and did not run ESLint.
- `node scripts/check_frontend_localization.mjs`: passed, 2875 source strings
  and 4151 translation keys at this stage.
- `ruff check tests/e2e/rsm_context.py`: passed. The formatting check initially
  required formatting; `ruff format` applied it.
- `tests/e2e/rsm_context.py` is connected to the context/full suites. It uses
  actual synthetic design/save/analysis API responses with delayed delivery,
  verifies blank rejection/zero/save-plus-history-failure/stale completion, and
  checks the committed obsolete analysis remains readable.
- Browser test **not executed yet**: a hidden Vite startup command on isolated
  port 5271 was denied by tool execution policy. No test success inferred from
  source inspection. Separate test backend/workspace is outside the repository.

## UI Guidance

Installed `ui-ux-pro-max/SKILL.md` consulted. Targeted UX search
`long summary text wrapping` selected Long Token Wrapping: shrinkable grid/flex
children and `overflow-wrap:anywhere`, not global `nowrap` or truncation of
stop reasons. Keep existing statistical workbench tokens and density.
React search returned effect cleanup/dependency guidance; React 19-only Actions
and Effect Events are not applicable to this repository's React 18.3.1.

## External References

- [Minitab factorial stepwise](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/analyze-factorial-design/methods-and-formulas/stepwise/):
  saturated initial pooling is separate from p-value elimination.
- [NIST CCD definitions](https://www.itl.nist.gov/div898/handbook/pri/section3/pri3361.htm):
  CCC cube bounds and CCI axial bounds have different coding.
- [ContourPy 1.3.2 metadata](https://pypi.org/project/contourpy/1.3.2/):
  Python >=3.10, BSD-3-Clause, native wheels; not claimed to be latest.
- [ContourPy line types](https://contourpy.readthedocs.io/en/v1.3.2/user_guide/calculate/line_type.html):
  server geometry must use an explicit serial output format.

No identical-data Minitab output has been provided; independent numerical
fixtures will not be described as a Minitab binary-output comparison.

## B Implementation and Checks

`_fractional_metadata` derives a complete effect partition by symmetric
difference using factor indices. New optional alias-view metadata is produced
from the verified catalogue on read; design hash input and legacy label fields
stay unchanged. Pydantic validates canonical term identity and bounded partition.
`FractionalAliasSummary` provides symbol/name/unit mapping, lower-order/all-class
selection and full-name disclosures. Both DOE HTML paths render these mappings
with escaping, not screenshots or a model refit.

- Alias/domain/design API tests: **25 passed** before the additional report
  assertion was added.
- Alias structure/API/report and existing factorial export tests: **10 passed**.
- Alias SSR/adapter and existing factorial UI tests: **10 passed**.
- Existing Starlette deprecation warnings remain; no dependency changed here.
- Browser/layout/legacy archive checks remain unexecuted.

## C Implementation and Checks

`factorial_estimability` chooses a response-independent basis with a fixed,
unit-column-scaled rank tolerance. `doe_matrix_rank` applies the same policy in
selection, final fitting and drop-term ANOVA for new fractions only; legacy/full
paths retain their original least-squares calls. Intercept/block, forced parents,
main terms and canonical interactions have deterministic priority. Exact signed
alias, structural-span confounding, other dependency and unavailable hierarchy
are recorded separately. Forced conflicts name controlled term IDs.

The design-owned POST preflight uses actual options and runs. The UI immediately
invalidates preflight on option changes, retains an editable term catalog after
errors, and sends the same normalized policy list to execution. PB remains
restricted. New fraction results are method 0.10.0/result4/config5; API25 and
metadata22. Stored results expose their committed plan, not the current draft.
Both dedicated HTML paths include alias/representative information.

- First related regression batch: **75 passed, 1 failed**. The failure asserted
  the obsolete blanket fraction prohibition; it now distinguishes PB rejection
  from the regular fraction's missing-response guard.
- New rank/selection/API/report and unchanged selection-reference/engine tests:
  **42 passed** after structural-span and shared-tolerance corrections.
- Hand-checkable ranks: 5-factor half fraction, 16 requested/independent columns,
  10 genuine two-way terms, zero initial residual DF; 4-factor half fraction,
  11 requested / 8 independent; 3-factor fraction records main/two-way confounding.
- API test creates/saves/analyzes/reopens/exports without changing design hash or
  stored result values. HTML visibly includes `I = ABCDE` and pooling.
- Alias/UI/term/runtime frontend batch: **17 passed**, 4 files.
- Frontend typecheck passed before the later summary-layout changes.
- Independent read-only agent found structural-span misclassification, missing
  forced-term identifiers, and inconsistent rank policies. All three were
  addressed; no bad numeric rank had been reproduced for the original bounded
  catalogue fixture.
- Runtime/API/startup/release-identity/web checks: **296 passed, 2 skipped**
  (POSIX-only lock test and Windows account unable to create a symlink).
  These run against the source checkout, not a Linux archive.
- Final targeted mypy: **8 files passed**; staged Python Ruff and diff whitespace
  checks passed. Existing Starlette deprecation warnings remain.
- Browser and exact archive are not verified; no main push/release.

## D/E/F Source Implementation and Verification

Explanatory summary wrapping and clipboard fallback were implemented
without changing global numeric cards. Actual browser bounds/zoom checks remain
unexecuted.

The new lack-of-fit regression test was run against the previous calculation:
**4 failed, 3 passed**. One failure directly reproduces `available=True` with
zero pure-error variance; the other three require the new explicit reason
metadata. This is calculation-path evidence, not a browser reproduction.

`doe_lack_of_fit` now separates decomposition from F/p availability, records
physical-settings/block grouping, and rejects material negative decomposition.
Full/general factorial and RSM share this small calculation boundary. Only
roundoff-scale negative SS is clamped. A first green attempt still failed four
identity checks because a NumPy bool escaped; that was converted to Python bool.

- LoF, center/reference, RSM/general/fraction API batch: **40 passed**.
- LoF API, factorial selection API, managed report API: **22 passed**.
- API contract general/RSM subset: **5 passed, 229 deselected**.
- Frontend full suite after D/F, before G/H/I: **103 files / 880 tests passed**.
- Focused typecheck/mypy passed at that stage, not a final full-project check.

The literal no-center fixture has N16/g8/p4, residual DF12, pure-error DF8,
LoF DF4, SSPE0.16, SSLoF64 and F800. Zero PE variance produces no F/p. The
API test exports visible reason text and reopens stored results.

DOE-only compact layouts use 280x210 units, 1040/780/520 container breakpoints,
shared scales by default and explicit 12-pair pagination. Status comes from
committed selection/estimability, not a p-value or draft. All pairs remain
reachable; missing observed cells are not filled. Expansion uses the same data.
Independent source review found two real factor-ID/name mapping problems in
compact labels/general HTML; both were corrected. Actual browser overlap,
zoom, focus and pagination remain unverified.

## G/H Coding and Center Recommendations

`rsm_coding` is shared by new design generation, result coding, stationary/grid
actual conversion and optimizer actual-to-coded evaluation. CCC input bounds
are cube levels; CCI bounds are axial; CCF uses alpha1. k4 low10/high20 gives
CCC cube10/20/axial5/25; CCI cube12.5/17.5/axial10/20; CCF10/20. Explicit
unequal-repeat rotatable alpha uses the factorial/axial repeat ratio. Old
schema1/2 canonical payloads do not acquire new fields.

Recommended centers apply only to full cube, one block, equal single repeats.
Manual counts are not overwritten on factor edits. CCC requires acknowledgment
of its previewed axial range. An independent review caught collapsed narrow
range labels in the preview. It now uses interval formatting plus full-precision
endpoint disclosures.

- Coding/optimizer unit batch: **19 passed**.
- First expanded CCD API batch: **30 passed, 3 failed** because the synthetic
  center-only-noise fixture correctly triggered an existing severe normality
  acknowledgment requirement. The fixture now explicitly acknowledges it.
- CCD create/save/analyze/restore/optimizer plus LoF API: **8 passed**.
- Independent read-only probe compared pre-expansion `fecaa16` generation with
  current code: five legacy CCI/CCF configurations had identical hashes and
  actual run levels. Three literal baseline hashes are now regression fixtures.
- Narrow-range SSR first run: **2 failed, 7 passed**. The test expected more
  displayed digits than the interval formatter promises; exact endpoint
  disclosure and numeric checks were added. This is not a browser result.

## I Final-Model Implementation (Checks in Progress)

`rsm_model_basis` defines exponent vectors in canonical factor order.
`rsm_model_workflow` connects them to the existing selection engine with explicit
square/main and interaction/main dependencies. Factorial fallback rules are
preserved. RSM saturated backward is rejected, never pooled. Final terms drive
fit, diagnostics, LoF, PRESS, stationary point, grid and optimizer. Singular
Hessians have no invented optimum. Exploratory-inference warnings persist
through downstream optimization and HTML.

Service reads dispatch supported method/envelope/result/config versions and
verify final basis/terms/coefficients/coding/config. UI options invalidate pending
analysis completions; historical response revision switching is guarded.
The same completed revision may be analyzed with different presets. No old
result/model is rewritten. Reports render saved selection and basis.

- Workflow/CCD/legacy engine/RSM initial batch: **42 passed**.
- Expanded coding/LoF/workflow/legacy engine batch: **55 passed**.
- Later API/report batch: **24 passed, 1 failed** due to a new test omitting the
  required randomization seed. Test input corrected; rerun pending.
- Independent agent compared old/new selection engines on a full-factorial
  fixture: entire none/backward selection payloads matched. No broader numeric
  equivalence is inferred from that probe.
- Latest frontend typecheck passed; targeted mypy found one ndarray/Sequence
  annotation mismatch, corrected, rerun pending.

## J Stored Contour Views and Integration

ContourPy1.3.2 uses serial Separate lines and OuterOffset filled polygons.
The server stores numeric paths/rings with holes, levels and `z[y][x]` orientation;
React and inline SVG reports render that same geometry. Constant surfaces have
one band, not invented contours. Actual/coded axes use stored factor transforms.
Convex-hull membership uses the full coded design, including the held dimensions;
slice clipping and projected-vs-on-slice points disclose extrapolation.

`plot-view` evaluates only the verified final exponent basis. It never fits,
selects terms, reads a raw dataset or runs CV. Explicit save validates the viewed
hash and records an immutable owner/source-locked asset. The listing returns
small descriptors; selected geometry is fetched separately rather than loading
every stored grid into browser state. New results retain a default contour and
all conditional main/interaction bundles. Reports use stored bundles, not live
UI pagination or new calculations.

Migration23 expands the existing DOE asset kind constraint to `plot_view`.
Existing BLOB bytes and hashes are preserved. It adds no new general report
table. View/report dependencies participate in atomic insert, delete preflight,
owner cascade, asset catalog and offline backup. Code rollback to metadata22
cannot simply open a migrated23 workspace; use a verified pre-migration backup
at a new path, never delete or overwrite the current workspace.

- Geometry: **5 passed** (plane, saddle, annular holes, constant, axis swap,
  full-dimensional hull slice, invalid levels).
- Plot view/model/storage API batch: **23 passed**; verifies saved custom view,
  checksum preservation and export with fit/basis-evaluation/geometry disabled.
- Migration/storage independent suite: **19 passed** before the subsequent
  descriptor-list refinement; rerun tracked separately.
- New frontend snapshot/contour SSR: **48 passed**, typecheck and file lint passed.
- Whole frontend at that point: **925 passed / 7 failed**. Five failures were
  obsolete guidance/label/runtime fixtures; two were lazy-import timeouts during
  concurrent backend verification. Changes and reruns are recorded separately,
  not treated as an initial clean pass.
- Full backend mypy: **216 source files passed**; Ruff backend passed.
- Windows reference suite: **12 passed** with NumPy2.2.6/SciPy1.15.3/sklearn1.7.2.
- Native Linux dependency run39443793234 failed the input-declaration guard.
  Only the four missing `.in` declarations were committed, without bypassing it.
  Run39445525189 then passed all four Ubuntu24.04 Python3.11/3.12 runtime/dev
  lock generation, exact wheel installation, `pip check` and contour smoke jobs.
  Product jobs and release-ready were skipped in this tooling-only run.

`rsm_context`, `doe_rsm_completion` and the existing factorial journey are wired
to actual UI suites. Local browser execution was not completed. Final native
product CI, exact archive verification, main and Release remain outstanding.

## Integration Checkpoint (2026-10-21, Windows)

These are source-checkout results, not a published archive receipt:

- Frontend full run with one Vitest worker: **107 files, 932 tests passed**.
  The earlier five obsolete fixtures were updated to the implemented contract;
  no lazy-import timeout was increased. The later restore tests are additional.
- Frontend typecheck, production build, localization coverage (2870 source
  strings / 4268 keys), capability generation check and backend Ruff passed.
  Build retains the existing large initial-chunk warning.
- Full mypy: **216 source files passed**.
- Whole Windows unit run: **2489 passed, 25 failed, 9 skipped** (3204.70s).
  This run overlapped implementation and collected older fixture expectations.
  Failures were traced to explicit method/schema expectations, incoherent
  synthetic optimizer DF, generated capability sync and newly connected E2E
  stage/document contracts. The 25 failed nodes' current equivalents plus three
  related protection cases subsequently passed (**28 passed**, 60.13s).
  This initial whole run is not recorded as a clean pass; frozen-source native
  CI is still required. Nine skips were six Windows symlink-privilege cases
  and three Linux/POSIX-only cases. Local Windows build was 19045, not a
  Windows 11 device verification.
- OpenAPI/frontend/document contract rerun: **233 passed**.
- Full frontend lint: **0 errors, 12 Fast Refresh export warnings**.
- Plot/source/migration/suite-partition batch: **116 passed**.
- Updated suite partition and runtime health: **76 passed**.
- Independent contour/asset/security/release-validator batch: **206 passed**.
  A red test first demonstrated that stored view design version/hash were not
  checked against the exact analysis. The reader now checks both. A deleted
  selected view returns a managed-source conflict, while historical HTML remains
  downloadable byte-for-byte. Direct missing-view lookup still returns 404.
- Curve reports now disclose stored hull flags in their full point table rather
  than promising hatching that exists only in the contour representation.
- Deferred restore tests first reproduced a stuck busy state after a pending
  restore was superseded by an empty/invalid route. Intent changes now clear
  owned busy state while invalidating late completions. Saved-view selection
  waits for verified source metadata, independently of the list response.
- An exploratory Ruff command over all `scripts/` also reported two pre-existing
  issues outside this task (`render_stat_dependency_record.py` unused import and
  `validate_normality_reference.py` import placement). The repository's required
  backend Ruff scope passes; these unrelated files were not rewritten.

New native browser stages use synthetic data only: regular-fraction KO/EN,
CCD/term presets/backward/saved custom views, and real Chromium tab zoom at
100/125/150 percent. Archive verification requires their structured successful
receipts, exact source IDs/hashes, source preservation and no analysis POST from
view/resize/zoom changes. Defining or unit-testing those receipts is not evidence
that the browser journey itself ran. Final native CI and exact-archive evidence
must accompany the release; a failed required gate prohibits publication.

## Tutorial Version Checkpoint (2026-10-21)

Native product run `39454810197`, source
`ca1162b371c9d5dc7a369edabd0dd9d05ddd6f00`, failed one tutorial metadata
assertion on both Ubuntu Python targets. Each reported **1 failed, 2648 passed,
13 skipped**: Python3.12 took 377.03s and Python3.11 took 382.94s. The skips
were the Windows-only PowerShell startup tests. The committed tutorial expected
`doe.factorial_design` v0.9.0 and `doe.response_surface` v0.3.0 rather than
the implemented v0.10.0/v0.4.0. Linux Ruff/format/mypy and the dependency-security
aggregate passed; frontend/browser stages did not run and Linux Release was
skipped. This run is not a successful product gate.

A new regression test reuses the existing real DOE API tutorial collector with
a fresh synthetic temporary workspace. Before changing fixture metadata, its
first two checks exposed additive RSM LoF metadata and stationary-point `reason`
keys in the normalized summary. The collector now explicitly selects the same
five LoF and eight stationary-point fields already documented by the tutorial.
The full application result and its new fields are unchanged and remain covered
by their separate API/domain tests.

The recorded factorial sample/DF/effects/residual ANOVA, RSM fit/stationary-point/
LoF values and both warning counts then matched the current APIs at the existing
absolute and relative tolerance of **1e-8**. No numeric fixture was regenerated
or edited, and no tolerance was widened. Only the two expected method-version
strings and their renderer-generated Markdown source lines changed.

Actual Windows/Python3.10 checks after this correction:

- `pytest backend/tests/tutorial/test_tutorial_data_pack.py -k doe_api -q`:
  **1 passed, 8 deselected, 3 deprecation warnings**, 12.50s.
- `pytest backend/tests/tutorial/test_tutorial_data_pack.py -q`:
  **9 passed, 3 deprecation warnings**, 18.28s, including the generated-document
  check and the new current-API numeric regression.
- `scripts/render_tutorial_results.py --write` synchronized 18 documentation
  blocks; the resulting document diff changes only the two version source lines.
- Ruff check for the changed Python files and format check for the backend test
  passed. No statistical implementation, user workspace or persisted result
  was modified.

These are focused source-checkout checks, not a rerun of all 18 API smoke
methods, native full CI, browser verification or an installed archive. Those
remaining gates require the next exact-source CI run.

The same follow-up also extends the DOE browser fixture to eight resize steps,
including 390px, and checks 4/3/2/1 chart columns against the actual
`.doe-compact-scope` content width. The archive validator requires that same
strict receipt. Its focused verifier tests passed **165 tests in 2.29s**, and
the three changed validation files passed targeted Ruff. The extended browser
journey has not yet run; these checks do not establish viewport behavior.

A subsequent source audit found the RSM browser fixture seeded Korean on every
navigation while expecting English after an in-app language change. Its seed
now applies only when locale storage is absent; the shared readiness/diagnostic
helper and English assertions remain unchanged. The four DOE browser files
passed Ruff, and suite-partition/archive-receipt tests passed **236 tests**.
This is a fixture correction verified by source inspection and contract tests,
not evidence that the actual native browser journey completed.

Run39457319672 (`468dad7`) passed Linux backend **2651 tests, 13 skipped**
and frontend **108 files, 936 tests**, then failed the new RSM context journey.
The child-page trace showed a successful initial response revision followed by
an identical second PUT 249ms later. The second request correctly returned
`409 doe_response_revision_conflict`; it was not a locale/chunk or analysis-lock
failure. The fixture now changes the first response to 0.25 before holding that
save, then edits it to 0.5 while the real completion is delayed. The product's
duplicate-revision rejection remains unchanged. Native browser rerun is required.

An opt-in `browser_diagnostics` workflow input runs the existing Linux context
and workflows browser suites without waiting for the full unit job. It does not
skip, replace or change any required Windows/Linux/security/archive/release-ready
gate. Its synthetic child-page artifacts remain separate from final native
archive evidence. This is early failure diagnosis, not a release shortcut.
The suite-partition and archive-validator regression batch passed **237 tests**
after that wiring change. The original ca1162b Windows job also finished with
the same tutorial-version failure: **2658 passed, 1 failed, 3 skipped**,
1828.00s on hosted Windows Server2025/Python3.10.11; its frontend did not run.

Run39460057458's early context suite passed after the revision-fixture correction.
Its workflows suite reached the five-factor analyses, HTML export and restore,
then the API-only setup for the four-factor fixture was correctly rejected by
the Vite Origin guard. The trace showed the real UI POST with Origin succeeded
and the helper POST without Origin returned `403 dev_origin_not_allowed`.
Only that synthetic helper now sends the exact local Origin; no Host/Origin/CORS
protection changed.

For iteration, `browser_diagnostics_only=true` can now explicitly run diagnostics
without product jobs. Such a run has no release-ready result or publishable
archive and is rejected by the release collector. Normal/full runs retain every
required gate and the four Windows suites. Earlier obsolete 468dad7/6400408 runs
were cancelled after collecting their Linux failures; their interrupted Windows
checks are not passes. Final source requires a fresh complete native run.

Diagnostic-only run39461010226 (`7678d1e`) passed the context suite. The workflows
suite completed the Korean fractional journey, then its English locator expected
`Maximum interaction order` while the captured DOM's existing accessible label
was `maximum interaction order`. English design/preflight/response requests were
successful; the child page had no page errors or failed assets. Only the fixture
label changed. The RSM browser fixture now also enters a synthetic long Korean/
English factor name and unit through the form before design generation, so the
same restored model exercises them during resize and real tab zoom checks.
This diagnostic run skipped product/release gates and produced no release.
