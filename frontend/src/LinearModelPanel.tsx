import { useState, type ReactNode } from "react";

import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionCatalogItem,
  DatasetVersionResponse,
  LinearModelResult,
  RegressionPredictionPreflightResponse,
  RegressionPredictionResponse,
  RegressionPredictionRowsPageResponse,
} from "./api";
import type { RegressionPredictionTargetState } from "./useRegressionPredictionTargetState";
import type { RegressionPredictionExportState } from "./useRegressionPredictionExportState";
import { useRegressionModelRetentionState } from "./useRegressionModelRetentionState";
import { formatBytes } from "./analysisWorkbenchUtils";

export interface LinearModelPredictionRowsState {
  error: string | null;
  isLoading: boolean;
  page: RegressionPredictionRowsPageResponse | null;
  onPageChange: (offset: number) => void;
}

interface LinearModelPanelProps {
  alpha: number;
  analysisResult: AnalysisResultEnvelope | null;
  confidenceLevel: number;
  filterValidationError: string | null;
  interactionKeys: string[];
  isRunningAnalysis: boolean;
  methodId: string;
  predictorColumnIds: string[];
  predictorColumns: DatasetColumnResponse[];
  prediction: RegressionPredictionResponse | null;
  predictionError: string | null;
  predictionExportState: RegressionPredictionExportState;
  predictionPreflight: RegressionPredictionPreflightResponse | null;
  predictionPreflightError: string | null;
  predictionRowsState: LinearModelPredictionRowsState;
  predictionTargetState: RegressionPredictionTargetState;
  quadraticColumnIds: string[];
  responseColumnId: string | null;
  responseColumns: DatasetColumnResponse[];
  result: LinearModelResult | null;
  isRunningPrediction: boolean;
  isRunningPredictionPreflight: boolean;
  version: DatasetVersionResponse | null;
  onAlphaChange: (alpha: number) => void;
  onConfidenceLevelChange: (confidenceLevel: number) => void;
  onResponseColumnChange: (columnId: string) => void;
  onRun: () => void;
  onRunPrediction: () => void;
  onRunPredictionPreflight: () => void;
  onToggleInteractionTerm: (key: string, checked: boolean) => void;
  onTogglePredictorColumn: (columnId: string, checked: boolean) => void;
  onToggleQuadraticColumn: (columnId: string, checked: boolean) => void;
}

const chartWidth = 440;
const chartHeight = 250;
const plot = {
  left: 48,
  right: 18,
  top: 18,
  bottom: 42,
};
const plotWidth = chartWidth - plot.left - plot.right;
const plotHeight = chartHeight - plot.top - plot.bottom;

