# Statistical Twin 분석 도메인 메뉴 및 UI 상세 명세

Status: implementation specification
Suggested repository path: `docs/analysis_domain_menu_spec.md`
Baseline reviewed: `fb07c68405e0038e2a694a35d806a1a191b2cfda`
Audience: frontend, backend, statistics, QA, and documentation engineers

---

## 1. 목적

이 문서는 기존 Statistical Twin의 통계 계산, method ID, 저장 결과, route와 실행 화면을 유지하면서 사용자에게 보이는 분석 메뉴를 다음 8개 도메인으로 재구성하는 구체적인 UI·옵션 명세다.

1. 기초통계·탐색 / Basic Statistics & Exploration
2. 평균비교·동등성 / Mean Comparison & Equivalence
3. 비율·범주형 데이터 / Proportions & Categorical Data
4. 상관·회귀·예측 / Correlation, Regression & Prediction
5. 실험계획·최적화 / DOE & Optimization
6. AI/ML 실험설계 / AI/ML Experimental Design
7. 품질·공정 모니터링 / Quality & Process Monitoring
8. 측정시스템·변동성 / Measurement Systems & Variability

이 문서는 **표시 계층과 사용자 흐름**의 source of truth다. 기존 통계 계산의 source of truth는 각 method contract와 현재 backend schema다.

---

## 2. 충돌 시 우선순위

구현 중 서로 다른 문서나 코드가 충돌하면 다음 우선순위를 따른다.

1. 각 method의 최신 `docs/*_contract.md`
2. backend Pydantic request/result schema와 method registry
3. 독립 reference fixture 및 현재 통과 중인 통계 테스트
4. 현재 frontend method panel의 실제 입력·결과 기능
5. 이 문서의 메뉴 배치·family·presentation 규칙
6. 일반 README 또는 오래된 screenshot

현재 method에 이 문서에 없는 옵션이 이미 구현되어 있다면 제거하지 않는다.
이 문서에 적힌 옵션과 현재 contract가 다르면 임의로 바꾸지 말고 차이를 보고한 뒤 contract를 우선한다.

---

## 3. 절대 호환 원칙

### 3.1 바꾸지 않는 것

- 기존 backend `AnalysisModuleId` 6개
- 기존 method ID
- 기존 method version
- 기존 result schema
- 저장 결과의 checksum
- 기존 direct URL
- Report Center restore
- model·DOE·Bayesian source dependency
- 현재 method panel의 계산 옵션과 결과
- 현재 filter, 실행, 이력, 비교, export workflow

### 3.2 새로 추가하는 것

- 사용자용 8개 presentation domain
- domain 아래 family
- domain/family용 landing UI와 sidebar tree
- method ID → presentation domain mapping
- planned workflow의 명확한 상태 표시
- 신규 method가 실제로 구현될 경우 별도 contract

### 3.3 기존 method screen 재사용

도메인 또는 family에서 method를 선택한 뒤에는 기존 `AnalysisWorkbench`와 해당 panel을 그대로 사용한다.

공통 순서:

1. 선택 method 제목
2. 입력·설계 기준 tag
3. 분석 도움말
4. 분석 filter
5. 역할·변수 선택
6. method 옵션
7. 실행 button
8. 결과
9. 저장 이력·비교
10. export

도메인 재구성을 이유로 method panel을 복제하거나 옵션을 새로 구현하지 않는다.

---

## 4. 다국어 규칙

현재 앱의 KOR/ENG locale infrastructure를 사용한다.

- domain/family 이름을 component에 하드코딩하지 않는다.
- `frontend/src/i18n/locales/en.ts`, `ko.ts` 또는 현재 번역 dictionary에 key를 추가한다.
- method 이름은 backend catalog의 `label_en`, `label_ko`를 우선 재사용한다.
- 사용자 데이터, 파일명, 컬럼명, 범주 수준, factor name은 번역하지 않는다.

권장 domain translation key:

```text
analysis.domain.basicExploration
analysis.domain.meanEquivalence
analysis.domain.proportionsCategorical
analysis.domain.correlationRegressionPrediction
analysis.domain.doeOptimization
analysis.domain.aiMlExperimentalDesign
analysis.domain.qualityProcessMonitoring
analysis.domain.measurementVariability
```

---

## 5. 공통 분석 landing UI

### 5.1 분석 첫 화면

현재 6개 backend module card 대신 8개 presentation domain card를 표시한다.

- wide desktop: 4열 × 2행
- laptop: 2열
- mobile: 1열
- 고정 높이 금지
- 긴 영어 제목이 잘리지 않음

각 domain card:

- domain 이름
- 한 줄 목적 설명
- 사용 가능한 method 수
- planned workflow 수
- 대표 family 2~4개
- `열기 / Open` action

### 5.2 domain 화면

도메인을 열면 family card를 표시한다.

family card 구성:

