# DataLab Studio 6개 통계 모듈 구현 가이드 v1.0

> 대상 구현 저장소: `kiwoju-git/Data-analysis-platform`
>
> 문서 저장소: `kiwoju-git/Repository`
>
> 기준 시점: 2026-06-23
>
> 기준 환경: **Windows 11 / PowerShell / Python 3.10.x / CPU-only / localhost 단일 사용자**

## 0. 문서의 지위와 사용법

이 문서는 기존 `data_prd_addendum.md`, `AGENTS.md`를 대체하지 않고 **6개 통계 모듈의 정보 구조, 구현 범위, 통계 규약, API, 저장 구조 및 단계별 개발 순서**를 구체화한다.

문서 간 우선순위는 다음과 같다.

1. 보안, 개인정보, 재현성, Windows/Python 3.10 및 CPU-only 제약은 `AGENTS.md`와 `data_prd_addendum.md`를 따른다.
2. 6개 상단 탭의 제품 범위, 메서드 정의, 구현 순서 및 완료 기준은 이 문서를 따른다.
3. 이 문서와 원본 PRD의 ML/AutoML 우선순위가 충돌하면 이 문서가 우선한다.
4. 구현 중 통계 방법을 바꾸거나 범위를 축소해야 하면 조용히 변경하지 말고 이 문서의 결정 기록을 갱신한다.

Codex는 기능 구현을 시작하기 전에 최소한 다음 파일을 읽어야 한다.

- `AGENTS.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `data_prd_addendum.md`
- 변경하려는 디렉터리의 코드와 테스트

이 문서에서 `P0`는 해당 Gate의 필수 범위, `P1`은 다음 확장, `P2`는 별도 승인 후 확장을 뜻한다.

---

## 1. 요구사항 요약과 명칭 정리

웹 애플리케이션의 분석 영역은 다음 6개 상단 모듈로 재구성한다.

| 모듈 ID | 상단 탭 표시명 | 포함 기능 |
| --- | --- | --- |
| `exploration` | 탐색적 분석 | Display Descriptive Statistics, Graphical Summary, Normality Test, Test for Equal Variances |
| `hypothesis` | 가설 검정 | t-Test, 2-Sample t-Test, ANOVA, Equivalence Test, 1-Sample Wilcoxon, Mann-Whitney, Kruskal-Wallis |
| `categorical` | 범주형 데이터 분석 | 1-Proportion, 2-Proportion, Chi-square Test for Association |
| `regression` | 상관관계 및 회귀분석 | Pearson Correlation, X–Y Correlation, Fit Regression Model, Predict, Response Optimizer |
| `quality` | 품질 관리 | Control Chart, Variables Charts for Individuals, Variables Charts for Subgroups, Run Chart, Capability Analysis, Gage R&R Study, Gage Run Chart |
| `doe` | 실험 계획법 | Design of Experiments (DoE), Response Surface Method (RSM) |

명칭은 다음처럼 바로잡는다.

- `Respone Surface Method` → **Response Surface Method**
- `Design of Experiment`는 화면에서 **Design of Experiments (DoE)**로 표기한다.
- `t-Test`는 본 문서에서 **1-Sample t-Test**를 뜻한다.
- 기존 목록에 없지만 실무상 필수인 **Paired t-Test**는 가설 검정의 추가 P0 메서드로 포함한다.
- `X–Y Correlation`은 시계열 지연 상관이 아니라 **여러 X 변수 집합과 여러 Y 변수 집합 사이의 교차 상관행렬**로 정의한다. 제품 소유자가 다른 의미를 원하면 구현 전에 이름과 계약을 바꾼다.
- `Control Chart`는 중복을 피하기 위해 **차트 선택 허브와 계수형 관리도(P/NP/C/U)**를 담당하고, 계량형 관리도는 별도 메뉴에서 담당한다.
- `Gage Run Chart`는 일반 Run Chart와 구분하여 **부품·측정자·반복별 측정값을 실행 순서 또는 부품 순서로 확인하는 측정시스템 진단 그래프**로 정의한다.

---

## 2. 현재 Gate A 구현 상태 점검

`Data-analysis-platform/main`의 확인 가능한 구현을 기준으로 한 상태이다.

### 2.1 이미 활용할 수 있는 기반

- FastAPI 앱 팩토리, 제한된 CORS, `/api/v1` 라우팅 및 구조화 오류 처리 기반
- 루트 안내 API `GET /`와 health API `GET /api/v1/health`
- React 18 + Vite + TypeScript 기반의 최소 셸과 API health 표시
- Windows-latest, Python 3.10, Node 22를 사용하는 CI
- PowerShell 기반 bootstrap/check/dev 흐름
- CSV/TSV/TXT/XLSX 원본 업로드
- Excel/스프레드시트에서 복사한 표 텍스트를 raw dataset으로 등록
- 업로드 크기 제한, 안전한 파일명, SHA-256, 임시 파일 후 `os.replace` 저장
- 파일 형식 감지와 파싱 옵션 제안, preamble 이후 headerless delimited text 데이터 시작 행 제안
- SQLite schema v3 migration과 `datasets`, `dataset_versions`, `dataset_columns` 메타데이터 테이블
- delimited text 및 basic XLSX 파싱 확정 API, header/headerless 확정 옵션, 불변 dataset version `v1`, dataset version/schema/rows 조회 API
- schema update API, 서버 페이지네이션 기반 row preview API, canonical JSONL rows/manifest materialization, duplicate-row, memory estimate, date/time preflight 및 persisted profile summary artifact를 포함한 profile/preflight API
- analysis method registry, `GET /api/v1/analysis-methods`, unavailable-only `POST /api/v1/analysis-runs` guard
- SQLite schema v4의 `analysis_runs`, `analysis_artifacts`, `jobs` metadata table과 schema v5의 `dataset_artifacts` metadata table
- `GET/DELETE /api/v1/analysis-runs/{analysis_id}`와 `GET/DELETE /api/v1/jobs/{job_id}` status/cancel skeleton
- 공통 analysis request/result/warning/provenance schema
- 업로드 또는 붙여넣기 입력, header/headerless 파싱 확정, Dataset Context Bar, schema update, row preview, basic profile/preflight table, split `AppChrome`/`useDatasetWorkflow`/`DatasetPreparationPage`/`DatasetParsingPanel`/`DatasetVersionPanel`/profile/schema/preview section data-preparation components, shared `datasetDisplay` helpers, 6개 모듈 planned/disabled shell, split `WorkspaceRouter`/`AnalysisPage`/`AnalysisShell`/`AnalysisWorkbench`/`DescriptiveAnalysisPanel`/`GraphicalSummaryPanel`/`NormalityAnalysisPanel`/`EqualVariancesPanel`/`OneSampleTPanel`/`PairedTPanel`/`EquivalenceTostPanel`/`OneSampleWilcoxonPanel`/`TwoSampleTPanel`/`MannWhitneyPanel`/`KruskalWallisPanel`/`OneWayAnovaPanel`/`OneProportionPanel`/`TwoProportionPanel`/`ChiSquareAssociationPanel`/`PearsonCorrelationPanel`/`XyCorrelationPanel`/`LinearModelPanel`/`IndividualsChartPanel`/`SubgroupChartPanel`/`RunChartPanel`/`CapabilityPanel`/`GageRrPreflightPanel`/`GageRunChartPanel` components, `useAnalysisSelection` route state, selected-method Workbench shell과 method-specific guidance를 보여주는 최소 UI
- ruff, mypy, pytest, ESLint, TypeScript, Vitest, frontend build 품질 게이트

### 2.2 6개 모듈 전에 반드시 보완해야 하는 공백

Gate B0 storage/run foundation 후에도 다음 기능은 아직 공통 플랫폼 계약으로 완성되어 있지 않다.

1. 공통 filter UI state를 다음 실제 executable method에 안전하게 연결하는 계약
2. 장시간 작업의 실제 worker 실행과 best-effort 취소
3. 차트와 표의 공통 직렬화 계약
4. RSM/optimizer와 확장 DOE 설계 자산의 저장 구조
5. route-level Analysis Workbench의 더 깊은 페이지/컴포넌트 분해
6. pandas, NumPy, SciPy, statsmodels, XLSX 파서 등 통계 실행 의존성
7. 분석별 기준 데이터와 수치 허용오차 테스트

따라서 곧바로 개별 통계식을 추가하지 말고, 남은 **Gate B0 – 분석 플랫폼 계약**을 먼저 완료해야 한다.

### 2.3 현재 문서의 작은 불일치

- Workbench의 저장 결과 history/export/comparison/restore 상태는 각각의
  전용 hook이 소유하고 `AnalysisShell`/`AnalysisWorkbench`에는 네 개의
  grouped state prop으로만 전달된다. 각 hook은 latest-request guard로
  reset, 새 요청 또는 unmount 이전의 응답과 `finally`가 최신
  상태/loading을 덮지 못하게 한다. 이전 field-by-field prop fallback은
  제거되었다.
- 현재 frontend의 `App.tsx`는 API bootstrap, route state, analysis orchestration ownership을 유지하지만, 앱 sidebar/topbar/context layout은 `AppChrome`으로 분리되었고, dataset upload/paste/parsing/schema/preview/profile workflow state와 API handlers는 `useDatasetWorkflow`로 분리되어 있다. B0 파싱 확정, Dataset Context Bar, schema update, row preview, basic profile/preflight table 렌더링은 `DatasetPreparationPage`, `DatasetParsingPanel`, `DatasetVersionPanel`, profile/schema/preview section components, 그리고 `datasetDisplay` helper로 분리되어 있다. 분석 영역은 `WorkspaceRouter`, `AnalysisPage`, `AnalysisShell`, `AnalysisWorkbench`, `DescriptiveAnalysisPanel`, `GraphicalSummaryPanel`, `NormalityAnalysisPanel`, `EqualVariancesPanel`, `OneSampleTPanel`, `PairedTPanel`, `EquivalenceTostPanel`, `OneSampleWilcoxonPanel`, `TwoSampleTPanel`, `MannWhitneyPanel`, `KruskalWallisPanel`, `OneWayAnovaPanel`, `OneProportionPanel`, `TwoProportionPanel`, `ChiSquareAssociationPanel`, `PearsonCorrelationPanel`, `XyCorrelationPanel`, `LinearModelPanel`, `RegressionPredictionWorkspace`, `ResponseOptimizerWorkspace`, `IndividualsChartPanel`, `SubgroupChartPanel`, `RunChartPanel`, `CapabilityPanel`, `GageRrPreflightPanel`, `GageRunChartPanel`로 분리되어 있고 URL 선택 상태는 `useAnalysisSelection`이 관리한다. `appRoute`가 루트/데이터셋 경로와 `/analysis/{module_id}/{method_id}` 경로를 구분하고 `WorkspaceRouter`가 데이터셋 page와 분석 page를 조건부 렌더링한다. 6개 모듈 catalog shell, selected-method Workbench shell, 30개 method-specific guidance는 이 컴포넌트 경계 안에서 렌더링되며, 선택된 분석은 `/analysis/{module_id}/{method_id}` 경로와 legacy hash fallback으로 복원된다. 지원되는 AND filter 조건 UI는 Workbench 공통 위치로 이동했고, 현재 실행 요청 payload로 직렬화되는 메서드는 `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, `eda.equal_variances`, `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`, `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, `categorical.chi_square_association`, `regression.pearson`, `regression.xy_correlation`, `regression.linear_model`, `quality.individuals_chart`, `quality.subgroup_chart`, `quality.run_chart`, `quality.capability`, `quality.gage_rr`, `quality.gage_run_chart`이다. `quality.gage_rr`는 실행 전 balanced crossed 설계 사전점검 shell과 실행 결과 패널을 함께 제공하고, `quality.gage_run_chart`는 같은 역할 선택을 재사용해 redacted index 기반 진단 차트를 렌더링한다.
- Gate D1 DOE 설계 자산 slice로 `doe.factorial_design`은 available 상태다. `POST /api/v1/doe-designs/factorial`와 `GET /api/v1/doe-designs/{design_id}`는 2-level full factorial 설계표를 생성/조회하고, SQLite schema v7의 `experiment_designs`, `experiment_design_versions`, `experiment_runs`에 design/version/run metadata와 `design_sha256`을 저장한다. `PUT /api/v1/doe-designs/{design_id}/responses`와 `GET /api/v1/doe-designs/{design_id}/responses`는 schema v8의 `experiment_run_responses`에 현재 design version의 run_order 전체와 정확히 맞는 numeric response series를 저장/조회한다. `POST /api/v1/analysis-runs`로는 `analysis_method_uses_dedicated_api`를 반환하며, 효과 추정, OLS/ANOVA, alias 구조, DOE 분석 차트는 아직 구현하지 않는다. Frontend는 `FactorialDesignPanel`에서 factor low/high, 반복, 센터점, block, random seed를 입력하고 실제 생성된 run table 미리보기와 response entry shell을 표시한다.
- 현재 backend 핵심 의존성에는 NumPy 2.2.6, SciPy 1.15.3, scikit-learn 1.7.2가 포함된다. scikit-learn은 `doe.bayesian_optimization`의 전용 spawn worker에서만 Matérn-5/2 GP/EI 계산에 import하며 API startup에서는 import하지 않는다. `eda.descriptive`, `eda.graphical_summary`, `quality.individuals_chart`, `quality.subgroup_chart`, `quality.run_chart`, `quality.capability`, `quality.gage_run_chart`, basic XLSX worksheet parsing은 Python 표준 라이브러리 기반이고, 나머지 현재 수치 메서드는 승인된 NumPy/SciPy/scikit-learn 경계를 사용한다. Python 환경은 CPython 3.10 Windows AMD64 wheel hash lock으로 고정하며, pandas/statsmodels/openpyxl 등 추가 의존성은 별도 호환성 검토 후 lock을 갱신한다.
- 현재 분석 실행 API는 `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, `eda.equal_variances`, `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`, `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, `categorical.chi_square_association`, `regression.pearson`, `regression.xy_correlation`, `regression.linear_model`, `quality.individuals_chart`, `quality.subgroup_chart`, `quality.run_chart`, `quality.capability`, `quality.gage_rr`, `quality.gage_run_chart`를 실제 계산으로 실행하고, 다른 미구현 메서드는 거부한다. `doe.factorial_design`은 available이지만 `POST /api/v1/analysis-runs`가 아니라 전용 `POST /api/v1/doe-designs/factorial` 설계 자산 API를 사용한다. `POST /api/v1/quality/gage-rr/preflight`는 `quality.gage_rr` 실행 전에 dataset version의 balanced crossed 설계 준비 여부만 반환하는 보조 API다. 통계 계산 mock result 또는 완료처럼 보이는 빈 결과 화면은 추가하지 않는다.

---

## 3. 기존 계획에서 변경해야 할 사항

### 3.1 제품의 중심축 변경

기존 PRD의 선형 흐름은 다음과 같았다.

```text
데이터 로드 → 전처리 → EDA → 통계검정 → ML → 평가 → 예측 → 리포트
```

새 제품 정보 구조는 다음처럼 바꾼다.

```text
프로젝트/데이터셋 준비
        ↓
