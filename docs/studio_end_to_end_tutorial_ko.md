# DataLab Studio 한국어 end-to-end 튜토리얼

## 1. 튜토리얼 목적

이 문서는 DataLab Studio를 처음 사용하는 사람이 synthetic 공정 데이터 등록부터 탐색,
가설검정, 회귀, Predict, 품질, DOE, Response Optimizer, Bayesian Optimization, 저장 결과
복원과 export까지 직접 수행하도록 안내한다. 화면에서 확인할 수치는
`examples/tutorial/tutorial_expected_results.json`을 현재 Studio API로 실제 실행해 얻은 값이다.

## 2. 필요한 파일

- `studio_process_training.csv`: 주 학습 데이터, 240행
- `studio_process_paste_60.tsv`: paste grid 연습용 첫 60행
- `studio_process_prediction.csv`: Predict와 Phase II용 48행
- `studio_process_prediction_invalid.csv`: 예측 사전점검 오류 연습용
- `studio_gage_rr.csv`: 10 parts x 3 operators x 2 replicates
- `studio_factorial_responses.csv`: 3요인 2반복 factorial 반응
- `studio_rsm_responses.csv`: 2요인 face-centered CCD 반응
- `studio_bayesian_observations.csv`: Bayesian 초기 관측 5개

모든 파일은 `examples/tutorial/`에 있다. SHA-256과 행/열 수는
`tutorial_data_manifest.json`에서 확인한다.

## 3. Synthetic data 고지

모든 행은 seed `20260718`로 생성한 가상 기록이다. 실존 인물, 회사, 제품, 장비 또는
생산 실적을 나타내지 않는다. `run_id`, line, supplier, operator 이름도 모두 가상 label이다.

## 4. Studio 실행

저장소 root의 PowerShell에서 다음을 실행한다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

브라우저에는 frontend가 안내한 `127.0.0.1` 주소를 입력한다. 오른쪽 위가 `API 연결됨`인지
확인한다. `API 연결 필요`이면 backend가 실행 중인지, 다른 process가 port를 점유했는지부터
확인한다. 데이터를 외부 사이트에 올리지 않는다.

## 5. 파일 업로드

1. 왼쪽 `데이터셋`을 선택한다.
2. `원본 데이터 파일`에서 `studio_process_training.csv`를 고른다.
3. `업로드`를 누른다.
4. raw SHA-256, 크기, parsing suggestion을 확인한다.

업로드는 분석을 즉시 실행하지 않는다. raw bytes는 보존되고 parsing 확정 후 immutable
dataset version이 만들어진다.

## 6. Excel/TSV 붙여넣기

1. `studio_process_paste_60.tsv`를 text editor 또는 spreadsheet에서 전체 선택해 복사한다.
2. `복사한 표 붙여넣기` surface를 클릭하고 `Ctrl+V`를 누른다.
3. `표 보기`에서 60행 x 15열, delimiter `Tab`, line ending `LF`를 확인한다.
4. 셀을 선택해 address와 전체 값을 inspector에서 확인한다.
5. `원문 보기`로 전환해 tab 원문이 유지되는지 확인한다.
6. `붙여넣기 데이터 등록`을 누른다.

Paste preview는 원문을 다시 serialize하지 않으며 HTML clipboard와 formula를 실행하지 않는다.
성공 후 raw draft는 browser storage에 남지 않는다.

## 7. Paste grid 확인

- 빈 셀은 빈 셀 표시로, 열 수가 다른 행은 ragged warning으로 구분한다.
- 최대 200행, 100열, 20,000 cells만 preview한다. 잘려도 server에 전달하는 원문은 그대로다.
- `다시 붙여넣기`는 새 원문을 staging하고 `모두 지우기`는 raw ref, preview, selection을 지운다.
- `첫 행을 헤더처럼 보기`는 표시만 바꾸며 제출 문자열을 수정하지 않는다.

## 8. Parsing confirmation

Server suggestion에서 encoding `utf-8`, delimiter `,` 또는 `Tab`, header `있음`, data start
row `2`를 확인하고 `파싱 확정`을 누른다. Browser preview와 server suggestion이 다르면 그
차이를 먼저 검토한다. 최종 authoritative control은 parsing confirmation이다.

## 9. Schema와 역할 지정

`studio_process_training.csv`는 다음처럼 확인한다.

