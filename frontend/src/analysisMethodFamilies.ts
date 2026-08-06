import type { AnalysisMethodDescriptor } from "./api";

export interface AnalysisMethodFamily {
  description: string;
  id: string;
  label: string;
  methods: AnalysisMethodDescriptor[];
}

const hypothesisFamilies = [
  {
    description: "평균을 기준값 또는 다른 표본과 비교합니다.",
    id: "t-tests",
    label: "t-검정",
    methodIds: [
      "hypothesis.one_sample_t",
      "hypothesis.paired_t",
      "hypothesis.two_sample_t",
    ],
  },
  {
    description: "사전에 정한 허용 한계 안에서 충분히 가까운지 평가합니다.",
    id: "equivalence-tests",
    label: "동등성 검정",
    methodIds: [
      "hypothesis.equivalence_tost",
      "hypothesis.paired_equivalence_tost",
      "hypothesis.two_sample_equivalence_tost",
    ],
  },
  {
    description: "독립된 여러 그룹의 평균을 비교합니다.",
    id: "analysis-of-variance",
    label: "분산분석",
    methodIds: ["hypothesis.one_way_anova"],
  },
  {
    description: "순위 기반 방법으로 한 표본 또는 독립 그룹을 비교합니다.",
    id: "nonparametric-tests",
    label: "비모수 검정",
    methodIds: [
      "hypothesis.one_sample_wilcoxon",
      "hypothesis.mann_whitney",
      "hypothesis.kruskal_wallis",
    ],
  },
] as const;

export function groupHypothesisMethods(
  methods: AnalysisMethodDescriptor[],
): AnalysisMethodFamily[] {
  const byId = new Map(methods.map((method) => [method.method_id, method]));
  const mappedIds = new Set<string>();
  const families: AnalysisMethodFamily[] = hypothesisFamilies.map((family) => {
    const familyMethods = family.methodIds
      .map((methodId) => byId.get(methodId))
      .filter((method): method is AnalysisMethodDescriptor => method !== undefined);
    familyMethods.forEach((method) => mappedIds.add(method.method_id));
    return {
      description: family.description,
      id: family.id,
      label: family.label,
      methods: familyMethods,
    };
  });
  const unmapped = methods.filter((method) => !mappedIds.has(method.method_id));
  if (unmapped.length > 0) {
    families.push({
      description: "새로 추가되었거나 별도 분류가 필요한 검정입니다.",
      id: "other-tests",
      label: "기타 검정",
      methods: unmapped,
    });
  }
  return families.filter((family) => family.methods.length > 0);
}
