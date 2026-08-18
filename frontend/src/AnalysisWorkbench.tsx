import { startTransition, useRef, useState, type ReactNode } from "react";

import { AnalysisPanelBoundary } from "./AnalysisPanelBoundary";
import { AnalysisDomainLanding } from "./AnalysisDomainLanding";
import { AnalysisResultExportPanel } from "./AnalysisResultExportPanel";
import { CompactAnalysisHistoryPanel } from "./CompactAnalysisHistoryPanel";
import { MethodHelpDrawer } from "./MethodHelpDrawer";
import { getMethodCardTags } from "./analysisMethodGuidance";
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
import { getAnalysisRunErrorDetails } from "./analysisRunErrors";
import type { AnalysisDomainDefinition } from "./analysisDomains";
import { analysisDomainForMethod } from "./analysisDomainMapping";
import type {
  AnalysisHistoryResultAvailabilityFilter,
  AnalysisHistoryStaleFilter,
} from "./analysisWorkbenchTypes";
import { availabilityLabel } from "./analysisWorkbenchUtils";
import { methodLabel } from "./i18n/catalogLabels";
import { useI18n } from "./i18n/LocaleProvider";

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
  activeDomain?: AnalysisDomainDefinition | null;
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
  showSelectedMethod?: boolean;
  onOpenDomain?: (domain: AnalysisDomainDefinition) => void;
  onSelectMethod: (moduleId: AnalysisModuleId, methodId: string | null) => void;
  onOpenHelp?: (section: "purpose" | "roles") => void;
  renderAnalysisFilters?: (method: AnalysisMethodDescriptor) => ReactNode;
  renderExecutableMethod: (method: AnalysisMethodDescriptor) => ReactNode;
}