| 용도 | 컬럼 | 권장 measurement/role |
| --- | --- | --- |
| X | `temperature_c`, `pressure_bar`, `cycle_time_s`, `catalyst_pct`, `feed_rate_kg_h` | continuous / Predictor |
| X | `material_grade` | nominal / Predictor |
| Y | `yield_pct`, `tensile_strength_mpa` | continuous / Response |
| Group | `production_line`, `supplier` | nominal / Group |
| Category | `pass_flag` | nominal / Response |
| Count | `defectives_count` | count / Count |
| Denominator | `inspected_count` | count / Denominator |
| Identifier/order | `run_id`, `timestamp` | identifier / Ignore 또는 Order |

`pass_flag`와 `defectives_count`는 결과에서 파생된 보조 컬럼이므로 `yield_pct` 회귀 predictor로
선택하지 않는다. 이는 leakage를 피하기 위한 튜토리얼 규칙이다.

## 10. Profile와 preflight

Profile에서 type, missing, distinct level, numeric range를 확인한다. Preflight의 `ready`는 해당
입력 계약을 통과했다는 뜻이지 독립성, 인과성 또는 모형 적합성을 증명하지 않는다. 실행 전
항상 dataset version, filter snapshot, N, 역할, missing policy, alpha와 warnings를 확인한다.

## 11. Canonical preview

Page size를 `10`, `25`, `50`, `100`으로 바꾸고 `특정 행으로 이동`을 사용한다. 셀을 선택하면
현재 canonical page의 전체 값이 inspector에 보인다. Page 이동 시 selection은 reset된다.
Studio는 전체 canonical rows를 browser state에 적재하지 않는다.

## 12. 탐색적 분석

### 기술통계와 그래프 요약

- **사용자 질문:** 수율과 인장강도의 중심, 산포, 범위와 이상치를 먼저 보고 싶은가?
- **Sample file:** `studio_process_training.csv`
- **Menu/module/method:** `분석` > `탐색적 분석` > `기술통계`, 이어서 `그래프 요약`
- **Column role:** `yield_pct`, `tensile_strength_mpa`를 분석 변수로 선택한다.
- **Option:** available-case-by-column, 그래프 point limit 500, histogram bin은 자동.
- **클릭 순서:** method 선택 > 역할 선택 > 사전점검 > `분석 실행`.
- **실행 전 확인:** 두 컬럼이 continuous이고 missing count가 0인지 확인한다.
- **예상 실제 결과:** `yield_pct` N=240, mean 80.3531, SD 4.9200, median 80.4689,
  Q1 76.7681, Q3 83.7415, range 66.9048~93.0186. `tensile_strength_mpa` mean
  430.0240, SD 13.1838, range 396.9931~468.7676이다.
- **먼저 읽을 값:** N/exclusions, mean/median, SD/IQR, min/max, boxplot outlier count.
- **해석 예시:** 수율의 일반적 위치는 약 80이고 관측 간 산포가 약 4.9 percentage points다.
- **과해석 금지:** histogram 모양만으로 정규성, 안정성 또는 원인을 확정하지 않는다.
- **예상 warning:** 그래프는 진단 도구이며 자동 검정 선택 규칙이 아니다.
- **오류 확인:** 숫자 컬럼이 nominal/string으로 확정되지 않았는지, filter 후 N=0인지 본다.

## 13. 가설검정

### Supplier 2-표본 t-검정

- **사용자 질문:** 두 synthetic supplier의 평균 수율 차이가 0과 다른가?
- **Sample file:** `studio_process_training.csv`
- **Menu/module/method:** `가설검정` > `2-표본 t-검정`
- **Column role:** Response=`yield_pct`, Group=`supplier`.
- **Option:** Welch, two-sided, alpha 0.05, confidence 0.95, null difference 0.
- **클릭 순서:** 역할/option 선택 > 사전점검 > `분석 실행`.
- **실행 전 확인:** 두 group이 독립 표본이라는 설계 가정을 사용자가 확인한다.
- **예상 실제 결과:** Supplier-1 N=123, mean 81.2239; Supplier-2 N=117, mean
  79.4633. 차이 1.7606, 95% CI [0.5084, 3.0128], p=0.00605, Hedges g=0.3570.
