# Mixed BO Frontend Checkpoint

## Acceptance Boundary

The schema-7 mixed study is a separate typed path. Legacy numeric studies,
recommendation routes, numeric ARD labels, saved model bytes and scalar goals
are not converted to mixed studies. The mixed interface supports:

- Explicit numeric, nominal and ordered categorical definitions; complete
  string labels, declared level order and named correlation assumptions.
- The existing complete-response-vector lifecycle, with actual observations,
  explicit repeat creation, abandon/close and owner-scoped deletion.
- Saved mixed model fitting with numeric kernel and measurement-noise choices,
  repeat compression, bounded typed starts and explicit resource settings.
- Immutable schema-3 candidate tables, complete CSV/TSV import, 50-row pages,
  explicit page evaluation, append/remove revisions and stored row identities.
- Manual ordered selection (up to eight rows, undo/redo) and separate automatic
  mixed maximin / Refine / Confirm augmentation records.
- Fixed-model complete-point prediction, numeric conditional curves and
  category-level discrete profiles; means, latent SD and predictive SD remain
  separate. A category profile is never a continuous integer-distance curve.
- Exact schema-10 batch reopening via `mixed_planning_batch_id`, current trial
  states and managed reports using a server-issued source descriptor.

No automatic POST retry is added. An explicit retry retains the request ID and
payload. Confirmation locks sensitive edits and uses a same-study commit fence
separate from computation freshness; a saved server outcome is not discarded
merely because the observation history refreshed. Source A/B/A transitions
invalidate old computation results. Resize, locale and profile display changes
do not fit a model or create experiments.

## Statistical and Privacy Constraints

- Category text is not parsed as numbers; `"001"` and `"1"` are different.
- Encoded category indices are equality/lookup keys, not default distances.
- Ordinal rank distance is an explicit equal-gap assumption for candidate
  distance. Kernel policy and distance policy are distinct choices.
- MaxPro is not offered for a study containing categorical factors. Mixed
  maximin is explicitly named as a different criterion.
- Model-free augmentation has no invented predictions. Model-based modes use
  the opened model and current eligibility source, not unsaved fit controls.
- The UI displays typed fitted-parameter roles, category coverage, convergence
  receipts and measurement-noise SD without calling category parameters ARD.
- Numeric discrete profiles use every executable level up to 100. Larger
  discrete profiles are unavailable instead of silently skipping levels.
- Full user factor/level/response names render as text. No new external
  endpoint, telemetry, raw diagnostic logging or browser artifact upload.
- These product covariance and acquisition policies are not claimed to be
  numerical reproductions of proprietary JMP Equal/Unequal/Latent or BO.

## Implementation

New typed boundaries: `api/types/boMixed.ts`, `api/boMixed.ts`,
`boMixedDraft.ts`, `boMixedPlanningDraft.ts`, `useMixedStudyActions.ts`,
`useMixedPlanning.ts`, `BayesianMixedStudyBuilder.tsx`,
`BayesianMixedStudyWorkspace.tsx`, `BayesianMixedPlanningPanel.tsx`,
`BayesianMixedSavedBatch.tsx`, and `i18n/boMixed.ts`.

The study lifecycle explicitly opts into the mixed GET union before dispatch.
Numeric consumers still reject schema 7 without that opt-in. The root workspace
keeps mutually exclusive exact batch query keys. The shared augmentation trace
and managed-report components accept typed mixed data without manufacturing a
numeric study or a file hash. API compatibility is 39; required metadata is 32,
with `bayesian_augmentation` and `bayesian_mixed_factor_planning` capabilities.

## Verification on This Checkout

Synthetic frontend fixtures are ownership/presentation tests, not independent
GP numerical reference calculations. Backend numeric evidence is maintained by
the integration owner separately.

| Stage | Actual outcome |
| --- | --- |
| Initial TypeScript static check | Four nullable callback expressions failed; corrected, next typecheck passed |
| Initial targeted ESLint | One test-expression error and two dependency/export warnings; corrected |
| Targeted ESLint rerun | Passed, no output, exit 0 |
| Narrow mixed/numeric transport, guards, presentation, runtime | 10 files / 88 tests passed, first run, 12.21 seconds |
| Entire frontend, one worker | 151 files / 1,346 tests passed, first run, 152.85 seconds; before the discrete-input follow-up below |
| Production build | Passed, exit 0; final rebuild after the follow-ups below transformed 2,261 modules, Vite 5.07 seconds; existing large-chunk and plugin-timing warnings remain |
| Built-app browser / API / report journey | Integration owner has authored the fixture; not yet executed at this checkpoint |
| Windows/Linux archive / final CI | Not executed by this frontend agent |

Commands (PowerShell, from `frontend`):

```powershell
npm run typecheck
npx eslint <changed frontend files>
npm run test -- --run <10 targeted test files> --maxWorkers=1
npm run test -- --run --maxWorkers=1
npm run build
```

Execution logs are outside Git under `$env:TEMP`:
`bo-mixed-frontend-targeted-first.log`, `bo-mixed-frontend-full-first.log`,
`bo-mixed-frontend-lint.log`, and `bo-mixed-frontend-build.log`.
The old numeric-planning checkpoint's earlier failures remain recorded; they
are not substituted for this execution's evidence.

### Discrete Input / Canonical Coordinate Follow-up

Source inspection found one display guard stricter than the server's existing
executable-grid contract. Input `0.30000000000000004` at step `0.1` is accepted
by the existing decimal-lattice validation, and the server separately retains
the supplied input and canonical actual coordinate `0.3`. The UI incorrectly
required these two records to be JSON-equal.

The focused red test was actually run and failed (one failure, 13 skipped).
`sameMixedExecutableInput` now checks the same decimal lattice and canonical
level for discrete factors; continuous values and category strings still
require exact identity. Out-of-bounds inputs, different levels, off-grid
coordinates, extra factors and changed category labels remain errors. No
source value is rewritten and the tolerance is not widened. Prediction
responses bind to the original submitted `input_coordinates`, then validate
their canonical actual coordinate independently.

The green rerun passed four files / 32 tests in 6.45 seconds; changed-file
ESLint passed and TypeScript plus production rebuild passed (Vite 5.36 seconds).
The logs are `$env:TEMP/bo-mixed-discrete-{red,green,build}.log`. The initial
failure is retained rather than hidden by the later success.

### Localization Fixture Boundary

The integration owner's first localization check rejected the synthetic user
label `한글 A` in `boMixed.fixture.ts`. This was test data, not a missing system
translation. Both mixed fixtures were renamed to `*.test.fixture.ts`, imports
were updated, and the existing test-file exclusion was used without changing
the localization checker or adding user labels to a translation catalog.
The actual checker rerun passed: 3,005 frontend source strings and 4,685 keys.
After the rename, the four targeted files / 32 tests passed again (6.47 seconds)
and the final TypeScript plus Vite build passed. Those final logs are
`$env:TEMP/bo-mixed-final-targeted.log` and `$env:TEMP/bo-mixed-final-build.log`.

Remaining browser evidence must distinguish API-seeded study creation from
the actual UI actions for observation entry, fit, candidate paging, ordering,
category profile, confirmation, exact reload and report download. The new
mixed builder's visual and keyboard validation is a separate browser case.
