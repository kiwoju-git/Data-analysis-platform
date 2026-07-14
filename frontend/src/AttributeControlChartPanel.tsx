import type {
  AnalysisResultEnvelope,
  AttributeControlChartPoint,
  AttributeControlChartResult,
  AttributeControlChartType,
  DatasetColumnResponse,
  DatasetVersionResponse,
} from "./api";

interface AttributeControlChartPanelProps {
  analysisResult: AnalysisResultEnvelope | null;
  chartType: AttributeControlChartType;
  constantOpportunityConfirmed: boolean;
  countColumnId: string | null;
  countColumns: DatasetColumnResponse[];
  denominatorColumnId: string | null;
  denominatorColumns: DatasetColumnResponse[];
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  methodId: string;
  result: AttributeControlChartResult | null;
  version: DatasetVersionResponse | null;
  onChartTypeChange: (chartType: AttributeControlChartType) => void;
  onConstantOpportunityConfirmedChange: (confirmed: boolean) => void;
  onCountColumnChange: (columnId: string) => void;
  onDenominatorColumnChange: (columnId: string) => void;
  onRun: () => void;
}

const chartOptions: Array<{
  type: AttributeControlChartType;
  label: string;
  purpose: string;
}> = [
  { type: "p", label: "P", purpose: "가변 표본 크기 불량률" },
  { type: "np", label: "NP", purpose: "고정 표본 크기 불량품 수" },
  { type: "c", label: "C", purpose: "동일 검사 기회의 결점 수" },
  { type: "u", label: "U", purpose: "가변 검사 기회의 단위당 결점" },
];

const chartWidth = 760;
const chartHeight = 300;
const plot = { left: 58, right: 22, top: 24, bottom: 44 };
const plotWidth = chartWidth - plot.left - plot.right;
const plotHeight = chartHeight - plot.top - plot.bottom;