- **먼저 읽을 값:** group N/mean, mean difference와 CI, Hedges g, 그 다음 p-value.
- **해석 예시:** 이 synthetic sample에서는 Supplier-1 수율이 평균 약 1.76 높고 효과는
  작음~중간 범위다. CI가 실무적으로 충분한 차이인지 별도로 판단한다.
- **과해석 금지:** supplier가 원인이라고 단정하거나 다른 공정 조건을 무시하지 않는다.
- **예상 warning:** independence assumption, normality/variance에 따라 자동 method 전환 없음.
- **오류 확인:** group level이 정확히 2개인지, missing/filter로 group이 비지 않았는지 본다.

### Production line 일원분산분석

- **사용자 질문:** 세 synthetic line의 평균 수율이 모두 같은가?
- **Sample file:** `studio_process_training.csv`
- **Menu/module/method:** `가설검정` > `일원분산분석`
- **Column role:** Response=`yield_pct`, Group=`production_line`.
- **Option:** standard ANOVA, Tukey-Kramer, after-significant, alpha 0.05, confidence 0.95.
- **클릭 순서:** 역할/option > 사전점검 > 실행 > post-hoc table 확인.
- **실행 전 확인:** group 독립성, extreme imbalance, 분산과 residual 진단을 확인한다.
- **예상 실제 결과:** N=240, line N은 81/81/78, F(2,237)=7.8778,
  p=0.000487, eta-squared=0.06234, omega-squared=0.05421, post-hoc 수행됨.
- **먼저 읽을 값:** group mean/N, omnibus estimate와 df, effect size, post-hoc CI.
- **해석 예시:** line 간 평균 차이의 근거가 있고 line factor가 표본 변동의 약 6%와 연관된다.
- **과해석 금지:** 모든 line pair가 다르다고 보거나 line 변경이 수율을 인과적으로 개선한다고
  단정하지 않는다.
- **예상 warning:** 독립성과 등분산은 설계/진단 검토가 필요하다.
- **오류 확인:** group 수가 2개 이하인지, constant response인지, 빈 group인지 확인한다.

## 14. 범주형 분석

### Pass 1-비율

- **사용자 질문:** Pass 비율이 기준 0.80과 다른가?
- **Sample file:** `studio_process_training.csv`
- **Menu/module/method:** `범주형 분석` > `1-비율`
- **Column role:** Response=`pass_flag`, event=`Pass`.
- **Option:** null=0.80, Wilson 95% CI, two-sided, alpha 0.05.
- **클릭 순서:** event 확인 > option > 사전점검 > 실행.
- **실행 전 확인:** Pass/Fail label과 event 정의를 확인한다.
- **예상 실제 결과:** 141/240, proportion=0.5875, 95% Wilson CI
  [0.5243, 0.6479], p 약 7.21e-14, Cohen h=-0.4676.
- **먼저 읽을 값:** event count/N, proportion과 CI, effect size, p-value.
- **해석 예시:** synthetic 기준 0.80보다 관측 Pass 비율이 실질적으로 낮다.
- **과해석 금지:** 정의된 synthetic Pass rule을 실제 품질 규격처럼 사용하지 않는다.
- **예상 warning:** event label과 독립 Bernoulli 가정은 사용자가 확인한다.
- **오류 확인:** event spelling/case와 missing category를 확인한다.

### Line x Pass 카이제곱

- **사용자 질문:** production line과 Pass/Fail이 연관되는가?
- **Sample file:** `studio_process_training.csv`
- **Menu/module/method:** `범주형 분석` > `카이제곱 독립성 검정`
- **Column role:** Row=`production_line`, Column=`pass_flag`.
- **Option:** Pearson chi-square, alpha 0.05.
- **클릭 순서:** 두 category 선택 > 사전점검 > 실행.
- **실행 전 확인:** 같은 행이 중복 집계가 아닌 독립 관측인지 확인한다.
- **예상 실제 결과:** N=240, chi-square(2)=3.7212, p=0.1556,
  Cramer's V=0.1245. 최소 expected count=32.175, 5 미만 cell=0.
- **먼저 읽을 값:** contingency counts, expected-count summary, V와 CI 지원 범위, p-value.
- **해석 예시:** 이 표본에서는 line과 Pass/Fail 연관의 강한 근거가 없고 효과도 작다.
- **과해석 금지:** p>0.05를 완전한 독립의 증명으로 해석하지 않는다.
- **예상 warning:** independence assumption, continuity correction 미사용.
- **오류 확인:** sparse table이면 expected count warning과 Fisher 적용 가능 범위를 확인한다.

