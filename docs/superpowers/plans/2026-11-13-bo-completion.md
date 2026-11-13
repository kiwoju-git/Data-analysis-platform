# BO Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Track each task and its evidence separately.

**Goal:** Repair current BO-related CI regressions, complete the requested remaining BO options, verify, and integrate into main without publishing a Linux release.

**Architecture:** Preserve existing numerical policies, immutable receipts and request ownership. Reuse existing BO import/domain/search contracts; scope mixture support only after reviewing its mathematical and lifecycle requirements.

**Tech Stack:** Python 3.10+, SciPy, FastAPI, React/TypeScript, existing SVG charts and Playwright.

**Spec:** User request for mandatory fixes plus remaining feature strengthening; existing `docs/bo_beta_numerical_compatibility.md`, `docs/bayesian_initial_observation_import_contract.md`, and `docs/bo_factor_correlation_contract.md`.

## Global Constraints

- BASE_SHA: `e36d40a7569bad311c08f294edbfa51f76cac82b`.
- Keep API 43 / metadata 34 unless a real new contract requires an increment.
- No changes to legacy recommendation bytes, numerical policy or user workspace.
- No Linux release publication in this task. Keep all existing CI gates.
- At most two auxiliary agents; only one heavy fit/test process at a time.
- No private `docs/jmp/` material or `examples/image2.png` in commits.
- Ordinary main merge/push only; preserve newer remote changes.

## Review Focus

1. Legacy algorithm dispatch must be tested independently of platform-specific floating-point output.
2. Canonical regression GPR navigation must preserve the selected dataset; no duplicate AI entry.
3. Advanced import option changes must invalidate stale preflight without losing user data.
4. Mixture closure must hold in creation, import, candidates, recommendations and saved readers, not merely in UI validation.
5. Documentation must distinguish current implementation, historical evidence, pending work and unexecuted checks.

## Task 1: Repair Existing CI Regressions

Files: `backend/tests/unit/test_bo_beta_numerical_policy.py`, `tests/e2e/critical_path.py`, focused tests and `docs/bo_completion_validation.md`.

- [x] Record CI run 43285568827 failures and local baseline.
- [x] Replace Windows-only computed-value equality with an independent frozen-operation-order expectation using the installed SciPy implementation. Preserve exact serialized legacy fixture/hash tests; no widened algorithm tolerances.
- [x] Test that absent policy selects the frozen algorithm, explicit current policy selects current implementation, and old limits/errors remain.
- [x] Replace stale contextual GPR-card assertions with actual AI-to-GPR navigation and dataset preservation assertions; retain executable GPR path coverage.
- [x] Run focused unit checks and built-app navigation, obtain independent review, commit.

## Task 2: Existing X/Y Advanced Options

- [x] Inspect reusable linear-constraint and categorical-correlation editors and draft validators.
- [x] Add focused failing request/state tests, then expose existing policies in the import flow without altering global dataset selection.
- [x] Validate stale preflight, actual constraints, correlation serialization, KO/EN and restore.
- [x] Review and commit with current capability documentation.

## Task 3: Mixture/Pseudocomponent Support

- [ ] Review source and official mathematical references; write explicit design before implementation.
- [ ] Confirm scope and closure/coding/search/storage contract; do not disguise ordinary inequality constraints as mixture support.
- [ ] Add independent transform, closure, constrained-search and lifecycle tests before implementation.
- [ ] Implement an end-to-end versioned slice including UI, stored readers and report semantics; review and commit.

## Owner Follow-up: Graphs And Canonical GPR Navigation

Owner confirmed on 2026-11-13 to continue the discussed graph/workflow stages,
and that standalone GPR should remain in its existing regression module without
an additional AI/ML entry. This supersedes Task 1's AI cross-link expectation.

- [x] Remove only the duplicate AI cross-link metadata, retaining the executable
  regression GPR route, dataset context, saved models and prediction workflow.
  First update navigation tests to fail on the current duplicate placement;
  then align capability metadata and E2E navigation with the canonical module.
- [x] Audit existing progress, conditional LOO and profiler views against the
  requested workflows before adding graphs. Reuse stored source-locked data and
  the shared chart primitives; do not label in-sample residuals as LOO residuals.
- [x] Implement only evidenced graph gaps/defects with tests for exact values,
  source changes, constant/unavailable data, KO/EN and built-browser interaction.
  Code and focused tests are complete, including the review-found dense-category
  label issue. Built Windows GPR/numeric/mixed journeys passed on run 2; run 1's
  stale E2E accessible-name failure remains recorded rather than hidden.
- [x] Investigate the recorded cross-platform stored-EI reader risk separately
  from the CI test portability fix; keep original bytes and hash protection.
  Actual saved-reader call paths and one simulated cross-OS serialized primitive
  are now confirmed. The owner approved historical receipt preservation on
  2026-11-13. Add a saved-reader-only boundary for the historical numerical
  policy, retaining checksum/source/policy/structure checks and all current
  calculation/commit-time numerical validation. Reproduction and tamper tests
  preceded the production change. Endpoint range guards reuse the frozen
  arithmetic budget; no global EI matching tolerance was widened. The first
  confirmation of an unconfirmed legacy result remains platform-sensitive.

## Task 4: Final Validation and Integration

- [x] Reconcile current capability documents and preserve historical evidence labels.
- [ ] Run narrow regression, full project checks, built-app synthetic workflows and security checks.
- [ ] Review whole branch, fetch latest remote, merge normally and push main.
- [ ] Verify CI for the exact final SHA and record actual passed/failed/unexecuted checks; do not publish Linux assets.
