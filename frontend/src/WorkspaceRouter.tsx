import type { AnalysisShellProps } from "./AnalysisShell";
import { AnalysisPage } from "./AnalysisPage";
import {
  DatasetPreparationPage,
  type DatasetPreparationPageProps,
} from "./DatasetPreparationPage";

export interface WorkspaceRouterProps {
  analysisPageProps: AnalysisShellProps;
  datasetPageProps: DatasetPreparationPageProps;
  flowError: string | null;
  isAnalysisPage: boolean;
}

export function WorkspaceRouter({
  analysisPageProps,
  datasetPageProps,
  flowError,
  isAnalysisPage,
}: WorkspaceRouterProps) {
  return (
    <section
      className="workspace"
      aria-labelledby={isAnalysisPage ? "analysis-modules-title" : "workspace-title"}
    >
      {isAnalysisPage && flowError !== null ? (
        <div className="error-box" role="alert">
          오류 코드: {flowError}
        </div>
      ) : null}
      {isAnalysisPage ? (
        <AnalysisPage {...analysisPageProps} />
      ) : (
        <DatasetPreparationPage {...datasetPageProps} />
      )}
    </section>
  );
}