공통 데이터셋 버전 및 분석 컨텍스트
        ↓
┌ 탐색적 분석
├ 가설 검정
├ 범주형 데이터 분석
├ 상관관계 및 회귀분석
├ 품질 관리
└ 실험 계획법
        ↓
공통 이력/리포트/내보내기
```

전처리, 데이터 버전, 리포트는 특정 탭에 속하지 않는 **공통 서비스**가 된다. 사용자는 하나의 분석을 마친 뒤 선형 단계의 “다음” 버튼을 따라갈 필요 없이 다른 통계 모듈로 이동할 수 있다.

### 3.2 ML/AutoML 우선순위 변경

- PyCaret AutoML, Optuna 튜닝, SHAP/LIME 및 일반 분류 ML은 6개 모듈이 안정화될 때까지 Gate E/P2로 이동한다.
- `Predict`는 우선 **회귀분석에서 앱이 생성한 회귀모델의 예측**을 뜻한다.
- 일반 ML 예측과 회귀 예측은 같은 화면/모델 ID를 무리하게 공유하지 않는다.
- `Response Optimizer`는 원시 데이터에 직접 적용하는 AI 최적화가 아니라 **검증된 회귀/DOE 반응표면 모델의 예측식과 설계영역**을 기반으로 한다.

### 3.3 데이터 모델 변경

일반적인 수치형/범주형 타입만으로는 품질관리와 DOE를 구현할 수 없다. 다음 역할을 추가해야 한다.

- 순서 또는 시간: `order`, `timestamp`
- 합리적 부분군: `subgroup_id`
- 부품: `part_id`
- 측정자: `operator_id`
- 반복: `replicate_id`
- 검사 단위/기회 수: `sample_size`, `opportunities`
- 규격: `lsl`, `usl`, `target`
- 단위: `unit`
- DOE 요인: `factor`, `factor_type`, `low`, `high`, `levels`, `center`
- DOE 실행: `standard_order`, `run_order`, `block`, `is_center_point`
- 반응: `response`

이 역할은 컬럼의 영구 타입과 구분한다. 같은 컬럼이 분석에 따라 그룹 또는 부분군 역할을 할 수 있으므로 **분석 구성 스냅샷에 역할을 저장**한다.

### 3.4 리포트 변경

리포트는 단순 그래프 모음이 아니라 다음을 포함해야 한다.

- 분석 메서드와 버전
- 사용 데이터셋 버전과 원본 SHA-256
- 필터, 변수 역할, 결측 처리, 표본 수와 제외 수
- 옵션, alpha, 대립가설, 다중비교 보정
- 추정치, 신뢰구간, 효과크기, 검정통계량, p-value
- 관리도 기준 구간 및 규칙 위반점
- 규격한계와 관리한계의 명확한 구분
- DOE 설계 생성 조건, 랜덤 시드, 실행 순서, alias 정보
- 경고, 가정, 한계, 소프트웨어/패키지 버전

---

## 4. 상단 탭과 전체 UI 정보 구조

### 4.1 권장 레이아웃

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ DataLab Studio | 프로젝트 | 데이터셋 v3 | 1,240행 | 저장됨 | API ready      │
├──────────────┬───────────────────────────────────────────────────────────────┤
│ 프로젝트     │ [탐색적 분석] [가설 검정] [범주형] [상관·회귀] [품질] [DOE] │
│ 데이터셋     ├───────────────────────────────────────────────────────────────┤
│ 분석 이력    │ 메서드 보조 탐색 | 입력/옵션 | 사전점검 | 실행 | 결과         │
│ 리포트       │                                                               │
│ 설정         │                                                               │
└──────────────┴───────────────────────────────────────────────────────────────┘
```

- 기존 왼쪽 사이드바는 **전역 자원 탐색**으로 유지한다.
- 6개 모듈은 main 영역 상단의 **라우트 기반 navigation**으로 둔다.
- 서로 다른 페이지로 이동하므로 ARIA `tablist`를 무조건 사용하지 말고 `<nav>`와 링크, `aria-current="page"`를 사용한다.
- 작은 화면에서는 가로 스크롤 또는 “분석 모듈” 메뉴로 축약한다.
- 선택한 프로젝트, 데이터셋 버전, 활성 필터와 행 수는 어떤 탭에서도 상단 Context Bar에 계속 표시한다.
- DOE의 설계 생성은 데이터셋이 없어도 진입 가능하다. 그 외 메서드는 데이터셋 버전이 없으면 실행을 비활성화하고 이유를 표시한다.

### 4.2 권장 라우트

```text
/projects/:projectId/datasets/:datasetVersionId/exploration/:methodId
/projects/:projectId/datasets/:datasetVersionId/hypothesis/:methodId
/projects/:projectId/datasets/:datasetVersionId/categorical/:methodId
/projects/:projectId/datasets/:datasetVersionId/regression/:methodId
/projects/:projectId/datasets/:datasetVersionId/quality/:methodId
/projects/:projectId/doe/designs/:designId?
```

라우트에는 화면 복구에 필요한 최소 ID만 둔다. 모든 분석 옵션을 query string에 노출하지 말고 초안 상태 또는 서버의 분석 구성으로 저장한다.

### 4.3 안정적인 메서드 ID

화면 표시명은 바뀔 수 있으나 아래 ID는 API, DB, 테스트, 내보내기에서 안정적으로 사용한다.

| 모듈 | 메서드 ID | 화면 표시명 |
| --- | --- | --- |
| 탐색 | `eda.descriptive` | Display Descriptive Statistics |
| 탐색 | `eda.graphical_summary` | Graphical Summary |
| 탐색 | `eda.normality` | Normality Test |
| 탐색 | `eda.equal_variances` | Test for Equal Variances |
| 가설 | `hypothesis.one_sample_t` | 1-Sample t-Test |
| 가설 | `hypothesis.paired_t` | Paired t-Test |
| 가설 | `hypothesis.two_sample_t` | 2-Sample t-Test |
| 가설 | `hypothesis.one_way_anova` | One-Way ANOVA |
| 가설 | `hypothesis.equivalence_tost` | Equivalence Test (TOST) |
| 가설 | `hypothesis.one_sample_wilcoxon` | 1-Sample Wilcoxon Signed-Rank |
| 가설 | `hypothesis.mann_whitney` | Mann-Whitney U |
| 가설 | `hypothesis.kruskal_wallis` | Kruskal-Wallis |
| 범주형 | `categorical.one_proportion` | 1-Proportion |
| 범주형 | `categorical.two_proportion` | 2-Proportion |
| 범주형 | `categorical.chi_square_association` | Chi-square Test for Association |
| 회귀 | `regression.pearson` | Pearson Correlation |
| 회귀 | `regression.xy_correlation` | X–Y Correlation |
| 회귀 | `regression.linear_model` | Fit Regression Model |
| 회귀 | `regression.predict` | Predict |
| 회귀 | `regression.response_optimizer` | Response Optimizer |
| 품질 | `quality.attribute_control_chart` | Control Chart |
| 품질 | `quality.individuals_chart` | Variables Charts for Individuals |
| 품질 | `quality.subgroup_chart` | Variables Charts for Subgroups |
| 품질 | `quality.run_chart` | Run Chart |
| 품질 | `quality.capability` | Capability Analysis |
| 품질 | `quality.gage_rr` | Gage R&R Study |
| 품질 | `quality.gage_run_chart` | Gage Run Chart |
| DOE | `doe.factorial_design` | Design of Experiments |
| DOE | `doe.response_surface` | Response Surface Method |
| DOE | `doe.bayesian_optimization` | Bayesian Optimization |

메서드의 계산 방식이 바뀌면 ID를 재사용하면서 결과 의미를 바꾸지 말고 `method_version`을 올린다.

---

## 5. 공통 Analysis Workbench

모든 메서드는 가능한 한 동일한 사용자 흐름을 사용한다.

1. **데이터 선택**: 데이터셋 버전, 필터, 원자료/요약자료 모드
2. **변수 역할 지정**: 반응, 그룹, X/Y, 부분군, 부품, 측정자 등
3. **옵션 설정**: 가설, alpha, CI, 검정 방식, 그래프, 보정
4. **사전점검**: 사용 N, 제외 N, 타입, 가정, 구조 오류, 예상 실행비용
5. **실행**: 빠른 분석은 동기 응답, 긴 분석은 job 생성
6. **결과**: 추정치 → CI → 효과크기 → 검정 → 진단 → 경고 순서
7. **저장/내보내기**: JSON, CSV table, 차트 이미지, HTML report, 재현 코드

### 5.1 공통 frontend 컴포넌트

```text
frontend/src/
├─ app/
│  ├─ router/
│  └─ layout/
├─ features/datasets/
├─ features/analyses/
│  ├─ catalog/
│  ├─ shared/
│  │  ├─ ModuleNavigation.tsx
│  │  ├─ DatasetContextBar.tsx
│  │  ├─ VariableRolePicker.tsx
│  │  ├─ AnalysisPreflight.tsx
│  │  ├─ AnalysisResult.tsx
│  │  ├─ AssumptionPanel.tsx
│  │  ├─ WarningPanel.tsx
│  │  └─ ProvenancePanel.tsx
│  ├─ exploration/
│  ├─ hypothesis/
│  ├─ categorical/
│  ├─ regression/
│  ├─ quality/
│  └─ doe/
└─ shared/
```

권장 frontend 기반은 다음과 같다.

- 라우팅: React Router 계열
- 서버 상태: TanStack Query 계열
- 폼: React Hook Form + Zod
- 차트: Plotly 계열 하나를 기본으로 하고 lazy-load
- 테이블: 서버 페이지네이션을 지원하는 허용적 라이선스 컴포넌트

Recharts와 Plotly를 같은 목적에 중복 도입하지 않는다. RSM contour/surface, Q-Q, control chart까지 표현할 수 있는 하나의 차트 계층을 우선한다.

### 5.2 미구현 메서드 표시

Gate B0에서 6개 상단 탭과 메서드 목록을 먼저 노출할 수 있으나 다음 규칙을 지킨다.

- 구현되지 않은 메서드는 `계획됨` 상태로 표시한다.
- 실행 버튼과 가짜 샘플 숫자를 표시하지 않는다.
- “완료”처럼 보이는 빈 결과 화면을 만들지 않는다.
- method catalog의 `availability` 값으로 `available`, `planned`, `disabled`를 구분한다.

---

## 6. 공통 backend 아키텍처

### 6.1 권장 디렉터리

```text
backend/app/
├─ analyses/
│  ├─ registry.py
│  ├─ contracts.py
│  ├─ validation.py
│  ├─ provenance.py
│  ├─ charts.py
│  ├─ exploration/
│  ├─ hypothesis/
│  ├─ categorical/
│  ├─ regression/
│  ├─ quality/
│  └─ doe/
├─ api/v1/
│  ├─ analysis_methods.py
│  ├─ analysis_runs.py
│  ├─ regression_models.py
│  └─ experiment_designs.py
├─ services/
├─ storage/
└─ workers/
```

통계 계산 함수는 FastAPI `Request`, SQLite connection, 전역 DataFrame을 직접 받지 않는다. 명시적 typed input을 받고 typed result를 반환한다.

### 6.2 메서드 registry

각 메서드는 다음 메타데이터를 registry에 등록한다.

```python
AnalysisMethodDescriptor(
    method_id="hypothesis.two_sample_t",
    method_version="1.0.0",
    module_id="hypothesis",
    label_ko="2-표본 t-검정",
    label_en="2-Sample t-Test",
    availability="available",
    request_model=TwoSampleTRequest,
    result_model=InferenceResult,
    execution_mode="inline",
)
```

목적은 다음과 같다.

- frontend와 backend의 메서드 목록 불일치 방지
- 버전과 지원 상태 노출
- 입력 스키마/OpenAPI 생성
- method ID별 권한·성능·테스트 추적
- 하나의 거대한 `if/elif` 분석 엔드포인트 방지

### 6.3 공통 분석 실행 요청

```json
{
  "method_id": "hypothesis.two_sample_t",
  "method_version": "1.0.0",
  "dataset_version_id": "uuid",
  "filter_snapshot": {
    "expression_version": 1,
    "conditions": []
  },
  "roles": {
    "response": "strength",
    "group": "supplier"
  },
  "options": {
    "variance_assumption": "unequal",
    "alternative": "two-sided",
    "alpha": 0.05,
    "confidence_level": 0.95,
    "missing_policy": "complete_case"
  }
}
```

### 6.4 공통 결과 envelope

```json
{
  "analysis_id": "uuid",
  "method": {
    "id": "hypothesis.two_sample_t",
    "version": "1.0.0",
    "label": "Welch 2-Sample t-Test"
  },
  "status": "succeeded",
  "sample": {
    "n_total": 120,
    "n_used": 114,
    "n_excluded": 6,
    "exclusions": [{"reason": "missing", "count": 6}],
    "groups": {"A": 58, "B": 56}
  },
  "estimates": [],
  "confidence_intervals": [],
  "tests": [],
  "effect_sizes": [],
  "assumptions": [],
  "warnings": [],
  "tables": [],
  "charts": [],
  "artifacts": [],
  "provenance": {}
}
```

- 적용되지 않는 값은 키 의미를 바꾸지 말고 `null` 또는 빈 배열을 사용한다.
- 내부 원값은 충분한 정밀도로 보존하고 UI에서만 반올림한다.
- 경고는 코드와 사용자 메시지를 함께 가진다.
- backend가 임의 HTML 또는 JavaScript를 반환하지 않는다.
- 차트는 허용된 `chart_kind`와 typed data로 반환하고 frontend가 렌더링한다.

### 6.5 API 표면

```text
GET    /api/v1/analysis-methods
POST   /api/v1/analysis-runs
GET    /api/v1/analysis-runs/{analysis_id}
DELETE /api/v1/analysis-runs/{analysis_id}
GET    /api/v1/jobs/{job_id}
DELETE /api/v1/jobs/{job_id}

POST   /api/v1/datasets/{dataset_id}/confirm-parsing
GET    /api/v1/datasets/{dataset_id}/versions
GET    /api/v1/dataset-versions/{version_id}
GET    /api/v1/dataset-versions/{version_id}/rows
GET    /api/v1/dataset-versions/{version_id}/schema

GET    /api/v1/regression-models/{model_id}
POST   /api/v1/regression-models/{model_id}/prediction-preflight
POST   /api/v1/regression-models/{model_id}/predictions
GET    /api/v1/regression-models/predictions/{prediction_id}/rows
GET    /api/v1/dataset-versions
POST   /api/v1/regression-models/predictions/{prediction_id}/exports/csv
POST   /api/v1/response-optimizations

POST   /api/v1/experiment-designs
GET    /api/v1/experiment-designs/{design_id}
POST   /api/v1/experiment-designs/{design_id}/randomize
POST   /api/v1/experiment-designs/{design_id}/responses
POST   /api/v1/experiment-designs/{design_id}/analyze
```

