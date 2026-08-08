# Statistical Twin

Statistical Twin은 Windows에서 로컬로 실행하는 통계 분석 웹 애플리케이션입니다.
데이터 등록과 품질 확인, 통계 분석, 회귀, 품질 관리, 실험계획법, 그래프 작성과
보고서 내보내기를 한 작업공간에서 수행합니다. 기본 실행은 `127.0.0.1`에만
바인딩되며 core workflow는 데이터를 외부 서비스로 전송하지 않습니다.

## 주요 기능

- CSV, TSV, TXT, XLSX 및 표 붙여넣기 등록
- 파싱 확인, 스키마·측정 수준·역할 설정, 데이터 품질 점검
- 탐색적 분석, 가설 검정, 범주형 분석, 상관·회귀, 품질 관리, 실험계획법
- 변수 선택형 그래프, 저장 결과 복원·비교, HTML/CSV/JSON 내보내기
- 데이터셋, 분석 결과, 모델, DOE 설계와 Bayesian Study의 로컬 자산 관리

## 필요 환경

- Windows 11
- PowerShell 5.1
- CPython 3.10.x
- Node.js 22
- Git

Docker, WSL, 관리자 권한, GPU 또는 외부 서비스는 필요하지 않습니다.

## 설치

```powershell
git clone https://github.com/kiwoju-git/Data-analysis-platform.git
cd Data-analysis-platform
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
```

GitHub에서 받은 ZIP을 사용하는 경우 압축을 푼 프로젝트 폴더에서
`bootstrap.ps1`을 실행하면 됩니다.

## 실행

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

실행 후 브라우저에서 [http://127.0.0.1:8600](http://127.0.0.1:8600)을 엽니다.
Backend는 `http://127.0.0.1:8000`에서 실행됩니다. 포트가 이미 사용 중이면 기존
프로세스를 자동으로 종료하거나 다른 포트로 이동하지 않고 오류를 표시합니다.

## 기본 사용 순서

1. `홈`에서 현재 작업공간과 최근 자산을 확인합니다.
2. `데이터셋 > 데이터 등록`에서 파일을 올리고 파싱을 확정합니다.
3. `데이터셋 > 미리보기`에서 스키마, 역할, 단위와 품질 점검 결과를 확인합니다.
4. `분석`에서 모듈과 method를 선택하고 사전점검 후 실행합니다.
5. `그래프 > 그래프 작성`에서 필요한 변수 조합을 시각화합니다.
6. `리포트`에서 저장 결과를 열거나 HTML/CSV/JSON으로 내보냅니다.
7. `관리`에서 데이터셋, 분석 결과, 모델, 실험 설계와 Study를 관리합니다.

회귀 예측은 별도 분석 메뉴가 아니라 `회귀모형 적합` 결과 아래의 `예측` 영역에서
조건 행을 입력해 실행합니다. 삭제 작업은 `관리`에서 영향과 blocker를 확인한 뒤에만
진행할 수 있습니다.

처음 사용하는 경우 [한국어 end-to-end 튜토리얼](docs/statistical_twin_end_to_end_tutorial_ko.md)과
[synthetic sample 안내](examples/tutorial/README.md)를 참고하십시오.

## 검사

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\tutorial_smoke.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-diagnostics
```

Chromium이 설치되지 않았다면 E2E 명령에 `-InstallBrowsers`를 추가합니다.

## 데이터와 보안

- 기본 bind 주소는 `127.0.0.1`입니다.
- 원본 데이터와 생성 자산은 Git 저장소 밖의 로컬 작업공간에 저장됩니다.
- 원본 행, 붙여넣기 값과 내부 절대 경로를 로그나 외부 telemetry로 보내지 않습니다.
- 임의 Python·shell·`eval` 실행과 외부 pickle/joblib 로딩을 지원하지 않습니다.

## 라이선스

이 저장소에는 별도 `LICENSE` 파일이 없습니다. 배포·재사용 조건을 임의의
오픈소스 라이선스로 해석하지 마십시오.
