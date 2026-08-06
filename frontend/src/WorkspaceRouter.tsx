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
  DatasetVersionDeleteResponse,
  DatasetVersionCatalogItem,
  DatasetVersionResponse,
} from "./api";
import type { AppRoute } from "./appRoute";
import {
  DatasetPreparationPage,
  type DatasetPreparationPageProps,
} from "./DatasetPreparationPage";
import {
  HelpCenterPage,
  GraphBuilderPage,
  ManageAssetsPage,
  ProjectOverviewPage,
  ReportCenterPage,
} from "./lazyWorkspacePages";
import { WorkspacePageBoundary } from "./WorkspacePageBoundary";
import type { WorkspaceMutationKind } from "./workspaceMutation";

export interface WorkspaceRouterProps {
  analysisPageProps: AnalysisShellProps;
  analysisCatalog: AnalysisMethodListResponse | null;
  analysisComparisonState?: AnalysisWorkbenchComparisonState;
  analysisHistoryState?: AnalysisWorkbenchHistoryState;
  analysisRestoredState?: AnalysisWorkbenchRestoredState;
  activeDatasetCatalogItem?: DatasetVersionCatalogItem | null;
  currentDatasetVersion?: DatasetVersionResponse | null;
  currentDatasetVersionId: string | null;
  datasetPageProps: DatasetPreparationPageProps;
  routePage: AppRoute["page"];
  onOpenAnalysisMethod: (method: AnalysisMethodDescriptor) => void;
  onActivateDataset: (versionId: string) => void;
  onAssetsDeleted: (response: DatasetVersionDeleteResponse) => void;
  onDatasetMetadataChanged: () => void;
  onOpenAnalysisPage: () => void;
  onOpenDatasetPage: () => void;
  onOpenGraphsPage: () => void;
  onOpenHelpPage: () => void;
  onOpenManagePage: () => void;
  onOpenReportsPage: (analysisId?: string) => void;
  onWorkspaceMutation?: (kind: WorkspaceMutationKind) => void;
  workspaceAssetRevision?: number;
}

export function WorkspaceRouter({
  analysisPageProps,
  analysisCatalog,
  analysisComparisonState,
  analysisHistoryState,
  analysisRestoredState,
  activeDatasetCatalogItem,
  currentDatasetVersion,
  currentDatasetVersionId,
  datasetPageProps,
  routePage,
  onOpenAnalysisMethod,
  onActivateDataset,
  onAssetsDeleted,
  onDatasetMetadataChanged,
  onOpenAnalysisPage,
  onOpenDatasetPage,
  onOpenGraphsPage,
  onOpenHelpPage,
  onOpenManagePage,
  onOpenReportsPage,
  onWorkspaceMutation = () => undefined,
  workspaceAssetRevision = 0,
}: WorkspaceRouterProps) {
  const labelledBy =
    routePage === "analysis"
      ? "analysis-modules-title"
      : routePage === "graphs"
        ? "graph-builder-title"
        : routePage === "reports"
          ? "report-center-title"
          : routePage === "help"
            ? "help-quick-start-title"
            : routePage === "manage"
              ? "asset-management-title"
              : routePage === "home"
                ? "project-overview-title"
                : "workspace-title";
  return (
    <section
      className="workspace"
      aria-labelledby={labelledBy}
    >
      {routePage === "analysis" ? <AnalysisPage {...analysisPageProps} /> : null}
      {routePage === "dataset" ? <DatasetPreparationPage {...datasetPageProps} /> : null}
      {routePage === "graphs" ? (
        <WorkspacePageBoundary pageKey="graphs">
          <GraphBuilderPage
            catalog={analysisCatalog}
            version={currentDatasetVersion ?? null}
            onOpenAnalysis={onOpenAnalysisMethod}
          />
        </WorkspacePageBoundary>
      ) : null}
      {routePage === "home" ? (
        <WorkspacePageBoundary pageKey="home">
          <ProjectOverviewPage
            activeDatasetCatalogItem={activeDatasetCatalogItem}
            analysisCatalog={analysisCatalog}
            currentDatasetVersion={currentDatasetVersion ?? null}
            onOpenAnalysis={onOpenAnalysisPage}
            onOpenDatasetPage={onOpenDatasetPage}
            onOpenGraphs={onOpenGraphsPage}
            onOpenHelp={onOpenHelpPage}
            onOpenManage={onOpenManagePage}
            onOpenReports={onOpenReportsPage}
            workspaceAssetRevision={workspaceAssetRevision}
          />
        </WorkspacePageBoundary>
      ) : null}
      {routePage === "reports" ? (
        <WorkspacePageBoundary pageKey="reports">
          <ReportCenterPage
            catalog={analysisCatalog}
            comparisonState={analysisComparisonState}
            currentDatasetVersionId={currentDatasetVersionId}
            historyState={analysisHistoryState}
            restoredState={analysisRestoredState}
            version={currentDatasetVersion ?? null}
            onWorkspaceMutation={onWorkspaceMutation}
            workspaceAssetRevision={workspaceAssetRevision}
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
            onAssetsDeleted={onAssetsDeleted}
            onDatasetMetadataChanged={onDatasetMetadataChanged}
            onWorkspaceMutation={onWorkspaceMutation}
            workspaceAssetRevision={workspaceAssetRevision}
          />
        </WorkspacePageBoundary>
      ) : null}
    </section>
  );
}
