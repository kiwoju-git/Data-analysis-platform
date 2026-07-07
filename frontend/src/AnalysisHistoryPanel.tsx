import type {
  AnalysisMethodListResponse,
  AnalysisRunComparisonResponse,
  AnalysisResultEnvelope,
  AnalysisRunListResponse,
  AnalysisRunState,
  DatasetVersionResponse,
} from "./api";
import { AnalysisComparisonPanel } from "./AnalysisComparisonPanel";
import type {
  AnalysisHistoryResultAvailabilityFilter,
  AnalysisHistoryStaleFilter,
} from "./analysisWorkbenchTypes";
import { formatDateTime, shortHash } from "./analysisWorkbenchUtils";

export function AnalysisHistoryPanel({
  catalog,
  history,
  methodIdFilter,
  offset,
  resultAvailabilityFilter,
  staleFilter,
  statusFilter,
  isLoading,
  isRestoring,
  fetchError,
  comparison,
  comparisonError,
  comparisonLeftId,
  comparisonRightId,
  isComparing,
  restoreError,
  restoredResult,
  version,
  onChangeFilters,
  onCompare,
  onPageChange,
  onRefresh,
  onRestore,
  onSelectComparisonRun,
}: {
  catalog: AnalysisMethodListResponse;
  history: AnalysisRunListResponse | null;
  methodIdFilter: string;
  offset: number;
  resultAvailabilityFilter: AnalysisHistoryResultAvailabilityFilter;
  staleFilter: AnalysisHistoryStaleFilter;
  statusFilter: AnalysisRunState | "";
  isLoading: boolean;
  isRestoring: boolean;
  fetchError: string | null;
  comparison: AnalysisRunComparisonResponse | null;
  comparisonError: string | null;
  comparisonLeftId: string | null;
  comparisonRightId: string | null;
  isComparing: boolean;
  restoreError: string | null;
  restoredResult: AnalysisResultEnvelope | null;
  version: DatasetVersionResponse | null;
  onChangeFilters: (filters: {
    methodId: string;
    resultAvailability: AnalysisHistoryResultAvailabilityFilter;
    stale: AnalysisHistoryStaleFilter;
    status: AnalysisRunState | "";
  }) => void;
  onCompare: () => void;
  onPageChange: (offset: number) => void;
  onRefresh: () => void;
  onRestore: (analysisId: string) => void;
  onSelectComparisonRun: (side: "left" | "right", analysisId: string) => void;
}) {
  const pageStart = history === null || history.returned_count === 0 ? 0 : history.offset + 1;
  const pageEnd = history === null ? 0 : history.offset + history.returned_count;
  const canMovePrevious = history !== null && history.offset > 0;
  const canMoveNext = history?.has_more === true;

  return (
    <section className="analysis-history-panel" aria-labelledby="analysis-history-title">
      <div className="panel-heading">
        <div>
          <h4 id="analysis-history-title">현재 데이터셋의 저장된 분석</h4>
          <p>
            {version === null
              ? "데이터셋 버전이 확정되면 저장된 분석을 조회할 수 있습니다."
              : `Dataset v${version.version_number} · ${version.version_id}`}
          </p>
        </div>
        <button
          className="secondary-button compact-button"
          disabled={version === null || isLoading}
          onClick={onRefresh}
          type="button"
        >
          {isLoading ? "조회 중" : "새로고침"}
        </button>
      </div>
      {version === null ? (
        <div className="notice-box">먼저 업로드 또는 붙여넣기 데이터를 파싱 확정해 dataset version을 만드세요.</div>
      ) : null}
      <div className="history-filter-summary">
        <strong>필터 상태</strong>
        <span>method {methodIdFilter.length === 0 ? "전체" : methodIdFilter}</span>
        <span>status {statusFilter.length === 0 ? "전체" : statusFilter}</span>
        <span>stale {staleFilter}</span>
        <span>result {resultAvailabilityFilter}</span>
      </div>
      <div className="analysis-history-controls">
        <label>
          <span>method</span>
          <select
            disabled={version === null || isLoading}
            onChange={(event) => {
              onChangeFilters({
                methodId: event.currentTarget.value,
                resultAvailability: resultAvailabilityFilter,
                stale: staleFilter,
                status: statusFilter,
              });
            }}
            value={methodIdFilter}
          >
            <option value="">전체</option>
            {catalog.methods.map((method) => (
              <option key={method.method_id} value={method.method_id}>
                {method.method_id}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>status</span>
          <select
            disabled={version === null || isLoading}
            onChange={(event) => {
              onChangeFilters({
                methodId: methodIdFilter,
                resultAvailability: resultAvailabilityFilter,
                stale: staleFilter,
                status: event.currentTarget.value as AnalysisRunState | "",
              });
            }}
            value={statusFilter}
          >
            <option value="">전체</option>
            <option value="succeeded">succeeded</option>
            <option value="failed">failed</option>
            <option value="cancelled">cancelled</option>
            <option value="running">running</option>
            <option value="queued">queued</option>
            <option value="cancel_requested">cancel_requested</option>
          </select>
        </label>
        <label>
          <span>stale</span>
          <select
            disabled={version === null || isLoading}
            onChange={(event) => {
              onChangeFilters({
                methodId: methodIdFilter,
                resultAvailability: resultAvailabilityFilter,
                stale: event.currentTarget.value as AnalysisHistoryStaleFilter,
                status: statusFilter,
              });
            }}
            value={staleFilter}
          >
            <option value="all">전체</option>
            <option value="stale">stale</option>
            <option value="fresh">fresh</option>
          </select>
        </label>
        <label>
          <span>result</span>
          <select
            disabled={version === null || isLoading}
            onChange={(event) => {
              onChangeFilters({
                methodId: methodIdFilter,
                resultAvailability: event.currentTarget
                  .value as AnalysisHistoryResultAvailabilityFilter,
                stale: staleFilter,
                status: statusFilter,
              });
            }}
            value={resultAvailabilityFilter}
          >
            <option value="all">전체</option>
            <option value="available">있음</option>
            <option value="unavailable">없음</option>
          </select>
        </label>
      </div>
      {fetchError !== null ? (
        <div className="error-box analysis-error-box" role="alert">
          <h4>분석 이력 조회 실패</h4>
          <code>오류 코드: {fetchError}</code>
        </div>
      ) : null}
      {version !== null && history !== null && history.runs.length === 0 ? (
        <div className="notice-box">현재 필터에 맞는 저장된 분석 결과가 없습니다.</div>
      ) : null}
      {history !== null && history.runs.length > 0 ? (
        <div className="analysis-history-list" aria-label="저장된 분석 목록">
          {history.runs.map((run) => (
            <article className="analysis-history-item" key={run.analysis_id}>
              <div>
                <strong>{run.method_id}</strong>
                <p>
                  v{run.method_version} · {run.status} · {formatDateTime(run.created_at)}
                </p>
                <div className="method-meta">
                  <span>{run.result_available ? "result 있음" : "result 없음"}</span>
                  <span>{run.artifact_count.toLocaleString()} artifacts</span>
                  {run.stale ? <span className="stale-badge">stale · 재검토 필요</span> : null}
                </div>
              </div>
              <div className="analysis-history-actions">
                <button
                  className="secondary-button compact-button"
                  disabled={!run.result_available || isRestoring}
                  onClick={() => {
                    onRestore(run.analysis_id);
                  }}
                  type="button"
                >
                  {run.result_available
                    ? isRestoring
                      ? "불러오는 중"
                      : "결과 불러오기"
                    : "결과 없음"}
                </button>
                <button
                  className={
                    comparisonLeftId === run.analysis_id
                      ? "secondary-button compact-button selected-compact-button"
                      : "secondary-button compact-button"
                  }
                  disabled={!run.result_available}
                  onClick={() => {
                    onSelectComparisonRun("left", run.analysis_id);
                  }}
                  type="button"
                >
                  왼쪽
                </button>
                <button
                  className={
                    comparisonRightId === run.analysis_id
                      ? "secondary-button compact-button selected-compact-button"
                      : "secondary-button compact-button"
                  }
                  disabled={!run.result_available}
                  onClick={() => {
                    onSelectComparisonRun("right", run.analysis_id);
                  }}
                  type="button"
                >
                  오른쪽
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : null}
      <div className="analysis-comparison-box" aria-label="저장된 분석 비교">
        <div>
          <strong>비교</strong>
          <span>left {comparisonLeftId === null ? "-" : shortHash(comparisonLeftId)}</span>
          <span>right {comparisonRightId === null ? "-" : shortHash(comparisonRightId)}</span>
        </div>
        <button
          className="secondary-button compact-button"
          disabled={
            comparisonLeftId === null ||
            comparisonRightId === null ||
            comparisonLeftId === comparisonRightId ||
            isComparing
          }
          onClick={onCompare}
          type="button"
        >
          {isComparing ? "비교 중" : "비교"}
        </button>
      </div>
      {comparisonError !== null ? (
        <div className="error-box analysis-error-box" role="alert">
          <h4>분석 비교 실패</h4>
          <code>오류 코드: {comparisonError}</code>
        </div>
      ) : null}
      {comparison !== null ? <AnalysisComparisonPanel comparison={comparison} /> : null}
      {history !== null ? (
        <div className="analysis-history-pagination" aria-label="저장된 분석 페이지">
          <span>
            {history.returned_count.toLocaleString()}개 표시 · {pageStart.toLocaleString()}-
            {pageEnd.toLocaleString()} · 다음 페이지 {history.has_more ? "있음" : "없음"}
          </span>
          <div>
            <button
              className="secondary-button compact-button"
              disabled={!canMovePrevious || isLoading}
              onClick={() => {
                onPageChange(Math.max(0, offset - history.limit));
              }}
              type="button"
            >
              이전
            </button>
            <button
              className="secondary-button compact-button"
              disabled={!canMoveNext || isLoading}
              onClick={() => {
                onPageChange(offset + history.limit);
              }}
              type="button"
            >
              다음
            </button>
          </div>
        </div>
      ) : null}
      {restoreError !== null ? (
        <div className="error-box analysis-error-box" role="alert">
          <h4>저장 결과 불러오기 실패</h4>
          <code>오류 코드: {restoreError}</code>
        </div>
      ) : null}
      {restoredResult !== null ? (
        <div className="restored-result-box" role="status">
          <strong>불러온 결과</strong>
          <span>
            {restoredResult.method_id} · v{restoredResult.method_version}
          </span>
          <span>{restoredResult.status}</span>
          <span>warning {restoredResult.warnings.length.toLocaleString()}개</span>
          <code>{shortHash(restoredResult.analysis_id)}</code>
          {typeof restoredResult.result?.summary_type === "string" ? (
            <span>{restoredResult.result.summary_type}</span>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