- family 이름
- 한 줄 선택 기준
- 포함 method compact button/list
- method 상태
- planned workflow가 있으면 실행 button이 아닌 `계획됨 / Planned` 표시

사용자가 domain 화면만 보고도 모든 method 이름을 확인할 수 있어야 한다.

### 5.3 sidebar

```text
분석
└─ Domain
   └─ Family
      └─ Method
```

규칙:

- family의 method 목록은 기본 접힘
- active method가 있는 chain은 자동 펼침
- domain/family click은 toggle만 수행
- method click만 실제 navigation 수행
- hidden contextual method는 일반 sidebar에서 제외
- planned workflow는 disabled item 또는 roadmap link로만 표시
- `aria-expanded`, `aria-controls`, `aria-current` 제공

---

## 6. 전체 domain mapping

| Presentation domain | Family | Current method / workflow | 상태 |
|---|---|---|---|
| 기초통계·탐색 | 분포와 요약 | `eda.descriptive`, `eda.graphical_summary`, `eda.normality` | Available |
| 기초통계·탐색 | 다변량 탐색 | `eda.multivariate_review` | Planned |
| 평균비교·동등성 | t-검정 | `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.two_sample_t` | Available |
| 평균비교·동등성 | ANOVA | `hypothesis.one_way_anova` | Available |
| 평균비교·동등성 | 동등성 검정 | 1-sample, paired, 2-sample TOST | Available |
| 평균비교·동등성 | 비모수 비교 | Wilcoxon, Mann–Whitney, Kruskal–Wallis | Available |
| 평균비교·동등성 | 비교성 평가 | Comparability Assessment | Planned workflow |
| 비율·범주형 데이터 | 비율 비교 | 1-Proportion, 2-Proportion | Available |
| 비율·범주형 데이터 | 범주형 관련성 | Chi-Square Test for Association | Available |
| 상관·회귀·예측 | 상관 분석 | Pearson, X–Y Correlation | Available |
| 상관·회귀·예측 | 회귀 모형 | Fit Regression Model | Available |
| 상관·회귀·예측 | 예측·최적화 | saved-model prediction, regression optimizer | Contextual |
| 상관·회귀·예측 | 잠재변수 회귀 | PLS Regression | Planned |
| 실험계획·최적화 | 요인배치 설계 | two-level full/fractional, general full factorial | Available |
| 실험계획·최적화 | 반응표면 | RSM | Available |
| 실험계획·최적화 | 최적화 | Response Optimizer | Available |
| AI/ML 실험설계 | 초기 공간 탐색 | LHS | Available |
| AI/ML 실험설계 | 순차 최적화 | Bayesian Optimization | Available |
| AI/ML 실험설계 | Surrogate 단계 | Gaussian Process | BO 내부 단계 |
| 품질·공정 모니터링 | 관리도 | attribute, subgroup, I-MR | Available |
| 품질·공정 모니터링 | 시계열 패턴 | Run Chart | Available |
| 품질·공정 모니터링 | 공정 성능 | Capability Analysis | Available |
| 품질·공정 모니터링 | 다변량 모니터링 | T²/GV/MEWMA/PCA/PLS monitoring | Planned |
| 측정시스템·변동성 | 변동성 비교 | Two Variances | New P0 |
| 측정시스템·변동성 | 변동성 비교 | Test for Equal Variances | Available |
| 측정시스템·변동성 | 측정시스템 | Gage R&R, Gage Run Chart | Available |

---

# 7. Domain 1 — 기초통계·탐색

## 7.1 목적

분포, 중심, 산포, 이상치와 기초적인 다변량 구조를 분석 전에 확인한다.

## 7.2 landing UI

Family 1: `분포와 요약 / Distribution & Summary`

```text
[기술통계] [그래프 요약] [정규성 검정]
```

Family 2: `다변량 탐색 / Multivariate Exploration`

```text
[Exploratory Multivariate Review — Planned]
```

`Test for Equal Variances`는 여기서 중복 노출하지 않고 `측정시스템·변동성`에 표시한다. 기존 route와 backend module은 유지한다.

## 7.3 기존 method 옵션 보존

### `eda.descriptive`

역할·입력:

- 수치형 변수 1개 이상
- 현재 dataset version
- 현재 analysis filter

기존 옵션:

- available-case by column missing policy
- 현재 구현된 표시 통계량과 정렬

결과에서 유지:

- N, missing
- mean, sample standard deviation, variance
- median, Q1, Q3, IQR
- minimum, maximum, range
- 현재 구현된 skewness/kurtosis 및 warning
- 컬럼 클릭 quick histogram/boxplot

UI 변경:

- domain/family 위치만 변경
- method panel과 결과 table은 유지

### `eda.graphical_summary`

역할·입력:

- 수치형 변수 1개 이상
- 현재 filter

기존 옵션:

- histogram bin 자동/직접 설정
- confidence level
- point limit은 고급 설정 또는 내부 기본값