export function AttributeControlChartPanel({
  analysisResult,
  chartType,
  constantOpportunityConfirmed,
  countColumnId,
  countColumns,
  denominatorColumnId,
  denominatorColumns,
  filterValidationError,
  isRunningAnalysis,
  methodId,
  result,
  version,
  onChartTypeChange,
  onConstantOpportunityConfirmedChange,
  onCountColumnChange,
  onDenominatorColumnChange,
  onRun,
}: AttributeControlChartPanelProps) {
  const needsDenominator = chartType !== "c";
  const canRun =
    version !== null &&
    countColumnId !== null &&
    (!needsDenominator || denominatorColumnId !== null) &&
    (chartType !== "c" || constantOpportunityConfirmed) &&
    filterValidationError === null;
  const countLabel = chartType === "p" || chartType === "np" ? "불량품 수" : "결점 수";
  const denominatorLabel = chartType === "u" ? "검사 기회" : "표본 크기";

  return (
    <section className="analysis-run-panel" aria-labelledby="attribute-chart-title">
      <div className="panel-heading">
        <div>
          <h3 id="attribute-chart-title">계수형 관리도 실행</h3>
          <p>{methodId}</p>
        </div>
        <span className="status-pill status-ready">사용 가능</span>
      </div>
      {version === null ? (
        <div className="notice-box">데이터셋 버전 생성 후 실행할 수 있습니다.</div>
      ) : (
        <>
          <div
            className="chart-mode-control"
            role="radiogroup"
            aria-label="계수형 관리도 유형"
          >
            {chartOptions.map((option) => (
              <button
                aria-checked={chartType === option.type}
                className={chartType === option.type ? "is-active" : undefined}
                key={option.type}
                onClick={() => {
                  onChartTypeChange(option.type);
                }}
                role="radio"
                title={option.purpose}
                type="button"
              >
                {option.label}
              </button>
            ))}
          </div>
          <div className="option-grid">
            <label>
              <span>{countLabel}</span>
              <select
                value={countColumnId ?? ""}
                onChange={(event) => {
                  onCountColumnChange(event.currentTarget.value);
                }}
              >
                <option value="">선택</option>
                {countColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
            {needsDenominator ? (
              <label>
                <span>{denominatorLabel}</span>
                <select
                  value={denominatorColumnId ?? ""}
                  onChange={(event) => {
                    onDenominatorColumnChange(event.currentTarget.value);
                  }}
                >
                  <option value="">선택</option>
                  {denominatorColumns.map((column) => (
                    <option key={column.column_id} value={column.column_id}>
                      {column.display_name}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <label className="checkbox-field">
                <input
                  checked={constantOpportunityConfirmed}
                  onChange={(event) => {
                    onConstantOpportunityConfirmedChange(event.currentTarget.checked);
                  }}
                  type="checkbox"
                />
                <span>모든 관측의 검사 기회가 동일함을 확인</span>
              </label>
            )}
            <div className="option-note">
              <strong>{chartType.toUpperCase()} chart</strong>
              <span>{chartOptions.find((option) => option.type === chartType)?.purpose}</span>
            </div>
          </div>
          <button
            className="primary-button"
            disabled={isRunningAnalysis || !canRun}
            onClick={onRun}
            type="button"
          >
            {isRunningAnalysis ? "실행 중" : `${chartType.toUpperCase()} 관리도 실행`}
          </button>
          {analysisResult?.warnings.length ? (
            <ul className="warning-list" aria-label="분석 경고">
              {analysisResult.warnings.map((warning, index) => (
                <li key={`${warning.code}-${index}`}>{warning.message}</li>
              ))}
            </ul>
          ) : null}
          {result === null ? null : (
            <>
              <div className="metadata-grid" aria-label="계수형 관리도 요약">
                <span>Chart</span>
                <strong>{result.chart_type.toUpperCase()}</strong>
                <span>계수 정의</span>
                <strong>{result.count_definition === "defectives" ? "불량품" : "결점"}</strong>
                <span>사용 관측</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>중심선</span>
                <strong>{formatNumber(result.center_line)}</strong>
                <span>Dispersion ratio</span>
                <strong>{formatNumber(result.dispersion.ratio)}</strong>
                <span>관측별 한계</span>
                <strong>{result.limits_vary ? "가변" : "고정"}</strong>
                <span>신호</span>
                <strong>{result.signals.length.toLocaleString()}개</strong>
              </div>
              <div className="result-section" aria-label="계수형 관리도 결과">
                <div className="chart-panel">
                  <div className="chart-panel-title">
                    {result.chart_type.toUpperCase()} chart · {result.count.display_name}
                  </div>
                  {renderAttributeChart(result)}
                </div>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>점</th>
                      <th>계수</th>
                      <th>{result.denominator_role === "sample_size" ? "표본 크기" : "검사 기회"}</th>
                      <th>값</th>
                      <th>LCL</th>
                      <th>UCL</th>
                      <th>신호</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.chart.points.slice(0, 25).map((point) => (
                      <tr key={point.position}>
                        <td>{point.position.toLocaleString()}</td>
                        <td>{point.count.toLocaleString()}</td>
                        <td>{point.denominator === null ? "동일 기회" : formatNumber(point.denominator)}</td>
                        <td>{formatNumber(point.value)}</td>
                        <td>{formatNumber(point.lcl)}</td>
                        <td>{formatNumber(point.ucl)}</td>
                        <td>{point.signal_codes.length ? "관리한계 밖" : "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}
    </section>
  );
}

function renderAttributeChart(result: AttributeControlChartResult) {
  const points = result.chart.points.filter((point) =>
    [point.position, point.value, point.lcl, point.ucl].every(Number.isFinite),
  );
  if (points.length === 0) {
    return null;
  }
  const xRange = paddedRange(points.map((point) => point.position));
  const yRange = paddedRange(
    points.flatMap((point) => [point.value, point.lcl, point.ucl, result.center_line]),
  );
  const path = (selector: (point: AttributeControlChartPoint) => number) =>
    points
      .map((point) => `${scaleX(point.position, xRange)},${scaleY(selector(point), yRange)}`)
      .join(" ");

  return (
    <svg className="mini-chart" role="img" viewBox={`0 0 ${chartWidth} ${chartHeight}`}>
      <title>
        {`${result.chart_type.toUpperCase()} 관리도. 중심선 ${formatNumber(result.center_line)}, 신호 ${result.signals.length}개`}
      </title>
      <rect
        fill="#ffffff"
        height={plotHeight}
        stroke="#d4dde8"
        width={plotWidth}
        x={plot.left}
        y={plot.top}
      />
      <polyline fill="none" points={path((point) => point.ucl)} stroke="#b45309" strokeWidth="1.4" />
      <line
        stroke="#6b7280"
        strokeDasharray="5 4"
        x1={plot.left}
        x2={plot.left + plotWidth}
        y1={scaleY(result.center_line, yRange)}
        y2={scaleY(result.center_line, yRange)}
      />
      <polyline fill="none" points={path((point) => point.lcl)} stroke="#b45309" strokeWidth="1.4" />
      <polyline fill="none" points={path((point) => point.value)} stroke="#1f4e79" strokeWidth="2" />
      {points.map((point) => (
        <circle
          cx={scaleX(point.position, xRange)}
          cy={scaleY(point.value, yRange)}
          fill={point.signal_codes.length ? "#b45309" : "#2563eb"}
          key={point.position}
          r={point.signal_codes.length ? 5 : 4}
          stroke="#172033"
        >
          <title>
            {`점 ${point.position}: ${formatNumber(point.value)} · LCL ${formatNumber(point.lcl)} · UCL ${formatNumber(point.ucl)}`}
          </title>
        </circle>
      ))}
      <text className="chart-axis-label" x={plot.left + 6} y={scaleY(result.center_line, yRange) - 5}>
        CL {formatNumber(result.center_line)}
      </text>
      <text className="chart-axis-label" x={plot.left} y={chartHeight - 12}>
        canonical position
      </text>
    </svg>
  );
}

function paddedRange(values: number[]): { min: number; max: number } {
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) {
    return { min: Math.max(0, min - 1), max: max + 1 };
  }
  const pad = (max - min) * 0.08;
  return { min: Math.max(0, min - pad), max: max + pad };
}

function scaleX(value: number, range: { min: number; max: number }) {
  return plot.left + ((value - range.min) / (range.max - range.min)) * plotWidth;
}

function scaleY(value: number, range: { min: number; max: number }) {
  return plot.top + plotHeight - ((value - range.min) / (range.max - range.min)) * plotHeight;
}

function formatNumber(value: number): string {
  if (!Number.isFinite(value)) {
    return "NA";
  }
  return new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 6 }).format(value);
}
