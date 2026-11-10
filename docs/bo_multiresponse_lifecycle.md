# BO Multiresponse Lifecycle: Stage 3c

Historical Stage3c scope/evidence follows. [Stage3d](bo_multiresponse_ui.md)
subsequently adds UI goal creation and measured-vector entry without changing
this API/storage contract. Its new verification is recorded separately.

Base/HEAD: `1db522a12a4023995d52bdcdcf750f9500c47381`.
Worktree: `feat/bo-desirability`. This follows the uncommitted Stage3a/3b
calculation foundation. The owner requested local work only: no GitHub push,
remote CI or Linux release in this stage.

## Scope And Acceptance

This stage stores real multiresponse measurements without treating a calculated
desirability score as an observation. It does not expose the internal
multiresponse recommendation worker yet. Acceptance criteria:

- Immutable response definitions with stable IDs, goals, units and importance.
- Complete measured vectors, atomic source-locked updates and idempotent replay.
- Unchanged scalar definitions, history hash inputs and trial response shape.
- Exact restore, explicit independent repeats, close, deletion and backup/restore.
- Stored historical HTML reports without fitting or replacing the source.
- Honest read-only built UI; all scalar recommendation paths reject vector owners.
- Focused red/green, existing regression, browser and full local checks.

Statistical risk: combining each response's best from different trials or
persisting a computed desirability as a measurement. Neither is done here.
Privacy: names/units/values remain local, escaped in HTML, and absent from logs.
Concurrency: existing SQLite transaction/CAS protects whole vectors and history;
identical concurrent retries must return the actually committed timestamp.
Compatibility: new schemas are dispatched, never injected into old hash inputs.
Performance: retain the existing200-trial and1..4-response product bounds;
this stage adds no GP fit or dependency and no background upload.

## Public And Stored Contract

API32 advertises `bayesian_response_vector_lifecycle` and explicitly false
`bayesian_multiresponse_recommendation`. The actual capability names are checked
against the runtime contract by tests. BO method0.8.0 is unchanged because its
public calculation policy is unchanged.

Scalar study4/history1 remains unchanged. Vector study5/history2 uses:

- `goal_type=desirability`, `observation_policy=complete_response_vector`.
- Explicit `curve_policy=derringer_suich_linear_v1` from the approved foundation.
- One to four unique response IDs; finite ordered thresholds/positive importance.
- Completed trial `response_values` with exactly those IDs and finite numbers.
- `objective_value=null` for vectors; never a geometric score or first response.
- Pending/abandoned trials have no measured vector. No missing-value imputation.

`PUT /api/v1/bayesian-studies/{study_id}/observations/batch` uses existing version,
history revision/hash and request ID fields. Invalid/mixed/incomplete vectors
reject the whole batch. Identical retries return the committed revision;
different payload under the same request ID conflicts. Concurrent saves do not
partially populate trials or append extra histories. A stale successful request
is not explained as a rollback of a committed server artifact.

Existing replicate, abandon, close and retention paths keep their owner/budget/
pending rules. Replicates get separate actual vectors, never their parent's
measurements. Vector history hashes include response IDs and actual values.
All scalar/legacy/current recommendation routes reject vector owners with
`bayesian_multiresponse_recommendation_not_enabled` before fitting.

Metadata26 is a real additive migration: nullable
`bayesian_trials.response_values_json`. Existing columns and immutable JSON
files are not rewritten. No new generic report table, job system or model
format is introduced. Raw values stay out of scalar SQL fields. Storage also
checks mode, exact keys, finiteness and replay consistency inside its transaction.

## UI And Reports

`BayesianVectorStudySnapshot` restores stored goals, units, all actual coordinates
and measured responses. It explicitly states read-only status and retains the
existing scalar creation/entry workflow. Locale/resize/reload do not submit a
measurement or fit request. Names remain user data even in English. Exact numeric
display preserves tiny values and close large measurements.

The historical `bayesian_history_revision` report reader accepts history2 only
with study5. It validates the requested hash and snapshot rather than substituting
the latest history. Renderer1.4.0 shows a separate observed-response curve for
each response, plus saved metadata/values. These are not predicted curves or
desirability scores. A history without stored recommendations has no invented
acquisition section. No source-row read, fit or model selection occurs in export.

## Implementation Map

| Boundary | Files and key functions |
| --- | --- |
| Shared response contract | New `api/v1/schemas/bayesian_desirability.py`; existing `schemas/bayesian.py` vector request/response unions |
| Lifecycle/hash validation | `services/bayesian_studies.py`: `create_bayesian_study`, `canonical_bayesian_observation_history_sha256`, `_requested_observations`, `_validate_trials`, `_validate_histories`, `require_scalar_bayesian_objective` |
| Atomic persistence | `storage/bayesian_studies.py`: `complete_bayesian_trial_batch_records`; `storage/metadata.py`: migration26 |
| Restore/report/backup | `dedicated_report_readers.py`, `dedicated_report_renderers.py`, `workspace_backup.py` |
| Read-only UI | New `BayesianVectorStudySnapshot.tsx`; existing `BayesianOptimizationWorkspace.tsx`, `useBayesianStudyDraftState.ts`, typed API/runtime contracts |
| Regression evidence | New `test_bayesian_multiresponse_lifecycle.py`, `test_bayesian_vector_storage.py`, `bayesianVectorSnapshot.test.tsx`, `tests/e2e/bo_vector_history.py`; existing contract/CI-suite tests extended |

## Current-Run Verification