빠른 통계도 반드시 `analysis_id`를 생성한다. 실행 시간이 짧으면 같은 응답에서 결과를 반환하고, 긴 작업이면 `202 Accepted`와 `job_id`를 반환한다.

---

## 7. Gate B0 데이터셋 및 저장 계약

### 7.1 불변 데이터셋 버전

업로드 원본과 분석 가능한 데이터는 분리한다.

```text
raw upload
  └─ parsing confirmation
       └─ dataset version v1
            ├─ schema.json
            ├─ canonical data file
            ├─ profile summary artifact
            └─ provenance.json
```

현재 stdlib slice의 canonical 형식은 UTF-8 JSONL rows와 JSON manifest이다. Profile scan은 raw 값 샘플 없이 aggregate/preflight 결과를 `profile_summary` JSON artifact로 저장한다. SQLite에는 `dataset_artifacts`로 상대 경로, SHA-256, media type, byte size만 저장한다. 권장 고성능 canonical 형식은 여전히 Parquet이지만, `pyarrow`의 Python 3.10/Windows 호환성과 라이선스를 확인한 뒤 채택한다. 승인 전 임시 방편으로 pickle/joblib을 사용하지 않는다.

### 7.2 최소 컬럼 메타데이터

```json
{
  "column_id": "stable-id",
  "original_name": "측정값",
  "display_name": "측정값",
  "storage_type": "float64",
  "measurement_level": "continuous",
  "nullable": true,
  "unit": "mm",
  "category_levels": null,
  "parse_failures": 0
}
```

측정수준 enum은 최소 다음을 지원한다.

- `continuous`
- `count`
- `ordinal`
- `nominal`
- `binary`
- `identifier`
- `datetime`
- `text`

### 7.3 SQLite migration 추가

현재 schema v3에는 `datasets`, `dataset_versions`, `dataset_columns`가 있다. 이후 Gate B0/B1에서 최소 아래 자원을 순서대로 추가한다.

| 테이블 | 핵심 필드 |
| --- | --- |
| `dataset_versions` | 구현됨: version ID, dataset ID, version number, source SHA-256, parsing options JSON, row/column count, schema hash, created_at |
| `dataset_columns` | 구현됨: version ID, stable column ID, original/display names, inferred data type, measurement level, role, unit |
| `dataset_artifacts` | 구현됨: version ID, kind, relative path, SHA-256, media type, byte size, created_at |
| `transformations` | parent/child version, operation ID/version, parameters JSON, affected rows/columns |
| `analysis_runs` | method ID/version, dataset version, config JSON, status, result path, timestamps, code version |
| `analysis_artifacts` | analysis ID, kind, path, hash, media type |
| `jobs` | job ID, type, state, progress, cancellation, error code |
| `regression_models` | model ID, analysis ID, safe model manifest, domain, schema hash |
| `experiment_designs` | design ID/version, family, factors, seed, status, dataset version |
| `experiment_runs` | design ID, standard order, run order, block, factor settings, response state |

- JSON에는 반드시 `schema_version`을 포함한다.
- 외래키와 필요한 created/status index를 추가한다.
- migration은 기존 v2 데이터베이스에서의 업그레이드 테스트를 포함한다.
- DB에는 대형 결과표와 원시 데이터 전체를 blob으로 넣지 않고 해시가 있는 workspace artifact로 저장한다.

### 7.4 필터와 분석 스냅샷

분석 실행 시 “현재 화면에 보이는 데이터”를 암묵적으로 사용하지 않는다.

- 데이터셋 버전 ID
- 필터 표현식 버전과 조건
- 정렬은 분석 의미가 있는 경우에만 포함
- 사용 행 ID 또는 결정 가능한 필터 해시
- 결측 처리

을 분석 매니페스트에 저장한다. 데이터 또는 필터가 바뀌면 이전 결과는 `stale`로 표시하되 삭제하지 않는다.

---

## 8. 공통 통계 규약

모든 추론 분석은 가능한 범위에서 다음을 반환한다.

- 사용 N과 제외 N
- 그룹별 N
- 핵심 추정치
- 95% 신뢰구간 기본값
- 검정통계량, 자유도, raw p-value
- 다중비교가 있으면 adjusted p-value
- 효과크기
- 가정과 진단
- 수치/구조 경고
- 계산 방법과 라이브러리 버전

### 8.1 금지 규칙

- 정규성 검정 p-value 하나만으로 모수/비모수 검정을 자동 전환하지 않는다.
- `p >= 0.05`를 동일성 또는 동등성의 증거라고 설명하지 않는다.
- 비모수 검정을 무조건 “중앙값 검정”이라고 설명하지 않는다.
- 관찰자료의 상관과 회귀 결과를 인과로 표현하지 않는다.
- 품질 규격한계와 관리한계를 같은 선이나 같은 개념으로 취급하지 않는다.
- 이상치를 자동 삭제하지 않는다.
- 실패한 계산을 0, 빈 표 또는 다른 검정으로 조용히 대체하지 않는다.
- 소수점 표시값으로 후속 계산하지 않는다.

### 8.2 공통 오류/경고 코드 예시

```text
insufficient_observations
missing_required_role
constant_variable
non_finite_values
empty_group
singular_design_matrix
model_not_converged
sparse_expected_counts
invalid_equivalence_bounds
paired_ids_incomplete
unstable_process
invalid_subgroup_structure
unbalanced_gage_design
unknown_category_level
prediction_extrapolation
design_aliasing
lack_of_pure_error
```

오류는 계산을 중단해야 하는 상태, 경고는 결과와 함께 지속적으로 보여야 하는 상태로 구분한다.

---

# 9. 모듈 1 – 탐색적 분석

## 9.1 Display Descriptive Statistics (`eda.descriptive`)

### 목적

분석 대상 변수의 분포, 중심, 산포, 결측 및 데이터 품질을 숫자로 요약한다.

### 입력

- 수치형 또는 범주형 변수 1개 이상
- 선택적 그룹 변수
- 결측 처리: 변수별 유효값 또는 공통 complete-case를 명시
- 선택적 신뢰수준

### 수치형 기본 출력

- 전체 N, 유효 N, 결측 N/비율
- 평균, 평균의 표준오차
- 표본 표준편차(`ddof=1`), 분산
- 최소, Q1, 중앙값, Q3, 최대
- 범위, IQR
- 왜도, excess kurtosis와 계산 정의
- 평균의 신뢰구간
- 고유값 수, 0/음수 수

CV는 평균이 0에 가깝지 않고 사용자가 ratio scale임을 확인한 경우에만 표시한다. 단위가 있는 데이터에서 CV 해석 제한을 툴팁으로 설명한다.

### 범주형 기본 출력

- 유효 N, 결측 N
- 수준별 빈도와 비율
- 최빈값
- 고유 수준 수
- 매우 희귀한 수준 경고

### 수용 기준

- 그룹별 통계와 전체 통계의 N 합계가 결측 정책과 일치한다.
- 상수열, 1개 관측, 무한대 값에 대해 명시적 경고가 있다.
- 표시 반올림을 바꿔도 내부 결과 JSON은 변하지 않는다.

## 9.2 Graphical Summary (`eda.graphical_summary`)

현재 구현 상태: `eda.graphical_summary`는 stdlib 기반 실제 계산으로 available 상태다. API는 canonical rows를 스트리밍해 histogram, boxplot, Q-Q, ECDF용 typed chart-data payload를 저장/반환하며, frontend는 이 payload에서 inline SVG histogram, box plot, Q-Q plot, ECDF와 결과 요약 테이블을 렌더링한다. Grouping/small multiple, KDE, chart artifact export는 아직 구현하지 않는다.

### 기본 그래프

- Histogram: Freedman–Diaconis bin 제안을 기본으로 하되 사용자 조정 가능
- Box plot: 점과 사분위 정보를 함께 제공, 점을 자동 삭제하지 않음
- Q-Q plot: 기준선과 충분한 축 레이블
- ECDF
- 그룹이 있으면 small multiple 또는 제한된 overlay

KDE는 bandwidth 선택이 결과에 큰 영향을 주므로 P1 옵션으로 두어도 된다.

### 사전점검

- 그룹 수가 지나치게 많으면 small multiple 대신 선택/필터를 요구한다.
- 대용량 점 그래프는 사용자가 알 수 있는 deterministic sampling 또는 density rendering을 사용한다. 전체 분석 계산에는 샘플을 사용하지 않는다.
- histogram 축과 단위를 표시한다.

### 출력

각 그래프에 사용 N, 결측 제외, bin/bandwidth, 그룹, 데이터셋 버전을 메타데이터로 포함한다.

## 9.3 Normality Test (`eda.normality`)

현재 구현 상태: `eda.normality`는 available 상태다. NumPy 2.2.6/SciPy 1.15.3을 production dependency로 고정했고, API는 canonical rows를 스트리밍해 Shapiro-Wilk, Anderson-Darling, Q-Q point payload를 저장/반환하며, frontend는 Q-Q point payload를 inline SVG Q-Q plot으로 렌더링한다. 정규성 결과만으로 후속 모수/비모수 검정을 자동 전환하지 않으며, grouped normality는 이번 slice에서 `normality_grouping_not_supported`로 거부한다. 상세 계약은 `docs/normality_method_contract.md`를 따른다.

의존성 스파이크는 native Windows PowerShell에서 기록되었고 결과는 `docs/stat_dependency_spike.md`에 있다. `scripts/check-stat-deps.ps1`는 이후 SciPy-backed method를 추가하거나 dependency pin을 변경할 때 재검증용으로 사용한다.

### P0 범위

- Anderson–Darling 계열 정규성 검정
- Shapiro–Wilk
- Q-Q plot
- 기술적 왜도/첨도와 N

단순 Kolmogorov–Smirnov를 표본 평균/표준편차로 맞춘 정규분포에 그대로 적용하지 않는다. 필요하면 Lilliefors 보정 방법을 별도 명시적으로 구현한다.

### 기본 정책

- 기본 화면은 정규성 p-value보다 Q-Q plot과 N을 먼저 보여준다.
- 큰 N에서는 아주 작은 이탈도 유의할 수 있고 작은 N에서는 검정력이 부족하다는 경고를 표시한다.
- Shapiro–Wilk의 라이브러리별 큰 표본 p-value 제한 경고를 전달한다.
- 정규성 검정 결과만으로 후속 검정을 자동 변경하지 않는다.

### 입력/출력

- 연속형 변수와 선택 그룹
- 그룹별 유효 N
- 검정명, 통계량, p-value
- Q-Q 좌표 또는 typed chart data
- 해석 제한 및 후속 대안

## 9.4 Test for Equal Variances (`eda.equal_variances`)

현재 구현 상태: `eda.equal_variances`는 available 상태다. NumPy 2.2.6/SciPy 1.15.3을 사용해 canonical rows에서 Brown-Forsythe(Levene `center="median"`)와 Levene(mean)을 계산하고, 그룹별 N/평균/중앙값/분산/표준편차 요약을 저장/반환한다. 결과는 `analysis_row_snapshot` provenance와 result SHA-256 persistence를 사용하며, 이 결과만으로 후속 pooled/Welch 또는 ANOVA 방식을 자동 전환하지 않는다. 상세 계약은 `docs/equal_variances_method_contract.md`를 따른다.

Levene/Brown-Forsythe smoke calculation도 `scripts/check-stat-deps.ps1`의 일부다. method available 전환에는 별도의 reference fixture, edge-case warnings, schema/result envelope 테스트가 필요하며 현재 slice에서 추가되었다.

### 지원 방식

- Brown–Forsythe: Levene `center="median"`, 기본 추천
- Levene `center="mean"`
- Bartlett: 아직 실행하지 않으며 정규성에 민감함을 명시
- 2개 그룹 F-test: 아직 실행하지 않으며 정규성 가정이 강함을 명시하는 선택 옵션

### 입력

- 연속 반응 1개
- 범주 그룹 1개, 최소 2수준
- alpha와 선택 방식

### 출력

- 그룹별 N, 평균/중앙값, SD, 분산
- 검정통계량과 p-value
- 완전케이스 N, 제외된 결측/비숫자 반응 수
- 가정 및 추천 이유

가설검정의 등분산 설정을 이 결과가 자동으로 바꾸지는 않는다. 사용자가 Welch/pooled를 명시적으로 선택해야 한다.

---

# 10. 모듈 2 – 가설 검정

## 10.1 1-Sample t-Test (`hypothesis.one_sample_t`)

현재 구현 상태: `hypothesis.one_sample_t`는 available 상태다. SciPy 1.15.3을 사용해 canonical rows에서 하나의 수치 반응 컬럼을 명시적 기준 평균과 비교한다. 결과는 complete-case 제외 수, 표본 N/평균/SD, 평균 차이, CI, t, df, p-value, Cohen dz, Hedges-corrected standardized effect, `analysis_row_snapshot` provenance, result SHA-256 persistence를 포함한다. 정규성 진단만으로 비모수 대안으로 자동 전환하지 않는다. 상세 계약은 `docs/one_sample_t_method_contract.md`를 따른다.

- 입력: 연속 변수, 기준 평균 `mu0`, 대립가설, alpha
- 기본: 양측, 95% CI
- 출력: N, 평균, SD, SE, 평균 차이, CI, t, df, p, one-sample standardized effect
- 경고: 상수열, 작은 N, 심한 비대칭/영향점

## 10.2 Paired t-Test (`hypothesis.paired_t`) – 추가 필수 기능

현재 구현 상태: `hypothesis.paired_t`는 available 상태다. SciPy 1.15.3을 사용해 canonical rows에서 wide 형식의 두 수치 측정 컬럼을 비교하며, pair difference는 `after - before`로 정의한다. 결과는 complete-pair 제외 수, 전/후 평균, 차이 평균/SD/중앙값, CI, t, df, p-value, Cohen dz, Hedges-corrected standardized effect, `analysis_row_snapshot` provenance, result SHA-256 persistence를 포함한다. long format subject ID/condition/response 입력 방식은 아직 범위 밖이며, 정규성 진단만으로 paired t 또는 비모수 대안으로 자동 전환하지 않는다. 상세 계약은 `docs/paired_t_method_contract.md`를 따른다.

원래 목록에는 빠져 있으나 반복 전후 또는 짝지어진 자료를 올바르게 처리하기 위해 P0에 추가한다.

- 입력 방식 A: 두 측정 컬럼
- 입력 방식 B: long format의 subject ID, condition, response
- pair ID 중복·누락 검사
- 분석은 pair difference에 대해 수행
- 불완전 pair 제외 수를 명시
- 출력: 차이 평균/SD/CI, t, df, p, paired effect size

독립 2표본 검정으로 잘못 실행하지 않도록 UI에서 설계를 먼저 묻는다.

## 10.3 2-Sample t-Test (`hypothesis.two_sample_t`)

