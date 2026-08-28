# Statistical Twin 발표용 4도메인 미리보기

이 ZIP은 홈, 데이터셋, 분석 메뉴를 제공하며 분석 도메인 1~4를 실행할 수 있습니다. 도메인 5~8은 계획됨 상태로 표시됩니다.

## 설치

프로젝트 루트에서 PowerShell을 열고 한 번 실행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-presentation.ps1
```

## 실행

```powershell
powershell -ExecutionPolicy Bypass -File .\START_HERE.ps1
```

- 화면: `http://127.0.0.1:8602`
- Backend: `http://127.0.0.1:8002`
- 작업공간: `%LOCALAPPDATA%\StatisticalTwinPresentationFourDomains`

전체 앱의 `8000/8600` 및 기존 작업공간과 분리되어 동시에 실행할 수 있습니다. 이 ZIP에서는 `scripts/dev.ps1` 대신 `START_HERE.ps1`을 실행하세요.

## 포트 진단

실행 전에 다음 명령으로 `8002/8602` 사용 가능 여부를 확인할 수 있습니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\diagnose-presentation.ps1
```

Windows가 `8602`를 예약해 `EACCES`를 반환하는 PC에서는 관리자 설정을 임의로 변경하지 말고, 비어 있는 포트를 지정해 실행합니다. 예:

```powershell
powershell -ExecutionPolicy Bypass -File .\START_HERE.ps1 -BackendPort 8002 -FrontendPort 9202
```
