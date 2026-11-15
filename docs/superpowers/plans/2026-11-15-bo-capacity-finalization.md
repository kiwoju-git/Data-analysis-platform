# BO Capacity Finalization

## Approved Scope

Finish the already implemented 500-observation, import-field feedback and
six-response changes; apply the local preview, verify load and regressions,
and integrate into main. Do not publish a Linux Release or add BO algorithms.

Baseline after fetch: `0a4f6ec5fd94217210a7b4ec11b37e611fe667ae`.
Reuse the dirty isolated `feat/bo-500-observations` worktree. Preserve every
existing change and private/untracked file in the root checkout. No `data_prd.md`
or nested AGENTS file exists in this worktree. Current contracts override old
historical feature inventories in the broad project guides.

## Acceptance And Risks

- Preview8620 serves the matching API46/frontend with metadata39 and the same
  workspace; do not interrupt an active calculation or rewrite saved artifacts.
- Measure actual six-model fitting of500 synthetic observations, not a duplicated
  fitted-state transport probe. Report time, peak memory, fit settings, convergence
  and restoration. Existing budgets and exact data counts must remain unchanged.
- Exercise six-response mixed/mixture UI paths using synthetic workspaces.
- Run complete local/static tests and native Windows/Linux/security/browser/archive
  gates on the candidate commit. Never treat failed, skipped or running gates as
  passed. Archive verification is distinct from publishing a Release.
- Keep tests sequential on this8GiB machine; use one read-only final reviewer.
- Preserve normalization, desirability math, response ordering, checksums, budgets,
  atomic lifecycle and old artifact readers. Metadata38 widens trial capacity;
  the review found an actual SQL snapshot limit requiring additive migration39.
  Migration39 preserves existing JSON and widens model snapshots only to24MiB.
- Push a feature branch for CI, then merge normally only after required gates pass.
  No force push or branch-protection bypass. Verify remote main after integration.

## Tasks

1. Safely apply the previously validated built preview; verify runtime/UI and
   refresh the existing browser only after the matching server is ready.
2. Add/run a reproducible synthetic500x6 resource benchmark and missing built UI
   coverage. Any product defect first receives a failing regression test.
3. Run whole-project checks, inspect failures, conduct fresh-context branch review,
   and record evidence in `docs/bo_capacity_finalization.md`.
4. Commit the coherent changes, push the feature branch, run native CI, fix real
   failures, merge to main and verify the final remote source/check results.

## Pre-flight

The capacity, field-validation and response-count tasks share import schemas,
runtime compatibility, saved-model payload bounds and E2E stage registries.
Review these together; do not split a commit across incomplete API/UI contracts.
Earlier task logs are history, not evidence of this final commit.

## Progress

- Setup: baseline fetched; existing isolation confirmed; localAPI45 observed.
- Local apply: final API46/metadata39 applied and browser refreshed; all43 business
  tables and4 stored assets verified unchanged, pre-migration SQLite backup retained.
- Resource/browser coverage: numeric/mixed500x6 measured with bounded settings and
  explicit warnings; built numeric/mixed/mixture six-response workflows passed.
  Exactly500-row import/reopen and501-row atomic rejection passed.
- Full checks/review: independent review identified SQL capacity bug; RED/GREEN
  actual insert, migration preservation and rollback tests added. Worker delayed-exit
  failure reproduced independently and fixed without extending the original deadline.
  Native full checks remain in progress; earlier stale-contract failures are recorded.
- Main integration: pending.
