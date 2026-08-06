import { useState } from "react";

import type {
  RegressionPastedPredictionMapping,
  RegressionPredictionInterval,
  RegressionPredictionRow,
} from "./api";

interface PredictionResultRow extends RegressionPredictionRow {
  predictor_values?: Record<string, number | string>;
}

export interface RegressionPredictionResultsTableProps {
  mappings?: RegressionPastedPredictionMapping[];
  rows: PredictionResultRow[];
  rowNumberOffset?: number;
}

export function RegressionPredictionResultsTable({
  mappings = [],
  rows,
  rowNumberOffset = 0,
}: RegressionPredictionResultsTableProps) {
  const [view, setView] = useState<"summary" | "full">("summary");
  const [expandedRows, setExpandedRows] = useState<Set<number>>(() => new Set());
  const hasInputs = mappings.length > 0 && rows.some((row) => row.predictor_values !== undefined);

  return (
    <div className="regression-prediction-results">
      {hasInputs ? (
        <div className="segmented-control compact-segments" aria-label="예측 결과 보기" role="group">
          <button
            aria-pressed={view === "summary"}
            className={view === "summary" ? "segment-active" : ""}
            onClick={() => setView("summary")}
            type="button"
          >
            요약 보기
          </button>
          <button
            aria-pressed={view === "full"}
            className={view === "full" ? "segment-active" : ""}
            onClick={() => setView("full")}
            type="button"
          >
            입력값 포함
          </button>
        </div>
      ) : null}
      {view === "full" && hasInputs ? (
        <FullPredictionTable mappings={mappings} rowNumberOffset={rowNumberOffset} rows={rows} />
      ) : (
        <SummaryPredictionTable
          expandedRows={expandedRows}
          mappings={mappings}
          rowNumberOffset={rowNumberOffset}
          rows={rows}
          onToggleRow={(rowIndex) => {
            setExpandedRows((current) => {
              const next = new Set(current);
              if (next.has(rowIndex)) next.delete(rowIndex);
              else next.add(rowIndex);
              return next;
            });
          }}
        />
      )}
    </div>
  );
}