결과에서 유지:

- normal-fit histogram
- Anderson–Darling summary
- moments와 five-number summary
- mean/median/stdev confidence intervals
- boxplot
- Q-Q plot
- ECDF 추가 그래프
- 기존 interactive chart·keyboard contract

### `eda.normality`

역할·입력:

- 연속형 수치 변수 1개 이상
- 선택적 group column

기존 옵션:

- alpha
- Q-Q point 포함 여부
- Q-Q point limit
- available-case/grouped policy

결과에서 유지:

- Shapiro-Wilk가 지원되는 범위의 결과
- Anderson–Darling
- Q-Q plot
- 그룹별 결과
- `정규성 가정 유지 가능 / Normality assumption may be retained`
- 검정 하나로 다음 분석을 자동 변경하지 않는 경고

## 7.4 Planned — Exploratory Multivariate Review

이 method를 실제로 구현하기 전까지 `Available`로 표시하지 않는다.

권장 future ID:

```text
eda.multivariate_review
```

P0 입력:

- 수치형 변수 2개 이상
- 권장 상한 20개, 실제 상한은 contract에서 확정
- scaling:
  - Standardized / correlation matrix
  - Original scale / covariance matrix
- missing policy:
  - complete case 기본
- confidence ellipse와 outlier threshold는 고급 설정

P0 결과:

- correlation heatmap
- PCA eigenvalues
- scree plot
- cumulative explained variance
- score plot
- loading plot
- selected component table
- T² 또는 score-distance 진단은 명확한 정의가 있을 때만 제공

금지:

- PCA와 PLS를 한 method로 혼합
- 결측을 자동 평균 대치
- component 수를 설명 없이 자동 고정
- PCA를 causal feature importance로 설명

---

# 8. Domain 2 — 평균비교·동등성

## 8.1 landing UI

Family 1: `t-검정 / t-Tests`

```text
[1-표본] [대응표본] [2-표본]
```

Family 2: `ANOVA`

```text
[일원분산분석]
```

Family 3: `동등성 검정 / Equivalence Tests`

```text
[1-표본] [대응표본] [2-표본]
```

Family 4: `비모수 비교 / Nonparametric Tests`

```text
[1-표본 Wilcoxon] [Mann–Whitney U] [Kruskal–Wallis]
```

Family 5: `비교성 평가 / Comparability Assessment`

```text
[Planned workflow]
```

`ANOVA`와 `One-Way ANOVA`를 별도 leaf로 중복 표시하지 않는다.
`2-Sample Comparison`은 별도 method가 아니라 quick guide로 제공한다.

## 8.2 t-검정 옵션 보존

### `hypothesis.one_sample_t`

- response: 수치형 1개
- null mean
- alternative: two-sided / greater / less
- alpha
- confidence level
- complete-case missing policy

결과:

- sample summary
- mean difference
- t, df, p-value
- confidence interval
- 현재 효과크기와 warning

### `hypothesis.paired_t`

- before column
- after column
- null difference
- alternative
- alpha
- confidence level
- complete-pair policy

결과:

- pair count와 incomplete pair count
- difference summary
- t, df, p-value
- difference CI
- 현재 효과크기

### `hypothesis.two_sample_t`

- numeric response
- group column with exactly two usable levels
- group direction을 결과에 명시
- variance assumption:
  - Welch 기본
  - pooled 명시적 선택
- null difference
- alternative
- alpha
- confidence level

결과:

- group summaries
- mean difference
- standard error와 df
- t/p/CI
- 현재 효과크기

## 8.3 ANOVA 옵션 보존

### `hypothesis.one_way_anova`

반드시 `docs/one_way_anova_method_contract.md`를 따른다.

입력:

- numeric response
- group column 2개 이상 level
- alpha
- confidence level

분산 모형:

- equal variance → standard ANOVA
- unequal variance → Welch ANOVA

호환 posthoc:

- standard:
  - none
  - Tukey-Kramer
  - Dunnett
- Welch:
  - none
  - Games-Howell

Dunnett:

- filtered group-level preflight
- control group 필수
- control 변경 시 result/input invalidation

comparison policy:

- when requested 기본
- legacy after-significant 복원

결과:

- 실제 사용한 variance model
- omnibus result
- group summary
- 호환 posthoc table
- Dunnett control
- standard ANOVA에서만 지원되는 effect size
- Welch에서 pooled SS/effect size를 가짜로 표시하지 않음

## 8.4 동등성 옵션 보존

`docs/equivalence_test_contract.md`를 따른다.

### 1-sample

- response
- reference mean
- lower/upper equivalence bounds
- alpha
- complete-case

### paired

- test column
- reference column
- lower/upper bounds
- alpha
- complete pairs
- difference direction = test - reference

### independent two-sample

