import type { ReactNode } from "react";

import { AnalysisHistoryPanel } from "./AnalysisHistoryPanel";
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
  AnalysisResultCsvExportResponse,
  AnalysisResultEnvelope,
  AnalysisResultHtmlReportResponse,
  AnalysisResultJsonExportResponse,
  AnalysisRunListResponse,
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

interface AnalysisWorkbenchProps {
  catalog: AnalysisMethodListResponse;
  selectedModuleId: AnalysisModuleId;
  selectedMethods: AnalysisMethodDescriptor[];
  selectedMethod: AnalysisMethodDescriptor | null;
  selectedAnalysisResult?: AnalysisResultEnvelope | null;
  analysisRunError: string | null;
  analysisResultCsvExport?: AnalysisResultCsvExportResponse | null;
  analysisResultCsvExportError?: string | null;
  analysisResultExportDownloadError?: string | null;
  analysisResultExportList?: AnalysisResultExportListResponse | null;
  analysisResultExportListError?: string | null;
  analysisResultHtmlReport?: AnalysisResultHtmlReportResponse | null;
  analysisResultHtmlReportError?: string | null;
  analysisResultJsonExport?: AnalysisResultJsonExportResponse | null;
  analysisResultJsonExportError?: string | null;
  analysisHistory?: AnalysisRunListResponse | null;
  analysisHistoryError?: string | null;
  analysisHistoryMethodId?: string;
  analysisHistoryOffset?: number;
  analysisHistoryResultAvailabilityFilter?: AnalysisHistoryResultAvailabilityFilter;
  analysisHistoryStaleFilter?: AnalysisHistoryStaleFilter;
  analysisHistoryStatus?: AnalysisRunState | "";
  analysisComparison?: AnalysisRunComparisonResponse | null;
  analysisComparisonError?: string | null;
  analysisComparisonLeftId?: string | null;
  analysisComparisonRightId?: string | null;
  isCreatingAnalysisResultCsvExport?: boolean;
  isCreatingAnalysisResultHtmlReport?: boolean;
  isCreatingAnalysisResultJsonExport?: boolean;
  isDownloadingAnalysisResultExport?: boolean;
  isLoadingAnalysisHistory?: boolean;
  isLoadingAnalysisResultExportList?: boolean;
  isComparingAnalysisRuns?: boolean;
  isRestoringAnalysisResult?: boolean;
  restoredAnalysisResult?: AnalysisResultEnvelope | null;
  restoredAnalysisResultError?: string | null;
  version: DatasetVersionResponse | null;
  profile: DatasetProfileResponse | null;
  onCreateAnalysisResultCsvExport?: (analysisId: string) => void;
  onCreateAnalysisResultHtmlReport?: (analysisId: string) => void;
  onCreateAnalysisResultJsonExport?: (analysisId: string) => void;
  onChangeAnalysisHistoryFilters?: (filters: {
    methodId: string;
    resultAvailability: AnalysisHistoryResultAvailabilityFilter;
    stale: AnalysisHistoryStaleFilter;
    status: AnalysisRunState | "";
  }) => void;
  onChangeAnalysisHistoryPage?: (offset: number) => void;
  onCompareAnalysisRuns?: () => void;
  onDownloadAnalysisResultExport?: (analysisId: string, exportId: string) => void;
  onRefreshAnalysisHistory?: () => void;
  onRestoreAnalysisRun?: (analysisId: string) => void;
  onSelectAnalysisComparisonRun?: (side: "left" | "right", analysisId: string) => void;
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
  analysisResultCsvExport = null,
  analysisResultCsvExportError = null,
  analysisResultExportDownloadError = null,
  analysisResultExportList = null,
  analysisResultExportListError = null,
  analysisResultHtmlReport = null,
  analysisResultHtmlReportError = null,
  analysisResultJsonExport = null,
  analysisResultJsonExportError = null,
  analysisHistory = null,
  analysisHistoryError = null,
  analysisHistoryMethodId = "",
  analysisHistoryOffset = 0,
  analysisHistoryResultAvailabilityFilter = "all",
  analysisHistoryStaleFilter = "all",
  analysisHistoryStatus = "",
  analysisComparison = null,
  analysisComparisonError = null,
  analysisComparisonLeftId = null,
  analysisComparisonRightId = null,
  isCreatingAnalysisResultCsvExport = false,
  isCreatingAnalysisResultHtmlReport = false,
  isCreatingAnalysisResultJsonExport = false,
  isDownloadingAnalysisResultExport = false,
  isLoadingAnalysisHistory = false,
  isLoadingAnalysisResultExportList = false,
  isComparingAnalysisRuns = false,
  isRestoringAnalysisResult = false,
  restoredAnalysisResult = null,
  restoredAnalysisResultError = null,
  version,
  profile,
  onCreateAnalysisResultCsvExport = () => undefined,
  onCreateAnalysisResultHtmlReport = () => undefined,
  onCreateAnalysisResultJsonExport = () => undefined,
  onChangeAnalysisHistoryFilters = () => undefined,
  onChangeAnalysisHistoryPage = () => undefined,
  onCompareAnalysisRuns = () => undefined,
  onDownloadAnalysisResultExport = () => undefined,
  onRefreshAnalysisHistory = () => undefined,
  onRestoreAnalysisRun = () => undefined,
  onSelectAnalysisComparisonRun = () => undefined,
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
  const analysisResultForExport = restoredAnalysisResult ?? selectedAnalysisResult;

