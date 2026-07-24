import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  IndividualsChartPoint,
  IndividualsChartResult,
  IndividualsChartSeries,
  MovingRangeChartSeries,
} from "./api";

interface IndividualsChartPanelProps {
  analysisResult: AnalysisResultEnvelope | null;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  methodId: string;
  orderColumnId: string | null;
  orderColumns: DatasetColumnResponse[];
  result: IndividualsChartResult | null;
  valueColumnId: string | null;
  valueColumns: DatasetColumnResponse[];
  version: DatasetVersionResponse | null;
  onOrderColumnChange: (columnId: string | null) => void;
  onRun: () => void;
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

export function IndividualsChartPanel({
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
}: IndividualsChartPanelProps) {
  const canRun = version !== null && valueColumnId !== null && filterValidationError === null;

  return (
    <section className="analysis-run-panel" data-analysis-execution={methodId}>
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
              <small className="field-help">
                업로드된 행 순서가 실제 시간 또는 공정 실행 순서를 의미하지 않는다면 날짜시간
                또는 실행 순서 컬럼을 선택하세요.
              </small>
            </label>
            <label>
              <span>순서 컬럼</span>
              <select
                value={orderColumnId ?? ""}
                onChange={(event) => {
                  onOrderColumnChange(event.currentTarget.value || null);
                }}
              >
                <option value="">선택 안 함 · canonical row order</option>
                {orderColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
            <div className="option-note">
              <strong>관리한계</strong>
              <span>MRbar / d2, 3-sigma</span>
            </div>
            <div className="option-note">
              <strong>Rule</strong>
              <span>limits, same side, trend, zone</span>
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
            {isRunningAnalysis ? "실행 중" : "I-MR 관리도 실행"}
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
              <div className="metadata-grid" aria-label="I-MR 관리도 요약">
                <span>전체 상태</span>
                <strong>{overallSignalStatus(result)}</strong>
                <span>측정값</span>
                <strong>{result.value.display_name}</strong>
                <span>순서</span>
                <strong>{formatOrderSource(result)}</strong>
                <span>사용 N</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>I center</span>
                <strong>{formatNumber(result.individuals_chart.center_line)}</strong>
                <span>MRbar</span>
                <strong>{formatNumber(result.sigma_estimator.mrbar)}</strong>
                <span>Sigma</span>
                <strong>{formatNumber(result.sigma_estimator.sigma)}</strong>
                <span>신호</span>
                <strong>{result.signals.length.toLocaleString()}개</strong>
                {result.order_duplicate_count > 0 ? (
                  <>
                    <span>순서 동률</span>
                    <strong>{result.order_duplicate_count.toLocaleString()}개</strong>
                  </>
                ) : null}
              </div>
              <div className="result-section" aria-label="I-MR 관리도 결과">
                <SignalSummary result={result} />
                <div className="chart-grid">
                  <div className="chart-panel">
                    <div className="chart-panel-title">I chart</div>
                    {renderControlChart(
                      result.individuals_chart,
                      `${result.value.display_name} I chart`,
                      "individuals",
                    )}
                  </div>
                  <div className="chart-panel">
                    <div className="chart-panel-title">MR chart</div>
                    {renderControlChart(
                      result.moving_range_chart,
                      `${result.value.display_name} MR chart`,
                      "moving_range",
                    )}
                  </div>
                </div>
              </div>
              <div className="notice-box" aria-label="I-MR 관리도 해석 안내">
                <strong>해석 기준</strong>
                <p>
                  관리한계 밖 점이나 연속 패턴 신호는 특별원인을 조사할 근거입니다. 관리한계
                  안에 있다는 사실만으로 공정 안정성, 정규성, 규격 만족 또는 측정시스템
                  적합성이 증명되지는 않습니다.
                </p>
                <p>
                  관리한계는 실제 공정 변동으로 추정하며, 규격한계는 사용자가 정한 허용
                  기준입니다. Run Chart는 관리한계를 계산하지 않지만 I-MR은 개별 측정값과
                  연속 측정 간 변화를 사용해 관리한계를 추정합니다.
                </p>
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
                      <td>I</td>
                      <td>{formatNumber(result.individuals_chart.lcl)}</td>
                      <td>{formatNumber(result.individuals_chart.center_line)}</td>
                      <td>{formatNumber(result.individuals_chart.ucl)}</td>
                      <td>{result.individuals_chart.point_count.toLocaleString()}</td>
                    </tr>
                    <tr>
                      <td>MR</td>
                      <td>{formatNumber(result.moving_range_chart.lcl)}</td>
                      <td>{formatNumber(result.moving_range_chart.center_line)}</td>
                      <td>{formatNumber(result.moving_range_chart.ucl)}</td>
                      <td>{result.moving_range_chart.point_count.toLocaleString()}</td>
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
                        <th>Chart</th>
                        <th>구간</th>
                        <th>값</th>
                        <th>방향/한계</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.signals.map((signal) => (
                        <tr key={signal.signal_id}>
                          <td>{signal.code}</td>
                          <td>{signal.chart}</td>
                          <td>{formatSignalPosition(signal)}</td>
                          <td>{formatNumber(signal.value)}</td>
                          <td>{formatSignalRule(signal)}</td>
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

function renderControlChart(
  series: IndividualsChartSeries | MovingRangeChartSeries,
  label: string,
  chartKind: "individuals" | "moving_range",
) {
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
      <desc>
        {`${label}. LCL ${formatNumber(series.lcl)}, 중심선 ${formatNumber(
          series.center_line,
        )}, UCL ${formatNumber(series.ucl)}. 사각형은 관리한계 신호, 마름모는 패턴 규칙 신호입니다.`}
      </desc>
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
          key={`${chartKind}-${point.position}-${point.value}`}
          chartKind={chartKind}
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
        canonical position
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

function ChartPoint({
  chartKind,
  point,
  x,
  y,
}: {
  chartKind: "individuals" | "moving_range";
  point: IndividualsChartPoint;
  x: number;
  y: number;
}) {
  const hasSignal = point.signal_codes.length > 0;
  const hasLimitSignal = point.signal_codes.some(
    (code) => code.includes("beyond_3_sigma") || code.includes("mr_beyond_ucl"),
  );
  const sourceLabel = `canonical ${point.canonical_position.toLocaleString()}`;
  if (hasLimitSignal) {
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
          {`${chartKind} ${point.position}: ${formatNumber(point.value)} · ${sourceLabel} · ${
            point.signal_codes.join(", ")
          }`}
        </title>
      </g>
    );
  }
  if (hasSignal) {
    const diamond = `${x},${y - 6} ${x + 6},${y} ${x},${y + 6} ${x - 6},${y}`;
    return (
      <g>
        <polygon points={diamond} fill="#ffffff" stroke="#b45309" strokeWidth="2.5" />
        <title>
          {`${chartKind} ${point.position}: ${formatNumber(point.value)} · ${sourceLabel} · ${
            point.signal_codes.join(", ")
          }`}
        </title>
      </g>
    );
  }

  return (
    <g>
      <circle cx={x} cy={y} r="4" fill="#2563eb" stroke="#172033" />
      <title>
        {`${chartKind} ${point.position}: ${formatNumber(point.value)} · ${sourceLabel}`}
      </title>
    </g>
  );
}

function SignalSummary({ result }: { result: IndividualsChartResult }) {
  const summary = summarizeSignals(result);
  return (
    <div className="metadata-grid" aria-label="I-MR 신호 요약">
      <span>I 차트 관리한계 밖</span>
      <strong>{summary.iLimit.toLocaleString()}점</strong>
      <span>MR 차트 관리한계 밖</span>
      <strong>{summary.mrLimit.toLocaleString()}점</strong>
      <span>중심선 한쪽 연속 신호</span>
      <strong>{summary.sameSide.toLocaleString()}건</strong>
      <span>추세 신호</span>
      <strong>{summary.trend.toLocaleString()}건</strong>
      <span>교대 신호</span>
      <strong>{summary.alternating.toLocaleString()}건</strong>
      <span>Zone rule 신호</span>
      <strong>{summary.zone.toLocaleString()}건</strong>
    </div>
  );
}

function summarizeSignals(result: IndividualsChartResult) {
  return result.signals.reduce(
    (summary, signal) => {
      if (signal.code === "individuals_chart_i_beyond_3_sigma") {
        summary.iLimit += 1;
      } else if (signal.code === "individuals_chart_mr_beyond_ucl") {
        summary.mrLimit += 1;
      } else if (signal.code === "individuals_chart_i_same_side_centerline") {
        summary.sameSide += 1;
      } else if (signal.code === "individuals_chart_i_trend") {
        summary.trend += 1;
      } else if (signal.code === "individuals_chart_i_alternating") {
        summary.alternating += 1;
      } else if (
        signal.code === "individuals_chart_i_two_of_three_beyond_2_sigma" ||
        signal.code === "individuals_chart_i_four_of_five_beyond_1_sigma" ||
        signal.code === "individuals_chart_i_fifteen_within_1_sigma" ||
        signal.code === "individuals_chart_i_eight_outside_1_sigma"
      ) {
        summary.zone += 1;
      }
      return summary;
    },
    { iLimit: 0, mrLimit: 0, sameSide: 0, trend: 0, alternating: 0, zone: 0 },
  );
}

function overallSignalStatus(result: IndividualsChartResult): string {
  return result.signals.length > 0
    ? "특별원인 신호 있음"
    : "현재 활성화된 관리도 규칙에서 신호 없음";
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

function formatOrderSource(result: IndividualsChartResult): string {
  if (result.order === null) {
    return "canonical row order";
  }
  if (result.order_source === "datetime_order_column_ascending") {
    return `${result.order.display_name} · datetime ascending`;
  }
  return `${result.order.display_name} · numeric ascending`;
}

function formatSignalPosition(signal: { position: number; start_position?: number }) {
  if (signal.start_position !== undefined && signal.start_position !== signal.position) {
    return `${signal.start_position.toLocaleString()}-${signal.position.toLocaleString()}`;
  }
  return signal.position.toLocaleString();
}

function formatSignalRule(signal: {
  count?: number;
  direction?: string;
  length?: number;
  limit?: string;
  sigma_multiple?: number;
}) {
  if (signal.limit !== undefined) {
    return signal.limit;
  }
  if (
    signal.direction !== undefined &&
    signal.count !== undefined &&
    signal.length !== undefined &&
    signal.sigma_multiple !== undefined
  ) {
    return `${signal.direction} · ${signal.count}/${signal.length} · ${formatNumber(
      signal.sigma_multiple,
    )}σ`;
  }
  if (
    signal.direction !== undefined &&
    signal.length !== undefined &&
    signal.sigma_multiple !== undefined
  ) {
    return `${signal.direction} · ${signal.length.toLocaleString()} · ${formatNumber(
      signal.sigma_multiple,
    )}σ`;
  }
  if (signal.direction !== undefined && signal.length !== undefined) {
    return `${signal.direction} · ${signal.length.toLocaleString()}`;
  }
  return signal.direction ?? "rule";
}

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "NA";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 6,
  }).format(value);
}