- response
- group exactly two levels
- test group
- reference group
- Welch 기본 / pooled 선택
- lower/upper bounds
- alpha
- difference direction = test - reference

공통 결과:

- estimate/SE/df
- lower and upper one-sided tests
- TOST p-value
- 1−2α confidence interval
- Equivalence Plot
- `동등성 근거 있음 / Evidence of equivalence`
- `동등성 근거 부족 / Insufficient evidence of equivalence`

일반 t-test의 비유의를 동등성으로 해석하지 않는다.

## 8.5 비모수 옵션 보존

### `hypothesis.one_sample_wilcoxon`

- response
- null location
- alternative
- method: auto / exact / asymptotic
- zero method: wilcox / pratt / zsplit
- alpha

### `hypothesis.mann_whitney`

- response
- group exactly two levels
- alternative
- method: auto / exact / asymptotic
- alpha

### `hypothesis.kruskal_wallis`

- response
- group 2개 이상
- alpha
- 현재 구현된 tie correction
- 현재 구현된 Dunn/Holm posthoc가 있으면 그대로 유지
- posthoc를 새로 추가하거나 제거할 경우 별도 contract 필요

## 8.6 Quick guide — 2-Sample Comparison

```text
독립 2그룹 평균 차이
→ 2-Sample t-Test

독립 2그룹 순위 기반 차이
→ Mann–Whitney U

독립 2그룹이 사전 허용범위 안에서 충분히 가까운지 평가
→ 2-Sample Equivalence Test

정확히 2그룹의 변동성 비교
→ Two Variances
```

## 8.7 Planned — Comparability Assessment

단일 검정으로 구현하지 않는다.

권장 future ID:

```text
hypothesis.comparability_assessment
```

P0 workflow 정의 전 필요한 입력:

- Test / Reference 또는 Before / After
- lot/batch identifier
- 복수 CQA
- CQA별 자료형
- CQA별 사전 지정 margin
- difference 또는 ratio scale
- 평균·변동성·분포 기준
- multiplicity 또는 overall decision policy

결과:

- CQA별 descriptive/graphical summary
- CQA별 mean/equivalence result
- variability comparison
- missing/inadequate sample warning
- overall evidence summary

금지:

- 단일 `comparability p-value`
- 자동 규제 승인 결론
- 관측 후 margin 자동 생성

---

# 9. Domain 3 — 비율·범주형 데이터

## 9.1 landing UI

Family 1: `비율 비교 / Proportion Tests`

```text
[1-Proportion] [2-Proportion]
```

Family 2: `범주형 관련성 / Categorical Association`

```text
[Chi-Square Test for Association]
```

## 9.2 `categorical.one_proportion`

입력·옵션:

- response/event column
- event level
- null proportion
- alternative
- alpha
- confidence level
- 현재 CI method selector, 기본 Wilson
- complete-case/current missing policy

결과:

- event count / total
- sample proportion
- confidence interval
- test statistic/p-value 또는 exact result
- method metadata

## 9.3 `categorical.two_proportion`

입력·옵션:

- binary/event response
- group exactly two levels
- event level
- group direction
- alternative
- alpha
- confidence level
- 현재 구현된 exact/approximation policy

결과:

- group별 event/total/proportion
- proportion difference
- CI
- test/p-value
- 현재 제공되는 risk ratio/odds ratio가 있으면 유지

## 9.4 `categorical.chi_square_association`

입력·옵션:

- row categorical variable
- column categorical variable
- alpha
- current missing policy

결과:

- contingency table
- expected counts
- chi-square, df, p-value
- sparse expected-count warning
- Cramér’s V가 현재 있으면 유지
- 2×2 Fisher exact가 현재 지원되면 유지

---

# 10. Domain 4 — 상관·회귀·예측

## 10.1 landing UI

Family 1: `상관 분석 / Correlation`

```text
[Pearson Correlation] [X–Y Correlation Matrix]
```

Family 2: `회귀 모형 / Regression Modeling`

```text
[Fit Regression Model]
```

Family 3: `예측·최적화 / Prediction & Optimization`

```text
[저장 모델로 예측] [회귀모형 기반 반응 최적화]
```

Family 4: `잠재변수 회귀 / Latent-Variable Regression`

```text
[PLS Regression — Planned]
```

Prediction과 regression optimizer는 contextual workflow다. 일반 method card를 중복 생성하지 않는다.

## 10.2 `regression.pearson`

- X numeric column
- Y numeric column
- alpha
- confidence level
- pairwise complete-case

결과:

- N
- Pearson r
- p-value
- CI
- interactive scatter
- 비인과 경고

## 10.3 `regression.xy_correlation`

- X variable set 1개 이상
- Y variable set 1개 이상
- alpha
- confidence level
- pairwise complete-case

결과:

- X×Y correlation matrix
- pairwise N
- p-value/CI
- selected cell detail

## 10.4 `regression.linear_model`

