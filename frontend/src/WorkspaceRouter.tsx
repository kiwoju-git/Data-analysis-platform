import type { AnalysisShellProps } from "./AnalysisShell";
import type {
  AnalysisWorkbenchComparisonState,
  AnalysisWorkbenchHistoryState,
  AnalysisWorkbenchRestoredState,
} from "./AnalysisWorkbench";
import { AnalysisPage } from "./AnalysisPage";
import type {
  AnalysisMethodDescriptor,
  AnalysisMethodListResponse,
  DatasetVersionResponse,
} from "./api";
import type { AppRoute } from "./appRoute";
import {
  DatasetPreparationPage,
  type DatasetPreparationPageProps,
} from "./DatasetPreparationPage";
import { HelpCenterPage, ManageAssetsPage, ReportCenterPage } from "./lazyWorkspacePages";
import { WorkspacePageBoundary } from "./WorkspacePageBoundary";

export interface WorkspaceRouterProps {
  analysisPageProps: AnalysisShellProps;
  analysisCatalog: AnalysisMethodListResponse | null;
  analysisComparisonState?: AnalysisWorkbenchComparisonState;
  analysisHistoryState?: AnalysisWorkbenchHistoryState;
  analysisRestoredState?: AnalysisWorkbenchRestoredState;
  currentDatasetVersion?: DatasetVersionResponse | null;
  currentDatasetVersionId: string | null;
  datasetPageProps: DatasetPreparationPageProps;
  routePage: AppRoute["page"];
  onOpenAnalysisMethod: (method: AnalysisMethodDescriptor) => void;
  onActivateDataset: (versionId: string) => void;
  onDatasetMetadataChanged: () => void;
}

export function WorkspaceRouter({
  analysisPageProps,
  analysisCatalog,
  analysisComparisonState,
  analysisHistoryState,
  analysisRestoredState,
  currentDatasetVersion,
  currentDatasetVersionId,
  datasetPageProps,
  routePage,
  onOpenAnalysisMethod,
  onActivateDataset,
  onDatasetMetadataChanged,
}: WorkspaceRouterProps) {
  const labelledBy = routePage === "analysis" ? "analysis-modules-title" : routePage === "reports" ? "report-center-title" : routePage === "help" ? "help-quick-start-title" : routePage === "manage" ? "asset-management-title" : "workspace-title";
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
            comparisonState={analysisComparisonState}
            currentDatasetVersionId={currentDatasetVersionId}
            historyState={analysisHistoryState}
            restoredState={analysisRestoredState}
            version={currentDatasetVersion ?? null}
          />
        </WorkspacePageBoundary>
      ) : null}
      {routePage === "help" ? (
        <WorkspacePageBoundary pageKey="help">
          <HelpCenterPage catalog={analysisCatalog} onOpenAnalysis={onOpenAnalysisMethod} />
        </WorkspacePageBoundary>
      ) : null}
      {routePage === "manage" ? (
        <WorkspacePageBoundary pageKey="manage">
          <ManageAssetsPage
            activeDatasetVersionId={currentDatasetVersionId}
            onActivateDataset={onActivateDataset}
            onDatasetMetadataChanged={onDatasetMetadataChanged}
          />
        </WorkspacePageBoundary>
      ) : null}
    </section>
  );
}