## 15. 상관관계

### Pearson과 X-Y 상관행렬

- **사용자 질문:** 공정 X와 두 Y 사이 선형 연관의 방향과 크기는 무엇인가?
- **Sample file:** `studio_process_training.csv`
- **Menu/module/method:** `상관관계 및 회귀` > `Pearson 상관`, 이어서 `X-Y 상관행렬`.
- **Column role:** Pearson X=`temperature_c`, Y=`yield_pct`. Matrix X는 5 numeric
  predictors, Y는 `yield_pct`, `tensile_strength_mpa`.
- **Option:** 95% CI, alpha 0.05; matrix는 pairwise complete case.
- **클릭 순서:** columns > 사전점검 > 실행 > 5 x 2 cells 확인.
- **실행 전 확인:** scatterplot의 비선형성, outlier, changing N을 확인한다.
- **예상 실제 결과:** temperature-yield r=0.47947, 95% CI [0.37565, 0.57141],
  p 약 3.36e-15, r-squared=0.22989. Matrix는 10 pairs, 각 N=240이다.
- **먼저 읽을 값:** N, scatterplot, r와 CI, 그 다음 p-value.
- **해석 예시:** temperature와 yield는 중간 정도의 양의 선형 연관을 보인다.
- **과해석 금지:** 상관을 원인, 최적 조건, 개별 예측 정확도로 해석하지 않는다.
- **예상 warning:** pairwise N, multiple comparisons, 비선형 패턴을 별도 검토한다.
- **오류 확인:** constant/non-numeric column과 filter 후 pair N을 확인한다.

## 16. 회귀모형 적합

- **사용자 질문:** 6개 predictor와 선택한 곡률/상호작용으로 수율을 설명할 수 있는가?
- **Sample file:** `studio_process_training.csv`
- **Menu/module/method:** `상관관계 및 회귀` > `회귀모형 적합`
- **Column role:** Response=`yield_pct`; predictors=5 numeric X + `material_grade`.
- **Option:** intercept 포함, standard covariance, 95% CI, quadratic=`temperature_c`,
  `pressure_bar`, interaction=`temperature_c * pressure_bar`.
- **클릭 순서:** 역할 > term 선택 > 사전점검 > 실행 > model manifest 저장 확인.
- **실행 전 확인:** leakage 보조 컬럼을 제외하고, categorical reference와 hierarchy를 확인한다.
- **예상 실제 결과:** N=240, exclusions=0, R-squared 약 0.750,
  adjusted R-squared 약 0.739. temperature 주효과 양수, 두 quadratic term 음수,
  temperature-pressure interaction 양수다. app-created model asset이 생성된다.
- **먼저 읽을 값:** N/exclusions, R-squared와 adjusted R-squared, coefficient estimate/CI,
  residual/influence diagnostics, warnings.
- **해석 예시:** 선택한 synthetic 조건 범위에서 모형이 수율 변동의 약 75%를 설명한다.
  음의 quadratic term은 범위 안 곡률을 나타낸다.
- **과해석 금지:** main-effect coefficient는 quadratic/interaction이 있을 때 단독 전체 효과가
  아니며, 회귀모형은 인과관계나 범위 밖 정확도를 보장하지 않는다.
- **예상 warning:** high condition number/VIF, standardized residual, leverage, Cook's distance,
  categorical treatment coding, associational-not-causal.
- **오류 확인:** singular terms, exact collinearity, reference level, stale source schema를 확인한다.

## 17. Top-level Predict

- **사용자 질문:** 저장된 fit을 새로운 48행에 적용하면 평균 반응과 개별 불확실성은 얼마인가?
- **Sample file:** source=`studio_process_training.csv`, target=`studio_process_prediction.csv`.
- **Menu/module/method:** `상관관계 및 회귀` > `예측` (`사용 가능 · 전용`).
- **Column role:** 저장된 source 회귀모형 선택, target dataset version 선택.
- **Option:** confidence 0.95, complete-case, intervals 포함.
- **클릭 순서:** model > target > `예측 사전점검` > `예측 실행` > page/CSV.
- **실행 전 확인:** source fresh, manifest checksum, target schema mapping, unseen levels,
  training range warnings를 확인한다.
