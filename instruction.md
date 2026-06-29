# DataLab Studio Instruction

이 문서는 Windows PowerShell 기준 설치, 실행, 점검, 기본 사용 방법을 정리한다.

## 1. 사전 준비

- Windows 11
- Python 3.10.x
- Node.js 22 LTS 또는 Node.js 20.19 이상
- Git

관리자 권한, Docker, WSL, Redis, GPU, 외부 서비스는 기본 실행에 필요하지 않다.

## 2. 최초 설치

저장소 루트에서 PowerShell을 열고 실행한다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
```

스크립트가 하는 일:

- `.venv`가 없으면 Python 3.10 가상환경 생성
- backend와 dev dependency 설치
- frontend npm dependency 설치

수동 설치가 필요하면 아래 순서로 실행한다.

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
npm --prefix .\frontend ci
```

## 3. 개발 서버 실행

backend와 frontend를 함께 실행한다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

기본 주소:

- Frontend: `http://127.0.0.1:5173`
- Backend API: `http://127.0.0.1:8000`
- Health check: `http://127.0.0.1:8000/api/v1/health`

backend만 실행:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -BackendOnly
```

frontend만 실행:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -FrontendOnly
```

## 4. API 연결 실패 해결

브라우저에 `API 연결 필요` 또는 `Failed to fetch`가 보이면 보통 backend가 꺼져 있거나 frontend가 다른 API 주소를 보고 있는 상태다.

확인 순서:

1. `powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1`로 backend와 frontend를 함께 켠다.
2. 브라우저에서 `http://127.0.0.1:8000/api/v1/health`가 열리는지 확인한다.
3. frontend가 다른 포트에서 실행 중이면 브라우저에 표시된 Vite 주소로 접속한다.
4. `VITE_API_BASE_URL`을 지정했다면 `http://127.0.0.1:8000`인지 확인한다.
5. backend는 기본적으로 `127.0.0.1`에만 바인딩한다. `0.0.0.0` 또는 LAN 공개 실행은 기본 지원 범위가 아니다.

## 5. 기본 사용 흐름

1. 브라우저에서 frontend 주소를 연다.
2. `원본 데이터 파일`에서 CSV/TSV/TXT/XLSX 파일을 업로드하거나, `복사한 표 붙여넣기`에 Excel 범위를 붙여넣는다.
3. 앱이 제안한 encoding, delimiter, header, data start row, missing token을 확인한다.
4. `파싱 확정`을 실행해 immutable dataset version `v1`을 만든다.
5. `스키마 확인`에서 컬럼 표시명, 측정 수준, 역할, 단위를 확인하고 저장한다.
6. `미리보기`로 canonical rows 기준 데이터를 확인한다.
7. `프로파일`로 결측, 타입, date/time, 중복, memory preflight를 확인한다.
8. `분석` 화면에서 실행 가능한 메서드를 선택한다.

현재 실행 가능한 분석:

- `eda.descriptive`: 기술통계
- `eda.graphical_summary`: histogram, boxplot, Q-Q, ECDF용 chart-data 요약
- `eda.normality`: Shapiro-Wilk, Anderson-Darling, Q-Q point payload

아직 실행 불가인 메서드는 `planned` 또는 `disabled`로 표시되며, fake result를 만들지 않는다.

## 6. 샘플 데이터 테스트

예시 데이터가 `D:\codex\data\input_example` 아래에 있으면 frontend에서 직접 업로드해 테스트할 수 있다.

권장 확인 흐름:

1. 파일 업로드
2. 파싱 옵션 확인
3. 파싱 확정
4. 스키마 저장
5. 미리보기 확인
6. 프로파일 확인
7. `eda.descriptive`, `eda.graphical_summary`, `eda.normality` 순서로 실행

Excel 파일은 현재 기본 worksheet cached value를 읽는다. 수식 재계산, 병합 셀 확장, 표시 형식 복원은 아직 범위 밖이다.

## 7. 검사 명령

전체 검사:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

테스트만 실행:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1
```

backend 일부 테스트:

```powershell
.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_normality.py .\backend\tests\unit\test_api_contracts.py
```

frontend 타입/테스트:

```powershell
npm --prefix .\frontend run typecheck
npm --prefix .\frontend run test -- --run
```

## 8. 로컬 데이터 위치

runtime workspace, SQLite DB, logs, exports, cache는 Git에 넣지 않는다.

기본 workspace root는 Windows `%LOCALAPPDATA%\DataLabStudio\`이며, 개발 중에는 환경변수로 바꿀 수 있다.

```powershell
$env:DATALAB_WORKSPACE_ROOT = "D:\datalab-workspace"
```

업로드 원본은 SHA-256과 size로 보존되고, 파싱 확정 후 분석은 canonical artifact를 기준으로 실행된다.
