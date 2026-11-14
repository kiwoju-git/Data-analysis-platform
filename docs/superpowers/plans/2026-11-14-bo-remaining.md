# BO Remaining Work Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete whole-factor profiling, immutable diagnostic view/report storage, explicit legacy recommendation renewal, and a bounded single-mixture BO workflow.

**Architecture:** Extend the existing numeric/mixed BO planning modules and saved safe GP evaluators. Views belong to exact BO model/history identities, not generic analysis IDs. A versioned mixture domain adapter owns closure, encoding, distance and profile paths without changing existing study bytes or scalar recommendation policies.

**Tech Stack:** Python 3.10+, FastAPI/Pydantic, SQLite, NumPy/SciPy/sklearn, React/TypeScript, existing SVG charts and Vitest/Playwright.

**Spec:** `docs/superpowers/specs/2026-11-14-bo-remaining-design.md`

## Global Constraints

- Baseline origin/main `a9abb4bac0f6104b8fd6ac270edcc80a5bc32050`; implementation starts at `41143beeb4f1935201717e5ff8e9f18ae266f4fe` on `feat/bo-remaining44`.
- At most two auxiliary agents; one heavy local test/build/model task at a time.
- Python 3.10, CPU-only, no new production dependency, no user pickle, no external dataset transfer.
- No automatic rewrite of historical JSON/hash inputs; immutable model/history/candidate ownership stays strict.
- Existing scalar and mixed BO, DOE/GPR, UI tokens/charts, canonical GPR menu and request fences remain.
- API43 becomes API44 for this integrated contract. Metadata changes only for actual new SQL structures.
- Whole matrix: at most 10 factors, 4 responses, 100 points per API evaluation chunk; sequential requests and bounded total budget, no partial success.
- Mixture: one continuous group of 2-8 components, total factors <=10, 1-4 response desirability planning only. No scalar EI/ETI mixture fallback.
- Exact JMP output parity is user-owned. No Linux Release publication. Native/security/archive validation is not waived.
- Private `docs/jmp`, user workspace/data and screenshots are not committed.

## Review Focus

- Model/history changes during the last matrix chunk must not publish an obsolete partial view (Task 1 deferred tests).
- A historical diagnostic view is readable/savable but cannot carry stale novelty or trial-confirmation permission (Task 2 owner tests).
- A successful commit with lost network response must replay exactly, including renewal lineage (Task 4 idempotency/race tests).
- Mixture closure and distance must not silently change when pseudocomponent coding changes (Tasks 5-6 independent fixtures).
- Restored old study/model/report bytes must retain their original interpretation and checksums (Tasks 2,4,6,8 compatibility tests).

---

### Task 1: Complete Source-Locked Profiler Matrix

**Files:**
- Create `frontend/src/features/bayesian/boProfileMatrix.ts`, `BayesianProfileMatrix.tsx`, `hooks/useBoProfileMatrix.ts` and matching tests.
- Modify `BayesianPlanningPanel.tsx`, `BayesianMixedPlanningPanel.tsx`, `BayesianProfileGrid.tsx`, `boPlanning.css`, `frontend/src/i18n/boPlanning.ts` only where shared existing presentation is reused.

**Interfaces:**
- `ProfileAxisPlan`: factor identity/name/unit/category, executable points, actual axis bounds and meaning.
- `evaluateProfileMatrix(plans, evaluateChunk, isCurrent, budget)`: sequential chunks; returns complete axis rows only or fails/stales without partial publication.
- `useBoProfileMatrix`: context/model/hold snapshot fence, applied matrix, busy/error, evaluate and invalidate.
- `BayesianProfileMatrix`: response rows/factor columns, paged columns, shared per-response range; quantity switch is display-only.

- [ ] Write tests for all numeric/mixed axes, response ID `desirability`, category levels, <=100 row chunks, late-chunk rejection, A-B-A edits, budget exhaustion and unchanged inputs.
- [ ] Run `npm --prefix frontend run test -- --run src/features/bayesian/boProfileMatrix.test.ts` and record expected missing-feature failure.
- [ ] Implement the bounded executor/hook and matrix component using existing point generators, result validators and SVG interaction; add a whole-factor action without removing single-axis/point controls.
- [ ] Run new tests plus existing numeric/mixed planning component/hook tests, typecheck; reviewer checks source fence and visual scale semantics.
- [ ] Commit coherent frontend feature with its tests and evidence.

### Task 2: Server Diagnostic Receipts And Immutable Views