export function AnalysisWorkbench({
  activeDomain,
  catalog,
  selectedMethod,
  selectedAnalysisResult = null,
  analysisRunError,
  exportState,
  restoredState,
  version,
  profile,
  showSelectedMethod = true,
  onOpenDomain = () => undefined,
  onSelectMethod,
  onOpenHelp = () => undefined,
  renderAnalysisFilters,
  renderExecutableMethod,
}: AnalysisWorkbenchProps) {
  const { locale } = useI18n();
  const [isMethodHelpOpen, setIsMethodHelpOpen] = useState(false);
  const methodHelpTriggerRef = useRef<HTMLButtonElement>(null);
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
  const effectiveRestoredState = {
    isRestoringAnalysisResult: restoredState?.isRestoringAnalysisResult ?? false,
    restoredAnalysisResult: restoredState?.restoredAnalysisResult ?? null,
    restoredAnalysisResultError: restoredState?.restoredAnalysisResultError ?? null,
    onRestoreAnalysisRun: restoredState?.onRestoreAnalysisRun ?? (() => undefined),
  };
  const analysisResultForExport =
    effectiveRestoredState.restoredAnalysisResult ?? selectedAnalysisResult;
  const selectedHypothesisTags =
    selectedMethod?.module_id === "hypothesis"
      ? getMethodCardTags(selectedMethod.method_id)
      : [];
  const selectMethod = (moduleId: AnalysisModuleId, methodId: string | null) => {
    setIsMethodHelpOpen(false);
    startTransition(() => {
      onSelectMethod(moduleId, methodId);
    });
  };
  const resolvedDomain =
    activeDomain === undefined && selectedMethod !== null
      ? analysisDomainForMethod(selectedMethod.method_id)
      : activeDomain ?? null;

  return (
    <>
      <div className="analysis-help-links" aria-label="분석 선택 도움말">
        <button className="text-button" onClick={() => onOpenHelp("purpose")} type="button">
          분석 선택 도움말
        </button>
        <button className="text-button" onClick={() => onOpenHelp("roles")} type="button">
          역할 사전
        </button>
      </div>
      <AnalysisDomainLanding
        catalog={catalog}
        domain={resolvedDomain}
        selectedMethodId={showSelectedMethod ? selectedMethod?.method_id ?? null : null}
        onOpenDomain={onOpenDomain}
        onSelectMethod={(method) => selectMethod(method.module_id, method.method_id)}
      />
      {showSelectedMethod && selectedMethod !== null ? (
        <section className="analysis-workbench" aria-labelledby="workbench-title">
          <div className="panel-heading workbench-heading">
            <div className="workbench-heading-main">
              <h3 id="workbench-title">{methodLabel(selectedMethod, locale)}</h3>
              <p>
                {locale === "ko" ? `${selectedMethod.label_en} · ` : ""}{selectedMethod.method_id}
              </p>
            </div>
            <div className="workbench-heading-side">
              {selectedHypothesisTags.length > 0 ? (
                <aside
                  aria-label={`${methodLabel(selectedMethod, locale)} 입력 및 설계 기준`}
                  className="hypothesis-method-context"
                >
                  <strong>입력·설계 기준</strong>
                  <div className="method-card-tags">
                    {selectedHypothesisTags.map((tag) => (
                      <span
                        className={`method-card-tag method-card-tag-${tag.category}`}
                        key={`${tag.category}-${tag.label}`}
                      >
                        {tag.label}
                      </span>
                    ))}
                  </div>
                </aside>
              ) : null}
              <div className="workbench-heading-actions">
                <button
                  aria-controls="method-help-drawer"
                  aria-expanded={isMethodHelpOpen}
                  className="secondary-button compact-button"
                  onClick={() => setIsMethodHelpOpen((open) => !open)}
                  ref={methodHelpTriggerRef}
                  type="button"
                >
                  분석 도움말
                </button>
                <span className={`availability-badge availability-${selectedMethod.availability}`}>
                  {availabilityLabel(selectedMethod)}
                </span>
              </div>
            </div>
          </div>
          <MethodHelpDrawer
            method={selectedMethod}
            open={isMethodHelpOpen}
            profile={profile}
            trigger={methodHelpTriggerRef.current}
            version={version}
            onClose={() => setIsMethodHelpOpen(false)}
          />
          {selectedMethod.execution_mode === "dedicated" ? (
            <div className="notice-box">
              저장된 Source 자산을 선택하면 연결 관계와 파일 무결성을 다시 확인합니다.
              확인을 통과한 자산만 실행할 수 있습니다.
            </div>
          ) : null}
          {selectedMethod.execution_mode !== "dedicated" &&
          renderAnalysisFilters !== undefined
            ? renderAnalysisFilters(selectedMethod)
            : null}
          {executablePanel !== null && executablePanel !== undefined ? (
            <AnalysisPanelBoundary panelKey={selectedMethod.method_id}>
              {executablePanel}
            </AnalysisPanelBoundary>
          ) : null}
          {selectedMethod.execution_mode !== "dedicated" && version !== null ? (
            <CompactAnalysisHistoryPanel
              isRestoring={effectiveRestoredState.isRestoringAnalysisResult}
              method={selectedMethod}
              refreshKey={selectedAnalysisResult?.analysis_id ?? null}
              version={version}
              onRestore={effectiveRestoredState.onRestoreAnalysisRun}
            />
          ) : null}
          {selectedMethod.execution_mode !== "dedicated" ? <AnalysisResultExportPanel
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
          /> : null}
          {analysisRunError !== null ? (
            <AnalysisRunErrorNotice errorCode={analysisRunError} />
          ) : null}
          {executablePanel === null || executablePanel === undefined ? (
            <section className="analysis-run-panel" aria-label="분석 실행 상태">
              <div className="notice-box">{workbenchStatusMessage(selectedMethod, locale)}</div>
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

function workbenchStatusMessage(
  method: AnalysisMethodDescriptor,
  locale: "en" | "ko",
): string {
  if (method.availability === "disabled") {
    return locale === "ko"
      ? method.disabled_reason ?? "이 메서드는 현재 비활성 상태입니다."
      : "This method is currently unavailable.";
  }
  if (method.availability === "planned") {
    return locale === "ko"
      ? method.disabled_reason ??
          "계산 코드, 기준 데이터, 수치 검증 테스트가 준비된 뒤 실행할 수 있습니다."
      : "This planned method is not yet available to run.";
  }
  return "선택한 메서드는 현재 실행할 수 있습니다.";
}
