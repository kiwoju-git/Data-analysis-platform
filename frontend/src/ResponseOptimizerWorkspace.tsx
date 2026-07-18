import { useEffect, useMemo, useRef, useState } from "react";

import {
  fetchResponseSurfaceAnalysis,
  fetchResponseSurfaceDesign,
  type DoeResponseSurfaceAnalysisCatalogItem,
  type DoeResponseSurfaceAnalysisResponse,
  type ResponseSurfaceDesignResponse,
} from "./api";
import { createLatestRequestGuard } from "./latestRequest";
import { ResponseOptimizerPanel } from "./ResponseOptimizerPanel";
import { useResponseSurfaceAnalysisCatalogState } from "./useResponseSurfaceAnalysisCatalogState";

export function ResponseOptimizerWorkspace({
  onNavigateToResponseSurface,
}: {
  onNavigateToResponseSurface: () => void;
}) {
  const initialQuery = useMemo(
    () => new URLSearchParams(typeof window === "undefined" ? "" : window.location.search),
    [],
  );
  const initialDesignId = validId(initialQuery.get("design_id"));
  const initialAnalysisId = validId(initialQuery.get("analysis_id"));
  const catalogState = useResponseSurfaceAnalysisCatalogState(
    initialDesignId,
    initialAnalysisId,
  );
  const [design, setDesign] = useState<ResponseSurfaceDesignResponse | null>(null);
  const [analysis, setAnalysis] =
    useState<DoeResponseSurfaceAnalysisResponse | null>(null);
  const [restoreError, setRestoreError] = useState<string | null>(null);
  const [isRestoring, setIsRestoring] = useState(false);
  const restoreGuard = useRef(createLatestRequestGuard()).current;

  useEffect(() => {
    restoreGuard.cancel();
    setDesign(null);
    setAnalysis(null);
    setRestoreError(null);
    setIsRestoring(false);
    if (
      catalogState.selectedDesignId === null ||
      catalogState.selectedAnalysisId === null
    ) {
      return;
    }
    const request = restoreGuard.begin();
    setIsRestoring(true);
    void Promise.all([
      fetchResponseSurfaceDesign(catalogState.selectedDesignId),
      fetchResponseSurfaceAnalysis(
        catalogState.selectedDesignId,
        catalogState.selectedAnalysisId,
      ),
    ])
      .then(([designResponse, analysisResponse]) => {
        if (!restoreGuard.isCurrent(request)) return;
        if (
          designResponse.design_id !== analysisResponse.design_id ||
          designResponse.design_version_id !== analysisResponse.design_version_id
        ) {
          setRestoreError("doe_rsm_analysis_dependency_mismatch");
          return;
        }
        setDesign(designResponse);
        setAnalysis(analysisResponse);
      })
      .catch((error) => {
        if (restoreGuard.isCurrent(request)) {
          setRestoreError(
            error instanceof Error ? error.message : "doe_rsm_analysis_restore_failed",
          );
        }
      })
      .finally(() => {
        if (restoreGuard.isCurrent(request)) setIsRestoring(false);
      });
    return () => restoreGuard.cancel();
  }, [
    catalogState.selectedAnalysisId,
    catalogState.selectedDesignId,
    restoreGuard,
  ]);

  function selectSource(value: string) {
    const [designId, analysisId] = value.split(":", 2);
    const nextDesignId = validId(designId ?? null);
    const nextAnalysisId = validId(analysisId ?? null);
    catalogState.onSelect(nextDesignId, nextAnalysisId);
    replaceWorkflowQuery(nextDesignId, nextAnalysisId);
  }

  const selectedValue =
    catalogState.selectedDesignId !== null && catalogState.selectedAnalysisId !== null
      ? `${catalogState.selectedDesignId}:${catalogState.selectedAnalysisId}`
      : "";

  return (
    <section className="analysis-run-panel" aria-labelledby="optimizer-workspace-title">
      <div className="panel-heading">
        <div>
          <h3 id="optimizer-workspace-title">저장된 RSM 분석으로 반응 최적화</h3>
          <p>regression.response_optimizer · 전용 워크플로</p>
        </div>
        <span className="status-pill status-ready">사용 가능 · 전용</span>
      </div>
      <div className="notice-box">
        저장된 full quadratic RSM 분석을 선택합니다. Source dependency와 checksum을 다시
        검증하며, blocking model은 최적화를 실행할 수 없습니다.
      </div>
      <div className="option-grid option-grid-wide">
        <label>
          <span>Source 반응표면 분석</span>
          <select
            aria-label="Source 반응표면 분석"
            disabled={catalogState.isLoading || isRestoring}
            value={selectedValue}
            onChange={(event) => selectSource(event.target.value)}
          >
            <option value="">반응표면 분석 선택</option>
            {selectedValue !== "" && catalogState.selectedSource === null ? (
              <option value={selectedValue}>
                저장된 선택 · {shortId(catalogState.selectedAnalysisId ?? "")}
              </option>
            ) : null}
            {catalogState.catalog?.analyses.map((item) => (
              <option
                key={item.analysis_id}
                value={`${item.design_id}:${item.analysis_id}`}
              >
                {sourceLabel(item)}
              </option>
            ))}
          </select>
        </label>
      </div>
      {catalogState.catalog?.total === 0 && catalogState.selectedAnalysisId === null ? (
        <div className="notice-box">
          <p>
            사용 가능한 반응표면 분석이 없습니다. 먼저 RSM 설계, 반응 입력, quadratic
            model 적합을 완료하세요.
          </p>
          <button
            className="secondary-button"
            onClick={onNavigateToResponseSurface}
            type="button"
          >
            반응표면법으로 이동
          </button>
        </div>
      ) : null}
      {catalogState.error !== null ? (
        <ErrorWithRetry code={catalogState.error} onRetry={catalogState.onRefresh} />
      ) : null}
      {isRestoring ? (
        <div className="notice-box" role="status">선택한 RSM dependency를 검증하고 있습니다.</div>
      ) : null}
      {catalogState.selectedSource !== null ? (
        <SourceSummary source={catalogState.selectedSource} />
      ) : null}
      {restoreError !== null ? (
        <div className="error-box" role="alert">
          선택한 RSM 분석을 복원하지 못했습니다. 오류 코드: {restoreError}
        </div>
      ) : null}
      {design !== null && analysis !== null ? (
        <ResponseOptimizerPanel design={design} analysis={analysis} />
      ) : null}
      {catalogState.catalog !== null && catalogState.catalog.total > catalogState.catalog.limit ? (
        <div className="result-pagination" aria-label="RSM source 목록 페이지 이동">
          <button
            disabled={catalogState.isLoading || !catalogState.catalog.has_previous}
            onClick={() =>
              catalogState.onPageChange(
                Math.max(0, catalogState.catalog!.offset - catalogState.catalog!.limit),
              )
            }
            type="button"
          >이전</button>
          <span>
            {catalogState.catalog.offset + 1}-
            {catalogState.catalog.offset + catalogState.catalog.returned} /{" "}
            {catalogState.catalog.total}
          </span>
          <button
            disabled={catalogState.isLoading || !catalogState.catalog.has_next}
            onClick={() =>
              catalogState.onPageChange(
                catalogState.catalog!.offset + catalogState.catalog!.limit,
              )
            }
            type="button"
          >다음</button>
        </div>
      ) : null}
    </section>
  );
}

