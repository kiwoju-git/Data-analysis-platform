# BO Noise-Aware Frontend Contract and Evidence

## Preserved Behavior

- The existing sequential UI still sends a one-item batch; there is no second single-target form.
- Legacy recommendation and mean-fantasy batch readers/rendering remain separate from V2.
- The existing study lifecycle, trial observation inputs, immutable history, dense settings tables,
  result tables, and shared number formatting are retained.
- No external calls, telemetry, new dependencies, model calculations, or automatic observation values
  were added to the frontend.

## New V2 Boundary

`useBayesianRecommendationState` snapshots the current history ID/hash and sends schema 2 through
the existing batch endpoint. Noise settings are `estimate` (default), raw-unit fixed measurement SD,
or `near_noiseless`. Advanced bounds are standardized-Y variances, not SD or jitter. Exact replicate
compression is explicit; nearby diagnostics require factor-specific tolerances and do not merge data.
The existing search defaults are retained with the V2 MC policy; sample count and optional normalized
batch distance are explicit settings.

`boNoisePolicy` rejects empty/partial/nonfinite numeric strings, reversed bounds, out-of-bounds initial
variance, fractional sample counts, and missing nearby tolerances. Each invalid field has an associated
accessible error. The global `formatLocaleNumber` defaults and model values are not changed.

Changes to requested policy/options and study history invalidate pending creation. Success, error and
finally all check request ownership. Returned study/history/hash are checked before applying results.
Locale and viewport are not request sources. Stored results remain identified as committed snapshots
when settings are edited; the stored result is not recomputed or relabeled as the draft.

`BayesianNoiseBatchResult` separates observed best, latent incumbent, base-posterior mean, latent SD,
new-observation predictive SD, and conditional planning SD. Raw-unit and standardized acquisition values
are separately labeled. MC seed is a string, avoiding JavaScript's integer precision limit. Raw N,
unique-condition N, effective training N, group members, within-group variation, nearby distances,
constraint status, all-zero acquisition status, and saved warnings remain visible.

## Explicit Replicates

`useBayesianReplicateState` and `BayesianReplicatePanel` require a completed parent, count 1-8,
available trial budget, active/no-pending lifecycle, and explicit intent confirmation. New trials use
the same coordinates and retain their parent identity; the existing observation table receives their
actual, independently entered measurements.

A failed or disconnected POST is not automatically repeated. An explicit retry preserves the exact
request ID and payload. The original server commit is not deleted. A successful registration is shown
independently of a subsequent trial-list refresh failure. `bayesianRequestId` uses Web Crypto UUID or
cryptographic random bytes on HTTP LAN; it never substitutes `Math.random`.

An idempotent replay can return the current completed or abandoned state if an operator has already
entered the replicate observation. The hook accepts these terminal states only on replay, preserves
study/version/parent/history ownership checks, and requires finite observations only for completed
trials. A new registration must still return pending trials with no invented observation.

## UI Guidance

Installed `ui-ux-pro-max` was applied narrowly: explicit form labels, field-linked errors, controlled
React inputs, secondary replicate commands, progressive advanced settings, and existing product tokens.
No replacement design system or layout-wide refactor was introduced.

## Verification Evidence

Executed on the Windows worktree during implementation:

- Vitest: `src/features/bayesian` plus `src/asyncHookState.test.ts`, 212 tests passed at the recorded
  run. Covers strict policy inputs, KO/EN static markup, tiny values, escaped user identity, preserved
  payloads, q1 target routing, option/history request races, prior finally protection, explicit replicate
  retry identity, terminal-state replay, inconsistent ownership/observation rejection, and stale
  replicate responses. This is not browser evidence. Before the terminal-state fix, the new tests
  reproduced two failures (completed/abandoned replay); the pending replay case already passed.
- Targeted ESLint: BO feature directory and BO API/type files passed.
- Whole frontend TypeScript check passed after the concurrently updated GPR types were connected.
- Python tests: release receipt and E2E suite-partition tests, 247 passed at the recorded run.
- Ruff: changed BO E2E and release-verification Python files passed.

New executable browser fixtures, **not executed locally by this subtask**:

- `tests/e2e/bo_noise_extension.py::verify_bo_noise_extension`: API-only synthetic initial provisioning,
  then visible q1 target, q2 joint batch, actual observation inputs, replicate registration, exact
  compression (raw 9/effective 7), KO/EN 1024/1440, restore, and no POST on locale/resize/restore.
- `verify_bo_noise_context`: server commits a replicate POST while the client receives a synthetic
  connection failure, then explicit identical retry proves no duplicated trials or altered history.
- Both are wired into distinct native workflow/context stages and the exact built Linux archive
  browser harness. The release verifier rejects missing/incomplete receipts.

Local dev/server startup had already been denied in the parent task; this subtask did not retry it.
Browser layout, native CI, archived installation, performance and release publication remain separate
gates owned by the parent integration. A fixture definition or static markup pass is not a passing
browser/release claim. Full frontend checking is also an integration gate while GPR files change.