export function LinearModelPanel({
  alpha,
  analysisResult,
  confidenceLevel,
  filterValidationError,
  interactionKeys,
  isRunningAnalysis,
  methodId,
  predictorColumnIds,
  predictorColumns,
  prediction,
  predictionError,
  predictionExportState,
  predictionPreflight,
  predictionPreflightError,
  predictionRowsState,
  predictionTargetState,
  quadraticColumnIds,
  responseColumnId,
  responseColumns,
  result,
  isRunningPrediction,
  isRunningPredictionPreflight,
  version,
  onAlphaChange,
  onConfidenceLevelChange,
  onResponseColumnChange,
  onRun,
  onRunPrediction,
  onRunPredictionPreflight,
  onToggleInteractionTerm,
  onTogglePredictorColumn,
  onToggleQuadraticColumn,
}: LinearModelPanelProps) {
  const modelId = result?.model_manifest?.model_id ?? null;
  const modelRetentionState = useRegressionModelRetentionState(modelId);
  const [modelDeletionConfirmed, setModelDeletionConfirmed] = useState(false);
  const modelAvailable = modelRetentionState.availability === "available";
  const modelUnavailable =
    modelRetentionState.availability === "unavailable_or_deleted";
  const modelIntegrityError = modelRetentionState.availability === "integrity_error";
  const modelAvailabilityTransientError =
    modelRetentionState.availability === null &&
    modelRetentionState.availabilityError !== null &&
    !modelRetentionState.isCheckingAvailability;
  const canRun =
    version !== null &&
    responseColumnId !== null &&
    predictorColumnIds.length > 0 &&
    !predictorColumnIds.includes(responseColumnId) &&
    alpha > 0 &&
    alpha < 1 &&
    confidenceLevel > 0 &&
    confidenceLevel < 1 &&
    filterValidationError === null;
  const topDiagnosticPoints =
    result?.diagnostics.diagnostic_points.points
      .slice()
      .sort((left, right) => {
        const leftDistance = left.cooks_distance ?? -1;
        const rightDistance = right.cooks_distance ?? -1;
        return rightDistance - leftDistance;
      })
      .slice(0, 5) ?? [];
  const selectedNumericPredictors = predictorColumns.filter(
    (column) => predictorColumnIds.includes(column.column_id) && isNumericLinearModelPredictor(column),
  );
  const interactionOptions = linearModelInteractionOptions(selectedNumericPredictors);
  const canRunPredictionPreflight =
    version !== null &&
    result?.model_manifest !== undefined &&
    predictionTargetState.selectedTargetVersionId !== null &&
    !isRunningPredictionPreflight &&
    modelAvailable;
  const canRunPrediction =
    version !== null &&
    result?.model_manifest !== undefined &&
    predictionPreflight !== null &&
    predictionPreflight.prediction_ready &&
    predictionPreflight.model_id === result.model_manifest.model_id &&
    predictionPreflight.target_dataset_version_id ===
      predictionTargetState.selectedTargetVersionId &&
    !isRunningPrediction &&
    !isRunningPredictionPreflight &&
    modelAvailable;
  const preflightErrorCount =
    predictionPreflight?.issues.filter((issue) => issue.severity === "error").length ?? 0;
  const preflightWarningCount =
    predictionPreflight?.issues.filter((issue) => issue.severity === "warning").length ?? 0;
  const activePredictionRowsPage =
    prediction !== null && predictionRowsState.page?.prediction_id === prediction.prediction_id
      ? predictionRowsState.page
      : null;
  const predictionRowsPreview =
    activePredictionRowsPage?.rows ?? prediction?.rows.slice(0, 25) ?? [];

  return (
    <section className="analysis-run-panel" aria-labelledby="linear-model-title">
      <div className="panel-heading">
        <div>
          <h3 id="linear-model-title">회귀모형 적합 실행</h3>
          <p>{methodId}</p>
        </div>
        <span className="status-pill status-ready">사용 가능</span>
      </div>
      {version === null ? (
        <div className="notice-box">데이터셋 버전 생성 후 실행할 수 있습니다.</div>
      ) : (
        <>
          <div className="notice-box">
            현재 slice는 숫자형 반응 변수 1개와 숫자형/범주형 main effect 예측변수를
            OLS로 계산합니다. 숫자형 predictor는 선택적으로 2차항과 숫자형끼리의
            상호작용 항을 추가할 수 있습니다. 범주형 예측변수는 첫 수준을 기준으로
            treatment coding하며, 관찰 데이터만으로 원인이라고 해석하지 않습니다.
          </div>
          <div className="option-grid option-grid-wide">
            <label>
              <span>반응 변수</span>
              <select
                value={responseColumnId ?? ""}
                onChange={(event) => {
                  onResponseColumnChange(event.currentTarget.value);
                }}
              >
                <option value="">선택</option>
                {responseColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
            <div className="checkbox-field">
              <span>예측변수</span>
              <div className="checkbox-list" aria-label="예측변수">
                {predictorColumns.map((column) => (
                  <label key={column.column_id}>
                    <input
                      checked={predictorColumnIds.includes(column.column_id)}
                      disabled={column.column_id === responseColumnId}
                      type="checkbox"
                      onChange={(event) => {
                        onTogglePredictorColumn(column.column_id, event.currentTarget.checked);
                      }}
                    />
                    <span>
                      {column.display_name}
                      <span className="cell-subtle">
                        {linearModelPredictorKind(column)}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
            </div>
            <label>
              <span>유의수준 alpha</span>
              <input
                max="0.5"
                min="0.001"
                step="0.001"
                type="number"
                value={alpha}
                onChange={(event) => {
                  onAlphaChange(Number(event.currentTarget.value));
                }}
              />
            </label>
            <label>
              <span>신뢰수준</span>
              <input
                max="0.999"
                min="0.5"
                step="0.001"
                type="number"
                value={confidenceLevel}
                onChange={(event) => {
                  onConfidenceLevelChange(Number(event.currentTarget.value));
                }}
              />
            </label>
          </div>
          {selectedNumericPredictors.length > 0 ? (
            <div className="option-grid option-grid-wide">
              <div className="checkbox-field">
                <span>숫자형 2차항</span>
                <div className="checkbox-list" aria-label="숫자형 2차항">
                  {selectedNumericPredictors.map((column) => (
                    <label key={column.column_id}>
                      <input
                        checked={quadraticColumnIds.includes(column.column_id)}
                        type="checkbox"
                        onChange={(event) => {
                          onToggleQuadraticColumn(
                            column.column_id,
                            event.currentTarget.checked,
                          );
                        }}
                      />
                      <span>{column.display_name}^2</span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="checkbox-field">
                <span>숫자형 상호작용</span>
                <div className="checkbox-list" aria-label="숫자형 상호작용">
                  {interactionOptions.length > 0 ? (
                    interactionOptions.map((option) => (
                      <label key={option.key}>
                        <input
                          checked={interactionKeys.includes(option.key)}
                          type="checkbox"
                          onChange={(event) => {
                            onToggleInteractionTerm(option.key, event.currentTarget.checked);
                          }}
                        />
                        <span>{option.label}</span>
                      </label>
                    ))
                  ) : (
                    <span className="empty-state">숫자형 predictor가 2개 이상 필요합니다.</span>
                  )}
                </div>
              </div>
            </div>
          ) : null}
          <button
            className="primary-button"
            disabled={isRunningAnalysis || !canRun}
            onClick={() => {
              onRun();
            }}
            type="button"
          >
            {isRunningAnalysis ? "실행 중" : "회귀모형 적합 실행"}
          </button>
          {analysisResult?.warnings.length ? (
            <ul className="warning-list" aria-label="분석 경고">
              {analysisResult.warnings.map((warning, index) => (
                <li key={`${warning.code}-${index}`}>{warning.message}</li>
              ))}
            </ul>
          ) : null}
          {result !== null ? (
            <>
              <div className="metadata-grid" aria-label="회귀모형 요약">
                <span>반응 변수</span>
                <strong>{result.response.display_name}</strong>
                <span>예측변수</span>
                <strong>{result.predictors.length.toLocaleString()}개</strong>
                <span>사용 N</span>
                <strong>
                  {result.sample.n_used.toLocaleString()} /{" "}
                  {result.sample.n_total.toLocaleString()}
                </strong>
                <span>잔차 자유도</span>
                <strong>{result.sample.df_residual.toLocaleString()}</strong>
                <span>R²</span>
                <strong>{formatModelNumber(result.fit.r_squared)}</strong>
                <span>Adjusted R²</span>
                <strong>{formatModelNumber(result.fit.adjusted_r_squared)}</strong>
                <span>Residual SE</span>
                <strong>{formatModelNumber(result.fit.residual_standard_error)}</strong>
                <span>F p-value</span>
                <strong>{formatModelNumber(result.fit.f_p_value)}</strong>
                {result.model_manifest ? (
                  <>
                    <span>Model ID</span>
                    <strong title={result.model_manifest.model_id}>
                      {shortIdentifier(result.model_manifest.model_id)}
                    </strong>
                    <span>Manifest</span>
                    <strong title={result.model_manifest.manifest_sha256}>
                      {shortIdentifier(result.model_manifest.manifest_sha256)}
                    </strong>
                  </>
                ) : null}
              </div>
              {result.model_manifest ? (
                <section className="result-section" aria-labelledby="linear-model-retention-title">
                  <div className="panel-heading">
                    <div>
                      <h4 id="linear-model-retention-title">저장 모델 관리</h4>
                      <p>
                        모델 manifest만 삭제합니다. 적합 결과와 원본 데이터는 유지되며,
                        이 모델을 사용한 예측 결과가 있으면 삭제가 차단됩니다.
                      </p>
                    </div>
                    <button
                      className="secondary-button"
                      disabled={
                        !modelAvailable ||
                        modelRetentionState.isDeleting ||
                        modelRetentionState.isLoadingPreflight ||
                        modelRetentionState.isCheckingAvailability
                      }
                      onClick={() => {
                        setModelDeletionConfirmed(false);
                        modelRetentionState.onLoadPreflight();
                      }}
                      type="button"
                    >
                      {modelRetentionState.isLoadingPreflight
                        ? "영향 확인 중"
                        : "삭제 영향 확인"}
                    </button>
                  </div>
                  {modelRetentionState.preflight ? (
                    <div className="notice-box">
                      <strong>
                        예측 참조 {modelRetentionState.preflight.counts.dependent_prediction_count.toLocaleString()}건
                      </strong>
                      <span>
                        manifest {formatBytes(
                          modelRetentionState.preflight.counts.manifest_file_bytes,
                        )}
                      </span>
                      {modelRetentionState.preflight.deletion_ready ? (
                        <label className="checkbox-field">
                          <input
                            checked={modelDeletionConfirmed}
                            type="checkbox"
                            onChange={(event) => {
                              setModelDeletionConfirmed(event.currentTarget.checked);
                            }}
                          />
                          <span>이 모델로 새 예측을 실행할 수 없게 됨을 확인했습니다.</span>
                        </label>
                      ) : (
                        <span>
                          종속 예측 결과를 먼저 삭제해야 모델을 삭제할 수 있습니다.
                        </span>
                      )}
                      <div className="button-row">
                        <button
                          className="secondary-button"
                          disabled={
                            !modelRetentionState.preflight.deletion_ready ||
                            !modelDeletionConfirmed ||
                            modelRetentionState.isDeleting
                          }
                          onClick={() => {
                            modelRetentionState.onDelete(modelRetentionState.preflight!);
                          }}
                          type="button"
                        >
                          {modelRetentionState.isDeleting ? "삭제 중" : "모델 삭제"}
                        </button>
                        <button
                          className="secondary-button"
                          disabled={modelRetentionState.isDeleting}
                          onClick={() => {
                            setModelDeletionConfirmed(false);
                            modelRetentionState.onClear();
                          }}
                          type="button"
                        >
                          취소
                        </button>
                      </div>
                    </div>
                  ) : null}
                  {modelUnavailable ? (
                    <div className="notice-box" role="status">
                      모형 적합 결과는 보존되어 있지만 예측용 모델 자산은 사용할 수
                      없습니다.
                    </div>
                  ) : null}
                  {modelIntegrityError ? (
                    <div className="error-box" role="alert">
                      예측용 모델 자산의 무결성을 확인할 수 없습니다. 모형 적합 결과만
                      표시합니다. 오류 코드: {modelRetentionState.availabilityError}
                    </div>
                  ) : null}
                  {modelRetentionState.isCheckingAvailability ? (
                    <div className="notice-box" role="status">
                      예측용 모델 자산의 사용 가능 상태를 확인하고 있습니다.
                    </div>
                  ) : null}
                  {modelAvailabilityTransientError ? (
                    <div className="error-box" role="alert">
                      <p>
                        예측용 모델 자산의 상태를 확인하지 못했습니다. 네트워크/API 상태를
                        확인한 뒤 다시 시도하세요. 오류 코드: {modelRetentionState.availabilityError}
                      </p>
                      <button
                        className="secondary-button"
                        onClick={modelRetentionState.onRetryAvailability}
                        type="button"
                      >
                        모델 상태 다시 확인
                      </button>
                    </div>
                  ) : null}
                  {modelRetentionState.error ? (
                    <div className="error-box" role="alert">
                      오류 코드: {modelRetentionState.error}
                    </div>
                  ) : null}
                </section>
              ) : null}
              <section
                className="result-section"
                aria-labelledby="linear-model-prediction-preflight-title"
              >
                <div className="panel-heading">
                  <div>
                    <h4 id="linear-model-prediction-preflight-title">
                      예측 사전점검
                    </h4>
                    <p>선택한 데이터셋 버전을 저장된 모델 manifest와 대조합니다.</p>
                  </div>
                  <div className="button-row">
                    <button
                      className="secondary-button"
                      disabled={!canRunPredictionPreflight}
                      onClick={() => {
                        onRunPredictionPreflight();
                      }}
                      type="button"
                    >
                      {isRunningPredictionPreflight ? "점검 중" : "사전점검 실행"}
                    </button>
                    <button
                      className="primary-button"
                      disabled={!canRunPrediction}
                      onClick={() => {
                        onRunPrediction();
                      }}
                      type="button"
                    >
                      {isRunningPrediction ? "예측 중" : "예측 실행"}
                    </button>
                  </div>
                </div>
                {result.model_manifest === undefined ? (
                  <div className="notice-box">저장된 model manifest가 없는 결과입니다.</div>
                ) : null}
                <div className="option-grid option-grid-wide">
                  <label>
                    <span>예측 대상 데이터셋 버전</span>
                    <select
                      aria-label="예측 대상 데이터셋 버전"
                      disabled={
                        predictionTargetState.selectedTargetVersionId === null ||
                        !modelAvailable ||
                        isRunningPredictionPreflight ||
                        isRunningPrediction ||
                        predictionExportState.isCreating ||
                        predictionExportState.isDownloading
                      }
                      value={predictionTargetState.selectedTargetVersionId ?? ""}
                      onChange={(event) => {
                        predictionTargetState.onSelect(event.target.value);
                      }}
                    >
                      {version !== null ? (
                        <option value={version.version_id}>
                          현재 데이터셋 · v{version.version_number} · {version.row_count.toLocaleString()}
                          행 × {version.column_count.toLocaleString()}열
                        </option>
                      ) : null}
                      {predictionTargetState.selectedTarget !== null &&
                      predictionTargetState.selectedTarget.version_id !== version?.version_id &&
                      !predictionTargetState.catalog?.versions.some(
                        (candidate) =>
                          candidate.version_id ===
                          predictionTargetState.selectedTarget?.version_id,
                      ) ? (
                        <option value={predictionTargetState.selectedTarget.version_id}>
                          {predictionTargetLabel(predictionTargetState.selectedTarget)}
                        </option>
                      ) : null}
                      {predictionTargetState.catalog?.versions
                        .filter((candidate) => candidate.version_id !== version?.version_id)
                        .map((candidate) => (
                          <option key={candidate.version_id} value={candidate.version_id}>
                            {predictionTargetLabel(candidate)}
                          </option>
                        ))}
                    </select>
                  </label>
                </div>
                {predictionTargetState.error !== null ? (
                  <div className="error-box" role="alert">
                    데이터셋 버전 목록 조회 실패: {predictionTargetState.error}
                  </div>
                ) : null}
                {predictionTargetState.catalog !== null &&
                predictionTargetState.catalog.total > predictionTargetState.catalog.limit ? (
                  <div className="result-pagination" aria-label="예측 대상 데이터셋 목록 페이지 이동">
                    <button
                      type="button"
                      disabled={
                        predictionTargetState.isLoading ||
                        !predictionTargetState.catalog.has_previous
                      }
                      onClick={() => {
                        predictionTargetState.onPageChange(
                          Math.max(
                            0,
                            predictionTargetState.catalog!.offset -
                              predictionTargetState.catalog!.limit,
                          ),
                        );
                      }}
                    >
                      이전
                    </button>
                    <span>
                      {predictionTargetState.catalog.offset + 1}-
                      {predictionTargetState.catalog.offset +
                        predictionTargetState.catalog.returned} / {predictionTargetState.catalog.total}
                    </span>
                    <button
                      type="button"
                      disabled={
                        predictionTargetState.isLoading || !predictionTargetState.catalog.has_next
                      }
                      onClick={() => {
                        predictionTargetState.onPageChange(
                          predictionTargetState.catalog!.offset +
                            predictionTargetState.catalog!.limit,
                        );
                      }}
                    >
                      다음
                    </button>
                  </div>
                ) : null}
                <div className="notice-box">
                  예측은 저장된 OLS 모델이 선택한 데이터셋 버전에 적용한 추정값입니다.
                  원인·효과나 확정값으로 해석하지 말고, 학습 범위 밖 값과 OLS 가정을 함께
                  확인해야 합니다. source dataset schema가 바뀌어 모델이 stale이면 현재
                  schema로 회귀모형을 다시 적합해야 합니다.
                </div>
                {predictionPreflightError !== null ? (
                  <div className="error-box" role="alert">
                    오류 코드: {predictionPreflightError}
                  </div>
                ) : null}
                {predictionError !== null ? (
                  <div className="error-box" role="alert">
                    오류 코드: {predictionError}
                  </div>
                ) : null}
                {predictionPreflight !== null ? (
                  <>
                    <div className="metadata-grid" aria-label="예측 사전점검 요약">
                      <span>상태</span>
                      <strong>
                        {predictionPreflight.prediction_ready ? "예측 준비 가능" : "확인 필요"}
                      </strong>
                      <span>대상 행</span>
                      <strong>
                        {predictionPreflight.row_count_usable.toLocaleString()} /{" "}
                        {predictionPreflight.row_count_total.toLocaleString()}
                      </strong>
                      <span>Schema hash</span>
                      <strong>
                        {predictionPreflight.schema_hash_match ? "일치" : "다름"}
                      </strong>
                      <span>Source model</span>
                      <strong>
                        {predictionPreflight.source_analysis_stale === true
                          ? "stale · 재적합 필요"
                          : predictionPreflight.source_analysis_stale === false
                            ? "fresh"
                            : "검증 불가"}
                      </strong>
                      <span>Source schema</span>
                      <strong>
                        {predictionPreflight.source_schema_hash_current === null
                          ? "검증 불가"
                          : predictionPreflight.source_schema_hash_current ===
                              predictionPreflight.source_schema_hash
                            ? "적합 시점과 일치"
                            : "변경됨 · 재적합 필요"}
                      </strong>
                      <span>문제</span>
                      <strong>
                        오류 {preflightErrorCount.toLocaleString()}개 · 경고{" "}
                        {preflightWarningCount.toLocaleString()}개
                      </strong>
                    </div>
                    {predictionPreflight.issues.length > 0 ? (
                      <ul className="warning-list" aria-label="예측 사전점검 문제">
                        {predictionPreflight.issues.map((issue, index) => (
                          <li key={`${issue.code}-${index}`}>
                            [{issue.severity}] {issue.message}
                            <span className="cell-subtle">
                              {issue.display_name ?? issue.code}
                              {issue.count !== null
                                ? ` · ${issue.count.toLocaleString()}건`
                                : ""}
                            </span>
                          </li>
                        ))}
                      </ul>
                    ) : null}
                    <div className="table-wrap">
                      <table className="result-table">
                        <thead>
                          <tr>
                            <th>컬럼</th>
                            <th>종류</th>
                            <th>매핑</th>
                            <th>상태</th>
                            <th>대상 컬럼</th>
                          </tr>
                        </thead>
                        <tbody>
                          {predictionPreflight.required_columns.map((mapping) => (
                            <tr key={mapping.source_column_id}>
                              <td>{mapping.display_name}</td>
                              <td>{predictionPredictorKindLabel(mapping.predictor_kind)}</td>
                              <td>{predictionMatchTypeLabel(mapping.match_type)}</td>
                              <td>{predictionStatusLabel(mapping.status)}</td>
                              <td>{shortIdentifier(mapping.target_column_id ?? "missing")}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {predictionPreflight.numeric_checks.length > 0 ? (
                      <div className="table-wrap">
                        <table className="result-table">
                          <thead>
                            <tr>
                              <th>숫자형 컬럼</th>
                              <th>유효</th>
                              <th>결측</th>
                              <th>비숫자</th>
                              <th>학습범위 아래</th>
                              <th>학습범위 위</th>
                            </tr>
                          </thead>
                          <tbody>
                            {predictionPreflight.numeric_checks.map((check) => (
                              <tr key={check.source_column_id}>
                                <td>{check.display_name}</td>
                                <td>{check.n_valid.toLocaleString()}</td>
                                <td>{check.n_missing.toLocaleString()}</td>
                                <td>{check.n_non_numeric.toLocaleString()}</td>
                                <td>{check.n_below_training_range.toLocaleString()}</td>
                                <td>{check.n_above_training_range.toLocaleString()}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : null}
                    {predictionPreflight.categorical_checks.length > 0 ? (
                      <div className="table-wrap">
                        <table className="result-table">
                          <thead>
                            <tr>
                              <th>범주형 컬럼</th>
                              <th>학습 level</th>
                              <th>유효</th>
                              <th>결측</th>
                              <th>새 level</th>
                            </tr>
                          </thead>
                          <tbody>
                            {predictionPreflight.categorical_checks.map((check) => (
                              <tr key={check.source_column_id}>
                                <td>{check.display_name}</td>
                                <td>{check.training_level_count.toLocaleString()}</td>
                                <td>{check.n_valid.toLocaleString()}</td>
                                <td>{check.n_missing.toLocaleString()}</td>
                                <td>{check.n_unseen_level.toLocaleString()}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : null}
                  </>
                ) : null}
                {prediction !== null ? (
                  <>
                    <div className="metadata-grid" aria-label="예측 결과 요약">
                      <span>Prediction ID</span>
                      <strong title={prediction.prediction_id}>
                        {shortIdentifier(prediction.prediction_id)}
                      </strong>
                      <span>예측 행</span>
                      <strong>
                        {prediction.row_count_predicted.toLocaleString()} /{" "}
                        {prediction.row_count_total.toLocaleString()}
                      </strong>
                      <span>제외 행</span>
                      <strong>{prediction.row_count_excluded.toLocaleString()}개</strong>
                      <span>응답 생략</span>
                      <strong>{prediction.row_count_omitted.toLocaleString()}개</strong>
                      <span>신뢰수준</span>
                      <strong>{formatPercent(prediction.confidence_level)}</strong>
                      <span>Inline rows</span>
                      <strong>
                        {prediction.rows.length.toLocaleString()} /{" "}
                        {prediction.row_limit.toLocaleString()}
                      </strong>
                    </div>
                    <div className="button-row" aria-label="전체 예측 CSV export">
                      <button
                        className="secondary-button"
                        disabled={
                          !modelAvailable ||
                          predictionExportState.isCreating ||
                          predictionExportState.isDownloading
                        }
                        onClick={predictionExportState.onCreate}
                        type="button"
                      >
                        {predictionExportState.isCreating
                          ? "전체 예측 CSV 생성 중"
                          : "전체 예측 CSV 생성"}
                      </button>
                      {predictionExportState.csvExport !== null ? (
                        <>
                          <span className="cell-subtle">
                            {predictionExportState.csvExport.row_count.toLocaleString()}행 · sha256:
                            {shortIdentifier(predictionExportState.csvExport.sha256)}
                          </span>
                          <button
                            className="secondary-button"
                            disabled={
                              !modelAvailable || predictionExportState.isDownloading
                            }
                            onClick={predictionExportState.onDownload}
                            type="button"
                          >
                            {predictionExportState.isDownloading
                              ? "CSV 다운로드 중"
                              : "전체 예측 CSV 다운로드"}
                          </button>
                        </>
                      ) : null}
                    </div>
                    {predictionExportState.error !== null ? (
                      <div className="error-box" role="alert">
                        예측 CSV export 실패: {predictionExportState.error}
                      </div>
                    ) : null}
                    {prediction.warnings.length > 0 ? (
                      <ul className="warning-list" aria-label="예측 경고">
                        {prediction.warnings.map((warning, index) => (
                          <li key={`${warning.code}-${index}`}>
                            [{warning.severity}] {warning.message}
                            <span className="cell-subtle">
                              {warning.count !== null
                                ? `${warning.code} · ${warning.count.toLocaleString()}건`
                                : warning.code}
                            </span>
                          </li>
                        ))}
                      </ul>
                    ) : null}
                    <div className="result-section" aria-label="예측 구간 차트 결과">
                      <div className="panel-heading">
                        <div>
                          <h4>예측 구간 차트</h4>
                          <p>Predicted mean · mean CI · prediction interval</p>
                        </div>
                      </div>
                      <div className="chart-grid chart-grid-single">
                        <ChartPanel title="예측 평균과 구간">
                          {renderPredictionIntervalChart(predictionRowsPreview)}
                        </ChartPanel>
                      </div>
                    </div>
                    <div className="table-wrap">
                      <table className="result-table">
                        <thead>
                          <tr>
                            <th>행 index</th>
                            <th>예측 평균</th>
                            <th>Mean CI</th>
                            <th>Prediction interval</th>
                            <th>경고</th>
                          </tr>
                        </thead>
                        <tbody>
                          {predictionRowsPreview.map((row) => (
                            <tr key={row.row_index}>
                              <td>{row.row_index.toLocaleString()}</td>
                              <td>{formatModelNumber(row.predicted_mean)}</td>
                              <td>{formatPredictionInterval(row.mean_confidence_interval)}</td>
                              <td>{formatPredictionInterval(row.prediction_interval)}</td>
                              <td>{row.warnings.length > 0 ? row.warnings.join(", ") : "없음"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {predictionRowsState.error !== null ? (
                      <div className="error-box" role="alert">
                        예측 행 조회 실패: {predictionRowsState.error}
                      </div>
                    ) : null}
                    {activePredictionRowsPage !== null ? (
                      <div className="result-pagination" aria-label="예측 행 페이지 이동">
                        <button
                          type="button"
                          disabled={
                            predictionRowsState.isLoading ||
                            !activePredictionRowsPage.has_previous
                          }
                          onClick={() => {
                            predictionRowsState.onPageChange(
                              Math.max(
                                0,
                                activePredictionRowsPage.offset - activePredictionRowsPage.limit,
                              ),
                            );
                          }}
                        >
                          이전
                        </button>
                        <span>
                          {activePredictionRowsPage.total === 0
                            ? "0 / 0"
                            : `${(
                                activePredictionRowsPage.offset + 1
                              ).toLocaleString()}-${(
                                activePredictionRowsPage.offset +
                                activePredictionRowsPage.returned
                              ).toLocaleString()} / ${activePredictionRowsPage.total.toLocaleString()}`}
                        </span>
                        <button
                          type="button"
                          disabled={
                            predictionRowsState.isLoading || !activePredictionRowsPage.has_next
                          }
                          onClick={() => {
                            predictionRowsState.onPageChange(
                              activePredictionRowsPage.offset + activePredictionRowsPage.limit,
                            );
                          }}
                        >
                          다음
                        </button>
                      </div>
                    ) : prediction.rows.length > predictionRowsPreview.length ? (
                      <p className="cell-subtle">
                        화면에는 처음 {predictionRowsPreview.length.toLocaleString()}개 예측 행만
                        표시합니다.
                      </p>
                    ) : null}
                  </>
                ) : null}
              </section>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>항</th>
                      <th>추정치</th>
                      <th>표준오차</th>
                      <th>CI</th>
                      <th>t</th>
                      <th>p-value</th>
                      <th>VIF</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.coefficients.map((coefficient) => (
                      <tr key={coefficient.term}>
                        <td>
                          {coefficient.term}
                          <span className="cell-subtle">{coefficient.term_kind}</span>
                        </td>
                        <td>{formatModelNumber(coefficient.estimate)}</td>
                        <td>{formatModelNumber(coefficient.standard_error)}</td>
                        <td>
                          {formatPercent(coefficient.confidence_interval.level)} CI{" "}
                          {formatModelNumber(coefficient.confidence_interval.lower)} -{" "}
                          {formatModelNumber(coefficient.confidence_interval.upper)}
                        </td>
                        <td>{formatModelNumber(coefficient.statistic)}</td>
                        <td>{formatModelNumber(coefficient.p_value)}</td>
                        <td>{formatModelNumber(coefficient.vif)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="metadata-grid" aria-label="회귀 진단 요약">
                <span>Condition number</span>
                <strong>{formatModelNumber(result.diagnostics.condition_number)}</strong>
                <span>최대 VIF</span>
                <strong>{formatModelNumber(result.diagnostics.max_vif)}</strong>
                <span>최대 표준화 잔차</span>
                <strong>
                  {formatModelNumber(result.diagnostics.residual_summary.max_abs_standardized)}
                </strong>
                <span>큰 잔차 후보</span>
                <strong>
                  {result.diagnostics.residual_summary.large_standardized_count.toLocaleString()}개
                </strong>
                <span>최대 leverage</span>
                <strong>{formatModelNumber(result.diagnostics.leverage.max)}</strong>
                <span>High leverage</span>
                <strong>{result.diagnostics.leverage.high_count.toLocaleString()}개</strong>
                <span>최대 Cook&apos;s D</span>
                <strong>{formatModelNumber(result.diagnostics.influence.cooks_distance_max)}</strong>
                <span>Influential 후보</span>
                <strong>
                  {result.diagnostics.influence.high_cooks_distance_count.toLocaleString()}개
                </strong>
                <span>Rank</span>
                <strong>{result.diagnostics.rank.toLocaleString()}</strong>
                <span>파라미터 수</span>
                <strong>{result.diagnostics.parameter_count.toLocaleString()}</strong>
              </div>
              <div className="result-section" aria-label="회귀 진단 차트 결과">
                <div className="panel-heading">
                  <div>
                    <h4>회귀 진단 차트</h4>
                    <p>
                      {result.diagnostics.diagnostic_points.points_included.toLocaleString()} /{" "}
                      {result.diagnostics.diagnostic_points.point_limit.toLocaleString()} diagnostic
                      points
                      {result.diagnostics.diagnostic_points.truncated ? " · capped" : ""}
                    </p>
                  </div>
                </div>
                <div className="chart-grid">
                  <ChartPanel title="Residuals vs Fitted">
                    {renderResidualFittedChart(result)}
                  </ChartPanel>
                  <ChartPanel title="Leverage vs Cook's D">
                    {renderInfluenceChart(result)}
                  </ChartPanel>
                </div>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>행 index</th>
                      <th>Fitted</th>
                      <th>Residual</th>
                      <th>Std residual</th>
                      <th>Leverage</th>
                      <th>Cook&apos;s D</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topDiagnosticPoints.map((point) => (
                      <tr key={point.row_index}>
                        <td>{point.row_index.toLocaleString()}</td>
                        <td>{formatModelNumber(point.fitted)}</td>
                        <td>{formatModelNumber(point.residual)}</td>
                        <td>{formatModelNumber(point.standardized_residual)}</td>
                        <td>{formatModelNumber(point.leverage)}</td>
                        <td>{formatModelNumber(point.cooks_distance)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : null}
        </>
      )}
    </section>
  );
}

function ChartPanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="chart-panel">
      <div className="chart-panel-title">{title}</div>
      {children}
    </div>
  );
}

function renderResidualFittedChart(result: LinearModelResult) {
  const points = result.diagnostics.diagnostic_points.points.filter(
    (point) => Number.isFinite(point.fitted) && Number.isFinite(point.residual),
  );
  if (points.length === 0) {
    return <EmptyChart label="진단 point 없음" />;
  }

  const xRange = paddedRange(points.map((point) => point.fitted));
  const yRange = paddedRange([...points.map((point) => point.residual), 0]);
  const zeroY = scale(0, yRange.min, yRange.max, plot.top + plotHeight, plot.top);
  return (
    <svg
      aria-label="linear model residuals versus fitted chart"
      className="chart-svg chart-svg-wide"
      role="img"
      viewBox={`0 0 ${chartWidth} ${chartHeight}`}
    >
      {chartAxes()}
      <line
        className="reference-line residual-zero-line"
        x1={plot.left}
        x2={plot.left + plotWidth}
        y1={zeroY}
        y2={zeroY}
      />
      {points.map((point) => (
        <circle
          key={point.row_index}
          className="diagnostic-point"
          cx={scale(point.fitted, xRange.min, xRange.max, plot.left, plot.left + plotWidth)}
          cy={scale(point.residual, yRange.min, yRange.max, plot.top + plotHeight, plot.top)}
          r="3"
        />
      ))}
      {chartTickLabels(formatModelNumber(xRange.min), formatModelNumber(xRange.max))}
      <text className="chart-axis-label" x={plot.left - 10} y={plot.top + 8}>
        {formatModelNumber(yRange.max)}
      </text>
    </svg>
  );
}

function renderInfluenceChart(result: LinearModelResult) {
  const points = result.diagnostics.diagnostic_points.points.filter(
    (point) =>
      Number.isFinite(point.leverage) &&
      point.cooks_distance !== null &&
      Number.isFinite(point.cooks_distance),
  );
  if (points.length === 0) {
    return <EmptyChart label="영향점 point 없음" />;
  }

  const xRange = paddedRange([
    ...points.map((point) => point.leverage),
    result.diagnostics.leverage.threshold,
  ]);
  const yRange = paddedRange([
    ...points.map((point) => point.cooks_distance ?? 0),
    result.diagnostics.influence.cooks_distance_threshold,
  ]);
  const leverageThresholdX = scale(
    result.diagnostics.leverage.threshold,
    xRange.min,
    xRange.max,
    plot.left,
    plot.left + plotWidth,
  );
  const cooksThresholdY = scale(
    result.diagnostics.influence.cooks_distance_threshold,
    yRange.min,
    yRange.max,
    plot.top + plotHeight,
    plot.top,
  );
  return (
    <svg
      aria-label="linear model leverage versus Cook's D chart"
      className="chart-svg chart-svg-wide"
      role="img"
      viewBox={`0 0 ${chartWidth} ${chartHeight}`}
    >
      {chartAxes()}
      <line
        className="reference-line"
        x1={leverageThresholdX}
        x2={leverageThresholdX}
        y1={plot.top}
        y2={plot.top + plotHeight}
      />
      <line
        className="reference-line"
        x1={plot.left}
        x2={plot.left + plotWidth}
        y1={cooksThresholdY}
        y2={cooksThresholdY}
      />
      {points.map((point) => (
        <circle
          key={point.row_index}
          className="influence-point"
          cx={scale(point.leverage, xRange.min, xRange.max, plot.left, plot.left + plotWidth)}
          cy={scale(
            point.cooks_distance ?? 0,
            yRange.min,
            yRange.max,
            plot.top + plotHeight,
            plot.top,
          )}
          r="3"
        />
      ))}
      {chartTickLabels(formatModelNumber(xRange.min), formatModelNumber(xRange.max))}
      <text className="chart-axis-label" x={plot.left - 10} y={plot.top + 8}>
        {formatModelNumber(yRange.max)}
      </text>
    </svg>
  );
}

function renderPredictionIntervalChart(rows: RegressionPredictionResponse["rows"]) {
  const rowsWithIntervals = rows.filter(
    (row) =>
      Number.isFinite(row.predicted_mean) &&
      row.mean_confidence_interval !== null &&
      row.prediction_interval !== null,
  );
  if (rowsWithIntervals.length === 0) {
    return <EmptyChart label="예측 구간 없음" />;
  }

  const yRange = paddedRange(
    rowsWithIntervals.flatMap((row) => [
      row.predicted_mean,
      row.mean_confidence_interval?.lower ?? row.predicted_mean,
      row.mean_confidence_interval?.upper ?? row.predicted_mean,
      row.prediction_interval?.lower ?? row.predicted_mean,
      row.prediction_interval?.upper ?? row.predicted_mean,
    ]),
  );
  return (
    <svg
      aria-label="regression prediction interval chart"
      className="chart-svg chart-svg-wide"
      role="img"
      viewBox={`0 0 ${chartWidth} ${chartHeight}`}
    >
      {chartAxes()}
      {rowsWithIntervals.map((row, index) => {
        const x = scale(index, 0, Math.max(1, rowsWithIntervals.length - 1), plot.left, plot.left + plotWidth);
        const predictionInterval = row.prediction_interval;
        const meanInterval = row.mean_confidence_interval;
        return (
          <g key={row.row_index}>
            {predictionInterval !== null ? (
              <line
                className="prediction-interval-line"
                x1={x}
                x2={x}
                y1={scale(predictionInterval.lower, yRange.min, yRange.max, plot.top + plotHeight, plot.top)}
                y2={scale(predictionInterval.upper, yRange.min, yRange.max, plot.top + plotHeight, plot.top)}
              />
            ) : null}
            {meanInterval !== null ? (
              <line
                className="prediction-ci-line"
                x1={x}
                x2={x}
                y1={scale(meanInterval.lower, yRange.min, yRange.max, plot.top + plotHeight, plot.top)}
                y2={scale(meanInterval.upper, yRange.min, yRange.max, plot.top + plotHeight, plot.top)}
              />
            ) : null}
            <circle
              className="prediction-mean-point"
              cx={x}
              cy={scale(row.predicted_mean, yRange.min, yRange.max, plot.top + plotHeight, plot.top)}
              r="3"
            />
          </g>
        );
      })}
      {chartTickLabels("1", rowsWithIntervals.length.toLocaleString())}
      <text className="chart-axis-label" x={plot.left - 10} y={plot.top + 8}>
        {formatModelNumber(yRange.max)}
      </text>
    </svg>
  );
}

function EmptyChart({ label }: { label: string }) {
  return (
    <svg
      aria-label={label}
      className="chart-svg chart-svg-empty"
      role="img"
      viewBox={`0 0 ${chartWidth} ${chartHeight}`}
    >
      <rect className="empty-chart-bg" height={plotHeight} width={plotWidth} x={plot.left} y={plot.top} />
      <text className="empty-chart-text" x={chartWidth / 2} y={chartHeight / 2}>
        {label}
      </text>
    </svg>
  );
}

function chartAxes() {
  return (
    <>
      <line
        className="chart-axis"
        x1={plot.left}
        x2={plot.left}
        y1={plot.top}
        y2={plot.top + plotHeight}
      />
      <line
        className="chart-axis"
        x1={plot.left}
        x2={plot.left + plotWidth}
        y1={plot.top + plotHeight}
        y2={plot.top + plotHeight}
      />
      <line
        className="chart-grid-line"
        x1={plot.left}
        x2={plot.left + plotWidth}
        y1={plot.top}
        y2={plot.top}
      />
    </>
  );
}

function chartTickLabels(leftLabel: string, rightLabel: string) {
  return (
    <>
      <text className="chart-axis-label" x={plot.left} y={chartHeight - 12}>
        {leftLabel}
      </text>
      <text className="chart-axis-label chart-axis-label-end" x={plot.left + plotWidth} y={chartHeight - 12}>
        {rightLabel}
      </text>
    </>
  );
}

function paddedRange(values: number[]): { min: number; max: number } {
  const finiteValues = values.filter((value) => Number.isFinite(value));
  if (finiteValues.length === 0) {
    return { min: 0, max: 1 };
  }
  const min = Math.min(...finiteValues);
  const max = Math.max(...finiteValues);
  if (min === max) {
    const padding = Math.max(1, Math.abs(min) * 0.1);
    return { min: min - padding, max: max + padding };
  }
  const padding = (max - min) * 0.04;
  return { min: min - padding, max: max + padding };
}

function scale(
  value: number,
  domainMin: number,
  domainMax: number,
  rangeMin: number,
  rangeMax: number,
): number {
  if (domainMin === domainMax) {
    return (rangeMin + rangeMax) / 2;
  }
  return rangeMin + ((value - domainMin) / (domainMax - domainMin)) * (rangeMax - rangeMin);
}

function formatPercent(value: number): string {
  return `${Math.round(value * 1000) / 10}%`;
}

function formatModelNumber(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "NA";
  }
  return value.toLocaleString("ko-KR", {
    maximumFractionDigits: 6,
    minimumFractionDigits: 0,
  });
}

function formatPredictionInterval(
  interval: RegressionPredictionResponse["rows"][number]["prediction_interval"],
): string {
  if (interval === null) {
    return "NA";
  }
  return `${formatPercent(interval.level)} ${formatModelNumber(interval.lower)} - ${formatModelNumber(
    interval.upper,
  )}`;
}

function predictionTargetLabel(target: DatasetVersionCatalogItem): string {
  return `${target.original_filename} · v${target.version_number} · ${target.row_count.toLocaleString()}행 × ${target.column_count.toLocaleString()}열 · ${shortIdentifier(target.version_id)}`;
}

function shortIdentifier(value: string): string {
  if (value.length <= 16) {
    return value;
  }
  return `${value.slice(0, 12)}...`;
}

function predictionPredictorKindLabel(kind: "numeric" | "categorical"): string {
  return kind === "numeric" ? "숫자형" : "범주형";
}

function predictionMatchTypeLabel(
  matchType: "column_id" | "display_name" | "missing" | "ambiguous",
): string {
  if (matchType === "column_id") {
    return "컬럼 ID";
  }
  if (matchType === "display_name") {
    return "표시명";
  }
  if (matchType === "ambiguous") {
    return "표시명 중복";
  }
  return "없음";
}

function predictionStatusLabel(status: "ok" | "warning" | "error"): string {
  if (status === "ok") {
    return "정상";
  }
  if (status === "warning") {
    return "경고";
  }
  return "오류";
}

function linearModelPredictorKind(column: DatasetColumnResponse): string {
  if (
    column.data_type === "text" ||
    column.data_type === "boolean" ||
    column.role === "factor" ||
    column.measurement_level === "nominal" ||
    column.measurement_level === "binary" ||
    column.measurement_level === "ordinal"
  ) {
    return "범주형";
  }
  return "숫자형";
}

function isNumericLinearModelPredictor(column: DatasetColumnResponse): boolean {
  return (
    (column.data_type === "integer" || column.data_type === "decimal") &&
    column.role !== "factor" &&
    column.measurement_level !== "nominal" &&
    column.measurement_level !== "binary" &&
    column.measurement_level !== "ordinal"
  );
}

function linearModelInteractionOptions(columns: DatasetColumnResponse[]): Array<{
  key: string;
  label: string;
}> {
  const options: Array<{ key: string; label: string }> = [];
  for (let leftIndex = 0; leftIndex < columns.length; leftIndex += 1) {
    for (let rightIndex = leftIndex + 1; rightIndex < columns.length; rightIndex += 1) {
      const left = columns[leftIndex];
      const right = columns[rightIndex];
      options.push({
        key: linearModelInteractionKey(left.column_id, right.column_id),
        label: `${left.display_name}:${right.display_name}`,
      });
    }
  }
  return options;
}

function linearModelInteractionKey(leftColumnId: string, rightColumnId: string): string {
  return [leftColumnId, rightColumnId].sort().join("::");
}
