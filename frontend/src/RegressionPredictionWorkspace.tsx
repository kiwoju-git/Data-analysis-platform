import { useMemo } from "react";

import type { RegressionModelCatalogItem } from "./api";
import { RegressionPredictionPanel } from "./RegressionPredictionPanel";
import { useRegressionModelCatalogState } from "./useRegressionModelCatalogState";
import { useRegressionModelRetentionState } from "./useRegressionModelRetentionState";
import { useRegressionPredictionExportState } from "./useRegressionPredictionExportState";
import { useRegressionPredictionRowsState } from "./useRegressionPredictionRowsState";
import { useRegressionPredictionState } from "./useRegressionPredictionState";
import { useRegressionPredictionTargetState } from "./useRegressionPredictionTargetState";

export function RegressionPredictionWorkspace({
  onNavigateToLinearModel,
}: {
  onNavigateToLinearModel: () => void;
}) {
  const initialQuery = useMemo(
    () => new URLSearchParams(typeof window === "undefined" ? "" : window.location.search),
    [],
  );
  const initialModelId = validId(initialQuery.get("model_id"));
  const initialTargetVersionId = validId(initialQuery.get("target_version_id"));
  const modelCatalog = useRegressionModelCatalogState(initialModelId);
  const retention = useRegressionModelRetentionState(modelCatalog.selectedModelId);
  const sourceVersionId = retention.manifest?.dataset_version_id ?? null;
  const targetState = useRegressionPredictionTargetState({
    activeModelId: modelCatalog.selectedModelId,
    currentVersionId: sourceVersionId,
    initialTargetVersionId,
  });
  const predictionState = useRegressionPredictionState({
    confidenceLevel: 0.95,
    currentDatasetVersionId: sourceVersionId,
    modelId: modelCatalog.selectedModelId,
    targetDatasetVersionId: targetState.selectedTargetVersionId,
  });
  const rowsState = useRegressionPredictionRowsState(
    predictionState.prediction?.prediction_id ?? null,
  );
  const exportState = useRegressionPredictionExportState(
    predictionState.prediction?.prediction_id ?? null,
  );
  const selectedCatalogModel = modelCatalog.selectedModel;
  const catalogBlocksModel =
    selectedCatalogModel?.availability === "source_stale" ||
    selectedCatalogModel?.availability === "integrity_error";
  const modelReady = retention.availability === "available" && !catalogBlocksModel;
  function selectModel(modelId: string | null) {
    modelCatalog.onSelect(modelId);
    replaceWorkflowQuery({ model_id: modelId, target_version_id: null });
  }

  function selectTarget(versionId: string) {
    targetState.onSelect(versionId);
    replaceWorkflowQuery({
      model_id: modelCatalog.selectedModelId,
      target_version_id: versionId,
    });
  }

  return (
    <section className="analysis-run-panel" aria-labelledby="prediction-workspace-title">
      <div className="panel-heading">
        <div>
          <h3 id="prediction-workspace-title">저장된 회귀모형으로 예측</h3>
          <p>regression.predict · 전용 워크플로</p>
        </div>
        <span className="status-pill status-ready">사용 가능 · 전용</span>
      </div>
      <div className="notice-box">
        저장된 app-created JSON 회귀모형을 선택한 뒤 대상 데이터셋의 schema와 학습 범위를
        점검합니다. 원본 predictor 값은 예측 결과와 export에 저장하지 않습니다.
      </div>
      <div className="option-grid option-grid-wide">
        <label>
          <span>Source 회귀모형</span>
          <select
            aria-label="Source 회귀모형"
            disabled={modelCatalog.isLoading}
            value={modelCatalog.selectedModelId ?? ""}
            onChange={(event) => selectModel(event.target.value || null)}
          >
            <option value="">회귀모형 선택</option>
            {modelCatalog.selectedModelId !== null && selectedCatalogModel === null ? (
              <option value={modelCatalog.selectedModelId}>
                저장된 선택 · {shortId(modelCatalog.selectedModelId)}
              </option>
            ) : null}
            {modelCatalog.catalog?.models.map((model) => (
              <option key={model.model_id} value={model.model_id}>
                {modelLabel(model)}
              </option>
            ))}
          </select>
        </label>
      </div>
      {modelCatalog.catalog?.total === 0 && modelCatalog.selectedModelId === null ? (
        <div className="notice-box">
          <p>저장된 회귀 모델이 없습니다. 먼저 회귀모형 적합을 실행하세요.</p>
          <button className="secondary-button" type="button" onClick={onNavigateToLinearModel}>
            회귀모형 적합으로 이동
          </button>
        </div>
      ) : null}
      {modelCatalog.error !== null ? (
        <CatalogError code={modelCatalog.error} onRetry={modelCatalog.onRefresh} />
      ) : null}
      {modelCatalog.catalog !== null &&
      modelCatalog.catalog.total > modelCatalog.catalog.limit ? (
        <div className="result-pagination" aria-label="회귀모형 source 목록 페이지 이동">
          <button
            disabled={modelCatalog.isLoading || !modelCatalog.catalog.has_previous}
            onClick={() =>
              modelCatalog.onPageChange(
                Math.max(0, modelCatalog.catalog!.offset - modelCatalog.catalog!.limit),
              )
            }
            type="button"
          >이전</button>
          <span>
            {modelCatalog.catalog.offset + 1}-
            {modelCatalog.catalog.offset + modelCatalog.catalog.returned} /{" "}
            {modelCatalog.catalog.total}
          </span>
          <button
            disabled={modelCatalog.isLoading || !modelCatalog.catalog.has_next}
            onClick={() =>
              modelCatalog.onPageChange(
                modelCatalog.catalog!.offset + modelCatalog.catalog!.limit,
              )
            }
            type="button"
          >다음</button>
        </div>
      ) : null}
      {retention.isCheckingAvailability ? (
        <div className="notice-box" role="status">선택한 모델의 checksum을 확인하고 있습니다.</div>
      ) : null}
      {selectedCatalogModel?.availability === "source_stale" ? (
        <div className="error-box" role="alert">
          Source dataset schema가 변경되어 이 모델은 stale입니다. 현재 schema로 회귀모형을
          다시 적합하세요.
        </div>
      ) : null}
      {selectedCatalogModel?.availability === "integrity_error" ||
      retention.availability === "integrity_error" ? (
        <div className="error-box" role="alert">
          예측용 모델 자산의 무결성을 확인할 수 없습니다. 오류 코드:{" "}
          {selectedCatalogModel?.availability_code ?? retention.availabilityError}
        </div>
      ) : null}
      {retention.availability === "unavailable_or_deleted" ? (
        <div className="notice-box" role="status">
          선택한 모델 자산을 찾을 수 없거나 삭제되었습니다. 다른 모델을 선택하세요.
        </div>
      ) : null}
      {retention.availability === null &&
      retention.availabilityError !== null &&
      !retention.isCheckingAvailability ? (
        <CatalogError
          code={retention.availabilityError}
          onRetry={retention.onRetryAvailability}
        />
      ) : null}
      {retention.manifest !== null ? (
        <div className="metadata-grid" aria-label="선택한 회귀모형 metadata">
          <span>Model ID</span><strong>{shortId(retention.manifest.model_id)}</strong>
          <span>Source analysis</span><strong>{shortId(retention.manifest.analysis_id)}</strong>
          <span>Method</span><strong>{retention.manifest.method_id} v{retention.manifest.method_version}</strong>
          <span>Source schema</span><strong>{shortId(retention.manifest.schema_hash)}</strong>
        </div>
      ) : null}
      <RegressionPredictionPanel
        currentVersion={null}
        expectedModelId={modelCatalog.selectedModelId}
        isRunningPrediction={predictionState.isRunningPrediction}
        isRunningPreflight={predictionState.isRunningPreflight}
        modelAvailable={modelReady}
        modelManifestAvailable={retention.manifest !== null}
        prediction={predictionState.prediction}
        predictionError={predictionState.predictionError}
        predictionExportState={exportState}
        predictionPreflight={predictionState.preflight}
        predictionPreflightError={predictionState.preflightError}
        predictionRowsState={rowsState}
        predictionTargetState={{ ...targetState, onSelect: selectTarget }}
        preflightButtonLabel="예측 사전점검"
        onRunPrediction={predictionState.onRunPrediction}
        onRunPreflight={predictionState.onRunPreflight}
      />
    </section>
  );
}

