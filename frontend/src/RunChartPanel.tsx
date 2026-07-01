import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  RunChartPoint,
  RunChartResult,
} from "./api";

interface RunChartPanelProps {
  analysisResult: AnalysisResultEnvelope | null;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  methodId: string;
  orderColumnId: string | null;
  orderColumns: DatasetColumnResponse[];
  result: RunChartResult | null;
  valueColumnId: string | null;
  valueColumns: DatasetColumnResponse[];
  version: DatasetVersionResponse | null;
  onOrderColumnChange: (columnId: string) => void;
  onRun: () => void;
  onValueColumnChange: (columnId: string) => void;
}

const chartWidth = 520;
const chartHeight = 270;
const plot = {
  left: 54,
  right: 18,
  top: 24,
  bottom: 44,
};
const plotWidth = chartWidth - plot.left - plot.right;
const plotHeight = chartHeight - plot.top - plot.bottom;

export function RunChartPanel({
  analysisResult,
  filterValidationError,
  isRunningAnalysis,
  methodId,
  orderColumnId,
  orderColumns,
  result,
  valueColumnId,
  valueColumns,
  version,
  onOrderColumnChange,
  onRun,
  onValueColumnChange,
}: RunChartPanelProps) {
  const canRun = version !== null && valueColumnId !== null && filterValidationError === null;

  return (
    <section className="analysis-run-panel" aria-labelledby="run-chart-title">
      <div className="panel-heading">
        <div>
          <h3 id="run-chart-title">런 차트 실행</h3>
          <p>{methodId}</p>
        </div>
        <span className="status-pill status-ready">사용 가능</span>
      </div>
      {version === null ? (
        <div className="notice-box">데이터셋 버전 생성 후 실행할 수 있습니다.</div>
      ) : (
        <>
          <div className="option-grid">
            <label>
              <span>측정값</span>
              <select
                value={valueColumnId ?? ""}
                onChange={(event) => {
                  onValueColumnChange(event.currentTarget.value);
                }}
              >
                <option value="">선택</option>
                {valueColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>순서</span>
              <select
                value={orderColumnId ?? ""}
                onChange={(event) => {
                  onOrderColumnChange(event.currentTarget.value);
                }}
              >
                <option value="">canonical row order</option>
                {orderColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
            <div className="option-note">
              <strong>중심선</strong>
              <span>median</span>
            </div>
            <div className="option-note">
              <strong>Trend</strong>
              <span>strict 6-point rule</span>
            </div>
            <div className="option-note">
              <strong>Oscillation</strong>
              <span>strict 14-point rule</span>
            </div>
            <div className="option-note">
              <strong>Clustering/Mixture</strong>
              <span>exact runs test α=0.05</span>
            </div>
          </div>
          <button
            className="primary-button"
            disabled={isRunningAnalysis || !canRun}
            onClick={() => {
              onRun();
            }}
            type="button"
          >
            {isRunningAnalysis ? "실행 중" : "런 차트 실행"}
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
              <div className="metadata-grid" aria-label="런 차트 요약">
                <span>측정값</span>
                <strong>{result.value.display_name}</strong>
                <span>사용 N</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>중심선</span>
                <strong>{formatRunChartNumber(result.center_line)}</strong>
                <span>순서</span>
                <strong>{formatRunChartOrder(result)}</strong>
                <span>Run count</span>
                <strong>{result.runs.run_count.toLocaleString()}</strong>
                <span>Runs test</span>
                <strong>{formatRunChartRunsTest(result)}</strong>
                <span>Trend 신호</span>
                <strong>
                  {countRunChartSignals(result, "run_chart_trend").toLocaleString()}개
                </strong>
                <span>Oscillation 신호</span>
                <strong>
                  {countRunChartSignals(result, "run_chart_oscillation").toLocaleString()}개
                </strong>
                <span>Clustering/Mixture</span>
                <strong>
                  {countRunChartSignals(result, "run_chart_clustering").toLocaleString()} /{" "}
                  {countRunChartSignals(result, "run_chart_mixture").toLocaleString()}개
                </strong>
                <span>관리한계</span>
                <strong>계산 안 함</strong>
              </div>
              <div className="result-section" aria-label="런 차트 결과">
                <div className="panel-heading">
                  <div>
                    <h4>런 차트</h4>
                    <p>
                      {result.chart.points.length.toLocaleString()} /{" "}
                      {result.chart.point_count.toLocaleString()} points
                      {result.chart.points_truncated ? " · capped" : ""}
                    </p>
                  </div>
                </div>
                <div className="chart-grid chart-grid-single">
                  <div className="chart-panel">
                    <div className="chart-panel-title">{result.value.display_name}</div>
                    {renderRunChart(result)}
                  </div>
                </div>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>Above</th>
                      <th>Below</th>
                      <th>Tie</th>
                      <th>최장 run</th>
                      <th>결측 제외</th>
                      <th>비숫자 제외</th>
                      <th>순서 결측 제외</th>
                      <th>순서 비숫자 제외</th>
                      <th>순서 tie</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{result.runs.n_above.toLocaleString()}</td>
                      <td>{result.runs.n_below.toLocaleString()}</td>
                      <td>{result.runs.n_ties.toLocaleString()}</td>
                      <td>{result.runs.longest_run_length.toLocaleString()}</td>
                      <td>{result.n_excluded_missing_value.toLocaleString()}</td>
                      <td>{result.n_excluded_non_numeric_value.toLocaleString()}</td>
                      <td>{(result.n_excluded_missing_order ?? 0).toLocaleString()}</td>
                      <td>{(result.n_excluded_non_numeric_order ?? 0).toLocaleString()}</td>
                      <td>{(result.order_duplicate_count ?? 0).toLocaleString()}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              {result.signals.length > 0 ? (
                <div className="table-wrap">
                  <table className="result-table">
                    <thead>
                      <tr>
                        <th>신호</th>
                        <th>방향</th>
                        <th>길이</th>
                        <th>구간</th>
                        <th>정의</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.signals.map((signal) => (
                        <tr key={signal.signal_id}>
                          <td>{signal.code}</td>
                          <td>{signal.direction}</td>
                          <td>{signal.length.toLocaleString()}</td>
                          <td>
                            {signal.start_position.toLocaleString()} -{" "}
                            {signal.end_position.toLocaleString()}
                          </td>
                          <td>{signal.definition}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </>
          ) : null}
        </>
      )}
    </section>
  );
}

function renderRunChart(result: RunChartResult) {
  const points = result.chart.points.filter(
    (point) => Number.isFinite(point.value) && Number.isFinite(point.position),
  );
  if (points.length === 0) {
    return <EmptyChart label="런 차트 point 없음" />;
  }

  const xRange = paddedRange(points.map((point) => point.position));
  const yRange = paddedRange([...points.map((point) => point.value), result.center_line]);
  const centerY = scaleY(result.center_line, yRange);
  const path = points
    .map((point) => `${scaleX(point.position, xRange)},${scaleY(point.value, yRange)}`)
    .join(" ");
  const xAxisLabel =
    result.chart.x_axis === "order_rank" ? "order rank" : "canonical position";

  return (
    <svg
      aria-label={`${result.value.display_name} run chart`}
      className="mini-chart"
      role="img"
      viewBox={`0 0 ${chartWidth} ${chartHeight}`}
    >
      <rect
        x={plot.left}
        y={plot.top}
        width={plotWidth}
        height={plotHeight}
        fill="#ffffff"
        stroke="#d4dde8"
      />
      <line
        x1={plot.left}
        x2={plot.left + plotWidth}
        y1={centerY}
        y2={centerY}
        stroke="#6b7280"
        strokeDasharray="5 4"
        strokeWidth="1.5"
      />
      <text x={plot.left + 6} y={centerY - 6} className="chart-axis-label">
        median {formatRunChartNumber(result.center_line)}
      </text>
      <polyline fill="none" points={path} stroke="#1f4e79" strokeWidth="2" />
      {points.map((point) => (
        <RunChartDot
          key={`${point.position}-${point.value}`}
          point={point}
          x={scaleX(point.position, xRange)}
          y={scaleY(point.value, yRange)}
        />
      ))}
      <line
        x1={plot.left}
        x2={plot.left}
        y1={plot.top}
        y2={plot.top + plotHeight}
        stroke="#7b8794"
      />
      <line
        x1={plot.left}
        x2={plot.left + plotWidth}
        y1={plot.top + plotHeight}
        y2={plot.top + plotHeight}
        stroke="#7b8794"
      />
      <text x={plot.left} y={chartHeight - 12} className="chart-axis-label">
        {xAxisLabel}
      </text>
      <text x={8} y={plot.top + 12} className="chart-axis-label">
        value
      </text>
      <text x={plot.left} y={plot.top + plotHeight + 18} className="chart-axis-label">
        {formatRunChartNumber(xRange.min)}
      </text>
      <text
        x={plot.left + plotWidth - 20}
        y={plot.top + plotHeight + 18}
        className="chart-axis-label"
      >
        {formatRunChartNumber(xRange.max)}
      </text>
    </svg>
  );
}

function RunChartDot({
  point,
  x,
  y,
}: {
  point: RunChartPoint;
  x: number;
  y: number;
}) {
  const hasSignal = point.signal_codes.length > 0;
  const signalLabel = point.signal_codes.join(", ");
  const sourceLabel =
    point.canonical_position === undefined
      ? ""
      : ` · canonical ${point.canonical_position.toLocaleString()}`;
  if (hasSignal) {
    return (
      <g>
        <rect
          x={x - 4.5}
          y={y - 4.5}
          width="9"
          height="9"
          fill="#b45309"
          stroke="#78350f"
        />
        <title>
          {`${point.position}: ${formatRunChartNumber(point.value)}${sourceLabel} · ${
            signalLabel
          }`}
        </title>
      </g>
    );
  }

  const fill =
    point.relative_to_center === "above"
      ? "#2563eb"
      : point.relative_to_center === "below"
        ? "#059669"
        : "#6b7280";
  return (
    <g>
      <circle cx={x} cy={y} r="4" fill={fill} stroke="#172033" />
      <title>
        {`${point.position}: ${formatRunChartNumber(point.value)}${sourceLabel} · ${
          point.relative_to_center
        }`}
      </title>
    </g>
  );
}

function countRunChartSignals(result: RunChartResult, code: string): number {
  return result.signals.filter((signal) => signal.code === code).length;
}

function formatRunChartOrder(result: RunChartResult): string {
  if (result.order == null) {
    return "canonical row order";
  }
  if (result.order.data_type === "datetime") {
    const timezone = result.order_timezone === "timezone_aware_utc" ? " · UTC" : "";
    return `${result.order.display_name} datetime asc${timezone}`;
  }
  return `${result.order.display_name} numeric asc`;
}

function formatRunChartRunsTest(result: RunChartResult): string {
  if (!result.runs_test.available) {
    return result.runs_test.skipped_reason === null
      ? "계산 안 함"
      : `계산 안 함 · ${result.runs_test.skipped_reason}`;
  }
  return `low p=${formatRunChartNumber(result.runs_test.p_value_low)} · high p=${formatRunChartNumber(
    result.runs_test.p_value_high,
  )}`;
}

function EmptyChart({ label }: { label: string }) {
  return (
    <svg className="mini-chart" role="img" viewBox={`0 0 ${chartWidth} ${chartHeight}`}>
      <rect width={chartWidth} height={chartHeight} fill="#f8fafc" />
      <text x={plot.left} y={chartHeight / 2} className="chart-axis-label">
        {label}
      </text>
    </svg>
  );
}

function paddedRange(values: number[]): { min: number; max: number } {
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) {
    const pad = Math.abs(min) > 1 ? Math.abs(min) * 0.1 : 1;
    return { min: min - pad, max: max + pad };
  }
  const pad = (max - min) * 0.08;
  return { min: min - pad, max: max + pad };
}

function scaleX(value: number, range: { min: number; max: number }) {
  return plot.left + ((value - range.min) / (range.max - range.min)) * plotWidth;
}

function scaleY(value: number, range: { min: number; max: number }) {
  return plot.top + plotHeight - ((value - range.min) / (range.max - range.min)) * plotHeight;
}

function formatRunChartNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "NA";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 6,
  }).format(value);
}