반드시 `docs/linear_model_method_contract.md`를 따른다.

입력:

- numeric response 1개
- numeric predictor 1개 이상
- categorical main-effect predictors
- optional numeric quadratic terms
- optional numeric×numeric interactions
- model selection:
  - none
  - backward elimination
- alpha-to-remove
- strong hierarchy
- alpha
- confidence level
- complete-case
- intercept included
- standard covariance

결과 순서:

1. model selection trace
2. regression equation
3. model summary
4. coefficients and VIF
5. ANOVA and lack-of-fit
6. residual 4-in-1
7. additional diagnostics
8. unusual observations
9. saved model
10. response optimization
11. prediction

현재 결과를 삭제하거나 domain landing에 복제하지 않는다.

## 10.5 Contextual prediction

입구:

- 회귀 결과의 `예측 입력 / Predict New Conditions`
- 관리 화면의 저장 모델 action
- legacy direct URL

옵션:

- manual row grid
- numeric predictor input
- categorical level select
- row add/delete
- paste import
- header/mapping preview
- full preflight
- confidence level
- mean CI and prediction interval

결과:

- summary view
- full input view
- predicted mean
- CI/PI
- row warning/status
- CSV export

## 10.6 Contextual regression optimizer

입구:

- 저장된 회귀모형 결과
- 저장 모델 관리 action

옵션:

- goal: maximize / minimize / target / range
- numeric bounds within training domain
- categorical allowed levels
- current constraints/search settings

결과:

- optimal predictor settings
- predicted response
- desirability
- numeric conditional profiles
- categorical profile table
- confirmation-experiment warning

## 10.7 Planned — PLS Regression

권장 future ID:

```text
regression.partial_least_squares
```

P0 입력:

- numeric response 1개 이상
- predictor 2개 이상
- standardize on/off, default on
- component selection:
  - cross-validation recommended
  - fixed component count
- maximum components
- CV folds or leave-one-out policy
- complete-case missing policy

P0 결과:

- selected component count
- X score
- Y score 또는 fitted response
- loading/weight
- explained X/Y variance
- PRESS and predicted R²
- CV curve
- coefficients
- prediction

PLS를 관리도로 부르지 않는다.

## 10.8 Gaussian Process 판단

Standalone GPR이 향후 필요하면 ID는 다음을 검토한다.

```text
regression.gaussian_process
```

이 경우 배치는 이 도메인이다. 현재 AI/ML Experimental Design에는 BO 내부 surrogate 단계만 표시한다.

---

# 11. Domain 5 — 실험계획·최적화

## 11.1 landing UI

Family 1: `요인배치 설계 / Factorial Designs`

```text
[2-Level Full/Fractional Factorial] [General Full Factorial]
```

Family 2: `반응표면 / Response Surface`

```text
[Response Surface Methodology]
```

Family 3: `최적화 / Optimization`

```text
[Response Optimizer]
```

LHS와 Bayesian은 이 도메인에서 중복 표시하지 않는다.

## 11.2 `doe.factorial_design`

반드시 `docs/factorial_design_method_contract.md`를 따른다.

설계 종류:

- two-level full factorial
- tested regular two-level fractional catalog

기본 설정:

- design name
- design type
- replicates
- center points

factor 설정:

- 2~6 continuous factors
- name
- low/high
- domain kind
- step/display decimals/unit when current factor-domain contract supports them

고급 설정:

- randomize
- randomization seed
- block count
- fractional design 선택 시 fraction ID, resolution, generator preview

분석 설정:

- response revision
- max interaction order
- confidence level
- diagnostic point limit advanced

결과:

- design table
- response entry/revision
- effects and coefficients
- alias/resolution for fractional
- ANOVA
- curvature/block effect
- main effect/interaction plots
- diagnostics
- HTML report

## 11.3 `doe.general_factorial_design`

- factor 2~6개
- each factor 2~10 numeric or text levels
- run cap 256
- replicates
- randomization settings
- maximum interaction order

결과:

- treatment-coded categorical model
- term block ANOVA
- response revision
- diagnostics

숫자 수준을 continuous -1/+1 효과로 해석하지 않는다.

## 11.4 `doe.response_surface`

반드시 `docs/response_surface_method_contract.md`를 따른다.

기본 설정:

- design name
- factors 2~5
- low/high/domain/unit
- alpha mode:
  - rotatable
  - face-centered
- center points
- randomization/seed

분석:

- full quadratic fixed hierarchy
- response revision
- confidence level

결과:

- coefficients
- term ANOVA
- pure error/lack-of-fit
- residual/influence diagnostics
- stationary point/classification
- contour plot
- response optimizer action

## 11.5 `doe.response_optimizer`

source:

- verified stored RSM analysis
- source response revision

목표:

- maximize
- minimize
- target
- range
- current multi-response desirability support가 있으면 유지

factor 검색:

- narrower bounds
- factor domain/step
- linear constraints

