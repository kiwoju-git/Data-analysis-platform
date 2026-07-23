import { useEffect, useRef, useState } from "react";

import type {
  AnalysisMethodListResponse,
  AnalysisResultEnvelope,
  DatasetVersionResponse,
} from "./api";
import { AnalysisHistoryWorkspace } from "./AnalysisHistoryWorkspace";
import { AnalysisRunDeletionConfirmation } from "./AnalysisHistoryPanel";
import type {
  AnalysisWorkbenchComparisonState,
  AnalysisWorkbenchHistoryState,
  AnalysisWorkbenchRestoredState,
} from "./AnalysisWorkbench";
import { AnalysisResultExportPanel } from "./AnalysisResultExportPanel";
import { formatDateTime } from "./analysisWorkbenchUtils";
import {
  reportCreationCapabilities,
  reportWorkflowCapabilities,
} from "./reportCenterCapabilities";
import { useAnalysisExportState } from "./useAnalysisExportState";
import { useAnalysisRunDeletionState } from "./useAnalysisRunDeletionState";
import { useReportCenterState } from "./useReportCenterState";

export function ReportCenterPage({
  catalog,
  comparisonState,
  currentDatasetVersionId,
  historyState,
  restoredState,
  version,
}: {
  catalog: AnalysisMethodListResponse | null;
  comparisonState?: AnalysisWorkbenchComparisonState;
  currentDatasetVersionId: string | null;
  historyState?: AnalysisWorkbenchHistoryState;
  restoredState?: AnalysisWorkbenchRestoredState;
  version?: DatasetVersionResponse | null;
}) {
  const [tab, setTab] = useState<"reports" | "history">(initialReportCenterTab);
  const onChangeHistoryFilters = historyState?.onChangeAnalysisHistoryFilters;

  useEffect(() => {
    if (tab !== "history" || onChangeHistoryFilters === undefined) return;
    onChangeHistoryFilters({
      methodId: queryValue("method_id") ?? "",
      resultAvailability: "all",
      stale: "all",
      status: "",
    });
  }, [onChangeHistoryFilters, tab]);

  const selectTab = (nextTab: "reports" | "history") => {
    setTab(nextTab);
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    url.searchParams.set("tab", nextTab);
    window.history.replaceState(null, "", `${url.pathname}${url.search}`);
  };

  return (
    <div className="report-center-page">
      <header className="page-heading-band">
        <div>
          <h2 id="report-center-title">리포트 센터</h2>
          <p>저장 분석의 전체 이력과 생성한 내보내기 파일을 관리합니다.</p>
        </div>
      </header>
      <div className="segmented-control" role="tablist" aria-label="리포트 센터 보기">
        <button
          aria-selected={tab === "reports"}
          className={tab === "reports" ? "segment-active" : ""}
          onClick={() => selectTab("reports")}
          role="tab"
          type="button"
        >
          보고서
        </button>
        <button
          aria-selected={tab === "history"}
          className={tab === "history" ? "segment-active" : ""}
          onClick={() => selectTab("history")}
          role="tab"
          type="button"
        >
          분석 이력
        </button>
      </div>
      {tab === "history" && catalog !== null ? (
        <AnalysisHistoryWorkspace
          catalog={catalog}
          comparisonState={comparisonState}
          historyState={historyState}
          restoredState={restoredState}
          version={version ?? null}
        />
      ) : null}
      {tab === "reports" ? (
        <ReportBrowser
          catalog={catalog}
          currentDatasetVersionId={currentDatasetVersionId}
        />
      ) : null}
    </div>
  );
}

