# Statistical Twin Presentation Profiles

발표용 ZIP은 전체 제품을 삭제한 배포본이 아니라 동일 source를 제한된 profile로 실행하는 prerelease입니다.

## Core preview

- 메뉴: 홈, 데이터셋, 분석
- 분석: 탐색적 분석, 가설 검정
- Backend: `127.0.0.1:8001`
- Frontend: `127.0.0.1:8701`
- Workspace: `%LOCALAPPDATA%\StatisticalTwinPresentationCore`

## Regression preview

- 메뉴: 홈, 데이터셋, 분석
- 분석: 탐색적 분석, 가설 검정, 상관관계 및 회귀분석
- Backend: `127.0.0.1:8002`
- Frontend: `127.0.0.1:8702`
- Workspace: `%LOCALAPPDATA%\StatisticalTwinPresentationRegression`

전체 앱은 `8000/8600`과 기존 workspace를 유지합니다. 세 실행 환경은 동시에 실행할 수 있으며 workspace DB를 공유하지 않습니다.

발표용 backend는 profile별 method catalog만 공개하고 숨겨진 method 실행을 `presentation_profile_method_unavailable`로 거부합니다. Core preview에는 regression 전용 route가 없고, Regression preview에만 저장 회귀모델 workflow에 필요한 regression route가 등록됩니다. DOE, Bayesian, 품질 관리, 그래프, 리포트, 자산 관리 route는 두 preview 모두에서 사용할 수 없습니다.

GitHub Release에서는 자동 생성된 source ZIP이 아니라 `statistical-twin-presentation-core-...zip` 또는 `statistical-twin-presentation-regression-...zip` custom asset을 받으세요. 각 custom ZIP의 `README.md`와 `START_HERE.ps1`이 해당 profile을 고정합니다.
