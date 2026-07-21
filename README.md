# DataLab Studio

DataLab Studio is a Windows-targeted, CPU-only, local-first statistical analysis web application.

데이터 업로드와 파싱 확인부터 통계 분석, 회귀 예측, 품질 관리, DOE, 결과 복원과
내보내기까지 한 PC 안에서 수행하는 FastAPI + React 애플리케이션입니다.

## 현재 상태

현재 저장소는 **internal alpha / release candidate 이전 단계**입니다. 핵심 workflow와
synthetic critical-path 검증은 구현되어 있지만, clean Windows 11/Python 3.10/Node 22
release gate와 최신 remote GitHub Actions 상태는 아직 별도 확인 대상입니다. 확인된
개발 검증과 미확인 release evidence는 [CI 상태](docs/ci_status.md)에 구분해 기록합니다.

## 주요 기능

- 탐색적 분석, 가설 검정, 범주형 데이터 분석
- 상관관계, 선형 회귀, 저장 모형 기반 Predict, Response Optimizer
- Run/Individuals/Subgroup Chart, Capability, Gage R&R, P/NP/C/U 관리도
- Factorial DOE, RSM, Bayesian Optimization study/관측/추천 lifecycle
- immutable dataset version, 분석 저장/복원/비교, checksum 검증
- 저장된 dataset version을 다시 활성화하는 paged 상단 selector
- generic JSON/CSV/HTML export와 Report Center
- Excel 범위용 view-only paste staging grid와 paged canonical preview
- 한국어 Help Center, method context help, end-to-end 튜토리얼

Bayesian 지원 범위는 bounded continuous, single-objective, sequential P0입니다. 실제
목적함수를 자동 실행하지 않으며 추천은 확인 실험 후보입니다. multiobjective/batch,
categorical/integer factor, nonlinear constraint와 전역 최적 보장은 현재 범위가 아닙니다.
상세 상태는 [Bayesian P0 release checklist](docs/bayesian_p0_release_checklist.md)에 있습니다.

## 지원 환경

- Windows 11 target
- PowerShell
- CPython 3.10.x
- Node.js 22 target
- CPU-only
- `127.0.0.1` localhost single-user 실행

Docker, WSL, Redis, 관리자 권한, GPU 또는 외부 서비스는 core flow에 필요하지 않습니다.

## 설치

```powershell
git clone https://github.com/kiwoju-git/Data-analysis-platform.git
cd Data-analysis-platform
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
```

의존성을 설치한 뒤에는 core runtime이 외부 데이터 전송 없이 동작하도록 설계되어
있습니다. Python 3.10 Windows 환경은 hash-locked wheel 설치 경로를 사용합니다.

## 실행

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

브라우저 주소는 Vite와 backend가 출력하는 localhost 주소를 사용합니다. 이미 사용 중인
포트가 있으면 실행 로그를 확인해 충돌을 해소하십시오. LAN 공개용 bind 주소로 바꾸는
것은 지원되는 shortcut이 아닙니다.

## 첫 사용 흐름

1. `데이터셋`에서 CSV/TSV/TXT/XLSX 파일을 올리거나 Excel 범위를 붙여넣습니다.
2. browser preview를 검토한 뒤 server parsing suggestion을 확인하고 파싱을 확정합니다.
3. schema에서 measurement level, 역할, 단위를 지정합니다.
4. `분석`에서 module과 method를 선택하고 사전점검 후 실행합니다.
5. 저장 결과를 복원·비교하거나 `리포트`에서 지원 형식으로 내보냅니다.

새 prediction target을 등록한 뒤 training data로 돌아갈 때는 상단
`현재 분석 데이터셋` selector를 사용합니다. 전환은 실행 전 입력과 화면 결과를 초기화하지만
저장된 분석·모델·예측 결과를 삭제하지 않습니다. 선형 회귀 결과의 Observed vs Fitted,
Residuals vs Fitted, Leverage vs Cook's D 점은 마우스와 키보드로 값을 확인할 수 있습니다.

처음 사용하는 경우 앱의 `도움말`과
[한국어 end-to-end 튜토리얼](docs/studio_end_to_end_tutorial_ko.md)을 먼저 확인하십시오.

## 튜토리얼과 Sample Data

- [한국어 Studio 튜토리얼](docs/studio_end_to_end_tutorial_ko.md)
- [Synthetic tutorial data 안내](examples/tutorial/README.md)
- 주요 파일: 240행 training CSV, 60행 paste TSV, 48행 prediction target,
  invalid prediction target, Gage R&R, Factorial, RSM, Bayesian observation samples
