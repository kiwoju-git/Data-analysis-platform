# DataLab Studio To-Do List

Last updated: 2026-06-22

## 1. Project Understanding

DataLab Studio는 Windows 11, PowerShell, Python 3.10.x, CPU-only 환경을 1급 지원하는 local-first 단일 사용자 통계 분석 웹 애플리케이션이다. 핵심 기술 결정은 FastAPI backend, React + Vite + TypeScript frontend, SQLite metadata, local workspace files, scikit-learn 기반 ML이다.

제품의 우선순위는 기능 수가 아니라 통계적 타당성, 재현성, 데이터 보호, 실패 시 안전성이다. 따라서 넓은 기능을 한 번에 구현하지 않고 `data_prd_addendum.md`의 Gate A, B, C, D 순서로 작은 수직 슬라이스를 완성한다.

현재 저장소 상태:

- [x] `AGENTS.md` 확인 완료
- [x] `data_prd_addendum.md` 확인 완료
- [x] 루트에 `data_prd.md` 없음 확인
- [x] 기존 backend/frontend 코드 없음 확인
- [x] 현재 디렉터리는 Git repository가 아님 확인
- [x] 구현 시작 게이트는 Gate A로 확정

고정 제약:

- 기본 bind address는 `127.0.0.1`
- core flow에서 외부 업로드, analytics, CDN, remote font, telemetry 금지
- Docker, WSL, Redis, 관리자 권한, GPU는 필수 요구사항이 아님
- 사용자 Python, shell command, `eval`, pickle/joblib upload loading 금지
- 원본 데이터는 불변 보존하고 SHA-256 provenance를 기록
- 통계 결과는 N, 제외 사유, assumptions, warnings, estimate, CI, effect size, p-value, provenance를 포함
- 한국어 UI를 기본으로 하되 API code, schema field, requirement ID는 영어 안정값 유지

## 2. Working Rule Checklist

모든 step 시작 전에 확인:

- [ ] 관련 요구사항, 기존 코드, 테스트, migration, instruction file 확인
- [ ] acceptance criteria 작성
- [ ] statistical, privacy, compatibility, migration, performance risk 확인
- [ ] 가장 작은 end-to-end change로 범위 제한
- [ ] 같은 변경에 테스트 추가 또는 갱신
- [ ] narrow check 먼저 실행 후 가능한 full check 실행
- [ ] API schema, docs, fixtures, migration, manifest version 변경 필요 여부 확인
- [ ] 실행한 명령과 실제 결과만 progress에 기록

절대 금지:

- [ ] 실행하지 않은 테스트를 passed로 기록
- [ ] fabricated statistical values 사용
- [ ] raw user data, secrets, generated workspaces, model artifacts를 Git에 저장
- [ ] broad exception handler로 실패 은폐
- [ ] silent sampling, coercion, row dropping, hypothesis/method switching
- [ ] unrelated rewrite 또는 전체 저장소 reformat

## 3. Gate Roadmap

### Gate A: Foundation

Exit criterion: 새 Windows 환경에서 문서화된 명령으로 설치하고 backend health와 frontend UI smoke test가 통과한다.

- [x] A1. Monorepo scaffold
  - [x] `backend/`, `frontend/`, `scripts/`, `docs/`, `.github/workflows/` 생성
  - [x] Python 3.10 compatible backend package metadata 작성
  - [x] React + Vite + TypeScript strict frontend scaffold 작성
  - [x] generated data/workspace/log/export directory가 repository 밖에 위치하도록 설계
- [x] A2. PowerShell workflow
  - [x] `scripts/bootstrap.ps1`
  - [x] `scripts/dev.ps1`
  - [x] `scripts/test.ps1`
  - [x] `scripts/check.ps1`
  - [x] 문서에는 `py -3.10`과 `.\.venv\Scripts\python.exe` 기준 명령만 사용