Native environment: Windows10 Home19045, CPython3.10.11, Node24.17.0,
NumPy2.2.6/SciPy1.15.3/scikit-learn1.7.2, CPU only. One heavy test process at a
time; parent plus one read-only/storage review agent. Synthetic workspaces only.

- Red: vector creation failed with422 before the new objective contract.
- First focused API regression:24 passed in71.33s.
- Expanded run:35 passed/1 failed. The failure was real: backup's explicit
  schema allowlist rejected metadata26. Added26 without weakening integrity checks.
- Review identified concurrent replay returning an uncommitted timestamp. The
  response now reads the persisted revision; a barrier test compares full replies.
- Initial mypy/typecheck issues in new union handling and fixtures were fixed,
  not suppressed. Focused UI/runtime tests:7 passed; typecheck passed.
- Final focused lifecycle/storage/internal-contract run:87 passed in138.32s.
  Runtime/entrypoint/web checks:10 passed/1 existing optional-build skip.
- The first built-UI run exposed a real omitted response-schema field pair:
  `/runtime-info` rejected the new capability keys. Updated its strict DTO and
  reran the health contract test; the UI no longer enters the mismatch gate.
- Separate harness failures were retained: a run began before server readiness;
  the locale fixture reset KO on every reload; removing it exposed the app's
  current EN default. The fixture now seeds KO only when storage is empty and
  verifies the user-selected stored locale before reloading. No product locale
  policy or timeout was changed to pass the test.
- Built Vite UI/Chromium149.0.7827.55 passed API-seeded vector restore,
  KO/EN/KO,1024/1440px, exact tiny/large values, Korean user names and reload.
  Browser API writes stayed zero and the complete server study stayed equal.
  Screenshot inspection found no clipped/overlapping content in the tested
  snapshot. This is not a vector input-form or recommendation journey.
- Production build, localization2980 strings/4653 keys and frontend lint passed
  (12 existing refresh warnings). Full project results follow after execution.
- Existing scalar built-UI review context and complete BO workflow passed:
  source invalidation, committed-but-disconnected explicit retry without extra
  trials, numeric kernel choices, q1 target, joint batch, independent repeats,
  exact aggregation (raw9/effective7), observation entry, restore and managed
  HTML report download/open. Old scalar history stayed unchanged. These do not
  establish multiresponse recommendation support.
- Full-check static phases passed: tutorial18 blocks, capability AST11 tests,
  generated matrix, Ruff/format481 files and mypy253 source modules.
- The complete backend invocation collected3555:3518 passed,27 failed,10 skipped
  in3586.31s. This was **not** a green `scripts/check.ps1` run; it stopped before
  frontend phases. Failures were8 old renderer1.3 expectations,1 synthetic
  pre-migration fixture using the current reader against an unmigrated DB,
  3 startup metadata expectations,3 E2E dispatch registrations,8 migration
  ledger expectations and4 OpenAPI union/version expectations.
- Only test fixtures/expectations, E2E stage registration and docs changed after
  that full run; product code did not. Expanded recheck first passed360/failed2:
  a new JSON-schema assertion expected `additionalProperties` rather than the
  actual ID-constrained `patternProperties`, and the new E2E step marker was
  absent from its coverage ledger. Both were corrected explicitly. The final
  full affected-file rerun passed362 tests in237.34s. No test was removed,
  skipped to bypass failure or given a larger numerical tolerance.
- The migration fixture uses current code to generate legacy-v2 payloads, then
  copies only old columns into a genuine metadata24 DDL database. It verifies
  study4/history1/config2/result2/model3/item2, foreign keys, every owner/head/
  trial/batch/history column in PK order, new-column NULL and original archive
  checksum before/after migration and restore. It is not an archive generated
  by an old installed binary. A separate populated25 migration fixture also
  verifies exact old-column/JSON/hash preservation.
- All3555 backend cases were exercised; the27 failures were covered by the
  final362-test rerun. A second monolithic full run was not performed after these
  test-only corrections. Do not report the original full command as exit0.
- Full frontend single-worker run:130 files/1127 tests passed in137.11s.
  Final Ruff lint/format and `git diff --check` passed. The earlier successful
  typecheck/build/lint/browser runs used the same final frontend/product sources.
  No product source was changed after the full backend invocation started.

Local preview remains at `http://127.0.0.1:8676` on a separate synthetic workspace,
not the user's default workspace. Original checkout still contains its unchanged
untracked `examples/image2.png`. Local HEAD/recorded origin/main remain the base
SHA above; no new commit, push, remote CI or release has been created.

No actual JMP output comparison. No Linux3.11/3.12, Windows11 specifically,
installed archive, remote CI or new dependency-security advisory audit is claimed
from these Windows source tests. Prior-stage runs are not current-run evidence.

## Reproduction And Rollback

```powershell
$env:PYTHONPATH = Join-Path $PWD 'backend'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bayesian_multiresponse_lifecycle.py backend/tests/unit/test_bayesian_vector_storage.py backend/tests/unit/test_bo_desirability_contract.py -q
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

Built-UI probe: `tests/e2e/bo_vector_history.py --base-url <isolated-loopback-url>
--output <external-synthetic-diagnostics-dir>`. It is also connected to the
existing context suite. It API-seeds vectors and tests real UI restoration,
not UI entry or recommendation confirmation.

No new published commit exists to revert yet. After eventual commits, revert only
these stages' commits in reverse order. API/frontend/backend must move together.
Older code rejects metadata26 and cannot read vector history2; code revert does
not downgrade a DB. Keep an offline backup made before upgrade and restore it to
a new empty path for old-code use. Never delete the current workspace or rewrite
its schema number; vectors created after that backup will not exist in it.
