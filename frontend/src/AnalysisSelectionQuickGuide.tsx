import type { AnalysisModuleId } from "./api";

interface AnalysisSelectionQuickGuideProps {
  selectedModuleId: AnalysisModuleId;
  onSelectMethod: (moduleId: AnalysisModuleId, methodId: string) => void;
}

interface GuideItem {
  label: string;
  methodLabel: string;
  moduleId: AnalysisModuleId;
  methodId: string;
}

const hypothesisGroups: ReadonlyArray<{
  title: string;
  items: readonly GuideItem[];
  note?: string;
}> = [
  {
    title: "한 모집단",
    items: [
      {
        label: "평균 비교",
        methodLabel: "1-Sample t",
        moduleId: "hypothesis",
        methodId: "hypothesis.one_sample_t",
      },
      {
        label: "순위 기반 위치 비교",
        methodLabel: "1-Sample Wilcoxon",
        moduleId: "hypothesis",
        methodId: "hypothesis.one_sample_wilcoxon",
      },
      {
        label: "동등성 평가",
        methodLabel: "TOST",
        moduleId: "hypothesis",
        methodId: "hypothesis.equivalence_tost",
      },
    ],
  },
  {
    title: "독립 2그룹",
    items: [
      {
        label: "평균 비교",
        methodLabel: "2-Sample t (Welch)",
        moduleId: "hypothesis",
        methodId: "hypothesis.two_sample_t",
      },
      {
        label: "순위 기반 비교",
        methodLabel: "Mann-Whitney",
        moduleId: "hypothesis",
        methodId: "hypothesis.mann_whitney",
      },
    ],
  },
  {
    title: "같은 대상 전후",
    items: [
      {
        label: "차이값 평균",
        methodLabel: "Paired t",
        moduleId: "hypothesis",
        methodId: "hypothesis.paired_t",
      },
    ],
    note: "대응표본 비모수 검정은 현재 별도 method로 지원하지 않습니다.",
  },
  {
    title: "독립 3그룹 이상",
    items: [
      {
        label: "평균 비교",
        methodLabel: "One-Way ANOVA",
        moduleId: "hypothesis",
        methodId: "hypothesis.one_way_anova",
      },
      {
        label: "순위 기반 비교",
        methodLabel: "Kruskal-Wallis",
        moduleId: "hypothesis",
        methodId: "hypothesis.kruskal_wallis",
      },
    ],
  },
  {
    title: "이항형 결과",
    items: [
      {
        label: "한 모집단 사건 비율",
        methodLabel: "1-Proportion",
        moduleId: "categorical",
        methodId: "categorical.one_proportion",
      },
      {
        label: "독립 2그룹 사건 비율",
        methodLabel: "2-Proportion",
        moduleId: "categorical",
        methodId: "categorical.two_proportion",
      },
    ],
  },
  {
    title: "두 범주형 변수",
    items: [
      {
        label: "관련성",
        methodLabel: "Chi-Square Association",
        moduleId: "categorical",
        methodId: "categorical.chi_square_association",
      },
    ],
  },
];

const categoricalItems: readonly GuideItem[] = [
  {
    label: "한 모집단 사건 비율",
    methodLabel: "1-Proportion",
    moduleId: "categorical",
    methodId: "categorical.one_proportion",
  },
  {
    label: "독립 2그룹 사건 비율",
    methodLabel: "2-Proportion",
    moduleId: "categorical",
    methodId: "categorical.two_proportion",
  },
  {
    label: "두 범주형 변수의 관련성",
    methodLabel: "Chi-Square",
    moduleId: "categorical",
    methodId: "categorical.chi_square_association",
  },
];

