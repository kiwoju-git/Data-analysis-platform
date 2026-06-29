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
    preflightChecks: ["SciPy 검증", "그룹 수", "그룹별 N", "상수 그룹", "비정규성 민감도"],
    resultFocus: ["그룹별 산포", "검정통계량", "p-value", "Welch 대안 안내"],
  },
  "hypothesis.one_sample_t": {
    methodId: "hypothesis.one_sample_t",
    roleRequirements: [required("반응", "연속형 수치 컬럼"), required("기준값", "비교할 모집단 평균")],
    optionChecklist: ["대립가설", "유의수준", "신뢰수준", "결측 처리"],
    preflightChecks: ["유효 N", "상수열", "정규성은 보조 점검", "기준값 입력"],
    resultFocus: ["평균 차이", "95% CI", "t 통계량/df", "효과크기"],
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
  },
  "hypothesis.two_sample_t": {
    methodId: "hypothesis.two_sample_t",
    roleRequirements: [required("반응", "연속형 수치 컬럼"), required("그룹", "정확히 2개 그룹")],
    optionChecklist: ["Welch 기본", "대립가설", "신뢰수준", "결측 처리"],
    preflightChecks: ["그룹별 N", "빈 그룹", "상수 그룹", "독립성 설계 확인"],
    resultFocus: ["평균 차이", "95% CI", "Welch df", "Hedges g"],
  },
  "hypothesis.one_way_anova": {
    methodId: "hypothesis.one_way_anova",
    roleRequirements: [required("반응", "연속형 수치 컬럼"), required("요인", "3개 이상 그룹")],
    optionChecklist: ["표준/Welch ANOVA", "사후검정", "다중비교 보정"],
    preflightChecks: ["그룹별 N", "분산 동질성", "상수 그룹", "사후검정 호환성"],
    resultFocus: ["omnibus 검정", "효과크기", "사후비교", "가정 경고"],
  },
  "hypothesis.equivalence_tost": {
    methodId: "hypothesis.equivalence_tost",
    roleRequirements: [required("반응", "연속형 수치 컬럼"), required("동등성 한계", "하한/상한 또는 허용 차이")],
    optionChecklist: ["동등성 한계", "신뢰수준", "대상 설계"],
    preflightChecks: ["한계값 방향", "유효 N", "설계 유형", "결측 제외 수"],
    resultFocus: ["TOST 결과", "CI와 동등성 한계", "효과크기"],
  },
  "hypothesis.one_sample_wilcoxon": {
    methodId: "hypothesis.one_sample_wilcoxon",
    roleRequirements: [required("반응", "순서형 또는 연속형 컬럼"), required("기준값", "비교 위치")],
    optionChecklist: ["대립가설", "zero difference 처리", "결측 처리"],
    preflightChecks: ["0 차이 수", "동률", "유효 N", "중앙값 단정 금지"],
    resultFocus: ["signed-rank 통계량", "p-value", "rank 기반 효과크기"],
  },
  "hypothesis.mann_whitney": {
    methodId: "hypothesis.mann_whitney",
    roleRequirements: [required("반응", "순서형 또는 연속형 컬럼"), required("그룹", "정확히 2개 독립 그룹")],
    optionChecklist: ["대립가설", "exact/asymptotic", "결측 처리"],
    preflightChecks: ["그룹별 N", "동률", "독립성 설계 확인", "분포 차이 해석"],
    resultFocus: ["U 통계량", "p-value", "rank-biserial 효과크기"],
  },
  "hypothesis.kruskal_wallis": {
    methodId: "hypothesis.kruskal_wallis",
    roleRequirements: [required("반응", "순서형 또는 연속형 컬럼"), required("그룹", "3개 이상 독립 그룹")],
    optionChecklist: ["Dunn 사후검정", "Holm 보정", "결측 처리"],
    preflightChecks: ["그룹별 N", "동률", "빈 그룹", "사후검정 보정"],
    resultFocus: ["H 통계량", "p-value", "사후비교", "효과크기"],
  },
  "categorical.one_proportion": {
    methodId: "categorical.one_proportion",
    roleRequirements: [required("사건/비사건", "이진 컬럼 또는 사건 수/전체 수")],
    optionChecklist: ["기준 비율", "대립가설", "신뢰수준", "정확/근사 방식"],
    preflightChecks: ["사건 수", "전체 N", "희소 조건", "이진 수준 확인"],
    resultFocus: ["비율 추정치", "CI", "검정통계량", "p-value"],
  },
  "categorical.two_proportion": {
    methodId: "categorical.two_proportion",
    roleRequirements: [required("결과", "이진 결과"), required("그룹", "정확히 2개 그룹")],
    optionChecklist: ["대립가설", "신뢰수준", "정확/근사 방식"],
    preflightChecks: ["그룹별 사건 수", "그룹별 N", "희소 조건", "수준 매핑"],
    resultFocus: ["비율 차이", "CI", "위험비/오즈비 후보", "p-value"],
  },
  "categorical.chi_square_association": {
    methodId: "categorical.chi_square_association",
    roleRequirements: [required("행 변수", "범주형 컬럼"), required("열 변수", "범주형 컬럼")],
    optionChecklist: ["연관성 검정", "Fisher 2x2 대안", "효과크기"],
    preflightChecks: ["분할표 크기", "기대도수", "희소 셀", "결측 제외 수"],
    resultFocus: ["카이제곱 통계량", "df", "p-value", "Cramer's V"],
  },
  "regression.pearson": {
    methodId: "regression.pearson",
    roleRequirements: [required("X", "연속형 수치 컬럼"), required("Y", "연속형 수치 컬럼")],
    optionChecklist: ["신뢰수준", "다중비교 보정", "결측 처리"],
    preflightChecks: ["쌍별 N", "상수열", "비선형 패턴", "이상점 후보"],
    resultFocus: ["상관계수", "CI", "p-value", "산점도 진단"],
  },
  "regression.xy_correlation": {
    methodId: "regression.xy_correlation",
    roleRequirements: [required("X 변수 집합", "수치 컬럼 1개 이상"), required("Y 변수 집합", "수치 컬럼 1개 이상")],
    optionChecklist: ["상관 방식", "다중비교 보정", "결측 처리"],
    preflightChecks: ["변수별 N", "상수열", "쌍별 결측 변화", "상관행렬 크기"],
    resultFocus: ["교차 상관행렬", "보정 p-value", "유효 N"],
  },
  "regression.linear_model": {
    methodId: "regression.linear_model",
    roleRequirements: [required("반응", "연속형 또는 이진 타깃"), required("예측변수", "수치/범주형 컬럼")],
    optionChecklist: ["모형 유형", "상호작용", "신뢰수준", "진단 출력"],
    preflightChecks: ["결측 complete-case", "다중공선성", "특이행렬", "분리/수렴"],
    resultFocus: ["계수 추정치", "CI", "잔차 진단", "모형 적합도"],
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
    roleRequirements: [required("측정값", "연속형 수치 컬럼"), required("순서", "시간 또는 실행 순서")],
    optionChecklist: ["I-MR", "관리규칙", "moving range 길이"],
    preflightChecks: ["순서 중복", "상수열", "결측", "시간 간격"],
    resultFocus: ["I chart", "MR chart", "관리한계", "규칙 위반"],
  },
  "quality.subgroup_chart": {
    methodId: "quality.subgroup_chart",
    roleRequirements: [required("측정값", "연속형 수치 컬럼"), required("부분군", "합리적 subgroup ID")],
    optionChecklist: ["Xbar-R/Xbar-S", "부분군 크기", "관리규칙"],
    preflightChecks: ["부분군별 N", "불균형 부분군", "부분군 내 상수", "순서"],
    resultFocus: ["부분군 평균", "부분군 산포", "관리한계", "규칙 위반"],
  },
  "quality.run_chart": {
    methodId: "quality.run_chart",
    roleRequirements: [required("측정값", "수치 또는 이진/계수 결과"), required("순서", "시간 또는 실행 순서")],
    optionChecklist: ["중심선", "run rule", "trend rule"],
    preflightChecks: ["순서 누락", "동률", "결측", "충분한 run 수"],
    resultFocus: ["run/trend", "중심선 crossing", "비무작위 패턴"],
  },
  "quality.capability": {
    methodId: "quality.capability",
    roleRequirements: [required("측정값", "연속형 수치 컬럼"), required("규격", "LSL/USL/target 중 필요한 값")],
    optionChecklist: ["정규/비정규 방식", "부분군", "신뢰수준"],
    preflightChecks: ["규격 순서", "공정 안정성", "정규성 보조 점검", "음수/단위"],
    resultFocus: ["Cp/Cpk", "Pp/Ppk", "규격 대비 분포", "한계 경고"],
  },
  "quality.gage_rr": {
    methodId: "quality.gage_rr",
    roleRequirements: [
      required("측정값", "연속형 수치 컬럼"),
      required("부품", "part ID"),
      required("측정자", "operator ID"),
      required("반복", "replicate ID"),
    ],
    optionChecklist: ["교차/중첩 설계", "ANOVA/Range 방식", "허용 기준"],
    preflightChecks: ["균형 설계", "반복 수", "부품-측정자 조합", "상호작용"],
    resultFocus: ["%GRR", "분산 성분", "ndc", "측정자/부품 진단"],
  },
  "quality.gage_run_chart": {
    methodId: "quality.gage_run_chart",
    roleRequirements: [required("측정값", "연속형 수치 컬럼"), required("부품/측정자/반복", "MSA 식별 역할")],
    optionChecklist: ["실행 순서", "패널 구분", "기준선 표시"],
    preflightChecks: ["순서", "불완전 반복", "부품/측정자 조합", "결측"],
    resultFocus: ["반복 패턴", "측정자 차이", "부품별 산포"],
  },
  "doe.factorial_design": {
    methodId: "doe.factorial_design",
    roleRequirements: [required("요인", "이름, 수준, low/high"), optional("블록", "블록 또는 반복 구조")],
    optionChecklist: ["설계 유형", "반복/센터점", "랜덤 seed", "run order"],
    preflightChecks: ["요인 수준", "alias 구조", "실행 수", "랜덤화 재현성"],
    resultFocus: ["설계표", "표준/실행 순서", "alias 정보", "재현 seed"],
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