현재 구현 상태: `hypothesis.two_sample_t`는 available 상태다. SciPy 1.15.3을 사용해 canonical rows에서 Welch unequal-variance를 기본으로 계산하고, pooled Student 방식은 사용자가 명시적으로 선택한 경우에만 실행한다. 결과는 exact two-group response design, complete-case 제외 수, 그룹별 N/평균/SD, 평균 차이, CI, t, df, p-value, Cohen's d, Hedges g, `analysis_row_snapshot` provenance, result SHA-256 persistence를 포함한다. 등분산/정규성 진단만으로 검정 방식을 자동 전환하지 않는다. 상세 계약은 `docs/two_sample_t_method_contract.md`를 따른다.

- 입력: 연속 반응 + 정확히 2수준 그룹 또는 두 수치 컬럼
- 기본: **Welch unequal-variance**
- pooled Student 방식은 사용자가 명시적으로 선택
- 출력: 각 그룹 N/평균/SD, 평균 차이와 CI, t, df, p, Hedges' g
- 선택: 단측/양측, 차이 기준값
- 경고: 그룹 불균형, 영향점, 상수 그룹, 비독립 설계

등분산 검정이 비유의라는 이유만으로 pooled 방식을 자동 선택하지 않는다.

## 10.4 One-Way ANOVA (`hypothesis.one_way_anova`)

현재 구현 상태: `hypothesis.one_way_anova`는 available 상태다. SciPy 1.15.3 F distribution과 studentized range distribution을 사용해 canonical rows에서 표준 고정효과 일원배치 ANOVA를 계산한다. 결과는 complete-case 제외 수, 그룹별 N/평균/분산/CI, ANOVA table, F statistic, p-value, eta squared, omega squared, 유의한 omnibus 후 Tukey-Kramer 사후비교, `analysis_row_snapshot` provenance, result SHA-256 persistence를 포함한다. Welch ANOVA, Games-Howell, 이원/반복/ANCOVA, summary-statistic 입력, 진단 결과 기반 자동 전환은 아직 구현하지 않는다. 상세 계약은 `docs/one_way_anova_method_contract.md`를 따른다.

### P0 범위

- 고정효과 일원배치 ANOVA
- 표준 ANOVA 후 Tukey-Kramer
- 전체 검정과 사후검정의 일관성 보장

### 출력

- 그룹별 기술통계
- ANOVA table: SS, df, MS, F, p
- 효과크기: omega squared 우선, eta squared 보조
- 사후 비교: 차이, CI, raw/adjusted p
- 독립성, 잔차 정규성, 등분산 가정 경고

### 후순위

- 이원배치/공변량/반복측정은 별도 P1/P2 메서드로 추가한다. 하나의 ANOVA 폼에 무리하게 숨기지 않는다.
- Welch ANOVA와 Games-Howell은 별도 검증 slice에서 추가한다.

## 10.5 Equivalence Test – TOST (`hypothesis.equivalence_tost`)

현재 구현 상태: `hypothesis.equivalence_tost`는 available 상태다. SciPy 1.15.3 t distribution을 사용해 canonical rows에서 하나의 수치 반응 컬럼을 명시적 기준 평균과 비교하는 1표본 평균 TOST를 계산한다. 결과는 complete-case 제외 수, 표본 요약, 평균 차이, lower/upper one-sided test statistic과 p-value, TOST p-value, `1 - 2 * alpha` CI, Cohen dz, Hedges-corrected standardized effect, `analysis_row_snapshot` provenance, result SHA-256 persistence를 포함한다. 동등성 한계는 제품이 제안하지 않으며 사용자가 사전에 지정한 raw-unit lower/upper bound만 받는다. paired mean-difference TOST, 독립 2표본 TOST, standardized margin 입력, 비모수 동등성 검정, 진단 결과 기반 자동 전환은 아직 구현하지 않는다. 상세 계약은 `docs/equivalence_tost_method_contract.md`를 따른다.

### 지원 설계

- 현재 P0: 1표본 평균
- 후순위: paired mean difference
- 후순위: 독립 2표본 평균 차이, Welch 기본

### 필수 입력

- numeric response column
- reference mean
- lower equivalence bound
- upper equivalence bound
- alpha
- 설계 유형: 현재 `one_sample_mean`만 허용

동등성 경계는 제품이 임의 기본값을 제공하지 않는다. 사용자가 연구/공정 의미에 따라 사전에 지정해야 한다.

### 판정

- 두 단측검정이 모두 alpha 미만이고 해당 CI가 동등성 구간에 포함될 때만 동등성 근거로 표시한다.
- 일반 차이검정 비유의를 동등성으로 해석하지 않는다.
- 결과는 두 단측검정의 통계량/p-value와 CI를 모두 보존한다.
- 표준화 경계 입력은 P1로 두고 원 단위 경계를 P0로 한다.

## 10.6 1-Sample Wilcoxon Signed-Rank (`hypothesis.one_sample_wilcoxon`)

현재 구현 상태: `hypothesis.one_sample_wilcoxon`는 available 상태다. SciPy 1.15.3을 사용해 canonical rows에서 하나의 수치 반응 컬럼을 명시적 기준 위치와 비교한다. 결과는 complete-case 제외 수, zero difference/tie counts, signed-rank W statistic, p-value, exact/asymptotic method 기록, `zero_method`, signed-rank sums, rank-biserial, `analysis_row_snapshot` provenance, result SHA-256 persistence를 포함한다. zero/tie가 있는 상태에서 exact를 명시 요청하면 `one_sample_wilcoxon_exact_with_zeros_or_ties`로 거부하며, 대칭성 가정 없이 단순 중앙값 검정으로 표현하지 않는다. 상세 계약은 `docs/one_sample_wilcoxon_method_contract.md`를 따른다.

- 입력: 수치 변수, 기준 위치 `mu0`
- 계산: `x - mu0`의 signed-rank
- zero difference와 tie 수를 보고
- exact/asymptotic 선택 근거와 실제 사용 방식을 기록
- `zero_method`를 사용자 옵션으로 노출할 경우 의미를 설명
- 효과크기: rank-biserial 또는 명시된 rank 기반 효과
- 분포의 대칭성 가정 없이는 단순 중앙값 검정으로 단정하지 않음
- Hodges–Lehmann 추정치와 CI는 검증 후 P1 가능

## 10.7 Mann-Whitney U (`hypothesis.mann_whitney`)

현재 구현 상태: `hypothesis.mann_whitney`는 available 상태다. SciPy 1.15.3을 사용해 canonical rows에서 독립 정확히 2그룹 Mann-Whitney U를 계산한다. 결과는 complete-case 제외 수, 그룹별 N/중앙값/rank sum/mean rank, U statistic, p-value, exact/asymptotic method 기록, tie flag, rank-biserial, common-language probability, `analysis_row_snapshot` provenance, result SHA-256 persistence를 포함한다. tie가 있는 상태에서 exact를 명시 요청하면 `mann_whitney_exact_with_ties`로 거부하며, 결과를 단순 중앙값 차이 검정으로 표현하지 않는다. 상세 계약은 `docs/mann_whitney_method_contract.md`를 따른다.

- 독립된 정확히 2그룹
- U, p, 그룹별 N, rank summary
- exact/asymptotic 방식과 tie 처리 기록
- rank-biserial 및 probability-of-superiority 보조 효과크기
- 분포 모양이 다르면 위치 차이 해석이 제한됨을 표시
- 중앙값만 비교하는 검정이라고 표현하지 않음

## 10.8 Kruskal-Wallis (`hypothesis.kruskal_wallis`)

현재 구현 상태: `hypothesis.kruskal_wallis`는 available 상태다. SciPy 1.15.3을 사용해 canonical rows에서 독립 3그룹 이상 rank 기반 overall 검정을 계산한다. 결과는 complete-case 제외 수, 그룹별 N/중앙값/IQR/rank sum/mean rank, tie-corrected H statistic, df, p-value, epsilon-squared, `analysis_row_snapshot` provenance, result SHA-256 persistence를 포함한다. overall 검정이 선택 alpha에서 유의할 때만 Dunn pairwise 비교와 Holm adjusted p-value를 실제 계산하며, overall이 유의하지 않으면 post-hoc은 `overall_not_significant` reason으로 생략한다. 상세 계약은 `docs/kruskal_wallis_method_contract.md`를 따른다.

- 독립 3그룹 이상
- tie-corrected H, df, p
- 그룹별 N/중앙값/IQR/rank summary
- epsilon-squared 계열 효과크기와 정의
- overall 유의 후 Dunn pairwise + Holm 보정을 P0 목표로 한다.
- 사후검정 전 overall 결과와 선택 정책을 보존한다.

---

# 11. 모듈 3 – 범주형 데이터 분석

범주형 분석은 원자료와 요약자료를 모두 고려해야 한다.

- 원자료: 행별 binary/category 값
- 요약자료: event count와 trial count

요약자료는 데이터셋 없이 입력할 수 있지만 결과 매니페스트에 사용자가 입력한 집계값과 입력 모드를 기록한다.

## 11.1 1-Proportion (`categorical.one_proportion`)

현재 구현 상태: `categorical.one_proportion`는 available 상태다. SciPy 1.15.3 `stats.binomtest`를 사용해 canonical rows에서 하나의 이진 반응 컬럼과 명시적 `event_level`을 exact binomial test로 비교한다. 결과는 complete-case 제외 수, event/non-event count, 표본 비율, `p - p0`, Wilson score 또는 Clopper-Pearson CI, p-value, Cohen h, `analysis_row_snapshot` provenance, result SHA-256 persistence를 포함한다. event/trial summary-count 직접 입력은 아직 구현하지 않는다. 상세 계약은 `docs/one_proportion_method_contract.md`를 따른다.

### 입력

- binary 변수와 event level
- 기준 비율 `p0`
- 대립가설, alpha
- 신뢰수준과 CI 방식

### 기본 출력

- event, total, sample proportion
- exact binomial test를 기본 검정으로 제공
- Wilson score CI를 기본 CI로 제공
- Clopper–Pearson exact CI 선택
- 차이 `p - p0`

normal approximation 사용 시 적합 조건과 실제 방식을 표시한다.

현재 slice에서는 normal approximation을 제공하지 않는다.

## 11.2 2-Proportion (`categorical.two_proportion`)

현재 구현 상태: `categorical.two_proportion`는 available 상태다. SciPy 1.15.3 `stats.fisher_exact`를 사용해 canonical rows에서 하나의 이진 반응 컬럼, 정확히 2수준 group, 명시적 `event_level`을 Fisher exact 2-proportion test로 비교한다. 결과는 complete-case 제외 수, 그룹별 event/non-event count, proportion difference, Newcombe-Wilson CI, p-value, risk ratio, odds ratio, `analysis_row_snapshot` provenance, result SHA-256 persistence를 포함한다. 두 그룹의 summary event/trial 직접 입력은 아직 구현하지 않는다. 상세 계약은 `docs/two_proportion_method_contract.md`를 따른다.

### 입력

- 현재 slice: dataset-backed binary response + 정확히 2수준 group
- event level 명시
- complete-case missing handling
- alternative, alpha, confidence level 명시

### 출력

- 그룹별 event, total, proportion
- proportion difference와 Newcombe-Wilson CI
- risk ratio, odds ratio와 지원 가능한 경우의 CI
- Fisher exact p-value
- 2x2 table
- N/exclusions, warnings, provenance

희소 2x2에서는 Fisher exact를 선택 가능하게 하고, 앱이 자동 변경한다면 사전점검에서 명확히 동의를 받는다. 무음 fallback은 금지한다.

현재 slice에서는 Fisher exact를 명시적 기본 검정으로 사용하며 두 그룹의 summary event/trial 입력, 자동 event level 추론은 제공하지 않는다.

## 11.3 Chi-square Test for Association (`categorical.chi_square_association`)

현재 구현 상태: `categorical.chi_square_association`는 available 상태다. SciPy 1.15.3 `stats.chi2_contingency(..., correction=False)`를 사용해 canonical rows에서 두 범주형 컬럼의 Pearson chi-square independence test를 계산한다. 결과는 complete-case 제외 수, observed/expected counts, row/column/total percentages, standardized residuals, chi-square statistic, df, p-value, Cramer's V, expected-count diagnostics, `analysis_row_snapshot` provenance, result SHA-256 persistence를 포함하며, frontend는 standardized residual heatmap을 렌더링한다. sparse 2x2 table은 Fisher exact recommendation만 기록하며 Fisher exact p-value를 계산하거나 자동 fallback하지 않는다. Summary-count contingency table 입력, chart artifact export, Monte Carlo/permutation은 아직 구현하지 않는다. 상세 계약은 `docs/chi_square_association_method_contract.md`를 따른다.

### 입력

- 현재 slice: dataset-backed row categorical column + column categorical column
- complete-case missing handling
- alpha 명시
- 집계 contingency table 입력은 P1
- 구조적 0과 관측 0을 구분할 수 있는 옵션은 P1

### 출력

- observed/expected counts
- row %, column %, total %
- Pearson chi-square, df, p
- Cramér's V와 정의
- standardized residuals
- 기대도수 조건 경고
- 희소 2x2이면 Fisher exact recommendation

여러 셀 residual을 유의성으로 해석할 때 다중비교 보정을 제공한다. 큰 RxC 희소표의 Monte Carlo/permutation은 P1로 둔다.

---

# 12. 모듈 4 – 상관관계 및 회귀분석

## 12.1 Pearson Correlation (`regression.pearson`)

현재 구현 상태: `regression.pearson`는 첫 Gate C1 available slice다. SciPy 1.15.3 `stats.pearsonr`와 Fisher z confidence interval을 사용해 canonical rows에서 두 수치 컬럼의 Pearson product-moment correlation을 계산한다. 결과는 complete-case 제외 수, X/Y sample summary, covariance, r, r-squared, p-value, Fisher z CI, capped raw-string-free scatterplot point payload, non-causation/linearity/outlier warnings, `analysis_row_snapshot` provenance, result SHA-256 persistence를 포함하며, frontend는 scatter payload를 inline SVG 산점도로 렌더링한다. Spearman/Kendall, 별도 scatterplot artifact/export, OLS model fitting, model manifest, prediction은 아직 구현하지 않는다. 상세 계약은 `docs/pearson_method_contract.md`를 따른다.

- 연속 X와 Y 각각 1개
- pairwise complete N
- r, Fisher-z CI, t/df/p
- scatter, 선형 추세선, 선택적 CI band
- 결측, 상수열, 극단 영향점 경고
- 상관을 인과로 표현하지 않음

## 12.2 X–Y Correlation (`regression.xy_correlation`)

현재 구현 상태: `regression.xy_correlation`는 두 번째 Gate C1 available slice다. SciPy 1.15.3 분포 함수를 사용해 canonical rows에서 X 수치 컬럼 집합과 Y 수치 컬럼 집합의 모든 조합을 pairwise Pearson product-moment correlation으로 계산한다. 결과는 각 X/Y 셀별 사용 N, 결측/비숫자 제외 수, r, r-squared, covariance, p-value, Fisher z CI, 셀별 실패 코드, non-causation/linearity/outlier warnings, `analysis_row_snapshot` provenance, result SHA-256 persistence를 포함하며, frontend는 pairwise r 값을 heatmap으로 렌더링한다. pairwise complete-case로 인해 셀마다 N이 달라질 수 있음을 경고한다. Spearman/Kendall, Holm/BH p-value adjustment, scatterplot artifact, OLS model fitting, model manifest, prediction은 아직 구현하지 않는다.