const doeItems: readonly (GuideItem & { description: string })[] = [
  {
    label: "중요 요인과 상호작용 선별",
    methodLabel: "2-level factorial",
    moduleId: "doe",
    methodId: "doe.factorial_design",
    description: "low/high 수준의 주효과와 상호작용을 추정합니다.",
  },
  {
    label: "연속 요인 범위 전체 탐색",
    methodLabel: "LHS",
    moduleId: "doe",
    methodId: "doe.latin_hypercube",
    description: "공간충전 초기점을 만들며 고전적 factorial 대비 설계는 아닙니다.",
  },
  {
    label: "관심영역 주변 곡률 확인",
    methodLabel: "Response Surface",
    moduleId: "doe",
    methodId: "doe.response_surface",
    description: "CCD 기반 2차 모형으로 국소 영역을 검토합니다.",
  },
  {
    label: "비용이 큰 실험의 순차 최적화",
    methodLabel: "Bayesian Optimization",
    moduleId: "doe",
    methodId: "doe.bayesian_optimization",
    description: "초기 관측 후 GP와 EI로 다음 실험을 한 번씩 추천합니다.",
  },
];

export function AnalysisSelectionQuickGuide({
  selectedModuleId,
  onSelectMethod,
}: AnalysisSelectionQuickGuideProps) {
  if (selectedModuleId === "hypothesis") {
    return (
      <details className="analysis-selection-guide">
        <summary>검정 선택 빠른 가이드</summary>
        <p>
          결과 데이터, 연구 설계와 비교하려는 모수를 차례로 확인한 뒤 후보 검정을
          선택하세요.
        </p>
        <div className="analysis-selection-guide-grid">
          {hypothesisGroups.map((group) => (
            <section aria-labelledby={`guide-${group.title}`} key={group.title}>
              <h3 id={`guide-${group.title}`}>{group.title}</h3>
              <div className="analysis-selection-guide-actions">
                {group.items.map((item) => (
                  <button
                    className="secondary-button compact-button"
                    key={item.methodId}
                    onClick={() => onSelectMethod(item.moduleId, item.methodId)}
                    type="button"
                  >
                    {item.label} → {item.methodLabel}
                  </button>
                ))}
              </div>
              {group.note !== undefined ? <p className="muted-copy">{group.note}</p> : null}
            </section>
          ))}
        </div>
        <p className="analysis-selection-guide-caution">
          표본 수 30과 정규성 검정 p-value는 절대적인 자동 선택 기준이 아닙니다. 연구
          설계, 독립성, 이상치, 분포 형태와 비교하려는 모수를 함께 확인하세요.
        </p>
      </details>
    );
  }

  if (selectedModuleId === "categorical") {
    return (
      <details className="analysis-selection-guide">
        <summary>범주형 검정 선택 빠른 가이드</summary>
        <div className="analysis-selection-guide-actions analysis-selection-guide-actions-row">
          {categoricalItems.map((item) => (
            <button
              className="secondary-button compact-button"
              key={item.methodId}
              onClick={() => onSelectMethod(item.moduleId, item.methodId)}
              type="button"
            >
              {item.label} → {item.methodLabel}
            </button>
          ))}
        </div>
        <p className="analysis-selection-guide-caution">
          희소한 2×2 분할표에서는 기대도수를 확인하고 Fisher exact를 검토하세요.
        </p>
      </details>
    );
  }

  if (selectedModuleId === "doe") {
    return (
      <details className="analysis-selection-guide">
        <summary>실험계획법 선택 가이드</summary>
        <div className="analysis-selection-guide-grid">
          {doeItems.map((item) => (
            <section key={item.methodId}>
              <button
                className="secondary-button compact-button"
                onClick={() => onSelectMethod(item.moduleId, item.methodId)}
                type="button"
              >
                {item.label} → {item.methodLabel}
              </button>
              <p className="muted-copy">{item.description}</p>
            </section>
          ))}
        </div>
        <p className="analysis-selection-guide-caution">
          설계 목적, 요인 범위, 실험 비용과 필요한 효과 추정을 함께 확인하세요.
          어떤 방법도 전역 최적점을 보장하지 않습니다.
        </p>
      </details>
    );
  }

  return null;
}
