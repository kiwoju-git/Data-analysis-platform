import { useEffect, useState } from "react";

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
import { measurementLevelLabel, roleLabel } from "./datasetDisplay";
import {
  RegressionPredictionPanel,
  type RegressionPredictionRowsState,
} from "./RegressionPredictionPanel";
import { LinearModelFitResults } from "./LinearModelFitResults";
import { RegressionResponseOptimizerPanel } from "./RegressionResponseOptimizerPanel";
import { updateRegressionModelMetadata } from "./api/regression";
import {
  isNumericLinearModelPredictor,
  linearModelPredictorKind as predictorKind,
} from "./linearModelColumns";

export type LinearModelPredictionRowsState = RegressionPredictionRowsState;

interface LinearModelPanelProps {
  alpha: number;
  analysisResult: AnalysisResultEnvelope | null;
  confidenceLevel: number;
  filterValidationError: string | null;
  interactionKeys: string[];
  modelSelectionMethod: "none" | "backward_elimination";
  alphaToRemove: number;
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
  onAlphaToRemoveChange: (alpha: number) => void;
  onModelSelectionMethodChange: (method: "none" | "backward_elimination") => void;
  onResponseColumnChange: (columnId: string) => void;
  onRun: () => void;
  onRunPrediction: () => void;
  onRunPredictionPreflight: () => void;
  onToggleInteractionTerm: (key: string, checked: boolean) => void;
  onTogglePredictorColumn: (columnId: string, checked: boolean) => void;
  onToggleQuadraticColumn: (columnId: string, checked: boolean) => void;
}

export function LinearModelPanel({
  alpha,
  analysisResult,
  confidenceLevel,
  filterValidationError,
  interactionKeys,
  modelSelectionMethod,
  alphaToRemove,
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
  onAlphaToRemoveChange,
  onModelSelectionMethodChange,
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
  const [modelName, setModelName] = useState("");
  const [modelNameError, setModelNameError] = useState<string | null>(null);
  const [isSavingModelName, setIsSavingModelName] = useState(false);
  const modelAvailable = modelRetentionState.availability === "available";
  const modelUnavailable =
    modelRetentionState.availability === "unavailable_or_deleted";
  const modelIntegrityError = modelRetentionState.availability === "integrity_error";

  useEffect(() => {
    setModelName("");
    setModelNameError(null);
  }, [modelId]);
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
    (modelSelectionMethod === "none" || (alphaToRemove > 0 && alphaToRemove < 1)) &&
    filterValidationError === null;
  const selectedNumericPredictors = predictorColumns.filter(
    (column) => predictorColumnIds.includes(column.column_id) && isNumericLinearModelPredictor(column),
  );
  const interactionOptions = linearModelInteractionOptions(selectedNumericPredictors);
  return (
    <section className="analysis-run-panel" data-analysis-execution={methodId}>
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
          <div className="option-grid option-grid-wide">
            <label>
              <span>모형 선택 방법</span>
              <select
                value={modelSelectionMethod}
                onChange={(event) =>
                  onModelSelectionMethodChange(
                    event.currentTarget.value as "none" | "backward_elimination",
                  )
                }
              >
                <option value="none">지정한 전체 모형 유지</option>
                <option value="backward_elimination">후진 제거</option>
              </select>
            </label>
            {modelSelectionMethod === "backward_elimination" ? (
              <label>
                <span>Alpha to remove</span>
                <input
                  aria-describedby="linear-model-alpha-remove-help"
                  max="0.999"
                  min="0.001"
                  step="0.01"
                  type="number"
                  value={alphaToRemove}
                  onChange={(event) => onAlphaToRemoveChange(Number(event.currentTarget.value))}
                />
                <small id="linear-model-alpha-remove-help">
                  제거 가능한 항 중 p-value가 가장 큰 항을 단계적으로 검토합니다.
                </small>
              </label>
            ) : null}
          </div>
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
              <LinearModelFitResults result={result} />
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
                  <div className="notice-box">
                    <strong>모델은 자동 저장되었습니다.</strong>
                    <span>이름과 메모는 모델 계산이나 manifest SHA를 변경하지 않습니다.</span>
                  </div>
                  <div className="button-row">
                    <label className="inline-field">
                      <span>모델 이름</span>
                      <input
                        maxLength={120}
                        value={modelName}
                        onChange={(event) => setModelName(event.currentTarget.value)}
                      />
                    </label>
                    <button
                      className="secondary-button"
                      disabled={isSavingModelName || modelId === null}
                      onClick={() => {
                        if (modelId === null) return;
                        setIsSavingModelName(true);
                        setModelNameError(null);
                        void updateRegressionModelMetadata(modelId, {
                          user_label: modelName,
                        })
                          .catch((error) => {
                            setModelNameError(
                              error instanceof Error ? error.message : "model_metadata_update_failed",
                            );
                          })
                          .finally(() => setIsSavingModelName(false));
                      }}
                      type="button"
                    >
                      {isSavingModelName ? "저장 중" : "이름 저장"}
                    </button>
                    <a className="secondary-button link-button" href="/manage">
                      관리 화면 열기
                    </a>
                  </div>
                  {modelNameError !== null ? (
                    <div className="error-box" role="alert">오류 코드: {modelNameError}</div>
                  ) : null}
                  {modelRetentionState.preflight ? (
                    <div className="notice-box">
                      <strong>
                        예측 참조 {modelRetentionState.preflight.counts.dependent_prediction_count.toLocaleString()}건
                      </strong>
                      <span>
                        붙여넣기 예측 {modelRetentionState.preflight.counts.dependent_pasted_prediction_count.toLocaleString()}건
                        · 회귀 최적화 {modelRetentionState.preflight.counts.dependent_optimization_count.toLocaleString()}건
                      </span>
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
              <RegressionResponseOptimizerPanel
                modelAvailable={modelAvailable}
                result={result}
              />
              <RegressionPredictionPanel
                currentVersion={version}
                expectedModelId={result.model_manifest?.model_id ?? null}
                isRunningPrediction={isRunningPrediction}
                isRunningPreflight={isRunningPredictionPreflight}
                modelAvailable={modelAvailable}
                modelManifestAvailable={result.model_manifest !== undefined}
                modelResult={result}
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
            </>
          ) : null}
        </>
      )}
    </section>
  );
}

function linearModelPredictorKind(column: DatasetColumnResponse): string {
  const representation = predictorKind(column) === "categorical" ? "범주형" : "숫자형";
  return `${representation} · ${measurementLevelLabel(column.measurement_level)} · ${roleLabel(column.role)} 역할`;
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
