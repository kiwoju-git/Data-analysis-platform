import { InteractiveHistogramChart } from "./charts/InteractiveHistogramChart";
import type {
  AnalysisResultEnvelope,
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
  return <InteractiveHistogramChart chartId="capability-histogram" columnName={result.value.display_name} unit={result.value.unit}
    nBasis={result.n_used} ordinate="density"
    bins={result.histogram.bins.map((bin, index) => ({ ...bin, include_lower: true, include_upper: index === result.histogram.bins.length - 1 }))}
    densityFitPoints={result.histogram.bins.map((bin) => ({ x: bin.midpoint, density: bin.normal_density }))}
    referenceValues={[["LSL", result.spec_limits.lsl], ["USL", result.spec_limits.usl], ["Target", result.spec_limits.target]].flatMap(([label, value]) =>
      typeof value === "number" ? [{ label: String(label), value }] : [])} />;
}

function specLabel(result: CapabilityResult) {
  const limits = result.spec_limits;
  return `LSL ${formatNullable(limits.lsl)} / USL ${formatNullable(limits.usl)}`;
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
