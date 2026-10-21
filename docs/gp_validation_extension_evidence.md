# GPR validation extension evidence

## Contract

This extends standalone GPR validation, not the BO surrogate policy. Existing
numeric K-fold, LOO, normalization, kernel optimization and fitted-model values
retain their existing calculation paths.

- `group_k_fold` requires `cv.group_column_id`, `shuffle=false`, 2-10 folds and
  at least as many distinct full group identities. An ID-role column is valid
  metadata and is not automatically a predictor. Missing group identity on an
  otherwise usable row is an error. This evaluates new-group generalization.
- `time_series_split` requires a time column, explicit numeric unit or timestamp
  format, and `shuffle=false`. Timestamps require an offset unless UTC is
  explicitly requested. Equal timestamps remain in one block. Expanding folds
  have strictly earlier training times. `gap_time_blocks` counts time blocks,
  not rows or elapsed time. Unequal elapsed time spans are retained in evidence.
- Optional `lag_features` has positive observation-order lags 1-100, a fixed
  one-step horizon, optional series ID, and time validation only. Lags never
  cross series, use current/future targets, or interpolate missing observations.
  Duplicate timestamps within a series are ambiguous and rejected. Irregular
  observation spacing is reported. This is rolling one-step evaluation after
  prior actual outcomes become known, not fixed-origin recursive forecasting.
- Lag sources in the fold's embargo interval are forbidden. Affected validation
  rows are excluded by the shared plan before fitting and recorded explicitly;
  an empty validation fold fails. No failed fitted fold is silently removed.
- Original and derived predictors together are limited to 12. Lag input sources
  must be numeric, non-nominal, non-ID columns. Response lag is permitted only
  with positive lag. Direct prediction requires explicit derived past-lag values;
  it does not read the unknown response of the prediction target.

The split plan is created once and shared by all compared kernels. Numeric
scaling, response normalization and kernel/noise fitting remain fold-local.
Initial training-only and embargo-excluded rows have null CV diagnostics. PRESS,
TSS, RMSE, MAE, NLPD and interval metrics use exactly the scored-row mask. Stored
metrics remain row weighted, not group macro metrics.

Result and manifest carry the plan, hash, fold row indices/group counts/time
ranges, scored coverage, and lag lineage. Row indices retain the established
filtered-snapshot, zero-based analysis-row meaning. They are not invented
canonical dataset row identifiers. Lag lineage records past source indices and
times, target time and explicit exclusion reasons.

## Implementation boundaries

Pure helpers: `gp_validation.py`, `gp_time_features.py`.
Integration: `gaussian_process_regression.py`,
`gaussian_process_kernel_selection.py`,
`analysis_runner_gaussian_process.py`, and typed options in `schemas/analyses.py`.
No SQL change or old artifact rewrite is required. The overall change owns the
new GPR result/manifest version and legacy 1/2/3 reader dispatch separately.

GPR method 0.4.0/result 4/manifest 4 use explicit readers alongside manifests
1/2/3. Numeric-only calculations keep the existing numerical path. Mixed
predictors use numeric-only scaling and full categorical identities; each fold
learns its own vocabulary. Unseen validation or prediction categories fail
explicitly. At most 4 nominal predictors with 32 levels each are permitted;
original plus derived predictors remain limited to 12. Nominal-only covariance
uses signal amplitude times the categorical mismatch kernel, not a numerical
distance between category codes. NPZ remains six bounded numeric arrays, with no
object array or pickle. Profiles use discrete categories, and surfaces only use
numeric axes with numeric median/categorical mode hold values.

