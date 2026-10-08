import type { AttributeControlChartResult, IndividualsChartSeries, MovingRangeChartSeries, RunChartResult, SubgroupChartSeries } from "../api";
import { useI18n } from "../i18n/LocaleProvider";
import { InteractiveScatterChart, type InteractiveScatterPoint, type ScatterReferenceLine } from "./InteractiveScatterChart";
import { paddedNumericRange, type NumericRange } from "./chartScale";

const number = (value: number | undefined) => value !== undefined && Number.isFinite(value) ? Number(value.toPrecision(7)).toString() : "-";
const limitLines = (series: { lcl: number; center_line: number; ucl: number }, range: NumericRange): ScatterReferenceLine[] =>
  [["LCL", series.lcl], ["CL", series.center_line], ["UCL", series.ucl]].map(([label, value]) => ({
    label: `${label}: ${number(Number(value))}`, x1: range.min, x2: range.max, y1: Number(value), y2: Number(value),
    className: label === "CL" ? "quality-center-line" : "quality-limit-line",
  }));

export function IndividualsResultChart({ series, label, chartKind, unit }: {
  series: IndividualsChartSeries | MovingRangeChartSeries; label: string; chartKind: "individuals" | "moving_range"; unit: string | null;
}) {
  const { t } = useI18n();
  const points: InteractiveScatterPoint[] = series.points.map((point) => ({
    id: `${chartKind}:${point.position}`, x: point.position, y: point.value, title: `${label}: ${point.position}`,
    ariaLabel: `${label}: ${point.position}, ${number(point.value)}, ${point.signal_codes.join(", ")}`,
    marker: point.signal_codes.some((code) => code.includes("beyond_3_sigma") || code.includes("mr_beyond_ucl")) ? "square" : point.signal_codes.length ? "diamond" : "circle",
    className: point.signal_codes.length ? "quality-signal-point" : "scatter-point",
    details: [{ label, value: number(point.value) }, { label: t("charts.canonicalPosition"), value: String(point.canonical_position) },
      { label: t("charts.signals"), value: point.signal_codes.join(", ") || "-" }],
  }));
  const xRange = paddedNumericRange(points.map((point) => point.x));
  return <InteractiveScatterChart chartId={`quality-${chartKind}`} sourceKey={chartKind} title={label} description={t("charts.controlSignals")}
    annotations={[t("charts.displayCount", { shown: points.length, total: series.point_count })]} points={points} connectPoints="line"
    formatValue={number} emptyLabel={t("charts.noData")} xLabel={t(series.x_axis === "order_rank" ? "charts.orderRank" : "charts.canonicalPosition")}
    yLabel={chartKind === "moving_range" ? t("charts.movingRange") : label} yUnit={unit} xRange={xRange} yRange={paddedNumericRange(points.map((point) => point.y))}
    referenceLines={limitLines(series, xRange)} />;
}

export function SubgroupResultChart({ series, label, unit, kind }: { series: SubgroupChartSeries; label: string; unit: string | null; kind: string }) {
  const { t } = useI18n();
  const points: InteractiveScatterPoint[] = series.points.map((point) => ({ id: `${kind}:${point.position}`, x: point.position, y: point.value,
    title: point.subgroup_label, ariaLabel: `${point.subgroup_label}: ${number(point.value)}`, marker: point.signal_codes.length ? "square" : "circle",
    className: point.signal_codes.length ? "quality-signal-point" : "scatter-point",
    details: [{ label, value: number(point.value) }, { label: "N", value: String(point.n) },
      { label: t("charts.canonicalPosition"), value: `${point.first_canonical_position} - ${point.last_canonical_position}` },
      { label: t("charts.signals"), value: point.signal_codes.join(", ") || "-" }],
  }));
  const xRange = paddedNumericRange(points.map((point) => point.x));
  return <InteractiveScatterChart chartId={`quality-${kind}`} sourceKey={kind} title={label} description={label} points={points} connectPoints="line"
    annotations={[t("charts.displayCount", { shown: points.length, total: series.point_count })]} formatValue={number} emptyLabel={t("charts.noData")}
    xLabel={t("charts.subgroupOrder")} yLabel={label} yUnit={unit} xRange={xRange} yRange={paddedNumericRange(points.map((point) => point.y))}
    referenceLines={limitLines(series, xRange)} />;
}

