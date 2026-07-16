import type { AnalysisMethodDescriptor } from "./api";

type RoleGuideKey =
  | "response"
  | "group"
  | "predictor"
  | "event"
  | "order"
  | "subgroup"
  | "part"
  | "operator"
  | "replicate"
  | "spec";

interface RoleGuideItem {
  key: RoleGuideKey;
  title: string;
  description: string;
  risk: string;
}

interface MethodRoleFocus {
  roleKeys: readonly RoleGuideKey[];
  title: string;
  detail: string;
}

const roleGuideItems: readonly RoleGuideItem[] = [
  {
    key: "response",
    title: "Response / 반응값 / Y",
    description: "비교하거나 예측하고 싶은 값입니다. 예: 강도, 수율, 측정값, 온도, 압력",
    risk: "반응값 대신 ID나 그룹 컬럼을 고르면 평균, 효과크기, 회귀계수가 의미 없는 값이 됩니다.",
  },
  {
    key: "group",
    title: "Group / 그룹",
    description: "반응값을 나누어 비교할 범주입니다. 예: A라인/B라인, 공급업체, 조건1/조건2",
    risk: "전후 측정인데 group으로 넣으면 독립 2표본 검정이 되어 잘못된 결과가 나올 수 있습니다.",
  },
  {
    key: "predictor",
    title: "Predictor / 설명변수 / X",
    description: "반응값을 설명하거나 예측하는 변수입니다. 예: 온도, 시간, 압력",
    risk: "결과를 만든 뒤에야 알 수 있는 변수를 X로 넣으면 누수 때문에 모델이 과하게 좋아 보입니다.",
  },
  {
    key: "event",
    title: "Event level / 사건 수준",
    description: "관심 있는 결과값입니다. 예: Pass, Fail, Defect, Yes",
    risk: "사건 수준을 반대로 고르면 비율, risk ratio, odds ratio 해석이 반대로 바뀝니다.",
  },
  {
    key: "order",
    title: "Order / 순서",
    description: "시간 또는 실행 순서입니다. 예: 생산 순서, 측정 순서, timestamp",
    risk: "실제 시간 순서가 아닌 컬럼을 넣으면 추세나 공정 안정성 신호를 잘못 읽을 수 있습니다.",
  },
  {
    key: "subgroup",
    title: "Subgroup / 부분군",
    description: "같은 조건에서 묶인 반복 측정 단위입니다. 예: 같은 시간대의 5개 샘플",
    risk: "부분군을 임의로 묶으면 Xbar/R, Xbar/S 관리한계가 공정 구조를 반영하지 못합니다.",
  },
  {
    key: "part",
    title: "Part / 부품",
    description: "Gage R&R에서 반복 측정되는 제품 또는 샘플입니다.",
    risk: "부품 ID가 중복되거나 빠지면 반복성/재현성 분산성분을 분리할 수 없습니다.",
  },
  {
    key: "operator",
    title: "Operator / 측정자",
    description: "Gage R&R에서 측정한 사람 또는 장비입니다.",
    risk: "측정자를 다른 그룹 변수와 혼동하면 재현성 변동을 잘못 추정합니다.",
  },
  {
    key: "replicate",
    title: "Replicate / 반복",
    description: "같은 부품/측정자의 반복 측정 번호입니다.",
    risk: "반복 번호가 균형을 이루지 않으면 현재 balanced crossed Gage R&R은 실행할 수 없습니다.",
  },
  {
    key: "spec",
    title: "LSL/USL/Target",
    description: "규격 하한, 규격 상한, 목표값입니다.",
    risk: "규격을 관리한계처럼 넣으면 capability 결과를 공정 안정성 판단으로 오해할 수 있습니다.",
  },
] as const;

