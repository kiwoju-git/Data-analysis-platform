import { useEffect, useRef, useState } from "react";

import {
  fetchAnalysisRuns,
  type AnalysisMethodDescriptor,
  type AnalysisRunListResponse,
  type DatasetVersionResponse,
} from "./api";
import { formatDateTime } from "./analysisWorkbenchUtils";
import { createLatestRequestGuard } from "./latestRequest";

const COMPACT_HISTORY_LIMIT = 3;

export function CompactAnalysisHistoryPanel({
  isRestoring,
  method,
  refreshKey,
  version,
  onRestore,
}: {
  isRestoring: boolean;
  method: AnalysisMethodDescriptor;
  refreshKey: string | null;
  version: DatasetVersionResponse;
  onRestore: (analysisId: string) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [history, setHistory] = useState<AnalysisRunListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const requestGuard = useRef(createLatestRequestGuard()).current;

  useEffect(() => {
    requestGuard.cancel();
    setHistory(null);
    setError(null);
    setIsLoading(false);
    if (!isOpen) return;

    const request = requestGuard.begin();
    setIsLoading(true);
    void fetchAnalysisRuns({
      datasetVersionId: version.version_id,
      methodId: method.method_id,
      status: null,
      stale: null,
      resultAvailable: null,
      limit: COMPACT_HISTORY_LIMIT,
      offset: 0,
    })
      .then((response) => {
        if (requestGuard.isCurrent(request)) setHistory(response);
      })
      .catch((fetchError) => {
        if (!requestGuard.isCurrent(request)) return;
        setError(
          fetchError instanceof Error ? fetchError.message : "analysis_history_fetch_failed",
        );
      })
      .finally(() => {
        if (requestGuard.isCurrent(request)) setIsLoading(false);
      });

    return () => requestGuard.cancel(request);
  }, [isOpen, method.method_id, refreshKey, requestGuard, version.version_id]);

  const countLabel =
    history === null
      ? "확인 전"
      : history.has_more
        ? `${history.returned_count.toLocaleString()}+`
        : history.returned_count.toLocaleString();
  const fullHistoryUrl = `/reports?tab=history&dataset_version_id=${encodeURIComponent(version.version_id)}&method_id=${encodeURIComponent(method.method_id)}`;

  return (
    <section className="compact-analysis-history" aria-labelledby="compact-history-title">
      <div className="compact-history-heading">
        <div>
          <h4 id="compact-history-title">저장된 분석 이력</h4>
          <p>이 데이터셋에서 이전에 실행한 결과를 다시 열거나 비교할 수 있습니다.</p>
        </div>
        <span className="status-pill" aria-label={`조회된 이력 ${countLabel}개`}>
          {countLabel}
        </span>
        <button
          aria-controls="compact-analysis-history-content"
          aria-expanded={isOpen}
          className="secondary-button compact-button"
          onClick={() => setIsOpen((current) => !current)}
          type="button"
        >
          {isOpen ? "닫기" : "최근 이력 열기"}
        </button>
      </div>
      {isOpen ? (
        <div id="compact-analysis-history-content">
          {isLoading ? <p role="status">최근 분석 이력 조회 중</p> : null}
          {error !== null ? (
            <div className="error-box" role="alert">
              최근 이력을 불러오지 못했습니다. 오류 코드: {error}
            </div>
          ) : null}
          {history !== null && history.runs.length === 0 ? (
            <p className="field-note">저장된 분석 없음</p>
          ) : null}
          {history !== null && history.runs.length > 0 ? (
            <div className="compact-history-list" aria-label="최근 저장 분석">
              {history.runs.map((run) => (
                <article key={run.analysis_id}>
                  <span>
                    <strong>{run.method_id}</strong>
                    <small>
                      v{run.method_version} · {formatDateTime(run.created_at)}
                    </small>
                  </span>
                  {run.stale ? <span className="stale-badge">stale</span> : null}
                  <button
                    className="secondary-button compact-button"
                    disabled={!run.result_available || isRestoring}
                    onClick={() => onRestore(run.analysis_id)}
                    type="button"
                  >
                    {run.result_available ? "결과 불러오기" : "결과 없음"}
                  </button>
                </article>
              ))}
            </div>
          ) : null}
          <a className="secondary-button link-button compact-history-link" href={fullHistoryUrl}>
            전체 이력 관리
          </a>
        </div>
      ) : null}
    </section>
  );
}