function SummaryPredictionTable({
  expandedRows,
  mappings,
  onToggleRow,
  rowNumberOffset,
  rows,
}: {
  expandedRows: Set<number>;
  mappings: RegressionPastedPredictionMapping[];
  onToggleRow: (rowIndex: number) => void;
  rowNumberOffset: number;
  rows: PredictionResultRow[];
}) {
  const hasInputs = mappings.length > 0;
  return (
    <div className="table-wrap regression-prediction-results-wrap">
      <table className="result-table regression-prediction-results-table is-summary">
        <colgroup>
          <col className="regression-prediction-row-column" />
          <col className="regression-prediction-mean-column" />
          <col className="regression-prediction-interval-column" />
          <col className="regression-prediction-interval-column" />
          <col className="regression-prediction-status-column" />
          {hasInputs ? <col className="regression-prediction-detail-column" /> : null}
        </colgroup>
        <thead><tr><th scope="col">입력 행</th><th scope="col">예측 평균</th><th scope="col">평균 신뢰구간</th><th scope="col">개별 예측구간</th><th scope="col">상태</th>{hasInputs ? <th scope="col">입력 조건</th> : null}</tr></thead>
        <tbody>
          {rows.map((row) => {
            const expanded = expandedRows.has(row.row_index);
            const hasRowInputs = hasInputs && row.predictor_values !== undefined;
            return (
              <PredictionSummaryRows
                expanded={expanded}
                hasInputs={hasRowInputs}
                key={row.row_index}
                mappings={mappings}
                row={row}
                rowNumber={row.row_index + rowNumberOffset + 1}
                onToggle={() => onToggleRow(row.row_index)}
              />
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function PredictionSummaryRows({ expanded, hasInputs, mappings, onToggle, row, rowNumber }: {
  expanded: boolean;
  hasInputs: boolean;
  mappings: RegressionPastedPredictionMapping[];
  onToggle: () => void;
  row: PredictionResultRow;
  rowNumber: number;
}) {
  return (
    <>
      <tr>
        <td>{rowNumber.toLocaleString()}</td>
        <td className="regression-prediction-number">{formatNumber(row.predicted_mean)}</td>
        <td className="regression-prediction-interval">{formatInterval(row.mean_confidence_interval)}</td>
        <td className="regression-prediction-interval">{formatInterval(row.prediction_interval)}</td>
        <td className="regression-prediction-status">{statusLabel(row.warnings)}</td>
        {mappings.length > 0 ? <td>{hasInputs ? <button aria-expanded={expanded} className="secondary-button compact-button" onClick={onToggle} type="button">{expanded ? "조건 닫기" : "조건 보기"}</button> : "-"}</td> : null}
      </tr>
      {hasInputs && expanded ? (
        <tr className="regression-prediction-detail-row"><td colSpan={6}>
          <dl className="regression-prediction-input-details">
            {mappings.map((mapping) => <div key={mapping.source_column_id}><dt>{mapping.display_name}</dt><dd>{String(row.predictor_values?.[mapping.source_column_id] ?? "-")}</dd></div>)}
          </dl>
        </td></tr>
      ) : null}
    </>
  );
}

function FullPredictionTable({ mappings, rowNumberOffset, rows }: {
  mappings: RegressionPastedPredictionMapping[];
  rowNumberOffset: number;
  rows: PredictionResultRow[];
}) {
  const minWidth = 70 + mappings.reduce((total, mapping) => total + (mapping.predictor_kind === "categorical" ? 170 : 140), 0) + 610;
  return (
    <div className="table-wrap regression-prediction-results-wrap">
      <table className="result-table regression-prediction-results-table is-full" style={{ minWidth: `${minWidth}px` }}>
        <colgroup>
          <col className="regression-prediction-row-column" />
          {mappings.map((mapping) => <col className={`regression-prediction-input-column is-${mapping.predictor_kind}`} key={mapping.source_column_id} />)}
          <col className="regression-prediction-mean-column" /><col className="regression-prediction-interval-column" /><col className="regression-prediction-interval-column" /><col className="regression-prediction-status-column" />
        </colgroup>
        <thead>
          <tr className="regression-prediction-header-groups"><th rowSpan={2} scope="col">입력 행</th><th colSpan={mappings.length} scope="colgroup">입력 조건</th><th colSpan={4} scope="colgroup">예측 결과</th></tr>
          <tr>{mappings.map((mapping) => <th key={mapping.source_column_id} scope="col">{mapping.display_name}</th>)}<th scope="col">예측 평균</th><th scope="col">평균 신뢰구간</th><th scope="col">개별 예측구간</th><th scope="col">상태</th></tr>
        </thead>
        <tbody>{rows.map((row) => <tr key={row.row_index}>
          <td>{(row.row_index + rowNumberOffset + 1).toLocaleString()}</td>
          {mappings.map((mapping) => <td className="regression-prediction-input-value" key={mapping.source_column_id}>{String(row.predictor_values?.[mapping.source_column_id] ?? "-")}</td>)}
          <td className="regression-prediction-number">{formatNumber(row.predicted_mean)}</td><td className="regression-prediction-interval">{formatInterval(row.mean_confidence_interval)}</td><td className="regression-prediction-interval">{formatInterval(row.prediction_interval)}</td><td className="regression-prediction-status">{statusLabel(row.warnings)}</td>
        </tr>)}</tbody>
      </table>
    </div>
  );
}

function statusLabel(warnings: string[]): string {
  return warnings.length === 0 ? "범위 안" : warnings.join(", ");
}

function formatNumber(value: number): string {
  return Number.isFinite(value) ? value.toLocaleString("ko-KR", { maximumSignificantDigits: 6 }) : "-";
}

function formatInterval(interval: RegressionPredictionInterval | null): string {
  return interval === null ? "-" : `[${formatNumber(interval.lower)}, ${formatNumber(interval.upper)}]`;
}
