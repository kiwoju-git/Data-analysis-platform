import type { RegressionPredictionResponse } from "../api";
import { useI18n } from "../i18n/LocaleProvider";
import { InteractiveScatterChart, type ChartInterval, type InteractiveScatterPoint } from "./InteractiveScatterChart";
import { paddedNumericRange } from "./chartScale";
import { integerChartTicks } from "./chartLayout";

export function PredictionIntervalChart({ rows, sourceKey, total }: { rows: RegressionPredictionResponse["rows"]; sourceKey: string; total: number }) {
  const { t, formatNumber } = useI18n();
  const intervals: ChartInterval[] = [];
  const points: InteractiveScatterPoint[] = rows.map((row) => {
    const id = `row:${row.row_index}`;
    const details = [{ label: t("charts.predictedMean"), value: formatNumber(row.predicted_mean) }];
    for (const [kind, value] of [["mean_ci", row.mean_confidence_interval], ["prediction_interval", row.prediction_interval]] as const) {
      if (value === null) continue;
      const label = `${t(kind === "mean_ci" ? "charts.meanCi" : "charts.predictionInterval")} (${formatNumber(value.level * 100)}%)`;
      intervals.push({ id: `${id}:${kind}`, pointId: id, kind, lower: value.lower, upper: value.upper, label });
      details.push({ label, value: `${formatNumber(value.lower)} - ${formatNumber(value.upper)}` });
    }
    return { id, x: row.row_index + 1, y: row.predicted_mean, title: `${t("charts.predictionRows")}: ${row.row_index + 1}`,
      ariaLabel: `${row.row_index + 1}: ${formatNumber(row.predicted_mean)}`, className: "prediction-mean-point", details };
  });
  const xRange = paddedNumericRange(points.map((point) => point.x));
  return <InteractiveScatterChart chartId="regression-prediction" sourceKey={sourceKey} title={t("charts.predictionTitle")} description={t("charts.predictionTitle")}
    annotations={[t("charts.displayCount", { shown: points.length, total })]} yFormatValue={formatNumber} emptyLabel={t("charts.noData")} points={points} intervals={intervals}
    xLabel={t("charts.predictionRows")} yLabel={t("charts.predictedMean")}
    xRange={xRange} xTicks={integerChartTicks(xRange)} yRange={paddedNumericRange(points.map((point) => point.y))} />;
}
