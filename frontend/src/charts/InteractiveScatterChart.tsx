import { useId } from "react";
import { t } from "../i18n/translate";
import { ChartAxes, type AxisSpec } from "./ChartAxes";
import { ChartFrame } from "./ChartFrame";
import { ChartItemFeedback } from "./ChartItemFeedback";
import { STANDARD_CHART_LAYOUT, SQUARE_CHART_LAYOUT, axisTitle } from "./chartLayout";
import { expandNumericRange, scaleChartValue, type NumericRange } from "./chartScale";
import { useChartPointInteraction } from "./useChartPointInteraction";

export interface InteractiveScatterPoint {
  ariaLabel: string;
  className: string;
  details: Array<{ label: string; value: string }>;
  id: string;
  title: string;
  warning?: boolean;
  x: number;
  y: number;
  marker?: "circle" | "square" | "diamond";
  seriesId?: string;
  label?: string;
  labelVisibility?: "always" | "active";
}
export interface ScatterReferenceLine {
  className?: string; label: string; x1: number; x2: number; y1: number; y2: number;
  arrow?: boolean;
}
export interface ChartSeries {
  id: string; label: string; className: string; pointIds: readonly string[];
  connect: "none" | "line" | "step";
}
export interface ChartInterval {
  id: string; pointId: string; lower: number; upper: number;
  kind: "mean_ci" | "prediction_interval";
  label?: string;
}
export interface ChartBand {
  id: string; label: string; className: string;
  points: ReadonlyArray<{ x: number; lower: number; upper: number }>;
}
export interface InteractiveScatterChartProps {
  annotations: string[]; chartId: string; compact?: boolean;
  connectPoints?: "line" | "step";
  description: string; emptyLabel: string; formatValue: (value: number) => string;
  points: InteractiveScatterPoint[]; referenceLines?: ScatterReferenceLine[];
  square?: boolean; title: string; xLabel: string; xRange: NumericRange; yLabel: string; yRange: NumericRange;
  xUnit?: string | null; yUnit?: string | null;
  xTicks?: AxisSpec["ticks"]; yTicks?: AxisSpec["ticks"];
  series?: readonly ChartSeries[]; intervals?: readonly ChartInterval[]; bands?: readonly ChartBand[];
  selectedPointId?: string | null; onPointSelect?: (pointId: string) => void;
  onPointActivate?: (pointId: string) => void; onSelectionClear?: () => void; sourceKey?: string;
}

