import { describe, expect, it, vi } from "vitest";

import { createSidebarNavigationGroups } from "./sidebarNavigationModel";

describe("sidebar navigation model", () => {
  it("builds seven readable groups with query-synchronized active leaves", () => {
    const onOpenManageTab = vi.fn();
    const groups = createSidebarNavigationGroups({
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
      "프로젝트",
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
      "데이터셋",
      "회귀모델",
    ]);
    expect(manage?.children.find((item) => item.active)?.id).toBe("models");
    expect(manage?.defaultChildId).toBe("models");
    manage?.children.find((item) => item.id === "datasets")?.onActivate();
    expect(onOpenManageTab).toHaveBeenCalledWith("datasets");
  });

  it("keeps all six analysis modules visible and blocks them without a catalog", () => {
    const groups = createSidebarNavigationGroups({
      activeAnalysisModuleId: "quality",
      activePage: "analysis",
      canOpenAnalysis: false,
      query: new URLSearchParams(),
      onOpenAnalysisModule: vi.fn(),
      onOpenDatasetSection: vi.fn(),
      onOpenHelpSection: vi.fn(),
      onOpenGraphs: vi.fn(),
      onOpenManageTab: vi.fn(),
      onOpenProject: vi.fn(),
      onOpenReportTab: vi.fn(),
    });
    const analysis = groups.find((group) => group.id === "analysis");

    expect(analysis?.children.map((item) => item.id)).toEqual([
      "exploration",
      "hypothesis",
      "categorical",
      "regression",
      "quality",
      "doe",
    ]);
    expect(analysis?.children.every((item) => item.disabled)).toBe(true);
    expect(analysis?.children.find((item) => item.active)?.id).toBe("quality");
    expect(analysis?.defaultChildId).toBe("quality");
  });

  it("marks method detail URLs as the active Help leaf", () => {
    const groups = createSidebarNavigationGroups({
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
    graphs?.children[0]?.onActivate();
    expect(onOpenGraphs).toHaveBeenCalledTimes(1);
  });
});
