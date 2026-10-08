import { GageResultChart } from "./charts/GageResultChart";
import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  GageRunChartResult,
} from "./api";

interface GageRunChartPanelProps {
  analysisResult: AnalysisResultEnvelope | null;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  measurementColumnId: string | null;
  measurementColumns: DatasetColumnResponse[];
  methodId: string;
  operatorColumnId: string | null;
  operatorColumns: DatasetColumnResponse[];
  orderColumnId: string | null;
  orderColumns: DatasetColumnResponse[];
  partColumnId: string | null;
  partColumns: DatasetColumnResponse[];
  replicateColumnId: string | null;
  replicateColumns: DatasetColumnResponse[];
  result: GageRunChartResult | null;
  version: DatasetVersionResponse | null;
  onMeasurementColumnChange: (columnId: string) => void;
  onOperatorColumnChange: (columnId: string) => void;
  onOrderColumnChange: (columnId: string) => void;
  onPartColumnChange: (columnId: string) => void;
  onReplicateColumnChange: (columnId: string) => void;
  onRun: () => void;
}

export function GageRunChartPanel({
  analysisResult,
  filterValidationError,
  isRunningAnalysis,
  measurementColumnId,
  measurementColumns,
  methodId,
  operatorColumnId,
  operatorColumns,
  orderColumnId,
  orderColumns,
  partColumnId,
  partColumns,
  replicateColumnId,
  replicateColumns,
  result,
  version,
  onMeasurementColumnChange,
  onOperatorColumnChange,
  onOrderColumnChange,
  onPartColumnChange,
  onReplicateColumnChange,
  onRun,
}: GageRunChartPanelProps) {
  const selectedColumnIds = [
    measurementColumnId,
    partColumnId,
    operatorColumnId,
    replicateColumnId,
  ].filter((columnId): columnId is string => columnId !== null);
  const roleColumnsDistinct = new Set(selectedColumnIds).size === selectedColumnIds.length;
  const canRun =
    version !== null &&
    measurementColumnId !== null &&
    partColumnId !== null &&
    operatorColumnId !== null &&
    replicateColumnId !== null &&
    roleColumnsDistinct &&
    filterValidationError === null;

  return (
    <section className="analysis-run-panel" data-analysis-execution={methodId}>
      {version === null ? (
        <div className="notice-box">데이터셋 버전 생성 후 실행할 수 있습니다.</div>
      ) : (
        <>
          <div className="option-grid">
            <ColumnSelect
              columns={measurementColumns}
              label="측정값"
              value={measurementColumnId}
              onChange={onMeasurementColumnChange}
            />
            <ColumnSelect
              columns={partColumns}
              label="부품"
              value={partColumnId}
              onChange={onPartColumnChange}
            />
            <ColumnSelect
              columns={operatorColumns}
              label="측정자"
              value={operatorColumnId}
              onChange={onOperatorColumnChange}
            />
            <ColumnSelect
              columns={replicateColumns}
              label="반복"
              value={replicateColumnId}
              onChange={onReplicateColumnChange}
            />
            <ColumnSelect
              columns={orderColumns}
              emptyLabel="canonical row order"
              label="실행 순서"
              value={orderColumnId}
              onChange={onOrderColumnChange}
            />
            <div className="option-note">
              <strong>표시 정책</strong>
              <span>part/operator/replicate index only</span>
            </div>
          </div>
          {!roleColumnsDistinct ? (
            <div className="notice-box notice-warning">
              측정값, 부품, 측정자, 반복 컬럼은 서로 달라야 합니다.
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
            {isRunningAnalysis ? "실행 중" : "Gage Run Chart 실행"}
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
              <div className="metadata-grid" aria-label="Gage Run Chart 요약">
                <span>사용 N</span>
                <strong>
                  {result.sample.n_used.toLocaleString()} /{" "}
                  {result.sample.n_total.toLocaleString()}
                </strong>
                <span>부품</span>
                <strong>{result.design.part_count.toLocaleString()}개</strong>
                <span>측정자</span>
                <strong>{result.design.operator_count.toLocaleString()}명</strong>
                <span>반복</span>
                <strong>{result.design.replicate_count?.toLocaleString() ?? "n/a"}회</strong>
                <span>평균</span>
                <strong>{formatNumber(result.summary.mean)}</strong>
                <span>범위</span>
                <strong>{formatNumber(result.summary.range)}</strong>
                <span>순서</span>
                <strong>{formatOrderSource(result.order_source)}</strong>
                <span>Label</span>
                <strong>redacted</strong>
              </div>
              <div className="result-section">
                <div className="panel-heading">
                  <div>
                    <h4>진단 차트</h4>
                    <p>
                      {result.chart.points.length.toLocaleString()} /{" "}
                      {result.chart.point_count.toLocaleString()} points
                      {result.chart.points_truncated ? " · capped" : ""}
                    </p>
                  </div>
                </div>
                <div className="chart-grid chart-grid-single analysis-result-grid">
                  <div className="chart-panel">
                    <div className="chart-panel-title">
                      Part facet · Operator color · Replicate symbol
                    </div>
                    <GageResultChart result={result} />
                  </div>
                </div>
              </div>
              <div className="result-section">
                <h4>부품 요약</h4>
                <SummaryTable rows={result.part_summaries} rowLabel="Part" />
              </div>
              <div className="result-section">
                <h4>측정자 요약</h4>
                <SummaryTable rows={result.operator_summaries} rowLabel="Operator" />
              </div>
            </>
          ) : null}
        </>
      )}
    </section>
  );
}

function ColumnSelect({
  columns,
  emptyLabel = "선택",
  label,
  value,
  onChange,
}: {
  columns: DatasetColumnResponse[];
  emptyLabel?: string;
  label: string;
  value: string | null;
  onChange: (columnId: string) => void;
}) {
  return (
    <label>
      <span>{label}</span>
      <select
        value={value ?? ""}
        onChange={(event) => {
          onChange(event.currentTarget.value);
        }}
      >
        <option value="">{emptyLabel}</option>
        {columns.map((column) => (
          <option key={column.column_id} value={column.column_id}>
            {column.display_name}
          </option>
        ))}
      </select>
    </label>
  );
}

function SummaryTable({
  rowLabel,
  rows,
}: {
  rowLabel: string;
  rows: GageRunChartResult["part_summaries"];
}) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>{rowLabel}</th>
            <th>N</th>
            <th>Mean</th>
            <th>Min</th>
            <th>Max</th>
            <th>Range</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.index}>
              <td>{row.index}</td>
              <td>{row.n.toLocaleString()}</td>
              <td>{formatNumber(row.mean)}</td>
              <td>{formatNumber(row.minimum)}</td>
              <td>{formatNumber(row.maximum)}</td>
              <td>{formatNumber(row.range)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatNumber(value: number): string {
  if (!Number.isFinite(value)) {
    return "n/a";
  }
  return value.toLocaleString(undefined, {
    maximumFractionDigits: 4,
  });
}

function formatOrderSource(source: string): string {
  if (source === "canonical_row_order") {
    return "canonical row";
  }
  if (source === "numeric_order_column_ascending") {
    return "numeric column";
  }
  if (source === "datetime_order_column_ascending") {
    return "datetime column";
  }
  return source;
}
