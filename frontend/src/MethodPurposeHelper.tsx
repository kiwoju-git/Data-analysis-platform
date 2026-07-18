import type { AnalysisMethodListResponse, AnalysisModuleId } from "./api";
import { availabilityLabel } from "./analysisWorkbenchUtils";

const purposeGuideItems = [
  {
    question: "한 컬럼의 분포와 이상치를 보고 싶다",
    methods: ["eda.graphical_summary", "eda.descriptive"],
    reason: "분포 모양, 요약 통계, 이상 후보를 먼저 확인합니다.",
    roles: "Response 또는 분석 변수",
    caution: "그래프 요약은 진단용이며, 차이가 있다는 검정 결론을 자동으로 만들지 않습니다.",
  },
  {
    question: "평균이 기준값과 다른지 보고 싶다",
    methods: ["hypothesis.one_sample_t"],
    reason: "한 숫자 컬럼의 평균을 사용자가 정한 기준 평균과 비교합니다.",
    roles: "Response, 기준값",
    caution: "기준값은 데이터에서 사후 선택하지 말고 분석 전에 정해야 합니다.",
  },
  {
    question: "두 그룹의 평균을 비교하고 싶다",
    methods: ["hypothesis.two_sample_t"],
    reason: "서로 독립인 두 그룹의 평균 차이를 Welch 기본값으로 봅니다.",
    roles: "Response, Group",
    caution: "같은 대상의 전후 비교라면 paired t-test를 써야 합니다.",
  },
  {
    question: "같은 대상의 전후를 비교하고 싶다",
    methods: ["hypothesis.paired_t"],
    reason: "같은 대상에서 나온 전/후 또는 조건 A/B 차이의 평균을 봅니다.",
    roles: "Before response, After response",
    caution: "쌍이 깨진 행은 제외되므로 complete pair 수를 확인해야 합니다.",
  },
  {
    question: "세 그룹 이상을 비교하고 싶다",
    methods: ["hypothesis.one_way_anova", "hypothesis.kruskal_wallis"],
    reason: "여러 독립 그룹의 차이를 평균 기반 또는 순위 기반으로 비교합니다.",
    roles: "Response, Group",
    caution: "전체 검정이 유의하지 않으면 사후비교가 제한될 수 있습니다.",
  },
  {
    question: "두 범주형 변수가 관련 있는지 보고 싶다",
    methods: ["categorical.chi_square_association"],
    reason: "분할표의 기대도수와 카이제곱 통계량으로 관련성을 점검합니다.",
    roles: "Row category, Column category",
    caution: "기대도수가 작은 2x2 표는 Fisher exact 권고를 함께 확인해야 합니다.",
  },
  {
    question: "두 숫자 변수가 관련 있는지 보고 싶다",
    methods: ["regression.pearson"],
    reason: "두 연속형 숫자 컬럼의 선형 상관과 신뢰구간을 봅니다.",
    roles: "Predictor X, Response Y",
    caution: "상관은 원인과 결과를 증명하지 않습니다.",
  },
  {
    question: "저장된 회귀모형으로 새 데이터를 예측하고 싶다",
    methods: ["regression.predict"],
    reason: "저장 모델을 선택하고 source freshness와 target schema를 확인한 뒤 예측합니다.",
    roles: "Response, Predictor, 예측 대상 데이터셋",
    caution: "source schema가 바뀌어 모델이 stale이면 현재 schema로 회귀모형을 다시 적합해야 합니다.",
  },
  {
    question: "공정이 안정적인지 보고 싶다",
    methods: [
      "quality.attribute_control_chart",
      "quality.individuals_chart",
      "quality.subgroup_chart",
      "quality.run_chart",
    ],
    reason: "시간/실행 순서 또는 부분군 구조에서 공정 신호를 확인합니다.",
    roles: "Response, Order 또는 Subgroup",
    caution: "실제 생산 순서나 합리적 부분군 구조가 맞는지 먼저 확인해야 합니다.",
  },
  {
    question: "규격을 만족하는지 보고 싶다",
    methods: ["quality.capability"],
    reason: "측정값이 LSL/USL/Target 기준으로 얼마나 규격 안에 들어오는지 봅니다.",
    roles: "Response, LSL, USL, Target",
    caution: "Spec limit은 control limit이 아니며, 안정성은 관리도로 별도 확인해야 합니다.",
  },
  {
    question: "측정시스템이 믿을 만한지 보고 싶다",
    methods: ["quality.gage_rr"],
    reason: "반복성, 재현성, 부품 간 변동을 balanced crossed 설계에서 분리합니다.",
    roles: "Response, Part, Operator, Replicate",
    caution: "Part-Operator-Replicate 조합이 균형 설계인지 사전점검이 필요합니다.",
  },
  {
    question: "요인실험을 설계하고 효과를 분석하고 싶다",
    methods: ["doe.factorial_design"],
    reason: "2-level full factorial 실행 순서를 만들고 저장한 반응의 효과와 ANOVA를 계산합니다.",
    roles: "Factor, low/high level, run order, response",
    caution: "효과는 -1/+1 coding 기준이며 RSM이나 최적 조건 추천으로 해석할 수 없습니다.",
  },
  {
    question: "곡률이 있는 공정 반응을 모델링하고 싶다",
    methods: ["doe.response_surface"],
    reason: "Central Composite Design과 full quadratic OLS로 반응표면을 모델링합니다.",
    roles: "Continuous factor bounds, run order, response",
    caution: "정상점과 optimizer 권장점은 모형 기반 후보이며 전역 최적이 아니므로 설계영역 안에서 확인 실험이 필요합니다.",
  },
  {
    question: "저장된 반응표면 모형으로 반응을 최적화하고 싶다",
    methods: ["regression.response_optimizer"],
    reason: "저장된 RSM 분석을 선택하고 eligibility를 확인한 뒤 bounded desirability 최적화를 실행합니다.",
    roles: "RSM source analysis, factor bounds, response goal",
    caution: "권장점은 전역 최적을 보장하지 않으며 별도의 확인 실험이 필요합니다.",
  },
  {
    question: "비용이 큰 실험을 순차적으로 탐색하고 싶다",
    methods: ["doe.bayesian_optimization"],
    reason: "관측 이력의 Gaussian Process surrogate와 Expected Improvement로 다음 실험 후보를 정하는 계획입니다.",
    roles: "Continuous factor bounds, objective, sequential trial history",
    caution: "현재는 계약 단계로 실행되지 않으며, 향후 추천도 전역 최적을 보장하거나 실험을 대신 수행하지 않습니다.",
  },
] as const;

