# Statistical Twin Four-Domain Presentation Preview 2026.08

이 release source는 `SOURCE_COMMIT.txt`에 기록된 최신 full main을 기준으로 합니다.

## 공개 범위

- 홈, 데이터셋, 분석 메뉴를 제공합니다.
- 1~4번 분석 도메인은 최신 full source와 같은 기능을 제공합니다.
- 5~8번 분석 도메인은 계획됨 카드로 표시되며 실행할 수 없습니다.
- frontend card/sidebar와 backend direct execution guard가 같은 범위를 사용합니다.

## 배포 범위

| Profile | Backend | Frontend | Workspace |
| --- | ---: | ---: | --- |
| Four domains | 8002 | 8602 | `StatisticalTwinPresentationFourDomains` |

전체 앱은 `8000/8600`을 유지합니다. 이 prerelease는 정식 전체 배포본이 아닙니다.

일부 Windows 환경은 동적 포트 예약으로 `8602` 바인딩을 거부할 수 있습니다. `scripts/diagnose-presentation.ps1`로 확인한 뒤 `START_HERE.ps1 -FrontendPort <available-port>`로 실행할 수 있으며, backend와 workspace 분리는 그대로 유지됩니다.