### 제품 정의

여러 X 변수 집합과 여러 Y 변수 집합의 모든 조합을 계산하는 교차 상관 workspace이다. 시계열 lagged cross-correlation이 아니다.

### 입력

- X set: 1개 이상 연속 변수
- Y set: 1개 이상 연속 변수
- missing policy: pairwise complete 기본 또는 공통 complete-case
- correlation method: Pearson P0, Spearman P1
- multiplicity: Holm 또는 Benjamini–Hochberg

### 출력

- X × Y r matrix
- X × Y raw p matrix
- adjusted p matrix
- pairwise N matrix
- 선택 셀의 scatter와 CI

pairwise deletion은 셀마다 N이 달라질 수 있음을 결과에 강조한다. 같은 변수가 양 집합에 중복되면 대각 자기상관을 제외할지 명시한다.

## 12.3 Fit Regression Model (`regression.linear_model`)

현재 구현 상태: `regression.linear_model`은 세 번째 Gate C1 available slice다. Canonical rows에서 숫자형 반응 컬럼 1개와 숫자형/범주형 main-effect 예측 컬럼 1개 이상을 complete-case로 읽고, intercept 포함 OLS 모형을 NumPy/SciPy로 계산한다. 범주형 예측변수는 안전한 term builder에서 첫 정렬 수준을 reference로 하는 treatment coding만 지원한다. 선택된 숫자형 predictor에 대해서는 명시적으로 요청한 2차항과 숫자형×숫자형 interaction을 추가할 수 있다. 결과는 사용 N과 제외 수, model specification, factor reference level, term source column IDs, 계수 estimate/SE/t/p/CI, R², adjusted R², residual standard error, F test, VIF, condition number, residual summary, leverage summary, Cook's distance summary, capped diagnostic points, non-causation/linearity/independence/homoscedasticity/residual-normality/outlier warnings, `analysis_row_snapshot` provenance, result SHA-256 persistence, safe JSON `regression_model_manifest` artifact, prediction basis metadata, `regression_models` metadata row, checksum-validated manifest retrieval, source-model freshness/schema/version 검증을 포함한 prediction preflight, same/cross-dataset predicted mean/CI/PI 계산, checksum-validated NDJSON 전체 행 저장과 paged retrieval, 전체 prediction CSV export, confirmed dataset version catalog/target 선택, 25행 prediction page 표시, inline residual/fitted and leverage/Cook diagnostic charts, 그리고 inline prediction interval chart를 포함한다. 범주형 interaction, factor×numeric interaction, no-intercept, HC3 robust covariance, exported residual/leverage chart artifacts는 아직 구현하지 않는다.

### P0 범위

- 연속 반응 1개
- 연속 predictor와 범주형 factor
- OLS 선형회귀
- main effects
- 사용자 선택 interaction과 2차항
- 명시적 intercept 설정
- HC3 robust covariance 선택

사용자 문자열을 `eval`하거나 무검증 formula로 실행하지 않는다. 안전한 term builder로 design matrix를 만든다.

### 출력

- model specification과 design matrix 열 매핑
- coefficient, SE, t, p, CI
- model summary: R², adjusted R², residual standard error, F test
- ANOVA/decomposition이 정의되는 경우 표 제공
- 잔차 vs fitted
- Q-Q plot
- scale-location
- leverage 및 Cook's distance
- VIF/condition 경고
- 이분산 진단
- ordered data로 지정된 경우에만 순서 관련 진단

### 모델 자산

- 앱이 만든 모델만 `model_id`로 저장
- 외부 pickle/joblib 업로드 금지
- 가능하면 coefficient, encoding, term, category level, scaling/domain을 JSON/배열 기반 안전한 artifact로 저장
- 모델 분석 ID, 데이터 버전, schema hash, 패키지 버전 포함

## 12.4 Predict (`regression.predict`)

### 입력

- `model_id`
- 수동 한 행 또는 데이터셋 버전
- confidence level

### 출력

- fitted/predicted mean
- mean response confidence interval
- individual observation prediction interval
- 원본 식별자를 보존한 batch result

### 검증

- 필수 컬럼, 타입, category level 검증
- 학습 범위 밖 연속값과 새로운 factor level 경고/거부
- 모델이 요구하는 term을 재현
- 데이터 누락이나 category 불일치를 조용히 0으로 인코딩하지 않음

현재 구현 상태: `regression.predict`는 catalog에서 available/dedicated로 표시되고 `/analysis/regression/regression.predict`에서 직접 진입한다. Paged metadata-only regression-model catalog에서 source를 고른 뒤 기존 full model GET으로 checksum과 source dependency를 재검증하며, Linear Model embedded entry와 top-level entry는 같은 `RegressionPredictionPanel` 및 prediction hooks를 사용한다. URL에는 `model_id`와 `target_version_id`만 기록해 reload source selection을 복원한다. Generic `POST /analysis-runs`는 `analysis_method_uses_dedicated_api`로 거부하며 fake result를 만들지 않는다. Preflight는 target mapping/range/category 검증 전에 source analysis 존재·method/version·stale 상태, fit/current source schema hash, source canonical artifact, model metadata와 manifest SHA를 검증한다. Prediction provenance와 config/result/rows/model 관계 검증은 기존 계약을 유지한다.

Prediction target selection, independent reference fixture, browser cross-dataset fit/preflight/predict, paged result retrieval, 그리고 전체 prediction row의 checksum-validated wide CSV export는 현재 구현되어 있다. 다음 prediction 확장은 별도 계약에서 manual single-row input 범위를 먼저 정의해야 한다.

## 12.5 Response Optimizer (`regression.response_optimizer`)

현재 구현 상태: `regression.response_optimizer`는 catalog에서
available/dedicated로 표시되고 top-level Workbench와 `ResponseSurfacePanel`
embedded entry에서 같은 `ResponseOptimizerPanel`을 사용한다. Paged metadata-only
RSM analysis catalog는 source ID, revision, method, eligibility count만 반환하고,
선택 시 기존 design/analysis GET으로 full checksum/dependency를 재검증한다. URL에는
`design_id`와 `analysis_id`만 기록한다. Generic analysis-run은 명시적으로 거부된다.
Backend는 동일 factor
space를 공유하는 최대 8개 response objective를 지원하며, 현재 UI는 방금 적합한
RSM response 하나를 구성한다. method version `0.3.0`, config/result schema `2`,
source-bundle schema `2`, SQLite schema `10`을 사용한다. Source bundle은 exact
RSM analysis와 immutable response revision ID/SHA를 고정하므로 이후 current
response correction이 생성되어도 이전 optimizer restore 의미가 바뀌지 않는다.
실행 전 source RSM의 rank, residual
inference/variance, lack-of-fit, response/checksum dependency를 검사하며 blocking
issue는 recommendation 없이 거부한다. low residual df와 influence/leverage/
normality advisory는 typed warning code를 사용자가 명시적으로 확인해야 하고 그
목록을 config/result에 저장한다. 상세 계약은
`docs/response_optimizer_contract.md`를 따른다.

### 선행 조건

- 검증된 회귀 또는 RSM 모델
- 각 factor의 허용 범위/수준
- 각 response의 목표와 중요도

### 목표 유형

- maximize
- minimize
- target
- within range

### 계산

- response별 desirability 0~1
- 다중 response는 가중 geometric composite desirability
- 실제 factor 단위의 선형 `<=`/`>=` 제약
- CPU budget이 있는 multi-start optimization
- 랜덤 시드와 초기점 기록

### 출력

- 추천 설정
- 각 response point prediction
- 개별/종합 desirability
- 활성 제약, 경계해 여부
- 학습/설계 영역 밖 extrapolation 여부
- 최적해가 전역 최적임을 보장하지 않는다는 제한

원자료에 직접 “최적값”을 제안하지 않는다. 모델 진단이 심각하게 실패했거나 설계영역이 정의되지 않으면 실행을 차단한다.

---

# 13. 모듈 5 – 품질 관리

품질관리 화면은 일반 통계보다 데이터 순서와 공정 맥락에 더 의존한다. 다음을 실행 전에 확인한다.

- 시간/실행 순서
- 합리적 부분군 정의
- 부분군 크기와 변화 여부
- 측정 단위
- 규격하한/상한/목표
- 기준기간(Phase I)과 모니터링기간(Phase II)
- 불량품 수와 결점 수의 구분

현재 구현은 Phase I 기준선 추정과 검증된 고정 한계를 적용하는 Phase II를 모두
지원한다. Phase II는 기준선을 자동 재적합하지 않는다.

## 13.1 Control Chart (`quality.attribute_control_chart`)

중복을 피하기 위해 P0에서 계수형 관리도와 차트 선택 허브를 제공한다.

현재 구현 상태: `quality.attribute_control_chart`는 method version `0.3.0`,
result schema `3`의 available Phase I/II slice다. P/NP는 불량품 수와 양의 정수 표본 크기, C/U는
결점 수와 검사 기회를 명시적으로 구분한다. P와 U는 관측별 분모에 따른
가변 3-sigma 한계, NP는 고정 표본 크기 한계, C는 사용자가 동일 검사
기회를 확인한 뒤 고정 한계를 계산한다. 자연 하한은 0, P/NP 자연 상한은
각각 1과 표본 크기로 절단하고 그 수를 결과에 기록한다. 현재 rule은
관리한계 밖 1점만 지원한다. Pearson dispersion ratio, 작은 Phase I
baseline, 취약한 정규근사, 제외 행, 한계 절단과 신호를 persistent warning으로
남기되 chart나 한계를 자동 교정하지 않는다. Frontend는 P/NP/C/U segmented
선택, C 동일 기회 확인, 관측별 한계 SVG와 결과표를 제공한다. Phase II는
검증된 immutable limit-set asset schema `1`을 사용자가 명시적으로 선택하고,
target schema/canonical dependency preflight를 통과한 뒤에만 frozen center와
한계를 적용한다. Preflight는 구조와 dependency만 확인하며 실제 행 값, 필터 후
usable point 수, NP 표본 크기와 count/denominator 계약은 실행 시 다시 검증한다.
Phase II는 유효 monitoring point 한 개부터 실행할 수 있고, 한 점일 때 Pearson
dispersion은 `available=false`, 자유도 0, ratio null로 보존한다. 기존
`0.1.0`/schema 1과 `0.2.0`/schema 2 결과는 저장 당시 의미로만 복원한다.
NP sample size와 C current opportunity 확인을 별도로 강제하며 target 행에서
한계를 재추정하지 않는다. 공통 stored result/row snapshot 및 JSON/CSV/HTML
export는 limit-set/target 관계를 다시 검증한다. chart image export는 아직
지원하지 않는다. 상세 계약은
`docs/attribute_control_chart_method_contract.md`와
`docs/attribute_control_chart_phase_2_contract.md`를 따른다.

| 차트 | 데이터 | 기본 용도 |
| --- | --- | --- |
| P chart | 불량품 수 / 표본크기 | 표본크기가 변할 수 있는 불량률 |
| NP chart | 불량품 수 | 일정 표본크기의 불량품 수 |
| C chart | 결점 수 | 일정 검사기회의 결점 수 |
| U chart | 결점 수 / 검사기회 | 검사기회가 변하는 단위당 결점 |

### 출력

- center line, UCL, LCL
- LCL의 자연스러운 0 truncation 표시
- 각 점의 분모/기회
- 규칙 위반점과 rule ID
- 제외 또는 baseline 설정

불량품(defective)과 결점(defect)을 UI에서 구분하고 잘못된 차트 선택을 경고한다.

## 13.2 Variables Charts for Individuals (`quality.individuals_chart`)

현재 구현 상태: `quality.individuals_chart`는 Gate D I-MR available slice다. Canonical rows에서 숫자형 측정값 컬럼 1개를 complete-case로 읽고, 기본값은 canonical row order를 실행 순서로 사용한다. 사용자가 숫자형 또는 날짜시간 순서 컬럼을 선택하면 해당 컬럼을 오름차순으로 정렬하고 같은 순서값은 canonical row position으로 안정 정렬한다. 날짜시간 순서 컬럼은 ISO 8601과 profile preflight의 대표 날짜/시간 형식을 지원하며, timezone-aware 값은 UTC 기준으로 비교하고 aware/naive 혼합은 거부한다. I chart는 산술평균 중심선과 `MRbar / d2` 기반 3-sigma 관리한계를 계산하고, MR chart는 인접 moving range 길이 2와 `D3=0`, `D4=3.267` 한계를 계산한다. 현재 explicit rule은 I chart 3-sigma 밖 점, MR chart UCL 초과 점, I chart 중심선 한쪽 연속 9점, I chart strict 연속 6점 증가/감소, I chart 연속 14점 교대 상승/하락, I chart 2-of-3 beyond 2-sigma, I chart 4-of-5 beyond 1-sigma, I chart 15-within-1-sigma, I chart 8-outside-1-sigma를 포함한다. 중심선과 같은 값은 same-side run을 끊고, 같은 adjacent 값은 trend/alternating run을 끊는다. 2-of-3 및 4-of-5 zone rule chart marker는 해당 sigma threshold를 실제로 넘은 점에만 붙이고, 15-within/8-outside pattern rule marker는 qualifying window의 모든 점에 붙인다. 모든 signal payload는 평가 window의 시작/끝을 기록한다. 모든 moving range가 0인 상수열은 `individuals_chart_zero_moving_range`로 거부하고 fake limit을 만들지 않는다. Frontend는 inline SVG I/MR chart, value/order selectors, signal table을 렌더링한다. Full Nelson/Western Electric rule set, subgroup charts, chart export artifact는 아직 구현하지 않는다. 상세 계약은 `docs/individuals_chart_method_contract.md`를 따른다.

P0는 I-MR chart이다.

- 개별 관측 순서 필수
- moving range 길이 2 기본
- Individuals와 Moving Range를 함께 표시
- 추정 sigma 방식과 상수 버전을 provenance에 기록
- 누락 또는 중복 순서 처리 명시
- 사용자가 지정한 baseline 제외점은 기록하고 원자료를 삭제하지 않음

## 13.3 Variables Charts for Subgroups (`quality.subgroup_chart`)

