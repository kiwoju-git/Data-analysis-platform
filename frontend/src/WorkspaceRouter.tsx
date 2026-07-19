import type { AnalysisShellProps } from "./AnalysisShell";
import { AnalysisPage } from "./AnalysisPage";
import type { AnalysisMethodDescriptor, AnalysisMethodListResponse } from "./api";
import type { AppRoute } from "./appRoute";
import {
  DatasetPreparationPage,
  type DatasetPreparationPageProps,
} from "./DatasetPreparationPage";
import { HelpCenterPage, ReportCenterPage } from "./lazyWorkspacePages";
import { WorkspacePageBoundary } from "./WorkspacePageBoundary";

export interface WorkspaceRouterProps {
  analysisPageProps: AnalysisShellProps;
  analysisCatalog: AnalysisMethodListResponse | null;
  currentDatasetVersionId: string | null;
  datasetPageProps: DatasetPreparationPageProps;
  routePage: AppRoute["page"];
  onOpenAnalysisMethod: (method: AnalysisMethodDescriptor) => void;
}

export function WorkspaceRouter({
  analysisPageProps,
  analysisCatalog,
  currentDatasetVersionId,
  datasetPageProps,
  routePage,
  onOpenAnalysisMethod,
}: WorkspaceRouterProps) {
  const labelledBy = routePage === "analysis" ? "analysis-modules-title" : routePage === "reports" ? "report-browser-title" : routePage === "help" ? "help-quick-start-title" : "workspace-title";
  return (
    <section
      className="workspace"
      aria-labelledby={labelledBy}
    >
      {routePage === "analysis" ? <AnalysisPage {...analysisPageProps} /> : null}
      {routePage === "dataset" ? <DatasetPreparationPage {...datasetPageProps} /> : null}
      {routePage === "reports" ? (
        <WorkspacePageBoundary pageKey="reports">
          <ReportCenterPage
            catalog={analysisCatalog}
            currentDatasetVersionId={currentDatasetVersionId}
          />
        </WorkspacePageBoundary>
      ) : null}
      {routePage === "help" ? (
        <WorkspacePageBoundary pageKey="help">
          <HelpCenterPage catalog={analysisCatalog} onOpenAnalysis={onOpenAnalysisMethod} />
        </WorkspacePageBoundary>
      ) : null}
    </section>
  );
}