- **예상 실제 결과:** preflight ready, total/usable 48/48, numeric extrapolation warning 4건,
  excluded 0, CSV 48행. 첫 predicted mean은 약 81.5367이고 mean CI는
  [80.5866, 82.4868], prediction interval은 [76.4940, 86.5795]다.
- **먼저 읽을 값:** source/target IDs, usable/excluded N, extrapolation, predicted mean,
  mean-response CI와 individual prediction interval.
- **해석 예시:** 첫 조건의 평균 반응 추정은 약 81.54지만 새 개별 관측의 범위는 더 넓다.
- **과해석 금지:** prediction은 확정값이 아니다. Mean CI는 같은 조건 평균의 불확실성이고
  prediction interval은 새 개별 관측 불확실성을 포함한다.
- **예상 warning:** display-name mapping, schema hash 차이, 4개 range extrapolation,
  OLS interval assumptions.
- **오류 확인:** stale source는 현재 schema로 재적합한다. Invalid sample의 missing
  `feed_rate_kg_h`, unseen D, nonnumeric pressure, missing catalyst를 수정한다.

URL에는 `model_id`, `target_version_id`, `prediction_id`만 남는다. Reload는 계산을 반복하지
않고 checksum-validated stored result와 rows를 복원한다.

## 18. Run Chart와 Individuals Chart

- **사용자 질문:** 관측 순서에서 비무작위 패턴이나 관리 한계 신호가 있는가?
- **Sample file:** `studio_process_training.csv`
- **Menu/module/method:** `품질 분석` > `런 차트`; 비교 학습으로 `개별값 관리도`.
- **Column role:** Value=`yield_pct`, Order=`timestamp`.
- **Option:** run chart median, trend 6, oscillation 14, alpha 0.05, point limit 500.
- **클릭 순서:** 역할/규칙 > 사전점검 > 실행 > signal list.
- **실행 전 확인:** timestamp가 실제 synthetic 순서이고 duplicate/missing이 없는지 본다.
- **예상 실제 결과:** Run Chart N=240, center median=80.4689, points=240, signal=0.
- **먼저 읽을 값:** order source, N/exclusions, center, rule definition과 signal 위치.
- **해석 예시:** 활성화된 run-chart 규칙에서는 신호가 검출되지 않았다.
- **과해석 금지:** Run Chart는 control chart가 아니며 신호 0이 안정성을 증명하지 않는다.
- **예상 warning:** not-control-chart, datetime order, 정의된 trend/oscillation/runs test.
- **오류 확인:** order type, duplicate order, missing value와 point cap을 확인한다.

## 19. Capability

- **사용자 질문:** 선언한 synthetic spec 안에서 수율 산포가 충분히 좁은가?
- **Sample file:** `studio_process_training.csv`
- **Menu/module/method:** `품질 분석` > `공정능력 분석`
- **Column role:** Value=`yield_pct`.
- **Option:** LSL=68, USL=92, Target=82, normal distribution, histogram limit 30.
- **클릭 순서:** value/spec > 사전점검 > 실행.
- **실행 전 확인:** spec limit이 control limit이 아니며 공정 안정성과 측정시스템을 별도 검토한다.
- **예상 실제 결과:** N=240, Cp=0.8009, Cpk=0.7773, Pp=0.8130, Ppk=0.7891.
- **먼저 읽을 값:** spec, N, mean/sigma estimator, Cp/Cpk와 Pp/Ppk, nonconformance.
- **해석 예시:** 이 synthetic spec에 대해 point estimate가 1보다 작아 산포/중심 개선 검토가 필요하다.
- **과해석 금지:** normal/stable process가 증명됐다고 하거나 confidence interval 없는 index를
  정밀한 장기 보장으로 사용하지 않는다.
- **예상 warning:** normal assumed, stability not proven, measurement not verified, no index CI.
- **오류 확인:** LSL<USL, numeric/nonconstant value, 충분한 N을 확인한다.

## 20. P Chart와 Phase II monitoring