고급:

- search seed/budget
- current deterministic search settings

결과:

- optimal settings
- predicted response
- desirability
- constraint evaluation
- source identity
- confirmation experiment warning

---

# 12. Domain 6 — AI/ML 실험설계

## 12.1 landing UI

상단 workflow:

```text
초기 공간 탐색
→ 실제 반응 입력
→ Gaussian Process surrogate
→ 획득함수
→ 다음 실험 추천
→ 실제 반응 입력
→ 반복
```

Family 1: `초기 공간 탐색 / Initial Space-Filling Design`

```text
[Latin Hypercube Sampling]
```

Family 2: `순차 최적화 / Sequential Optimization`

```text
[Bayesian Optimization]
```

Gaussian Process는 별도 가짜 method button이 아니다.

## 12.2 `doe.latin_hypercube`

반드시 `docs/lhs_design_contract.md`를 따른다.

기본 설정:

- design name
- run count 2~200

factor:

- 1~6 factors
- low/high
- continuous or discrete numeric
- step
- display decimals
- unit

고급:

- design seed
- run-order seed
- optimization:
  - random-cd
  - none
- run order randomization

결과:

- immutable design table
- actual and normalized coordinates
- quality metrics
- parallel coordinates
- two-factor scatter projection
- shared run selection
- response input/revision
- CSV export

LHS가 효과 추정이나 최적화를 자동 수행한다고 표시하지 않는다.

## 12.3 `doe.bayesian_optimization`

반드시 다음 문서를 따른다.

- `docs/bayesian_optimization_contract.md`
- `docs/bayesian_batch_recommendation_contract.md`
- `docs/bayesian_study_lifecycle_contract.md`

Study 기본:

- study name
- objective response name/unit
- goal:
  - maximize
  - minimize
  - match target
- target/tolerance when applicable

초기 설계:

- factor 1~6개
- continuous or fixed-step numeric
- bounds/domain/step/unit
- initial design size
- initial policy:
  - LHS random-cd for unconstrained
  - feasible uniform policy for linear constraints
- seed
- actual-unit linear constraints up to current cap

관측:

- pending initial/recommendation trials
- bulk observation entry
- paste import
- individual abandon
- immutable history revision

다음 실험 추천:

- execution mode:
  - sequential single
  - synchronous batch
- batch size 1~8
- acquisition:
  - EI
  - Expected Target Improvement for target goal
- exploration profile:
  - exploitation
  - balanced
  - exploration
  - custom xi
- total trial budget
- current advanced search settings

결과:

- GP kernel/model summary
- completed observation count
- posterior mean/std
- acquisition value
- incumbent or target distance
- constraints
- recommendation reason
- batch fantasy-conditioning explanation
- pending trial state
- no-global-optimum and confirmation warnings

## 12.4 Gaussian Process 표시

Bayesian summary 안에 read-only card로 표시한다.

```text
Gaussian Process Surrogate
- Kernel
- Fitted observations
- Length scales
- Log marginal likelihood
- Prediction uncertainty
- Model status
```

별도 실행 button을 만들지 않는다.

---

# 13. Domain 7 — 품질·공정 모니터링

## 13.1 landing UI

Family 1: `관리도 / Control Charts`

```text
[Attribute Control Chart] [Variables Charts for Subgroups] [I-MR Chart]
```

Family 2: `시계열 패턴 / Time-Ordered Patterns`

```text
[Run Chart]
```

Family 3: `공정 성능 / Process Performance`

```text
[Capability Analysis]
```

Family 4: `다변량 모니터링 / Multivariate Monitoring`

```text
[Planned]
```

Gage methods는 측정시스템·변동성으로 이동한다.

## 13.2 `quality.attribute_control_chart`

현재 contract와 UI를 유지한다.

차트 type:

- p
- np
- c
- u

입력:

- defect/defective count
- denominator/opportunity where required
- order/time
- constant opportunity confirmation where required

Phase:

- Phase I
- Phase II using validated limit set

결과:

- center/control limits
- signals
- limit set lifecycle
- monitoring preflight

## 13.3 `quality.subgroup_chart`

- numeric measurement
- subgroup column
- chart type:
  - Xbar-R
  - Xbar-S
- current ordering/group validation
- subgroup size policy

결과:

- Xbar chart
- R or S chart
- limits
- signal table
- warnings

## 13.4 `quality.individuals_chart`

- numeric value
- optional order column
- current I-MR calculation
- pattern rules

결과:

- I chart
- MR chart
- control limits
- signal summary
- control vs specification explanation

## 13.5 `quality.run_chart`

- numeric value
- optional order
- median center
- current sequence rules
- current four approximate p-values

결과:

- Run Chart
- clustering/mixture/trend/oscillation
- sequence signal
- “관리한계 없음” 설명

## 13.6 `quality.capability`