- 기대 결과: [tutorial_expected_results.json](examples/tutorial/tutorial_expected_results.json)

실제 local API와 expected result 18개 section을 비교합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\tutorial_smoke.ps1
```

Sample은 고정 seed로 생성한 완전한 synthetic data이며 실제 개인정보나 회사 데이터를
포함하지 않습니다.

## 검사 명령

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\tutorial_smoke.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-diagnostics
```

`check.ps1`은 Ruff, format, mypy, backend pytest, frontend lint/typecheck/Vitest/build,
tutorial Markdown truth check를 실행합니다. Chromium 설치가 필요하면
`scripts\e2e.ps1 -InstallBrowsers`를 먼저 실행합니다.

## 개인정보와 보안

- 기본 bind는 `127.0.0.1`이며 외부 데이터 upload나 telemetry가 core flow에 없습니다.
- raw row, clipboard content, filename, internal absolute path를 log/telemetry에 기록하지 않습니다.
- app-created safe JSON artifact만 검증하며 외부 pickle/joblib을 역직렬화하지 않습니다.
- pasted formula-like text를 실행하지 않고 HTML clipboard를 렌더링하지 않습니다.
- user Python, shell, `eval` 실행을 제공하지 않습니다.
- workspace와 생성 artifact는 Git 저장소 밖의 configured local workspace에 둡니다.

자세한 기준은 [AGENTS.md](AGENTS.md)와
[PRD addendum](data_prd_addendum.md)을 참조하십시오.

## 리포트 지원 범위

| Workflow | JSON | CSV | HTML |
| --- | --- | --- | --- |
| Generic analysis run | 지원 | 지원 | 지원 |
| Regression Predict | stored result 복원 | full prediction CSV | 현재 미지원 |
| Response Optimizer / RSM | stored result 복원 | 현재 미지원 | 현재 미지원 |
| Factorial DOE | design/result workflow | 별도 결과 경로 | design HTML 지원 |
| Bayesian Optimization | study/recommendation 복원 | 현재 미지원 | 현재 미지원 |

PDF와 Word export는 현재 지원하지 않습니다. 상세 capability는
[Report Center 계약](docs/report_center_contract.md)에 있습니다.

## 프로젝트 구조

```text
backend/              FastAPI, domain/service/statistics/storage, pytest
frontend/             React + Vite + TypeScript UI와 Vitest
scripts/              bootstrap, dev, check, tutorial smoke, E2E 진입점
docs/                 method/lifecycle/보안/진행 계약과 사용자 문서
examples/tutorial/    deterministic synthetic tutorial pack
tests/e2e/            Chromium critical path
```

## 주요 문서

- [작업 규칙](AGENTS.md)
- [6-module 구현 가이드](docs/six_module_implementation_guide.md)
- [제품 보완 요구사항](data_prd_addendum.md)
- [Gate B 진행 상태](docs/progress_gate_b.md)
- [CI와 validation 상태](docs/ci_status.md)
- [Frontend module loading](docs/frontend_module_loading.md)
- [Bayesian Optimization 계약](docs/bayesian_optimization_contract.md)
- [Bayesian lifecycle 계약](docs/bayesian_study_lifecycle_contract.md)
- [Bayesian P0 release checklist](docs/bayesian_p0_release_checklist.md)
- [Bayesian catalog 성능](docs/bayesian_catalog_performance.md)
- [Report Center 계약](docs/report_center_contract.md)
- [한국어 튜토리얼](docs/studio_end_to_end_tutorial_ko.md)

## 알려진 제한사항

- Paste grid는 registration 전 view-only이며 cell edit/full Excel editor가 아닙니다.
- 일부 dedicated workflow는 HTML report를 아직 지원하지 않습니다.
- PDF/Word, chart image export는 지원하지 않습니다.
- Clean Windows 11/Python 3.10/Node 22 release evidence와 remote required checks는
  [CI 상태](docs/ci_status.md)에 따라 별도 gate로 남아 있습니다.
- WECO/Nelson, Laney, non-normal capability 등 advanced quality 기능은 backlog입니다.
- Bayesian multiobjective, batch recommendation, categorical/integer factor, nonlinear
  constraint와 objective 자동 실행은 현재 P0 범위가 아닙니다.

## 라이선스

이 저장소에는 현재 별도 `LICENSE` 파일이 없습니다. 배포·재사용 조건을 임의의
오픈소스 라이선스로 해석하지 마십시오.
