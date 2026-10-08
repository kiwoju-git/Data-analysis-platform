import { useEffect, useRef, useState } from "react";
import type { GaussianProcessRegressionResult } from "../api";
import { createGaussianProcessPointPredictions } from "../api/regression";
import { useI18n } from "../i18n/LocaleProvider";
import { localizedErrorDisplay } from "../i18n/errorMessages";
import { createLatestRequestGuard } from "../latestRequest";
import { InteractiveScatterChart, type InteractiveScatterPoint } from "./InteractiveScatterChart";
import { InteractiveGridChart } from "./InteractiveGridChart";
import { paddedNumericRange } from "./chartScale";
import { gpResidualModel, gpScatterModel, gpSurfaceRequest, gpUncertaintyModel, joinGpSurfaceRows } from "./gpChartModels";

type Props = { result: GaussianProcessRegressionResult; scope: string };
const number = (value: number | null) => value !== null && Number.isFinite(value) ? Number(value.toPrecision(7)).toString() : "-";

export function GpScatter({ result, mode, scope }: Props & { mode: "fitted" | "cv" }) {
  const { t } = useI18n();
  const predictionLabel = t(mode === "fitted" ? "gp.fitted" : "gp.cvFitted");
  const points: InteractiveScatterPoint[] = gpScatterModel(result, mode).map((point) => ({ ...point,
    title: `${t("gp.row")} ${point.rowIndex + 1}`, ariaLabel: `${t("gp.row")} ${point.rowIndex + 1}, ${number(point.x)}, ${number(point.y)}`, className: "gp-chart-point",
    details: [{ label: t("gp.observed"), value: number(point.x) }, { label: predictionLabel, value: number(point.y) }, { label: t("gp.residual"), value: number(point.residual) }] }));
  const range = paddedNumericRange(points.flatMap((point) => [point.x, point.y]));
  const title = t(mode === "fitted" ? "gp.observedFitted" : "gp.observedCv");
  return <InteractiveScatterChart chartId={`gp-${mode}`} sourceKey={`${scope}:${mode}`} title={title} description={title}
    annotations={[t("charts.displayCount", { shown: points.length, total: result.sample.n_used })]} emptyLabel={t("charts.noData")} formatValue={number} points={points}
    xLabel={`${t("gp.observed")} ${result.response.display_name}`} yLabel={`${predictionLabel} ${result.response.display_name}`}
    xUnit={result.response.unit} yUnit={result.response.unit} xRange={range} yRange={range}
    referenceLines={[{ label: "y = x", x1: range.min, y1: range.min, x2: range.max, y2: range.max }]} />;
}

export function GpResidualChart({ result, scope }: Props) {
  const { t } = useI18n();
  const points: InteractiveScatterPoint[] = gpResidualModel(result).map((point) => ({ ...point,
    title: `${t("gp.row")} ${point.rowIndex + 1}`, ariaLabel: `${t("gp.row")} ${point.rowIndex + 1}, ${number(point.x)}, ${number(point.y)}`, className: "gp-chart-point",
    details: [{ label: t("gp.fitted"), value: number(point.x) }, { label: t("gp.residual"), value: number(point.y) }, { label: t("charts.standardizedResidual"), value: number(point.standardizedResidual) }] }));
  const xRange = paddedNumericRange(points.map((point) => point.x));
  return <InteractiveScatterChart chartId="gp-residual" sourceKey={`${scope}:residual`} title={t("gp.residualDiagnostics")} description={t("gp.residualDiagnostics")}
    annotations={[]} emptyLabel={t("charts.noData")} formatValue={number} points={points}
    xLabel={t("gp.fitted")} yLabel={t("gp.residual")} xUnit={result.response.unit} yUnit={result.response.unit} xRange={xRange} yRange={paddedNumericRange([0, ...points.map((point) => point.y)])}
    referenceLines={[{ label: "0", x1: xRange.min, x2: xRange.max, y1: 0, y2: 0 }]} />;
}