- [x] A3. Backend base
  - [x] FastAPI app 생성
  - [x] `/` 안내 route 구현
  - [x] `/api/v1/health` 구현
  - [x] 기본 bind address `127.0.0.1` 유지
  - [x] typed error response와 `correlation_id` 기본 구조 추가
  - [x] request body, raw records, absolute paths가 log/error에 노출되지 않도록 기본 logger 구성
- [x] A4. Storage and migration skeleton
  - [x] SQLite metadata initialization
  - [x] migration version table 또는 migration framework 결정 및 기록
  - [x] workspace root는 환경변수로 override 가능
  - [x] atomic write helper 방향 확정
- [x] A5. Shared API contracts
  - [x] dataset/job/result ID model 기본 정의
  - [x] job states: `queued`, `running`, `succeeded`, `failed`, `cancel_requested`, `cancelled`
  - [x] stable error code structure 정의
- [x] A6. Frontend base
  - [x] Korean-first app shell
  - [x] health status smoke UI
  - [x] no CDN, no remote font, no telemetry
  - [x] accessible labels and keyboard-friendly base navigation
- [x] A7. Quality gates
  - [x] backend ruff, format check, mypy, pytest wiring
  - [x] frontend lint, typecheck, test, build wiring
  - [x] Windows CI with Python 3.10
  - [x] smoke test for health/UI

### Gate B: Statistical MVP

Exit criterion: 기준 데이터셋에서 독립 참조 결과와 허용오차 내 일치하고, 분석 매니페스트로 재실행이 가능하다.

- [ ] B1. Safe upload and parsing
  - [ ] CSV, TSV, XLSX upload
  - [ ] actual file type, size, parser limits, decompression ratio validation
  - [ ] UTF-8, UTF-8-SIG, CP949 support
  - [ ] delimiter, quote, decimal/thousands, header row options
  - [ ] raw file preservation with SHA-256
- [ ] B2. Schema confirmation
  - [ ] numeric/categorical/string/boolean/datetime/ID candidate inference
  - [ ] duplicate/empty column handling with original-name mapping
  - [ ] missing token policy confirmation
  - [ ] no type decision based only on pandas dtype
- [ ] B3. Dataset versions and lineage
  - [ ] immutable dataset version records
  - [ ] transformation records with parent ID, parameters, affected rows, created time
  - [ ] stale result marking when source version changes
- [ ] B4. Profile and preview
  - [ ] row/column counts, missing rates, unique counts, range, quantiles, duplicate rows, memory estimate
  - [ ] paginated row API
  - [ ] frontend virtualization, no full dataset in browser state
- [ ] B5. Core preprocessing
  - [ ] explicit complete-case default for inferential analyses
  - [ ] destructive transformation preview and confirmation
  - [ ] no Python `eval`; whitelist parser only when formula support is added
- [ ] B6. Core statistics
  - [ ] descriptive statistics with denominator and sample SD definition
  - [ ] Welch default for independent two-group mean comparison
  - [ ] paired test with subject/pair validation
  - [ ] ANOVA/Welch ANOVA with compatible post-hoc direction
  - [ ] nonparametric tests without overclaiming median difference
  - [ ] chi-square expected cell checks and Fisher exact for sparse 2x2 where appropriate
  - [ ] Pearson/Spearman/Kendall correlation with N, CI, multiplicity
- [ ] B7. Result contract
  - [ ] method, rationale, assumptions, warnings
  - [ ] `n_total`, `n_used`, exclusions, group sizes
  - [ ] estimate, 95% CI, statistic, df where applicable
  - [ ] raw p-value and adjusted p-value where applicable
  - [ ] effect size and CI when mathematically supported
  - [ ] provenance manifest with versions, seed, dataset hash/version
- [ ] B8. Exports
  - [ ] CSV/JSON result export
  - [ ] reproducible Python code export
  - [ ] HTML report P0
  - [ ] CSV formula injection defense for strings beginning with `=`, `+`, `-`, `@`

