# Existing X/Y BO Start Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development. Track each test cycle here.

**Goal:** Repair recommendation precision, import measured X/Y safely, and expose the existing GPR workflow.

**Architecture:** Reuse common dataset selection and immutable canonical rows. Add an explicit imported-study policy and transactional source reference. Keep BO/GPR computation separate; repair Beta EI without changing its statistical definition.

**Tech Stack:** Existing Python 3.10/FastAPI/SQLite/SciPy, React/TypeScript/SVG.

**Spec:** `docs/superpowers/specs/2026-11-12-bo-xy-start-design.md`

## Global Constraints

- BASE_SHA: `0070640d8bab3ae8aa2218fea7165cfe229562ee` (fetched origin/main).
- Preserve user preview and all user data. Synthetic external workspaces only.
- No new production dependency or Linux release publication.
- At most one heavy test/worker job at a time; a read-only reviewer may run alongside.
- Baseline API42/metadata33; implemented API43/metadata34 for the new contract
  and actual import ownership/idempotency SQL migration.

## Review Focus

- Positive but tiny Beta EI must not be converted into fake deterministic zero.
- Existing dataset filters/schema may change between preflight and import.
- Duplicate network confirmation must not create a second study.
- Historical data may contain repeated coordinates with different observations.
- Graph overlap and held-out-vs-training labels must remain truthful.

## Task 1: Stable Beta Improvement

Files: `backend/app/statistics/bo_desirability_acquisition.py`, focused numeric
helper if needed; `backend/tests/unit/test_bo_desirability_acquisition.py`,
`test_bo_desirability_public_batch.py`; algorithm/version contracts.

- [x] Baseline: acquisition unit tests, 24 passed (Windows Python3.10).
- [x] Capture exact synthetic failing moments, distinguish rounded underflow from positive EI.
- [x] Implement cancellation-safe Beta EI with explicit numeric-error checks.
- [x] Run unit/reference tests and real q1/q2 review-confirm-observe-next-review.
- [x] Document numerical policy and compatibility.

## Task 2: Versioned Dataset Import Backend

Files: new `backend/app/api/v1/schemas/bo_dataset_import.py`,
`backend/app/services/bo_dataset_import.py`, relevant study readers/storage,
dataset retention, routes and migration; import API/restore/security tests.

Interfaces: typed preflight + from-dataset commit using version/schema/canonical
hash, filter, X column/factor mapping, Y column/objective mapping, request ID.
Preflight returns counts/source digest; commit consumes expected digest and
returns the normal study response. No GP fit during import.

- [x] Red tests: exact X/Y, repeats, stale schema/filter, 201 rows, incomplete Y,
      transaction rollback, idempotency, dataset-deletion conflict.
- [x] Implement explicit imported initial policy and source ownership.
- [x] Verify scalar/multiresponse recommendations, restore and legacy bytes.
- [x] Update import contract and API/runtime schemas.

## Task 3: Dataset Import UI And GPR Entry

Files: `BayesianOptimizationWorkspace.tsx`, import form/hook/types/client,
AnalysisShell prop boundary, domain landing/navigation and relevant tests.

- [x] Red tests for selected dataset mapping, stale preflight, preserved input,
      no implicit POST retries and navigation to existing GPR.
- [x] Add new-initial-design/existing-X/Y mode, map columns and explicit preflight.
- [x] Keep creation response ownership guarded; surface committed study/catalog.
- [x] Verify actual built UI with synthetic CSV, recommendation and stored report.

## Task 4: Graph Audit And Verification

Files: `BayesianProgressCharts.tsx`, `bayesianProgress.css`, chart tests/E2E,
`docs/bo_xy_start_validation.md`.

- [x] Assert measured and cumulative-best markers remain visible at identical X/Y.
- [x] Fix proven occlusion; verify no coordinate, response or history changes.
- [x] Inventory existing LOO/profiler/residual/surface support against references.
- [x] Run relevant suites, full project checks, built UI and independent review.
- [x] Record exact commands/results/unverified environments and integration policy.
- [ ] Re-fetch origin/main, commit the complete contract, fast-forward and push.

## Execution Record

- Source audit: multiresponse q2 failure reproduced previously in an isolated
  real-worker built app; this task will rerun after the numeric fix.
- Baseline GPR was present under regression; the AI entry now opens that same
  method, preserving header-selected data and the canonical regression route.
- Baseline dataset import was future-only; the versioned API/UI is implemented.
- Marker occlusion is source-confirmed; user-reference images do not establish
  an application calculation defect. No new graph values will be invented.
- Numeric acquisition/batch/public API suite: 79 passed on this worktree.
- Backend import focused suite: 19 passed. Broader no-fit regression: 101 passed,
  one old migration-table expectation failed, corrected in the focused rerun.
- Frontend request ownership: 6 passed, including RED/GREEN normalization of
  omitted/null filter values; no automatic write retry, late-result invalidation.
- Full frontend: 164 files / 1473 tests passed. Final build/lint/typecheck,
  backend Ruff/mypy, localization/capability and Windows dependency audits passed.
- Built UI: import, stale preflight, locale/resize, q2/observe/q1, GPR actual fit,
  progress chart interactions and managed report/offline HTML passed. Initial
  failed browser attempts remain in diagnostics; they are not counted as passes.
- Independent source review is complete. Its report-reader finding was verified
  and fixed with RED/GREEN tests and actual managed-report browser output.
- Full integration initially found stale contracts and a missing local venv.
  These failures and their fixes remain in the execution ledger; no checks were
  removed. Final official `scripts/check.ps1` exited0: backend4443passed/10skipped,
  frontend1473passed, all static/build steps passed.
- See `docs/bo_xy_start_validation.md` for detailed evidence, remaining limits,
  the final browser rerun and remote integration/rollback boundary.