function ReportBrowser({
  catalog,
  currentDatasetVersionId,
}: {
  catalog: AnalysisMethodListResponse | null;
  currentDatasetVersionId: string | null;
}) {
  const state = useReportCenterState(currentDatasetVersionId);
  const selectedItem =
    state.list?.runs.find(
      (item) => item.analysis_id === state.selectedAnalysisId,
    ) ?? null;

  return (
    <div className="report-browser-workspace">
      <div className="notice-box">
        Report Center는 기존 checksum 검증 export API를 사용합니다. 지원하지 않는
        dedicated HTML 형식은 일반 HTML로 대체하지 않습니다.
      </div>
      <section className="report-browser" aria-labelledby="report-browser-title">
        <div className="panel-heading">
          <div>
            <h3 id="report-browser-title">저장 분석 목록</h3>
            <p>선택한 결과의 작업은 해당 목록 항목 바로 아래에 표시됩니다.</p>
          </div>
          <button
            className="secondary-button"
            disabled={state.isLoadingList}
            onClick={state.onRefresh}
            type="button"
          >
            새로고침
          </button>
        </div>
        <ReportFilters
          catalog={catalog}
          currentDatasetVersionId={currentDatasetVersionId}
          state={state}
        />
        {state.isLoadingList ? (
          <div className="notice-box" role="status">리포트 목록을 불러오는 중입니다.</div>
        ) : null}
        {state.listError !== null ? (
          <div className="error-box" role="alert">오류 코드: {state.listError}</div>
        ) : null}
        {state.list !== null && state.list.runs.length === 0 ? (
          <div className="notice-box">조건에 맞는 저장 분석이 없습니다.</div>
        ) : null}
        <div className="report-run-list">
          {state.list?.runs.map((run) => {
            const selected = state.selectedAnalysisId === run.analysis_id;
            return (
              <article className="report-run-item" key={run.analysis_id}>
                <button
                  aria-current={selected ? "true" : undefined}
                  className={selected ? "report-run-row is-selected" : "report-run-row"}
                  disabled={!run.result_available || run.status !== "succeeded"}
                  onClick={() => state.onSelectAnalysis(run.analysis_id)}
                  type="button"
                >
                  <span>
                    <strong>
                      {catalog?.methods.find(
                        (method) => method.method_id === run.method_id,
                      )?.label_ko ?? run.method_id}
                    </strong>
                    <code>{run.method_id} · v{run.method_version}</code>
                  </span>
                  <span>완료 {formatDateTime(run.completed_at ?? run.updated_at)}</span>
                  <span>
                    Dataset{" "}
                    {run.dataset_version_id === null
                      ? "전용 source"
                      : run.dataset_version_id.slice(0, 12)}
                  </span>
                  <span>{run.artifact_count.toLocaleString()} artifacts</span>
                  <span>
                    {run.status} · result {run.result_available ? "있음" : "없음"}
                  </span>
                  {run.stale ? (
                    <span className="stale-badge">stale · 재검토 필요</span>
                  ) : (
                    <span>현재</span>
                  )}
                </button>
                {selected ? (
                  <SelectedReportState
                    isLoading={state.isLoadingResult}
                    onDeleted={state.onSelectedAnalysisDeleted}
                    result={state.selectedResult}
                    resultError={state.selectedResultError}
                    stale={run.stale}
                  />
                ) : null}
              </article>
            );
          })}
        </div>
        {state.selectedAnalysisId !== null && selectedItem === null ? (
          <div className="report-direct-selection">
            <SelectedReportState
              isLoading={state.isLoadingResult}
              onDeleted={state.onSelectedAnalysisDeleted}
              result={state.selectedResult}
              resultError={state.selectedResultError}
              stale={false}
            />
          </div>
        ) : null}
        {state.list !== null ? (
          <div className="analysis-history-pagination">
            <span>
              {state.list.returned_count === 0 ? 0 : state.list.offset + 1}부터{" "}
              {state.list.offset + state.list.returned_count}까지
            </span>
            <div>
              <button
                className="secondary-button compact-button"
                disabled={state.offset === 0}
                onClick={() => state.onChangeOffset(state.offset - state.list!.limit)}
                type="button"
              >
                이전
              </button>
              <button
                className="secondary-button compact-button"
                disabled={!state.list.has_more}
                onClick={() => state.onChangeOffset(state.offset + state.list!.limit)}
                type="button"
              >
                다음
              </button>
            </div>
          </div>
        ) : null}
      </section>
      <ReportCapabilityMatrix />
    </div>
  );
}

