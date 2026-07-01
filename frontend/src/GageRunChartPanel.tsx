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

const chartWidth = 540;
const chartHeight = 280;
const plot = {
  left: 56,
  right: 22,
  top: 24,
  bottom: 44,
};
const plotWidth = chartWidth - plot.left - plot.right;
const plotHeight = chartHeight - plot.top - plot.bottom;

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
    <section className="analysis-run-panel" aria-labelledby="gage-run-chart-title">
      <div className="panel-heading">
        <div>
          <h3 id="gage-run-chart-title">Gage Run Chart 실행</h3>
          <p>{methodId}</p>
        </div>
        <span className="status-pill status-ready">사용 가능</span>
      </div>
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
                <div className="chart-grid chart-grid-single">
                  <div className="chart-panel">
                    <div className="chart-panel-title">
                      Part facet · Operator color · Replicate symbol
                    </div>
                    {renderGageRunChart(result)}
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

function renderGageRunChart(result: GageRunChartResult) {
  const points = result.chart.points;
  if (points.length === 0) {
    return <div className="empty-state">표시할 point가 없습니다.</div>;
  }
  const values = [...points.map((point) => point.value), result.summary.mean];
  const yMin = Math.min(...values);
  const yMax = Math.max(...values);
  const yPadding = yMax === yMin ? 1 : (yMax - yMin) * 0.08;
  const min = yMin - yPadding;
  const max = yMax + yPadding;
  const xMax = Math.max(...points.map((point) => point.position), 1);
  const xScale = (position: number) =>
    plot.left + (xMax <= 1 ? 0 : ((position - 1) / (xMax - 1)) * plotWidth);
  const yScale = (value: number) => plot.top + ((max - value) / (max - min)) * plotHeight;
  const meanY = yScale(result.summary.mean);

  return (
    <svg
      aria-label="Gage Run Chart"
      className="analysis-chart"
      role="img"
      viewBox={`0 0 ${chartWidth} ${chartHeight}`}
    >
      <line
        stroke="currentColor"
        strokeOpacity="0.25"
        x1={plot.left}
        x2={plot.left + plotWidth}
        y1={meanY}
        y2={meanY}
      />
      <text className="chart-axis-label" x={plot.left + plotWidth - 56} y={meanY - 6}>
        mean
      </text>
      <line
        stroke="currentColor"
        strokeOpacity="0.35"
        x1={plot.left}
        x2={plot.left}
        y1={plot.top}
        y2={plot.top + plotHeight}
      />
      <line
        stroke="currentColor"
        strokeOpacity="0.35"
        x1={plot.left}
        x2={plot.left + plotWidth}
        y1={plot.top + plotHeight}
        y2={plot.top + plotHeight}
      />
      {points.map((point) => (
        <circle
          className={`chart-point chart-series-${(point.operator_index - 1) % 6}`}
          cx={xScale(point.position)}
          cy={yScale(point.value)}
          key={`${point.position}-${point.canonical_position}`}
          r={point.replicate_index % 2 === 0 ? 4.6 : 3.4}
        >
          <title>{`Run ${point.position}, Part index ${point.part_index}, Operator index ${point.operator_index}, Replicate index ${point.replicate_index}, Value ${formatNumber(point.value)}`}</title>
        </circle>
      ))}
      <text className="chart-axis-label" x={plot.left} y={chartHeight - 8}>
        run order
      </text>
      <text
        className="chart-axis-label"
        transform={`rotate(-90 ${14} ${plot.top + plotHeight})`}
        x={14}
        y={plot.top + plotHeight}
      >
        measurement
      </text>
    </svg>
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