- **사용자 질문:** stable baseline frozen limit로 신규 48개 비율을 monitoring할 수 있는가?
- **Sample file:** Phase I=`studio_process_training.csv`; Phase II=`studio_process_prediction.csv`.
- **Menu/module/method:** `품질 분석` > `계수형 관리도` > P chart.
- **Column role:** count=`defectives_count`, denominator=`inspected_count`.
- **Option:** Phase I, defectives, complete-case; 승격 후 Phase II에서 limit set과 target 선택.
- **클릭 순서:** Phase I 실행 > eligibility 확인 > limit set 생성 > target upload >
  monitoring preflight > Phase II 실행.
- **실행 전 확인:** count는 integer 0~denominator, denominator>0, 같은 의미/단위를 확인한다.
- **예상 실제 결과:** Phase I center=0.0599591, points=240, signals=0, limit set 승격 가능.
  Phase II points=48, signals=0, Pearson dispersion available, ratio=1.80186.
- **먼저 읽을 값:** frozen source dependency, target N, center/LCL/UCL, strict outside signals,
  dispersion availability.
- **해석 예시:** 48개 monitoring point는 이 frozen 3-sigma limits 밖 신호가 없다.
- **과해석 금지:** Phase II에서 baseline을 자동 재적합하지 않으며 signal 0을 무결점으로 보지 않는다.
- **예상 warning:** schema-only preflight 뒤 실제 행/필터는 실행 시 다시 검증한다.
- **오류 확인:** NP varying denominator, count>denominator, noninteger, zero usable point를 본다.

## 21. Gage R&R

- **사용자 질문:** 측정시스템 변동이 part-to-part 변동보다 충분히 작은가?
- **Sample file:** `studio_gage_rr.csv`
- **Menu/module/method:** `품질 분석` > `Gage R&R`
- **Column role:** Measurement=`measurement_mpa`, Part=`part_id`, Operator=`operator_id`,
  Replicate=`replicate`.
- **Option:** balanced crossed ANOVA, complete-case.
- **클릭 순서:** 역할 > Gage preflight > balanced 확인 > 실행.
- **실행 전 확인:** 10 x 3 cells마다 replicate 2개가 있고 ID가 비어 있지 않은지 본다.
- **예상 실제 결과:** N=60, balanced=true, repeatability %study variation=3.9713,
  reproducibility=10.5090, total Gage R&R=11.2344, part-to-part=99.3669, ndc=12.
- **먼저 읽을 값:** design completeness, variance components, %contribution/%study variation, ndc.
- **해석 예시:** synthetic part 구분력은 크지만 reproducibility 개선 여지는 남는다.
- **과해석 금지:** 한 study로 모든 측정 범위/시간/operator의 적합성을 보장하지 않는다.
- **예상 warning:** balanced crossed/independence assumptions, interaction not pooled, labels redacted.
- **오류 확인:** missing cell, duplicate replicate, numeric measurement, balanced design을 확인한다.

## 22. Factorial DOE

- **사용자 질문:** 세 요인의 main effect와 temperature-pressure interaction은 무엇인가?
- **Sample file:** `studio_factorial_responses.csv`
- **Menu/module/method:** `실험계획법` > `실험 계획 생성`
- **Column role:** factors temperature 68/84, pressure 7/13, catalyst 0.8/2.2; response yield.
- **Option:** replicates=2, center points=0, randomize=false, seed=20260718, block=1.
- **클릭 순서:** 설계 생성 > run table actual coordinates와 CSV를 맞춤 > 16 responses 저장 >
  max interaction order 2 > 분석 실행.
- **실행 전 확인:** UI run order와 파일의 factor coordinates/replicate를 함께 확인한다.
- **예상 실제 결과:** N=16, residual df=9. 효과 크기 순서는 temperature 6.8707,
  pressure 3.9555, temperature-pressure 3.3892, catalyst 0.8814 순이다.
- **먼저 읽을 값:** coding, hierarchy, effect estimate/CI, ANOVA residual, diagnostics.
- **해석 예시:** synthetic 범위에서는 temperature main effect와 temperature-pressure
  interaction이 주요하다.
- **과해석 금지:** effect를 범위 밖 최적 조건이나 인과 보장의 전부로 보지 않는다.
- **예상 warning:** associational/confirmation, hierarchy와 fixed two-level region 제한.
- **오류 확인:** response count/run order mismatch, 분석 후 response lock을 확인한다.

## 23. RSM