function ReportFilters({
  catalog,
  currentDatasetVersionId,
  state,
}: {
  catalog: AnalysisMethodListResponse | null;
  currentDatasetVersionId: string | null;
  state: ReturnType<typeof useReportCenterState>;
}) {
  return (
    <div className="report-filter-grid">
      <label>
        Method
        <select
          value={state.methodId}
          onChange={(event) => state.onChangeMethodId(event.target.value)}
        >
          <option value="">전체</option>
          {catalog?.methods.map((method) => (
            <option key={method.method_id} value={method.method_id}>
              {method.label_ko}
            </option>
          ))}
        </select>
      </label>
      <label>
        Stale 상태
        <select
          value={state.staleFilter}
          onChange={(event) =>
            state.onChangeStaleFilter(
              event.target.value as "all" | "fresh" | "stale",
            )
          }
        >
          <option value="all">전체</option>
          <option value="fresh">현재</option>
          <option value="stale">stale</option>
        </select>
      </label>
      <label>
        Status
        <select
          value={state.status}
          onChange={(event) =>
            state.onChangeStatus(event.target.value as typeof state.status)
          }
        >
          <option value="">전체</option>
          <option value="succeeded">succeeded</option>
          <option value="failed">failed</option>
          <option value="cancelled">cancelled</option>
          <option value="running">running</option>
          <option value="queued">queued</option>
        </select>
      </label>
      <label>
        저장 결과
        <select
          value={state.resultFilter}
          onChange={(event) =>
            state.onChangeResultFilter(
              event.target.value as typeof state.resultFilter,
            )
          }
        >
          <option value="available">있음</option>
          <option value="unavailable">없음</option>
          <option value="all">전체</option>
        </select>
      </label>
      <label className="checkbox-field report-dataset-filter">
        <input
          checked={state.currentDatasetOnly}
          disabled={currentDatasetVersionId === null}
          onChange={(event) =>
            state.onChangeCurrentDatasetOnly(event.target.checked)
          }
          type="checkbox"
        />
        현재 데이터셋만
      </label>
    </div>
  );
}

function SelectedReportState({
  isLoading,
  onDeleted,
  result,
  resultError,
  stale,
}: {
  isLoading: boolean;
  onDeleted: () => void;
  result: AnalysisResultEnvelope | null;
  resultError: string | null;
  stale: boolean;
}) {
  if (isLoading) {
    return (
      <div className="notice-box" role="status">
        저장 결과 무결성을 확인하는 중입니다.
      </div>
    );
  }
  if (resultError !== null) {
    return (
      <div className="error-box" role="alert">
        저장 결과를 열 수 없습니다. 오류 코드: {resultError}
      </div>
    );
  }
  return result === null ? null : (
    <SelectedReportActions onDeleted={onDeleted} result={result} stale={stale} />
  );
}

