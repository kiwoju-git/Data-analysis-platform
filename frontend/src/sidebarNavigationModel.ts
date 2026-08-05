import type {
  AnalysisMethodDescriptor,
  AnalysisMethodListResponse,
  AnalysisModuleId,
} from "./api";
import type { AppRoute } from "./appRoute";

export interface SidebarNavigationItem {
  active: boolean;
  children?: SidebarNavigationItem[];
  disabled?: boolean;
  id: string;
  label: string;
  onActivate?: () => void;
}

export interface SidebarNavigationGroup {
  active: boolean;
  children: SidebarNavigationItem[];
  id: AppRoute["page"];
  label: string;
}

export type DatasetSidebarSection = "dataset-intake" | "dataset-version";

interface SidebarNavigationOptions {
  activeAnalysisModuleId: AnalysisModuleId;
  activeAnalysisMethodId: string | null;
  analysisCatalog: AnalysisMethodListResponse | null;
  activePage: AppRoute["page"];
  canOpenAnalysis: boolean;
  query: URLSearchParams;
  onOpenAnalysisModule: (moduleId: AnalysisModuleId) => void;
  onOpenAnalysisMethod: (method: AnalysisMethodDescriptor) => void;
  onOpenDatasetSection: (section: DatasetSidebarSection) => void;
  onOpenHelpSection: (
    section: "purpose" | "roles" | "methods" | "tutorial",
  ) => void;
  onOpenManageTab: (tab: "datasets" | "models") => void;
  onOpenGraphs: () => void;
  onOpenProject: () => void;
  onOpenReportTab: (tab: "reports" | "history") => void;
}

export function createSidebarNavigationGroups({
  activeAnalysisModuleId,
  activeAnalysisMethodId,
  analysisCatalog,
  activePage,
  canOpenAnalysis,
  query,
  onOpenAnalysisModule,
  onOpenAnalysisMethod,
  onOpenDatasetSection,
  onOpenHelpSection,
  onOpenManageTab,
  onOpenGraphs,
  onOpenProject,
  onOpenReportTab,
}: SidebarNavigationOptions): SidebarNavigationGroup[] {
  const datasetSection = normalizeDatasetSidebarSection(query.get("section"));
  const reportTab = query.get("tab") === "history" ? "history" : "reports";
  const manageTab = query.get("tab") === "models" ? "models" : "datasets";
  const helpSection =
    query.get("section") ?? (query.has("method_id") ? "methods" : "purpose");

  return [
    {
      active: activePage === "project",
      children: [
        {
          active: activePage === "project",
          id: "project-overview",
          label: "프로젝트 개요",
          onActivate: onOpenProject,
        },
      ],
      id: "project",
      label: "프로젝트",
    },
    {
      active: activePage === "dataset",
      children: [
        ["dataset-intake", "데이터 등록"],
        ["dataset-version", "미리보기"],
      ].map(([id, label]) => ({
        active: activePage === "dataset" && datasetSection === id,
        id,
        label,
        onActivate: () =>
          onOpenDatasetSection(id as DatasetSidebarSection),
      })),
      id: "dataset",
      label: "데이터셋",
    },
    {
      active: activePage === "analysis",
      children: (analysisCatalog?.modules ?? [])
        .slice()
        .sort((left, right) => left.order - right.order)
        .map((module) => ({
          active:
            activePage === "analysis" && activeAnalysisModuleId === module.module_id,
          children: (analysisCatalog?.methods ?? [])
            .filter((method) => method.module_id === module.module_id)
            .slice()
            .sort((left, right) => left.order - right.order)
            .map((method) => ({
              active:
                activePage === "analysis" && activeAnalysisMethodId === method.method_id,
              disabled: !canOpenAnalysis || method.availability !== "available",
              id: method.method_id,
              label: method.label_ko,
              onActivate: () => onOpenAnalysisMethod(method),
            })),
          disabled: !canOpenAnalysis,
          id: module.module_id,
          label: module.label_ko,
          onActivate: () => onOpenAnalysisModule(module.module_id),
        })),
      id: "analysis",
      label: "분석",
    },
    {
      active: activePage === "graphs",
      children: [
        {
          active: activePage === "graphs",
          id: "graph-builder",
          label: "그래프 작성",
          onActivate: onOpenGraphs,
        },
      ],
      id: "graphs",
      label: "그래프",
    },
    {
      active: activePage === "reports",
      children: [
        ["reports", "보고서"],
        ["history", "분석 이력"],
      ].map(([id, label]) => ({
        active: activePage === "reports" && reportTab === id,
        id,
        label,
        onActivate: () => onOpenReportTab(id as "reports" | "history"),
      })),
      id: "reports",
      label: "리포트",
    },
    {
      active: activePage === "manage",
      children: [
        ["datasets", "데이터셋"],
        ["models", "회귀모델"],
      ].map(([id, label]) => ({
        active: activePage === "manage" && manageTab === id,
        id,
        label,
        onActivate: () => onOpenManageTab(id as "datasets" | "models"),
      })),
      id: "manage",
      label: "관리",
    },
    {
      active: activePage === "help",
      children: [
        ["purpose", "질문으로 찾기"],
        ["roles", "역할 사전"],
        ["methods", "Method별 설명"],
        ["tutorial", "튜토리얼"],
      ].map(([id, label]) => ({
        active: activePage === "help" && helpSection === id,
        id,
        label,
        onActivate: () =>
          onOpenHelpSection(id as "purpose" | "roles" | "methods" | "tutorial"),
      })),
      id: "help",
      label: "도움말",
    },
  ];
}

export function normalizeDatasetSidebarSection(
  requested: string | null,
): DatasetSidebarSection {
  return requested === "dataset-version" ? "dataset-version" : "dataset-intake";
}

export function normalizedDatasetSidebarLocation(href: string): string | null {
  const url = new URL(href);
  const requested = url.searchParams.get("section");
  const normalized = normalizeDatasetSidebarSection(requested);
  if (requested === null || requested === normalized) {
    return null;
  }
  url.searchParams.set("section", normalized);
  return `${url.pathname}${url.search}${url.hash}`;
}
