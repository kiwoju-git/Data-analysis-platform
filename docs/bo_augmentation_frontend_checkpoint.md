# Automatic Augmentation Frontend Checkpoint

## Scope

This gate adds numeric-factor augmentation to the existing desirability-study
workspace. It does not change scalar studies, the numeric/manual Profiler, a GP
fit, or the observed experiment history. Nominal/ordinal UI integration is a
separate subsequent gate.

New candidate revisions use schema 2 with explicit study definition, observation
history, trial count, novelty tolerance and nullable model identity. Uniform or
complete CSV/TSV candidates can be saved without fitting a model. The server
returns only a bounded page. The older manual planning interface intentionally
lists schema 1 candidate revisions only until its reader supports schema 2.

## Selection Policies

- Continuous-factor MaxPro is a named incremental projection criterion.
- Numeric-discrete space filling uses an explicitly different mixed-maximin
  criterion. It is not labeled MaxPro.
- Refine v2 uses first-point Beta EI and an alternating desirability/normalized
  response latent-SD schedule.
- Confirm uses first-point expected desirability, then uncertainty inside the
  saved competitive set. It is not a guarantee of the optimum.

The automatic selection trace is read-only. Its precise row IDs, order, score
scale, candidate counts and competitive thresholds are displayed from the saved
payload. Model-free selections show unavailable predictions, never fabricated
response values. Model-based selections retain response names and units and
separate latent from new-observation predictive SD.

Starting a manual selection is an explicit action that creates a separate,
model-bound schema 1 candidate table from selected coordinates. It does not edit
the automatic trace, inherit its algorithm claim, or create pending trials.
This path requires a current saved model.

## Source and Commit Ownership

Draft, model, candidate and history changes invalidate computation responses,
errors and finalizers. Confirmation locks sensitive controls. Its committed
outcome is fenced by study identity rather than by mutable presentation drafts.
An old study A request cannot apply after A-to-B-to-A navigation.

POSTs are never retried automatically. An explicit retry reuses the saved request
ID and exact payload or the exact selection ID plus configuration/result hashes.
Already committed artifacts are not deleted when a screen request is obsolete.

Saved schema 9 batches use the dedicated `augmentation_batch_id` query parameter.
Exact reload calls `augmentation-batches/{id}` and validates study, definition,
selection, candidate and item relationships. It never substitutes the newest
batch. Managed-report creation obtains the server's exact report descriptor and
verifies returned source-reference hashes; it does not invent file hashes.

Saved automatic reviews can be reopened by their exact selection ID. A separate
bounded automatic-review catalog endpoint is not implemented in this checkpoint.
Deletion impact uses the existing shared planning-record counts, now explicitly
labeled as covering both manual and automatic selections.

## Evidence

- Source-confirmed: new numeric schema 2/9 API contracts and existing manual
  schema 1/8 contracts were inspected.
- Implemented: transport, strict drafts, source guards, policy/trace display
  boundaries, exact batch/report source, and scoped KO/EN labels.
- Static check: `npm run typecheck` passed after the final fixture additions
  (session 13748). An earlier run caught one incomplete test history DTO; the
  fixture was corrected to retain the required history fields, not the contract.
- Static check: targeted ESLint passed for the new augmentation files and touched
  planning/workspace files (session 25903).
- Unit/presentation/transport: eight frontend test files, 66 tests passed in
  11.19 seconds, single worker, session 8592. This was the first augmentation
  test run; it had no failures. The group includes the existing manual planning
  draft, API, panel, saved-batch and deletion regressions.
- Unverified: built-app browser, full frontend suite, native Windows/Linux
  suites and exact archive. The parent owns the compute slot and integration.

The fixtures are synthetic ownership/presentation data. They are not independent
GP/acquisition numeric references or JMP-output parity evidence. Pure acquisition
and service numerical verification are recorded separately by the parent.

The focused command was:

```powershell
npm --prefix .\frontend test -- --run src/features/bayesian/boAugmentationDraft.test.ts src/features/bayesian/BayesianAugmentationPanel.test.tsx src/api/boAugmentation.test.ts src/features/bayesian/boPlanningDraft.test.ts src/features/bayesian/BayesianPlanningSavedBatch.test.tsx src/features/bayesian/BayesianPlanningPanel.test.tsx src/features/bayesian/BayesianPlanningDeletion.test.tsx src/api/boPlanning.test.ts --maxWorkers=1
```

The complete command output is in the tool-session transcript; no separate full
log file is claimed by this checkpoint.