function modelLabel(model: RegressionModelCatalogItem): string {
  const response = model.response?.display_name ?? "metadata 확인 필요";
  const state =
    model.availability === "available"
      ? "사용 가능"
      : model.availability === "source_stale"
        ? "stale"
        : "무결성 오류";
  return `${response} · predictor ${model.predictor_count ?? "?"}개 · ${state} · ${shortId(model.model_id)}`;
}

function CatalogError({ code, onRetry }: { code: string; onRetry: () => void }) {
  return (
    <div className="error-box" role="alert">
      <p>목록 또는 자산 상태를 확인하지 못했습니다. 오류 코드: {code}</p>
      <button className="secondary-button" onClick={onRetry} type="button">다시 시도</button>
    </div>
  );
}

function validId(value: string | null): string | null {
  return value !== null && /^[0-9a-f]{8}-[0-9a-f-]{27}$/i.test(value) ? value : null;
}

function replaceWorkflowQuery(values: Record<string, string | null>) {
  const url = new URL(window.location.href);
  Object.entries(values).forEach(([key, value]) => {
    if (value === null) url.searchParams.delete(key);
    else url.searchParams.set(key, value);
  });
  window.history.replaceState({}, "", `${url.pathname}${url.search}`);
}

function shortId(value: string): string {
  return value.length <= 16 ? value : `${value.slice(0, 8)}…${value.slice(-6)}`;
}