function SelectedReportActions({
  onDeleted,
  result,
  stale,
}: {
  onDeleted: () => void;
  result: AnalysisResultEnvelope;
  stale: boolean;
}) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const exportState = useAnalysisExportState({
    currentAnalysisId: result.analysis_id,
    currentDatasetVersionId: result.dataset_version_id,
    resetKey: 0,
  });
  const deletionState = useAnalysisRunDeletionState(result.analysis_id, onDeleted);
  const capabilities = reportCreationCapabilities(result.method_id);

  useEffect(() => {
    headingRef.current?.focus();
  }, [result.analysis_id]);

  return (
    <section className="report-selected-result" aria-labelledby="report-selected-title">
      <div className="panel-heading">
        <div>
          <h3 id="report-selected-title" ref={headingRef} tabIndex={-1}>
            선택한 결과 작업
          </h3>
          <p>{result.method_id} · v{result.method_version}</p>
        </div>
        {stale ? (
          <span className="stale-badge">stale · 보고서 해석 재검토</span>
        ) : null}
      </div>
      <p className="field-note">
        내보내기 파일 삭제는 export 하나만 제거합니다. 저장 분석 결과 삭제는
        result, row snapshot, 연결 export를 함께 제거합니다.
      </p>
      <AnalysisResultExportPanel
        analysisResult={result}
        creationCapabilities={capabilities}
        csvExportError={exportState.analysisResultCsvExportError}
        csvExportResult={exportState.analysisResultCsvExport}
        deletion={exportState.analysisResultExportDeletion}
        deletionError={exportState.analysisResultExportDeletionError}
        deletionPreflight={exportState.analysisResultExportDeletionPreflight}
        downloadError={exportState.analysisResultExportDownloadError}
        exportError={exportState.analysisResultJsonExportError}
        exportList={exportState.analysisResultExportList}
        exportListError={exportState.analysisResultExportListError}
        exportResult={exportState.analysisResultJsonExport}
        htmlReportError={exportState.analysisResultHtmlReportError}
        htmlReportResult={exportState.analysisResultHtmlReport}
        isDeletingExport={exportState.isDeletingAnalysisResultExport}
        isDownloadingExport={exportState.isDownloadingAnalysisResultExport}
        isExportingCsv={exportState.isCreatingAnalysisResultCsvExport}
        isExportingHtml={exportState.isCreatingAnalysisResultHtmlReport}
        isExportingJson={exportState.isCreatingAnalysisResultJsonExport}
        isLoadingDeletionPreflight={
          exportState.isLoadingAnalysisResultExportDeletionPreflight
        }
        isLoadingExportList={exportState.isLoadingAnalysisResultExportList}
        onClearDeletion={exportState.onClearAnalysisResultExportDeletion}
        onCreateCsvExport={exportState.onCreateAnalysisResultCsvExport}
        onCreateExport={exportState.onCreateAnalysisResultJsonExport}
        onCreateHtmlReport={exportState.onCreateAnalysisResultHtmlReport}
        onDeleteExport={exportState.onDeleteAnalysisResultExport}
        onDownloadExport={exportState.onDownloadAnalysisResultExport}
        onLoadDeletionPreflight={
          exportState.onLoadAnalysisResultExportDeletionPreflight
        }
      />
      {!capabilities.html ? (
        <p className="notice-box">
          이 dedicated workflow의 HTML 보고서는 현재 지원되지 않습니다.
        </p>
      ) : null}
      <div className="report-analysis-deletion">
        <button
          className="secondary-button"
          disabled={deletionState.isLoadingPreflight || deletionState.isDeleting}
          onClick={deletionState.onLoadPreflight}
          type="button"
        >
          {deletionState.isLoadingPreflight
            ? "삭제 영향 확인 중"
            : "저장 분석 결과 삭제 영향 확인"}
        </button>
        {deletionState.preflight !== null ? (
          deletionState.preflight.deletion_ready ? (
            <AnalysisRunDeletionConfirmation
              isDeleting={deletionState.isDeleting}
              onCancel={deletionState.onClear}
              onConfirm={() => deletionState.onDelete(deletionState.preflight!)}
              preflight={deletionState.preflight}
            />
          ) : (
            <div className="notice-box">
              참조 자산 때문에 삭제할 수 없습니다:{" "}
              {deletionState.preflight.blockers.join(", ")}
            </div>
          )
        ) : null}
        {deletionState.error !== null ? (
          <div className="error-box" role="alert">
            삭제 오류: {deletionState.error}
          </div>
        ) : null}
      </div>
    </section>
  );
}

function ReportCapabilityMatrix() {
  return (
    <section
      className="report-capability-section"
      aria-labelledby="report-capability-title"
    >
      <div className="panel-heading">
        <div>
          <h3 id="report-capability-title">전용 workflow 지원 범위</h3>
          <p>P0 capability matrix</p>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Workflow</th>
              <th>저장 결과</th>
              <th>JSON</th>
              <th>CSV</th>
              <th>HTML</th>
              <th>이동</th>
            </tr>
          </thead>
          <tbody>
            {reportWorkflowCapabilities.map((item) => (
              <tr key={item.methodId}>
                <td>
                  <strong>{item.label}</strong>
                  <span className="cell-subtle">{item.methodId}</span>
                </td>
                <td>{item.storedResult}</td>
                <td>{item.json}</td>
                <td>{item.csv}</td>
                <td>{item.html}</td>
                <td><a href={item.workflowPath}>열기</a></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function initialReportCenterTab(): "reports" | "history" {
  return queryValue("tab") === "history" ? "history" : "reports";
}

function queryValue(name: string): string | null {
  if (typeof window === "undefined") return null;
  return new URL(window.location.href).searchParams.get(name);
}
