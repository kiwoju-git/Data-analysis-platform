import { t } from "../i18n/translate";
import { ChartItemFeedback } from "./ChartItemFeedback";
import { ChartFrame } from "./ChartFrame";
import { ChartAxes } from "./ChartAxes";
import { paddedNumericRange, scaleChartValue } from "./chartScale";
import { useChartItemInteraction } from "./useChartItemInteraction";

export interface InteractiveHistogramBin {
  count: number; include_lower: boolean; include_upper: boolean; lower: number; upper: number;
  density?: number;
}
interface InteractiveHistogramChartProps {
  bins: InteractiveHistogramBin[]; chartId: string; columnName: string; nBasis: number;
  normalFitPoints?: Array<{ x: number; expected_count: number }>;
  densityFitPoints?: Array<{ x: number; density: number }>;
  ordinate?: "count" | "density"; unit?: string | null; sourceKey?: string;
  referenceValues?: Array<{ label: string; value: number }>;
}
const layout = { width: 360, height: 210, maxWidth: 640, plot: { left: 60, top: 16, width: 288, height: 130 } };

export function InteractiveHistogramChart({ bins, chartId, columnName, nBasis, normalFitPoints = [],
  densityFitPoints = [], ordinate = "count", unit, sourceKey, referenceValues = [] }: InteractiveHistogramChartProps) {
  const records = bins.map((bin, index) => ({ bin, index, id: `${chartId}:bin:${index}`, value: ordinate === "count" ? bin.count : bin.density }));
  const valid = records.filter(({ bin, value }) => [bin.lower, bin.upper, bin.count, value].every(Number.isFinite) &&
    (bin.upper > bin.lower || ordinate === "count" && bin.upper === bin.lower && bin.include_lower && bin.include_upper) && bin.count >= 0 && value! >= 0);
  const fit = (ordinate === "count" ? normalFitPoints.map((point) => ({ x: point.x, value: point.expected_count })) : densityFitPoints.map((point) => ({ x: point.x, value: point.density })));
  const fitValid = fit.every((point) => Number.isFinite(point.x) && Number.isFinite(point.value) && point.value >= 0);
  const refs = referenceValues.filter((ref) => Number.isFinite(ref.value));
  const interaction = useChartItemInteraction(valid.map((item) => item.id), { sourceKey });
  const invalid = bins.length - valid.length + referenceValues.length - refs.length + (fitValid ? 0 : fit.length);
  if (!valid.length) return <div className="empty-state">{t("charts.noData")}{invalid > 0 && <p>{t("charts.invalidData", { count: invalid })}</p>}</div>;
  const range = paddedNumericRange([...valid.flatMap(({ bin }) => [bin.lower, bin.upper]), ...refs.map((ref) => ref.value), ...(fitValid ? fit.map((point) => point.x) : [])]);
  const maxValue = Math.max(0, ...valid.map((item) => item.value!), ...(fitValid ? fit.map((point) => point.value) : []));
  const yRange = { min: 0, max: maxValue > 0 ? maxValue * 1.08 : 1 };
  const { plot } = layout;
  const x = (value: number) => scaleChartValue(value, range, plot.left, plot.left + plot.width);
  const y = (value: number) => scaleChartValue(value, yRange, plot.top + plot.height, plot.top);
  const title = `${columnName} ${t("charts.histogram")}`;
  const yLabel = t(ordinate === "count" ? "charts.count" : "charts.density");
  return <ChartFrame chartId={chartId} title={title} description={title} layout={layout}
    axes={<ChartAxes layout={layout} x={{ label: columnName, unit, range }} y={{ label: yLabel, range: yRange }} />}
    footer={<>
      <ul className="chart-series-legend">{refs.map((ref) => <li key={ref.label}>{ref.label}: {formatNumber(ref.value)}</li>)}
        {fit.length > 0 && fitValid && <li>{t("charts.normalFit")}</li>}</ul>
      {invalid > 0 && <p>{t("charts.invalidData", { count: invalid })}</p>}
      <ChartItemFeedback interaction={interaction} items={valid.map(({ bin, index, id, value }) => ({ id, title: `Bin ${index + 1}`,
        details: [...binDetails(bin, index, nBasis), ...(ordinate === "density" ? [{ label: yLabel, value: formatNumber(value!) }] : [])] }))} />
    </>}>
    {valid.map(({ bin, id, index, value }) => {
      const left = x(bin.lower); const right = x(bin.upper); const top = y(value!);
      const barHeight = plot.top + plot.height - top;
      return <g key={id}>
        <rect className="histogram-bar" x={left} y={top} width={Math.max(1, right - left - 1)} height={barHeight} />
        <rect className={`chart-histogram-hit ${interaction.stateClass(id)}`} x={left} y={barHeight > 0 ? top : top - 8}
          width={Math.max(1, right - left - 1)} height={Math.max(8, barHeight)} fill="transparent"
          role="img" aria-label={`${columnName} bin ${index + 1}, ${formatNumber(bin.lower)} - ${formatNumber(bin.upper)}, ${yLabel} ${formatNumber(value!)}`}
          aria-describedby={interaction.describedBy(id)} data-selected={interaction.pinnedId === id ? "true" : "false"}
          tabIndex={interaction.tabIndexFor(id)} ref={(element) => interaction.itemRef(id, element)}
          onFocus={() => interaction.activateItem(id, "focus")} onBlur={() => interaction.clearFocus(id)}
          onPointerEnter={(event) => interaction.move(id, event)} onPointerMove={(event) => interaction.move(id, event)} onPointerLeave={() => interaction.clearHover(id)}
          onClick={() => interaction.pin(id)} onKeyDown={(event) => interaction.handleKeyDown(event, id)}>
          <title>{`${formatNumber(bin.lower)} - ${formatNumber(bin.upper)}: ${formatNumber(value!)}`}</title>
        </rect>
      </g>;
    })}
    {fit.length > 1 && fitValid && <polyline className="histogram-normal-fit-line" fill="none" points={fit.map((point) => `${x(point.x)},${y(point.value)}`).join(" ")}><title>{t("charts.normalFit")}</title></polyline>}
    {refs.map((ref) => <line key={ref.label} className="quality-limit-line" x1={x(ref.value)} x2={x(ref.value)} y1={plot.top} y2={plot.top + plot.height}><title>{`${ref.label}: ${formatNumber(ref.value)}`}</title></line>)}
  </ChartFrame>;
}
function binDetails(bin: InteractiveHistogramBin, index: number, nBasis: number) {
  return [
    { label: "Bin", value: String(index + 1) },
    { label: t("charts.binBounds"), value: `${bin.include_lower ? "[" : "("}${formatNumber(bin.lower)}, ${formatNumber(bin.upper)}${bin.include_upper ? "]" : ")"}` },
    { label: t("charts.count"), value: bin.count.toLocaleString() },
    { label: t("charts.proportion"), value: nBasis > 0 ? `${formatNumber(bin.count / nBasis * 100)}%` : "-" },
  ];
}
function formatNumber(value: number): string {
  return Number.isFinite(value) ? Number(value.toPrecision(6)).toString() : "-";
}
