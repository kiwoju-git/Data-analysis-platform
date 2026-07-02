import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  PearsonCorrelationResult,
} from "./api";

interface PearsonCorrelationPanelProps {
  alpha: number;
  analysisResult: AnalysisResultEnvelope | null;
  confidenceLevel: number;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  methodId: string;
  result: PearsonCorrelationResult | null;
  version: DatasetVersionResponse | null;
  xColumnId: string | null;
  xColumns: DatasetColumnResponse[];
  yColumnId: string | null;
  yColumns: DatasetColumnResponse[];
  onAlphaChange: (alpha: number) => void;
  onConfidenceLevelChange: (confidenceLevel: number) => void;
  onRun: () => void;
  onXColumnChange: (columnId: string) => void;
  onYColumnChange: (columnId: string) => void;
}

const chartWidth = 420;
const chartHeight = 250;
const plot = {
  left: 48,
  right: 14,
  top: 18,
  bottom: 42,
};
const plotWidth = chartWidth - plot.left - plot.right;
const plotHeight = chartHeight - plot.top - plot.bottom;

export function PearsonCorrelationPanel({
  alpha,
  analysisResult,
  confidenceLevel,
  filterValidationError,
  isRunningAnalysis,
  methodId,
  result,
  version,
  xColumnId,
  xColumns,
  yColumnId,
  yColumns,
  onAlphaChange,
  onConfidenceLevelChange,
  onRun,
  onXColumnChange,
  onYColumnChange,
}: PearsonCorrelationPanelProps) {
  const canRun =
    version !== null &&
    xColumnId !== null &&
    yColumnId !== null &&
    xColumnId !== yColumnId &&
    alpha > 0 &&
    alpha < 1 &&
    confidenceLevel > 0 &&
    confidenceLevel < 1 &&
    filterValidationError === null;

  return (
    <section className="analysis-run-panel" aria-labelledby="pearson-title">
      <div className="panel-heading">
        <div>
          <h3 id="pearson-title">Pearson 상관 실행</h3>
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
              <span>X 변수</span>
              <select
                value={xColumnId ?? ""}
                onChange={(event) => {
                  onXColumnChange(event.currentTarget.value);
                }}
              >
                <option value="">선택</option>
                {xColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Y 변수</span>
              <select
                value={yColumnId ?? ""}
                onChange={(event) => {
                  onYColumnChange(event.currentTarget.value);
                }}
              >
                <option value="">선택</option>
                {yColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
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
          <button
            className="primary-button"
            disabled={isRunningAnalysis || !canRun}
            onClick={() => {
              onRun();
            }}
            type="button"
          >
            {isRunningAnalysis ? "실행 중" : "Pearson 상관 실행"}
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
              <div className="metadata-grid" aria-label="Pearson 상관 요약">
                <span>변수</span>
                <strong>
                  {result.x.display_name} / {result.y.display_name}
                </strong>
                <span>사용 N</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>결측 제외</span>
                <strong>
                  {(result.n_excluded_missing_x + result.n_excluded_missing_y).toLocaleString()}
                </strong>
                <span>비숫자 제외</span>
                <strong>
                  {(
                    result.n_excluded_non_numeric_x + result.n_excluded_non_numeric_y
                  ).toLocaleString()}
                </strong>
              </div>
              <div className="result-section" aria-label="Pearson 산점도 결과">
                <div className="panel-heading">
                  <div>
                    <h4>산점도</h4>
                    <p>
                      {result.scatterplot.points.length.toLocaleString()} /{" "}
                      {result.scatterplot.point_count.toLocaleString()} points
                      {result.scatterplot.points_truncated ? " · capped" : ""}
                    </p>
                  </div>
                </div>
                <div className="chart-grid chart-grid-single">
                  <div className="chart-panel">
                    <div className="chart-panel-title">
                      {result.x.display_name} vs {result.y.display_name}
                    </div>
                    {renderScatterPlot(result)}
                  </div>
                </div>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>r</th>
                      <th>CI</th>
                      <th>p-value</th>
                      <th>r²</th>
                      <th>공분산</th>
                      <th>결정</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{formatAnalysisNumber(result.association.correlation)}</td>
                      <td>{confidenceIntervalLabel(result)}</td>
                      <td>{formatAnalysisNumber(result.test.p_value)}</td>
                      <td>{formatAnalysisNumber(result.association.r_squared)}</td>
                      <td>{formatAnalysisNumber(result.association.covariance)}</td>
                      <td>{result.test.reject_null ? "기각" : "기각 안 함"}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>변수</th>
                      <th>N</th>
                      <th>평균</th>
                      <th>표준편차</th>
                      <th>범위</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{result.x.display_name}</td>
                      <td>{result.x_summary.n.toLocaleString()}</td>
                      <td>{formatAnalysisNumber(result.x_summary.mean)}</td>
                      <td>{formatAnalysisNumber(result.x_summary.std)}</td>
                      <td>
                        {formatAnalysisNumber(result.x_summary.min)} -{" "}
                        {formatAnalysisNumber(result.x_summary.max)}
                      </td>
                    </tr>
                    <tr>
                      <td>{result.y.display_name}</td>
                      <td>{result.y_summary.n.toLocaleString()}</td>
                      <td>{formatAnalysisNumber(result.y_summary.mean)}</td>
                      <td>{formatAnalysisNumber(result.y_summary.std)}</td>
                      <td>
                        {formatAnalysisNumber(result.y_summary.min)} -{" "}
                        {formatAnalysisNumber(result.y_summary.max)}
                      </td>
                    </tr>
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

function renderScatterPlot(result: PearsonCorrelationResult) {
  const points = result.scatterplot.points.filter(
    (point) => Number.isFinite(point.x) && Number.isFinite(point.y),
  );
  if (points.length === 0) {
    return <EmptyChart label="산점도 point 없음" />;
  }

  const xRange = paddedRange(points.map((point) => point.x));
  const yRange = paddedRange(points.map((point) => point.y));
  return (
    <svg
      aria-label={`${result.x.display_name} ${result.y.display_name} scatter plot`}
      className="chart-svg chart-svg-wide"
      role="img"
      viewBox={`0 0 ${chartWidth} ${chartHeight}`}
    >
      {chartAxes()}
      {points.map((point, index) => (
        <circle
          key={`${point.x}-${point.y}-${index}`}
          className="scatter-point"
          cx={scale(point.x, xRange.min, xRange.max, plot.left, plot.left + plotWidth)}
          cy={scale(point.y, yRange.min, yRange.max, plot.top + plotHeight, plot.top)}
          r="3"
        />
      ))}
      {chartTickLabels(formatAnalysisNumber(xRange.min), formatAnalysisNumber(xRange.max))}
      <text className="chart-axis-label" x={plot.left - 10} y={plot.top + 8}>
        {formatAnalysisNumber(yRange.max)}
      </text>
      <text className="chart-axis-label" x={plot.left - 10} y={plot.top + plotHeight}>
        {formatAnalysisNumber(yRange.min)}
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

function confidenceIntervalLabel(result: PearsonCorrelationResult): string {
  const { lower, upper, level } = result.confidence_interval;
  if (lower === null || upper === null) {
    return "계산 불가";
  }
  return `${formatPercent(level)} CI ${formatAnalysisNumber(lower)} - ${formatAnalysisNumber(
    upper,
  )}`;
}

function formatPercent(value: number): string {
  return `${Math.round(value * 1000) / 10}%`;
}

function formatAnalysisNumber(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "NA";
  }
  return value.toLocaleString("ko-KR", {
    maximumFractionDigits: 6,
    minimumFractionDigits: 0,
  });
}
