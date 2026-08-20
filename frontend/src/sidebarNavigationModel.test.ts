import { describe, expect, it, vi } from "vitest";

import type { AnalysisMethodListResponse } from "./api";

import {
  createSidebarNavigationGroups,
  normalizeDatasetSidebarSection,
  normalizedDatasetSidebarLocation,
} from "./sidebarNavigationModel";

const analysisCatalog: AnalysisMethodListResponse = {
  modules: [
    ["exploration", "탐색적 분석", 10] as const,
    ["hypothesis", "가설 검정", 20] as const,
    ["categorical", "범주형 데이터 분석", 30] as const,
    ["regression", "상관관계·회귀", 40] as const,
    ["quality", "품질 관리", 50] as const,
    ["doe", "실험 계획법", 60] as const,
  ].map(([module_id, label_ko, order]) => ({
    module_id: module_id as AnalysisMethodListResponse["modules"][number]["module_id"],
    label_ko,
    label_en: String(label_ko),
    order,
  })),
  methods: [
    ["eda.descriptive", "기술통계", "exploration"],
    ["eda.graphical_summary", "그래프 요약", "exploration"],
    ["eda.normality", "정규성 검정", "exploration"],
    ["eda.equal_variances", "등분산 검정", "exploration"],
    ["hypothesis.one_way_anova", "일원분산분석", "hypothesis"],
    ["categorical.chi_square_association", "카이제곱 독립성 검정", "categorical"],
    ["quality.run_chart", "런 차트", "quality"],
    ["quality.capability", "공정능력 분석", "quality"],
    ["doe.latin_hypercube", "LHS 공간충전 설계", "doe"],
    ["doe.bayesian_optimization", "베이지안 최적화", "doe"],
  ].map(
    ([method_id, label, module_id], index) => ({
      method_id,
      method_version: "0.1.0",
      module_id: module_id as AnalysisMethodListResponse["methods"][number]["module_id"],
      label_ko: label,
      label_en: label,
      availability: "available" as const,
      execution_mode: "inline" as const,
      requires_dataset: true,
      order: index + 1,
      disabled_reason: null,
    }),
  ),
};

const catalogOptions = {
  activeAnalysisMethodId: null,
  analysisCatalog,
  onOpenAnalysisMethod: vi.fn(),
};

