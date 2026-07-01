import type { ReactNode } from "react";

import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  GraphicalSummaryResult,
} from "./api";

interface GraphicalSummaryPanelProps {
  analysisResult: AnalysisResultEnvelope | null;
  filterValidationError: string | null;
  graphicalColumns: DatasetColumnResponse[];
  graphicalResult: GraphicalSummaryResult | null;
  isRunningAnalysis: boolean;
  methodId: string;
  selectedColumnIds: string[];
  version: DatasetVersionResponse | null;
  onRun: () => void;
  onToggleColumn: (columnId: string, checked: boolean) => void;
}

const maxGraphicalColumns = 20;
const chartWidth = 360;
const chartHeight = 210;
const plot = {
  left: 38,
  right: 12,
  top: 16,
  bottom: 36,
};
const plotWidth = chartWidth - plot.left - plot.right;
const plotHeight = chartHeight - plot.top - plot.bottom;

export function GraphicalSummaryPanel({
  analysisResult,
  filterValidationError,
  graphicalColumns,
  graphicalResult,
  isRunningAnalysis,
  methodId,
  selectedColumnIds,
  version,
  onRun,
  onToggleColumn,
}: GraphicalSummaryPanelProps) {
  return (
    <section className="analysis-run-panel" aria-labelledby="graphical-summary-title">
      <div className="panel-heading">
        <div>
          <h3 id="graphical-summary-title">그래프 요약 실행</h3>
          <p>{methodId}</p>
        </div>
        <span className="status-pill status-ready">사용 가능</span>
      </div>
      {version === null ? (
        <div className="notice-box">데이터셋 버전 생성 후 실행할 수 있습니다.</div>
      ) : (
        <>
          <div className="column-picker" aria-label="그래프 요약 컬럼 선택">
            {graphicalColumns.map((column) => (
              <label key={column.column_id}>
                <input
                  checked={selectedColumnIds.includes(column.column_id)}
                  type="checkbox"
                  onChange={(event) => {
                    onToggleColumn(column.column_id, event.currentTarget.checked);
                  }}
                />
                <span>{column.display_name}</span>
              </label>
            ))}
          </div>
          <button
            className="primary-button"
            disabled={
              isRunningAnalysis ||
              selectedColumnIds.length === 0 ||
              selectedColumnIds.length > maxGraphicalColumns ||
              filterValidationError !== null
            }
            onClick={() => {
              onRun();
            }}
            type="button"
          >
            {isRunningAnalysis ? "실행 중" : "그래프 요약 실행"}
          </button>
          {analysisResult?.provenance.row_count_included !== undefined &&
          analysisResult.provenance.row_count_included !== null ? (
            <div className="metadata-grid" aria-label="분석 대상 행">
              <span>사용 행</span>
              <strong>
                {analysisResult.provenance.row_count_included.toLocaleString()} /{" "}
                {(
                  analysisResult.provenance.row_count_total ??
                  analysisResult.provenance.row_count_included
                ).toLocaleString()}
              </strong>
            </div>
          ) : null}
          {analysisResult?.warnings.length ? (
            <ul className="warning-list" aria-label="분석 경고">
              {analysisResult.warnings.map((warning, index) => (
                <li key={`${warning.code}-${index}`}>{warning.message}</li>
              ))}
            </ul>
          ) : null}
          {graphicalResult !== null ? (
            <div className="graphical-summary-results" aria-label="그래프 요약 결과">
              <div className="result-section">
                <div className="panel-heading">
                  <div>
                    <h4>분포 시각화</h4>
                    <p>
                      {graphicalResult.histogram_method} histogram ·{" "}
                      {graphicalResult.boxplot_method} boxplot · point cap{" "}
                      {graphicalResult.point_limit.toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="graphical-summary-grid">
                  {graphicalResult.columns.map((column) => (
                    <GraphicalSummaryVisualCard key={column.column_id} column={column} />
                  ))}
                </div>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>컬럼</th>
                      <th>N</th>
                      <th>결측</th>
                      <th>최소</th>
                      <th>Q1</th>
                      <th>중앙값</th>
                      <th>Q3</th>
                      <th>최대</th>
                      <th>Bins</th>
                      <th>Outliers</th>
                      <th>Q-Q</th>
                      <th>ECDF</th>
                    </tr>
                  </thead>
                  <tbody>
                    {graphicalResult.columns.map((column) => (
                      <tr key={column.column_id}>
                        <td>{column.display_name}</td>
                        <td>{column.n_used}</td>
                        <td>{column.n_missing}</td>
                        <td>{formatAnalysisNumber(column.min)}</td>
                        <td>{formatAnalysisNumber(column.q1)}</td>
                        <td>{formatAnalysisNumber(column.median)}</td>
                        <td>{formatAnalysisNumber(column.q3)}</td>
                        <td>{formatAnalysisNumber(column.max)}</td>
                        <td>{column.histogram.bin_count}</td>
                        <td>{column.boxplot.outlier_count}</td>
                        <td>{column.qq_plot.point_count}</td>
                        <td>{column.ecdf.point_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}

function GraphicalSummaryVisualCard({
  column,
}: {
  column: GraphicalSummaryResult["columns"][number];
}) {
  return (
    <section className="graphical-summary-card" aria-label={`${column.display_name} 그래프 요약`}>
      <div className="graphical-card-heading">
        <div>
          <h5>{column.display_name}</h5>
          <p>
            N {column.n_used.toLocaleString()} · missing {column.n_missing.toLocaleString()}
          </p>
        </div>
        {column.warnings.length > 0 ? (
          <span className="chart-warning-count">{column.warnings.length} warning</span>
        ) : null}
      </div>
      <div className="chart-grid">
        <ChartPanel title="히스토그램">{renderHistogram(column)}</ChartPanel>
        <ChartPanel title="박스플롯">{renderBoxplot(column)}</ChartPanel>
        <ChartPanel title="Q-Q Plot">{renderQqPlot(column)}</ChartPanel>
        <ChartPanel title="ECDF">{renderEcdf(column)}</ChartPanel>
      </div>
      {column.warnings.length > 0 ? (
        <ul className="inline-warning-list" aria-label={`${column.display_name} 그래프 경고`}>
          {column.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}
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

function renderHistogram(column: GraphicalSummaryResult["columns"][number]) {
  const bins = column.histogram.bins;
  if (bins.length === 0) {
    return <EmptyChart label="숫자 데이터 없음" />;
  }
  const range = paddedRange([
    ...bins.map((bin) => bin.lower),
    ...bins.map((bin) => bin.upper),
  ]);
  const maxCount = Math.max(1, ...bins.map((bin) => bin.count));
  return (
    <svg
      aria-label={`${column.display_name} histogram`}
      className="chart-svg"
      role="img"
      viewBox={`0 0 ${chartWidth} ${chartHeight}`}
    >
      {chartAxes()}
      {bins.map((bin, index) => {
        const x1 = scale(bin.lower, range.min, range.max, plot.left, plot.left + plotWidth);
        const x2 = scale(bin.upper, range.min, range.max, plot.left, plot.left + plotWidth);
        const barWidth = Math.max(1, x2 - x1 - 1);
        const barHeight = (bin.count / maxCount) * plotHeight;
        return (
          <rect
            key={`${bin.lower}-${bin.upper}-${index}`}
            className="histogram-bar"
            height={barHeight}
            width={barWidth}
            x={x1}
            y={plot.top + plotHeight - barHeight}
          />
        );
      })}
      {chartTickLabels(formatAnalysisNumber(range.min), formatAnalysisNumber(range.max))}
      <text className="chart-axis-label" x={plot.left - 8} y={plot.top + 8}>
        {maxCount}
      </text>
    </svg>
  );
}

function renderBoxplot(column: GraphicalSummaryResult["columns"][number]) {
  const boxplot = column.boxplot;
  const required = [
    boxplot.lower_whisker,
    boxplot.q1,
    boxplot.median,
    boxplot.q3,
    boxplot.upper_whisker,
  ];
  if (required.some((value) => value === null)) {
    return <EmptyChart label="숫자 데이터 없음" />;
  }
  const lowerWhisker = boxplot.lower_whisker ?? 0;
  const q1 = boxplot.q1 ?? lowerWhisker;
  const median = boxplot.median ?? q1;
  const q3 = boxplot.q3 ?? median;
  const upperWhisker = boxplot.upper_whisker ?? q3;
  const range = paddedRange([lowerWhisker, q1, median, q3, upperWhisker]);
  const y = plot.top + plotHeight / 2;
  const boxTop = y - 22;
  const boxHeight = 44;
  const xLower = scale(lowerWhisker, range.min, range.max, plot.left, plot.left + plotWidth);
  const xQ1 = scale(q1, range.min, range.max, plot.left, plot.left + plotWidth);
  const xMedian = scale(median, range.min, range.max, plot.left, plot.left + plotWidth);
  const xQ3 = scale(q3, range.min, range.max, plot.left, plot.left + plotWidth);
  const xUpper = scale(upperWhisker, range.min, range.max, plot.left, plot.left + plotWidth);
  return (
    <svg
      aria-label={`${column.display_name} boxplot`}
      className="chart-svg"
      role="img"
      viewBox={`0 0 ${chartWidth} ${chartHeight}`}
    >
      {chartAxes(false)}
      <line className="boxplot-line" x1={xLower} x2={xUpper} y1={y} y2={y} />
      <line className="boxplot-line" x1={xLower} x2={xLower} y1={y - 16} y2={y + 16} />
      <line className="boxplot-line" x1={xUpper} x2={xUpper} y1={y - 16} y2={y + 16} />
      <rect
        className="boxplot-box"
        height={boxHeight}
        width={Math.max(1, xQ3 - xQ1)}
        x={xQ1}
        y={boxTop}
      />
      <line className="boxplot-median" x1={xMedian} x2={xMedian} y1={boxTop} y2={boxTop + boxHeight} />
      {boxplot.outlier_count > 0 ? (
        <text className="chart-note" x={plot.left} y={plot.top + 20}>
          outliers {boxplot.outlier_count}
        </text>
      ) : null}
      {chartTickLabels(formatAnalysisNumber(range.min), formatAnalysisNumber(range.max))}
    </svg>
  );
}

function renderQqPlot(column: GraphicalSummaryResult["columns"][number]) {
  const points = column.qq_plot.points
    .filter(
      (point): point is { theoretical: number; sample: number } =>
        typeof point.theoretical === "number" && typeof point.sample === "number",
    )
    .slice(0, 500);
  if (points.length === 0) {
    return <EmptyChart label="Q-Q point 없음" />;
  }
  const xRange = paddedRange(points.map((point) => point.theoretical));
  const yRange = paddedRange(points.map((point) => point.sample));
  return (
    <svg
      aria-label={`${column.display_name} Q-Q plot`}
      className="chart-svg"
      role="img"
      viewBox={`0 0 ${chartWidth} ${chartHeight}`}
    >
      {chartAxes()}
      <line
        className="reference-line"
        x1={plot.left}
        x2={plot.left + plotWidth}
        y1={plot.top + plotHeight}
        y2={plot.top}
      />
      {points.map((point, index) => (
        <circle
          key={`${point.theoretical}-${point.sample}-${index}`}
          className="qq-point"
          cx={scale(point.theoretical, xRange.min, xRange.max, plot.left, plot.left + plotWidth)}
          cy={scale(point.sample, yRange.min, yRange.max, plot.top + plotHeight, plot.top)}
          r="2"
        />
      ))}
      {chartTickLabels(formatAnalysisNumber(xRange.min), formatAnalysisNumber(xRange.max))}
      <text className="chart-axis-label" x={plot.left - 8} y={plot.top + 8}>
        {formatAnalysisNumber(yRange.max)}
      </text>
    </svg>
  );
}

function renderEcdf(column: GraphicalSummaryResult["columns"][number]) {
  const points = column.ecdf.points
    .filter(
      (point): point is { x: number; probability: number } =>
        typeof point.x === "number" && typeof point.probability === "number",
    )
    .slice(0, 500)
    .sort((left, right) => left.x - right.x || left.probability - right.probability);
  if (points.length === 0) {
    return <EmptyChart label="ECDF point 없음" />;
  }
  const xRange = paddedRange(points.map((point) => point.x));
  const path = ecdfPath(points, xRange);
  return (
    <svg
      aria-label={`${column.display_name} ECDF`}
      className="chart-svg"
      role="img"
      viewBox={`0 0 ${chartWidth} ${chartHeight}`}
    >
      {chartAxes()}
      <path className="ecdf-line" d={path} />
      {points.map((point, index) => (
        <circle
          key={`${point.x}-${point.probability}-${index}`}
          className="ecdf-point"
          cx={scale(point.x, xRange.min, xRange.max, plot.left, plot.left + plotWidth)}
          cy={scale(point.probability, 0, 1, plot.top + plotHeight, plot.top)}
          r="1.6"
        />
      ))}
      {chartTickLabels(formatAnalysisNumber(xRange.min), formatAnalysisNumber(xRange.max))}
      <text className="chart-axis-label" x={plot.left - 8} y={plot.top + 8}>
        1
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

function chartAxes(showYAxis = true) {
  return (
    <>
      {showYAxis ? (
        <line
          className="chart-axis"
          x1={plot.left}
          x2={plot.left}
          y1={plot.top}
          y2={plot.top + plotHeight}
        />
      ) : null}
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
      <text className="chart-axis-label" x={plot.left} y={chartHeight - 10}>
        {leftLabel}
      </text>
      <text className="chart-axis-label chart-axis-label-end" x={plot.left + plotWidth} y={chartHeight - 10}>
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

function ecdfPath(points: Array<{ x: number; probability: number }>, xRange: { min: number; max: number }) {
  let previousY = plot.top + plotHeight;
  const parts = [`M ${plot.left} ${previousY}`];
  for (const point of points) {
    const x = scale(point.x, xRange.min, xRange.max, plot.left, plot.left + plotWidth);
    const y = scale(point.probability, 0, 1, plot.top + plotHeight, plot.top);
    parts.push(`L ${x} ${previousY}`, `L ${x} ${y}`);
    previousY = y;
  }
  parts.push(`L ${plot.left + plotWidth} ${previousY}`);
  return parts.join(" ");
}

function formatAnalysisNumber(value: number | null): string {
  if (value === null) {
    return "-";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 6,
  }).format(value);
}