function SourceSummary({ source }: { source: DoeResponseSurfaceAnalysisCatalogItem }) {
  return (
    <div className="metadata-grid" aria-label="선택한 RSM source metadata">
      <span>Design</span><strong>{source.design_name}</strong>
      <span>Response</span><strong>{source.response_name}</strong>
      <span>Revision</span><strong>v{source.response_revision_number ?? "?"}</strong>
      <span>Eligibility</span><strong>{eligibilityLabel(source.eligibility_status)}</strong>
      <span>Blocking / advisory</span><strong>{source.blocking_issue_count} / {source.advisory_issue_count}</strong>
      <span>Analysis ID</span><strong>{shortId(source.analysis_id)}</strong>
    </div>
  );
}

function ErrorWithRetry({ code, onRetry }: { code: string; onRetry: () => void }) {
  return (
    <div className="error-box" role="alert">
      <p>RSM source 목록을 불러오지 못했습니다. 오류 코드: {code}</p>
      <button className="secondary-button" onClick={onRetry} type="button">다시 시도</button>
    </div>
  );
}

function sourceLabel(source: DoeResponseSurfaceAnalysisCatalogItem): string {
  return `${source.design_name} · ${source.response_name} · ${eligibilityLabel(source.eligibility_status)} · ${shortId(source.analysis_id)}`;
}

function eligibilityLabel(value: DoeResponseSurfaceAnalysisCatalogItem["eligibility_status"]): string {
  switch (value) {
    case "eligible": return "실행 가능";
    case "acknowledgment_required": return "확인 필요";
    case "ineligible": return "차단됨";
    case "integrity_error": return "무결성 오류";
    case "incompatible_method_version": return "버전 불일치";
  }
}

function validId(value: string | null): string | null {
  return value !== null && /^[0-9a-f]{8}-[0-9a-f-]{27}$/i.test(value) ? value : null;
}

function replaceWorkflowQuery(designId: string | null, analysisId: string | null) {
  const url = new URL(window.location.href);
  if (designId === null || analysisId === null) {
    url.searchParams.delete("design_id");
    url.searchParams.delete("analysis_id");
  } else {
    url.searchParams.set("design_id", designId);
    url.searchParams.set("analysis_id", analysisId);
  }
  window.history.replaceState({}, "", `${url.pathname}${url.search}`);
}

function shortId(value: string): string {
  return value.length <= 16 ? value : `${value.slice(0, 8)}…${value.slice(-6)}`;
}
