# Statistical Twin Presentation Preview 2026.08

이 release source는 `SOURCE_COMMIT.txt`에 기록된 최신 full main을 기준으로 하며 두 개의 custom ZIP profile을 제공합니다.

## 수정 사항

- ZIP의 첫 README가 full `dev.ps1`을 안내하던 문제를 제거했습니다.
- custom ZIP은 profile이 고정된 `START_HERE.ps1`만 첫 실행 경로로 제공합니다.
- backend child job에 profile, workspace, CORS를 명시적으로 전달합니다.
- Core preview와 Regression preview의 port와 workspace를 서로 분리했습니다.
- frontend menu, backend method catalog, direct route guard를 같은 profile allowlist로 검증합니다.

## 배포 범위

| Profile | 분석 module | Backend | Frontend | Workspace |
| --- | --- | ---: | ---: | --- |
| Core | 탐색적 분석, 가설 검정 | 8001 | 8701 | `StatisticalTwinPresentationCore` |
| Regression | Core + 상관관계 및 회귀분석 | 8002 | 8702 | `StatisticalTwinPresentationRegression` |

전체 앱은 `8000/8600`을 유지합니다. 이 prerelease는 정식 전체 배포본이 아닙니다.