export function GpUncertaintyChart({ result, scope }: Props) {
  const { t } = useI18n();
  const points: InteractiveScatterPoint[] = gpUncertaintyModel(result).map((point) => ({ ...point,
    title: `${t("gp.row")} ${point.x}`, ariaLabel: `${t("gp.row")} ${point.x}, ${number(point.y)}`, className: "gp-uncertainty-point",
    details: [{ label: t("gp.newObservationSd"), value: number(point.y) }] }));
  return <InteractiveScatterChart chartId="gp-uncertainty" sourceKey={`${scope}:uncertainty`} title={t("gp.uncertaintyDiagnostics")} description={t("gp.newObservationSd")}
    annotations={[]} emptyLabel={t("charts.noData")} formatValue={number} points={points}
    xLabel={t("gp.row")} yLabel={t("gp.newObservationSd")} yUnit={result.response.unit}
    xRange={paddedNumericRange(points.map((point) => point.x))} yRange={paddedNumericRange([0, ...points.map((point) => point.y)])} />;
}

export function GpProfileChart({ profile, result, scope }: Props & { profile: GaussianProcessRegressionResult["conditional_profiles"][number] }) {
  const { t } = useI18n();
  const points: InteractiveScatterPoint[] = profile.points.map((point) => ({ id: `value:${point.value}`, x: point.value, y: point.predicted_mean,
    title: profile.display_name, ariaLabel: `${profile.display_name} ${number(point.value)}, ${number(point.predicted_mean)}`, className: "gp-profile-point",
    details: [{ label: profile.display_name, value: number(point.value) }, { label: t("gp.predictedMean"), value: number(point.predicted_mean) },
      { label: t("gp.predictiveInterval"), value: `${number(point.predictive_interval_95.lower)} - ${number(point.predictive_interval_95.upper)}` }] }));
  return <figure className="gp-profile-chart"><figcaption>{profile.display_name}</figcaption>
    <InteractiveScatterChart chartId={`gp-profile-${profile.column_id}`} sourceKey={`${scope}:profile:${profile.column_id}`}
      title={`${t("gp.conditionalProfiles")}: ${profile.display_name}`} description={t("gp.profileNotice")} annotations={[t("gp.profileNotice")]}
      emptyLabel={t("charts.noData")} formatValue={number} points={points} connectPoints="line"
      xLabel={profile.display_name} xUnit={result.predictors.find((column) => column.column_id === profile.column_id)?.unit}
      yLabel={`${t("gp.predictedMean")} ${result.response.display_name}`} yUnit={result.response.unit}
      xRange={paddedNumericRange(points.map((point) => point.x))} yRange={paddedNumericRange(profile.points.flatMap((point) => [point.predictive_interval_95.lower, point.predictive_interval_95.upper]))}
      bands={[{ id: "observation-95", label: t("gp.predictiveInterval"), className: "gp-profile-band", points: profile.points.map((point) => ({ x: point.value, lower: point.predictive_interval_95.lower, upper: point.predictive_interval_95.upper })) }]} />
  </figure>;
}