- **사용자 질문:** temperature-pressure 영역 안에서 곡률과 stationary maximum은 어디인가?
- **Sample file:** `studio_rsm_responses.csv`
- **Menu/module/method:** `실험계획법` > `반응표면법`
- **Column role:** temperature 65~85 C, pressure 6~14 bar, response=`yield_pct`.
- **Option:** face-centered, factorial/axial replicate=1, center=5, randomize=false,
  seed=20260718, confidence 0.95, contour 21.
- **클릭 순서:** CCD 생성 > coordinates 매칭 > 13 responses 저장 > quadratic model 실행.
- **실행 전 확인:** center 반복과 pure error, factor region, response lock 안내를 확인한다.
- **예상 실제 결과:** R-squared=0.99874, adjusted=0.99784. Stationary maximum은
  temperature 약 76.4437, pressure 9.6718, predicted response 90.9986이며 region 안이다.
  Lack-of-fit F=0.5212, p=0.6904로 blocking되지 않는다.
- **먼저 읽을 값:** rank/df, coefficient/ANOVA, lack-of-fit, stationary classification/region,
  contour와 residual diagnostics.
- **해석 예시:** 설정한 synthetic region 안에 fitted stationary maximum 후보가 있다.
- **과해석 금지:** R-squared가 높아도 confirmation run, model assumptions와 region 제한이 남는다.
- **예상 warning:** associational, contour slice/confirmation, influential point review.
- **오류 확인:** source eligibility의 blocking/advisory, response revision과 checksum을 확인한다.

## 24. Top-level Response Optimizer

- **사용자 질문:** 저장된 RSM에서 yield를 maximize하는 bounded candidate는 무엇인가?
- **Sample file:** source=`studio_rsm_responses.csv`로 만든 stored RSM analysis.
- **Menu/module/method:** `상관관계 및 회귀` > `반응 최적화` (`사용 가능 · 전용`).
- **Column role:** stored source RSM analysis, response goal maximize.
- **Option:** source contour lower/target, design bounds 유지, seed 20260718,
  candidates 256, multi-start 8, max evaluations 5000, time 5000ms.
- **클릭 순서:** source 선택 > eligibility 확인/필요 warning 승인 > goal/bounds > 실행.
- **실행 전 확인:** blocker 없음, advisory는 code별 명시 승인, constraints와 bounds를 검토한다.
- **예상 실제 결과:** recommended temperature 약 76.5545, pressure 9.6828,
  predicted response 90.9982, composite desirability 1.0, termination search_completed.
- **먼저 읽을 값:** source model, goal/threshold, coordinates, predicted response, desirability,
  constraint slack, termination reason.
- **해석 예시:** fitted model과 선언한 region/goal 아래의 확인 실험 후보다.
- **과해석 금지:** 전역 최적을 보장하지 않고 uncertainty-aware desirability가 아니며 실제 관측이 아니다.
- **예상 warning:** global optimum not guaranteed, confirmation run required, point prediction,
  model adequacy review.
- **오류 확인:** ineligible/stale/tampered source, acknowledgment code와 bound 순서를 확인한다.

URL의 `design_id`, `analysis_id`, `optimization_id`는 reload 후 checksum-validated stored result를
복원한다. 재계산하지 않는다.

## 25. Bayesian Optimization

- **사용자 질문:** 수동 관측 5개 뒤 다음 확인 실험 후보는 어디인가?
- **Sample file:** `studio_bayesian_observations.csv`
- **Menu/module/method:** `실험계획법` > `베이지안 최적화`
- **Column role:** factors temperature 60~90, pressure 5~15; objective yield maximize.
- **Option:** initial size 5, seed 20260718, no constraints; recommendation seed 20260718,
  candidate 128, local start 4, xi 0.01, trial budget 20.
- **클릭 순서:** study 생성 > trial number/coordinates 대조 > 각 objective 저장 확인 > 추천 요청.
- **실행 전 확인:** objective value와 coordinates, 저장 후 수정 불가, pending trial 없음 확인.
- **예상 실제 결과:** completed observations=5. 추천은 temperature 약 61.2818,
  pressure 11.4636, predicted mean 83.9666, posterior SD 4.2736, EI 0.2677,
  recommendation trial은 pending이다.
- **먼저 읽을 값:** completed N/history SHA, GP model warning, predicted mean/SD, EI,
  actual coordinates, pending/completed/abandoned state.