`standard_exact` remains at 500 valid rows. `extended_exact` admits at most 2,000
only after the conservative 512 MiB working-memory estimate, fit budget and
option checks. Extended fitting runs in the owned spawn worker. Large query
prediction is chunked at 256 rows, without a query-by-query joint covariance.
Lag preparation has a separate conservative 32 MiB estimate for retained rows,
strings, observation sorting and lineage, within the general base reserve. This
is a preflight estimate, not an OS-enforced memory limit. It raises
`gp_parse_memory_budget_exceeded` rather than truncating rows. Streaming parsing
also stops with `gp_usable_rows_limit` immediately after the first excess valid
row. Existing source artifacts are not deleted on either failure.

Recorded fit timings are actual elapsed model construction/fit time, excluding
preprocessing and prediction. Final fit and per-fold values are separate; CV
fit time is their sum. Worker RSS evidence and full resource benchmarks are
recorded by the separate resource-verification harness.

## Executed evidence

Windows, CPython 3.10 virtual environment, single numerical-library threads,
synthetic fixtures and isolated temporary workspaces only.

- Initial new helper tests failed at import before implementation (red).
- First 12 pure/calculation tests passed in 8.45 seconds.
- First API/options integration: 20 tests passed in 31.33 seconds, including real
  CSV ingestion, ID-role group metadata, saved result/model restore, and explicit
  lag-value direct prediction matching the stored fitted value at 1e-9 tolerance.
- Existing seven GPR unit/reference/API/report suites plus those 20 tests:
  123 passed in 160.53 seconds. Five existing Starlette deprecation warnings.
- An added candidate-details parity test initially failed because optional
  retained candidate details omitted the common plan. That field was added;
  this failure did not indicate a different split or different fitted values.
- Mypy: six owned source files passed after an Optional metric type correction.
- Mixed integration first failed on the old numeric-only parser, then four
  tests passed, including category-label bijection, nominal-only fitting,
  unseen-fold rejection and safe state reconstruction.
- Manifest 4 initially encountered the generic OLS manifest-4 validator. The
  dispatch is now method-specific. Ten API extension tests then passed in
  38.78 seconds, including 501-row spawned fitting and 600 saved-model queries.
- Lag memory/early row-limit tests first failed twice, then passed twice after
  explicit bounded preparation and immediate valid-row limit checks.
- Independent review reproduced an overly strict GroupKFold boundary: five rows,
  five groups and five folds were rejected although every training fold has four
  rows. The group-only guard was corrected, preserving old row-KFold policy;
  independent sklearn and actual GP boundary tests plus validation tests passed
  (20 tests, 12.50 seconds).
- Nominal-only models now persist a warning that numeric kernel presets are
  inactive as distinct numeric families. KO/EN component rendering passed eight
  tests. Mixed and nominal-only real API fitting, safe model restore, saved
  prediction and unknown-category/type rejection passed two parameterized tests
  in 49.53 seconds. This warning does not change fitting or switch presets.
- The combined existing GPR and new validation/mixed/resource/API/reader suites,
  plus execution/catalog checks, produced 196 passed and one failure in
  327.71 seconds. The sole failure was the not-yet-regenerated capability matrix
  still containing API 25 while runtime had moved to 26, not a GP calculation
  failure. The complete product generator/full-check gate remains separate.
- After the group boundary and nominal-only warning corrections, the focused
  ten-suite GPR legacy/reference/API/report/context/extension matrix passed all
  123 tests in 348.59 seconds. It ran concurrently with other validation work;
  that duration is test evidence, not an isolated performance benchmark.
- E2E suite partition and exact-archive receipt verifier tests passed 255 tests
  in 9.96 seconds. These check harness wiring/required receipts, not execution
  of the browser forms themselves. Owned seven-file mypy, Ruff checks and
  Python compilation of the five changed browser/verifier modules passed.

`tests/e2e/gp_validation_extension.py` is connected to the `prediction` suite and
the exact-archive initial journey. It prepares only synthetic CSV through API,
then manipulates Group/Time/lag forms, mixed saved-model prediction, categorical
surface holds and explicit view saving. Managed report reopening/downloads and
KO/EN 1024/1440 resizing are asserted. Unknown-category rejection is explicitly
an API check, since the UI offers only trained categories. The archive verifier
requires the receipt, including zero locale/resize fit/prediction POSTs. These
new browser scenarios were written but not locally executed because server
launch was denied by the environment policy; native CI must provide execution
evidence before release.