export function InteractiveScatterChart({ annotations, chartId, compact = false, connectPoints,
  description, emptyLabel, points, referenceLines = [], square = false, title,
  xLabel, xRange, yLabel, yRange, xUnit, yUnit, xTicks, yTicks, series = [], intervals = [], bands = [],
  selectedPointId, onPointSelect, onPointActivate, onSelectionClear, sourceKey,
}: InteractiveScatterChartProps) {
  const arrowId = `chart-arrow-${useId().replace(/:/g, "")}`;
  const counts = new Map<string, number>();
  points.forEach((point) => counts.set(point.id, (counts.get(point.id) ?? 0) + 1));
  const validPoints = points.filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y) && counts.get(point.id) === 1);
  const byId = new Map(validPoints.map((point) => [point.id, point]));
  const validLines = referenceLines.filter((line) => [line.x1, line.x2, line.y1, line.y2].every(Number.isFinite));
  const validIntervals = intervals.filter((interval) => byId.has(interval.pointId) && Number.isFinite(interval.lower) && Number.isFinite(interval.upper) && interval.lower <= interval.upper);
  const validBands = bands.filter((band) => band.points.length > 0 && band.points.every((point) => [point.x, point.lower, point.upper].every(Number.isFinite) && point.lower <= point.upper));
  const invalidCount = points.length - validPoints.length + referenceLines.length - validLines.length + intervals.length - validIntervals.length + bands.length - validBands.length;
  const interaction = useChartPointInteraction(validPoints.map((point) => point.id), {
    sourceKey, selectedId: selectedPointId, onSelect: onPointSelect, onActivate: onPointActivate, onClear: onSelectionClear,
  });
  const layout = square ? SQUARE_CHART_LAYOUT : STANDARD_CHART_LAYOUT;
  const { plot } = layout;
  const xDomain = expandNumericRange(xRange, [...validPoints.map((point) => point.x), ...validLines.flatMap((line) => [line.x1, line.x2]), ...validBands.flatMap((band) => band.points.map((point) => point.x))]);
  const yDomain = expandNumericRange(yRange, [...validPoints.map((point) => point.y), ...validLines.flatMap((line) => [line.y1, line.y2]), ...validIntervals.flatMap((interval) => [interval.lower, interval.upper]), ...validBands.flatMap((band) => band.points.flatMap((point) => [point.lower, point.upper]))]);
  const x = (value: number) => scaleChartValue(value, xDomain, plot.left, plot.left + plot.width);
  const y = (value: number) => scaleChartValue(value, yDomain, plot.top + plot.height, plot.top);
  const pointSeries = new Set(validPoints.map((point) => point.seriesId ?? "default"));
  const lineSeries: readonly ChartSeries[] = series.length > 0 ? series : connectPoints && pointSeries.size === 1
    ? [{ id: "default", label: title, className: "interactive-data-line", pointIds: validPoints.map((point) => point.id), connect: connectPoints }] : [];
  if (validPoints.length === 0) return <div className="empty-state">{emptyLabel}{invalidCount > 0 && <p>{t("charts.invalidData", { count: invalidCount })}</p>}</div>;
  const labelBoxes: Array<{ left: number; top: number; right: number; bottom: number }> = [];
  const labels = validPoints.filter((point) => point.label && (point.labelVisibility === "always" || interaction.activeItem?.id === point.id || interaction.pinnedId === point.id))
    .sort((a, b) => Number(b.id === interaction.activeItem?.id || b.id === interaction.pinnedId) - Number(a.id === interaction.activeItem?.id || a.id === interaction.pinnedId))
    .flatMap((point) => {
      const text = point.label!.length > 24 ? `${point.label!.slice(0, 21)}...` : point.label!;
      const width = Math.min(plot.width, [...text].reduce((sum, char) => sum + (char.charCodeAt(0) > 127 ? 12 : 7), 0));
      const left = Math.max(plot.left, Math.min(plot.left + plot.width - width, x(point.x) + (point.x > (xDomain.min + xDomain.max) / 2 ? -width - 7 : 7)));
      const top = Math.max(plot.top, y(point.y) - 23);
      const box = { left, top, right: left + width, bottom: top + 16 };
      if (labelBoxes.some((other) => box.left < other.right + 4 && box.right + 4 > other.left && box.top < other.bottom + 2 && box.bottom + 2 > other.top)) return [];
      labelBoxes.push(box);
      return [{ point, text, left, top }];
    });
  return <ChartFrame chartId={chartId} title={title}
    description={`${description}; ${axisTitle(xLabel, xUnit)}; ${axisTitle(yLabel, yUnit)}`}
    layout={layout} className={compact ? "chart-frame-compact" : ""}
    axes={<ChartAxes layout={layout} x={{ label: xLabel, unit: xUnit, range: xDomain, ticks: xTicks }} y={{ label: yLabel, unit: yUnit, range: yDomain, ticks: yTicks }} />}
    overlay={labels.map(({ point, text, left, top }) => <text key={point.id} className="chart-vector-label" x={left} y={top + 12}
      textAnchor="start"><title>{point.label}</title>{text}</text>)}
    footer={<>
      {(series.length > 0 || validBands.length > 0 || validIntervals.length > 0 || validLines.some((line) => !line.arrow)) && <ul className="chart-series-legend">
        {series.map((item) => {
          const point = item.pointIds.map((id) => byId.get(id)).find(Boolean);
          return <li key={item.id}><svg aria-hidden="true" viewBox="0 0 24 12">
            {item.connect !== "none" && <line className={`interactive-data-line ${item.className}`} x1={0} x2={24} y1={6} y2={6} />}
            {point?.marker === "diamond" ? <polygon className={point.className} points="12,2 16,6 12,10 8,6" />
              : point?.marker === "square" ? <rect className={point.className} x={9} y={3} width={6} height={6} />
                : <circle className={point?.className ?? item.className} cx={12} cy={6} r={3} />}
          </svg>{item.label}</li>;
        })}
        {validBands.map((band) => <li key={band.id}>{band.label}</li>)}
        {[...new Map(validLines.filter((line) => !line.arrow).map((line) => [line.label, line])).values()].map((line) =>
          <li key={`reference:${line.label}`}><svg aria-hidden="true" viewBox="0 0 24 12"><line className={`reference-line ${line.className ?? ""}`} x1={0} x2={24} y1={6} y2={6} /></svg>{line.label}</li>)}
        {[...new Set(validIntervals.map((interval) => interval.label ?? t(interval.kind === "mean_ci" ? "charts.meanCi" : "charts.predictionInterval")))].map((label) => <li key={label}>{label}</li>)}
      </ul>}
      {invalidCount > 0 && <p className="notice-box notice-warning">{t("charts.invalidData", { count: invalidCount })}</p>}
      <div className="chart-annotations">{annotations.map((annotation) => <span key={annotation}>{annotation}</span>)}</div>
      <ChartItemFeedback interaction={interaction} items={validPoints} />
    </>}>
    <defs><marker id={arrowId} viewBox="0 0 10 10" refX={9} refY={5} markerWidth={5} markerHeight={5} orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke" /></marker></defs>
    {validBands.map((band) => <path key={band.id} className={`chart-interval-band ${band.className}`} d={`${band.points.map((point, index) => `${index === 0 ? "M" : "L"} ${x(point.x)} ${y(point.upper)}`).join(" ")} ${[...band.points].reverse().map((point) => `L ${x(point.x)} ${y(point.lower)}`).join(" ")} Z`}><title>{band.label}</title></path>)}
    {validLines.map((line, index) => <g key={`${line.label}-${index}`}><line className={`reference-line ${line.className ?? ""}`} x1={x(line.x1)} x2={x(line.x2)} y1={y(line.y1)} y2={y(line.y2)} markerEnd={line.arrow ? `url(#${arrowId})` : undefined} /><title>{line.label}</title></g>)}
    {lineSeries.filter((item) => item.connect !== "none").map((item) => <path key={item.id} className={`interactive-data-line ${item.className}`} d={pointPath(item.pointIds.map((id) => byId.get(id)), x, y, item.connect === "step" ? "step" : "line")} />)}
    {validIntervals.map((interval) => {
      const at = x(byId.get(interval.pointId)!.x);
      return <g key={interval.id} className={`chart-interval chart-interval-${interval.kind}`} data-interval-kind={interval.kind}>
        <line x1={at} x2={at} y1={y(interval.lower)} y2={y(interval.upper)} />
        <line x1={at - 4} x2={at + 4} y1={y(interval.lower)} y2={y(interval.lower)} />
        <line x1={at - 4} x2={at + 4} y1={y(interval.upper)} y2={y(interval.upper)} />
      </g>;
    })}
    {validPoints.map((point) => {
      const cx = x(point.x); const cy = y(point.y);
      const props = {
        "aria-label": point.ariaLabel, "aria-describedby": interaction.describedBy(point.id),
        className: `${point.className} ${interaction.stateClass(point.id)}`,
        "data-selected": interaction.pinnedId === point.id ? "true" : "false",
        onBlur: () => interaction.clearFocus(point.id), onClick: () => interaction.pin(point.id),
        onFocus: () => interaction.activateItem(point.id, "focus"),
        onKeyDown: (event: React.KeyboardEvent<SVGElement>) => interaction.handleKeyDown(event, point.id),
        onPointerEnter: (event: React.PointerEvent<SVGElement>) => interaction.move(point.id, event),
        onPointerMove: (event: React.PointerEvent<SVGElement>) => interaction.move(point.id, event),
        onPointerLeave: () => interaction.clearHover(point.id),
        ref: (element: SVGElement | null) => interaction.itemRef(point.id, element),
        role: "img", tabIndex: interaction.tabIndexFor(point.id),
      };
      return <g key={point.id}>
        {point.warning && <circle className="chart-warning-ring" cx={cx} cy={cy} r={6} />}
        {point.marker === "square" ? <rect {...props} x={cx - 3.5} y={cy - 3.5} width={7} height={7}><title>{point.ariaLabel}</title></rect>
          : point.marker === "diamond" ? <polygon {...props} points={`${cx},${cy - 4.5} ${cx + 4.5},${cy} ${cx},${cy + 4.5} ${cx - 4.5},${cy}`}><title>{point.ariaLabel}</title></polygon>
            : <circle {...props} cx={cx} cy={cy} r={3.5}><title>{point.ariaLabel}</title></circle>}
      </g>;
    })}
  </ChartFrame>;
}

function pointPath(points: readonly (InteractiveScatterPoint | undefined)[], x: (value: number) => number, y: (value: number) => number, mode: "line" | "step"): string {
  const parts: string[] = [];
  let previousY: number | null = null;
  for (const point of points) {
    if (!point) { previousY = null; continue; }
    if (mode === "step" && previousY !== null) parts.push(`L ${x(point.x)} ${previousY}`);
    parts.push(`${previousY === null ? "M" : "L"} ${x(point.x)} ${y(point.y)}`);
    previousY = y(point.y);
  }
  return parts.join(" ");
}
