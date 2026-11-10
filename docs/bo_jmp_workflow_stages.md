# Reviewed BO Workflow Stages

Stage1 BASE_SHA: `757554df78e49e0321965c2d92223c41c05b7275`.

The existing UI, noise-aware latent EI/ETI, joint MC batch policy, immutable
history and legacy readers are retained. This is a staged implementation of
the JMP-inspired workflow, not a numerical JMP compatibility claim.

Current integration: API39/metadata32, BO method0.15.0. The remaining
[completion gates](bo_completion_gates.md) connect persistent candidate tables,
manual ordered selection, saved-model Profiler, separate augmentation and typed
nominal/ordinal studies. Current-run validation is recorded in that ledger;
integration in source is not itself a final browser/CI pass.

The earlier [stored target-curve recommendations](bo_target_curve_recommendation_gate.md)
checkpoint was API37/metadata30. Explicit peak-one Gaussian targets connect to immutable
study6, q1..8 review/confirmation, measured entry, restore and reports. DS-linear
remains the default. This follows the separate
[target curve comparison preview](bo_target_curve_preview_gate.md) and builds on
[workshop-led fit quality](bo_fit_quality_gate.md) and
[Stage3h public ordered batches](bo_desirability_public_batch.md).
The hypothetical preview remains non-persistent and never supplies GP predictions.
Candidate tables and augmentation are extended by the current integration;
numerical JMP parity remains unverified.
Stage1 evidence and rollback below are historical, not the
current contract or current test evidence. Stage-specific ledgers define which
later behavior has actually been implemented and verified.

## Stage 1 Acceptance

- Generate a bounded recommendation for review without creating pending trials.
- Show actual settings, base posterior mean, latent/predictive SD and marginal
  acquisition before the operator explicitly confirms the whole ordered batch.
- Confirmation uses the exact server-held calculation, without fitting again.
- Recheck source, pending lifecycle, budget, bounds, constraints and novelty.
- Commit all trials atomically. Repeating confirmation returns the same batch,
  including after restart or after observations have subsequently been entered.
- Source or option changes invalidate the browser review, including stale
  success/error/finally responses. No automatic POST retry.
- Unconfirmed reviews are transient, bounded to eight per application instance,
  four MiB each, twenty minutes, and lost on restart. They are not managed
  artifacts or a persistent imported candidate table. Confirmed batches retain
  the existing full persistence/report/backup contract.

Statistical risk: reordering or dropping selected points would invalidate their
conditional MC marginal scores. Stage 1 therefore confirms the entire ordered
batch; it does not offer misleading subset selection. Privacy risk: reviews
contain model-derived values and remain local, never logs or telemetry.
Compatibility risk: retain the original direct-create API and stored schemas.
Only the additive API contract changes; no SQL or statistical version change.
API30 requires `bayesian_recommendation_review`; metadata remains24.
Resource risk: retain owned spawn worker/time/evaluation limits and bound review
memory. One review calculation is admitted at a time; a second returns the
explicit `bayesian_review_busy` code without starting another worker. Cache
expiry/oldest-entry eviction cannot delete an already committed result.

## Stage Roadmap And Historical Boundaries

1. Versioned numeric kernel choices are now tracked in
   [Stage 2](bo_kernel_alignment.md), including current-run evidence.
2. Multiresponse goal/desirability contracts and immutable observation mappings.
   [Stage 3a](bo_desirability_foundation.md) adds a locally validated pure
   calculation foundation only; no multiresponse API/UI is enabled yet.
   [Stage 3b](bo_desirability_recommendation_core.md) connects raw-response models,
   joint desirability incumbent and q1 mixed candidate search through a bounded
   internal worker. [Stage 3c](bo_multiresponse_lifecycle.md) adds versioned vector
   persistence, exact history reports and read-only UI restoration.
   [Stage 3d](bo_multiresponse_ui.md) adds explicit goal setup and measured-vector
   entry with reviewed, source-locked idempotent saves.
   [Stage 3e](bo_desirability_review.md) now connects q1 multiresponse candidate
   review/confirmation, exact-source restore and managed reports. At that gate,
   API33/meta27 distinguished q1 from unsupported multiresponse batches.
   [Stage 3f](bo_desirability_batch_acquisition.md) adds an internal correlated
   latent conditional-MC/Beta scorer with independent numeric tests. It does not
   expose q>1 review, confirmation, reports or UI at that stage.
   [Stage 3g](bo_desirability_batch_search.md) connects internal q1..8 executable
   mixed search, combined budgets and the same bounded worker. Public q>1 was
   still disabled at that gate. The planned next gate was the complete ordered
   review/confirm/actual observation/restore/report/UI workflow, not another
   isolated math extension.
   No scalar history is repurposed. Stage-specific evidence is in each document.
   [Stage 3h](bo_desirability_public_batch.md) is the public ordered-batch gate:
   review all q1..8 candidates, atomically confirm, enter individual actual
   vectors, restore partially completed batches and report the exact saved
   batch. API34/meta28 and a new version tuple retain the old q1 contract.
   Its current execution ledger, not earlier-stage passes, determines completion.