### Gate C: Regression and ML

Exit criterion: leakage prevention tests and holdout reevaluation pass, and same seed reproduces the result.

- [ ] C1. Regression diagnostics
  - [ ] linear regression residual, heteroscedasticity, multicollinearity, influence checks
  - [ ] logistic regression separation, convergence, calibration, event count warnings
- [ ] C2. Leakage-safe sklearn pipelines
  - [ ] preprocessing and model as `Pipeline`/`ColumnTransformer`
  - [ ] imputer, encoder, scaler, feature selection fit inside training fold only
  - [ ] ordinary, stratified, group-aware, and time-aware split support as needed
- [ ] C3. Baseline model evaluation
  - [ ] classification metrics beyond accuracy
  - [ ] regression MAE, RMSE, R2
  - [ ] MAPE warning or disable when target has zero/near-zero values
  - [ ] holdout or nested CV for tuned evaluation
- [ ] C4. Model artifacts
  - [ ] model card with data version, target, features, split, metrics, package versions
  - [ ] schema validation for prediction data
  - [ ] only app-created artifacts loaded with manifest version and hash
  - [ ] no external pickle/joblib upload deserialization

### Gate D: Advanced Features

Exit criterion: each advanced feature has explicit approval, compatibility tests, and does not weaken Gates A-C.

- [ ] D1. Hyperparameter tuning with explicit time/trial/fold/memory/failure budgets
- [ ] D2. Limited model explanation with non-causal warnings
- [ ] D3. PDF report generation through Windows-compatible verified path
- [ ] D4. Repeated-measures ANOVA with subject ID, sphericity, correction, incomplete observation warnings
- [ ] D5. Power/sample-size tools with assumption and effect-size definition warnings

## 4. Risk Register

Review this section before and after each implementation step.

| Risk area | Current risk | Required mitigation | Status |
| --- | --- | --- | --- |
| Statistical correctness | Test selection or result interpretation may overclaim from dtype or p-value alone. | Require design metadata, assumptions, N/exclusions, CI, effect size, warnings, provenance. | Open |
| Privacy/security | Uploaded cell values, file names, paths, or raw request bodies may leak into logs/errors/UI HTML. | Redacted structured logs, sanitized errors, text rendering, no telemetry, no external calls. | Open |
| Compatibility | Code may accidentally assume POSIX, Python 3.11+, GPU, Docker, admin rights, or network runtime. | PowerShell docs, Python 3.10 metadata, pathlib, Windows CI, CPU-only deps. | Open |
| Migration/storage | SQLite schema and workspace files may drift or corrupt on crash. | Versioned migrations, atomic writes, startup recovery checks, no repository data storage. | Open |
| Performance/reliability | Large files may exhaust memory or block the API event loop. | Upload limits, memory preflight, worker process abstraction, pagination, virtualization. | Open |
| Dependency/license | A dependency may be GPL/commercial/evaluation-only or too heavy. | Record dependency review before adding production dependency. | Open |

## 5. Validation Commands

Use these once the corresponding project pieces exist. Record only commands actually run in the progress log.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

Expected full check after scaffolding:

```powershell
.\.venv\Scripts\python.exe -m ruff check .\backend
.\.venv\Scripts\python.exe -m ruff format --check .\backend
.\.venv\Scripts\python.exe -m mypy .\backend\app
.\.venv\Scripts\python.exe -m pytest .\backend\tests
npm --prefix .\frontend run lint
npm --prefix .\frontend run typecheck
npm --prefix .\frontend run test -- --run
npm --prefix .\frontend run build
```

## 6. Progress Log

### 2026-06-22, Phase 0, Step 0.1: Requirements grounding

Status: completed

Changed files:

- `to_do_list.md`

Requirements reviewed:

- `AGENTS.md`
- `data_prd_addendum.md`

