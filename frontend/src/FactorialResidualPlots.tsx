import { useId, useState } from "react";
import type { DoeFinalModelWorkflow } from "./api/types/doeModelWorkflow";
import { InteractiveHistogramChart } from "./charts/InteractiveHistogramChart";
import { InteractiveScatterChart, type ScatterReferenceLine } from "./charts/InteractiveScatterChart";
import { paddedNumericRange } from "./charts/chartScale";
import { factorialNumber } from "./doe/factorialWorkflowPresentation";
import { t } from "./i18n/translate";

export function FactorialResidualPlots({ plots }: { plots: DoeFinalModelWorkflow["residual_plots"] }) {
  const id = useId().replace(/:/g, "");
  const [mode, setMode] = useState<"raw" | "standardized">("raw");
  const view = plots[mode];
  const label = t(mode === "raw" ? "doe.residual.raw" : "doe.residual.standardized");
  function scatter(kind: "qq" | "fits" | "order") {
    const data = kind === "qq" ? view.qq_points.map((point) => ({ ...point, x: point.theoretical_quantile, y: point.residual }))
      : view.points.map((point) => ({ ...point, x: kind === "fits" ? point.fitted : point.run_order, y: point.residual }));
    const range = paddedNumericRange(data.map((point) => point.x));
    const lines: ScatterReferenceLine[] = kind === "qq" ? (view.reference_line === null ? [] : [{ label: "Normal reference", x1: range.min, x2: range.max,
      y1: view.reference_line.intercept + range.min * view.reference_line.slope, y2: view.reference_line.intercept + range.max * view.reference_line.slope }])
      : [{ label: "0", x1: range.min, x2: range.max, y1: 0, y2: 0 }];
    return <InteractiveScatterChart chartId={`${id}-${mode}-${kind}`} title={t(`doe.residual.${kind}`)} description={t("doe.residual.description")}
      annotations={[]} emptyLabel={t("doe.residual.empty")} formatValue={factorialNumber}
      xLabel={t(kind === "qq" ? "doe.residual.quantile" : kind === "fits" ? "doe.residual.fitted" : "doe.residual.run")} yLabel={label}
      xRange={range} yRange={paddedNumericRange([0, ...data.map((point) => point.y), ...lines.flatMap((line) => [line.y1, line.y2])])} referenceLines={lines}
      points={data.map((point) => ({ id: `${id}-${kind}-${point.run_order}`, title: `${t("doe.residual.run")} ${point.run_order}`,
        ariaLabel: `${t("doe.residual.run")} ${point.run_order}: ${factorialNumber(point.y)}`, className: "scatter-point",
        x: point.x, y: point.y, details: [{ label, value: factorialNumber(point.y) }, { label: t("doe.residual.run"), value: String(point.run_order) }] }))} />;
  }
  return <details className="result-section factorial-residual-plots"><summary>{t("doe.residual.open")}</summary>
    <label className="factorial-inline-select"><span>{t("doe.residual.mode")}</span><select value={mode} onChange={(event) => setMode(event.currentTarget.value as typeof mode)}>
      <option value="raw">{t("doe.residual.raw")}</option><option value="standardized">{t("doe.residual.standardized")}</option>
    </select></label><p className="field-help">{t("doe.residual.description")} N = {plots.n_total}</p>
    <div className="chart-grid linear-model-four-in-one">
      <div className="chart-panel"><h4>{t("doe.residual.qq")}</h4>{scatter("qq")}</div>
      <div className="chart-panel"><h4>{t("doe.residual.histogram")}</h4><InteractiveHistogramChart chartId={`${id}-${mode}-histogram`}
        columnName={label} nBasis={view.n} bins={view.histogram.map((bin, index) => ({ ...bin, include_lower: true, include_upper: index === view.histogram.length - 1 }))} /></div>
      <div className="chart-panel"><h4>{t("doe.residual.fits")}</h4>{scatter("fits")}</div>
      <div className="chart-panel"><h4>{t("doe.residual.order")}</h4>{scatter("order")}</div>
    </div>
  </details>;
}