const methodRoleFocusById: Readonly<Record<string, MethodRoleFocus>> = {
  "regression.linear_model": {
    roleKeys: ["response", "predictor"],
    title: "회귀모형 적합과 저장 모델 예측",
    detail:
      "저장 모델 예측은 이 화면에서 실행합니다. source dataset schema가 바뀌어 모델이 stale이면 예측 전에 현재 schema로 회귀모형을 다시 적합해야 합니다.",
  },
  "hypothesis.two_sample_t": {
    roleKeys: ["response", "group"],
    title: "2-표본 t-검정 핵심 역할",
    detail:
      "Response는 비교할 숫자값, Group은 정확히 두 독립 그룹입니다. 독립성은 데이터만으로 검증되지 않으므로 실험/측정 설계를 확인해야 합니다.",
  },
  "hypothesis.paired_t": {
    roleKeys: ["response"],
    title: "대응표본 t-검정 핵심 역할",
    detail:
      "Before/After는 같은 대상에서 나온 두 측정값입니다. 전후 측정인데 Group으로 넣으면 독립 2표본 검정이 되어 설계를 잘못 반영합니다.",
  },
  "quality.capability": {
    roleKeys: ["response", "spec"],
    title: "Capability 핵심 역할",
    detail:
      "측정값과 LSL/USL/Target을 구분하세요. Spec limit은 고객/공정 규격이고 control limit이 아니므로 공정 안정성 판단은 관리도와 함께 봐야 합니다.",
  },
  "quality.gage_rr": {
    roleKeys: ["response", "part", "operator", "replicate"],
    title: "Gage R&R 핵심 역할",
    detail:
      "Part, Operator, Replicate가 balanced crossed design을 이루어야 합니다. 현재 slice는 nested 또는 unbalanced 설계를 자동 보정하지 않습니다.",
  },
  "doe.factorial_design": {
    roleKeys: ["predictor", "order"],
    title: "DOE 설계 핵심 역할",
    detail:
      "Factor 이름, low/high level, run order, random seed와 각 run의 Response가 재현성을 결정합니다. 효과와 ANOVA는 -1/+1 coding 및 선택한 hierarchy 모형을 기준으로 해석합니다.",
  },
  "doe.response_surface": {
    roleKeys: ["predictor", "response", "order"],
    title: "반응표면 설계 핵심 역할",
    detail:
      "각 Factor의 low/high는 실제 안전 설계경계이며 axial point가 이 경계에 놓입니다. 저장한 run별 Response로 full quadratic 모형을 적합하고, 정상점과 optimizer 권장점은 설계영역 포함 여부 및 확인 실험 필요성과 함께 해석합니다.",
  },
  "doe.bayesian_optimization": {
    roleKeys: ["predictor", "response", "order"],
    title: "순차 Bayesian Optimization 핵심 역할",
    detail:
      "연속 Factor 경계, 최대/최소 Objective, 초기 Trial과 추천 Trial, 실제 관측 Response를 구분해야 합니다. 전용 화면은 Matérn-5/2 GP와 Expected Improvement로 다음 후보를 계산하지만 목적함수를 실행하거나 전역 최적을 보장하지 않습니다.",
  },
};

export function StatisticalRoleGuide({ selectedMethod }: { selectedMethod: AnalysisMethodDescriptor | null }) {
  const focus =
    selectedMethod === null ? null : methodRoleFocusById[selectedMethod.method_id] ?? null;
  const focusedRoleKeys = new Set(focus?.roleKeys ?? []);

  return (
    <section className="role-guide-panel" aria-labelledby="role-guide-title">
      <div className="panel-heading">
        <div>
          <h3 id="role-guide-title">역할 설명</h3>
          <p>
            분석은 column의 통계 역할을 기준으로 실행됩니다. 같은 컬럼이라도 역할 선택이
            달라지면 질문과 가정이 달라집니다.
          </p>
        </div>
      </div>
      {focus !== null ? (
        <div className="role-focus-box" role="note">
          <strong>{focus.title}</strong>
          <p>{focus.detail}</p>
        </div>
      ) : null}
      <div className="role-guide-grid">
        {roleGuideItems.map((item) => (
          <article
            className={
              focusedRoleKeys.has(item.key)
                ? "role-guide-item role-guide-item-highlight"
                : "role-guide-item"
            }
            key={item.title}
          >
            <h4>{item.title}</h4>
            <p>{item.description}</p>
            <small>{item.risk}</small>
          </article>
        ))}
      </div>
    </section>
  );
}