현재 구현 상태: `quality.subgroup_chart`는 Gate D Xbar-R/Xbar-S fixed-subgroup available slice다. Canonical rows에서 숫자형 측정값 컬럼 1개와 부분군 ID 컬럼 1개를 complete-case로 읽고, 부분군은 canonical row에서 처음 나타난 순서로 표시한다. 이번 slice는 모든 부분군 크기가 같아야 하며 subgroup size 2-10의 표준 `A2/D3/D4` Xbar-R 상수와 `A3/B3/B4` Xbar-S 상수를 지원한다. Xbar-R은 부분군 평균의 평균을 중심선으로, `Xbarbar +/- A2 * Rbar`를 Xbar 관리한계로 계산하고, R chart는 `D3 * Rbar`와 `D4 * Rbar`를 관리한계로 계산한다. Xbar-S는 부분군 표본표준편차(`n - 1`) 평균 `Sbar`를 사용해 `Xbarbar +/- A3 * Sbar`, `B3 * Sbar`, `B4 * Sbar`를 계산한다. 현재 rule은 Xbar/R/S chart에서 관리한계 밖 1점 신호만 구현한다. 부분군 크기가 섞이면 `subgroup_chart_varying_subgroup_size_unsupported`, 평균 부분군 범위가 0이면 `subgroup_chart_zero_average_range`, 평균 부분군 표본표준편차가 0이면 `subgroup_chart_zero_average_stddev`로 거부하고 fake limit을 만들지 않는다. Frontend는 Xbar-R/Xbar-S 선택, inline SVG Xbar/R/S chart, value/subgroup selectors, signal table을 렌더링한다. Varying subgroup-size limits, full Nelson/Western Electric rule set, capability analysis, Gage R&R, chart export artifact는 아직 구현하지 않는다. 상세 계약은 `docs/subgroup_chart_method_contract.md`를 따른다.

P0 범위:

- X-bar & R
- X-bar & S

입력:

- 연속 측정값
- subgroup ID
- subgroup 내 관측
- optional order/time

사전점검:

- subgroup size 분포
- singleton subgroup
- 비연속 순서
- varying subgroup size
- 합리적 부분군 여부는 사용자 확인

고정 크기 부분군을 우선 구현하고 varying size의 정확한 한계는 검증 후 P1로 확장할 수 있다. 관리도 상수는 코드에 출처와 테스트를 둔다.

## 13.4 공통 관리도 규칙

P0 최소 규칙은 다음으로 제한하고 정확히 이름 붙인다.

1. 1점이 3 sigma 한계 밖
2. 연속 3점 중 2점이 같은 쪽 2 sigma 밖
3. 연속 5점 중 4점이 같은 쪽 1 sigma 밖
4. 연속 8점이 중심선 같은 쪽

전체 Nelson/Western Electric rule set은 P1에서 추가한다. 규칙 적용 여부와 기준 window를 결과에 저장한다.

## 13.5 Run Chart (`quality.run_chart`)

현재 구현 상태: `quality.run_chart`는 Gate D available slice다. Canonical rows에서 숫자형 측정값 컬럼 1개를 complete-case로 읽고, 기본값은 canonical row order를 x축으로 사용한다. 사용자가 숫자형 또는 날짜시간 순서 컬럼을 선택하면 해당 컬럼을 오름차순으로 정렬하고 같은 순서값은 canonical row position으로 안정 정렬한다. 날짜시간 순서 컬럼은 ISO 8601과 profile preflight의 대표 날짜/시간 형식을 지원하며, timezone-aware 값은 UTC 기준으로 비교하고 aware/naive 혼합은 거부한다. Median 중심선, above/below median run count, tie-to-median 제외 정책, 명시 정의된 strict 6-point monotonic trend signal, strict 14-point oscillation signal, 그리고 median 위/아래 run count의 exact 조건부 분포에 기반한 clustering/mixture signal을 계산한다. 결과는 `analysis_row_snapshot` provenance와 result SHA-256 persistence를 사용하며, frontend는 inline SVG run chart와 run/signal table을 렌더링한다. Control limits는 계산하지 않으며, trend/oscillation/clustering/mixture signal을 관리도 out-of-control 신호로 표현하지 않는다. Chart export artifact는 아직 구현하지 않는다. 상세 계약은 `docs/run_chart_method_contract.md`를 따른다.

- x: 순서 또는 시간
- y: 측정값
- center: median 기본
- control limits 없음
- runs above/below median
- trend, clustering, mixture, oscillation 신호는 구현된 정의를 명시
- median과 같은 tie 처리 방식을 기록

Run Chart의 신호를 관리도 out-of-control과 같은 것으로 표현하지 않는다.

## 13.6 Capability Analysis (`quality.capability`)

현재 구현 상태: `quality.capability`는 Gate D normal capability first slice다. Canonical rows에서 숫자형 측정값 컬럼 1개를 complete-case로 읽고, 사용자가 LSL 또는 USL 중 최소 하나와 optional target을 입력한다. 첫 slice는 정규모형 기반 capability point estimate만 계산한다. Overall sigma는 sample standard deviation(`ddof=1`), within sigma는 canonical row 순서의 인접 moving range 평균 `MRbar / d2`(`d2=1.128`)로 추정한다. 양측 spec이면 Cp/Cpk와 Pp/Ppk의 two-sided/lower/upper/min-side 지수를 계산하고, 한쪽 spec이면 양측 지수는 `null`로 두며 사용 가능한 side index만 계산한다. 관측 비규격 count/proportion/ppm과 정규모형 기대 비규격 probability/ppm, histogram bin payload와 fitted normal density를 반환한다. Frontend는 LSL/USL/target 입력, inline SVG histogram + normal curve + spec lines, capability index table, observed/expected nonconformance table을 렌더링한다. 공정 안정성, 정규모형 적합성, 측정시스템 적합성은 자동 보증하지 않고 persistent warning으로 남긴다. Cpm, confidence interval, non-normal capability, Box-Cox/Johnson 변환, subgroup pooled sigma, chart export artifact는 아직 구현하지 않는다. 상세 계약은 `docs/capability_method_contract.md`를 따른다.

### P0 범위

- 연속 반응
- Normal capability
- 양측 또는 한쪽 spec
- Cp, Cpk: within sigma 기반
- Pp, Ppk: overall sigma 기반
- 관측/예상 비규격 비율
- histogram + fitted distribution + spec lines

### 필수 입력

- LSL 및/또는 USL
- optional target
- subgroup 또는 individuals sigma 추정 방식
- 단위

### 필수 경고

- 공정이 안정되지 않으면 capability 지수의 장기 해석이 부적절함
- spec limits와 control limits가 다름
- 데이터가 정규모형에 부적합할 수 있음
- 측정시스템이 불충분하면 capability도 왜곡될 수 있음

Cpm, 비정규 분포 capability, Box-Cox/Johnson 변환, bootstrap CI는 P1로 둔다. CI가 없는 point estimate만 제공한다면 결과에 제한을 명시하고 출시 기준에서 재검토한다.

## 13.7 Gage R&R Study (`quality.gage_rr`)

현재 구현 상태: `quality.gage_rr`는 balanced crossed ANOVA first slice로 실행 가능하다. `POST /api/v1/quality/gage-rr/preflight`는 canonical rows를 읽어 측정값, 부품, 측정자, 반복 컬럼의 balanced crossed 설계 준비 여부를 사전점검하고, `POST /api/v1/analysis-runs`는 같은 역할 컬럼으로 실제 Gage R&R ANOVA를 실행한다. 실행 결과는 row snapshot provenance와 함께 저장되며 `GET /api/v1/analysis-runs/{analysis_id}/result`로 checksum 검증 후 재조회된다. 결과 payload는 ANOVA table, raw/final variance components, repeatability, reproducibility, total Gage R&R, part-to-part, total variation, % contribution, % study variation, ndc, negative variance component clamp policy, interaction no-pooling policy를 포함한다. 원문 part/operator/replicate label은 preflight와 result payload 모두에서 반환하지 않는다. Nested, unbalanced, expanded Gage R&R, tolerance/process variation, component/interaction plot, pooling 선택 UI는 아직 구현하지 않는다. Gage Run Chart는 별도 `quality.gage_run_chart` method로 구현한다. 상세 계약은 `docs/gage_rr_preflight_contract.md`와 `docs/gage_rr_method_contract.md`를 따른다.

### P0 설계

- crossed study
- balanced design
- multiple parts, operators, replicates
- ANOVA variance-components 방식

### 역할

- measurement
- part ID
- operator ID
- replicate 또는 반복 순서
- optional tolerance/process variation

### 모델 요소

- part
- operator
- part × operator
- repeatability/error

### 출력

- 설계 균형성과 셀별 반복 수
- ANOVA table
- raw와 최종 variance components
- repeatability, reproducibility, total Gage R&R, part-to-part, total variation
- % contribution
- % study variation
- tolerance가 있으면 % tolerance
- process variation이 있으면 해당 비교
- number of distinct categories(ndc)와 계산 정의
- component/interaction plots

음수 variance component는 조용히 숨기지 않는다. 최종 보고에서 0으로 제한한다면 raw estimate, 제한 정책 및 경고를 함께 남긴다.

part×operator interaction을 pooling하는 옵션은 명시적으로 설정하고 임계값을 기록한다. 기본은 상호작용을 보존하는 방향으로 시작한다.

Nested, unbalanced, expanded Gage R&R은 P1/P2이다.

## 13.8 Gage Run Chart (`quality.gage_run_chart`)

현재 구현 상태: `quality.gage_run_chart`는 balanced crossed 측정시스템 설계의 first slice로 실행 가능하다. `POST /api/v1/analysis-runs`는 canonical rows와 common row snapshot을 사용해 측정값, 부품, 측정자, 반복 컬럼을 검증하고, 선택적 order 컬럼 또는 canonical row order로 진단 chart payload를 만든다. 결과는 usable/excluded row counts, balanced design counts, 전체/부품/측정자 요약, capped point payload, warning metadata, row snapshot provenance, result SHA-256 persistence를 포함한다. 원문 part/operator/replicate label은 반환하지 않고 index만 반환한다. 상세 계약은 `docs/gage_run_chart_method_contract.md`를 따른다.

P0 범위:

- x: optional numeric/datetime run order 또는 canonical row order
- y: numeric measurement
- color/series: operator index
- symbol/point variation: replicate index
- 부품별/측정자별 평균과 범위 요약
- balanced crossed design 검증
- raw part/operator/replicate label redaction

현재 first slice는 Gage R&R 분산성분 결과를 대체하지 않는다. 데이터가 Gage 설계와 연결되지 않으면 단순 run chart로 자동 변경하지 않는다. Component/interaction plot, part/operator faceting, exported chart artifacts, paged high-volume chart payload는 후속 slice에서 별도 계약과 테스트를 추가한 뒤 구현한다.

---

# 14. 모듈 6 – 실험 계획법

DOE는 업로드된 데이터에 분석만 수행하는 모듈이 아니다. **설계 생성 → 랜덤화 → 실행표 내보내기 → 반응 입력/가져오기 → 모델 적합 → 진단/최적화**의 자산 생명주기가 필요하다.

## 14.1 공통 DOE 자산

```json
{
  "design_id": "uuid",
  "design_version": 1,
  "family": "two_level_full_factorial",
  "factors": [],
  "blocks": 1,
  "replicates": 1,
  "center_points": 0,
  "randomization_seed": 20260623,
  "status": "designed"
}
```

상태 예시:

```text
draft → designed → randomized → responses_in_progress → completed → analyzed
```

반응값 입력 후에는 기존 run order를 재생성하거나 factor level을 덮어쓰지 않는다. 변경은 새 design version으로 만든다.

## 14.2 Design of Experiments (`doe.factorial_design`)

현재 구현 상태: Gate D1 2-level full factorial 설계, immutable response revision/history, 효과/OLS/ANOVA 분석 slice가 구현되어 있다. `doe.factorial_design` v0.3.0은 catalog에서 available이지만 일반 분석 실행 API가 아니라 dedicated design/response-revision/analysis/report routes를 사용한다. Response revision schema 1과 analysis envelope/config schema 2는 정확한 revision ID/number/SHA를 고정하며 calculation result schema는 1을 유지한다. SQLite schema 10은 ordered values, current head, analysis-revision 관계를 저장하고 schema-v9 current response는 저장 결과를 다시 쓰지 않고 deterministic revision 1로 backfill한다. 2-6개 연속 factor, 반복, center point, fixed block, deterministic randomization, standard/run order, design/response/result checksum, -1/+1 coding, hierarchy 고정 interaction, curvature, block effects, partial drop-one SS, pure error/lack-of-fit, residual/influence diagnostics, main/interaction plot payload, Workbench current/history/correction UI와 HTML report를 지원한다. Fractional factorial alias analysis, optimizer, chart image export는 아직 구현하지 않는다. 상세 계약은 `docs/factorial_design_method_contract.md`와 `docs/doe_response_revision_contract.md`를 따른다.

### P0 설계 생성

- 2-level full factorial
- 연속 factor 우선
- factor name, unit, low, high
- replicate
- center point
- optional block
- randomization on/off와 seed
- standard order와 run order 동시 보존

초기 CPU/화면 한도를 위해 factor 수와 총 run 수에 명시적 제한을 둔다. 제한은 설정값이며 무음 축약하지 않는다.

### P1 설계

- fractional factorial
- generator와 resolution
- alias structure
- Plackett–Burman screening
- general full factorial

### 분석 P0

- coded와 uncoded coefficient
- main effects와 선택 interaction
- hierarchy 원칙
- ANOVA
- effect estimates와 CI
- Pareto chart of standardized effects
- main effects plot
- interaction plot
- residual diagnostics
- replicate가 있을 때 pure error와 lack-of-fit

자동 backward elimination을 기본으로 하지 않는다. term 제거는 설계 alias와 hierarchy를 고려한 명시적 동작이어야 한다.

## 14.3 Response Surface Method (`doe.response_surface`)

현재 구현 상태: Gate D2의 RSM 및 bounded optimizer slice가 구현되어 있다. `doe.response_surface` v0.2.0 전용 API에서 2-5개 연속 factor의 CCD를 생성하며 새 design schema 2는 family를 `central_composite`로 저장하고 rotatable/face-centered geometry는 `alpha_mode`로 구분한다. 기존 schema-1 `central_composite_inscribed` payload는 원래 family/mode/SHA를 유지해 복원한다. Response revision schema 1과 analysis envelope/config schema 2는 exact historical response revision을 고정하며 calculation result schema는 1을 유지한다. 분석 후 참조 revision은 API/UI 모두 read-only이고 잘못 입력한 값을 고칠 때는 current revision을 supersede하는 새 revision을 생성한다. coefficient inference, partial drop-one ANOVA, pure error/lack-of-fit, residual/influence diagnostics, Hessian stationary-point 분류와 axial/factorial 영역 판정, 첫 두 factor의 21x21 contour payload, Workbench current/history/correction UI, SQLite schema-10 checksum/dependency 저장을 지원한다. 적합 후 같은 화면에서 source-model eligibility gate를 통과한 경우에만 maximize/minimize/target/range desirability, 좁힌 factor bounds, 선형 부등식 제약, deterministic search budget을 사용하는 `regression.response_optimizer` v0.3.0을 실행하고 검증된 결과를 복원할 수 있다. 상세 revision/분석/optimizer 계약은 `docs/doe_response_revision_contract.md`, `docs/response_surface_method_contract.md`, `docs/response_optimizer_contract.md`를 따른다.

### P0

