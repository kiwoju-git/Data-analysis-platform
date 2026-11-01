import { useId, useState } from "react";
import type { DoeResidualView } from "../api/types/doeModelWorkflow";
import { InteractiveHistogramChart } from "../charts/InteractiveHistogramChart";
import { InteractiveScatterChart, type ScatterReferenceLine } from "../charts/InteractiveScatterChart";
import { paddedNumericRange } from "../charts/chartScale";
import { integerChartTicks } from "../charts/chartLayout";
import { formatMeasurement } from "../statisticalNumberFormat";
import { t } from "../i18n/translate";

type ResidualView = DoeResidualView & {
  n_available?: number; n_displayed?: number; unavailable_reason?: string | null;
};
export interface DoeResidualPlotsProps {
  plots: { raw: ResidualView; standardized: ResidualView; n_total: number; point_limit: number; truncated: boolean };
  sourceKey?: string;
  responseUnit?: string | null;
  defaultOpen?: boolean;
}

function unavailableMessage(reason: string): string {
  switch (reason) {
    case "no_residual_degrees_of_freedom": return t("doe.residual.reason.no_residual_degrees_of_freedom");
    case "residual_variance_unavailable": return t("doe.residual.reason.residual_variance_unavailable");
    case "standardization_denominator_unavailable": return t("doe.residual.reason.standardization_denominator_unavailable");
    case "non_finite_residuals": return t("doe.residual.reason.non_finite_residuals");
    default: return t("doe.residual.empty");
  }
}

export function DoeResidualPlots({ plots, sourceKey, responseUnit, defaultOpen = false }: DoeResidualPlotsProps) {
  const id = useId().replace(/:/g, "");
  const [mode, setMode] = useState<"raw" | "standardized">("raw");
  const [open, setOpen] = useState(defaultOpen);
  const view = plots[mode];
  const baseLabel = t(mode === "raw" ? "doe.residual.raw" : "doe.residual.standardized");
  const label = mode === "raw" && responseUnit ? `${baseLabel} (${responseUnit})` : baseLabel;
  const fittedLabel = `${t("doe.residual.fitted")}${responseUnit ? ` (${responseUnit})` : ""}`;
  const currentSource = `${sourceKey ?? id}:${mode}`;
  function scatter(kind: "qq" | "fits" | "order") {
    const data = kind === "qq" ? view.qq_points.map((point) => ({ ...point, x: point.theoretical_quantile, y: point.residual }))
      : view.points.map((point) => ({ ...point, x: kind === "fits" ? point.fitted : point.run_order, y: point.residual }));
    const range = paddedNumericRange(data.map((point) => point.x));
    const lines: ScatterReferenceLine[] = kind === "qq" ? (view.reference_line === null ? [] : [{ label: t("doe.residual.reference"), x1: range.min, x2: range.max,
      y1: view.reference_line.intercept + range.min * view.reference_line.slope, y2: view.reference_line.intercept + range.max * view.reference_line.slope }])
      : [{ label: "0", x1: range.min, x2: range.max, y1: 0, y2: 0 }];
    return <InteractiveScatterChart chartId={`${id}-${mode}-${kind}`} sourceKey={currentSource} title={t(`doe.residual.${kind}`)} description={t("doe.residual.description")}
      annotations={[]} emptyLabel={t("doe.residual.empty")}
      xLabel={kind === "fits" ? fittedLabel : t(kind === "qq" ? "doe.residual.quantile" : "doe.residual.run")} yLabel={label}
      xRange={range} xTicks={kind === "order" ? integerChartTicks(range) : undefined} yRange={paddedNumericRange([0, ...data.map((point) => point.y), ...lines.flatMap((line) => [line.y1, line.y2])])} referenceLines={lines}
      points={data.map((point) => ({ id: `${id}-${kind}-${point.run_order}`, title: `${t("doe.residual.run")} ${point.run_order}`,
        ariaLabel: `${t("doe.residual.run")} ${point.run_order}: ${formatMeasurement(point.y)}`, className: "scatter-point",
        x: point.x, y: point.y, details: [{ label, value: formatMeasurement(point.y) }, { label: t("doe.residual.run"), value: String(point.run_order) },
          { label: kind === "fits" ? fittedLabel : t(kind === "qq" ? "doe.residual.quantile" : "doe.residual.run"), value: formatMeasurement(point.x) }] }))} />;
  }
  return <details className="result-section factorial-residual-plots" open={open} onToggle={(event) => setOpen(event.currentTarget.open)}><summary>{t("doe.residual.open")}</summary>
    <label className="factorial-inline-select"><span>{t("doe.residual.mode")}</span><select value={mode} onChange={(event) => setMode(event.currentTarget.value as typeof mode)}>
      <option value="raw">{t("doe.residual.raw")}</option><option value="standardized">{t("doe.residual.standardized")}</option>
    </select></label><p className="field-help">{t("doe.residual.description")} N = {plots.n_total}. {t("doe.residual.counts", {
      available: view.n_available ?? view.n, displayed: view.n_displayed ?? view.points.length,
    })}</p>
    {view.unavailable_reason && <p className="notice-box">{unavailableMessage(view.unavailable_reason)}</p>}
    <div className="chart-grid linear-model-four-in-one analysis-result-grid">
      <div className="chart-panel"><h4>{t("doe.residual.qq")}</h4>{scatter("qq")}</div>
      <div className="chart-panel"><h4>{t("doe.residual.histogram")}</h4><InteractiveHistogramChart chartId={`${id}-${mode}-histogram`}
        sourceKey={currentSource} columnName={baseLabel} unit={mode === "raw" ? responseUnit : null} nBasis={view.n} bins={view.histogram.map((bin, index) => ({ ...bin, include_lower: true, include_upper: index === view.histogram.length - 1 }))} /></div>
      <div className="chart-panel"><h4>{t("doe.residual.fits")}</h4>{scatter("fits")}</div>
      <div className="chart-panel"><h4>{t("doe.residual.order")}</h4>{scatter("order")}</div>
    </div>
  </details>;
}