Acceptance criteria:

- [x] Project constraints summarized
- [x] Gate A-D checklist created
- [x] Step/Phase progress format created
- [x] Risk register created
- [x] Validation command section created

Risks reviewed:

- Statistical: no statistical code added; future gates must enforce result contract and tests.
- Privacy/security: no user data added; future gates must keep workspace data outside the repository.
- Compatibility: official commands documented as PowerShell; no platform-specific code added.
- Migration: no SQLite schema yet; Gate A must introduce migration skeleton.
- Performance: no runtime behavior yet; Gate B must add upload limits and memory preflight.

Commands run:

- `rg --files -g 'AGENTS.md' -g 'AGENTS.override.md' -g 'data_prd_addendum.md' -g 'data_prd.md' -g 'to_do_list.md'`
- `find . -maxdepth 2 -type f | sort`
- `git status --short`

Result:

- Existing files found: `AGENTS.md`, `data_prd_addendum.md`
- `data_prd.md` was not present
- No backend/frontend implementation exists yet
- `git status --short` failed because `/mnt/d/codex/data` is not currently a Git repository

Known limitations:

- No project scripts or test suites exist yet, so product checks cannot run until Gate A scaffolding is implemented.
- The original `data_prd.md` is absent; current planning follows `AGENTS.md` and `data_prd_addendum.md`.

### 2026-06-22, Phase 1, Step 1.1: Gate A initial scaffold

Status: completed

Changed files:

