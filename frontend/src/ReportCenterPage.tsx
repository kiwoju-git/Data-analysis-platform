import type { AnalysisMethodListResponse } from "./api";
import { AnalysisResultExportPanel } from "./AnalysisResultExportPanel";
import { formatDateTime } from "./analysisWorkbenchUtils";
import {
  reportCreationCapabilities,
  reportWorkflowCapabilities,
} from "./reportCenterCapabilities";
import { useAnalysisExportState } from "./useAnalysisExportState";
import { useReportCenterState } from "./useReportCenterState";

export function ReportCenterPage({
  catalog,
  currentDatasetVersionId,
}: {
  catalog: AnalysisMethodListResponse | null;
  currentDatasetVersionId: string | null;
}) {
  const state = useReportCenterState(currentDatasetVersionId);
  const exportState = useAnalysisExportState({
    currentAnalysisId: state.selectedResult?.analysis_id ?? null,
    currentDatasetVersionId: state.selectedResult?.dataset_version_id ?? null,
    resetKey: 0,
  });
  const selectedItem = state.list?.runs.find(
    (item) => item.analysis_id === state.selectedResult?.analysis_id,
  ) ?? null;
  const capabilities = state.selectedResult === null
    ? { json: true, csv: true, html: true }
    : reportCreationCapabilities(state.selectedResult.method_id);

  return (
    <div className="report-center-page">
      <header className="page-heading-band">
        <div><h2>리포트 센터</h2><p>저장된 일반 분석 결과의 JSON, CSV, HTML을 찾고 생성하고 다운로드합니다.</p></div>
      </header>
      <div className="notice-box">
        Report Center는 기존 checksum 검증 export API를 사용합니다. Predict와 DOE 전용 결과의
        지원 범위는 아래 capability 표와 해당 전용 화면에서 확인하세요.
      </div>
      <section className="report-browser" aria-labelledby="report-browser-title">
        <div className="panel-heading"><div><h3 id="report-browser-title">저장 분석 목록</h3><p>성공했고 저장 결과가 있는 analysis-run만 표시합니다.</p></div>
          <button className="secondary-button" disabled={state.isLoadingList} onClick={state.onRefresh} type="button">새로고침</button>
        </div>
        <div className="report-filter-grid">
          <label>Method
            <select value={state.methodId} onChange={(event) => state.onChangeMethodId(event.target.value)}>
              <option value="">전체</option>
              {catalog?.methods.map((method) => <option key={method.method_id} value={method.method_id}>{method.label_ko}</option>)}
            </select>
          </label>
          <label>Stale 상태
            <select value={state.staleFilter} onChange={(event) => state.onChangeStaleFilter(event.target.value as "all" | "fresh" | "stale")}>
              <option value="all">전체</option><option value="fresh">현재</option><option value="stale">stale</option>
            </select>
          </label>
          <label>Status
            <select value={state.status} onChange={(event) => state.onChangeStatus(event.target.value as typeof state.status)}>
              <option value="">전체</option><option value="succeeded">succeeded</option><option value="failed">failed</option><option value="cancelled">cancelled</option><option value="running">running</option><option value="queued">queued</option>
            </select>
          </label>
          <label>저장 결과
            <select value={state.resultFilter} onChange={(event) => state.onChangeResultFilter(event.target.value as typeof state.resultFilter)}>
              <option value="available">있음</option><option value="unavailable">없음</option><option value="all">전체</option>
            </select>
          </label>
          <label className="checkbox-field report-dataset-filter">
            <input checked={state.currentDatasetOnly} disabled={currentDatasetVersionId === null} onChange={(event) => state.onChangeCurrentDatasetOnly(event.target.checked)} type="checkbox" />
            현재 데이터셋만
          </label>
        </div>
        {state.isLoadingList ? <div className="notice-box" role="status">리포트 목록을 불러오는 중입니다.</div> : null}
        {state.listError !== null ? <div className="error-box" role="alert">오류 코드: {state.listError}</div> : null}
        {state.list !== null && state.list.runs.length === 0 ? <div className="notice-box">조건에 맞는 저장 분석이 없습니다.</div> : null}
        <div className="report-run-list">
          {state.list?.runs.map((run) => (
            <button className="report-run-row" disabled={!run.result_available || run.status !== "succeeded"} key={run.analysis_id} onClick={() => state.onSelectAnalysis(run.analysis_id)} type="button">
              <span><strong>{catalog?.methods.find((method) => method.method_id === run.method_id)?.label_ko ?? run.method_id}</strong><code>{run.method_id} · v{run.method_version}</code></span>
              <span>완료 {formatDateTime(run.completed_at ?? run.updated_at)}</span>
              <span>Dataset {run.dataset_version_id === null ? "전용 source" : run.dataset_version_id.slice(0, 12)}</span>
              <span>{run.artifact_count.toLocaleString()} artifacts</span>
              <span>{run.status} · result {run.result_available ? "있음" : "없음"}</span>
              {run.stale ? <span className="stale-badge">stale · 재검토 필요</span> : <span>현재</span>}
            </button>
          ))}
        </div>
        {state.list !== null ? (
          <div className="analysis-history-pagination">
            <span>{state.list.offset + 1}부터 {state.list.offset + state.list.returned_count}까지</span>
            <div><button className="secondary-button compact-button" disabled={state.offset === 0} onClick={() => state.onChangeOffset(state.offset - state.list!.limit)} type="button">이전</button>
              <button className="secondary-button compact-button" disabled={!state.list.has_more} onClick={() => state.onChangeOffset(state.offset + state.list!.limit)} type="button">다음</button></div>
          </div>
        ) : null}
      </section>
      {state.isLoadingResult ? <div className="notice-box" role="status">저장 결과 무결성을 확인하는 중입니다.</div> : null}
      {state.selectedResultError !== null ? <div className="error-box" role="alert">저장 결과를 열 수 없습니다. 오류 코드: {state.selectedResultError}</div> : null}
      {state.selectedResult !== null ? (
        <section className="report-selected-result" aria-labelledby="report-selected-title">
          <div className="panel-heading"><div><h3 id="report-selected-title">선택한 결과</h3><p>{state.selectedResult.method_id} · v{state.selectedResult.method_version}</p></div>
            {selectedItem?.stale ? <span className="stale-badge">stale · 보고서 해석 재검토</span> : null}
          </div>
          <AnalysisResultExportPanel
            analysisResult={state.selectedResult}
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
            isLoadingDeletionPreflight={exportState.isLoadingAnalysisResultExportDeletionPreflight}
            isLoadingExportList={exportState.isLoadingAnalysisResultExportList}
            onClearDeletion={exportState.onClearAnalysisResultExportDeletion}
            onCreateCsvExport={exportState.onCreateAnalysisResultCsvExport}
            onCreateExport={exportState.onCreateAnalysisResultJsonExport}
            onCreateHtmlReport={exportState.onCreateAnalysisResultHtmlReport}
            onDeleteExport={exportState.onDeleteAnalysisResultExport}
            onDownloadExport={exportState.onDownloadAnalysisResultExport}
            onLoadDeletionPreflight={exportState.onLoadAnalysisResultExportDeletionPreflight}
          />
          {!capabilities.html ? <p className="notice-box">이 dedicated workflow의 HTML 보고서는 현재 지원되지 않습니다. 지원되지 않는 형식을 일반 HTML로 대체하지 않습니다.</p> : null}
        </section>
      ) : null}
      <section className="report-capability-section" aria-labelledby="report-capability-title">
        <div className="panel-heading"><div><h3 id="report-capability-title">전용 workflow 지원 범위</h3><p>P0 capability matrix</p></div></div>
        <div className="table-wrap"><table><thead><tr><th>Workflow</th><th>저장 결과</th><th>JSON</th><th>CSV</th><th>HTML</th><th>이동</th></tr></thead>
          <tbody>{reportWorkflowCapabilities.map((item) => <tr key={item.methodId}><td><strong>{item.label}</strong><span className="cell-subtle">{item.methodId}</span></td><td>{item.storedResult}</td><td>{item.json}</td><td>{item.csv}</td><td>{item.html}</td><td><a href={item.workflowPath}>열기</a></td></tr>)}</tbody></table></div>
      </section>
    </div>
  );
}
