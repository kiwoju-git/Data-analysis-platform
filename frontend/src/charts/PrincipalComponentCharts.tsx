import type { PrincipalComponentsResult } from "../api";
import { useI18n } from "../i18n/LocaleProvider";
import { InteractiveScatterChart, type InteractiveScatterPoint } from "./InteractiveScatterChart";
import { InteractiveHorizontalBarChart } from "./InteractiveHorizontalBarChart";
import { paddedNumericRange } from "./chartScale";
import { pcaBiplotModel, pcaLoadingModel, pcaOutlierModel, pcaScoreModel, pcaSymmetricRange } from "./pcaChartModels";

const number = (value: number) => Number.isFinite(value) ? Number(value.toPrecision(7)).toString() : "-";
type ResultProps = { result: PrincipalComponentsResult; analysisId: string };
type PairProps = ResultProps & { xComponent: number; yComponent: number | null };

export function ComponentPairSelectors({ components, onX, onY, x, y }: { components: number[]; onX: (value: number) => void; onY: (value: number) => void; x: number; y: number | null }) {
  if (components.length < 2) return null;
  return <div className="pca-component-pair"><select aria-label="PC X" value={x} onChange={(event) => onX(Number(event.currentTarget.value))}>{components.map((component) => <option disabled={component === y} key={component} value={component}>PC{component}</option>)}</select><select aria-label="PC Y" value={y ?? undefined} onChange={(event) => onY(Number(event.currentTarget.value))}>{components.map((component) => <option disabled={component === x} key={component} value={component}>PC{component}</option>)}</select></div>;
}

export function ScreePlot({ result, analysisId }: ResultProps) {
  const { t } = useI18n();
  const points: InteractiveScatterPoint[] = result.eigenanalysis.map((row) => ({ id: `component:${row.component}`, x: row.component, y: row.eigenvalue,
    title: `PC${row.component}`, ariaLabel: `PC${row.component}, ${number(row.eigenvalue)}`, className: row.selected ? "pca-point is-selected" : "pca-point",
    details: [{ label: t("pca.eigenvalue"), value: number(row.eigenvalue) }, { label: t("pca.proportion"), value: number(row.proportion) },
      { label: t("pca.cumulativeProportion"), value: number(row.cumulative_proportion) }, { label: t("pca.selected"), value: t(row.selected ? "pca.yes" : "pca.no") }] }));
  return <InteractiveScatterChart chartId="pca-scree" sourceKey={`${analysisId}:scree`} title={t("pca.screePlot")} description={t("pca.screePlotDesc")}
    annotations={[]} emptyLabel={t("charts.noData")} formatValue={number} points={points} connectPoints="line"
    xLabel={t("pca.component")} yLabel={t("pca.eigenvalue")}
    xRange={paddedNumericRange(points.map((point) => point.x))} yRange={paddedNumericRange([0, ...points.map((point) => point.y)])}
    xTicks={result.eigenanalysis.map((row) => ({ value: row.component, label: String(row.component) }))} />;
}

export function ScorePlot({ result, analysisId, xComponent, yComponent }: PairProps) {
  const { t } = useI18n();
  const axis = (component: number) => t("pca.scoreAxis", { component, percent: number((result.eigenanalysis.find((row) => row.component === component)?.proportion ?? NaN) * 100) });
  const points: InteractiveScatterPoint[] = pcaScoreModel(result, xComponent, yComponent).map((point) => ({ ...point,
    title: `${t("pca.row")} ${point.rowNumber}`, ariaLabel: `${t("pca.row")} ${point.rowNumber}: ${number(point.x)}, ${number(point.y)}`,
    className: point.outlier ? "pca-point is-outlier" : "pca-point", warning: point.outlier,
    details: [{ label: t("pca.row"), value: String(point.rowNumber) }, { label: yComponent === null ? t("pca.row") : axis(xComponent), value: number(point.x) },
      { label: axis(yComponent ?? xComponent), value: number(point.y) }, { label: t("pca.mahalanobis"), value: number(point.distanceSquared) }, { label: t("pca.outlier"), value: t(point.outlier ? "pca.yes" : "pca.no") }] }));
  const range = pcaSymmetricRange(points.flatMap((point) => [point.x, point.y]));
  return <InteractiveScatterChart chartId="pca-score" sourceKey={`${analysisId}:score:${xComponent}:${yComponent}`} title={t("pca.scorePlot")}
    description={t("pca.scorePlotDesc")} annotations={[t("charts.displayCount", { shown: points.length, total: result.sample.n_used })]}
    emptyLabel={t("charts.noData")} formatValue={number} points={points} square={yComponent !== null}
    xLabel={yComponent === null ? t("pca.row") : axis(xComponent)} yLabel={axis(yComponent ?? xComponent)}
    xRange={yComponent === null ? paddedNumericRange(points.map((point) => point.x)) : range} yRange={yComponent === null ? paddedNumericRange(points.map((point) => point.y)) : range} />;
}

