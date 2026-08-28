# Statistical Twin Four-Domain Presentation Preview

이 prerelease는 최신 full source를 삭제하지 않고 별도 profile로 제한합니다.

- 상단 메뉴: 홈, 데이터셋, 분석
- 사용 가능 도메인: 기초통계·탐색, 평균비교·동등성, 비율·범주형 데이터, 상관·회귀·예측
- 계획됨 도메인: 실험계획·최적화, AI/ML 실험설계, 품질·공정 모니터링, 측정시스템·변동성
- Backend: `127.0.0.1:8002`
- Frontend: `127.0.0.1:8602`
- Workspace: `%LOCALAPPDATA%\StatisticalTwinPresentationFourDomains`

계획됨 도메인은 PCA 계획 카드와 같은 비활성 정보 카드로 표시됩니다. 해당 method를 direct API로 실행하면 `presentation_profile_method_unavailable` 오류를 반환합니다.

전체 앱은 `8000/8600`과 기존 workspace를 유지하므로 같은 컴퓨터에서 동시에 실행할 수 있습니다. GitHub Release에서는 profile이 고정된 custom ZIP과 그 안의 `START_HERE.ps1`을 사용합니다.
