# Existing X/Y BO Start And Recommendation Reliability

## Intent And Decisions

The user approved reuse of the dataset already selected in the application
header. Do not add another upload or dataset picker inside BO. BO consumes
completed historical X/Y observations; GPR remains a separate supervised
analysis of that same selected dataset. Preserve current UI density, source
guards, numeric formatters, saved artifacts, and the recent DOE/GPR work.

Approaches considered: reuse the common dataset ingestion and map columns
(selected by the user); duplicate upload/paste inside BO and GPR (rejected:
duplicate parsing, state, and storage responsibilities). Never attach old Y
values to newly generated LHS X coordinates.

## Acceptance Criteria

1. Reproduce the multiresponse default-Matern q2 precision failure with
   synthetic observations. Evaluate the same moment-matched Beta EI stably;
   do not silently switch to a point mass, alter noise, or discard candidates.
   Preserve explicit failures for invalid/unrepresentable moments.
2. Start a study from the selected immutable dataset: explicit X/Y mapping,
   response goals, factor bounds/domains, missing policy and filter snapshot.
   Preflight displays row counts, exact repeats, and source identity. Commit
   creates completed observations atomically and allows normal recommendation.
   Preserve repeated measurements rather than averaging them implicitly.
3. Store versioned import provenance and hashes; validate schema/source again
   at commit. Keep old generated-design readers unchanged. Protect dataset
   deletion while an imported study owns a reference. Make retries idempotent.
4. Link AI's GP entry to the existing standalone GPR route. Use the selected
   dataset and existing response/predictor form, not a second GP engine.
5. Audit progress/coordinate/desirability graphs against saved values. Correct
   confirmed marker occlusion without moving true coordinates. User screenshots
   are reference layouts, not evidence of a wrong calculation in this app.
6. Inventory the requested actual-vs-LOO, profiler, residual and response-surface
   views. Show only values supported by the corresponding stored model/CV data;
   never substitute training predictions for held-out predictions.

## Contracts And Risks

- Existing artifact JSON is immutable and must not be reserialized on restore.
- New import policy is not LHS/uniform. Use explicit version dispatch.
- Raw limit remains 200 observations/trials and existing factor/domain limits.
  Import is not a way around budgets. No silent row truncation.
- Imported copies are user data; no values, names, paths or private JMP material
  in logs, git evidence, external diagnostics or error strings.
- A source column/schema/filter change invalidates preflight and UI responses.
- Dataset deletion and study creation race must serialize under the existing
  metadata transaction boundary. A new source-reference table requires an
  additive migration and backup/retention tests; no schema bump without SQL.
- Bounded integration for Beta tails must not make acquisition search exceed
  existing worker/evaluation budgets. Verify errors and runtime, not only values.
- Existing BO and standalone GPR keep their distinct fit/normalization policies.
- No new production dependency, release publication or user-workspace mutation.

## Validation

Independent Beta quadrature/closed forms; synthetic real-worker q1/q2 lifecycle;
invalid inputs and no-partial-commit checks; imported X/Y equality and checksums;
schema/filter staleness, repeats, limits, retry, source deletion and restore;
UI source-change deferred responses; built-browser KO/EN ingestion/recommendation
and GPR navigation; visible chart coordinates, markers and keyboard interaction.
Record unit/API/browser/native/release coverage separately. Linux release is
deferred by the user; do not describe local development checks as native release
verification.
