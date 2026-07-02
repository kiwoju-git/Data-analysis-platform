export interface MethodRoleRequirement {
  label: string;
  required: boolean;
  detail: string;
}

export interface AnalysisMethodGuidance {
  methodId: string;
  roleRequirements: readonly MethodRoleRequirement[];
  optionChecklist: readonly string[];
  preflightChecks: readonly string[];
  resultFocus: readonly string[];
  plainLanguage?: string;
  commonErrors?: readonly string[];
}

function required(label: string, detail: string): MethodRoleRequirement {
  return { label, required: true, detail };
}

function optional(label: string, detail: string): MethodRoleRequirement {
  return { label, required: false, detail };
}

export const analysisMethodGuidance = {
  "eda.descriptive": {
    methodId: "eda.descriptive",
    roleRequirements: [
      required("분석 변수", "수치형 컬럼 1개 이상"),
      optional("그룹", "그룹별 요약은 다음 slice에서 확장"),
    ],
    optionChecklist: ["결측 처리 정책", "표시할 통계량", "분위수 계산 방식"],
    preflightChecks: ["수치 파싱 가능 여부", "결측 수", "상수열", "ID 역할 제외"],
    resultFocus: ["N/결측", "평균/표본 표준편차", "중앙값/IQR", "범위"],
  },
  "eda.graphical_summary": {
    methodId: "eda.graphical_summary",
    roleRequirements: [required("분석 변수", "수치형 또는 범주형 컬럼"), optional("그룹", "패널 또는 색상 구분")],
    optionChecklist: ["히스토그램 bin", "박스플롯 표시", "Q-Q plot 표시"],
    preflightChecks: ["표본 수", "고유값 수", "극단값 후보", "렌더링 비용"],
    resultFocus: ["분포 모양", "이상 후보", "그룹 비교 시각화"],
  },
  "eda.normality": {
    methodId: "eda.normality",
    roleRequirements: [required("분석 변수", "연속형 수치 컬럼"), optional("그룹", "그룹별 정규성 점검")],
    optionChecklist: ["유의수준", "Q-Q plot", "Shapiro-Wilk/Anderson-Darling"],
    preflightChecks: ["표본 수 범위", "상수열", "비정규 자동 전환 금지", "결측 제외 수"],
    resultFocus: ["Q-Q plot", "검정통계량", "p-value", "정규성 한계 경고"],
  },
  "eda.equal_variances": {
    methodId: "eda.equal_variances",
    roleRequirements: [required("반응", "연속형 수치 컬럼"), required("그룹", "2개 이상 그룹 컬럼")],
    optionChecklist: ["Brown-Forsythe/Levene", "유의수준", "결측 처리"],
    preflightChecks: ["그룹 수", "그룹별 N", "상수 그룹", "비정규성 민감도"],
    resultFocus: ["그룹별 산포", "검정통계량", "p-value", "Welch 대안 안내"],
  },
  "hypothesis.one_sample_t": {
    methodId: "hypothesis.one_sample_t",
    roleRequirements: [required("반응", "연속형 수치 컬럼"), required("기준값", "비교할 모집단 평균")],
    optionChecklist: ["대립가설", "유의수준", "신뢰수준", "결측 처리"],
    preflightChecks: ["유효 N", "상수열", "정규성은 보조 점검", "기준값 입력"],
    resultFocus: ["평균 차이", "95% CI", "t 통계량/df", "효과크기"],
    plainLanguage:
      "한 숫자 컬럼의 평균이 사용자가 입력한 기준 평균과 다르다고 볼 근거가 있는지 확인합니다. 예를 들어 평균 두께가 목표 10과 다른지 보는 검정입니다.",
    commonErrors: [
      "반응 변수에 문자 컬럼이나 ID 컬럼을 고른 경우",
      "기준 평균이 비어 있거나 숫자가 아닌 경우",
      "필터나 결측 때문에 사용 가능한 숫자 값이 2개 미만인 경우",
    ],
  },
  "hypothesis.paired_t": {
    methodId: "hypothesis.paired_t",
    roleRequirements: [
      required("전/후 반응", "쌍을 이루는 수치 컬럼 2개"),
      required("쌍 ID", "long 형식에서는 subject/pair ID"),
    ],
    optionChecklist: ["대립가설", "신뢰수준", "불완전 쌍 처리"],
    preflightChecks: ["쌍 매칭", "불완전 쌍 수", "차이값 상수 여부", "결측 제외 수"],
    resultFocus: ["평균 차이", "차이의 CI", "paired t", "효과크기"],
    plainLanguage:
      "같은 대상의 전/후 또는 두 조건 측정값을 비교합니다. 각 행에서 두 번째 측정값에서 첫 번째 측정값을 뺀 차이의 평균을 검정합니다.",
    commonErrors: [
      "전 측정과 후 측정에 같은 컬럼을 고른 경우",
      "둘 중 하나가 숫자 컬럼이 아닌 경우",
      "한쪽 값이 빠진 행이 많아 complete pair가 부족한 경우",
    ],
  },
  "hypothesis.two_sample_t": {
    methodId: "hypothesis.two_sample_t",
    roleRequirements: [required("반응", "연속형 수치 컬럼"), required("그룹", "정확히 2개 그룹")],
    optionChecklist: ["Welch 기본", "대립가설", "신뢰수준", "결측 처리"],
    preflightChecks: ["그룹별 N", "빈 그룹", "상수 그룹", "독립성 설계 확인"],
    resultFocus: ["평균 차이", "95% CI", "Welch df", "Hedges g"],
    plainLanguage:
      "두 독립 그룹의 평균 차이를 비교합니다. 기본은 Welch 방식이라 두 그룹의 분산이 같다고 강하게 가정하지 않습니다.",
    commonErrors: [
      "그룹 컬럼에 실제 그룹이 정확히 2개가 아닌 경우",
      "반응 변수와 그룹 변수에 같은 컬럼을 고른 경우",
      "필터 후 한 그룹이 비거나 값이 모두 같은 경우",
    ],
  },
  "hypothesis.one_way_anova": {
    methodId: "hypothesis.one_way_anova",
    roleRequirements: [required("반응", "연속형 수치 컬럼"), required("요인", "2개 이상 독립 그룹")],
    optionChecklist: ["표준 ANOVA", "Tukey-Kramer 사후비교", "유의한 omnibus 후 사후비교", "결측 처리"],
    preflightChecks: ["그룹별 N", "잔차 정규성 설계 확인", "등분산 가정", "상수 그룹"],
    resultFocus: ["ANOVA table", "F 통계량/p-value", "eta/omega squared", "Tukey-Kramer 비교"],
    plainLanguage:
      "세 개 이상 그룹의 평균이 모두 같다고 보기 어려운지 먼저 확인합니다. 전체 검정이 유의할 때만 어떤 그룹끼리 다른지 사후비교를 보여줍니다.",
    commonErrors: [
      "그룹 컬럼에 사용 가능한 그룹이 2개 미만인 경우",
      "반응 변수가 숫자 컬럼이 아닌 경우",
      "그룹 안 값이 모두 같거나 결측 제외 후 그룹별 N이 부족한 경우",
    ],
  },
  "hypothesis.equivalence_tost": {
    methodId: "hypothesis.equivalence_tost",
    roleRequirements: [
      required("반응", "연속형 수치 컬럼"),
      required("기준 평균", "비교할 모집단 평균"),
      required("동등성 한계", "원 단위 평균 차이 하한/상한"),
    ],
    optionChecklist: ["1표본 평균 설계", "동등성 한계", "유의수준", "결측 처리"],
    preflightChecks: ["한계값 방향", "유효 N", "상수열", "동등성 한계 사전 지정"],
    resultFocus: ["두 단측검정 p-value", "TOST 판정", "CI와 동등성 한계", "Cohen dz"],
    plainLanguage:
      "평균이 기준값과 '충분히 비슷하다'고 볼 근거를 확인합니다. 일반 t-test에서 차이가 안 난다는 결과만으로 동등하다고 말할 수 없어서, 허용 가능한 차이 범위인 동등성 하한/상한을 먼저 정해야 합니다.",
    commonErrors: [
      "동등성 하한이 상한보다 크거나 같은 경우",
      "동등성 한계를 임의로 너무 넓게 잡아 결과를 좋게 만드는 경우",
      "반응 변수에 숫자 컬럼이 아닌 컬럼을 고른 경우",
    ],
  },
  "hypothesis.one_sample_wilcoxon": {
    methodId: "hypothesis.one_sample_wilcoxon",
    roleRequirements: [required("반응", "순서형 또는 연속형 컬럼"), required("기준값", "비교 위치")],
    optionChecklist: ["대립가설", "zero difference 처리", "결측 처리"],
    preflightChecks: ["0 차이 수", "동률", "유효 N", "중앙값 단정 금지"],
    resultFocus: ["signed-rank 통계량", "p-value", "rank 기반 효과크기"],
    plainLanguage:
      "한 컬럼의 값들이 기준 위치보다 전반적으로 크거나 작은지 순위 기반으로 봅니다. 정규성 가정이 부담스러울 때 쓰지만, 자동 대체 검정은 아닙니다.",
    commonErrors: [
      "기준값과 정확히 같은 값이 많아 zero difference 처리가 필요한 경우",
      "exact 방식을 요청했지만 동률이나 0 차이가 있는 경우",
      "결과를 무조건 중앙값 차이로만 해석하는 경우",
    ],
  },
  "hypothesis.mann_whitney": {
    methodId: "hypothesis.mann_whitney",
    roleRequirements: [required("반응", "순서형 또는 연속형 컬럼"), required("그룹", "정확히 2개 독립 그룹")],
    optionChecklist: ["대립가설", "exact/asymptotic", "결측 처리"],
    preflightChecks: ["그룹별 N", "동률", "독립성 설계 확인", "분포 차이 해석"],
    resultFocus: ["U 통계량", "p-value", "rank-biserial 효과크기"],
    plainLanguage:
      "두 독립 그룹의 값 분포가 한쪽으로 더 크거나 다른지 순위로 비교합니다. 평균 차이 검정이 아니라 순위 기반 비교입니다.",
    commonErrors: [
      "그룹이 정확히 2개가 아닌 경우",
      "exact 방식을 요청했지만 동률이 있는 경우",
      "결과를 단순히 중앙값 차이라고만 해석하는 경우",
    ],
  },
  "hypothesis.kruskal_wallis": {
    methodId: "hypothesis.kruskal_wallis",
    roleRequirements: [required("반응", "순서형 또는 연속형 컬럼"), required("그룹", "3개 이상 독립 그룹")],
    optionChecklist: ["Dunn 사후검정", "Holm 보정", "결측 처리"],
    preflightChecks: ["그룹별 N", "동률", "빈 그룹", "사후검정 보정"],
    resultFocus: ["H 통계량", "p-value", "사후비교", "효과크기"],
    plainLanguage:
      "세 개 이상 독립 그룹을 순위 기반으로 비교합니다. 전체 검정이 유의할 때만 Dunn/Holm 사후비교로 어떤 그룹 차이가 큰지 봅니다.",
    commonErrors: [
      "사용 가능한 그룹이 3개 미만인 경우",
      "필터 후 일부 그룹이 비는 경우",
      "전체 검정이 유의하지 않은데 사후비교를 기대하는 경우",
    ],
  },
  "categorical.one_proportion": {
    methodId: "categorical.one_proportion",
    roleRequirements: [required("사건/비사건", "이진 반응 컬럼과 사건 수준")],
    optionChecklist: ["기준 비율", "대립가설", "신뢰수준", "CI 방식"],
    preflightChecks: ["사건 수", "전체 N", "이진 수준 확인", "독립성 설계 확인"],
    resultFocus: ["비율 추정치", "CI", "exact binomial p-value", "Cohen h"],
    plainLanguage:
      "예/아니오처럼 두 수준인 컬럼에서 사건 비율이 기준 비율과 다른지 확인합니다.",
    commonErrors: [
      "사건 수준에 실제 데이터에 없는 값을 입력한 경우",
      "반응 컬럼이 이진 컬럼이 아닌 경우",
      "기준 비율이 0과 1 사이가 아닌 경우",
    ],
  },
  "categorical.two_proportion": {
    methodId: "categorical.two_proportion",
    roleRequirements: [required("결과", "이진 반응 컬럼"), required("그룹", "정확히 2개 그룹")],
    optionChecklist: ["사건 수준", "대립가설", "신뢰수준", "complete-case 결측 처리"],
    preflightChecks: ["그룹별 사건 수", "그룹별 N", "기대도수", "독립성 설계 확인"],
    resultFocus: ["비율 차이", "Newcombe-Wilson CI", "Fisher exact p-value", "risk/odds ratio"],
    plainLanguage:
      "두 그룹의 사건 비율이 다른지 비교합니다. 현재는 정확히 2개 그룹과 이진 반응 컬럼을 사용합니다.",
    commonErrors: [
      "그룹이 정확히 2개가 아닌 경우",
      "사건 수준이 실제 반응 값과 일치하지 않는 경우",
      "반응 변수와 그룹 변수에 같은 컬럼을 고른 경우",
    ],
  },
  "categorical.chi_square_association": {
    methodId: "categorical.chi_square_association",
    roleRequirements: [required("행 변수", "범주형 컬럼"), required("열 변수", "범주형 컬럼")],
    optionChecklist: ["Pearson 카이제곱", "유의수준", "complete-case 결측 처리"],
    preflightChecks: ["분할표 크기", "기대도수", "희소 2x2 Fisher 권고", "결측 제외 수"],
    resultFocus: ["카이제곱 통계량", "df", "p-value", "Cramer's V", "기대도수 진단"],
    plainLanguage:
      "두 범주형 변수가 서로 독립이라고 보기 어려운지 확인합니다. 예를 들어 그룹과 합격/불합격이 관련 있어 보이는지 보는 검정입니다.",
    commonErrors: [
      "행 변수와 열 변수에 같은 컬럼을 고른 경우",
      "ID처럼 고유값이 너무 많은 컬럼을 범주형 변수로 고른 경우",
      "기대도수가 작아 Fisher exact 같은 다른 방법을 검토해야 하는 경우",
    ],
  },
  "regression.pearson": {
    methodId: "regression.pearson",
    roleRequirements: [required("X", "연속형 수치 컬럼"), required("Y", "연속형 수치 컬럼")],
    optionChecklist: ["신뢰수준", "다중비교 보정", "결측 처리"],
    preflightChecks: ["쌍별 N", "상수열", "비선형 패턴", "이상점 후보"],
    resultFocus: ["상관계수", "CI", "p-value", "산점도 진단"],
    plainLanguage:
      "두 숫자 컬럼이 함께 증가하거나 감소하는 선형 관계가 있는지 요약합니다. r은 -1에서 1 사이이며, 1에 가까울수록 같은 방향, -1에 가까울수록 반대 방향 선형 관계가 강합니다.",
    commonErrors: [
      "X와 Y에 같은 컬럼을 고른 경우",
      "둘 중 하나가 숫자 컬럼이 아니거나 ID 컬럼인 경우",
      "필터/결측/문자값 제외 후 사용 가능한 쌍이 4개 미만인 경우",
      "상관을 인과관계로 해석하는 경우",
    ],
  },
  "regression.xy_correlation": {
    methodId: "regression.xy_correlation",
    roleRequirements: [required("X 변수 집합", "수치 컬럼 1개 이상"), required("Y 변수 집합", "수치 컬럼 1개 이상")],
    optionChecklist: ["Pearson pairwise 상관", "신뢰수준", "pairwise complete-case 결측 처리"],
    preflightChecks: ["변수별 N", "상수열", "쌍별 결측 변화", "상관행렬 크기"],
    resultFocus: ["교차 상관행렬", "p-value", "Fisher z CI", "유효 N"],
    plainLanguage:
      "여러 X 숫자 컬럼과 여러 Y 숫자 컬럼 사이의 선형 상관을 한 번에 표로 봅니다. 각 칸은 하나의 X/Y 조합이므로 사용 N이 서로 다를 수 있습니다.",
    commonErrors: [
      "X 또는 Y 변수 집합에 숫자 컬럼을 하나도 고르지 않은 경우",
      "필터/결측/문자값 제외 후 특정 X/Y 조합의 사용 가능한 쌍이 4개 미만인 경우",
      "한 컬럼이 상수처럼 변하지 않아 해당 조합의 상관을 계산할 수 없는 경우",
      "상관이 큰 셀을 원인과 결과로 해석하는 경우",
    ],
  },
  "regression.linear_model": {
    methodId: "regression.linear_model",
    roleRequirements: [required("반응 변수", "연속형 수치 컬럼 1개"), required("예측변수", "숫자형 또는 범주형 컬럼 1개 이상")],
    optionChecklist: ["OLS main effects", "범주형 treatment coding", "숫자형 2차항/상호작용", "intercept 포함", "신뢰수준", "complete-case 결측 처리"],
    preflightChecks: ["사용 N과 잔차 자유도", "상수 컬럼/단일 수준 factor", "추가 항의 rank deficiency", "condition number와 VIF"],
    resultFocus: ["계수 추정치", "CI", "p-value", "R²/adjusted R²", "잔차/leverage/Cook's D"],
    plainLanguage:
      "숫자형 반응 변수 Y가 숫자형 예측변수, 범주형 factor, 선택한 숫자형 2차항/상호작용 항과 평균적으로 어떻게 함께 변하는지 OLS 선형회귀로 적합합니다. 범주형 계수는 기준 수준과 비교한 평균 차이 추정치입니다.",
    commonErrors: [
      "반응 변수와 예측변수에 같은 컬럼을 고른 경우",
      "예측변수 수에 비해 complete-case 행이 너무 적은 경우",
      "범주형 예측변수가 필터 후 한 수준만 남은 경우",
      "2차항 또는 상호작용 항이 기존 predictor와 완전히 중복되어 설계행렬이 특이해지는 경우",
      "예측변수들이 서로 완전히 중복되거나 선형 조합인 경우",
      "회귀계수를 관찰 데이터만으로 원인 효과라고 해석하는 경우",
    ],
  },
  "regression.predict": {
    methodId: "regression.predict",
    roleRequirements: [required("모델", "앱이 생성한 회귀 모델"), required("예측 데이터", "학습 스키마와 호환되는 데이터셋")],
    optionChecklist: ["예측 구간", "스키마 매핑", "내보내기 형식"],
    preflightChecks: ["모델 manifest", "스키마 drift", "범주 수준", "외삽 위험"],
    resultFocus: ["예측값", "예측/신뢰 구간", "스키마 경고"],
  },
  "regression.response_optimizer": {
    methodId: "regression.response_optimizer",
    roleRequirements: [required("검증된 모델", "회귀 또는 DOE 반응표면 모델"), required("목표", "최대/최소/목표값")],
    optionChecklist: ["요인 범위", "목표 가중치", "제약조건"],
    preflightChecks: ["모델 유효성", "설계영역", "외삽", "다중반응 목표 충돌"],
    resultFocus: ["최적 조건", "예측 반응", "desirability", "제약 경고"],
  },
  "quality.attribute_control_chart": {
    methodId: "quality.attribute_control_chart",
    roleRequirements: [required("결함/불량 수", "계수형 결과"), required("표본 크기/기회수", "p/np/c/u 차트 기준")],
    optionChecklist: ["차트 유형", "관리한계", "규칙 세트"],
    preflightChecks: ["음수/비정수", "표본 크기 변화", "과산포", "시계열 순서"],
    resultFocus: ["중심선", "관리한계", "규칙 위반점", "공정 안정성"],
  },
  "quality.individuals_chart": {
    methodId: "quality.individuals_chart",
    roleRequirements: [
      required("측정값", "연속형 수치 컬럼"),
      optional("순서", "비워두면 canonical row order, 선택하면 숫자형/날짜시간 컬럼 오름차순"),
    ],
    optionChecklist: [
      "I-MR",
      "MRbar/d2 관리한계",
      "3-sigma 밖 1점 rule",
      "중심선 한쪽 연속 9점 rule",
      "연속 6점 증가/감소 trend rule",
      "연속 14점 교대 상승/하락 rule",
      "2-sigma 밖 2-of-3 zone rule",
      "1-sigma 밖 4-of-5 zone rule",
      "1-sigma 안쪽 연속 15점 rule",
      "1-sigma 밖 연속 8점 rule",
      "complete-case 결측 처리",
    ],
    preflightChecks: [
      "선택한 순서 컬럼이 실제 시간/공정 순서인지 확인",
      "순서 컬럼 결측/파싱 실패",
      "상수열",
      "측정값 결측",
      "숫자 파싱 가능 여부",
    ],
    resultFocus: [
      "I chart",
      "MR chart",
      "관리한계",
      "관리한계 밖 점",
      "same-side/trend/alternating 신호",
      "zone 신호",
    ],
  },
  "quality.subgroup_chart": {
    methodId: "quality.subgroup_chart",
    roleRequirements: [required("측정값", "연속형 수치 컬럼"), required("부분군", "합리적 subgroup ID")],
    optionChecklist: [
      "Xbar-R 또는 Xbar-S",
      "고정 부분군 크기 2-10",
      "complete-case 결측 처리",
      "관리한계 밖 1점 rule",
    ],
    preflightChecks: [
      "부분군별 N",
      "불균형 부분군",
      "singleton subgroup",
      "평균 range/stddev 0",
      "합리적 부분군 여부",
    ],
    resultFocus: [
      "Xbar chart",
      "R/S chart",
      "부분군 평균",
      "부분군 범위 또는 표본표준편차",
      "관리한계",
      "규칙 위반",
    ],
  },
  "quality.run_chart": {
    methodId: "quality.run_chart",
    roleRequirements: [
      required("측정값", "연속형 수치 컬럼"),
      optional("순서", "비워두면 canonical row order, 선택하면 숫자형/날짜시간 컬럼 오름차순"),
    ],
    optionChecklist: [
      "median 중심선",
      "tie 제외 run count",
      "strict 6-point trend rule",
      "strict 14-point oscillation rule",
    ],
    preflightChecks: [
      "측정값 숫자 파싱 가능 여부",
      "순서 컬럼 숫자 또는 날짜시간 파싱 가능 여부",
      "날짜시간 순서 컬럼 timezone 혼합 여부",
      "동률",
      "결측 제외 수",
      "사용 가능한 숫자 값 3개 이상",
    ],
    resultFocus: ["run count", "above/below median", "trend/oscillation 신호", "관리한계 없음"],
    plainLanguage:
      "측정값이 시간 또는 실행 순서상 무작위로 흔들리는지 보는 시각화입니다. 순서 컬럼을 비우면 데이터셋의 canonical row 순서를 사용하고, 숫자형 또는 날짜시간 순서 컬럼을 선택하면 오름차순으로 정렬합니다. 관리도처럼 control limit을 만들지 않습니다.",
    commonErrors: [
      "측정값에 문자 컬럼이나 ID 컬럼을 고른 경우",
      "업로드 순서가 실제 실행 순서를 의미하지 않는 데이터에 그대로 적용하는 경우",
      "런 차트 신호를 관리도 out-of-control 신호로 해석하는 경우",
    ],
  },
  "quality.capability": {
    methodId: "quality.capability",
    roleRequirements: [
      required("측정값", "연속형 수치 컬럼"),
      required("규격", "LSL 또는 USL 중 최소 하나"),
    ],
    optionChecklist: [
      "Normal capability",
      "LSL/USL/optional target",
      "overall sample SD",
      "MRbar/d2 within sigma",
      "complete-case 결측 처리",
    ],
    preflightChecks: [
      "LSL < USL",
      "target이 spec 안에 있는지 확인",
      "상수열",
      "공정 안정성은 별도 관리도로 확인",
      "정규모형 적합성은 자동 보증하지 않음",
    ],
    resultFocus: ["Cp/Cpk", "Pp/Ppk", "관측/기대 비규격률", "histogram + spec lines"],
    plainLanguage:
      "측정값 분포가 지정한 규격 한계 안에 얼마나 들어오는지 보는 분석입니다. Spec limit은 관리한계가 아니며, 공정 안정성과 측정시스템 적합성은 별도로 확인해야 합니다.",
  },
  "quality.gage_rr": {
    methodId: "quality.gage_rr",
    roleRequirements: [
      required("측정값", "연속형 수치 컬럼"),
      required("부품", "part ID"),
      required("측정자", "operator ID"),
      required("반복", "replicate ID"),
    ],
    optionChecklist: ["balanced crossed ANOVA", "complete-case 결측 처리", "interaction 보존"],
    preflightChecks: ["균형 설계", "반복 수", "부품-측정자 조합", "raw label 비노출"],
    resultFocus: ["ANOVA table", "variance components", "%Contribution", "%Study Variation", "ndc"],
    plainLanguage:
      "측정시스템의 반복성, 재현성, 부품 간 변동을 분리해서 보는 분석입니다. 현재는 balanced crossed ANOVA 설계만 계산하며, nested/unbalanced 설계와 interaction pooling은 아직 지원하지 않습니다.",
  },
  "quality.gage_run_chart": {
    methodId: "quality.gage_run_chart",
    roleRequirements: [
      required("측정값", "연속형 수치 컬럼"),
      required("부품", "part ID"),
      required("측정자", "operator ID"),
      required("반복", "replicate ID"),
      optional("실행 순서", "숫자형 또는 날짜시간 컬럼"),
    ],
    optionChecklist: ["canonical row 또는 order column", "balanced crossed 설계", "raw label 비노출"],
    preflightChecks: ["부품-측정자 셀", "반복 ID 중복", "반복 수 균형", "결측 제외 수"],
    resultFocus: ["run-order chart", "part/operator/replicate index", "부품별 산포", "측정자별 평균"],
    plainLanguage:
      "Gage 설계 데이터를 부품, 측정자, 반복 index로 나누어 실행 순서상 패턴을 보는 진단 차트입니다. Gage R&R 분산성분 결과를 대체하지 않으며, 불완전 설계를 단순 Run Chart로 자동 변경하지 않습니다.",
  },
  "doe.factorial_design": {
    methodId: "doe.factorial_design",
    roleRequirements: [required("요인", "이름, 수준, low/high"), optional("블록", "블록 또는 반복 구조")],
    optionChecklist: ["2-level full factorial", "반복/센터점", "랜덤 seed", "run order"],
    preflightChecks: ["요인 수준", "실행 수 제한", "블록 수", "랜덤화 재현성"],
    resultFocus: ["설계표", "표준/실행 순서", "design SHA-256", "재현 seed"],
    plainLanguage:
      "현재 slice는 2-level full factorial 설계표를 생성하고 저장합니다. 반응 입력, 효과 추정, OLS/ANOVA 분석은 다음 DOE slice에서 추가합니다.",
  },
  "doe.response_surface": {
    methodId: "doe.response_surface",
    roleRequirements: [required("요인", "연속 요인과 설계영역"), required("반응", "최적화할 response")],
    optionChecklist: ["CCD/Box-Behnken", "센터점", "블록", "모형 차수"],
    preflightChecks: ["설계영역", "pure error", "alias/curvature", "외삽 위험"],
    resultFocus: ["반응표면 모델", "contour/surface", "최적 후보", "lack-of-fit"],
  },
} as const satisfies Record<string, AnalysisMethodGuidance>;

export const analysisMethodGuidanceIds = Object.keys(analysisMethodGuidance);

const guidanceById: Readonly<Record<string, AnalysisMethodGuidance>> = analysisMethodGuidance;

const fallbackGuidance: AnalysisMethodGuidance = {
  methodId: "unknown",
  roleRequirements: [required("입력 역할", "메서드별 입력 계약이 아직 정의되지 않았습니다.")],
  optionChecklist: ["메서드 계약 정의"],
  preflightChecks: ["입력 계약 정의"],
  resultFocus: ["구조화 결과 계약"],
};

export function getAnalysisMethodGuidance(methodId: string): AnalysisMethodGuidance {
  return guidanceById[methodId] ?? { ...fallbackGuidance, methodId };
}