3. Persistent candidate-set revisions, imported candidates, manual selection,
   profiler and explicitly named augmentation policies.
4. Nominal/ordinal kernel families after their mathematical and storage
   contracts are independently validated.

Do not advertise these options until computation, restore, UI and reports work.
Our Gaussian latent EI/ETI is not JMP's desirability-distribution acquisition.
JMP 19.2 documented candidate workflows are the UX reference:
https://www.jmp.com/support/help/en/19.2/jmp/candidate-set.shtml
https://www.jmp.com/support/help/en/19.2/jmp/current-batch.shtml

## Historical Stage1 Evidence

Implementation and current-run tests are recorded below as they execute.
Prior research tests are not evidence for this change. Linux publication is
deferred; source/build/browser/CI/archive evidence must remain distinguished.

- Red: after correcting a test helper's missing `kind`, the review API test
  failed with404 before routes were implemented.
- Green: native Windows CPython3.10.11 narrow review/noise API/health/web tests:
  `39 passed, 1 skipped` in185.63s. The skip is an existing web-UI build-dependent
  test; not claimed as a pass. This includes actual owned spawn, no-refit
  confirmation, exact numeric result retention, restart retry, concurrent
  confirmation, stale source, tampering, memory expiry and capacity tests.
- Independent review found a confirmation race: another request can commit and
  evict the cache after the first database lookup. A deterministic regression
  reproduced409 instead of replaying201. Moving cache lookup into the replay
  guard fixed it; review/OpenAPI/runtime checks initially passed248 tests. The
  final expanded set passed249 tests in48.48s, including source-during-fit,
  byte-limit and post-observation replay cases. A new independent-run parity
  assertion initially included wall-clock fit duration; only that timing field
  was separated from exact model/candidate numeric comparisons. No numeric
  tolerance was increased.
- Frontend full single-worker suite passed128 files/1102 tests before the final
  captured-callback guard. The updated three targeted files passed200 tests.
  The final full single-worker rerun passed128 files/1103 tests in121.24s.
  Initial lint found11 async callback errors in new tests; corrected rather than
  suppressing the rule. Final lint passed with12 existing fast-refresh warnings.
- Production UI build passed. On native Windows/Chromium, the built UI passed
  review invalidation, KO/EN at1024/1440, no POST on locale/resize/reload, and a
  real server commit followed by simulated response loss and explicit retry.
  The retry retained the same batch and created no extra trial.
- The existing BO built-UI workflow passed q1 target, q2 joint batch, observation
  entry, explicit replicate entry, exact aggregation, restore, managed report
  creation/download and the saved HTML numeric checks. Synthetic fixtures only.
- Screenshot inspection found a wrapped scientific exponent in the narrow
  English review table. A review-only numeric nowrap rule was added; rebuild and
  browser recheck passed, including reinspection of the1024px English screenshot.
- Final Ruff lint and formatting passed (462 files); mypy passed245 source
  files. Tutorial Markdown, capability AST11 tests, generated capability matrix
  and localization checks passed (2961 source strings/4634 keys). Production
  build/typecheck passed; existing large-chunk/plugin-timing warnings remain.
- The full local backend suite was intentionally interrupted at approximately4%
  to limit this computer's resource use. It is not a pass; full native coverage
  is delegated to the unchanged remote CI gates. No product test was removed.
- Full native CI and its archive check remain mandatory before main integration;
  their commit-specific results belong to the PR/check run rather than a claim
  based on previous runs. Linux prerelease publication is intentionally deferred
  by the owner's instruction.

## Historical Stage1 Reproduction And Rollback

Use the repository's locked bootstrap and check scripts. Focused PowerShell:

```powershell
$env:PYTHONPATH = Join-Path $PWD 'backend'
.\.venv\Scripts\python.exe -m pytest `
  backend/tests/unit/test_bayesian_review_api.py `
  backend/tests/unit/test_openapi_frontend_contract.py `
  backend/tests/unit/test_runtime_entrypoint_versions.py -q
```

The focused frontend files are `asyncHookState.test.ts`,
`api/bayesianReview.test.ts` and
`features/bayesian/bayesianRecommendationReview.test.tsx`; use `--maxWorkers=1`
on resource-limited machines. `bo_noise_extension.py` integrates the built/native
review workflow into existing context/workflows suites and archive validation.
Local browser evidence used Chromium, a production Vite build, a loopback API
and a new synthetic temporary workspace, not user data or an installed release.

Revert only this feature's commit with `git revert <feature-commit>`. Runtime,
frontend and backend changes form one contract and must be reverted together.
Stage1 had no metadata migration. Its confirmed recommendations retain the existing
method0.7.0/config2/result2/model3/item2 formats and remain readable by the prior
source. Unconfirmed reviews are transient and are lost on restart. Do not delete
workspaces, models, trials or results as part of a code rollback.

Do not apply that no-migration statement to Stage3h. The current public batch
gate adds metadata28 and a new version tuple; follow its explicit
[compatibility and rollback boundaries](bo_desirability_public_batch.md#rollback).
