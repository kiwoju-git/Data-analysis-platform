# BO Import Field Validation Implementation Plan

**Goal:** Identify missing/invalid fields in Existing X/Y import without changing
valid request payloads, calculations, persisted data, or the current layout.

**Architecture:** Add a pure, locale-independent field-issue projection beside
the existing authoritative request builder. Render translated inline feedback,
accessible invalid/described-by attributes, and a linked summary. Validate on
preflight, then recheck on edits without moving focus on every keystroke.

**Scope:** Study name, X/Y column mappings, numeric domains/steps, category levels,
scalar target/tolerance, desirability thresholds/importance, and display aliases.
Advanced backend/constraint/source errors retain the existing form-level notice;
do not guess an offending field from an ambiguous server error code.

**Constraints/Risks:** Preserve the existing dirty 500-row worktree; no migration,
API/schema/statistical version changes or new dependencies. Strict parsing must
not turn empty strings into zero. Keep source/latest-request invalidation and
idempotent creation unchanged. Use synthetic fixtures, never user records.
Do not replace the live built UI before validation or discard the user's draft.

## Acceptance And Steps

- [x] Add failing tests for simultaneous missing name/targets, strict numeric
  parsing, bound/goal order, duplicate/absent columns, category/discrete domains,
  stable row keys after deletion, and preservation of draft/request values.
- [x] Implement `datasetImportFieldIssues(version, draft)` with semantic codes;
  existing request builders and backend validation remain authoritative.
- [x] Connect inline errors and `aria-invalid`/`aria-describedby`; after failed
  preflight focus the first invalid field, with summary links for other fields.
  Fixing a field removes its error. Editing does not steal focus or re-mount.
- [x] Test shared response-goal optional feedback without changing other callers.
- [x] Run focused tests, typecheck, lint, all frontend tests, localization checks,
  and a separate built-app browser test (KO/EN, narrow/wide, no invalid POST,
  valid preflight, locale changes and input preservation; existing unit tests
  cover source ownership, not a new full browser source-switch scenario).
- [x] Document actual evidence and limitations; deploy frontend assets locally
  only after validation, without automatically refreshing the user's form.

## Review Focus

- Inactive thresholds and scalar maximum/minimum must not require target inputs.
- Numeric zero and scientific notation remain valid; partial drafts remain text.
- Cross-field errors clear when either dependent field changes.
- Category identities and original column names are not translated or rewritten.
- Server-only failures must not falsely mark arbitrary fields invalid.

## Evidence

`data_prd.md` is absent; the addendum and current BO import contract were
used. Source-confirmed: `buildDatasetImportRequest` returns one code and the form
renders a single generic error block. UIX Pro Max guidance: inline errors linked
with `aria-describedby`, non-color indication, accessible summary/focus.

### Source And Review

- Worktree `feat/bo-500-observations`, base
  `0a4f6ec5fd94217210a7b4ec11b37e611fe667ae`; existing uncommitted capacity work
  preserved. This change adds no backend/API/metadata/statistical version change.
- Initial 14 new tests failed because the field validator did not exist. The
  first built-app red run failed on the missing `aria-invalid` attribute.
- Independent read-only review caught two regressions: valid fixed mixture
  bounds were rejected, and focus could target a disabled constrained X mapping.
  Each was reproduced before correction. Final review found no further concrete
  behavior issue in those boundaries, and strengthened the locked-link test.
- During integration, a helper initialization-order error caused eight existing
  component tests to fail and the synthetic page to lose its import form. Fixed
  with a hoisted helper; do not count that failed run as successful validation.
- A full single-thread-pool experiment hit the existing lazy-loader test timeout
  and was stopped. No timeout was increased; final regression uses the normal
  fork pool with one worker; all 1,605 tests subsequently passed.

### Final Verification

- Focused validator/request/advanced/component tests: 44 passed before the final
  focus adjustment. Final complete frontend run: 183 files, 1,605 tests passed,
  zero failures/skips. `frontend-final.json` contains the machine-readable report.
- Production build including TypeScript: passed, external temporary output only.
  Existing chunk-size/plugin-timing warnings remain.
- Localization checker: 3,047 source strings / 4,727 keys verified.
- Frontend lint: exit 0, no errors; 12 existing Fast Refresh export warnings in
  unrelated GP/regularization/DOE modules. New feedback helper has no warning.
- Python ruff on both affected E2E modules: passed using the root Python 3.10
  environment. The worktree environment lacks the ruff executable; its initial
  module invocation failed before lint execution and was not counted as passing.
  Ruff format check passed after formatting the new Python test. Git diff check
  also passed.
- Built-app browser/API test passed on Windows 10 build 19045, Python 3.10.11,
  Chromium 149.0.7827.55 with synthetic 12-row data. Invalid drafts made zero BO
  POSTs; repaired drafts made one real preflight with `n_used=12`, no study or
  model created, no page errors. KO/EN, 1024/1440 widths, DOM spacing/overflow,
  summary navigation, partial `1e` draft, locked X/duplicate Y, and Korean study
  name preservation verified. Screenshot inspected as well as numeric DOM checks.
- Evidence is outside Git at `%TEMP%/DataLab-bo-field-validation-20261115/`:
  initial/review failures retained separately from `green-final` and the final
  strengthened-test rerun `green-reviewed` (passed).
- Not run for this UI-only change: full backend suite, Linux/native CI,
  release archive, browser zoom, assistive-technology session. No GitHub push
  or release publication performed. No user workspace was used as a fixture.

### Commands

From the isolated worktree, with one test worker to limit resource use:

```powershell
npm --prefix frontend test -- --run --maxWorkers=1 --reporter=json --outputFile="$env:TEMP\DataLab-bo-field-validation-20261115\frontend-final.json"
npm --prefix frontend run lint
npm --prefix frontend run build -- --outDir "$env:TEMP\DataLab-bo-field-validation-20261115\web"
node scripts/check_frontend_localization.mjs
.\.venv\Scripts\python.exe tests/e2e/bo_import_validation.py --base-url http://127.0.0.1:8623 --output "$env:TEMP\DataLab-bo-field-validation-20261115\green-reviewed" --isolated-workspace
```

Python `-m ruff check` and `-m ruff format --check` targeted
`tests/e2e/bo_import_validation.py` and `tests/e2e/bo_dataset_import.py` using the
root environment. Full backend/project/security CI was not rerun for this scope.

### Local Application

Published the same tested static bytes to the existing localhost:8620 preview.
Preserved old hashed assets for already-open tabs and atomically replaced only
the entry HTML, with its previous copy retained. Initial replacement with a
cross-volume backup failed without changing the entry; same-volume replacement
then succeeded. HTTP entry and BO chunk hashes were verified against tested
files. Entry SHA-256:
`c88fc3deafab20ad05cd1ebc980206b1e932a22d46a12f54a98e1b6590739b62`.
No user browser refresh or backend restart was performed. Unsaved drafts may
reset on the user's next refresh; no user dataset/study/result was modified.
The separate synthetic server on 8623 was stopped after verification.
