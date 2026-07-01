import type { AnalysisShellProps } from "./AnalysisShell";
import { AnalysisPage } from "./AnalysisPage";
import {
  DatasetPreparationPage,
  type DatasetPreparationPageProps,
} from "./DatasetPreparationPage";

export interface WorkspaceRouterProps {
  analysisPageProps: AnalysisShellProps;
  datasetPageProps: DatasetPreparationPageProps;
  isAnalysisPage: boolean;
}

export function WorkspaceRouter({
  analysisPageProps,
  datasetPageProps,
  isAnalysisPage,
}: WorkspaceRouterProps) {
  return (
    <section
      className="workspace"
      aria-labelledby={isAnalysisPage ? "analysis-modules-title" : "workspace-title"}
    >
      {isAnalysisPage ? (
        <AnalysisPage {...analysisPageProps} />
      ) : (
        <DatasetPreparationPage {...datasetPageProps} />
      )}
    </section>
  );
}
