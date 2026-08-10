# Statistical Twin 발표용 Core 미리보기

이 ZIP은 **홈, 데이터셋, 탐색적 분석, 가설 검정**만 공개하는 발표용 버전입니다.
전체 앱과 동시에 실행할 수 있도록 별도 포트와 작업공간을 사용합니다.

## 설치

프로젝트 루트에서 PowerShell을 열고 한 번 실행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-presentation.ps1
```

## 실행

```powershell
powershell -ExecutionPolicy Bypass -File .\START_HERE.ps1
```

- 화면: `http://127.0.0.1:8701`
- Backend: `http://127.0.0.1:8001`
- 작업공간: `%LOCALAPPDATA%\StatisticalTwinPresentationCore`

전체 앱은 기존 `8000/8600`과 기존 작업공간을 그대로 사용합니다.
이 ZIP에서는 `scripts/dev.ps1`이 아니라 반드시 `START_HERE.ps1`을 실행하세요.
