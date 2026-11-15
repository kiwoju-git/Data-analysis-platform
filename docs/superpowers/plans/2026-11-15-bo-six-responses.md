# Six-Response Desirability Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans task by task; one
> read-only reviewer checks compatibility and resource boundaries.

**Goal:** Support 1-6 desirability responses throughout existing BO workflows,
including existing X/Y import, without changing the desirability algorithm.

**Architecture:** Extend the shared response capacity across schemas, domain
validation, storage readers and frontend controls. Preserve all statistical
policies, hashes, source guards, sequential model fitting and resource budgets.
API 45 becomes 46; metadata remains 38 if no SQL structure/check needs changing.

**Tech Stack:** Existing Python 3.10/FastAPI/NumPy/sklearn and React/TypeScript.

**Spec:** User request: increase the current four desirability responses to six.
No new objective, independent-response assumption, kernel, UI redesign or automatic
conversion of stored studies is requested. Continue in the dirty isolated
`feat/bo-500-observations` worktree and preserve the previous capacity/feedback work.
`data_prd.md` is absent; the addendum and current BO contracts remain authoritative.

## Acceptance And Risks

- Six responses accepted; seven rejected before fitting or partial writes.
- All six values/models/predictions survive create, recommend, observe, restore,
  candidate/Profiler/view/report contracts in numeric/mixed/mixture workflows.
- Weighted geometric desirability uses all six; no truncation/reweighting policy
  change. Existing 1-4 response results retain their values and bytes.
- More response models increase cost; existing shared fit/evaluation/time
  budgets remain active. Transport/document capacity is bounded at 24MiB after
  reproducing an 18,532,785-byte six-response/500-row snapshot above the old16MiB
  bound. Owner/workspace quotas are unchanged. No extra parallel fits.
- New six-response artifacts are not promised readable by older four-response code.
- Local server update requires a backend restart; do not interrupt a live fit or
  refresh the user's unsaved form without coordinating the handoff.

## Tasks

- [x] Write/run red tests for six-goal geometry, schema limits, six-column import
  and restore, frontend goal construction/add button and seventh-response rejection.
- [x] Add `MAX_BO_RESPONSES = 6` in backend/core and frontend BO limits; use it in
  all response collections/validators, leaving unrelated dimension/schema fours alone.
- [x] Verify real six-model planning/recommendation and downstream stored view/report
  contracts. Keep existing resource budgets and legacy hash behavior unchanged.
- [x] Update runtime capability, KO/EN wording/help and current product contracts;
  preserve historical evidence documents instead of rewriting old claims.
- [x] Run focused numerical/API tests, existing BO regressions, static checks,
  frontend suite and built-app six-response workflow with a synthetic workspace.
- [x] Review final diff and record failures and unrun environments.
- [ ] Apply the validated local build after a safe server handoff. User approved,
  but the restart command was blocked by the execution tool before running. A
  syntax-checked manual helper is ready; live8620 remainsAPI45. No GitHub
  push/release this turn.

## Evidence

See `docs/bo_six_responses.md` for red/green tests, evidence and resource limits.
Baseline HEAD `0a4f6ec5fd94217210a7b4ec11b37e611fe667ae` plus preserved
uncommitted API45/metadata38 capacity work and field-feedback work.
