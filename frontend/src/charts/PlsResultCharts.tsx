import type { PlsRegressionResult } from "../api";
import { useI18n } from "../i18n/LocaleProvider";
import { InteractiveScatterChart, type InteractiveScatterPoint } from "./InteractiveScatterChart";
import { InteractiveHorizontalBarChart } from "./InteractiveHorizontalBarChart";
import { paddedNumericRange } from "./chartScale";
import { plsLoadingModel, plsResponseModel, plsScoreModel, plsSelectionModel } from "./plsChartModels";

type Props = { result: PlsRegressionResult; analysisId: string };
const number = (value: number) => Number.isFinite(value) ? Number(value.toPrecision(7)).toString() : "-";

export function LineMetricChart({ result, analysisId }: Props) {
  const { t } = useI18n();
  const points: InteractiveScatterPoint[] = plsSelectionModel(result).map((point) => ({ ...point,
    title: `${t("pls.components")} ${point.x}`, ariaLabel: `${point.seriesId === "training" ? t("pls.trainingR") : t("pls.cvPredictedR")} ${number(point.y)}`,
    className: point.seriesId === "training" ? "pls-training-point" : "pls-cv-point",
    marker: point.seriesId === "training" ? "circle" : "diamond",
    details: [{ label: point.seriesId === "training" ? t("pls.trainingR") : t("pls.cvPredictedR"), value: number(point.y) },
      { label: t("pls.press"), value: number(point.row.press) }, { label: t("pls.cvRmse"), value: number(point.row.cv_rmse) },
      { label: t("pls.selected"), value: t(point.x === result.component_selection.selected_components ? "pls.yes" : "pls.no") }] }));
  const yRange = paddedNumericRange(points.map((point) => point.y));
  return <InteractiveScatterChart chartId="pls-selection" sourceKey={`${analysisId}:selection`} title={t("pls.modelSelectionPlot")}
    description={t("pls.modelSelectionPlotDesc")} annotations={[]} emptyLabel={t("charts.noData")} formatValue={number} points={points}
    xLabel={t("pls.components")} yLabel="R²" xRange={paddedNumericRange(points.map((point) => point.x))} yRange={yRange}
    xTicks={result.component_selection.rows.map((row) => ({ value: row.components, label: String(row.components) }))}
    series={[{ id: "training", label: t("pls.trainingR"), className: "pls-training-line", connect: "line", pointIds: points.filter((point) => point.seriesId === "training").map((point) => point.id) },
      { id: "cv", label: t("pls.cvPredictedR"), className: "pls-cv-line", connect: "line", pointIds: points.filter((point) => point.seriesId === "cv").map((point) => point.id) }]}
    referenceLines={[{ label: t("pls.selected"), className: "pls-selected-component-line", x1: result.component_selection.selected_components, x2: result.component_selection.selected_components, y1: yRange.min, y2: yRange.max }]} />;
}

export function ResponsePlot({ result, analysisId }: Props) {
  const { t } = useI18n();
  const points: InteractiveScatterPoint[] = plsResponseModel(result).map((point) => ({ ...point,
    title: `${t("pls.row")} ${point.rowIndex + 1}`, ariaLabel: `${t("pls.row")} ${point.rowIndex + 1}: ${number(point.x)}, ${number(point.y)}`,
    className: point.seriesId === "fitted" ? "pls-training-point" : "pls-cv-point", marker: point.seriesId === "fitted" ? "circle" : "diamond",
    details: [{ label: t("pls.observed"), value: number(point.x) }, { label: t(point.seriesId === "fitted" ? "pls.fitted" : "pls.cvFitted"), value: number(point.y) },
      { label: t(point.seriesId === "fitted" ? "pls.residual" : "pls.cvResidual"), value: number(point.residual) }] }));
  const range = paddedNumericRange(points.flatMap((point) => [point.x, point.y]));
  return <InteractiveScatterChart chartId="pls-response" sourceKey={`${analysisId}:response`} title={t("pls.responsePlot")} description={t("pls.responsePlotDesc")}
    annotations={[t("charts.displayCount", { shown: result.diagnostics.points.length, total: result.diagnostics.point_count_total })]}
    emptyLabel={t("charts.noData")} formatValue={number} points={points} xRange={range} yRange={range}
    xLabel={`${t("pls.observed")} ${result.response.display_name}`} yLabel={`${t("pls.predictedValue")} ${result.response.display_name}`} xUnit={result.response.unit} yUnit={result.response.unit}
    referenceLines={[{ label: "y = x", x1: range.min, y1: range.min, x2: range.max, y2: range.max }]}
    series={[{ id: "fitted", label: t("pls.fitted"), className: "pls-training-point", connect: "none", pointIds: points.filter((point) => point.seriesId === "fitted").map((point) => point.id) },
      { id: "cv", label: t("pls.cvFitted"), className: "pls-cv-point", connect: "none", pointIds: points.filter((point) => point.seriesId === "cv").map((point) => point.id) }]} />;
}

export function ScorePlot({ result, analysisId }: Props) {
  const { t } = useI18n();
  const model = plsScoreModel(result);
  const xLabel = model.dimensions >= 2 ? "PLS t1" : t("pls.row");
  const yLabel = model.dimensions >= 2 ? "PLS t2" : "PLS t1";
  const points: InteractiveScatterPoint[] = model.points.map((point) => ({ ...point, title: `${t("pls.row")} ${point.rowIndex + 1}`,
    ariaLabel: `${t("pls.row")} ${point.rowIndex + 1}: ${number(point.x)}, ${number(point.y)}`, className: "pls-score-point",
    details: [{ label: xLabel, value: number(point.x) }, { label: yLabel, value: number(point.y) }] }));
  return <InteractiveScatterChart chartId="pls-scores" sourceKey={`${analysisId}:scores`} title={t("pls.scores")} description={t("pls.scoresPlotDesc")}
    annotations={[t("charts.displayCount", { shown: points.length, total: result.sample.n_used })]} emptyLabel={t("charts.noData")} formatValue={number} points={points}
    xLabel={xLabel} yLabel={yLabel} xRange={paddedNumericRange(points.map((point) => point.x))} yRange={paddedNumericRange(points.map((point) => point.y))} />;
}

export function LoadingPlot({ component, result, analysisId }: Props & { component: number }) {
  const { t } = useI18n();
  const title = t("pls.loadingPlotTitle", { component });
  return <InteractiveHorizontalBarChart chartId="pls-loading" sourceKey={`${analysisId}:loading:${component}`} title={title} description={t("pls.loadingPlotDesc")}
    xLabel={title} yLabel={t("pls.predictor")} pageSize={12}
    items={plsLoadingModel(result, component).map((item) => ({ ...item, title: item.label,
      className: item.value >= 0 ? "pls-loading-positive" : "pls-loading-negative", details: [{ label: title, value: number(item.value) }] }))} />;
}
