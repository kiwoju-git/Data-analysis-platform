import type { PearsonCorrelationResult } from "../api";
import { useI18n } from "../i18n/LocaleProvider";
import { InteractiveScatterChart } from "./InteractiveScatterChart";
import { paddedNumericRange } from "./chartScale";
import { formatChartTick } from "./chartLayout";
import { formatChartDetailValue } from "./chartNumberFormatting";

export function PearsonResultChart({ result }: { result: PearsonCorrelationResult }) {
  const { t, locale } = useI18n();
  const formatNumber = (value: number) => formatChartDetailValue(value, locale);
  return <InteractiveScatterChart chartId="pearson-scatter" title={`${result.x.display_name} / ${result.y.display_name}`}
    description={`${result.x.display_name} / ${result.y.display_name}`} annotations={[]} formatValue={(value) => formatChartTick(value, locale)} emptyLabel={t("charts.noData")}
    points={result.scatterplot.points.map((point, index) => ({ ...point, id: `display-point:${index}`,
      title: t("charts.displayPoint", { index: index + 1 }), ariaLabel: `${result.x.display_name}: ${formatNumber(point.x)}, ${result.y.display_name}: ${formatNumber(point.y)}`,
      className: "scatter-point", details: [{ label: result.x.display_name, value: formatNumber(point.x) }, { label: result.y.display_name, value: formatNumber(point.y) }] }))}
    xLabel={result.x.display_name} yLabel={result.y.display_name} xUnit={result.x.unit} yUnit={result.y.unit}
    xRange={paddedNumericRange(result.scatterplot.points.map((point) => point.x))} yRange={paddedNumericRange(result.scatterplot.points.map((point) => point.y))} />;
}
