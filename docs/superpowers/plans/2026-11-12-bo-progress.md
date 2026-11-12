# BO Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for implementation; use a fresh independent reviewer before integration. Steps use checkbox syntax for tracking.

**Goal:** Add interactive BO progress and saved candidate context without changing recommendation math.

**Architecture:** Bounded, read-only adapters consume verified Study and saved batch responses. Shared SVG charts display measured/derived views. Existing lifecycle and request guards remain authoritative.

**Tech Stack:** React18, TypeScript, Vitest, existing Playwright/Python3.10 tests; no new dependencies.

**Spec:** `docs/superpowers/specs/2026-11-12-bo-progress-design.md`

## Global Constraints

- Preserve UI layout, statistics, API42/metadata33, stored artifacts and user data.
- At most one subagent concurrently; resource-heavy test jobs run sequentially.
- Preserve Windows3.10/Linux3.12/Python3.11 compatibility and required CI gates.
- No Linux Release publication in this task.

## Review Focus

1. Out-of-order completed trials must not imply actual chronological improvement.
2. Pending/abandoned values must not appear as zero or influence cumulative best.
3. Scalar max/min must not invent desirability limits; Gaussian tails must not use DS.
4. Historical candidates must retain saved strategy despite editing the current draft.
5. Equal category labels/overlapping replicates need distinct trial identities and keyboard access.

### Task 1: Read-only progress models and charts

Files: create `frontend/src/features/bayesian/bayesianProgress.ts`, tests,
`BayesianProgressCharts.tsx`, `bayesianProgress.css`, localized message module;
connect in `BayesianOptimizationWorkspace.tsx` for numeric and mixed studies.
Interfaces: `buildBayesianProgress(study, responseId)` produces actual, best and
observed-desirability point sequences; factor projection consumes actual coordinates.

- [x] Write tests for the five review-focus classes, DS/Gaussian/geometric values,
  maximize/minimize/target, nonfinite/missing values, and immutable inputs.
- [x] Run new tests RED; implement adapters; run them GREEN.
- [x] Render three bounded views using existing scatter interaction and category
  ticks; add component tests for labels, units, empty states and source identity.
- [x] Run focused Vitest with one worker, typecheck, lint; commit complete slice.

### Task 2: Replicate disclosure and saved candidate meaning

Files: `BayesianReplicatePanel.tsx`, `BayesianNoiseBatchResult.tsx`,
`BayesianRecommendationReview.tsx`, shared presentation helper/tests as needed.
Interfaces: read saved batch acquisition preference and objective; reviewed
results use their captured source, never an edited live setting.

- [x] Assert initially collapsed controls and visible error/retry outcomes RED.
- [x] Assert stored goal/strategy/acquisition labels across KO/EN and draft edits RED.
- [x] Implement native disclosure and compact right-side context; run GREEN.
- [x] Run existing recommendation/noise/review/replicate regressions and commit.

### Task 3: Built browser verification and JMP comparison

Files: new `tests/e2e/bo_progress.py` or existing suite extension,
fixture entry, `docs/bo_progress_validation_20261112.md`.

- [x] Run built-app synthetic browser flows for scalar/vector/mixed charts,
  keyboard/pin, responsive widths, locale switching, restore, measured entry,
  no POST on chart changes, and unchanged history checksums.
- [x] Rerun local supplied-example comparison against final code; retain private
  inputs locally. Record saved JMP vs app deltas and unmatched conditions.
- [ ] Run full project checks sequentially and independent code review; fix
  important findings with regression tests and record any unavailable checks.
- [ ] Commit evidence, push feature branch, await required native/security/E2E
  gates, merge normally into main, and verify final remote SHA. No force push.

## Execution Ledger

- BASE_SHA: `1df6515a7e5e0e728633e0b1f16f42e7f23911e8`.
- Branch: `feat/bo-progress-charts`, existing isolated `bo-desirability` worktree.
- User approved three graph types, existing interactive styling, comparison MD
  and main publication. No new approval loop between implementation tasks.
- Ruling: progress projection is UI-only and does not bump API or statistical
  versions. Existing saved goals/trials are sufficient; unsupported policy values
  fail visibly instead of producing guessed desirability.
- Independent review found and tests reproduced pending-state pin ownership,
  weighted Gaussian overflow, and sparse/long category tick issues. All are
  addressed in the display adapter without changing stored data or GP math.
- Initial built-browser failure was the new selector's implicit accessible label,
  which included option text. Explicit names fixed this; no timeout was increased.
- First full frontend run: 1423 passed / 3 failed because an older review fixture
  omitted required incumbent/planning fields. Updated that fixture to the real
  response contract. Fresh full rerun:160 files/1427 tests passed.
- Verified implementation SHA: `834694d30d53c5d1a1fe21ac9ab3527c10988c81`.
  Fresh private JMP baseline/sensitivity checks:108/24 passed;16 fits recorded.
  Saved-output differences and unknown final JMP settings remain documented,
  rather than treating independent numerical checks as proof of JMP parity.
- Local full backend was not run; focused backend/reference tests, all frontend
  tests, static checks and built-browser journeys passed. Required native CI and
  main integration remain open until their actual completion.