**Files:**
- Create `backend/app/api/v1/schemas/bo_views.py`, `backend/app/services/bo_views.py`, `backend/app/storage/bo_views.py` and unit/API tests.
- Extend BO routes and metadata migration, existing numeric/mixed saved-model and LOO evaluators through thin adapters; preserve old API paths.

**Interfaces:**
- `evaluate_bo_view(settings, study_id, request) -> BoViewEvaluation`: exact model hash, view kind/applied holds/axes, server numeric payload, bounded receipt ID/hash/expiry.
- `save_bo_view(settings, study_id, request) -> BoSavedView`: expected receipt/model/content hashes + request ID; no re-evaluation or refit.
- `get_bo_view` / `list_bo_views`: validate stored hashes/owner/version without requiring current study history.
- `BoViewPayload` omits novelty, pending state and candidate eligibility; retains fixed constraints and immutable source only.

- [ ] Add tests for historical model evaluation, forged payload/hash/owner, expiration, same-ID retry and conflicting reuse, no-fit save and rollback on failure.
- [ ] Run new pytest files red; implement bounded receipts plus transactional view storage and real additive migration.
- [ ] Assert database upgrade preserves previous model/result bytes, foreign ownership fails, restart reads saved views and abandoned receipts do not persist.
- [ ] Run storage/migration/BO owner regression tests and review before committing.

### Task 3: Saved View UI, Reports, Retention And Backup

**Files:**
- Extend `frontend/src/api/boPlanning.ts`, controlled BO types, matrix/LOO panels with explicit save/open controls.
- Extend `backend/app/api/v1/schemas/reports.py`, BO report source resolver/renderers, report coverage, retention and workspace backup contracts.
- Create `backend/app/services/bo_view_report.py` and focused renderer/API tests.

**Interfaces:**
- `BayesianHistoryReportSource` new typed `view` attachment identifies a validated saved view and original history.
- `render_bo_view(view, locale)` renders saved numeric rows/LOO only; no dataset/model evaluation.
- Save action consumes exact server receipt; UI displays applied holds/hash and historical status.

- [ ] Add failing save/open/report tests proving all factors/responses, axis units, both uncertainty meanings and no fit/raw loading during export.
- [ ] Implement six ownership paths together: API, UI, catalog, report, retention/deletion and offline backup/restore.
- [ ] Verify idempotent save, checksum conservation, HTML escaping/CSP, KO/EN and keyboard behavior; run report and backup regressions.
- [ ] Review and commit the end-to-end saved view feature.

### Task 4: Explicit Legacy Augmentation Renewal

**Files:**
- Extend `backend/app/api/v1/schemas/bo_augmentation.py`, BO augmentation route, `services/bo_augmentation.py`, `bo_augmentation_batches.py`, planning storage/lineage.
- Extend `frontend/src/features/bayesian/hooks/useBayesianAugmentation.ts`, `BayesianAugmentationPanel.tsx`, API/types and localized renewal labels.
- Add unit/API/UI renewal tests.

**Interfaces:**
- `renew_augmentation_selection(settings, study_id, selection_id, request)` clones stored request with new request ID; exact old model/candidate/history and current numerical policy.
- Renewal lineage records parent selection/config/result hashes outside old hash payload; new selection/lineage commit atomically.
- First confirm of absent-policy legacy EI returns stable renewal-required code. Confirmed replay remains supported.

- [ ] Add red tests for absent-policy first confirmation, unchanged historical GET/hash, same-request retry, differing payload conflict, pending/history/closed rejection and confirmed replay.
- [ ] Implement explicit renewal; do not use current UI draft, auto-confirm, refit or relax worker numerical validation.
- [ ] Add UI review transition, exact new rows/scores, parent link and source invalidation; run existing augmentation race/compatibility suites.
- [ ] Review and commit.

### Task 5: Mixture Domain Mathematics And Contract

**Files:**
- Create `backend/app/statistics/bo_mixture_domain.py`, `backend/app/api/v1/schemas/bo_mixture.py`, domain tests.
- Extend versioned study/domain dispatch and safe model snapshot validation without modifying old schema parsing.

**Interfaces:**
- `validate_mixture_domain(factors, mixture)` resolves ordered components, S, bounds, coding mode and positive-dimensional feasibility.
- `encode_mixture_point` / `decode_mixture_point`: exact lower/upper pseudocomponent formulas from spec; reject nonclosure, no renormalization.
- `mixture_design_distance`: actual bound-normalized numeric distance, category equality/ordinal semantics; independent of GP coding.
- `mixture_profile_points`: co-vary excess/deficit ratios, bounded feasible interval, explicit unavailable zero mass.