describe("sidebar navigation model", () => {
  it("builds seven readable groups with query-synchronized active leaves", () => {
    const onOpenManageTab = vi.fn();
    const groups = createSidebarNavigationGroups({
      ...catalogOptions,
      activeAnalysisModuleId: "quality",
      activePage: "manage",
      canOpenAnalysis: true,
      query: new URLSearchParams("tab=models"),
      onOpenAnalysisModule: vi.fn(),
      onOpenDatasetSection: vi.fn(),
      onOpenHelpSection: vi.fn(),
      onOpenGraphs: vi.fn(),
      onOpenManageTab,
      onOpenProject: vi.fn(),
      onOpenReportTab: vi.fn(),
    });

    expect(groups.map((group) => group.label)).toEqual([
      "홈",
      "데이터셋",
      "분석",
      "그래프",
      "리포트",
      "관리",
      "도움말",
    ]);
    const manage = groups.find((group) => group.id === "manage");
    expect(manage?.active).toBe(true);
    expect(manage?.children.map((item) => item.label)).toEqual([
      "전체 자산",
      "데이터셋",
      "분석 결과",
      "모델",
      "실험 설계·스터디",
    ]);
    expect(manage?.children.find((item) => item.active)?.id).toBe("models");
    manage?.children.find((item) => item.id === "datasets")?.onActivate?.();
    expect(onOpenManageTab).toHaveBeenCalledWith("datasets");
  });

  it("keeps all eight analysis domains visible and blocks them while unavailable", () => {
    const onOpenAnalysisDomain = vi.fn();
    const groups = createSidebarNavigationGroups({
      ...catalogOptions,
      activeAnalysisDomainId: "quality-process-monitoring",
      activePage: "analysis",
      canOpenAnalysis: false,
      query: new URLSearchParams(),
      onOpenAnalysisModule: vi.fn(),
      onOpenAnalysisDomain,
      onOpenDatasetSection: vi.fn(),
      onOpenHelpSection: vi.fn(),
      onOpenGraphs: vi.fn(),
      onOpenManageTab: vi.fn(),
      onOpenProject: vi.fn(),
      onOpenReportTab: vi.fn(),
    });
    const analysis = groups.find((group) => group.id === "analysis");

    expect(analysis?.children.map((item) => item.id)).toEqual([
      "basic-exploration",
      "mean-equivalence",
      "proportions-categorical",
      "correlation-regression-prediction",
      "doe-optimization",
      "ai-ml-experimental-design",
      "quality-process-monitoring",
      "measurement-variability",
    ]);
    expect(analysis?.children.every((item) => item.disabled)).toBe(true);
    expect(analysis?.children.find((item) => item.active)?.id).toBe(
      "quality-process-monitoring",
    );
    expect(
      analysis?.children
        .find((item) => item.id === "correlation-regression-prediction")
        ?.children?.some((item) => item.id.endsWith("prediction-optimization")),
    ).toBe(false);
    expect(
      analysis?.children
        .find((item) => item.id === "ai-ml-experimental-design")
        ?.children?.some((item) => item.id.endsWith("surrogate-stage")),
    ).toBe(false);
    const basic = analysis?.children.find((item) => item.id === "basic-exploration");
    expect(basic?.children?.map((item) => item.id)).toEqual([
      "eda.descriptive",
      "eda.graphical_summary",
      "eda.normality",
      "planned-eda.multivariate_review",
    ]);
    expect(basic?.children?.some((item) => item.id.includes("distribution-summary"))).toBe(false);
    basic?.onActivate?.();
    expect(onOpenAnalysisDomain).toHaveBeenCalledWith(expect.objectContaining({ id: "basic-exploration" }));
  });

  it("flattens single-method families and keeps GP as contextual information", () => {
    const groups = createSidebarNavigationGroups({
      ...catalogOptions,
      activeAnalysisDomainId: "mean-equivalence",
      activePage: "analysis",
      canOpenAnalysis: true,
      query: new URLSearchParams(),
      onOpenAnalysisDomain: vi.fn(),
      onOpenDatasetSection: vi.fn(),
      onOpenHelpSection: vi.fn(),
      onOpenGraphs: vi.fn(),
      onOpenManageTab: vi.fn(),
      onOpenProject: vi.fn(),
      onOpenReportTab: vi.fn(),
    });
    const analysis = groups.find((group) => group.id === "analysis");
    const mean = analysis?.children.find((item) => item.id === "mean-equivalence");
    const anova = mean?.children?.find((item) => item.id === "hypothesis.one_way_anova");
    expect(anova?.label).toBe("ANOVA");
    expect(anova?.children).toBeUndefined();
    const categorical = analysis?.children.find((item) => item.id === "proportions-categorical");
    expect(categorical?.children?.find((item) => item.id === "categorical.chi_square_association")?.label).toBe("범주형 관련성");
    const quality = analysis?.children.find((item) => item.id === "quality-process-monitoring");
    expect(quality?.children?.find((item) => item.id === "quality.run_chart")?.label).toBe("시계열 패턴");
    const ai = analysis?.children.find((item) => item.id === "ai-ml-experimental-design");
    expect(ai?.children?.find((item) => item.id === "planned-gaussian-process-surrogate")?.disabled).toBe(true);
  });

  it("keeps only registration and preview dataset shortcuts", () => {
    const groups = createSidebarNavigationGroups({
      ...catalogOptions,
      activeAnalysisModuleId: "exploration",
      activePage: "dataset",
      canOpenAnalysis: true,
      query: new URLSearchParams("section=dataset-parsing"),
      onOpenAnalysisModule: vi.fn(),
      onOpenDatasetSection: vi.fn(),
      onOpenHelpSection: vi.fn(),
      onOpenGraphs: vi.fn(),
      onOpenManageTab: vi.fn(),
      onOpenProject: vi.fn(),
      onOpenReportTab: vi.fn(),
    });
    const dataset = groups.find((group) => group.id === "dataset");

    expect(dataset?.children.map((item) => item.label)).toEqual([
      "데이터 등록",
      "미리보기",
    ]);
    expect(dataset?.children.find((item) => item.active)?.id).toBe(
      "dataset-intake",
    );
    expect(dataset?.children.some((item) => item.id === "dataset-parsing")).toBe(
      false,
    );
    expect(normalizeDatasetSidebarSection("dataset-parsing")).toBe(
      "dataset-intake",
    );
    expect(normalizeDatasetSidebarSection("unknown-section")).toBe(
      "dataset-intake",
    );
    expect(normalizeDatasetSidebarSection("dataset-version")).toBe(
      "dataset-version",
    );
    expect(
      normalizedDatasetSidebarLocation(
        "http://127.0.0.1:8600/?section=dataset-parsing&dataset_version_id=v1",
      ),
    ).toBe("/?section=dataset-intake&dataset_version_id=v1");
    expect(
      normalizedDatasetSidebarLocation(
        "http://127.0.0.1:8600/?section=dataset-version",
      ),
    ).toBeNull();
  });

  it("builds the active domain-family-method chain and leaves planned work disabled", () => {
    const groups = createSidebarNavigationGroups({
      ...catalogOptions,
      activeAnalysisMethodId: "eda.equal_variances",
      activePage: "analysis",
      canOpenAnalysis: true,
      query: new URLSearchParams(),
      onOpenDatasetSection: vi.fn(),
      onOpenHelpSection: vi.fn(),
      onOpenGraphs: vi.fn(),
      onOpenManageTab: vi.fn(),
      onOpenProject: vi.fn(),
      onOpenReportTab: vi.fn(),
    });
    const analysis = groups.find((group) => group.id === "analysis");
    const measurement = analysis?.children.find(
      (item) => item.id === "measurement-variability",
    );
    const variance = measurement?.children?.find((item) =>
      item.id.endsWith("variance-comparison"),
    );

    expect(measurement?.active).toBe(true);
    expect(variance?.active).toBe(true);
    expect(variance?.children?.find((item) => item.id === "eda.equal_variances")?.active).toBe(
      true,
    );
    const plannedTwoVariances = variance?.children?.find((item) =>
      item.id.includes("quality.two_variances"),
    );
    expect(plannedTwoVariances?.disabled).toBe(true);
    expect(plannedTwoVariances).not.toHaveProperty("onActivate");
  });

  it("marks method detail URLs as the active Help leaf", () => {
    const groups = createSidebarNavigationGroups({
      ...catalogOptions,
      activeAnalysisModuleId: "exploration",
      activePage: "help",
      canOpenAnalysis: true,
      query: new URLSearchParams("method_id=quality.run_chart"),
      onOpenAnalysisModule: vi.fn(),
      onOpenDatasetSection: vi.fn(),
      onOpenHelpSection: vi.fn(),
      onOpenGraphs: vi.fn(),
      onOpenManageTab: vi.fn(),
      onOpenProject: vi.fn(),
      onOpenReportTab: vi.fn(),
    });

    expect(
      groups
        .find((group) => group.id === "help")
        ?.children.find((item) => item.active)?.id,
    ).toBe("methods");
  });

  it("opens the graph builder from the active Graph group", () => {
    const onOpenGraphs = vi.fn();
    const groups = createSidebarNavigationGroups({
      ...catalogOptions,
      activeAnalysisModuleId: "exploration",
      activePage: "graphs",
      canOpenAnalysis: true,
      query: new URLSearchParams("dataset_version_id=version-1"),
      onOpenAnalysisModule: vi.fn(),
      onOpenDatasetSection: vi.fn(),
      onOpenGraphs,
      onOpenHelpSection: vi.fn(),
      onOpenManageTab: vi.fn(),
      onOpenProject: vi.fn(),
      onOpenReportTab: vi.fn(),
    });
    const graphs = groups.find((group) => group.id === "graphs");

    expect(graphs?.active).toBe(true);
    expect(graphs?.children[0]?.label).toBe("그래프 작성");
    expect(graphs?.children[0]?.active).toBe(true);
    expect(graphs?.children[0]?.id).toBe("graph-builder");
    graphs?.children[0]?.onActivate?.();
    expect(onOpenGraphs).toHaveBeenCalledTimes(1);
  });
});
