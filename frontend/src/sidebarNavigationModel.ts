import type {
  AnalysisMethodDescriptor,
  AnalysisMethodListResponse,
} from "./api";
import type { AppRoute } from "./appRoute";
import { ANALYSIS_DOMAINS, type AnalysisDomainId } from "./analysisDomains";
import { analysisMethodPlacement } from "./analysisDomainMapping";
import { methodLabel } from "./i18n/catalogLabels";
import { getCurrentLocale } from "./i18n/store";
import { t } from "./i18n/translate";
import type { AppLocale } from "./i18n/types";

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
  direct?: boolean;
  id: AppRoute["page"];
  label: string;
  onActivate?: () => void;
}

export type DatasetSidebarSection = "dataset-intake" | "dataset-version";

interface SidebarNavigationOptions {
  locale?: AppLocale;
  activeAnalysisDomainId?: AnalysisDomainId | null;
  activeAnalysisModuleId?: string;
  activeAnalysisMethodId: string | null;
  analysisCatalog: AnalysisMethodListResponse | null;
  activePage: AppRoute["page"];
  canOpenAnalysis: boolean;
  query: URLSearchParams;
  onOpenAnalysisMethod: (method: AnalysisMethodDescriptor) => void;
  onOpenAnalysisModule?: (moduleId: string) => void;
  onOpenDatasetSection: (section: DatasetSidebarSection) => void;
  onOpenHelpSection: (
    section: "purpose" | "roles" | "methods" | "tutorial",
  ) => void;
  onOpenManageTab: (
    tab: "all" | "datasets" | "analyses" | "models" | "designs",
  ) => void;
  onOpenGraphs: () => void;
  onOpenProject: () => void;
  onOpenReportTab: (tab: "reports" | "history") => void;
}

export function createSidebarNavigationGroups({
  locale = getCurrentLocale(),
  activeAnalysisDomainId,
  activeAnalysisMethodId,
  analysisCatalog,
  activePage,
  canOpenAnalysis,
  query,
  onOpenAnalysisMethod,
  onOpenDatasetSection,
  onOpenHelpSection,
  onOpenManageTab,
  onOpenGraphs,
  onOpenProject,
  onOpenReportTab,
}: SidebarNavigationOptions): SidebarNavigationGroup[] {
  const resolvedActiveDomainId =
    activeAnalysisDomainId === undefined && activeAnalysisMethodId !== null
      ? analysisMethodPlacement(activeAnalysisMethodId)?.domain.id ?? null
      : activeAnalysisDomainId ?? null;
  const datasetSection = normalizeDatasetSidebarSection(query.get("section"));
  const reportTab = query.get("tab") === "history" ? "history" : "reports";
  const requestedManageTab = query.get("tab");
  const manageTab = ["all", "datasets", "analyses", "models", "designs"].includes(
    requestedManageTab ?? "",
  )
    ? requestedManageTab!
    : "all";
  const helpSection =
    query.get("section") ?? (query.has("method_id") ? "methods" : "purpose");

  return [
    {
      active: activePage === "home",
      children: [],
      direct: true,
      id: "home",
      label: "홈",
      onActivate: onOpenProject,
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
      children: ANALYSIS_DOMAINS.map((domain) => ({
        active:
          activePage === "analysis" && resolvedActiveDomainId === domain.id,
        children: domain.families.flatMap((family) => {
          const activeFamily =
            activeAnalysisMethodId !== null &&
            analysisMethodPlacement(activeAnalysisMethodId)?.family.id === family.id;
          const methodItems = family.methodIds.flatMap((methodId) => {
            const method = analysisCatalog?.methods.find(
              (candidate) => candidate.method_id === methodId,
            );
            if (method === undefined) return [];
            return [{
              active:
                activePage === "analysis" && activeAnalysisMethodId === method.method_id,
              disabled: !canOpenAnalysis || method.availability !== "available",
              id: method.method_id,
              label: methodLabel(method, locale),
              onActivate: () => onOpenAnalysisMethod(method),
            }];
          });
          const plannedItems = (family.plannedWorkflows ?? []).map((workflow) => ({
            active: false,
            disabled: true,
            id: `planned-${workflow.id}`,
            label: `${t(workflow.labelKey, {}, locale)} · ${t("analysisPlanned.label", {}, locale)}`,
          }));
          if (methodItems.length === 0 && plannedItems.length === 0) return [];
          return [{
            active: activeFamily,
            children: [...methodItems, ...plannedItems],
            id: `${domain.id}-${family.id}`,
            label: t(family.labelKey, {}, locale),
          }];
        }),
        disabled: !canOpenAnalysis,
        id: domain.id,
        label: t(domain.labelKey, {}, locale),
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
        ["all", "전체 자산"],
        ["datasets", "데이터셋"],
        ["analyses", "분석 결과"],
        ["models", "모델"],
        ["designs", "실험 설계·스터디"],
      ].map(([id, label]) => ({
        active: activePage === "manage" && manageTab === id,
        id,
        label,
        onActivate: () =>
          onOpenManageTab(
            id as "all" | "datasets" | "analyses" | "models" | "designs",
          ),
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