Test files: `test_gp_validation_extension.py` and
`test_gp_validation_extension_api.py`. Assertions include full long group IDs,
disjoint groups, equal-time blocks, timestamp offsets, fold-local means, independent
scored PRESS/RMSE calculation, past-only/series-isolated lag lineage, embargo
exclusion, missing/ambiguous metadata, serialization without NaN, stored hashes,
and missing lag input rejection.

Browser forms, KO/EN labels, built Linux archive, native CI and resource-profile
benchmarks are separate integration gates; the above Python/API evidence does
not claim those gates passed. HTML export smoke uses stored result and checks
table/SVG presence and unchanged model bytes; it does not yet establish visible
parity for every new validation-plan field.

## First native CI corrections

Run `39613148814` at source `1c178d33444d185625418f5bb71270d39d1aa1df`
did not pass the product gates. Its Linux check stopped at Mypy because Linux
ctypes stubs do not expose `WinDLL`; the Windows-only peak-RSS branch now uses
an explicit typed platform boundary, matching the Linux-only resource branch.
The native Windows worker tests, including positive peak-RSS reporting, passed
8 tests in 19.93 seconds. CI-style Mypy with `--platform linux` and
`--platform win32` passed for the worker. An additional invocation explicitly using the backend strict config
(not the root CI invocation) found 13 existing/dependency strict issues; that
invocation is not counted as a pass.

The early workflows diagnostic run failed in the existing chart fixture
before reaching the new GP form journey: a broad child-button locator matched
both Generate Surface and the newly added Save Applied View action. It now
targets the explicit Generate Surface name. The chart fixture also uses the
common child-page diagnostic owner so its own URL, DOM, screenshot and trace
survive failure, rather than depending on an unrelated top-level page.
Diagnostic/partition unit checks passed 83 tests in 7.40 seconds; these mock
checks do not replace rerunning the actual native browser workflow.

Additional actual time/lag fits verified that saved HTML CV plots contain exactly
the scored observations, not fake zero-valued warm-up predictions, and that
KO/EN plan/lag tables preserve the saved identity. The two report checks passed
in 15.28 seconds while fit, saved-model prediction and raw-row readers were
forbidden during export; source payload bytes remained equivalent. This closes
that specific report coverage gap, not the pending native browser journey.

Python 3.11's first full calculation/API check reported 20 failures, 2,939
passes and 13 skips. Most were old schema/version/test expectations. The
sklearn import-boundary check also exposed a real startup regression after its
module allowlist was updated: the new mixed-kernel base class was imported by
the main GPR module at application startup. Mixed-kernel imports now happen
only at fit/state-load/payload/warning execution boundaries. Startup still must
not import sklearn. The import-boundary, stored-family report, mixed fitting,
time/lag report and E2E marker checks then passed 42 tests in 55.21 seconds.
The surface report test now checks all three stored quantities and confirms
that legacy results without latent SD report that section as unavailable.

## Second native browser diagnostic run

Run `39616780776` at source `20a5b1f973986cd17dc0dc1e71df7cdc7d72f4c3`
was a browser-only diagnostic, not a passing release-ready gate. The prediction
job `119279871802` reached the new GP extension form but stopped before its
first fit: the Response select's wrapping label included option text, so an
exact accessible-name query could not find it. The child page was mounted,
runtime-compatible and English, with no page errors or failed assets. Its
actual DOM, screenshot and Playwright trace were retained in artifact
`12353755995`; the screenshot confirms the synthetic dataset and visible form.

