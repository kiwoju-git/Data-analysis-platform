# DataLab Studio Backend

DataLab Studio의 local-first FastAPI package입니다. 제품 설치, 실행, 사용자 튜토리얼은
[루트 README](../README.md)를 먼저 참조하십시오.

## 개발 진입점

- 애플리케이션: `backend/app/main.py`
- versioned API: `/api/v1`
- router: `backend/app/api/v1/`
- typed schema: `backend/app/api/v1/schemas/`
- service orchestration: `backend/app/services/`
- FastAPI와 독립된 계산: `backend/app/statistics/`
- SQLite/workspace storage: `backend/app/storage/`
- OpenAPI: 실행 중인 local backend의 `/docs` 또는 `/openapi.json`

API route 전체 목록은 이 문서에 복제하지 않습니다. OpenAPI와 router source가
authoritative source입니다.

## 검사

저장소 root에서 공통 검사를 실행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

Backend만 좁게 확인할 때:

```powershell
.\.venv\Scripts\python.exe -m ruff check .\backend
.\.venv\Scripts\python.exe -m ruff format --check .\backend
.\.venv\Scripts\python.exe -m mypy .\backend\app
.\.venv\Scripts\python.exe -m pytest .\backend\tests
```

Direct dependency와 Python 3.10 Windows wheel hash lock은
`backend/pyproject.toml`과 `backend/requirements-py310-win.lock`에서 관리합니다.

## Storage와 migration

현재 SQLite schema version은 `14`입니다. Dataset version, analysis result, DOE response
revision, Bayesian history/recommendation/lifecycle, control-limit set 등 persisted relation은
migration과 backward-compatibility test를 통해 변경합니다. 기존 stored record를 새
method/result 의미로 조용히 재해석하지 않습니다.

Workspace write는 app-owned 경로와 checksum metadata를 사용하며 가능한 곳에서 atomic
replacement와 quarantine recovery를 적용합니다. Raw user workspace나 생성 artifact를 Git에
commit하지 않습니다.

## 보안 경계

- 기본 bind는 `127.0.0.1`이며 core API는 local single-user용입니다.
- raw row, request body, filename, internal path, traceback을 client error/log에 노출하지 않습니다.
- 외부 pickle/joblib, arbitrary Python/shell/`eval`을 허용하지 않습니다.
- CPU-bound statistics와 scikit-learn 작업은 async event loop에서 직접 실행하지 않습니다.
- API 오류는 stable code와 `correlation_id`를 사용합니다.

통계, 개인정보, Windows 호환성 규칙은 [AGENTS.md](../AGENTS.md)와
[PRD addendum](../data_prd_addendum.md)가 우선합니다.