- numeric value
- LSL and/or USL according to current contract
- optional target
- current distribution assumption/policy
- current filter/missing handling

결과:

- capability indices
- histogram/spec lines
- warnings about process stability and distribution

## 13.7 Planned — Multivariate Monitoring

한 method name 아래 mode를 제공할 수 있으나 실제 계산별 contract가 필요하다.

권장 future ID:

```text
quality.multivariate_monitoring
```

Phase 1:

- Hotelling T² Chart
- Generalized Variance Chart
- T²-Generalized Variance Chart

Phase 2:

- MEWMA

Phase 3:

- PCA-based monitoring
- PLS-based monitoring

공통 입력:

- multiple numeric variables
- optional subgroup/time/order
- Phase I reference data
- Phase II monitoring data or limit set
- standardization policy
- alpha/control-limit policy

PCA monitoring 결과:

- scores/loadings
- T²
- SPE/Q residual
- limits
- contribution plot

PLS monitoring은 저장 PLS model을 source로 해야 하며 standalone PLS regression과 분리한다.

---

# 14. Domain 8 — 측정시스템·변동성

## 14.1 landing UI

Family 1: `변동성 비교 / Variability Comparison`

```text
[Two Variances] [Test for Equal Variances]
```

Family 2: `측정시스템 분석 / Measurement System Analysis`

```text
[Gage R&R Study] [Gage Run Chart]
```

## 14.2 New P0 — Two Variances

권장 method ID:

```text
quality.two_variances
```

이 method는 기존 `eda.equal_variances`와 합치지 않는다.

입력:

- numeric response
- group column
- exactly two selected groups
- group 1 / group 2 direction
- scale:
  - standard deviation ratio
  - variance ratio
- hypothesized ratio, default 1
- alternative:
  - not equal
  - less
  - greater
- confidence level
- method selection:
  - Bonett
  - Brown–Forsythe Levene
  - Both
  - normal-theory F test, explicit only

결과:

- group N, mean, standard deviation, variance
- estimated ratio
- ratio confidence interval
- Bonett result
- Levene result
- F-test when requested
- one/two-sided interpretation
- normality-sensitive F-test warning

금지:

- F-test를 default로 자동 선택
- 비유의를 “분산이 같다”고 증명한 것으로 표현
- two-group method를 3개 이상 그룹에 적용

신규 contract:

```text
docs/two_variances_method_contract.md
```

## 14.3 `eda.equal_variances`

반드시 `docs/equal_variances_method_contract.md`를 따른다.

입력:

- numeric response
- group 2개 이상
- alpha
- complete-case

기본 결과:

- Multiple Comparisons
- Levene Test (Brown–Forsythe median-centered)
- comparison intervals chart

추가:

- classical mean-centered Levene는 additional test로만 표시

이 method는 이 domain에만 기본 표시한다. 기존 backend module/route는 유지한다.

## 14.4 `quality.gage_rr`

현재 contract와 UI를 그대로 유지한다.

최소 역할:

- measurement
- part
- operator
- replicate 또는 현재 반복 식별 정책

현재 옵션:

- 현재 crossed/nested 지원 범위
- interaction policy
- tolerance 또는 study variation option이 있다면 유지
- preflight

결과:

- repeatability
- reproducibility
- part-to-part
- total Gage R&R
- variance components
- % contribution / % study variation
- interaction result
- warning

새 domain 이동을 이유로 계산이나 input을 변경하지 않는다.

## 14.5 `quality.gage_run_chart`

현재 역할·옵션을 유지한다.

- measurement
- part/operator grouping
- optional order/replicate
- current chart arrangement

결과:

- grouped measurement run/point plot
- operator/part identification
- measurement system pattern review

---

# 15. Planned·Contextual 상태 규칙

## 15.1 Available

- 실제 실행 가능
- 저장 result 생성
- tests와 contract 존재

## 15.2 Planned

- disabled
- 구체적인 미구현 이유
- 실행 button 없음
- 가짜 chart/result 없음

## 15.3 Contextual workflow

- source asset 또는 선행 method 결과 필요
- 일반 method card보다 source 화면 action으로 진입

예:

- Regression Predict
- Regression Optimizer
- RSM Response Optimizer
- Gaussian Process summary inside BO

---

# 16. Frontend 구현 구조

권장 파일:

```text
frontend/src/analysisDomains.ts
frontend/src/analysisDomainMapping.ts
frontend/src/analysisDomainGuidance.ts
frontend/src/AnalysisDomainLanding.tsx
frontend/src/AnalysisDomainFamilyCard.tsx
```

권장 타입:

```ts
export type AnalysisDomainId =
  | "basic-exploration"
  | "mean-equivalence"
  | "proportions-categorical"
  | "correlation-regression-prediction"
  | "doe-optimization"
  | "ai-ml-experimental-design"
  | "quality-process-monitoring"
  | "measurement-variability";

export interface AnalysisDomainFamily {
  id: string;
  labelKey: TranslationKey;
  descriptionKey: TranslationKey;
  methodIds: readonly string[];
  plannedWorkflowIds?: readonly string[];
}
```