Response and extension metadata/axis/hold selects now have explicit localized
accessible names matching their visible labels. The workflows job
`119279871375` separately reached the existing GP fitted-result checks and
failed because its unscoped X-axis selector matched both initial draft axes
and applied result axes. That assertion now scopes the applied surface result.
These are accessibility and fixture-scoping corrections, not numerical-model
changes. The new form journey still requires a successful native rerun.

KO/EN component markup plus existing extension and chart adapter tests passed
17 tests in 5.16 seconds. Markup assertions do not prove browser interaction.
The synthetic receipt now retains the existing lag and surface request/response
snapshots, so archive restart/second-install verification can compare the same
stored model and applied view without fitting another model.

## Native GP browser journey passed

Run `39619608275`, source `6fe0b509a726a43be340450b4f0faf47a3ec5927`,
prediction job `119289234987` passed on Ubuntu/Python 3.12 at
`2026-10-21T14:47:55Z`. Artifact `12353084481` retains the actual synthetic
receipt, KO/EN screenshots, saved prediction reports and child trace.
This is native browser execution evidence, not a mock or API-only substitute.

- Group form: 36 used/scored rows, six full-identity groups, disjoint fold groups.
- Time form: 36 used rows, 27 scored rows and nine training-only warm-up rows.
- Positive lag form: 35 used rows, 24 scored rows and 11 training-only rows;
  persisted source times precede target times. Four predictors include the
  explicit past-response lag. Direct lag-value prediction completed.
- Mixed model: restored stored analysis, numeric/category input prediction,
  saved prediction and managed report reopen/download completed.
- Surface: category hold `level-B`, 10-by-10 grid, saved `latent_sd` view with
  100 prediction rows. The report uses that explicit applied view snapshot.
- KO/EN at 1024/1440 CSS-pixel viewports: ready prediction preserved, no page
  horizontal overflow, zero analysis/prediction POSTs on locale/resize changes.
  Screenshots were inspected; this does not substitute for browser-zoom tests.
- Source result checksums remained unchanged. Unknown-category rejection was
  tested through API; the UI deliberately offers only trained levels.

The failed preceding runs remain recorded above. Windows browser execution,
full product aggregate gates and exact-archive restart/second-install verification
are separate acceptance gates and are not implied by this successful job.

The same run's workflows job passed the existing GP fitting, uncertainty and
kernel-comparison stages, then failed later at the existing Bayesian mobile
overflow assertion. That later failure is not recorded as a GP pass for the
whole workflow. The current-code 501-row extended worker API regression was
rerun locally: one test passed in 27.88 seconds, with three dependency
deprecation warnings; the earlier long-running old-code process failure did
not reproduce.

Screenshot timing is now strengthened separately: both BO and GP fixtures use
`wait_for_layout_settled` to await actual drawer animations, then test content
bounds. GP records main/surface/sidebar geometry at each locale/viewport. The
helper and invalid-geometry regression checks passed as part of 83 unit tests
in 6.85 seconds. These new post-transition geometry assertions require another
native execution; the prior screenshots alone do not prove their result.

Python 3.11 native job `119289234826` passed 2,994 tests with 13 skips and
114 warnings in 449.75 seconds. Its numerical probe remains explicitly
diagnostic-only, including the BO 100-evaluation budget failure and subsequent
200-evaluation diagnostic result. Linux job `119289235264` later stopped at
the localization registry gate before its browser stage: 91 newly explicit
BO KO/EN display pairs had not been registered. Their existing translations
are now registered without changing request objects, enum values, user input,
the compiler scope or API transport. Two obsolete legacy source mappings were
removed, while their translation keys remain readable.

The localization check now passes 2,959 source strings and 4,404 keys. Local
i18n/BO/hook checks passed 234 tests; full frontend lint, typecheck and build
passed. Lint retained 12 fast-refresh warnings; build retained the chunk-size
and localization-plugin timing warnings. Compiler regression tests explicitly
confirm that registering these display pairs does not rewrite the `text(ko,en)`
helper arguments, request names or `noise_mode` enum values.
