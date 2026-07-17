import { startTransition, type ReactNode } from "react";

import { AnalysisHistoryPanel } from "./AnalysisHistoryPanel";
import { AnalysisPanelBoundary } from "./AnalysisPanelBoundary";
import { AnalysisResultExportPanel } from "./AnalysisResultExportPanel";
import { MethodPurposeHelper } from "./MethodPurposeHelper";
import { PreflightExplanationPanel } from "./PreflightExplanationPanel";
import { StatisticalRoleGuide } from "./StatisticalRoleGuide";
import type {
  AnalysisMethodDescriptor,
  AnalysisMethodListResponse,
  AnalysisModuleId,
  AnalysisRunComparisonResponse,
  AnalysisResultExportListResponse,
  AnalysisResultExportDeleteResponse,
  AnalysisResultExportDeletionPreflightResponse,
  AnalysisResultCsvExportResponse,
  AnalysisResultEnvelope,
  AnalysisResultHtmlReportResponse,
  AnalysisResultJsonExportResponse,
  AnalysisRunListResponse,
  AnalysisRunDeleteResponse,
  AnalysisRunDeletionPreflightResponse,
  AnalysisRunState,
  DatasetProfileResponse,
  DatasetVersionResponse,
} from "./api";
import { getAnalysisMethodGuidance } from "./analysisMethodGuidance";
import { getAnalysisRunErrorDetails } from "./analysisRunErrors";
import type {
  AnalysisHistoryResultAvailabilityFilter,
  AnalysisHistoryStaleFilter,
} from "./analysisWorkbenchTypes";
import { availabilityLabel } from "./analysisWorkbenchUtils";

export interface AnalysisWorkbenchExportState {
  analysisResultCsvExport?: AnalysisResultCsvExportResponse | null;
  analysisResultCsvExportError?: string | null;
  analysisResultExportDownloadError?: string | null;
  analysisResultExportDeletion?: AnalysisResultExportDeleteResponse | null;
  analysisResultExportDeletionError?: string | null;
  analysisResultExportDeletionPreflight?: AnalysisResultExportDeletionPreflightResponse | null;
  analysisResultExportList?: AnalysisResultExportListResponse | null;
  analysisResultExportListError?: string | null;
  analysisResultHtmlReport?: AnalysisResultHtmlReportResponse | null;
  analysisResultHtmlReportError?: string | null;
  analysisResultJsonExport?: AnalysisResultJsonExportResponse | null;
  analysisResultJsonExportError?: string | null;
  isCreatingAnalysisResultCsvExport?: boolean;
  isCreatingAnalysisResultHtmlReport?: boolean;
  isCreatingAnalysisResultJsonExport?: boolean;
  isDownloadingAnalysisResultExport?: boolean;
  isDeletingAnalysisResultExport?: boolean;
  isLoadingAnalysisResultExportList?: boolean;
  isLoadingAnalysisResultExportDeletionPreflight?: boolean;
  onCreateAnalysisResultCsvExport?: (analysisId: string) => void;
  onCreateAnalysisResultHtmlReport?: (analysisId: string) => void;
  onCreateAnalysisResultJsonExport?: (analysisId: string) => void;
  onDownloadAnalysisResultExport?: (analysisId: string, exportId: string) => void;
  onLoadAnalysisResultExportDeletionPreflight?: (
    analysisId: string,
    exportId: string,
  ) => void;
  onDeleteAnalysisResultExport?: (
    preflight: AnalysisResultExportDeletionPreflightResponse,
  ) => void;
  onClearAnalysisResultExportDeletion?: () => void;
}