- [ ] Red tests: L=(.3,.4,.1), S=1, z=(1,0,0) maps (.5,.4,.1); upper roundtrip, finite/units/bounds/closure/degeneracy, fixed components, coding-independent distance.
- [ ] Implement pure typed helpers; use independent algebra/hand fixtures, not production helper generated reference values.
- [ ] Add new study contract and preserve old schema5/6/7 bytes/readers. Select new versions from actual current dispatch; do not reuse old semantics.
- [ ] Run domain/schema/reference tests; review before integration.

### Task 6: Mixture Study, Fit, Candidates And Trial Lifecycle

**Files:**
- Extend mixed study/import/initial-design services, `bo_factor_domains.py`, numeric/mixed saved surrogate adapters, planning candidate/selection/confirmation paths and storage CHECK migration if required.
- New mixture integration tests use synthetic histories only.

**Interfaces:**
- Domain-policy adapter selects numeric surrogate when no category, mixed equality kernel when category exists. No dummy category.
- Candidate generator returns feasible actual closure points and seed/attempt/termination metadata; candidate/manual/import entry points share domain validation.
- Stored model carries ordered mixture transform and unchanged actual training coordinates; restore always uses stored transform.

- [ ] Add red API tests for create/import/fit/predict/candidate/confirm/observe/next, process categories/discrete levels, insufficient feasible pool, atomic batch rollback and duplicate requests.
- [ ] Implement bounded seeded closure-polytope sampling, current budget/constraint/novelty guards, safe numeric encoding and versioned lifecycle contracts.
- [ ] Verify same actual point produces same prediction through live model, restored model and candidate scoring; closure/history source hashes remain immutable.
- [ ] Run numeric and mixed lifecycle/retention/backup regression suites; review and commit together with needed schema migrations.

### Task 7: Mixture UI, Co-Varying Profiler And Reports

**Files:**
- Extend BO definition/import controls, mixed planning/profile adapters, controlled API types and localized messages.
- Extend saved view renderer for declared co-varying component path and mixture metadata.

**Interfaces:**
- New study mode explicitly sends group components/total/coding; incompatible scalar/extra-group requests are explained, not converted.
- Matrix component consumes feasible mixture-axis plans from the shared domain contract; process factors keep existing conditional paths.

- [ ] Add red UI tests for input intermediates, all-numeric mixture, mixture+category, unsupported scalar mode, hold changes, closure and zero balancing mass.
- [ ] Implement minimal existing-style controls and co-varying curve labels; preserved actual units and applied settings.
- [ ] Verify saved views/report/restore keep mixture path, coding, domain and exact values; run KO/EN/source guard tests.
- [ ] Review and commit.

### Task 8: Integrated Evidence, Compatibility And Main

**Files:**
- Extend `tests/e2e/bo_persistent_planning.py`, built workflows registry and new focused view/mixture journeys.
- Update runtime API contract, method/report contracts, capability docs, `docs/bo_remaining_completion.md` and this plan ledger.

- [ ] Built UI: imported numeric/mixed history -> fit -> complete matrix -> save/open/report; old recommendation -> renew/review -> confirm; mixture import -> fit -> candidate -> observe -> next.
- [ ] Assert exact values/source hashes, locale/resize no computation POST, stale success/error/finally rejection, keyboard interaction and server-offline HTML.
- [ ] Run full local backend/frontend checks with one heavy task; run existing Windows E2E partitions and collect current failures without suppressing tests.
- [ ] Fresh independent whole-branch review; fix important findings with regressions.
- [ ] Fetch origin/main, preserve newer commits, normal merge/fast-forward and push only coherent verified code. Record final remote SHA and exact CI outcomes; no force push or Release publication.

## Execution Ledger

- 2026-11-14: user approved all four design deliverables. Source and instruction scan completed; `data_prd.md` absent. Existing stabilization commits are baseline evidence only, not new feature verification.
- Tasks 1-7: implemented and reviewed, with focused regression evidence in
  `docs/bo_remaining_completion.md`. Final process-axis findings were corrected
  in one consolidated fix wave and scoped re-review passed.
- Task 8: numeric and mixture built journeys passed; full local check and native
  CI/integration remain pending. The task checklists above retain the original
  execution sequence; this ledger and the completion audit record actual status.
- Acceptance is end-to-end; helper tests or old successful CI runs do not complete these tasks.