export function LoadingPlot({ result, analysisId, xComponent, yComponent }: PairProps) {
  const { t } = useI18n();
  const label = (component: number) => `PC${component} loading`;
  if (yComponent === null) return <InteractiveHorizontalBarChart chartId="pca-loading-1d" sourceKey={`${analysisId}:loading:${xComponent}`}
    title={t("pca.loadingPlot")} description={t("pca.loadings")} xLabel={label(xComponent)} yLabel={t("pca.variable")}
    items={result.loadings.map((row) => ({ id: row.column_id, label: row.display_name, title: row.display_name, value: row.values[xComponent - 1],
      details: [{ label: label(xComponent), value: number(row.values[xComponent - 1]) }] }))} />;
  const points: InteractiveScatterPoint[] = pcaLoadingModel(result, xComponent, yComponent).map((point) => ({ ...point, title: point.label,
    ariaLabel: `${point.label}: ${number(point.x)}, ${number(point.y)}`, className: "pca-point", labelVisibility: result.loadings.length <= 12 ? "always" : "active",
    details: [{ label: label(xComponent), value: number(point.x) }, { label: label(yComponent), value: number(point.y) }] }));
  const range = pcaSymmetricRange(points.flatMap((point) => [point.x, point.y]));
  return <InteractiveScatterChart chartId="pca-loading" sourceKey={`${analysisId}:loading:${xComponent}:${yComponent}`} title={t("pca.loadingPlot")}
    description={t("pca.loadings")} annotations={[]} emptyLabel={t("charts.noData")} formatValue={number} points={points} square
    xLabel={label(xComponent)} yLabel={label(yComponent)} xRange={range} yRange={range} />;
}

export function Biplot({ result, analysisId, xComponent, yComponent }: PairProps) {
  const { t } = useI18n();
  if (yComponent === null) return <p className="field-help">{t("pca.biplotNeedsTwo")}</p>;
  const model = pcaBiplotModel(result, xComponent, yComponent);
  const scores: InteractiveScatterPoint[] = model.rawScorePoints.map((point) => ({ ...point, title: `${t("pca.row")} ${point.rowNumber}`,
    label: String(point.rowNumber), labelVisibility: "active", className: point.outlier ? "pca-point is-outlier" : "pca-point", warning: point.outlier,
    ariaLabel: `${t("pca.row")} ${point.rowNumber}: ${number(point.x)}, ${number(point.y)}`,
    details: [{ label: `PC${xComponent} score`, value: number(point.x) }, { label: `PC${yComponent} score`, value: number(point.y) }] }));
  const vectors: InteractiveScatterPoint[] = model.displayedLoadingVectors.map((point, index) => ({ ...point, title: point.label,
    labelVisibility: result.loadings.length <= 12 ? "always" : "active", className: "pca-loading-point", marker: "diamond",
    ariaLabel: `${point.label}: ${number(model.rawLoadingVectors[index].x)}, ${number(model.rawLoadingVectors[index].y)}`,
    details: [{ label: `PC${xComponent} loading`, value: number(model.rawLoadingVectors[index].x) }, { label: `PC${yComponent} loading`, value: number(model.rawLoadingVectors[index].y) },
      { label: t("pca.loadingDisplayScale"), value: number(model.loadingDisplayScale) }] }));
  const points = [...scores, ...vectors]; const range = pcaSymmetricRange(points.flatMap((point) => [point.x, point.y]));
  return <InteractiveScatterChart chartId="pca-biplot" sourceKey={`${analysisId}:biplot:${xComponent}:${yComponent}`} title={t("pca.biplot")} description={t("pca.biplotScaleNote")}
    annotations={[t("pca.biplotScaleNote"), `${t("pca.loadingDisplayScale")}: ${number(model.loadingDisplayScale)}`]}
    emptyLabel={t("charts.noData")} formatValue={number} points={points} square xLabel={`PC${xComponent} score`} yLabel={`PC${yComponent} score`} xRange={range} yRange={range}
    referenceLines={vectors.map((point) => ({ label: point.title, className: "pca-loading-vector", x1: 0, y1: 0, x2: point.x, y2: point.y, arrow: true }))} />;
}

export function OutlierPlot({ result, analysisId }: ResultProps) {
  const { t } = useI18n();
  const points: InteractiveScatterPoint[] = pcaOutlierModel(result).map((point) => ({ ...point, title: `${t("pca.row")} ${point.x}`,
    ariaLabel: `${t("pca.row")} ${point.x}, ${number(point.y)}`, className: point.outlier ? "pca-point is-outlier" : "pca-point", warning: point.outlier,
    details: [{ label: t("pca.row"), value: String(point.x) }, { label: t("pca.mahalanobis"), value: number(point.y) }, { label: "Alpha", value: number(result.outliers.alpha) }] }));
  const xRange = paddedNumericRange(points.map((point) => point.x));
  return <InteractiveScatterChart chartId="pca-outliers" sourceKey={`${analysisId}:outliers`} title={t("pca.outlierPlot")} description={t("pca.outlierPlotDesc")}
    annotations={[result.outliers.method, `Alpha: ${number(result.outliers.alpha)}`]} emptyLabel={t("charts.noData")} formatValue={number} points={points}
    xLabel={t("pca.row")} yLabel={t("pca.mahalanobis")} xRange={xRange} yRange={paddedNumericRange([0, result.outliers.reference_value, ...points.map((point) => point.y)])}
    referenceLines={[{ label: `${result.outliers.method}; Alpha ${number(result.outliers.alpha)}`, x1: xRange.min, x2: xRange.max, y1: result.outliers.reference_value, y2: result.outliers.reference_value }]} />;
}