export interface AnalysisWorkbenchHistoryState {
  analysisHistory?: AnalysisRunListResponse | null;
  analysisHistoryError?: string | null;
  analysisHistoryMethodId?: string;
  analysisHistoryOffset?: number;
  analysisHistoryResultAvailabilityFilter?: AnalysisHistoryResultAvailabilityFilter;
  analysisHistoryStaleFilter?: AnalysisHistoryStaleFilter;
  analysisHistoryStatus?: AnalysisRunState | "";
  analysisRunDeletion?: AnalysisRunDeleteResponse | null;
  analysisRunDeletionError?: string | null;
  analysisRunDeletionPreflight?: AnalysisRunDeletionPreflightResponse | null;
  isDeletingAnalysisRun?: boolean;
  isLoadingAnalysisHistory?: boolean;
  isLoadingAnalysisRunDeletionPreflight?: boolean;
  onChangeAnalysisHistoryFilters?: (filters: {
    methodId: string;
    resultAvailability: AnalysisHistoryResultAvailabilityFilter;
    stale: AnalysisHistoryStaleFilter;
    status: AnalysisRunState | "";
  }) => void;
  onChangeAnalysisHistoryPage?: (offset: number) => void;
  onRefreshAnalysisHistory?: () => void;
  onClearAnalysisRunDeletion?: () => void;
  onDeleteAnalysisRun?: (preflight: AnalysisRunDeletionPreflightResponse) => void;
  onLoadAnalysisRunDeletionPreflight?: (analysisId: string) => void;
}

export interface AnalysisWorkbenchComparisonState {
  analysisComparison?: AnalysisRunComparisonResponse | null;
  analysisComparisonError?: string | null;
  analysisComparisonLeftId?: string | null;
  analysisComparisonRightId?: string | null;
  isComparingAnalysisRuns?: boolean;
  onCompareAnalysisRuns?: () => void;
  onSelectAnalysisComparisonRun?: (side: "left" | "right", analysisId: string) => void;
}

export interface AnalysisWorkbenchRestoredState {
  isRestoringAnalysisResult?: boolean;
  restoredAnalysisResult?: AnalysisResultEnvelope | null;
  restoredAnalysisResultError?: string | null;
  onRestoreAnalysisRun?: (analysisId: string) => void;
}

interface AnalysisWorkbenchProps {
  catalog: AnalysisMethodListResponse;
  selectedModuleId: AnalysisModuleId;
  selectedMethods: AnalysisMethodDescriptor[];
  selectedMethod: AnalysisMethodDescriptor | null;
  selectedAnalysisResult?: AnalysisResultEnvelope | null;
  analysisRunError: string | null;
  comparisonState?: AnalysisWorkbenchComparisonState;
  exportState?: AnalysisWorkbenchExportState;
  historyState?: AnalysisWorkbenchHistoryState;
  restoredState?: AnalysisWorkbenchRestoredState;
  version: DatasetVersionResponse | null;
  profile: DatasetProfileResponse | null;
  onSelectMethod: (moduleId: AnalysisModuleId, methodId: string | null) => void;
  renderAnalysisFilters?: (method: AnalysisMethodDescriptor) => ReactNode;
  renderExecutableMethod: (method: AnalysisMethodDescriptor) => ReactNode;
}

const workbenchSteps = [
  "데이터",
  "역할",
  "옵션",
  "사전점검",
  "실행",
  "결과",
] as const;