export function RunResultChart({ result }: { result: {
  value: Pick<RunChartResult["value"], "display_name" | "unit">;
  center_line: number;
  chart: Pick<RunChartResult["chart"], "points" | "x_axis">;
} }) {
  const { t } = useI18n();
  const points: InteractiveScatterPoint[] = result.chart.points.map((point) => ({ id: `run:${point.position}`, x: point.position, y: point.value,
    title: `${point.position}`, ariaLabel: `${point.position}: ${number(point.value)}, ${point.relative_to_center}`,
    marker: point.signal_codes.length ? "square" : "circle", className: point.signal_codes.length ? "quality-signal-point" : `run-point-${point.relative_to_center}`,
    details: [{ label: result.value.display_name, value: number(point.value) }, { label: t("charts.canonicalPosition"), value: number(point.canonical_position) },
      { label: t("charts.relativeToCenter"), value: t(point.relative_to_center === "tie" ? "charts.equal" : `charts.${point.relative_to_center}`) }, { label: t("charts.signals"), value: point.signal_codes.join(", ") || "-" }],
  }));
  const xRange = paddedNumericRange(points.map((point) => point.x));
  return <InteractiveScatterChart chartId="quality-run" title={`${result.value.display_name} Run Chart`} description={t("charts.runMedian")}
    annotations={[]} formatValue={number} emptyLabel={t("charts.noData")} points={points} connectPoints="line"
    xLabel={t(result.chart.x_axis === "order_rank" ? "charts.orderRank" : "charts.canonicalPosition")} yLabel={result.value.display_name} yUnit={result.value.unit}
    xRange={xRange} yRange={paddedNumericRange(points.map((point) => point.y))}
    referenceLines={[{ label: `${t("charts.runMedian")}: ${number(result.center_line)}`, x1: xRange.min, x2: xRange.max, y1: result.center_line, y2: result.center_line, className: "quality-center-line" }]} />;
}

export function AttributeResultChart({ result }: { result: Pick<AttributeControlChartResult, "chart_type" | "center_line" | "limit_set_dependency"> & {
  chart: Pick<AttributeControlChartResult["chart"], "points" | "y_axis" | "point_count">;
} }) {
  const { t } = useI18n();
  const label = t(`charts.attribute.${result.chart.y_axis}`);
  const points: InteractiveScatterPoint[] = result.chart.points.map((point) => ({ id: `${result.chart_type}:${point.position}`, x: point.position, y: point.value,
    title: `${result.chart_type.toUpperCase()}: ${point.position}`, ariaLabel: `${point.position}: ${number(point.value)}, LCL ${number(point.lcl)}, UCL ${number(point.ucl)}`,
    className: point.signal_codes.length ? "quality-signal-point" : "scatter-point", marker: "circle",
    details: [{ label, value: number(point.value) }, { label: t("charts.canonicalPosition"), value: String(point.canonical_position) },
      { label: t("charts.count"), value: number(point.count) }, { label: t("charts.denominator"), value: number(point.denominator ?? undefined) },
      { label: "LCL", value: number(point.lcl) }, { label: "UCL", value: number(point.ucl) },
      { label: t("charts.signals"), value: point.signal_codes.join(", ") || "-" },
      ...(result.limit_set_dependency ? [{ label: t("charts.frozenLimits"), value: result.limit_set_dependency.limit_set_id }] : [])],
  }));
  const xRange = paddedNumericRange(points.map((point) => point.x));
  const lines: ScatterReferenceLine[] = [{ label: `CL: ${number(result.center_line)}`, className: "quality-center-line", x1: xRange.min, x2: xRange.max, y1: result.center_line, y2: result.center_line }];
  for (const key of ["lcl", "ucl"] as const) {
    result.chart.points.forEach((point, index) => {
      const next = result.chart.points[index + 1];
      if (next) lines.push({ label: key.toUpperCase(), className: "quality-limit-line", x1: point.position, x2: next.position, y1: point[key], y2: next[key] });
      else if (result.chart.points.length === 1) lines.push({ label: key.toUpperCase(), className: "quality-limit-line", x1: xRange.min, x2: xRange.max, y1: point[key], y2: point[key] });
    });
  }
  return <InteractiveScatterChart chartId={`quality-${result.chart_type}`} title={`${result.chart_type.toUpperCase()} Chart`} description={label}
    annotations={[t("charts.displayCount", { shown: points.length, total: result.chart.point_count })]} points={points} connectPoints="line" formatValue={number} emptyLabel={t("charts.noData")}
    xLabel={t("charts.canonicalPosition")} yLabel={label} xRange={xRange} yRange={paddedNumericRange(points.map((point) => point.y))} referenceLines={lines} />;
}
