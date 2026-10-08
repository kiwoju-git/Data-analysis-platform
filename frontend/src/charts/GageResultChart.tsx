import type { GageRunChartResult } from "../api";
import { useI18n } from "../i18n/LocaleProvider";
import { InteractiveScatterChart } from "./InteractiveScatterChart";
import { paddedNumericRange } from "./chartScale";

export function GageResultChart({ result }: { result: GageRunChartResult }) {
  const { t, formatNumber } = useI18n();
  const points = result.chart.points.map((point) => ({ id: `run:${point.position}:${point.canonical_position}`,
    x: point.position, y: point.value, seriesId: `operator:${point.operator_index}`, title: `Run ${point.position}`,
    markerRadius: point.replicate_index % 2 === 0 ? 4.6 : 3.4,
    className: `chart-point chart-series-${(point.operator_index - 1) % 6}`, ariaLabel: `Run ${point.position}: ${formatNumber(point.value)}`,
    details: [{ label: result.columns.measurement.display_name, value: formatNumber(point.value) },
      { label: t("charts.partIndex"), value: String(point.part_index) }, { label: t("charts.operatorIndex"), value: String(point.operator_index) },
      { label: t("charts.replicateIndex"), value: String(point.replicate_index) }, { label: t("charts.canonicalPosition"), value: String(point.canonical_position) }],
  }));
  const xRange = paddedNumericRange(points.map((point) => point.x));
  return <InteractiveScatterChart chartId="gage-run" title="Gage Run Chart" description="Gage Run Chart"
    points={points} annotations={[t("charts.displayCount", { shown: points.length, total: result.chart.point_count })]}
    emptyLabel={t("charts.noData")} formatValue={formatNumber} xLabel={t("charts.runOrder")} yLabel={result.columns.measurement.display_name} yUnit={result.columns.measurement.unit}
    xRange={xRange} yRange={paddedNumericRange(points.map((point) => point.y))}
    series={[...new Set(points.map((point) => point.seriesId))].map((id) => ({ id, label: `${t("charts.operatorIndex")}: ${id.split(":")[1]}`, className: points.find((point) => point.seriesId === id)!.className,
      pointIds: points.filter((point) => point.seriesId === id).map((point) => point.id), connect: "none" }))}
    referenceLines={[{ label: `${t("charts.mean")}: ${formatNumber(result.summary.mean)}`, x1: xRange.min, x2: xRange.max, y1: result.summary.mean, y2: result.summary.mean }]} />;
}