export function MethodPurposeHelper({
  catalog,
  onSelectMethod,
}: {
  catalog: AnalysisMethodListResponse;
  onSelectMethod: (moduleId: AnalysisModuleId, methodId: string | null) => void;
}) {
  const methodsById = new Map(catalog.methods.map((method) => [method.method_id, method]));

  return (
    <section className="method-purpose-helper" aria-labelledby="method-purpose-helper-title">
      <div className="panel-heading">
        <div>
          <h3 id="method-purpose-helper-title">무엇을 알고 싶나요?</h3>
          <p>
            질문에서 출발해 후보 method와 필요한 역할을 확인합니다. 선택해도 분석은 자동
            실행되지 않습니다.
          </p>
        </div>
      </div>
      <div className="purpose-card-grid">
        {purposeGuideItems.map((item) => (
          <article className="purpose-card" key={item.question}>
            <h4>{item.question}</h4>
            <p>{item.reason}</p>
            <div className="purpose-method-list" aria-label={`${item.question} 추천 method`}>
              {item.methods.map((methodId) => {
                const method = methodsById.get(methodId) ?? null;
                const canSelect = method !== null && method.availability === "available";
                return (
                  <button
                    aria-label={`${method?.label_ko ?? methodId} 메서드 보기`}
                    className={
                      canSelect
                        ? "purpose-method-button"
                        : "purpose-method-button purpose-method-button-muted"
                    }
                    disabled={!canSelect}
                    key={methodId}
                    onClick={() => {
                      if (method !== null) {
                        onSelectMethod(method.module_id, method.method_id);
                      }
                    }}
                    type="button"
                  >
                    <span>{method?.label_ko ?? "catalog 없음"}</span>
                    <code>{methodId}</code>
                    <small>
                      {method === null
                        ? "catalog 없음"
                        : method.availability === "available"
                          ? "메서드 보기"
                          : availabilityLabel(method)}
                    </small>
                  </button>
                );
              })}
            </div>
            <div className="purpose-role-line">
              <strong>필요 역할</strong>
              <span>{item.roles}</span>
            </div>
            <p className="purpose-caution">
              <strong>주의</strong> {item.caution}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
