import { useMemo, useState } from "react";

import type {
  LinearModelResult,
  RegressionPastedPredictionColumnMappingRequest,
  RegressionPastedPredictionPreflightResponse,
  RegressionPastedPredictionResponse,
} from "./api";
import {
  createRegressionPastedPrediction,
  fetchRegressionPastedPredictionPreflight,
} from "./api/regression";

interface RegressionPastedPredictionPanelProps {
  modelResult: LinearModelResult;
  onSelectDataset: () => void;
}

type Delimiter = "auto" | "tab" | "comma";

export function RegressionPastedPredictionPanel({
  modelResult,
  onSelectDataset,
}: RegressionPastedPredictionPanelProps) {
  const [content, setContent] = useState("");
  const [hasHeader, setHasHeader] = useState(true);
  const [delimiter, setDelimiter] = useState<Delimiter>("auto");
  const [columnMappings, setColumnMappings] = useState<Record<string, string>>({});
  const [preflight, setPreflight] =
    useState<RegressionPastedPredictionPreflightResponse | null>(null);
  const [prediction, setPrediction] =
    useState<RegressionPastedPredictionResponse | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [isPredicting, setIsPredicting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const tablePreview = useMemo(
    () => parsePreview(content, delimiter, hasHeader),
    [content, delimiter, hasHeader],
  );
  const manifest = modelResult.model_manifest;
  const canCheck =
    manifest !== undefined && content.trim().length > 0 && !isChecking && !isPredicting;
  const canPredict =
    preflight?.prediction_ready === true &&
    preflight.model_manifest_sha256 === manifest?.manifest_sha256 &&
    !isChecking &&
    !isPredicting;

  function invalidate(): void {
    setPreflight(null);
    setPrediction(null);
    setError(null);
  }

  function mappings(): RegressionPastedPredictionColumnMappingRequest[] {
    return modelResult.predictors.flatMap((predictor, predictorIndex) => {
      const selected = columnMappings[predictor.column_id];
      if (selected !== undefined && selected !== "") {
        return [{ input_column_index: Number(selected), source_column_id: predictor.column_id }];
      }
      const matchingHeader = tablePreview.headers.findIndex(
        (header) => header === predictor.column_id || header === predictor.display_name,
      );
      if (matchingHeader >= 0) {
        return [
          { input_column_index: matchingHeader, source_column_id: predictor.column_id },
        ];
      }
      if (tablePreview.columnCount === modelResult.predictors.length) {
        return [{ input_column_index: predictorIndex, source_column_id: predictor.column_id }];
      }
      return [];
    });
  }

  async function runPreflight(): Promise<void> {
    if (manifest === undefined) {
      return;
    }
    setIsChecking(true);
    setError(null);
    setPrediction(null);
    try {
      const result = await fetchRegressionPastedPredictionPreflight(manifest.model_id, {
        content,
        has_header: hasHeader,
        delimiter,
        column_mappings: mappings(),
        expected_model_manifest_sha256: manifest.manifest_sha256,
      });
      setPreflight(result);
    } catch (caught) {
      setPreflight(null);
      setError(errorMessage(caught));
    } finally {
      setIsChecking(false);
    }
  }

  async function runPrediction(): Promise<void> {
    if (manifest === undefined || preflight === null) {
      return;
    }
    setIsPredicting(true);
    setError(null);
    try {
      const result = await createRegressionPastedPrediction(manifest.model_id, {
        content,
        has_header: hasHeader,
        delimiter,
        column_mappings: mappings(),
        expected_model_manifest_sha256: manifest.manifest_sha256,
        expected_normalized_input_sha256: preflight.normalized_input_sha256,
        confidence_level: modelResult.confidence_level,
        include_intervals: true,
      });
      setPrediction(result);
    } catch (caught) {
      setPrediction(null);
      setError(errorMessage(caught));
    } finally {
      setIsPredicting(false);
    }
  }

  return (
    <section className="result-section" aria-labelledby="regression-pasted-prediction-title">
      <div className="panel-heading">
        <div>
          <h4 id="regression-pasted-prediction-title">예측</h4>
          <p>저장된 최종 회귀모형으로 새 조건의 반응을 계산합니다.</p>
        </div>
      </div>
      <PredictionInputKindSelector value="pasted" onSelectDataset={onSelectDataset} />
      <div className="option-grid option-grid-wide">
        <label className="prediction-paste-field">
          <span>예측값 붙여넣기</span>
          <textarea
            aria-describedby="regression-paste-help"
            rows={8}
            value={content}
            onChange={(event) => {
              setContent(event.currentTarget.value);
              invalidate();
            }}
            placeholder={pastePlaceholder(modelResult)}
          />
          <small id="regression-paste-help">
            Excel 표, 탭 구분 또는 CSV를 붙여넣을 수 있습니다. 최대 2MB, 10,000행입니다.
          </small>
        </label>
      </div>
      <div className="inline-field-row regression-paste-options">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={hasHeader}
            onChange={(event) => {
              setHasHeader(event.currentTarget.checked);
              invalidate();
            }}
          />
          첫 행에 열 이름 포함
        </label>
        <label>
          구분자
          <select
            value={delimiter}
            onChange={(event) => {
              setDelimiter(event.currentTarget.value as Delimiter);
              invalidate();
            }}
          >
            <option value="auto">자동 감지</option>
            <option value="tab">탭</option>
            <option value="comma">쉼표</option>
          </select>
        </label>
      </div>

      {tablePreview.columnCount > 0 ? (
        <>
          <h5>예측변수 매핑</h5>
          <div className="table-wrap">
            <table className="result-table">
              <thead>
                <tr>
                  <th scope="col">모형 예측변수</th>
                  <th scope="col">종류</th>
                  <th scope="col">붙여넣은 열</th>
                </tr>
              </thead>
              <tbody>
                {modelResult.predictors.map((predictor, predictorIndex) => (
                  <tr key={predictor.column_id}>
                    <td>{predictor.display_name}</td>
                    <td>{predictorKindLabel(modelResult, predictor.column_id)}</td>
                    <td>
                      <select
                        aria-label={`${predictor.display_name} 붙여넣은 열`}
                        value={
                          columnMappings[predictor.column_id] ??
                          defaultMapping(tablePreview.headers, predictor, predictorIndex, modelResult)
                        }
                        onChange={(event) => {
                          setColumnMappings((current) => ({
                            ...current,
                            [predictor.column_id]: event.currentTarget.value,
                          }));
                          invalidate();
                        }}
                      >
                        <option value="">선택</option>
                        {tablePreview.headers.map((header, index) => (
                          <option key={`${index}-${header}`} value={String(index)}>
                            {header}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h5>입력 미리보기</h5>
          <div className="table-wrap prediction-paste-preview">
            <table className="result-table">
              <thead>
                <tr>
                  {tablePreview.headers.map((header, index) => (
                    <th key={`${index}-${header}`} scope="col">{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {tablePreview.rows.map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {tablePreview.headers.map((_, columnIndex) => (
                      <td key={columnIndex}>{row[columnIndex] ?? ""}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}

      <div className="doe-action-bar">
        <div className="doe-validation-summary">
          붙여넣은 값은 데이터셋 목록에 등록되지 않습니다.
        </div>
        <div className="button-row">
          <button className="secondary-button" disabled={!canCheck} onClick={() => void runPreflight()} type="button">
            {isChecking ? "사전점검 중" : "예측 사전점검"}
          </button>
          <button className="primary-button" disabled={!canPredict} onClick={() => void runPrediction()} type="button">
            {isPredicting ? "예측 중" : "예측 실행"}
          </button>
        </div>
      </div>
      {error !== null ? <div className="error-box" role="alert">오류 코드: {error}</div> : null}
      {preflight !== null ? <PastedPreflightSummary preflight={preflight} /> : null}
      {prediction !== null ? <PastedPredictionResults prediction={prediction} /> : null}
    </section>
  );
}

export function PredictionInputKindSelector({
  value,
  onSelectDataset,
  onSelectPasted,
}: {
  value: "dataset" | "pasted";
  onSelectDataset: () => void;
  onSelectPasted?: () => void;
}) {
  return (
    <fieldset className="segmented-fieldset prediction-input-kind">
      <legend>입력 방식</legend>
      <div className="segmented-control">
        <label>
          <input
            type="radio"
            name="regression-prediction-input-kind"
            checked={value === "dataset"}
            onChange={onSelectDataset}
          />
          <span>데이터셋에서 선택</span>
        </label>
        <label>
          <input
            type="radio"
            name="regression-prediction-input-kind"
            checked={value === "pasted"}
            onChange={onSelectPasted ?? (() => undefined)}
          />
          <span>직접 입력·붙여넣기</span>
        </label>
      </div>
    </fieldset>
  );
}

function PastedPreflightSummary({
  preflight,
}: {
  preflight: RegressionPastedPredictionPreflightResponse;
}) {
  return (
    <div className={preflight.prediction_ready ? "success-box" : "error-box"} role="status">
      <strong>{preflight.prediction_ready ? "예측 준비 완료" : "입력을 확인하세요"}</strong>
      <p>
        사용 가능 {preflight.row_count_usable.toLocaleString()} / 전체 {preflight.row_count_total.toLocaleString()}행
        {preflight.row_count_excluded > 0 ? ` · 제외 ${preflight.row_count_excluded.toLocaleString()}행` : ""}
      </p>
      {preflight.issues.map((issue) => (
        <p key={`${issue.code}-${issue.count ?? ""}`}>{issue.message}{issue.count === null ? "" : ` (${issue.count})`}</p>
      ))}
    </div>
  );
}

function PastedPredictionResults({ prediction }: { prediction: RegressionPastedPredictionResponse }) {
  return (
    <>
      <h4>붙여넣기 예측 결과</h4>
      <div className="metadata-grid">
        <span>예측</span><strong>{prediction.row_count_predicted.toLocaleString()}행</strong>
        <span>제외</span><strong>{prediction.row_count_excluded.toLocaleString()}행</strong>
        <span>신뢰수준</span><strong>{(prediction.confidence_level * 100).toFixed(1)}%</strong>
      </div>
      <div className="table-wrap">
        <table className="result-table">
          <thead>
            <tr>
              <th scope="col">입력 행</th>
              {prediction.mappings.map((mapping) => <th key={mapping.source_column_id} scope="col">{mapping.display_name}</th>)}
              <th scope="col">예측 평균</th>
              <th scope="col">평균 신뢰구간</th>
              <th scope="col">개별 예측구간</th>
              <th scope="col">상태</th>
            </tr>
          </thead>
          <tbody>
            {prediction.rows.map((row) => (
              <tr key={row.row_index}>
                <td>{row.row_index + 1}</td>
                {prediction.mappings.map((mapping) => <td key={mapping.source_column_id}>{String(row.predictor_values[mapping.source_column_id] ?? "")}</td>)}
                <td>{formatNumber(row.predicted_mean)}</td>
                <td>{formatInterval(row.mean_confidence_interval)}</td>
                <td>{formatInterval(row.prediction_interval)}</td>
                <td>{row.warnings.length === 0 ? "범위 안" : row.warnings.join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {prediction.truncated ? <div className="notice-box">화면에는 앞 {prediction.row_limit.toLocaleString()}행만 표시합니다.</div> : null}
      {prediction.warnings.map((warning) => <div className="notice-box" key={warning.code}>{warning.message}</div>)}
    </>
  );
}

function parsePreview(content: string, delimiter: Delimiter, hasHeader: boolean) {
  const lines = content.replace(/\r\n?/g, "\n").split("\n").filter((line) => line.trim() !== "");
  if (lines.length === 0) {
    return { headers: [] as string[], rows: [] as string[][], columnCount: 0 };
  }
  const separator = delimiter === "tab" ? "\t" : delimiter === "comma" ? "," : lines[0].includes("\t") ? "\t" : ",";
  const rows = lines.slice(0, 11).map((line) => line.split(separator).map((cell) => cell.trim()));
  const columnCount = Math.max(...rows.map((row) => row.length));
  const headers = hasHeader ? rows[0] : Array.from({ length: columnCount }, (_, index) => `입력 ${index + 1}`);
  return { headers, rows: (hasHeader ? rows.slice(1) : rows).slice(0, 10), columnCount };
}

function defaultMapping(
  headers: string[],
  predictor: LinearModelResult["predictors"][number],
  predictorIndex: number,
  result: LinearModelResult,
): string {
  const matching = headers.findIndex((header) => header === predictor.column_id || header === predictor.display_name);
  if (matching >= 0) return String(matching);
  return headers.length === result.predictors.length ? String(predictorIndex) : "";
}

function predictorKindLabel(result: LinearModelResult, columnId: string): string {
  return result.training_domain?.predictors.find((item) => item.column_id === columnId)?.kind === "categorical" ? "범주형" : "숫자형";
}

function pastePlaceholder(result: LinearModelResult): string {
  const headers = result.predictors.map((predictor) => predictor.display_name).join("\t");
  return `${headers}\n${result.predictors.map(() => "값").join("\t")}`;
}

function formatNumber(value: number): string {
  return Number.isFinite(value) ? value.toLocaleString("ko-KR", { maximumSignificantDigits: 6 }) : "-";
}

function formatInterval(interval: { lower: number; upper: number } | null): string {
  return interval === null ? "-" : `${formatNumber(interval.lower)} ~ ${formatNumber(interval.upper)}`;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "regression_pasted_prediction_failed";
}
