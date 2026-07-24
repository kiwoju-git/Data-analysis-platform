import type { GraphPreviewType } from "./api";

export interface GraphBuilderDefinition {
  graphType: GraphPreviewType;
  label: string;
  description: string;
  maximumValues: number;
  supportsGroup: boolean;
  supportsOrder: boolean;
}

export const graphBuilderDefinitions: readonly GraphBuilderDefinition[] = [
  {
    graphType: "box_plot",
    label: "Box Plot",
    description: "여러 수치 변수 또는 한 수치 변수의 그룹별 분포를 비교합니다.",
    maximumValues: 12,
    supportsGroup: true,
    supportsOrder: false,
  },
  {
    graphType: "individual_value_plot",
    label: "Individual Value Plot",
    description: "최대 2,000개 실제 관측값을 자동 표본추출 없이 표시합니다.",
    maximumValues: 8,
    supportsGroup: true,
    supportsOrder: false,
  },
  {
    graphType: "histogram",
    label: "Histogram",
    description: "변수별 bin을 사용한 small multiples를 표시합니다.",
    maximumValues: 8,
    supportsGroup: false,
    supportsOrder: false,
  },
  {
    graphType: "qq_plot",
    label: "Q-Q Plot",
    description: "정규분포 분위수와 표본 분위수의 관계를 시각적으로 검토합니다.",
    maximumValues: 8,
    supportsGroup: false,
    supportsOrder: false,
  },
  {
    graphType: "ecdf",
    label: "ECDF",
    description: "변수별 경험 누적분포를 표시합니다.",
    maximumValues: 6,
    supportsGroup: false,
    supportsOrder: false,
  },
  {
    graphType: "scatter_plot",
    label: "Scatter Plot",
    description: "X 한 개와 Y 최대 여섯 개의 관계를 Y별 패널로 표시합니다.",
    maximumValues: 6,
    supportsGroup: true,
    supportsOrder: false,
  },
  {
    graphType: "run_chart",
    label: "Run Chart",
    description: "공통 순서를 사용하되 변수별 중앙선과 패턴을 따로 계산합니다.",
    maximumValues: 6,
    supportsGroup: false,
    supportsOrder: true,
  },
  {
    graphType: "imr_chart",
    label: "I-MR Chart",
    description: "변수별 I chart와 MR chart 관리한계를 독립적으로 계산합니다.",
    maximumValues: 6,
    supportsGroup: false,
    supportsOrder: true,
  },
] as const;

export function graphBuilderDefinition(graphType: GraphPreviewType): GraphBuilderDefinition {
  const definition = graphBuilderDefinitions.find((item) => item.graphType === graphType);
  if (definition === undefined) {
    throw new Error("graph_builder_type_not_found");
  }
  return definition;
}