export function GpSurfaceChart({ result, scope }: Props) {
  const { t, locale } = useI18n();
  const [view, setView] = useState<"mean" | "uncertainty">("mean");
  const initialSurface = result.two_predictor_surface;
  const [xColumnId, setXColumnId] = useState(initialSurface?.x_column_id ?? "");
  const [yColumnId, setYColumnId] = useState(initialSurface?.y_column_id ?? "");
  const [surface, setSurface] = useState(initialSurface);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const guard = useRef(createLatestRequestGuard()).current;
  const manifest = result.model_manifest;
  const source = `${scope}:${manifest?.model_id ?? ""}:${manifest?.manifest_sha256 ?? ""}`;
  const latestSource = useRef(source); latestSource.current = source;
  useEffect(() => {
    guard.cancel(); setIsGenerating(false); setError(null);
    setXColumnId(initialSurface?.x_column_id ?? ""); setYColumnId(initialSurface?.y_column_id ?? ""); setSurface(initialSurface);
    return () => guard.cancel();
  }, [guard, initialSurface, source]);

  async function generateSurface() {
    const snapshot = gpSurfaceRequest(result, xColumnId, yColumnId);
    if (snapshot === null) return;
    const token = guard.begin(); const requestSource = source;
    const current = () => guard.isCurrent(token) && latestSource.current === requestSource;
    setIsGenerating(true); setError(null);
    try {
      const response = await createGaussianProcessPointPredictions(snapshot.modelId, { expected_model_manifest_sha256: snapshot.manifestHash, rows: snapshot.rows });
      if (!current()) return;
      setSurface(joinGpSurfaceRows(snapshot, response));
    } catch (caught) {
      if (!current()) return;
      if (caught instanceof Error && caught.message === "gp_surface_response_invalid") setError(`${t("gp.surfaceResponseInvalid")} (gp_surface_response_invalid)`);
      else { const display = localizedErrorDisplay(caught, locale); setError(`${display.message} (${display.code})`); }
    } finally { if (current()) setIsGenerating(false); }
  }
  if (surface === null) return null;
  const valueLabel = t(view === "mean" ? "gp.predictedMean" : "gp.newObservationSd");
  const fixedDescription = result.predictors.flatMap((predictor, index) => predictor.column_id === surface.x_column_id || predictor.column_id === surface.y_column_id ? [] : [`${predictor.display_name}=${number(surface.fixed_values[index])}`]).join("; ");
  return <section className="result-section gp-surface-result">
    <div className="section-heading-row"><h4>{t("gp.surface")}</h4><div className="segmented-control">
      <button aria-pressed={view === "mean"} onClick={() => setView("mean")} type="button">{t("gp.surfaceMean")}</button>
      <button aria-pressed={view === "uncertainty"} onClick={() => setView("uncertainty")} type="button">{t("gp.surfaceUncertainty")}</button>
    </div></div><p>{t("gp.surfaceNotice")}</p>
    <div className="gp-surface-controls">
      <label><span>{t("gp.surfaceX")}</span><select value={xColumnId} onChange={(event) => setXColumnId(event.currentTarget.value)}>{result.predictors.map((predictor) => <option key={predictor.column_id} value={predictor.column_id} disabled={predictor.column_id === yColumnId}>{predictor.display_name}</option>)}</select></label>
      <label><span>{t("gp.surfaceY")}</span><select value={yColumnId} onChange={(event) => setYColumnId(event.currentTarget.value)}>{result.predictors.map((predictor) => <option key={predictor.column_id} value={predictor.column_id} disabled={predictor.column_id === xColumnId}>{predictor.display_name}</option>)}</select></label>
      <button type="button" disabled={manifest === undefined || xColumnId === yColumnId} onClick={() => void generateSurface()}>{isGenerating ? t("gp.generatingSurface") : t("gp.generateSurface")}</button>
    </div>
    {error !== null && <div className="notice-box error" role="alert">{error}</div>}
    <InteractiveGridChart chartId="gp-surface" sourceKey={`${source}:${surface.x_column_id}:${surface.y_column_id}:${view}`} title={t("gp.surface")} description={t("gp.surfaceNotice")}
      xLabel={surface.x_display_name} yLabel={surface.y_display_name} valueLabel={valueLabel}
      xUnit={result.predictors.find((column) => column.column_id === surface.x_column_id)?.unit} yUnit={result.predictors.find((column) => column.column_id === surface.y_column_id)?.unit} valueUnit={result.response.unit}
      cells={surface.points.map((point) => ({ id: `cell:${point.x}:${point.y}`, x: point.x, y: point.y, value: view === "mean" ? point.predicted_mean : point.predictive_standard_deviation,
        title: valueLabel, details: [{ label: surface.x_display_name, value: number(point.x) }, { label: surface.y_display_name, value: number(point.y) },
          { label: valueLabel, value: number(view === "mean" ? point.predicted_mean : point.predictive_standard_deviation) }, { label: t("gp.profileNotice"), value: fixedDescription }] }))} />
  </section>;
}