- `.gitignore`
- `.github/workflows/ci.yml`
- `backend/README.md`
- `backend/pyproject.toml`
- `backend/app/**`
- `backend/tests/unit/test_health.py`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/eslint.config.js`
- `frontend/index.html`
- `frontend/src/**`
- `frontend/tsconfig.json`
- `frontend/vite.config.ts`
- `scripts/bootstrap.ps1`
- `scripts/check.ps1`
- `scripts/dev.ps1`
- `scripts/test.ps1`
- `docs/dependency_review.md`
- `docs/setup.md`
- `to_do_list.md`

Requirements reviewed:

- `AGENTS.md` sections 2, 3, 4, 5, 6, 10, 11, 12, 13, 15, 16
- `data_prd_addendum.md` DEC-001, DEC-002, DEC-003, DEC-004, DEC-005, DEC-012, SEC-001, SEC-002, Gate A

Acceptance criteria:

- [x] Monorepo scaffold exists for backend, frontend, scripts, docs, and CI
- [x] Backend exposes `/api/v1/health`
- [x] Backend settings default to `127.0.0.1`
- [x] Backend has stable error response structure with `correlation_id`
- [x] Frontend renders a Korean-first local app shell and health status area
- [x] Direct dependencies are pinned and frontend lockfile is generated
- [x] Minimal backend and frontend smoke tests exist
- [x] `to_do_list.md` progress and Gate A checklist are updated

Risks reviewed:

- Statistical: no statistical calculation added; future Gate B must implement full statistical result contract before analysis features.
- Privacy/security: no raw data handling added; local runtime data is ignored and default workspace root is outside the repository on Windows.
- Compatibility: Python metadata is constrained to Python 3.10; frontend uses Node-compatible pinned dependencies; official commands are documented for PowerShell.
- Migration: SQLite migration skeleton is still open and remains the next Gate A backend task.
- Performance: no heavy CPU/data path added; future upload/profile work must add memory preflight and workers before large-data handling.

Commands run:

- `python --version`
- `python3 --version`
- `cmd.exe /c py -3.10 --version`
- `powershell.exe -NoProfile -Command "py -3.10 --version"`
- `npm --prefix ./frontend install --package-lock-only --ignore-scripts`
- `npm --prefix ./frontend audit --json`
- `npm --prefix ./frontend view @vitejs/plugin-react version peerDependencies engines license --json`
- `npm --prefix ./frontend view @vitejs/plugin-react@6.0.2 peerDependenciesMeta --json`
- `npm --prefix ./frontend view vite@8.0.16 version engines license --json`
- `cmd.exe /c py -3.10 -m venv .venv`
- `cmd.exe /c py -3.10 -m pip --python .venv install --upgrade pip`
- `cmd.exe /c py -3.10 -m pip --python .venv install -e ".\backend[dev]"`
- `npm --prefix ./frontend ci`
- `npm --prefix ./frontend run lint`
- `npm --prefix ./frontend run typecheck`
- `npm --prefix ./frontend run test -- --run`
- `npm --prefix ./frontend run build`
- `npm --prefix ./frontend audit --audit-level=low`
- Restarted backend dev server on `http://127.0.0.1:8000`
- Restarted frontend dev server on `http://127.0.0.1:5173/`
- Verified `http://127.0.0.1:8000/` with Windows Python `urllib`
- Verified `http://127.0.0.1:8000/api/v1/health` with Windows Python `urllib`
- Verified `http://127.0.0.1:5173/` with Windows Python `urllib`
- Backend dev server start through `py -3.10 -c` because PowerShell wrapper could not run in this WSL session
- `npm --prefix ./frontend run dev -- --host 127.0.0.1`
- `curl -sS http://127.0.0.1:8000/api/v1/health`
- `curl -sS http://127.0.0.1:5173/`
- `cmd.exe /c curl.exe -sS http://127.0.0.1:8000/api/v1/health`
- `cmd.exe /c curl.exe -sS http://127.0.0.1:5173/`
- Backend ruff/mypy/pytest equivalents through `py -3.10 -c` because direct `.venv\Scripts\*.exe` execution failed under the current WSL interop session.

Result:

- `py -3.10`: Python 3.10.11
- `python3`: Python 3.12.3, not used for project validation
- `python`: failed due broken Windows pyenv shim in WSL path
- Frontend lockfile generated with 0 npm audit vulnerabilities after upgrading Vite/plugin/Vitest/ESLint pins
- Backend install completed in `.venv`
- Backend ruff check: passed
- Backend ruff format check: passed
- Backend mypy: passed, 9 source files
- Backend pytest: passed, 2 tests
- Frontend lint: passed
- Frontend typecheck: passed
- Frontend Vitest: passed, 1 test
- Frontend build: passed
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1` could not run in this WSL session due `UtilBindVsockAnyPort` socket failure before script execution
- Backend dev server started and logged `Uvicorn running on http://127.0.0.1:8000`
- Frontend dev server started and logged `Local: http://127.0.0.1:5173/`
- WSL `curl` could not connect to the Windows-hosted loopback servers from this shell
- Windows `curl.exe` verification could not run because the same WSL interop socket failure occurred

Known limitations:

- Gate A is not complete until SQLite metadata initialization, migration versioning, shared dataset/job/result ID models, and job state contracts are added.
- Official PowerShell wrapper scripts were created but not fully executed because this WSL session cannot currently launch `powershell.exe`; individual equivalent checks were run instead.
- Dev servers are currently running in this session for manual browser testing: backend `http://127.0.0.1:8000`, frontend `http://127.0.0.1:5173/`.

### 2026-06-22, Phase 1, Step 1.2: Local sample input note

Status: completed

Changed files:

- `.gitignore`
- `to_do_list.md`

Requirements reviewed:

- `AGENTS.md` section 10: Data security and privacy rules
- `data_prd_addendum.md` SEC-007, SEC-009, Gate B upload/profile flow

Acceptance criteria:

- [x] Local sample data location noted without reading or copying raw contents
- [x] `input_example/` added to `.gitignore` so user-provided data is not tracked
- [x] Future manual flow identified: upload input data, confirm schema, preview/profile, then analysis

Risks reviewed:

- Statistical: Bayesian/optimization-oriented sample data is not analyzed yet; future analysis method must be explicitly specified and validated.
- Privacy/security: raw sample data contents were not read, logged, copied, or committed.
- Compatibility: local path is Windows workspace-local; product code must not hardcode this path.
- Migration: no metadata/schema change in this step.
- Performance: file size listing only; future upload flow must enforce size and memory preflight.

Commands run:

- `find input_example -maxdepth 3 -type f -printf '%p\t%s bytes\n' | sort`
- `rg -n "input_example|Gate A|Gate B|Phase 1|A4|A5|B1" to_do_list.md .gitignore`

Result:

- Found one local sample file under `input_example/`
- No raw data contents were inspected

Known limitations:

- The application cannot upload or preview this file yet; Gate B safe upload and preview APIs are not implemented.

### 2026-06-22, Phase 1, Step 1.3: Root route, metadata store, and common contracts

Status: completed

Changed files:

- `.env.example`
- `backend/app/api/root.py`
- `backend/app/api/v1/schemas/common.py`
- `backend/app/main.py`
- `backend/app/storage/metadata.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_app_startup.py`
- `backend/tests/unit/test_health.py`
- `backend/tests/unit/test_metadata_store.py`
- `docs/setup.md`
- `docs/storage.md`
- `to_do_list.md`

Requirements reviewed:

- `AGENTS.md` sections 5, 6, 10, 13, 15, 16
- `data_prd_addendum.md` DEC-001, DEC-002, DEC-005, DEC-012, SEC-001, SEC-007, SEC-009, Gate A

Acceptance criteria:

- [x] `GET /` returns safe API entrypoint links instead of a 404
- [x] SQLite metadata store initializes under the configured workspace root
- [x] `schema_migrations` records the current migration version
- [x] `PRAGMA user_version` records the current schema version
- [x] Startup initializes metadata storage through FastAPI lifespan
- [x] Common dataset/analysis/model/report/result/job ID aliases exist
- [x] Job state values are fixed to the PRD contract
- [x] Tests cover root response, startup storage initialization, migration idempotency, Unicode/space paths, and job state serialization

Risks reviewed:

- Statistical: no statistical method or result calculation added in this step.
- Privacy/security: metadata DB path is under local workspace, not Git; `.env.example` contains only non-secret names/defaults.
- Compatibility: storage uses `pathlib` and stdlib `sqlite3`; tests include a path with spaces and Korean characters.
- Migration: migration table and `user_version` are established; future schema changes still need forward migration tests from previous schema.
- Performance: startup creates only a small metadata DB and does not load datasets or block on heavy work.

Commands run:

- Stopped existing backend/frontend dev sessions before edits
- `rg --files backend frontend scripts docs | sort`
- `sed -n '1,220p' backend/app/main.py`
- `sed -n '1,220p' backend/app/core/config.py`
- `sed -n '1,220p' backend/tests/unit/test_health.py`
- Backend ruff check equivalent through `py -3.10 -c`
- Backend ruff format check equivalent through `py -3.10 -c`
- Backend mypy equivalent through `py -3.10 -c`
- Backend pytest equivalent through `py -3.10 -c`
- `npm --prefix ./frontend run lint`
- `npm --prefix ./frontend run typecheck`
- `npm --prefix ./frontend run test -- --run`
- `npm --prefix ./frontend run build`
- `npm --prefix ./frontend audit --audit-level=low`

Result:

- Backend ruff check: passed
- Backend ruff format check: passed
- Backend mypy: passed, 14 source files
- Backend pytest: passed, 8 tests
- Frontend lint: passed
- Frontend typecheck: passed
- Frontend Vitest: passed, 1 test
- Frontend build: passed
- npm audit: 0 vulnerabilities
- `GET /`: returned safe service/version/API link JSON
- `GET /api/v1/health`: returned `ready`
- Frontend dev server: returned Korean HTML shell entrypoint

Known limitations:

- A4 is still not fully complete because the reusable atomic write helper has not been implemented.
- Official PowerShell wrapper scripts still were not re-run in this WSL session because of the earlier `powershell.exe` interop socket failure.
- Upload, preview, profile, and analysis flows are not implemented yet.
- Dev servers are currently running for manual testing: backend `http://127.0.0.1:8000`, frontend `http://127.0.0.1:5173/`.

### 2026-06-23, Phase 1, Step 1.4: Atomic writes and Gate A progress document

Status: completed

Changed files:

- `backend/app/storage/atomic.py`
- `backend/tests/unit/test_atomic.py`
- `docs/storage.md`
- `docs/progress_gate_a.md`
- `to_do_list.md`

Requirements reviewed:

- `AGENTS.md` sections 5, 6, 10, 13, 15, 16
- `data_prd_addendum.md` DEC-005, section 8.2 recovery requirements, SEC-007, SEC-009, Gate A

Acceptance criteria:

- [x] Atomic helper writes temporary files in the same target directory
- [x] Atomic helper replaces targets using `os.replace`
- [x] Atomic helper flushes and fsyncs file content before replacement
- [x] Atomic helper preserves the old target and removes temp files when writing fails
- [x] Tests cover replacement, failure cleanup, and paths with spaces/Korean characters
- [x] Storage docs identify when to use and not use the helper
- [x] Gate A progress document exists and summarizes completed work, validation, risks, and Gate B entry

Risks reviewed:

- Statistical: no statistical calculation added.
- Privacy/security: no user data read; helper is for app-owned artifacts and does not log file contents.
- Compatibility: uses `pathlib`, stdlib `tempfile`, and `os.replace`; tests include Windows-relevant path names.
- Migration: atomic helper supports future crash-safe metadata-adjacent artifact writes; SQLite migration logic unchanged.
- Performance: helper is intended for small manifests/results, not streaming large uploaded datasets.

Commands run:

- `rg -n "A4|atomic|Step 1.3|Gate A|Progress" to_do_list.md docs backend/app backend/tests`
- `rg --files backend/app backend/tests docs scripts | sort`
- `sed -n '1,240p' backend/app/storage/metadata.py`
- `sed -n '1,240p' docs/storage.md`
- `sed -n '50,120p' to_do_list.md`
- `sed -n '410,520p' to_do_list.md`
- Backend ruff check equivalent through `py -3.10 -c`
- Backend ruff format check equivalent through `py -3.10 -c`
- Backend mypy equivalent through `py -3.10 -c`
- Backend atomic pytest equivalent through `py -3.10 -c`

Result:

- Backend ruff check: passed
- Backend ruff format check: passed
- Backend mypy: passed, 15 source files
- Backend atomic tests: passed, 4 tests

Additional Gate A validation after progress document update:

- Backend ruff check: passed
- Backend ruff format check: passed
- Backend mypy: passed, 15 source files
- Backend pytest: passed, 12 tests
- Frontend lint: passed
- Frontend typecheck: passed
- Frontend Vitest: passed, 1 test
- Frontend build: passed
- npm audit: 0 vulnerabilities

Known limitations:

- Official PowerShell wrapper scripts still need validation in a normal Windows PowerShell session.
- Gate B upload, preview, profile, and analysis flows are not implemented yet.

## 7. Progress Entry Template

Copy this template at the end of section 6 after each completed step.

```markdown
### YYYY-MM-DD, Phase X, Step X.Y: Short title

Status: completed | blocked | superseded

Changed files:

- `path/to/file`

Requirements reviewed:

- `REQ-ID` or document section

Acceptance criteria:

- [ ] Criterion 1
- [ ] Criterion 2

Risks reviewed:

- Statistical:
- Privacy/security:
- Compatibility:
- Migration:
- Performance:

Commands run:

- `command`

Result:

- Actual result only

Known limitations:

- Limitation or `None`
```