  return (
    <>
      <MethodPurposeHelper catalog={catalog} onSelectMethod={onSelectMethod} />
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
              onSelectMethod(module.module_id, firstMethod?.method_id ?? null);
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
              onSelectMethod(method.module_id, method.method_id);
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
          {executablePanel !== null && executablePanel !== undefined ? executablePanel : null}
          <AnalysisHistoryPanel
            catalog={catalog}
            history={analysisHistory}
            methodIdFilter={analysisHistoryMethodId}
            offset={analysisHistoryOffset}
            resultAvailabilityFilter={analysisHistoryResultAvailabilityFilter}
            staleFilter={analysisHistoryStaleFilter}
            statusFilter={analysisHistoryStatus}
            isLoading={isLoadingAnalysisHistory}
            isRestoring={isRestoringAnalysisResult}
            restoreError={restoredAnalysisResultError}
            fetchError={analysisHistoryError}
            comparison={analysisComparison}
            comparisonError={analysisComparisonError}
            comparisonLeftId={analysisComparisonLeftId}
            comparisonRightId={analysisComparisonRightId}
            isComparing={isComparingAnalysisRuns}
            restoredResult={restoredAnalysisResult}
            version={version}
            onChangeFilters={onChangeAnalysisHistoryFilters}
            onCompare={onCompareAnalysisRuns}
            onPageChange={onChangeAnalysisHistoryPage}
            onRefresh={onRefreshAnalysisHistory}
            onRestore={onRestoreAnalysisRun}
            onSelectComparisonRun={onSelectAnalysisComparisonRun}
          />
          <AnalysisResultExportPanel
            analysisResult={analysisResultForExport}
            csvExportError={analysisResultCsvExportError}
            csvExportResult={analysisResultCsvExport}
            downloadError={analysisResultExportDownloadError}
            exportList={analysisResultExportList}
            exportListError={analysisResultExportListError}
            htmlReportError={analysisResultHtmlReportError}
            htmlReportResult={analysisResultHtmlReport}
            isExportingCsv={isCreatingAnalysisResultCsvExport}
            isExportingHtml={isCreatingAnalysisResultHtmlReport}
            isExportingJson={isCreatingAnalysisResultJsonExport}
            isDownloadingExport={isDownloadingAnalysisResultExport}
            isLoadingExportList={isLoadingAnalysisResultExportList}
            exportError={analysisResultJsonExportError}
            exportResult={analysisResultJsonExport}
            onCreateCsvExport={onCreateAnalysisResultCsvExport}
            onCreateExport={onCreateAnalysisResultJsonExport}
            onCreateHtmlReport={onCreateAnalysisResultHtmlReport}
            onDownloadExport={onDownloadAnalysisResultExport}
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
