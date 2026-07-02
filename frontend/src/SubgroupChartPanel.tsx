import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  SubgroupChartPoint,
  SubgroupChartResult,
  SubgroupChartSeries,
} from "./api";

type SubgroupChartType = "xbar_r" | "xbar_s";

interface SubgroupChartPanelProps {
  analysisResult: AnalysisResultEnvelope | null;
  chartType: SubgroupChartType;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  methodId: string;
  result: SubgroupChartResult | null;
  subgroupColumnId: string | null;
  subgroupColumns: DatasetColumnResponse[];
  valueColumnId: string | null;
  valueColumns: DatasetColumnResponse[];
  version: DatasetVersionResponse | null;
  onChartTypeChange: (chartType: SubgroupChartType) => void;
  onRun: () => void;
  onSubgroupColumnChange: (columnId: string) => void;
  onValueColumnChange: (columnId: string) => void;
}

const chartWidth = 520;
const chartHeight = 250;
const plot = {
  left: 54,
  right: 18,
  top: 22,
  bottom: 42,
};
const plotWidth = chartWidth - plot.left - plot.right;
const plotHeight = chartHeight - plot.top - plot.bottom;

export function SubgroupChartPanel({
  analysisResult,
  chartType,
  filterValidationError,
  isRunningAnalysis,
  methodId,
  result,
  subgroupColumnId,
  subgroupColumns,
  valueColumnId,
  valueColumns,
  version,
  onChartTypeChange,
  onRun,
  onSubgroupColumnChange,
  onValueColumnChange,
}: SubgroupChartPanelProps) {
  const canRun =
    version !== null &&
    valueColumnId !== null &&
    subgroupColumnId !== null &&
    filterValidationError === null;
  const secondaryChart = result === null ? null : subgroupChartDispersionSeries(result);
  const secondaryChartLabel = result?.chart_type === "xbar_s" ? "S" : "R";
  const secondaryCenterLabel = result?.chart_type === "xbar_s" ? "Sbar" : "Rbar";

  return (
    <section className="analysis-run-panel" aria-labelledby="subgroup-chart-title">
      <div className="panel-heading">
        <div>
          <h3 id="subgroup-chart-title">부분군 관리도 실행</h3>
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
              <span>부분군</span>
              <select
                value={subgroupColumnId ?? ""}
                onChange={(event) => {
                  onSubgroupColumnChange(event.currentTarget.value);
                }}
              >
                <option value="">선택</option>
                {subgroupColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Chart</span>
              <select
                value={chartType}
                onChange={(event) => {
                  onChartTypeChange(event.currentTarget.value as SubgroupChartType);
                }}
              >
                <option value="xbar_r">Xbar-R</option>
                <option value="xbar_s">Xbar-S</option>
              </select>
            </label>
            <div className="option-note">
              <strong>Rule</strong>
              <span>fixed subgroup size · control limit signals</span>
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
            {isRunningAnalysis ? "실행 중" : "부분군 관리도 실행"}
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
              <div className="metadata-grid" aria-label="부분군 관리도 요약">
                <span>측정값</span>
                <strong>{result.value.display_name}</strong>
                <span>부분군</span>
                <strong>{result.subgroup.display_name}</strong>
                <span>부분군 수</span>
                <strong>{result.subgroup_count.toLocaleString()}</strong>
                <span>부분군 크기</span>
                <strong>{result.subgroup_size.toLocaleString()}</strong>
                <span>사용 N</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>Xbar center</span>
                <strong>{formatNumber(result.xbar_chart.center_line)}</strong>
                <span>{secondaryCenterLabel}</span>
                <strong>
                  {secondaryChart === null ? "n/a" : formatNumber(secondaryChart.center_line)}
                </strong>
                <span>신호</span>
                <strong>{result.signals.length.toLocaleString()}개</strong>
              </div>
              <div className="result-section" aria-label="부분군 관리도 결과">
                <div className="chart-grid">
                  <div className="chart-panel">
                    <div className="chart-panel-title">Xbar chart</div>
                    {renderControlChart(result.xbar_chart, `${result.value.display_name} Xbar`)}
                  </div>
                  {secondaryChart === null ? null : (
                    <div className="chart-panel">
                      <div className="chart-panel-title">{secondaryChartLabel} chart</div>
                      {renderControlChart(
                        secondaryChart,
                        `${result.value.display_name} ${secondaryChartLabel}`,
                      )}
                    </div>
                  )}
                </div>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>Chart</th>
                      <th>LCL</th>
                      <th>Center</th>
                      <th>UCL</th>
                      <th>Points</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Xbar</td>
                      <td>{formatNumber(result.xbar_chart.lcl)}</td>
                      <td>{formatNumber(result.xbar_chart.center_line)}</td>
                      <td>{formatNumber(result.xbar_chart.ucl)}</td>
                      <td>{result.xbar_chart.point_count.toLocaleString()}</td>
                    </tr>
                    {secondaryChart === null ? null : (
                      <tr>
                        <td>{secondaryChartLabel}</td>
                        <td>{formatNumber(secondaryChart.lcl)}</td>
                        <td>{formatNumber(secondaryChart.center_line)}</td>
                        <td>{formatNumber(secondaryChart.ucl)}</td>
                        <td>{secondaryChart.point_count.toLocaleString()}</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              {result.signals.length > 0 ? (
                <div className="table-wrap">
                  <table className="result-table">
                    <thead>
                      <tr>
                        <th>신호</th>
                        <th>Chart</th>
                        <th>부분군</th>
                        <th>값</th>
                        <th>한계</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.signals.map((signal) => (
                        <tr key={signal.signal_id}>
                          <td>{signal.code}</td>
                          <td>{signal.chart}</td>
                          <td>{signal.subgroup_label}</td>
                          <td>{formatNumber(signal.value)}</td>
                          <td>{signal.limit}</td>
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

function subgroupChartDispersionSeries(result: SubgroupChartResult): SubgroupChartSeries | null {
  if (result.chart_type === "xbar_s") {
    return result.s_chart ?? null;
  }
  return result.r_chart ?? null;
}

function renderControlChart(series: SubgroupChartSeries, label: string) {
  const points = series.points.filter(
    (point) => Number.isFinite(point.value) && Number.isFinite(point.position),
  );
  if (points.length === 0) {
    return <EmptyChart label="관리도 point 없음" />;
  }

  const yRange = paddedRange([
    ...points.map((point) => point.value),
    series.lcl,
    series.center_line,
    series.ucl,
  ]);
  const xRange = paddedRange(points.map((point) => point.position));
  const path = points
    .map((point) => `${scaleX(point.position, xRange)},${scaleY(point.value, yRange)}`)
    .join(" ");

  return (
    <svg className="mini-chart" role="img" viewBox={`0 0 ${chartWidth} ${chartHeight}`}>
      <title>{label}</title>
      <rect
        x={plot.left}
        y={plot.top}
        width={plotWidth}
        height={plotHeight}
        fill="#ffffff"
        stroke="#d4dde8"
      />
      <ControlLine label="UCL" range={yRange} value={series.ucl} />
      <ControlLine label="CL" range={yRange} value={series.center_line} dashed />
      <ControlLine label="LCL" range={yRange} value={series.lcl} />
      <polyline fill="none" points={path} stroke="#1f4e79" strokeWidth="2" />
      {points.map((point) => (
        <ChartPoint
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
        subgroup position
      </text>
      <text x={8} y={plot.top + 12} className="chart-axis-label">
        value
      </text>
    </svg>
  );
}

function ControlLine({
  dashed = false,
  label,
  range,
  value,
}: {
  dashed?: boolean;
  label: string;
  range: { min: number; max: number };
  value: number;
}) {
  const y = scaleY(value, range);
  return (
    <g>
      <line
        x1={plot.left}
        x2={plot.left + plotWidth}
        y1={y}
        y2={y}
        stroke={dashed ? "#6b7280" : "#b45309"}
        strokeDasharray={dashed ? "5 4" : undefined}
        strokeWidth="1.3"
      />
      <text x={plot.left + 6} y={y - 5} className="chart-axis-label">
        {label} {formatNumber(value)}
      </text>
    </g>
  );
}

function ChartPoint({ point, x, y }: { point: SubgroupChartPoint; x: number; y: number }) {
  const hasSignal = point.signal_codes.length > 0;
  const sourceLabel = `canonical ${point.first_canonical_position.toLocaleString()}-${point.last_canonical_position.toLocaleString()}`;
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
          {`${point.subgroup_label}: ${formatNumber(point.value)} · ${sourceLabel} · ${
            point.signal_codes.join(", ")
          }`}
        </title>
      </g>
    );
  }

  return (
    <g>
      <circle cx={x} cy={y} r="4" fill="#2563eb" stroke="#172033" />
      <title>{`${point.subgroup_label}: ${formatNumber(point.value)} · ${sourceLabel}`}</title>
    </g>
  );
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

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "NA";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 6,
  }).format(value);
}