- **해석 예시:** 큰 uncertainty와 EI를 고려해 다음 확인 후보를 제시한 것이다.
- **과해석 금지:** 추천은 실제 관측이 아니고 전역 최적을 보장하지 않으며 Studio가 실험을
  자동 실행하지 않는다.
- **예상 warning:** model convergence warning, confirmation required, no global optimum guarantee.
- **오류 확인:** history revision conflict, pending recommendation, trial budget, duplicate/abandoned
  coordinates, time budget code를 확인한다.

## 26. 저장 분석 history

Generic analysis-run method는 dataset-scoped `분석 이력`에서 status, method version, stale,
result availability를 filter하고 저장 결과를 복원한다. Predict와 Response Optimizer 같은
dedicated workflow는 관계없는 generic history를 표시하지 않고 각 전용 panel/URL에서 결과를
복원한다.

## 27. 결과 비교

같은 의미의 compatible stored analysis 두 개를 선택해 N, config, warnings, 주요 result 차이를
비교한다. 서로 다른 method/version/schema를 억지로 같은 숫자로 비교하지 않는다. Stale 여부와
source dataset version을 함께 읽는다.

## 28. JSON/CSV/HTML export

- JSON: full structured result/provenance 검토
- CSV: method가 정의한 tabular summary 또는 full prediction rows
- HTML: self-contained 정적 보고서

Export 전에 method/version, dataset/source IDs, N/exclusions, warnings와 stale 상태를 확인한다.
CSV는 formula injection 방어가 적용되며 internal path나 raw predictor 값이 prediction result에
추가되지 않는다.

## 29. 삭제와 retention 주의사항

삭제 preflight가 blocker와 정확한 영향 count를 보여준다. 분석이 참조하는 model, prediction,
limit set, study/design artifact는 block-by-default다. Source fit result와 예측용 model asset은
서로 다른 자산이다. Model asset이 unavailable이면 fit table은 남을 수 있지만 새 Predict는
비활성화된다. 확인 ID/hash를 읽고 irreversible action을 승인한다.

## 30. 자주 발생하는 오류

| 증상/code 의미 | 확인 방법 |
| --- | --- |
| `api_unreachable` | backend 실행, `127.0.0.1` bind, port와 frontend API base 확인 |
| parsing preview 차이 | Browser grid는 staging, server confirmation이 authoritative |
| zero usable rows | filter, missing/non-numeric, schema type 확인 |
| source model stale | 현재 source schema로 Linear Model 재적합 |
| prediction schema/unseen level | predictor 이름/type, category A/B/C, invalid sample 오류 확인 |
| optimizer source ineligible | rank, residual variance/df, lack-of-fit, checksum 검토 |
| Bayesian history conflict | 최신 study/history reload 후 terminal action 재확인 |
| stored result integrity error | 재계산으로 덮지 말고 checksum/dependency 손상을 별도 처리 |

오류 응답에는 raw cell, filename, traceback, internal absolute path가 없어야 한다.

## 31. 결과로 말할 수 있는 것

- 정의한 sample/filter에서의 estimate, CI, effect size와 N/exclusions
- 선택한 method와 가정 아래의 통계적 불확실성
- fitted regression/RSM의 선언된 범위 안 model-based prediction/recommendation
- frozen Phase II limits 밖 strict signal 존재 여부
- Bayesian surrogate가 현재 관측 이력 아래 제안한 다음 확인 후보

## 32. 결과로 말할 수 없는 것

- 관측 연관만으로 입증된 인과관계
- p-value 하나만으로 실무적 중요성 또는 재현성
- 신호가 없다는 이유로 증명된 안정성/무결점
- 높은 R-squared가 보장하는 범위 밖 정확도
- Predict/Optimizer/Bayesian recommendation의 확정값 또는 전역 최적 보장
- 자동으로 증명된 independence, normality, homoscedasticity, MAR/MNAR

## 33. 다음 학습 경로

1. 같은 dataset에서 filter snapshot을 바꾸고 N/exclusions 변화를 비교한다.
2. Invalid prediction sample을 사전점검해 오류를 하나씩 수정한다.
3. RSM bounds/goal을 바꾸되 source eligibility와 confirmation run 원칙을 유지한다.
4. Bayesian recommendation을 실제 synthetic formula로 확인한 뒤 observation을 terminal 저장한다.
5. `scripts/tutorial_smoke.ps1`로 문서 수치와 현재 Studio API가 계속 일치하는지 검증한다.