- Central Composite Design(CCD)
- face-centered 또는 rotatable 옵션
- 실제 안전경계 low/high와 파생 center
- axial/center point
- randomization seed
- 2차 회귀모형: linear + interaction + square
- contour plot
- residual diagnostics
- stationary point/eigen 분석과 설계영역 판정

### P1

- Box–Behnken
- orthogonal CCD 옵션
- block
- ridge analysis
- sequential augmentation
- surface perspective plot
- multi-response objective builder 확장

### 입력/출력 규칙

- contour/surface에서 표시하지 않는 factor의 고정값을 명시
- 설계영역 밖 예측을 기본 optimizer 후보에서 제외
- 2차항이 포함되면 hierarchy를 유지
- replicate가 없으면 lack-of-fit 검정 불가 경고
- 단일 최적점 외에 주변 민감도와 feasible region을 제공

### 초기 제외 범위

- mixture designs
- split-plot
- optimal/custom designs
- covariate-adjusted DOE
- Bayesian adaptive experimentation

이 기능들은 일반 factorial/RSM과 데이터 구조가 크게 달라 별도 P2 설계를 요구한다.

---

## 15. 추가해야 할 목적 모듈 및 후속 기능

사용자 목록에는 없지만 통계적으로 완결된 제품을 위해 다음을 backlog에 명시한다.

| 기능 | 이유 | 권장 우선순위 |
| --- | --- | --- |
| Paired t-Test | 반복/짝 자료를 독립표본으로 오용하지 않기 위해 필요 | P0 추가 |
| Paired Wilcoxon | 짝 자료의 비모수 대안 | P1 |
| Spearman/Kendall | 비선형 단조·순서자료 상관 | P1 |
| Power/Sample Size | 동등성, 비율, DOE 계획에 중요 | P1 |
| Multiple Linear Regression term builder | DOE/RSM과 일반 회귀 공통 기반 | P0 |
| Robust regression/robust CI | 영향점에 민감한 OLS 보완 | P2 |
| Measurement Bias/Linearity/Stability | Gage R&R만으로 측정시스템 전체 평가 불가 | P1 |
| Attribute Agreement Analysis | 범주 판정 측정시스템 | P2 |
| Non-normal Capability | 제조데이터에서 빈번 | P1 |
| Time-series/Autocorrelation handling | SPC의 독립성 위반 대응 | P1/P2 |
| Units and metadata | 규격·DOE·공정 결과 해석에 필수 | P0 기반 |
| Statistical glossary | 비전문가의 방법 오용 방지 | P0/P1 |
| Method recommendation guide | 정답 자동선택이 아닌 근거·대안 제공 | P1 |

---

## 16. 의존성 도입 계획

현재 backend에는 통계 계산 의존성이 없다. Gate B0에서 Windows/Python 3.10 compatibility spike를 먼저 수행한다.

### 16.1 후보군

- NumPy 2.2 계열 후보
- pandas 2.3 계열 후보
- SciPy 1.15 계열 후보
- statsmodels 0.14.6 후보
- openpyxl 3.1 계열
- pyarrow: Python 3.10 Windows wheel이 검증된 버전
- pyDOE3 1.6 계열: DOE 설계 생성 후보

위 버전은 최종 pin이 아니라 **호환성 검증 후보**다. Codex는 다음을 확인한 후 exact pin과 lockfile을 커밋한다.

1. Python 3.10 설치 성공
2. Windows wheel 존재
3. CPU-only import와 smoke calculation
4. NumPy/SciPy/pandas/statsmodels ABI 조합
5. 라이선스
6. offline runtime
7. startup/memory 영향
8. CI full check

### 16.2 라이브러리 역할

- SciPy: 기초 검정과 분포
- statsmodels: 회귀, 다중비교, 일부 진단 및 TOST
- pandas/NumPy: 데이터 처리와 수치 배열
- pyDOE3: 설계 행렬 생성 후보
- 품질관리 계산: 공식을 직접 검증 가능한 작은 모듈로 구현하되 출처·상수·테스트를 명시

하나의 편의 라이브러리에 결과 전체를 위임하고 내부 방법·버전을 숨기지 않는다. Pingouin, 대형 AutoML, GPU 패키지는 이 단계의 필수 의존성이 아니다.

### 16.3 frontend 후보

- router
- server-state query library
- typed form/validation
- Plotly 계열 chart renderer
- 접근 가능한 table/virtualization

모든 dependency는 React 18, 현재 Node LTS/CI, TypeScript strict, 오프라인 번들, 라이선스를 확인한다.

---

## 17. 테스트 및 수치 검증 전략

### 17.1 모든 메서드의 최소 테스트 세트

1. 손계산 가능한 작은 fixture
2. 독립적으로 검증된 reference fixture
3. 결측/빈 그룹/상수열/NaN/Inf
4. 최소 N과 큰 N
5. ties/zero/sparse cells
6. 결과 수치 허용오차
7. 경고 코드와 N/제외 메타데이터
8. JSON serialization round trip
9. 동일 데이터·옵션의 결정적 결과
10. Windows path와 한글 컬럼명

snapshot만으로 통계 정확성을 검증하지 않는다.

### 17.2 모듈별 추가 테스트

- t/ANOVA: Welch df, pooled 분기, post-hoc 보정
- TOST: 경계 내부/외부/한쪽만 통과
- Wilcoxon/Mann-Whitney: tie와 zero, exact/asymptotic
- 비율/카이제곱: 희소표, event level, expected counts
- 회귀: singular matrix, categorical coding, interaction hierarchy, extrapolation
- 관리도: 알려진 상수, 각 rule 위반 위치, Phase I baseline
- Capability: within/overall sigma와 one-sided spec
- Gage R&R: balanced crossed fixture, variance component, ndc, 음수 component 정책
- DOE: run 수, randomization 재현, coded value, alias structure
- RSM: CCD point, quadratic coefficient, contour grid, optimizer bounds

### 17.3 reference provenance

fixture마다 다음을 기록한다.

- 데이터 생성 또는 공개 출처
- 참조 소프트웨어/버전
- 참조 옵션과 반올림 전 결과
- 허용오차 근거
- 검증 날짜

특정 상용 소프트웨어와의 화면/반올림 일치를 “통계적 정답”으로 간주하지 않는다. 상용 도구 호환성이 제품 요구라면 별도 acceptance matrix를 만든다.

### 17.4 E2E 핵심 경로

- 업로드 → 파싱 확정 → schema → 탐색 통계 → 결과 저장
- 2표본 t → preflight → 실행 → report export
- 범주형 event level 선택 → 2-proportion
- 회귀 적합 → model 저장 → 새 데이터 예측
- ordered data → I-MR → rule violation
- Gage 데이터 → Gage R&R → Gage Run Chart
- DOE 생성 → 랜덤화 → response 입력 → 분석
- RSM → contour → response optimizer

---

## 18. 변경된 단계별 개발 로드맵

## Gate B0 – 분석 플랫폼 계약

### 구현

- 파싱 확정 API와 canonical dataset version
- schema/measurement level/unit 확인
- rows pagination과 데이터셋 Context Bar
- SQLite migration: versions, columns, analysis runs, artifacts, jobs
- method registry와 6개 top navigation
- 공통 analysis request/result/warning/provenance schema
- frontend router, query, form, chart 기반 선택
- 통계 dependency compatibility spike와 lock
- stale backend README 수정

### 첫 실제 구현 PR 범위

Gate B0은 여러 PR로 쪼갠다. 첫 실제 구현 PR은 현재 working tree에 구현되어 있으며 다음만 포함한다.

1. 업로드 파싱 확정 request/response schema와 API
2. delimited text 업로드의 불변 `dataset_version` 생성
3. `dataset_columns` migration
4. dataset version 조회 API
5. 업로드, 파싱 확정, 버전 상태 및 컬럼 메타데이터 표시 UI의 최소 경로

첫 PR에서 통계 메서드 계산, analysis mock result, fake chart/table result, 6개 모듈 전체 라우팅 구현은 금지한다.

Gate B0 second slice도 현재 working tree에 구현되어 있다. Gate B0 third slice의 registry/navigation 부분과 storage/run foundation도 현재 working tree에 구현되어 있다. Canonical JSONL rows/manifest materialization과 `dataset_artifacts` schema v5가 구현되어 있다. Profile과 첫 `eda.descriptive` analysis row source는 validated canonical rows로 전환되어 있으며, artifact 손상/누락 시 raw fallback 없이 명시 오류를 반환한다. Basic profile/preflight API/UI는 aggregate counts, warnings, duplicate-row count, memory estimate, date/time format/timezone preflight, persisted `profile_summary` artifact 범위로 구현되어 있고, frontend rendering은 `AppChrome`, `useDatasetWorkflow`, split dataset-preparation components, 그리고 `datasetDisplay` helper로 분리되어 있다. Six-module Workbench는 path-restorable selected-method shell, legacy hash fallback, route-selected analysis page rendering through `WorkspaceRouter`, split `AnalysisPage`/`AnalysisShell`/`AnalysisWorkbench`/`DescriptiveAnalysisPanel`/`GraphicalSummaryPanel`/`NormalityAnalysisPanel`/`EqualVariancesPanel`/`OneSampleTPanel`/`PairedTPanel`/`EquivalenceTostPanel`/`OneSampleWilcoxonPanel`/`TwoSampleTPanel`/`MannWhitneyPanel`/`KruskalWallisPanel`/`OneWayAnovaPanel`/`OneProportionPanel`/`TwoProportionPanel`/`ChiSquareAssociationPanel`/`PearsonCorrelationPanel`/`XyCorrelationPanel` components, `useAnalysisSelection` route state, 30개 method-specific guidance 범위로 구현되어 있다. Gate B1 slice로 `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, `eda.equal_variances`가 실제 계산, API 실행, result JSON persistence, 최소 UI 결과 테이블까지 구현되어 있다. Gate B2 slice로 `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`, `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, `categorical.chi_square_association`가 각각 명시적 기준 평균 1표본 t-검정, wide 전/후 측정 컬럼 대응표본 t-검정, 명시적 기준 위치 1표본 signed-rank, Welch 기본/명시적 pooled 2표본 t-검정, 독립 2그룹 Mann-Whitney U, 독립 3그룹 이상 Kruskal-Wallis와 유의 시 Dunn/Holm 사후비교, 표준 일원배치 ANOVA와 유의 시 Tukey-Kramer 사후비교, 1표본 평균 TOST, 이진 반응 컬럼의 1-비율 exact binomial test, 이진 반응/정확히 2그룹의 Fisher exact 2-비율 test, 두 범주형 컬럼의 Pearson chi-square independence test, p-value, effect size, row snapshot provenance, persisted result retrieval, 최소 UI 결과 테이블 범위로 구현되어 있다. Gate C1 첫 slice로 `regression.pearson`이 두 수치 컬럼 Pearson product-moment correlation, Fisher z CI, p-value, covariance/r-squared, non-causation warnings, row snapshot provenance, persisted result retrieval, 최소 UI 결과 테이블 범위로 구현되어 있다. Gate C1 두 번째 slice로 `regression.xy_correlation`이 X/Y 수치 컬럼 집합의 pairwise Pearson 상관행렬, 셀별 N/제외 수, r/r-squared/covariance, p-value, Fisher z CI, 셀별 실패 코드, row snapshot provenance, persisted result retrieval, 최소 UI 결과 테이블 범위로 구현되어 있다. Gate C1 세 번째 slice로 `regression.linear_model`이 OLS main-effect/selected-term fitting, diagnostics, row snapshot provenance, persisted result retrieval, safe JSON model manifest storage, checksum-validated model manifest retrieval, stored-model prediction preflight, and backend app-created OLS prediction 범위로 구현되어 있다. `analysis_row_snapshot` artifact 저장, 제한된 non-empty filter expression engine, 그리고 Workbench-level frontend filter controls도 구현되어 있으며, 실제 실행 payload 연결은 네 개 current EDA method와 `hypothesis.one_sample_t`/`hypothesis.paired_t`/`hypothesis.one_sample_wilcoxon`/`hypothesis.two_sample_t`/`hypothesis.mann_whitney`/`hypothesis.kruskal_wallis`/`hypothesis.one_way_anova`/`hypothesis.equivalence_tost`/`categorical.one_proportion`/`categorical.two_proportion`/`categorical.chi_square_association`/`regression.pearson`/`regression.xy_correlation`/`regression.linear_model`에 적용된다.

### 종료 기준

- 업로드한 파일이 불변 v1로 물질화되고 재시작 후 동일 schema/hash로 열린다.
- 6개 상단 탭이 URL과 keyboard navigation으로 동작한다.
- 미구현 메서드는 계획됨으로 표시되고 실행되지 않는다.
- synthetic dummy가 아닌 최소 reference 계산 하나가 공통 run 계약을 통과한다.
- Windows full check가 통과한다.

## Gate B1 – 탐색적 분석

- descriptive
- graphical summary
- normality
- equal variances
- 공통 chart/table/result 컴포넌트

**종료 기준:** 4개 메서드의 reference·edge·E2E 테스트와 결과 내보내기가 통과한다.

## Gate B2 – 가설 및 범주형 분석

- one-sample/paired/two-sample t
- one-way/Welch ANOVA와 대응 post-hoc
- TOST
- Wilcoxon, Mann-Whitney, Kruskal-Wallis
- 1/2 proportion, chi-square/Fisher

**종료 기준:** 설계 유형 오용을 preflight에서 차단하고 모든 추론 결과가 N, CI, 효과크기, 가정, 경고를 제공한다.

## Gate C1 – 상관·회귀·예측

- Pearson
- X–Y matrix
- safe OLS term builder
- diagnostics
- safe model asset
- predict

**종료 기준:** 모델 schema drift와 extrapolation을 탐지하고 저장 모델 재현 테스트가 통과한다.

## Gate C2 – 기본 품질관리

- attribute P/NP/C/U
- I-MR
- X-bar/R 및 X-bar/S
- run chart
- normal capability
- 공통 rule engine

**종료 기준:** reference control limits와 rule violation index가 허용오차 내 일치하며 spec/control limits를 구분한다.

## Gate C3 – 측정시스템 분석

- balanced crossed Gage R&R
- variance components
- Gage Run Chart

**종료 기준:** reference fixture의 component와 ndc가 검증되고 unbalanced/nested 입력은 정확한 오류 또는 계획됨 상태를 반환한다.

## Gate D1 – Factorial DOE

- 현재 완료된 slice: 2-level full factorial design/immutable response revision/analysis metadata, deterministic randomization, schema v7-v10 storage, dedicated design/current-history-correction/analysis/report API, 효과/OLS/ANOVA/pure error/lack-of-fit/diagnostics, Workbench 결과와 revision history UI.
- design asset/version
- 2-level full factorial
- randomization/block/replicate/center
- response import/storage
- effects/OLS/ANOVA/diagnostics

**종료 기준:** 동일 seed가 동일 run order를 만들고 response 입력 후 설계가 불변이며 reference effect를 재현한다.

## Gate D2 – RSM 및 최적화

