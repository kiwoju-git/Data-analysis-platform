import { useState, type ReactNode } from "react";

import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  LinearModelResult,
  RegressionPredictionPreflightResponse,
  RegressionPredictionResponse,
} from "./api";
import type { RegressionPredictionTargetState } from "./useRegressionPredictionTargetState";
import type { RegressionPredictionExportState } from "./useRegressionPredictionExportState";
import { useRegressionModelRetentionState } from "./useRegressionModelRetentionState";
import { formatBytes } from "./analysisWorkbenchUtils";
import {
  RegressionPredictionPanel,
  type RegressionPredictionRowsState,
} from "./RegressionPredictionPanel";

export type LinearModelPredictionRowsState = RegressionPredictionRowsState;

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
              <RegressionPredictionPanel
                currentVersion={version}
                expectedModelId={result.model_manifest?.model_id ?? null}
                isRunningPrediction={isRunningPrediction}
                isRunningPreflight={isRunningPredictionPreflight}
                modelAvailable={modelAvailable}
                modelManifestAvailable={result.model_manifest !== undefined}
                prediction={prediction}
                predictionError={predictionError}
                predictionExportState={predictionExportState}
                predictionPreflight={predictionPreflight}
                predictionPreflightError={predictionPreflightError}
                predictionRowsState={predictionRowsState}
                predictionTargetState={predictionTargetState}
                onRunPrediction={onRunPrediction}
                onRunPreflight={onRunPredictionPreflight}
              />
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

function shortIdentifier(value: string): string {
  if (value.length <= 16) {
    return value;
  }
  return `${value.slice(0, 12)}...`;
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
