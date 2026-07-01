import type {
  AnalysisResultEnvelope,
  CapabilityHistogramBin,
  CapabilityResult,
  DatasetColumnResponse,
  DatasetVersionResponse,
} from "./api";

interface CapabilityPanelProps {
  analysisResult: AnalysisResultEnvelope | null;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  lsl: string;
  methodId: string;
  result: CapabilityResult | null;
  target: string;
  usl: string;
  valueColumnId: string | null;
  valueColumns: DatasetColumnResponse[];
  version: DatasetVersionResponse | null;
  onLslChange: (value: string) => void;
  onRun: () => void;
  onTargetChange: (value: string) => void;
  onUslChange: (value: string) => void;
  onValueColumnChange: (columnId: string) => void;
}

const chartWidth = 560;
const chartHeight = 260;
const plot = {
  left: 54,
  right: 20,
  top: 24,
  bottom: 44,
};
const plotWidth = chartWidth - plot.left - plot.right;
const plotHeight = chartHeight - plot.top - plot.bottom;

export function CapabilityPanel({
  analysisResult,
  filterValidationError,
  isRunningAnalysis,
  lsl,
  methodId,
  result,
  target,
  usl,
  valueColumnId,
  valueColumns,
  version,
  onLslChange,
  onRun,
  onTargetChange,
  onUslChange,
  onValueColumnChange,
}: CapabilityPanelProps) {
  const specValidation = capabilitySpecValidation(lsl, usl, target);
  const canRun =
    version !== null &&
    valueColumnId !== null &&
    filterValidationError === null &&
    specValidation.kind === "ready";

  return (
    <section className="analysis-run-panel" aria-labelledby="capability-title">
      <div className="panel-heading">
        <div>
          <h3 id="capability-title">공정능력 분석 실행</h3>
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
              <span>LSL</span>
              <input
                inputMode="decimal"
                placeholder="optional"
                value={lsl}
                onChange={(event) => {
                  onLslChange(event.currentTarget.value);
                }}
              />
            </label>
            <label>
              <span>USL</span>
              <input
                inputMode="decimal"
                placeholder="optional"
                value={usl}
                onChange={(event) => {
                  onUslChange(event.currentTarget.value);
                }}
              />
            </label>
            <label>
              <span>Target</span>
              <input
                inputMode="decimal"
                placeholder="optional"
                value={target}
                onChange={(event) => {
                  onTargetChange(event.currentTarget.value);
                }}
              />
            </label>
            <div className="option-note">
              <strong>Sigma</strong>
              <span>overall SD, MRbar/d2 within</span>
            </div>
            <div className="option-note">
              <strong>Model</strong>
              <span>normal capability</span>
            </div>
          </div>
          {specValidation.kind === "error" ? (
            <div className="notice-box notice-warning">{specValidation.message}</div>
          ) : null}
          <button
            className="primary-button"
            disabled={isRunningAnalysis || !canRun}
            onClick={() => {
              onRun();
            }}
            type="button"
          >
            {isRunningAnalysis ? "실행 중" : "공정능력 분석 실행"}
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
              <div className="metadata-grid" aria-label="공정능력 요약">
                <span>측정값</span>
                <strong>{result.value.display_name}</strong>
                <span>사용 N</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>평균</span>
                <strong>{formatNumber(result.sample.mean)}</strong>
                <span>Overall SD</span>
                <strong>{formatNumber(result.sample.std_overall)}</strong>
                <span>Within SD</span>
                <strong>{formatNumber(result.sample.std_within)}</strong>
                <span>Spec</span>
                <strong>{specLabel(result)}</strong>
              </div>
              <div className="result-section" aria-label="공정능력 시각화">
                {renderCapabilityHistogram(result)}
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>Index</th>
                      <th>Within</th>
                      <th>Overall</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Cp / Pp</td>
                      <td>{formatNullable(result.capability.within.two_sided)}</td>
                      <td>{formatNullable(result.capability.overall.two_sided)}</td>
                    </tr>
                    <tr>
                      <td>CPL / PPL</td>
                      <td>{formatNullable(result.capability.within.lower)}</td>
                      <td>{formatNullable(result.capability.overall.lower)}</td>
                    </tr>
                    <tr>
                      <td>CPU / PPU</td>
                      <td>{formatNullable(result.capability.within.upper)}</td>
                      <td>{formatNullable(result.capability.overall.upper)}</td>
                    </tr>
                    <tr>
                      <td>Cpk / Ppk</td>
                      <td>{formatNullable(result.capability.within.min_side)}</td>
                      <td>{formatNullable(result.capability.overall.min_side)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>비규격</th>
                      <th>관측</th>
                      <th>정규모형 기대</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Below LSL</td>
                      <td>{result.observed_nonconformance.below_lsl_count.toLocaleString()}</td>
                      <td>
                        {formatPercent(
                          result.expected_nonconformance_normal.below_lsl_probability,
                        )}
                      </td>
                    </tr>
                    <tr>
                      <td>Above USL</td>
                      <td>{result.observed_nonconformance.above_usl_count.toLocaleString()}</td>
                      <td>
                        {formatPercent(
                          result.expected_nonconformance_normal.above_usl_probability,
                        )}
                      </td>
                    </tr>
                    <tr>
                      <td>Total ppm</td>
                      <td>{formatNumber(result.observed_nonconformance.total_ppm)}</td>
                      <td>{formatNumber(result.expected_nonconformance_normal.total_ppm)}</td>
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

function capabilitySpecValidation(
  lsl: string,
  usl: string,
  target: string,
): { kind: "ready" | "empty" } | { kind: "error"; message: string } {
  const parsedLsl = parseOptionalNumber(lsl);
  const parsedUsl = parseOptionalNumber(usl);
  const parsedTarget = parseOptionalNumber(target);
  if (parsedLsl.kind === "error" || parsedUsl.kind === "error" || parsedTarget.kind === "error") {
    return { kind: "error", message: "Spec limit과 target은 숫자여야 합니다." };
  }
  if (parsedLsl.value === null && parsedUsl.value === null) {
    return { kind: "empty" };
  }
  if (parsedLsl.value !== null && parsedUsl.value !== null && parsedLsl.value >= parsedUsl.value) {
    return { kind: "error", message: "LSL은 USL보다 작아야 합니다." };
  }
  if (parsedTarget.value !== null) {
    if (parsedLsl.value !== null && parsedTarget.value < parsedLsl.value) {
      return { kind: "error", message: "Target은 지정된 spec 안에 있어야 합니다." };
    }
    if (parsedUsl.value !== null && parsedTarget.value > parsedUsl.value) {
      return { kind: "error", message: "Target은 지정된 spec 안에 있어야 합니다." };
    }
  }
  return { kind: "ready" };
}

function parseOptionalNumber(value: string): { kind: "ok"; value: number | null } | { kind: "error" } {
  const trimmed = value.trim();
  if (trimmed.length === 0) {
    return { kind: "ok", value: null };
  }
  const parsed = Number(trimmed);
  if (!Number.isFinite(parsed)) {
    return { kind: "error" };
  }
  return { kind: "ok", value: parsed };
}

function renderCapabilityHistogram(result: CapabilityResult) {
  const bins = result.histogram.bins;
  if (bins.length === 0) {
    return <EmptyChart label="histogram 없음" />;
  }

  const valueMin = Math.min(
    bins[0].lower,
    result.spec_limits.lsl ?? bins[0].lower,
    result.spec_limits.target ?? bins[0].lower,
  );
  const valueMax = Math.max(
    bins[bins.length - 1].upper,
    result.spec_limits.usl ?? bins[bins.length - 1].upper,
    result.spec_limits.target ?? bins[bins.length - 1].upper,
  );
  const yMax = Math.max(...bins.map((bin) => bin.density), ...bins.map((bin) => bin.normal_density));
  const xRange = paddedRange([valueMin, valueMax]);
  const yRange = { min: 0, max: yMax * 1.12 };
  const densityPath = bins
    .map((bin) => `${scaleX(bin.midpoint, xRange)},${scaleY(bin.normal_density, yRange)}`)
    .join(" ");

  return (
    <svg className="mini-chart" role="img" viewBox={`0 0 ${chartWidth} ${chartHeight}`}>
      <title>{`${result.value.display_name} capability histogram`}</title>
      <rect
        x={plot.left}
        y={plot.top}
        width={plotWidth}
        height={plotHeight}
        fill="#ffffff"
        stroke="#d4dde8"
      />
      {bins.map((bin) => (
        <HistogramBar key={`${bin.lower}-${bin.upper}`} bin={bin} xRange={xRange} yRange={yRange} />
      ))}
      <polyline fill="none" points={densityPath} stroke="#1f4e79" strokeWidth="2" />
      {result.spec_limits.lsl === null ? null : (
        <SpecLine label="LSL" value={result.spec_limits.lsl} range={xRange} />
      )}
      {result.spec_limits.usl === null ? null : (
        <SpecLine label="USL" value={result.spec_limits.usl} range={xRange} />
      )}
      {result.spec_limits.target === null ? null : (
        <SpecLine label="Target" value={result.spec_limits.target} range={xRange} muted />
      )}
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
        measurement value
      </text>
      <text x={8} y={plot.top + 12} className="chart-axis-label">
        density
      </text>
    </svg>
  );
}

function HistogramBar({
  bin,
  xRange,
  yRange,
}: {
  bin: CapabilityHistogramBin;
  xRange: { min: number; max: number };
  yRange: { min: number; max: number };
}) {
  const x1 = scaleX(bin.lower, xRange);
  const x2 = scaleX(bin.upper, xRange);
  const y = scaleY(bin.density, yRange);
  return (
    <g>
      <rect
        x={x1}
        y={y}
        width={Math.max(1, x2 - x1 - 1)}
        height={plot.top + plotHeight - y}
        fill="#d7e8f7"
        stroke="#7aa6ca"
      />
      <title>{`${formatNumber(bin.lower)}-${formatNumber(bin.upper)}: ${bin.count}`}</title>
    </g>
  );
}

function SpecLine({
  label,
  muted = false,
  range,
  value,
}: {
  label: string;
  muted?: boolean;
  range: { min: number; max: number };
  value: number;
}) {
  const x = scaleX(value, range);
  return (
    <g>
      <line
        x1={x}
        x2={x}
        y1={plot.top}
        y2={plot.top + plotHeight}
        stroke={muted ? "#6b7280" : "#b45309"}
        strokeDasharray={muted ? "5 4" : undefined}
        strokeWidth="1.5"
      />
      <text x={x + 4} y={plot.top + 14} className="chart-axis-label">
        {label} {formatNumber(value)}
      </text>
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

function specLabel(result: CapabilityResult) {
  const limits = result.spec_limits;
  return `LSL ${formatNullable(limits.lsl)} / USL ${formatNullable(limits.usl)}`;
}

function paddedRange(values: number[]): { min: number; max: number } {
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) {
    const pad = Math.abs(min) > 1 ? Math.abs(min) * 0.1 : 1;
    return { min: min - pad, max: max + pad };
  }
  const pad = (max - min) * 0.06;
  return { min: min - pad, max: max + pad };
}

function scaleX(value: number, range: { min: number; max: number }) {
  return plot.left + ((value - range.min) / (range.max - range.min)) * plotWidth;
}

function scaleY(value: number, range: { min: number; max: number }) {
  return plot.top + plotHeight - ((value - range.min) / (range.max - range.min)) * plotHeight;
}

function formatNullable(value: number | null) {
  return value === null ? "n/a" : formatNumber(value);
}

function formatNumber(value: number) {
  if (!Number.isFinite(value)) {
    return "n/a";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 4,
  }).format(value);
}

function formatPercent(value: number) {
  if (!Number.isFinite(value)) {
    return "n/a";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 3,
    style: "percent",
  }).format(value);
}
