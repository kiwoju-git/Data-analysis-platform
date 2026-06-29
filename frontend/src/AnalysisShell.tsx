import { AnalysisFilterControls } from "./AnalysisFilterControls";
import { AnalysisWorkbench } from "./AnalysisWorkbench";
import { DescriptiveAnalysisPanel } from "./DescriptiveAnalysisPanel";
import { GraphicalSummaryPanel } from "./GraphicalSummaryPanel";
import { NormalityAnalysisPanel } from "./NormalityAnalysisPanel";
import type {
  AnalysisMethodDescriptor,
  AnalysisMethodListResponse,
  AnalysisModuleId,
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetProfileResponse,
  DatasetVersionResponse,
  DescriptiveStatisticsResult,
  GraphicalSummaryResult,
  NormalityResult,
} from "./api";
import type { AnalysisFilterDraft } from "./analysisFilters";

export interface AnalysisShellProps {
  analysisCatalog: AnalysisMethodListResponse | null;
  analysisCatalogError: string | null;
  analysisFilterDrafts: AnalysisFilterDraft[];
  analysisFilterValidationError: string | null;
  analysisFilterValidationMessage: string | null;
  analysisResult: AnalysisResultEnvelope | null;
  descriptiveColumns: DatasetColumnResponse[];
  descriptiveResult: DescriptiveStatisticsResult | null;
  graphicalSummaryAnalysisResult: AnalysisResultEnvelope | null;
  graphicalSummaryColumns: DatasetColumnResponse[];
  graphicalSummaryResult: GraphicalSummaryResult | null;
  isRunningAnalysis: boolean;
  normalityAlpha: number;
  normalityAnalysisResult: AnalysisResultEnvelope | null;
  normalityColumns: DatasetColumnResponse[];
  normalityResult: NormalityResult | null;
  profile: DatasetProfileResponse | null;
  selectedDescriptiveColumnIds: string[];
  selectedGraphicalSummaryColumnIds: string[];
  selectedNormalityColumnIds: string[];
  selectedMethod: AnalysisMethodDescriptor | null;
  selectedMethods: AnalysisMethodDescriptor[];
  selectedModuleId: AnalysisModuleId;
  version: DatasetVersionResponse | null;
  onAnalysisFilterDraftsChange: (drafts: AnalysisFilterDraft[]) => void;
  onRunDescriptiveAnalysis: () => void;
  onRunGraphicalSummaryAnalysis: () => void;
  onRunNormalityAnalysis: () => void;
  onSelectMethod: (moduleId: AnalysisModuleId, methodId: string | null) => void;
  onNormalityAlphaChange: (alpha: number) => void;
  onToggleDescriptiveColumn: (columnId: string, checked: boolean) => void;
  onToggleGraphicalSummaryColumn: (columnId: string, checked: boolean) => void;
  onToggleNormalityColumn: (columnId: string, checked: boolean) => void;
}

export function AnalysisShell({
  analysisCatalog,
  analysisCatalogError,
  analysisFilterDrafts,
  analysisFilterValidationError,
  analysisFilterValidationMessage,
  analysisResult,
  descriptiveColumns,
  descriptiveResult,
  graphicalSummaryAnalysisResult,
  graphicalSummaryColumns,
  graphicalSummaryResult,
  isRunningAnalysis,
  normalityAlpha,
  normalityAnalysisResult,
  normalityColumns,
  normalityResult,
  profile,
  selectedDescriptiveColumnIds,
  selectedGraphicalSummaryColumnIds,
  selectedNormalityColumnIds,
  selectedMethod,
  selectedMethods,
  selectedModuleId,
  version,
  onAnalysisFilterDraftsChange,
  onRunDescriptiveAnalysis,
  onRunGraphicalSummaryAnalysis,
  onRunNormalityAnalysis,
  onSelectMethod,
  onNormalityAlphaChange,
  onToggleDescriptiveColumn,
  onToggleGraphicalSummaryColumn,
  onToggleNormalityColumn,
}: AnalysisShellProps) {
  const selectedModule =
    analysisCatalog?.modules.find((module) => module.module_id === selectedModuleId) ?? null;

  return (
    <section className="analysis-shell" aria-labelledby="analysis-modules-title">
      <div className="analysis-heading">
        <div>
          <h2 id="analysis-modules-title">분석 모듈</h2>
          {selectedModule !== null ? (
            <p>
              {selectedModule.label_ko} · {selectedModule.label_en}
            </p>
          ) : null}
        </div>
        <span className="status-pill">Gate B0</span>
      </div>
      {analysisCatalogError !== null ? (
        <div className="notice-box">분석 메서드 registry를 불러오지 못했습니다.</div>
      ) : null}
      {analysisCatalog === null && analysisCatalogError === null ? (
        <div className="notice-box">분석 메서드 조회 중</div>
      ) : null}
      {analysisCatalog !== null ? (
        <AnalysisWorkbench
          catalog={analysisCatalog}
          profile={profile}
          selectedMethod={selectedMethod}
          selectedMethods={selectedMethods}
          selectedModuleId={selectedModuleId}
          version={version}
          onSelectMethod={onSelectMethod}
          renderAnalysisFilters={(method) =>
            method.requires_dataset && version !== null ? (
              <>
                <AnalysisFilterControls
                  columns={version.columns}
                  drafts={analysisFilterDrafts}
                  onChange={onAnalysisFilterDraftsChange}
                />
                {analysisFilterValidationMessage !== null ? (
                  <div className="error-box">{analysisFilterValidationMessage}</div>
                ) : null}
              </>
            ) : null
          }
          renderExecutableMethod={(method) => {
            if (method.method_id === "eda.descriptive" && method.availability === "available") {
              return (
                <DescriptiveAnalysisPanel
                  analysisResult={analysisResult}
                  descriptiveColumns={descriptiveColumns}
                  descriptiveResult={descriptiveResult}
                  filterValidationError={analysisFilterValidationError}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  selectedColumnIds={selectedDescriptiveColumnIds}
                  version={version}
                  onRun={onRunDescriptiveAnalysis}
                  onToggleColumn={onToggleDescriptiveColumn}
                />
              );
            }
            if (
              method.method_id === "eda.graphical_summary" &&
              method.availability === "available"
            ) {
              return (
                <GraphicalSummaryPanel
                  analysisResult={graphicalSummaryAnalysisResult}
                  filterValidationError={analysisFilterValidationError}
                  graphicalColumns={graphicalSummaryColumns}
                  graphicalResult={graphicalSummaryResult}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  selectedColumnIds={selectedGraphicalSummaryColumnIds}
                  version={version}
                  onRun={onRunGraphicalSummaryAnalysis}
                  onToggleColumn={onToggleGraphicalSummaryColumn}
                />
              );
            }
            if (method.method_id === "eda.normality" && method.availability === "available") {
              return (
                <NormalityAnalysisPanel
                  alpha={normalityAlpha}
                  analysisResult={normalityAnalysisResult}
                  filterValidationError={analysisFilterValidationError}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  normalityColumns={normalityColumns}
                  normalityResult={normalityResult}
                  selectedColumnIds={selectedNormalityColumnIds}
                  version={version}
                  onAlphaChange={onNormalityAlphaChange}
                  onRun={onRunNormalityAnalysis}
                  onToggleColumn={onToggleNormalityColumn}
                />
              );
            }
            return null;
          }}
        />
      ) : null}
    </section>
  );
}