export function AnalysisWorkbench({
  catalog,
  selectedModuleId,
  selectedMethods,
  selectedMethod,
  selectedAnalysisResult = null,
  analysisRunError,
  comparisonState,
  exportState,
  historyState,
  restoredState,
  version,
  profile,
  onSelectMethod,
  renderAnalysisFilters,
  renderExecutableMethod,
}: AnalysisWorkbenchProps) {
  const selectedGuidance =
    selectedMethod === null ? null : getAnalysisMethodGuidance(selectedMethod.method_id);
  const executablePanel =
    selectedMethod !== null &&
    (selectedMethod.availability === "available" || selectedMethod.method_id === "quality.gage_rr")
      ? renderExecutableMethod(selectedMethod)
      : null;
  const effectiveExportState = {
    analysisResultCsvExport: exportState?.analysisResultCsvExport ?? null,
    analysisResultCsvExportError: exportState?.analysisResultCsvExportError ?? null,
    analysisResultExportDownloadError: exportState?.analysisResultExportDownloadError ?? null,
    analysisResultExportDeletion: exportState?.analysisResultExportDeletion ?? null,
    analysisResultExportDeletionError: exportState?.analysisResultExportDeletionError ?? null,
    analysisResultExportDeletionPreflight:
      exportState?.analysisResultExportDeletionPreflight ?? null,
    analysisResultExportList: exportState?.analysisResultExportList ?? null,
    analysisResultExportListError: exportState?.analysisResultExportListError ?? null,
    analysisResultHtmlReport: exportState?.analysisResultHtmlReport ?? null,
    analysisResultHtmlReportError: exportState?.analysisResultHtmlReportError ?? null,
    analysisResultJsonExport: exportState?.analysisResultJsonExport ?? null,
    analysisResultJsonExportError: exportState?.analysisResultJsonExportError ?? null,
    isCreatingAnalysisResultCsvExport: exportState?.isCreatingAnalysisResultCsvExport ?? false,
    isCreatingAnalysisResultHtmlReport: exportState?.isCreatingAnalysisResultHtmlReport ?? false,
    isCreatingAnalysisResultJsonExport: exportState?.isCreatingAnalysisResultJsonExport ?? false,
    isDownloadingAnalysisResultExport: exportState?.isDownloadingAnalysisResultExport ?? false,
    isDeletingAnalysisResultExport: exportState?.isDeletingAnalysisResultExport ?? false,
    isLoadingAnalysisResultExportList: exportState?.isLoadingAnalysisResultExportList ?? false,
    isLoadingAnalysisResultExportDeletionPreflight:
      exportState?.isLoadingAnalysisResultExportDeletionPreflight ?? false,
    onCreateAnalysisResultCsvExport:
      exportState?.onCreateAnalysisResultCsvExport ?? (() => undefined),
    onCreateAnalysisResultHtmlReport:
      exportState?.onCreateAnalysisResultHtmlReport ?? (() => undefined),
    onCreateAnalysisResultJsonExport:
      exportState?.onCreateAnalysisResultJsonExport ?? (() => undefined),
    onDownloadAnalysisResultExport:
      exportState?.onDownloadAnalysisResultExport ?? (() => undefined),
    onLoadAnalysisResultExportDeletionPreflight:
      exportState?.onLoadAnalysisResultExportDeletionPreflight ?? (() => undefined),
    onDeleteAnalysisResultExport:
      exportState?.onDeleteAnalysisResultExport ?? (() => undefined),
    onClearAnalysisResultExportDeletion:
      exportState?.onClearAnalysisResultExportDeletion ?? (() => undefined),
  };
  const effectiveHistoryState = {
    analysisHistory: historyState?.analysisHistory ?? null,
    analysisHistoryError: historyState?.analysisHistoryError ?? null,
    analysisHistoryMethodId: historyState?.analysisHistoryMethodId ?? "",
    analysisHistoryOffset: historyState?.analysisHistoryOffset ?? 0,
    analysisHistoryResultAvailabilityFilter:
      historyState?.analysisHistoryResultAvailabilityFilter ?? "all",
    analysisHistoryStaleFilter: historyState?.analysisHistoryStaleFilter ?? "all",
    analysisHistoryStatus: historyState?.analysisHistoryStatus ?? "",
    analysisRunDeletion: historyState?.analysisRunDeletion ?? null,
    analysisRunDeletionError: historyState?.analysisRunDeletionError ?? null,
    analysisRunDeletionPreflight: historyState?.analysisRunDeletionPreflight ?? null,
    isDeletingAnalysisRun: historyState?.isDeletingAnalysisRun ?? false,
    isLoadingAnalysisHistory: historyState?.isLoadingAnalysisHistory ?? false,
    isLoadingAnalysisRunDeletionPreflight:
      historyState?.isLoadingAnalysisRunDeletionPreflight ?? false,
    onChangeAnalysisHistoryFilters:
      historyState?.onChangeAnalysisHistoryFilters ?? (() => undefined),
    onChangeAnalysisHistoryPage:
      historyState?.onChangeAnalysisHistoryPage ?? (() => undefined),
    onRefreshAnalysisHistory: historyState?.onRefreshAnalysisHistory ?? (() => undefined),
    onClearAnalysisRunDeletion:
      historyState?.onClearAnalysisRunDeletion ?? (() => undefined),
    onDeleteAnalysisRun: historyState?.onDeleteAnalysisRun ?? (() => undefined),
    onLoadAnalysisRunDeletionPreflight:
      historyState?.onLoadAnalysisRunDeletionPreflight ?? (() => undefined),
  };
  const effectiveComparisonState = {
    analysisComparison: comparisonState?.analysisComparison ?? null,
    analysisComparisonError: comparisonState?.analysisComparisonError ?? null,
    analysisComparisonLeftId: comparisonState?.analysisComparisonLeftId ?? null,
    analysisComparisonRightId: comparisonState?.analysisComparisonRightId ?? null,
    isComparingAnalysisRuns: comparisonState?.isComparingAnalysisRuns ?? false,
    onCompareAnalysisRuns: comparisonState?.onCompareAnalysisRuns ?? (() => undefined),
    onSelectAnalysisComparisonRun:
      comparisonState?.onSelectAnalysisComparisonRun ?? (() => undefined),
  };
  const effectiveRestoredState = {
    isRestoringAnalysisResult: restoredState?.isRestoringAnalysisResult ?? false,
    restoredAnalysisResult: restoredState?.restoredAnalysisResult ?? null,
    restoredAnalysisResultError: restoredState?.restoredAnalysisResultError ?? null,
    onRestoreAnalysisRun: restoredState?.onRestoreAnalysisRun ?? (() => undefined),
  };
  const analysisResultForExport =
    effectiveRestoredState.restoredAnalysisResult ?? selectedAnalysisResult;
  const selectMethod = (moduleId: AnalysisModuleId, methodId: string | null) => {
    startTransition(() => {
      onSelectMethod(moduleId, methodId);
    });
  };

  return (
    <>
      <MethodPurposeHelper catalog={catalog} onSelectMethod={selectMethod} />
      <StatisticalRoleGuide selectedMethod={selectedMethod} />
      <nav className="module-nav" aria-label="분석 모듈">
        {catalog.modules.map((module) => (
          <button
            aria-current={module.module_id === selectedModuleId ? "page" : undefined}
            className={
              module.module_id === selectedModuleId
                ? "module-button module-button-active"
                : "module-button"
            }
            key={module.module_id}
            onClick={() => {
              const firstMethod =
                catalog.methods.find((method) => method.module_id === module.module_id) ?? null;
              selectMethod(module.module_id, firstMethod?.method_id ?? null);
            }}
            type="button"
          >
            <span>{module.label_ko}</span>
            <small>{module.label_en}</small>
          </button>
        ))}
      </nav>
      <div className="method-grid" aria-label="분석 메서드">
        {selectedMethods.map((method) => (
          <button
            aria-pressed={method.method_id === selectedMethod?.method_id}
            className={
              method.method_id === selectedMethod?.method_id
                ? "method-item method-item-active"
                : "method-item"
            }
            key={method.method_id}
            onClick={() => {
              selectMethod(method.module_id, method.method_id);
            }}
            type="button"
          >
            <div className="method-title-row">
              <div>
                <h3>{method.label_ko}</h3>
                <p>{method.label_en}</p>
              </div>
              <span className={`availability-badge availability-${method.availability}`}>
                {availabilityLabel(method)}
              </span>
            </div>
            <div className="method-meta">
              <span>{method.method_id}</span>
              <span>v{method.method_version}</span>
              <span>{method.requires_dataset ? "데이터셋 필요" : "데이터셋 없이 가능"}</span>
            </div>
            {method.disabled_reason !== null ? (
              <p className="method-reason">{method.disabled_reason}</p>
            ) : null}
          </button>
        ))}
      </div>
      {selectedMethod !== null ? (
        <section className="analysis-workbench" aria-labelledby="workbench-title">
          <div className="panel-heading workbench-heading">
            <div>
              <h3 id="workbench-title">{selectedMethod.label_ko}</h3>
              <p>
                {selectedMethod.label_en} · {selectedMethod.method_id}
              </p>
            </div>
            <span className={`availability-badge availability-${selectedMethod.availability}`}>
              {availabilityLabel(selectedMethod)}
            </span>
          </div>
          <ol className="workbench-steps" aria-label="분석 실행 단계">
            {workbenchSteps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          <div className="workbench-summary">
            <div>
              <span>데이터셋</span>
              <strong>
                {version === null
                  ? selectedMethod.requires_dataset
                    ? "필요"
                    : "선택 사항"
                  : `v${version.version_number} · ${version.row_count.toLocaleString()}행`}
              </strong>
            </div>
            <div>
              <span>사전점검</span>
              <strong>
                {profile === null
                  ? "대기"
                  : `${profile.columns.length.toLocaleString()}컬럼 점검됨`}
              </strong>
            </div>
            <div>
              <span>실행 방식</span>
              <strong>{selectedMethod.execution_mode}</strong>
            </div>
          </div>
          <PreflightExplanationPanel
            guidance={selectedGuidance}
            method={selectedMethod}
            profile={profile}
            version={version}
          />
          {renderAnalysisFilters !== undefined ? renderAnalysisFilters(selectedMethod) : null}
          {selectedGuidance !== null ? (
            <>
              {selectedGuidance.plainLanguage !== undefined ||
              selectedGuidance.commonErrors !== undefined ? (
                <section className="method-help-box" aria-label="메서드 쉬운 설명">
                  {selectedGuidance.plainLanguage !== undefined ? (
                    <>
                      <h4>쉽게 말하면</h4>
                      <p>{selectedGuidance.plainLanguage}</p>
                    </>
                  ) : null}
                  {selectedGuidance.commonErrors !== undefined ? (
                    <>
                      <h4>오류가 자주 나는 이유</h4>
                      <ul className="compact-list">
                        {selectedGuidance.commonErrors.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </>
                  ) : null}
                </section>
              ) : null}
              <div className="guidance-grid" aria-label="메서드 입력 계약">
                <section>
                  <h4>필요 역할</h4>
                  <ul className="guidance-list">
                    {selectedGuidance.roleRequirements.map((role) => (
                      <li key={`${role.label}-${role.detail}`}>
                        <strong>{role.label}</strong>
                        <span>{role.required ? "필수" : "선택"}</span>
                        <p>{role.detail}</p>
                      </li>
                    ))}
                  </ul>
                </section>
                <section>
                  <h4>옵션</h4>
                  <ul className="compact-list">
                    {selectedGuidance.optionChecklist.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </section>
                <section>
                  <h4>사전점검</h4>
                  <ul className="compact-list">
                    {selectedGuidance.preflightChecks.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </section>
                <section>
                  <h4>결과 초점</h4>
                  <ul className="compact-list">
                    {selectedGuidance.resultFocus.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </section>
              </div>
            </>
          ) : null}
          {executablePanel !== null && executablePanel !== undefined ? (
            <AnalysisPanelBoundary panelKey={selectedMethod.method_id}>
              {executablePanel}
            </AnalysisPanelBoundary>
          ) : null}
          <AnalysisHistoryPanel
            catalog={catalog}
            history={effectiveHistoryState.analysisHistory}
            methodIdFilter={effectiveHistoryState.analysisHistoryMethodId}
            offset={effectiveHistoryState.analysisHistoryOffset}
            resultAvailabilityFilter={
              effectiveHistoryState.analysisHistoryResultAvailabilityFilter
            }
            staleFilter={effectiveHistoryState.analysisHistoryStaleFilter}
            statusFilter={effectiveHistoryState.analysisHistoryStatus}
            isLoading={effectiveHistoryState.isLoadingAnalysisHistory}
            isRestoring={effectiveRestoredState.isRestoringAnalysisResult}
            restoreError={effectiveRestoredState.restoredAnalysisResultError}
            fetchError={effectiveHistoryState.analysisHistoryError}
            comparison={effectiveComparisonState.analysisComparison}
            comparisonError={effectiveComparisonState.analysisComparisonError}
            comparisonLeftId={effectiveComparisonState.analysisComparisonLeftId}
            comparisonRightId={effectiveComparisonState.analysisComparisonRightId}
            isComparing={effectiveComparisonState.isComparingAnalysisRuns}
            restoredResult={effectiveRestoredState.restoredAnalysisResult}
            deletion={effectiveHistoryState.analysisRunDeletion}
            deletionError={effectiveHistoryState.analysisRunDeletionError}
            deletionPreflight={effectiveHistoryState.analysisRunDeletionPreflight}
            isDeleting={effectiveHistoryState.isDeletingAnalysisRun}
            isLoadingDeletionPreflight={
              effectiveHistoryState.isLoadingAnalysisRunDeletionPreflight
            }
            version={version}
            onChangeFilters={effectiveHistoryState.onChangeAnalysisHistoryFilters}
            onCompare={effectiveComparisonState.onCompareAnalysisRuns}
            onPageChange={effectiveHistoryState.onChangeAnalysisHistoryPage}
            onRefresh={effectiveHistoryState.onRefreshAnalysisHistory}
            onRestore={effectiveRestoredState.onRestoreAnalysisRun}
            onClearDeletion={effectiveHistoryState.onClearAnalysisRunDeletion}
            onDelete={effectiveHistoryState.onDeleteAnalysisRun}
            onLoadDeletionPreflight={
              effectiveHistoryState.onLoadAnalysisRunDeletionPreflight
            }
            onSelectComparisonRun={effectiveComparisonState.onSelectAnalysisComparisonRun}
          />
          <AnalysisResultExportPanel
            analysisResult={analysisResultForExport}
            csvExportError={effectiveExportState.analysisResultCsvExportError}
            csvExportResult={effectiveExportState.analysisResultCsvExport}
            downloadError={effectiveExportState.analysisResultExportDownloadError}
            deletion={effectiveExportState.analysisResultExportDeletion}
            deletionError={effectiveExportState.analysisResultExportDeletionError}
            deletionPreflight={effectiveExportState.analysisResultExportDeletionPreflight}
            exportList={effectiveExportState.analysisResultExportList}
            exportListError={effectiveExportState.analysisResultExportListError}
            htmlReportError={effectiveExportState.analysisResultHtmlReportError}
            htmlReportResult={effectiveExportState.analysisResultHtmlReport}
            isExportingCsv={effectiveExportState.isCreatingAnalysisResultCsvExport}
            isExportingHtml={effectiveExportState.isCreatingAnalysisResultHtmlReport}
            isExportingJson={effectiveExportState.isCreatingAnalysisResultJsonExport}
            isDownloadingExport={effectiveExportState.isDownloadingAnalysisResultExport}
            isDeletingExport={effectiveExportState.isDeletingAnalysisResultExport}
            isLoadingExportList={effectiveExportState.isLoadingAnalysisResultExportList}
            isLoadingDeletionPreflight={
              effectiveExportState.isLoadingAnalysisResultExportDeletionPreflight
            }
            exportError={effectiveExportState.analysisResultJsonExportError}
            exportResult={effectiveExportState.analysisResultJsonExport}
            onCreateCsvExport={effectiveExportState.onCreateAnalysisResultCsvExport}
            onCreateExport={effectiveExportState.onCreateAnalysisResultJsonExport}
            onCreateHtmlReport={effectiveExportState.onCreateAnalysisResultHtmlReport}
            onDownloadExport={effectiveExportState.onDownloadAnalysisResultExport}
            onLoadDeletionPreflight={
              effectiveExportState.onLoadAnalysisResultExportDeletionPreflight
            }
            onDeleteExport={effectiveExportState.onDeleteAnalysisResultExport}
            onClearDeletion={effectiveExportState.onClearAnalysisResultExportDeletion}
          />
          {analysisRunError !== null ? (
            <AnalysisRunErrorNotice errorCode={analysisRunError} />
          ) : null}
          {executablePanel === null || executablePanel === undefined ? (
            <section className="analysis-run-panel" aria-labelledby="method-status-title">
              <div className="panel-heading">
                <div>
                  <h3 id="method-status-title">실행 상태</h3>
                  <p>{selectedMethod.method_id}</p>
                </div>
                <span className={`availability-badge availability-${selectedMethod.availability}`}>
                  {availabilityLabel(selectedMethod)}
                </span>
              </div>
              <div className="notice-box">{workbenchStatusMessage(selectedMethod)}</div>
            </section>
          ) : null}
        </section>
      ) : null}
    </>
  );
}

function AnalysisRunErrorNotice({ errorCode }: { errorCode: string }) {
  const details = getAnalysisRunErrorDetails(errorCode);
  return (
    <div className="error-box analysis-error-box" role="alert">
      <h4>{details.title}</h4>
      <p>{details.message}</p>
      <p>
        <strong>해결 방법:</strong> {details.action}
      </p>
      <code>오류 코드: {errorCode}</code>
    </div>
  );
}

function workbenchStatusMessage(method: AnalysisMethodDescriptor): string {
  if (method.availability === "disabled") {
    return method.disabled_reason ?? "이 메서드는 현재 비활성 상태입니다.";
  }
  if (method.availability === "planned") {
    return (
      method.disabled_reason ??
      "계산 코드, 기준 데이터, 수치 검증 테스트가 준비된 뒤 실행할 수 있습니다."
    );
  }
  return "선택한 메서드는 현재 실행할 수 있습니다.";
}