- 현재 완료: CCD, full quadratic model, contour payload, residual diagnostics,
  design-region validation, bounded response optimizer, desirability,
  deterministic search budgets, checksum/provenance storage
- 후속 후보: surface perspective, uncertainty-aware desirability,
  nonlinear/integer constraints
- Box–Behnken P1 후보

**종료 기준:** 설계영역과 제약을 준수하고 알려진 quadratic surface의 최적점/경계 동작을 테스트한다.

## Gate E – 후순위 ML/고급 통계

- 일반 분류/회귀 ML
- AutoML/tuning
- SHAP/LIME
- 고급 ANOVA/혼합모형
- 비정규 capability
- 확장 Gage/DOE

Gate E는 B~D의 품질 기준을 낮추지 않는다.

현재 `doe.bayesian_optimization`은 dedicated API/UI에서 실행하는 `0.2.2`
available method다. 연속 factor 1~6개, 단일 maximize/minimize objective, 실제
관측 completed trial history, Matérn-5/2 Gaussian Process, Expected Improvement,
실제 단위 선형 부등식 constraint, deterministic seed/trial/candidate/time budget을
계약으로 고정한다. 앱은 목적함수, Python, shell 또는 장비를 실행하지 않고 추천을
관측값으로 자동 승격하지 않는다. Generic analysis-run은 계산하지 않고 전용
`/api/v1/bayesian-studies` 경로를 반환한다.

SQLite schema 12는 schema-11 study/history foundation을 보존하면서 추천과
`origin=recommendation` trial 관계를 추가한다. Study/history schema 1은 그대로며
recommendation config/result/model schema는 각각 1이다. Spawn worker는 수치 thread를
1개로 제한하고 GP fit/candidate/local search/evaluation/time budget을 강제한다. 결과는
예측 평균, posterior SD, EI, incumbent, 제약 평가, 사용 budget, package version,
확인 실험 필요와 전역 최적 비보장 warning을 분리해 저장한다.
Dedicated UI는 최대 16개 실제 단위 선형 부등식을 입력하고 저장된 식과 추천점의
feasibility를 표시한다. Restore는 checksum뿐 아니라 result/trial 좌표, source-history
관측 수와 incumbent, request/result budget, constraint evaluation, model/provenance 관계를
교차 검증한다. 5개 seed의 20-trial Branin simple-regret gate와 Windows spawn/fit/search
local benchmark는 같은 계산 정책의 회귀 근거이며 method/result schema를 바꾸지 않는다.

Lifecycle correctness 정책은 factor 수에 따른 initial-design 최소값, 200 trial/관측과
초기 empty를 포함한 201 history revision 상한, study를 고립시키는 initial-trial
abandon 차단, completed/pending/abandoned 모든 좌표의 재추천 제외를 backend와 UI에
같이 강제한다. Dedicated latest endpoint는 immutable recommendation snapshot과 현재
trial의 pending/completed/abandoned 상태 및 실제 관측을 분리한다. Request-level total
trial budget 기본값 50은 UI에 표시하고 도달 시 추천을 차단하며, fit/acquisition/worker
time budget은 public `bayesian_optimization_budget_exhausted`로 통일한다. 이 patch는
study/history/config/result/model schema와 기존 `0.2.0`/`0.2.1` restore 의미를
바꾸지 않는다. SQLite schema 14와 lifecycle-event schema 1은 optimistic
study-version/history 잠금을 사용하는 `active -> completed|abandoned` 전이, 최종
count/history/definition/recommendation SHA 관계, reason/request/build provenance를
고정한다. Pending trial을 암묵적으로 닫지 않으며 종료 후 모든 mutation은 storage
transaction에서도 차단한다. UI는 종료 study를 read-only로 복원하고 명시적
`predecessor_study_id`를 가진 successor 생성만 제공한다. Close는 삭제가 아니다.
별도 retention slice는 종료된 Bayesian metadata graph에 대해 checksum 검증
preflight, 정확한 manifest 확인, active/successor-reference 차단, 단일 SQLite
transaction 삭제를 제공한다. 현재 Bayesian graph의 file count는 0이며 dataset,
analysis/export, DOE, model, limit-set 파일 삭제로 확대 해석하지 않는다. 후속 bounded
slices는 개별 export, succeeded analysis run, regression-model manifest, 그리고
attribute-control limit-set 삭제를 각각 exact-manifest 확인과 quarantine recovery로
구현했다. Model은 dependent prediction, limit-set은 dependent Phase II analysis가
있으면 삭제를 차단하며 source result로 cascade하지 않는다. Dataset과 DOE root 삭제,
bulk/automatic cleanup은 여전히 제공하지 않는다. 상세 계약은
`docs/bayesian_study_lifecycle_contract.md`와
`docs/workspace_retention_contract.md`를 따른다.

The 2026-07-15 isolated dependency spike selected scikit-learn 1.7.2 as the
newest stable CPython 3.10 candidate and passed wheel-only installation against
NumPy 2.2.6/SciPy 1.15.3, offline import/runtime, `pip check`, single-threaded
CPU execution, and deterministic fixed-kernel GP smoke. The product owner then
approved Windows 11 client validation as a release gate rather than a
dependency-development gate. `scikit-learn==1.7.2` is now a production pin and
the reviewed Windows CPython 3.10 environment is protected by a 45-wheel
SHA-256 lock. The measured host remains Windows 10 Home build 19045, so actual
Windows 11 validation is still required before release. The current GP/EI
development evidence is not relabeled as Windows 11 approval. See
`docs/scikit_learn_dependency_spike.md` and
`docs/bayesian_optimization_contract.md`.

Frontend module loading slice는 618.10 kB였던 단일 main JavaScript asset을
463.89 kB main과 Regression 41.53 kB, Quality 58.83 kB, DOE 57.26 kB on-demand
chunk로 분리했다. Method 선택은 `startTransition`을 사용하고 execution panel은
접근 가능한 Suspense loading state와 내부 오류를 노출하지 않는 resettable error
boundary 안에서 렌더한다. 세 direct route, 실제 module resource, import 실패
주입을 browser E2E로 검증한다. 전체 JS 합계는 621.51 kB로 소폭 증가했으므로 이
변경은 전체 코드 감소가 아니라 초기 main payload 24.95% 감소로 기록한다. 상세
측정과 제한은 `docs/frontend_module_loading.md`를 따른다.

---

## 19. Codex 구현 절차

Codex는 메서드를 한꺼번에 빈 골격으로 추가하지 말고 다음 vertical slice를 반복한다.

1. 해당 requirement와 method ID 확인
2. request/result Pydantic schema
3. pure domain calculation
4. 손계산 fixture와 reference test
5. edge/error/warning test
6. service에서 dataset version 읽기
7. API run registry 연결
8. frontend method form과 preflight
9. result table/chart/warning/provenance
10. E2E
11. docs/OpenAPI/schema version 갱신
12. `scripts/check.ps1` 실행

### 19.1 PR 단위

권장 PR은 하나의 메서드 또는 밀접한 공통 기반 단위다.

좋은 예:

- `feat: add immutable dataset version materialization`
- `feat: add common analysis run contract`
- `feat: add descriptive statistics vertical slice`
- `feat: add Welch two-sample t test`
- `feat: add I-MR chart and rule engine`

피해야 할 예:

- “implement all statistics”
- 통계 라이브러리, UI, DB, 20개 메서드를 한 PR에 추가
- 계산 없이 메뉴와 mock 결과만 완료 처리

### 19.2 각 PR 설명에 포함할 내용

- 관련 Gate와 method ID
- 수용 기준
- 사용 공식/라이브러리/버전
- 데이터와 결측 처리
- reference fixture
- 실행한 명령과 결과
- 알려진 제한
- 새 dependency의 Windows/Python 3.10/라이선스 검토

---

## 20. 현재 단계에서 특히 빠뜨리기 쉬운 부분

1. **원자료와 요약자료 모드**: 비율 검정은 count 입력이 필요하고 t-test도 향후 summary 입력 요구가 있을 수 있다.
2. **순서의 불변성**: 관리도/Run Chart는 업로드 순서, 정렬, timestamp가 결과를 바꾼다.
3. **합리적 부분군**: 단순히 같은 ID를 묶는 것과 공정적으로 적절한 부분군은 다르다.
4. **단위**: capability, equivalence bound, DOE factor 범위와 optimizer 해석에 필요하다.
5. **규격과 통제의 구분**: spec은 고객/설계 요구, control limit은 공정 데이터 추정이다.
6. **동등성 경계**: 통계 도구가 자동으로 정할 수 없다.
7. **Gage 설계 유형**: crossed/nested, balanced/unbalanced를 구분하지 않으면 잘못된 분산성분이 나온다.
8. **DOE run order**: 반응 입력 뒤 재랜덤화하면 감사 가능성이 사라진다.
9. **alias와 hierarchy**: fractional design/term selection에서 필수다.
10. **모델의 안전한 저장**: 외부 pickle 호환보다 schema와 provenance가 우선이다.
11. **수치 알고리즘 버전**: 라이브러리 업데이트가 p-value/최적화 결과를 바꿀 수 있다.
12. **다중검정**: X–Y matrix, post-hoc, residual cell 분석에 필수다.
13. **장시간 작업 취소**: DOE search/optimizer/대형 chart 생성은 worker budget이 필요하다.
14. **접근성**: 관리도 위반을 색상만으로 표시하지 않는다.
15. **결과 stale 처리**: 데이터 버전 또는 설정 변경 후 과거 결과를 현재 결과처럼 표시하지 않는다.
16. **상용 도구 호환성 범위**: 통계적으로 타당한 결과와 특정 제품의 반올림/정책 일치는 별도 요구다.
17. **표준 문서 라이선스**: AIAG/ISO 등 유료 표준의 문구와 규칙을 무단 복제하지 않는다.
18. **한글 컬럼명과 경로**: Windows 실사용 fixture에 포함한다.

---

## 21. 제품 소유자가 출시 전에 확정할 결정

개발을 막지 않도록 안전한 기본값을 함께 제시한다.

| 결정 | 개발 기본값 | 출시 전 확인 |
| --- | --- | --- |
| X–Y Correlation 의미 | X 집합 × Y 집합 교차 상관 | lagged cross-correlation 필요 여부 |
| ANOVA P0 범위 | 일원배치/Welch | 이원/반복/ANCOVA 필요 시점 |
| TOST 범위 | 평균 차이, 원 단위 bound | 비율/분산/표준화 bound 필요 여부 |
| Control Chart | P/NP/C/U + 선택 허브 | 특정 산업 rule set |
| SPC 단계 | Phase I 우선 | Phase II 실시간 감시 필요 여부 |
| Gage R&R | balanced crossed ANOVA | nested/unbalanced 및 표준별 보고서 |
| Capability | normal capability | 비정규 분포와 변환 우선순위 |
| DOE | 2-level full factorial | fractional/PB/general factorial 우선순위 |
| RSM | CCD | Box–Behnken 동시 P0 여부 |
| 상용 도구 호환 | 통계 정확성 우선 | Minitab 등과 수치/화면 parity 여부 |
| 요약자료 입력 | 비율 분석 P0 | t/ANOVA summary data 필요 여부 |
| 최대 데이터 | 현 설정과 benchmark | 실제 PC/공정 데이터 규모 |
| 보고서 표준 | 내부 HTML/CSV/JSON | 사내 승인 양식·전자서명 |

---

## 22. 6개 모듈 Definition of Done

메서드는 다음을 모두 충족해야 완료다.

1. 안정적인 method ID/version과 typed request/result가 있다.
2. 데이터셋 버전, 필터, 역할, 옵션이 매니페스트에 저장된다.
3. 사용 N, 제외 N 및 결측 정책이 표시된다.
4. 가능한 추정치, CI, 효과크기, 검정통계량, p-value가 있다.
5. 가정, 경고 및 해석 제한이 결과와 리포트에 남는다.
6. pure calculation에 hand/reference/edge tests가 있다.
7. API, frontend, E2E의 하나의 vertical slice가 실제 계산으로 연결된다.
8. 수치 허용오차와 reference provenance가 문서화된다.
9. Windows/Python 3.10/CPU-only full check가 통과한다.
10. 외부 네트워크, 비밀, raw user data logging, untrusted pickle이 없다.
11. 접근성과 keyboard navigation이 동작한다.
12. 미구현 경로, fake result, 무음 fallback이 없다.
13. 데이터/설계 변경 시 stale 또는 새 version이 된다.
14. export가 화면의 반올림값이 아닌 원 결과와 provenance를 보존한다.
15. dependency와 라이선스 검토가 끝났다.

---

## 23. Codex 첫 작업 권장 순서

다음 프롬프트 범위는 `eda.descriptive`와 canonical JSONL/profile preflight 구현 전 기준이었다. 현재는 첫 reference-backed method, canonical artifact materialization, canonical reader adoption, duplicate-row count, memory estimate, persisted profile artifact, date/time preflight, filter row freezing, non-empty filter engine, route-level selected-analysis restore, Workbench-level frontend filter controls, `AppChrome`/`useDatasetWorkflow`/`WorkspaceRouter`/split analysis page/shell components, 그리고 `useAnalysisSelection`이 구현되었으므로 다음 narrow slice에서는 필요한 경우에만 route/layout boundary를 더 줄이거나 다음 reference-backed method의 공통 filter state 연결 중 하나만 선택하는 것이 안전하다.

```text
AGENTS.md, docs/six_module_implementation_guide.md, to_do_list.md, data_prd_addendum.md를 읽고
다음 narrow slice만 구현한다.

범위:
1. router-mounted analysis page 또는 다음 reference-backed method의 공통 filter state 연결 중 하나만 선택
2. 추가 계산을 시작한다면 hand/reference/edge tests와 no mock result 보장 테스트 포함
3. analysis_runs/jobs/artifacts metadata 계약을 사용하되 `eda.descriptive` 외 planned method를 executable로 바꾸지 않음
4. migration/unit/integration/frontend tests

선택한 첫 reference-backed method 외의 통계 계산이나 mock 결과는 추가하지 않는다.
완료 시 변경 파일, migration version, 실행 명령, 테스트 결과, 알려진 제한을 보고한다.
```

다음 PR에서도 실제 계산과 기준 테스트가 없는 메서드는 executable로 바꾸지 않는다.

---

## 24. 구현 참고 자료

- SciPy statistics API: https://docs.scipy.org/doc/scipy/reference/stats.html
- statsmodels statistics and TOST API: https://www.statsmodels.org/stable/stats.html
- statsmodels `ttost_ind`: https://www.statsmodels.org/stable/generated/statsmodels.stats.weightstats.ttost_ind.html
- statsmodels `ttost_paired`: https://www.statsmodels.org/stable/generated/statsmodels.stats.weightstats.ttost_paired.html
- NIST/SEMATECH Engineering Statistics Handbook: https://www.itl.nist.gov/div898/handbook/
- pyDOE3 documentation: https://pydoe3.readthedocs.io/

참고 자료의 계산 정책을 그대로 복사하지 말고 제품의 method version, 옵션, reference test와 연결한다.
