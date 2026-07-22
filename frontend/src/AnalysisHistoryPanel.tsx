import { useState } from "react";

import type {
  AnalysisMethodListResponse,
  AnalysisRunComparisonResponse,
  AnalysisResultEnvelope,
  AnalysisRunListResponse,
  AnalysisRunDeleteResponse,
  AnalysisRunDeletionPreflightResponse,
  AnalysisRunState,
  DatasetVersionResponse,
} from "./api";
import { AnalysisComparisonPanel } from "./AnalysisComparisonPanel";
import type {
  AnalysisHistoryResultAvailabilityFilter,
  AnalysisHistoryStaleFilter,
} from "./analysisWorkbenchTypes";
import { formatBytes, formatDateTime, shortHash } from "./analysisWorkbenchUtils";

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
  deletion,
  deletionError,
  deletionPreflight,
  isDeleting,
  isLoadingDeletionPreflight,
  version,
  onChangeFilters,
  onCompare,
  onPageChange,
  onRefresh,
  onRestore,
  onClearDeletion,
  onDelete,
  onLoadDeletionPreflight,
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
  deletion: AnalysisRunDeleteResponse | null;
  deletionError: string | null;
  deletionPreflight: AnalysisRunDeletionPreflightResponse | null;
  isDeleting: boolean;
  isLoadingDeletionPreflight: boolean;
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
  onClearDeletion: () => void;
  onDelete: (preflight: AnalysisRunDeletionPreflightResponse) => void;
  onLoadDeletionPreflight: (analysisId: string) => void;
  onSelectComparisonRun: (side: "left" | "right", analysisId: string) => void;
}) {
  const [pendingDeletionAnalysisId, setPendingDeletionAnalysisId] = useState<string | null>(null);
  const pageStart = history === null || history.returned_count === 0 ? 0 : history.offset + 1;
  const pageEnd = history === null ? 0 : history.offset + history.returned_count;
  const canMovePrevious = history !== null && history.offset > 0;
  const canMoveNext = history?.has_more === true;

  return (
    <section className="analysis-history-panel" aria-labelledby="analysis-history-title">
      <div className="panel-heading">
        <div>
          <h4 id="analysis-history-title">전체 분석 이력</h4>
          <p>
            {version === null
              ? "데이터셋 버전이 확정되면 저장된 분석을 조회할 수 있습니다."
              : `현재 데이터셋의 저장된 분석 · Dataset v${version.version_number} · ${version.version_id}`}
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
                <button
                  className="secondary-button compact-button"
                  disabled={
                    !run.result_available ||
                    run.status !== "succeeded" ||
                    isLoadingDeletionPreflight ||
                    isDeleting
                  }
                  onClick={() => {
                    setPendingDeletionAnalysisId(null);
                    onLoadDeletionPreflight(run.analysis_id);
                  }}
                  type="button"
                >
                  삭제 영향 확인
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : null}
      {isLoadingDeletionPreflight ? (
        <div className="notice-box">분석 실행 삭제 영향 확인 중</div>
      ) : null}
      {deletionPreflight !== null ? (
        <div className="notice-box" aria-label="analysis run 삭제 영향">
          <strong>{deletionPreflight.method_id}</strong>
          <span>
            파일 {deletionPreflight.counts.total_file_count.toLocaleString()}개 ·{" "}
            {formatBytes(deletionPreflight.counts.file_bytes)}
          </span>
          <span>
            metadata {deletionPreflight.counts.metadata_record_count.toLocaleString()}건 · export{" "}
            {deletionPreflight.counts.export_file_count.toLocaleString()}개
          </span>
          {deletionPreflight.deletion_ready ? (
            <>
              <p>저장 결과, row snapshot, 연결된 export를 한 번에 영구 삭제합니다.</p>
              <button
                className="secondary-button compact-button"
                disabled={isDeleting}
                onClick={() => setPendingDeletionAnalysisId(deletionPreflight.analysis_id)}
                type="button"
              >
                영구 삭제 확인
              </button>
            </>
          ) : (
            <>
              <p>참조 중인 자산이 있어 이 분석 실행은 삭제할 수 없습니다.</p>
              <div className="method-meta">
                {deletionPreflight.blockers.map((blocker) => (
                  <code key={blocker}>{analysisRunDeletionBlockerLabel(blocker)}</code>
                ))}
              </div>
            </>
          )}
        </div>
      ) : null}
      {pendingDeletionAnalysisId !== null &&
      deletionPreflight !== null &&
      pendingDeletionAnalysisId === deletionPreflight.analysis_id ? (
        <AnalysisRunDeletionConfirmation
          isDeleting={isDeleting}
          onCancel={() => {
            setPendingDeletionAnalysisId(null);
            onClearDeletion();
          }}
          onConfirm={() => onDelete(deletionPreflight)}
          preflight={deletionPreflight}
        />
      ) : null}
      {deletion !== null ? (
        <div className="notice-box" role="status">
          분석 실행 삭제 완료 · 파일 {deletion.deleted_counts.total_file_count.toLocaleString()}개 ·{" "}
          {formatBytes(deletion.deleted_counts.file_bytes)}
          {deletion.cleanup_status === "quarantined_pending_cleanup"
            ? " · 파일 cleanup은 다음 앱 시작에서 재시도됩니다."
            : ""}
        </div>
      ) : null}
      {deletionError !== null ? (
        <div className="error-box analysis-error-box" role="alert">
          <h4>분석 실행 삭제 실패</h4>
          <p>이력과 삭제 영향을 다시 확인한 뒤 재시도하세요.</p>
          <code>오류 코드: {deletionError}</code>
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

export function AnalysisRunDeletionConfirmation({
  isDeleting,
  onCancel,
  onConfirm,
  preflight,
}: {
  isDeleting: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  preflight: AnalysisRunDeletionPreflightResponse;
}) {
  return (
    <div className="error-box" aria-label="analysis run irreversible deletion 확인">
      <strong>{preflight.method_id}</strong>
      <p>
        파일 {preflight.counts.total_file_count.toLocaleString()}개 ·{" "}
        {formatBytes(preflight.counts.file_bytes)}와 metadata{" "}
        {preflight.counts.metadata_record_count.toLocaleString()}건을 영구 삭제합니다.
      </p>
      <p>저장 결과, row snapshot, 연결된 export는 복원할 수 없습니다.</p>
      <div className="button-row">
        <button
          className="secondary-button compact-button"
          disabled={isDeleting}
          onClick={onConfirm}
          type="button"
        >
          {isDeleting ? "영구 삭제 중" : "분석 실행 영구 삭제"}
        </button>
        <button
          className="secondary-button compact-button"
          disabled={isDeleting}
          onClick={onCancel}
          type="button"
        >
          취소
        </button>
      </div>
    </div>
  );
}

function analysisRunDeletionBlockerLabel(code: string): string {
  const labels: Record<string, string> = {
    analysis_run_deletion_status_unsupported: "완료되지 않은 실행",
    analysis_run_deletion_result_unavailable: "저장 결과 없음",
    analysis_run_deletion_regression_model_dependency: "저장 회귀모형이 참조 중",
    analysis_run_deletion_regression_prediction_dependency: "회귀 예측 실행이 참조 중",
    analysis_run_deletion_limit_set_dependency: "Phase II limit set이 참조 중",
    analysis_run_deletion_job_dependency: "job audit record가 참조 중",
  };
  return labels[code] ?? code;
}