method ID가 여러 domain에 들어가면 build/test 실패하도록 한다.

---

# 17. Route·selection 규칙

기존 method URL은 유지한다.

```text
/analysis/{legacy-module}/{method-id}
```

active domain은 method ID mapping으로 계산한다.

예:

```text
eda.equal_variances
→ measurement-variability
```

backend module ID만 보고 domain을 계산하지 않는다.

Domain landing은 frontend query를 사용할 수 있다.

```text
/analysis?domain=measurement-variability
```

필수:

- refresh
- direct URL
- back/forward
- dataset query 보존
- locale 보존

---

# 18. 자동 무결성 검사

반드시 다음 test를 추가한다.

1. 모든 visible available method는 정확히 한 domain에 존재
2. duplicate method ID 없음
3. registry에 없는 method ID 없음
4. 신규 visible method에 mapping이 없으면 실패
5. contextual method가 일반 목록에 노출되지 않음
6. planned workflow는 executable method로 취급되지 않음
7. KOR/ENG key parity
8. active method의 domain/family chain 자동 펼침

---

# 19. 관련 문서 참조표

Agent는 각 method UI를 변경하기 전에 현재 repository에서 다음 문서를 찾아 읽어야 한다.

| 영역 | 우선 참고 문서 |
|---|---|
| Graphical Summary | `docs/graphical_summary_method_contract.md` 또는 현재 graphical-summary contract, `docs/interactive_chart_contract.md` |
| Equal Variances | `docs/equal_variances_method_contract.md` |
| One-Way ANOVA | `docs/one_way_anova_method_contract.md` |
| Equivalence | `docs/equivalence_test_contract.md` |
| Linear Model | `docs/linear_model_method_contract.md` |
| Regression Prediction | `docs/regression_prediction_contract.md` |
| Regression Optimizer | `docs/regression_response_optimizer_contract.md` |
| Attribute Control Chart | `docs/attribute_control_chart_method_contract.md` |
| I-MR | `docs/individuals_chart_method_contract.md` |
| Run Chart | `docs/run_chart_method_contract.md` |
| Factorial/General Factorial | `docs/factorial_design_method_contract.md` |
| LHS | `docs/lhs_design_contract.md` |
| RSM | `docs/response_surface_method_contract.md` |
| Response Optimizer | `docs/response_optimizer_contract.md` |
| Bayesian | `docs/bayesian_optimization_contract.md`, `docs/bayesian_batch_recommendation_contract.md`, `docs/bayesian_study_lifecycle_contract.md` |
| Asset/report compatibility | `docs/asset_management_contract.md`, `docs/method_versioning.md`, `docs/runtime_compatibility_contract.md` |

문서명이 현재 branch에서 다르면 동일 method ID를 포함하는 최신 contract를 찾아 사용한다.

---

# 20. Phase 분리

## Phase 1 — 메뉴·UI 재구성

- 8 domain
- family grouping
- sidebar
- landing UI
- help/search/domain mapping
- current method options/results 100% 유지

계산 변경 없음.
API 변경 없음.
DB migration 없음.
method version 변경 없음.

## Phase 2 — Two Variances

- 신규 method
- backend calculation
- panel
- result/report
- reference test

## Phase 3 — 큰 신규 기능

별도 PR:

- Exploratory Multivariate Review/PCA
- PLS Regression
- Comparability Assessment
- Multivariate Monitoring

한 PR에서 Phase 1~3 전체를 동시에 구현하지 않는다.

---

# 21. 최종 Acceptance Criteria

- [ ] 기존 6개 backend module ID 유지
- [ ] 사용자 화면에 8개 domain 표시
- [ ] 모든 기존 visible method가 정확히 한 번 표시
- [ ] 기존 method panel의 옵션이 하나도 사라지지 않음
- [ ] 기존 result section, history, export 유지
- [ ] ANOVA와 One-Way ANOVA 중복 없음
- [ ] 2-Sample Comparison을 가짜 method로 만들지 않음
- [ ] Comparability를 단일 equivalence alias로 만들지 않음
- [ ] Gaussian Process를 별도 실험설계 method로 중복 노출하지 않음
- [ ] PLS Regression과 PLS Monitoring을 구분
- [ ] Gage와 Equal Variances가 측정시스템·변동성에 표시
- [ ] LHS와 Bayesian이 AI/ML 실험설계에 표시
- [ ] Factorial/RSM/Optimizer가 DOE & Optimization에 표시
- [ ] direct URL, restore, report, model source가 정상
- [ ] KOR/ENG 모두 정상
- [ ] mobile sidebar와 landing card 정상
- [ ] Phase 1에서 통계 계산/version/schema가 변경되지 않음
