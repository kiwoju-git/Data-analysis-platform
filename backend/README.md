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

Bayesian backend는 route/schema, Study lifecycle, recommendation orchestration,
consistency validation, 독립 계산, SQLite storage로 분리되어 있습니다. Frontend 모듈 구조와
P0 완료 범위는 [Bayesian P0 release checklist](../docs/bayesian_p0_release_checklist.md)를
참조하십시오. GP/Matérn/EI 계산과 persisted schema는 UI 모듈화나 route delivery 변경과
독립적으로 유지합니다.

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
Linux의 지원 대상은 Ubuntu 24.04 x86_64 / CPython 3.12이며 별도 runtime/dev
해시 lock을 사용합니다. CPython 3.11 호환성 lock과 CI도 별도입니다.
Windows 3.10 경로를 Linux lock으로 대체하지 않습니다. 설치와 배포 전제조건은
[Linux 안내](../README-linux.md)를 참조하십시오.

## Storage와 migration

현재 API와 metadata version은 [생성된 capability matrix](../docs/generated/analysis_capability_matrix.md)와
`core/runtime_contract.py`, `storage/metadata.py`의 상수로 확인합니다. 이 문서에 과거 숫자를
별도로 유지하지 않습니다. Dataset version, analysis result, DOE response
revision, Bayesian history/recommendation/lifecycle, control-limit set 등 persisted relation은
migration과 backward-compatibility test를 통해 변경합니다. 기존 stored record를 새
method/result 의미로 조용히 재해석하지 않습니다.

Workspace write는 app-owned 경로와 checksum metadata를 사용하며 가능한 곳에서 atomic
replacement와 quarantine recovery를 적용합니다. Raw user workspace나 생성 artifact를 Git에
commit하지 않습니다.

## 보안 경계

- Windows 개발 API는 loopback이고, 승인된 LAN 개발 frontend는 same-origin proxy를 통해
  `0.0.0.0:8600`으로 접속합니다. `dev.ps1 -LocalOnly`는 loopback 전용입니다.
- Linux source 개발은 기본 loopback이며 명시적 `--lan`이 필요합니다. Linux Release는
  승인된 trusted-LAN 기본 bind와 Host/Origin guard를 사용하고 `--local-only`로 제한합니다.
  어느 경로도 인증된 다중 사용자 서비스나 공개 인터넷 배포를 의미하지 않습니다.
- raw row, request body, filename, internal path, traceback을 client error/log에 노출하지 않습니다.
- 외부 pickle/joblib, arbitrary Python/shell/`eval`을 허용하지 않습니다.
- CPU-bound statistics와 scikit-learn 작업은 async event loop에서 직접 실행하지 않습니다.
- API 오류는 stable code와 `correlation_id`를 사용합니다.

통계, 개인정보, Windows 호환성 규칙은 [AGENTS.md](../AGENTS.md)와
[PRD addendum](../data_prd_addendum.md)가 우선합니다.

## Capability와 도움말 정합성

[Capability 계약](../docs/analysis_capability_contract.md)과
[생성 matrix](../docs/generated/analysis_capability_matrix.md)는 실제 method registry,
runner/route, 저장 report reader, frontend 분류를 교차 검증합니다. `scripts/check.ps1`과
`scripts/check.sh`는 오프라인으로 생성 결과가 최신인지 확인합니다. Node는 이 개발 검사에만
필요하며 backend 실행이나 설치된 Release의 Python-only 검사에 요구되지 않습니다.
정적 matrix는 실행 전 조건 검사 또는 개별 저장 결과의 `full/summary/unsupported`
report capability를 대체하지 않습니다.
