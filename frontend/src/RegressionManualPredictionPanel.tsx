import { useMemo, useRef, useState } from "react";

import type {
  LinearModelResult,
  RegressionPastedPredictionPreflightResponse,
  RegressionPastedPredictionResponse,
} from "./api";
import {
  createRegressionPastedPrediction,
  fetchRegressionPastedPredictionPreflight,
} from "./api/regression";

interface ManualRow {
  id: string;
  values: Record<string, string>;
}

interface Props {
  modelAvailable?: boolean;
  modelResult: LinearModelResult;
}

export function RegressionManualPredictionPanel({
  modelAvailable = true,
  modelResult,
}: Props) {
  const nextRowId = useRef(2);
  const [rows, setRows] = useState<ManualRow[]>([emptyRow("manual-row-1", modelResult)]);
  const [pasteOpen, setPasteOpen] = useState(false);
  const [pasteContent, setPasteContent] = useState("");
  const [pasteHasHeader, setPasteHasHeader] = useState(false);
  const [preflight, setPreflight] =
    useState<RegressionPastedPredictionPreflightResponse | null>(null);
  const [prediction, setPrediction] =
    useState<RegressionPastedPredictionResponse | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [isPredicting, setIsPredicting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const manifest = modelResult.model_manifest;
  const domains = useMemo(
    () =>
      new Map(
        (modelResult.training_domain?.predictors ?? []).map((domain) => [
          domain.column_id,
          domain,
        ]),
      ),
    [modelResult.training_domain],
  );
  const issues = useMemo(
    () => validateRows(rows, modelResult, domains),
    [domains, modelResult, rows],
  );
  const table = useMemo(() => serializeRows(rows, modelResult), [modelResult, rows]);
  const canCheck =
    modelAvailable &&
    manifest !== undefined &&
    issues.size === 0 &&
    !isChecking &&
    !isPredicting;
  const canPredict =
    canCheck &&
    preflight?.prediction_ready === true &&
    preflight.row_count_usable === rows.length &&
    preflight.model_manifest_sha256 === manifest?.manifest_sha256;

  function invalidate(): void {
    setPreflight(null);
    setPrediction(null);
    setError(null);
  }

  function updateValue(rowId: string, columnId: string, value: string): void {
    setRows((current) =>
      current.map((row) =>
        row.id === rowId ? { ...row, values: { ...row.values, [columnId]: value } } : row,
      ),
    );
    invalidate();
  }

  function addRow(): void {
    if (rows.length >= 10_000) return;
    const id = `manual-row-${nextRowId.current++}`;
    setRows((current) => [...current, emptyRow(id, modelResult)]);
    invalidate();
  }

  function removeRow(rowId: string): void {
    setRows((current) => {
      const remaining = current.filter((row) => row.id !== rowId);
      return remaining.length > 0
        ? remaining
        : [emptyRow(`manual-row-${nextRowId.current++}`, modelResult)];
    });
    invalidate();
  }

  async function runPreflight(): Promise<void> {
    if (manifest === undefined || !canCheck) return;
    setIsChecking(true);
    setError(null);
    setPrediction(null);
    try {
      const response = await fetchRegressionPastedPredictionPreflight(manifest.model_id, {
        content: table,
        has_header: true,
        delimiter: "tab",
        column_mappings: modelResult.predictors.map((predictor, index) => ({
          input_column_index: index,
          source_column_id: predictor.column_id,
        })),
        expected_model_manifest_sha256: manifest.manifest_sha256,
      });
      if (response.row_count_usable !== rows.length) {
        setError("입력한 행 중 점검을 통과하지 못한 행이 있어 전체 예측을 차단했습니다.");
        setPreflight(response);
        return;
      }
      setPreflight(response);
    } catch (caught) {
      setError(errorMessage(caught));
      setPreflight(null);
    } finally {
      setIsChecking(false);
    }
  }

  async function runPrediction(): Promise<void> {
    if (manifest === undefined || preflight === null || !canPredict) return;
    setIsPredicting(true);
    setError(null);
    try {
      const response = await createRegressionPastedPrediction(manifest.model_id, {
        content: table,
        has_header: true,
        delimiter: "tab",
        column_mappings: modelResult.predictors.map((predictor, index) => ({
          input_column_index: index,
          source_column_id: predictor.column_id,
        })),
        expected_model_manifest_sha256: manifest.manifest_sha256,
        expected_normalized_input_sha256: preflight.normalized_input_sha256,
        confidence_level: modelResult.confidence_level,
        include_intervals: true,
      });
      if (response.row_count_predicted !== rows.length) {
        setError("일부 행만 예측된 응답은 저장 결과로 표시하지 않습니다.");
        setPrediction(null);
        return;
      }
      setPrediction(response);
    } catch (caught) {
      setError(errorMessage(caught));
      setPrediction(null);
    } finally {
      setIsPredicting(false);
    }
  }

  function importPaste(): void {
    const imported = parseImportedRows(pasteContent, pasteHasHeader, modelResult);
    if (imported.error !== null) {
      setError(imported.error);
      return;
    }
    setRows(
      imported.rows.map((values) => ({
        id: `manual-row-${nextRowId.current++}`,
        values,
      })),
    );
    setPasteOpen(false);
    setPasteContent("");
    invalidate();
  }

  return (
    <section className="result-section regression-manual-prediction" aria-labelledby="regression-manual-prediction-title">
      <div className="panel-heading">
        <div>
          <h4 id="regression-manual-prediction-title">예측 조건 입력</h4>
          <p>저장된 최종 회귀모형에 적용할 조건을 행 단위로 입력하고 한 번에 점검합니다.</p>
        </div>
      </div>
      {manifest === undefined ? (
        <div className="notice-box">저장된 model manifest가 없는 결과입니다.</div>
      ) : null}
      {!modelAvailable ? (
        <div className="notice-box">저장 모델을 사용할 수 없어 새 예측을 실행할 수 없습니다.</div>
      ) : null}
      <div className="table-wrap regression-manual-grid-wrap">
        <table className="result-table regression-manual-grid">
          <thead>
            <tr>
              <th scope="col">행</th>
              {modelResult.predictors.map((predictor) => (
                <th key={predictor.column_id} scope="col">{predictor.display_name}</th>
              ))}
              <th scope="col">상태</th>
              <th scope="col">작업</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={row.id}>
                <th scope="row">{rowIndex + 1}</th>
                {modelResult.predictors.map((predictor) => {
                  const domain = domains.get(predictor.column_id);
                  const issue = issues.get(`${row.id}:${predictor.column_id}`);
                  const inputId = `${row.id}-${predictor.column_id}`;
                  return (
                    <td key={predictor.column_id}>
                      {domain?.kind === "categorical" ? (
                        <select
                          aria-describedby={issue ? `${inputId}-error` : undefined}
                          aria-invalid={issue ? true : undefined}
                          aria-label={`${rowIndex + 1}행 ${predictor.display_name}`}
                          id={inputId}
                          value={row.values[predictor.column_id] ?? ""}
                          onChange={(event) => updateValue(row.id, predictor.column_id, event.currentTarget.value)}
                        >
                          <option value="">선택</option>
                          {(domain.levels ?? []).map((level) => <option key={level} value={level}>{level}</option>)}
                        </select>
                      ) : (
                        <input
                          aria-describedby={issue ? `${inputId}-error` : undefined}
                          aria-invalid={issue ? true : undefined}
                          aria-label={`${rowIndex + 1}행 ${predictor.display_name}`}
                          id={inputId}
                          inputMode={domain?.integer_only ? "numeric" : "decimal"}
                          type="text"
                          value={row.values[predictor.column_id] ?? ""}
                          onChange={(event) => updateValue(row.id, predictor.column_id, event.currentTarget.value)}
                        />
                      )}
                      {issue ? <small className="field-error" id={`${inputId}-error`}>{issue}</small> : null}
                      {domain?.kind === "numeric" && domain.minimum !== undefined && domain.maximum !== undefined ? (
                        <small className="cell-subtle">학습 {formatNumber(domain.minimum)} ~ {formatNumber(domain.maximum)}</small>
                      ) : null}
                    </td>
                  );
                })}
                <td>{rowHasIssue(row.id, issues) ? "확인 필요" : "입력 완료"}</td>
                <td><button aria-label={`${rowIndex + 1}행 삭제`} className="secondary-button compact-button" onClick={() => removeRow(row.id)} type="button">삭제</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="button-row regression-manual-row-actions">
        <button className="secondary-button" disabled={rows.length >= 10_000} onClick={addRow} type="button">행 추가</button>
        <button className="secondary-button" onClick={() => setPasteOpen((open) => !open)} type="button">붙여넣기 가져오기</button>
      </div>
      {pasteOpen ? (
        <section className="notice-box regression-paste-import" aria-labelledby="regression-paste-import-title">
          <h5 id="regression-paste-import-title">붙여넣기 가져오기</h5>
          <textarea aria-label="예측 조건 붙여넣기" rows={7} value={pasteContent} onChange={(event) => setPasteContent(event.currentTarget.value)} />
          <label className="checkbox-label"><input checked={pasteHasHeader} onChange={(event) => setPasteHasHeader(event.currentTarget.checked)} type="checkbox" />첫 행에 열 이름 포함</label>
          <p>탭 구분 Excel 표 또는 CSV를 확인한 뒤 현재 입력 grid에 적용합니다.</p>
          <div className="button-row">
            <button className="secondary-button" onClick={() => setPasteOpen(false)} type="button">취소</button>
            <button className="primary-button" disabled={pasteContent.trim() === ""} onClick={importPaste} type="button">입력 grid에 적용</button>
          </div>
        </section>
      ) : null}
      <div className="doe-action-bar">
        <div className="doe-validation-summary">
          {issues.size > 0 ? `수정할 cell ${issues.size.toLocaleString()}개` : `예측 조건 ${rows.length.toLocaleString()}행`}
        </div>
        <div className="button-row">
          <button className="secondary-button" disabled={!canCheck} onClick={() => void runPreflight()} type="button">{isChecking ? "점검 중" : "전체 사전점검"}</button>
          <button className="primary-button" disabled={!canPredict} onClick={() => void runPrediction()} type="button">{isPredicting ? "예측 중" : "전체 예측 실행"}</button>
        </div>
      </div>
      {error ? <div className="error-box" role="alert">{error}</div> : null}
      {preflight ? <div className={canPredict ? "success-box" : "error-box"} role="status">사용 가능 {preflight.row_count_usable.toLocaleString()} / 전체 {preflight.row_count_total.toLocaleString()}행</div> : null}
      {prediction ? <ManualPredictionResults prediction={prediction} /> : null}
      <div className="notice-box">입력한 값은 데이터셋 목록에 등록되지 않습니다. 학습 범위 밖 예측과 OLS 가정을 함께 확인하세요.</div>
    </section>
  );
}

function ManualPredictionResults({ prediction }: { prediction: RegressionPastedPredictionResponse }) {
  return (
    <section aria-labelledby="regression-manual-results-title">
      <h4 id="regression-manual-results-title">예측 결과</h4>
      <div className="table-wrap"><table className="result-table"><thead><tr><th scope="col">입력 행</th>{prediction.mappings.map((mapping) => <th key={mapping.source_column_id} scope="col">{mapping.display_name}</th>)}<th scope="col">예측 평균</th><th scope="col">평균 신뢰구간</th><th scope="col">개별 예측구간</th><th scope="col">상태</th></tr></thead><tbody>{prediction.rows.map((row) => <tr key={row.row_index}><td>{row.row_index + 1}</td>{prediction.mappings.map((mapping) => <td key={mapping.source_column_id}>{String(row.predictor_values[mapping.source_column_id] ?? "")}</td>)}<td>{formatNumber(row.predicted_mean)}</td><td>{formatInterval(row.mean_confidence_interval)}</td><td>{formatInterval(row.prediction_interval)}</td><td>{row.warnings.length === 0 ? "범위 안" : row.warnings.join(", ")}</td></tr>)}</tbody></table></div>
    </section>
  );
}

function emptyRow(id: string, result: LinearModelResult): ManualRow {
  return { id, values: Object.fromEntries(result.predictors.map((predictor) => [predictor.column_id, ""])) };
}

function validateRows(
  rows: ManualRow[],
  result: LinearModelResult,
  domains: Map<string, NonNullable<LinearModelResult["training_domain"]>["predictors"][number]>,
): Map<string, string> {
  const issues = new Map<string, string>();
  rows.forEach((row) => result.predictors.forEach((predictor) => {
    const value = (row.values[predictor.column_id] ?? "").trim();
    const key = `${row.id}:${predictor.column_id}`;
    const domain = domains.get(predictor.column_id);
    if (value === "") issues.set(key, "필수 값");
    else if (domain?.kind !== "categorical") {
      const numeric = Number(value);
      if (!Number.isFinite(numeric)) issues.set(key, "숫자를 입력하세요");
      else if (domain?.integer_only && !Number.isInteger(numeric)) issues.set(key, "정수를 입력하세요");
    } else if (!(domain.levels ?? []).includes(value)) issues.set(key, "학습된 수준을 선택하세요");
  }));
  return issues;
}

function rowHasIssue(rowId: string, issues: Map<string, string>): boolean {
  return [...issues.keys()].some((key) => key.startsWith(`${rowId}:`));
}

function serializeRows(rows: ManualRow[], result: LinearModelResult): string {
  const escape = (value: string) => value.replace(/\t|\r|\n/g, " ");
  return [
    result.predictors.map((predictor) => escape(predictor.column_id)).join("\t"),
    ...rows.map((row) => result.predictors.map((predictor) => escape(row.values[predictor.column_id] ?? "")).join("\t")),
  ].join("\n");
}

function parseImportedRows(content: string, hasHeader: boolean, result: LinearModelResult): { rows: Array<Record<string, string>>; error: string | null } {
  const lines = content.replace(/\r\n?/g, "\n").split("\n").filter((line) => line.trim() !== "");
  if (hasHeader && lines.length === 1) return { rows: [], error: "첫 행을 열 이름으로 사용하도록 설정되어 실제 예측 데이터 행이 없습니다. 첫 행에 열 이름 포함을 해제하세요." };
  if (lines.length === 0) return { rows: [], error: "붙여넣은 값이 없습니다." };
  const separator = lines[0].includes("\t") ? "\t" : ",";
  let cells = lines.map((line) => line.split(separator).map((cell) => cell.trim()));
  let indexes = result.predictors.map((_, index) => index);
  if (hasHeader) {
    const header = cells[0];
    indexes = result.predictors.map((predictor) => header.findIndex((value) => value === predictor.column_id || value === predictor.display_name));
    if (indexes.some((index) => index < 0)) return { rows: [], error: "모든 predictor 열 이름을 찾을 수 없습니다." };
    cells = cells.slice(1);
  } else if (cells.every((row) => row.length === 1) && cells.length === result.predictors.length) {
    cells = [cells.map((row) => row[0])];
  }
  if (cells.length > 10_000) return { rows: [], error: "예측 조건은 최대 10,000행입니다." };
  if (cells.some((row) => indexes.some((index) => index >= row.length))) return { rows: [], error: "붙여넣은 열 수와 predictor mapping을 확인하세요." };
  return {
    rows: cells.map((row) => Object.fromEntries(result.predictors.map((predictor, index) => [predictor.column_id, row[indexes[index]] ?? ""]))),
    error: null,
  };
}

function formatNumber(value: number): string {
  return Number.isFinite(value) ? value.toLocaleString("ko-KR", { maximumSignificantDigits: 6 }) : "-";
}

function formatInterval(interval: { lower: number; upper: number } | null): string {
  return interval === null ? "-" : `${formatNumber(interval.lower)} ~ ${formatNumber(interval.upper)}`;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "regression_manual_prediction_failed";
}
