import { useEffect, useRef, useState } from "react";
import type { GaussianProcessRegressionResult, GaussianProcessPointPredictionResponse } from "../api";
import { createGaussianProcessPointPredictions } from "../api/regression";
import { useI18n } from "../i18n/LocaleProvider";
import { localizedErrorDisplay } from "../i18n/errorMessages";
import { createLatestRequestGuard } from "../latestRequest";
import { InteractiveScatterChart, type InteractiveScatterPoint } from "./InteractiveScatterChart";
import { InteractiveGridChart } from "./InteractiveGridChart";
import { paddedNumericRange } from "./chartScale";
import { integerChartTicks } from "./chartLayout";
import { gpResidualModel, gpScatterModel, gpSurfaceRequest, gpUncertaintyModel, joinGpSurfaceRows, type GpSurfaceRequestSnapshot } from "./gpChartModels";
import { formatExactNumericValue, formatInterval } from "../statisticalNumberFormat";
import { savedPredictionDescriptor } from "../savedPredictionDescriptor";

type Props = { result: GaussianProcessRegressionResult; scope: string };
const number = formatExactNumericValue;
const valueText = (value: number | string | undefined) => typeof value === "string" ? value : number(value);

export function GpScatter({ result, mode, scope }: Props & { mode: "fitted" | "cv" }) {
  const { t } = useI18n();
  const predictionLabel = t(mode === "fitted" ? "gp.fitted" : "gp.cvFitted");
  const points: InteractiveScatterPoint[] = gpScatterModel(result, mode).map((point) => ({ ...point,
    title: `${t("gp.row")} ${point.rowIndex + 1}`, ariaLabel: `${t("gp.row")} ${point.rowIndex + 1}, ${number(point.x)}, ${number(point.y)}`, className: "gp-chart-point",
    details: [{ label: t("gp.observed"), value: number(point.x) }, { label: predictionLabel, value: number(point.y) }, { label: t("gp.residual"), value: number(point.residual) }] }));
  const range = paddedNumericRange(points.flatMap((point) => [point.x, point.y]));
  const title = t(mode === "fitted" ? "gp.observedFitted" : "gp.observedCv");
  return <InteractiveScatterChart chartId={`gp-${mode}`} sourceKey={`${scope}:${mode}`} title={title} description={title}
    annotations={[t("charts.displayCount", { shown: points.length, total: result.sample.n_used })]} emptyLabel={t("charts.noData")} points={points}
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
    annotations={[]} emptyLabel={t("charts.noData")} points={points}
    xLabel={t("gp.fitted")} yLabel={t("gp.residual")} xUnit={result.response.unit} yUnit={result.response.unit} xRange={xRange} yRange={paddedNumericRange([0, ...points.map((point) => point.y)])}
    referenceLines={[{ label: "0", x1: xRange.min, x2: xRange.max, y1: 0, y2: 0 }]} />;
}

export function GpUncertaintyChart({ result, scope }: Props) {
  const { t } = useI18n();
  const points: InteractiveScatterPoint[] = gpUncertaintyModel(result).map((point) => ({ ...point,
    title: `${t("gp.row")} ${point.x}`, ariaLabel: `${t("gp.row")} ${point.x}, ${number(point.y)}`, className: "gp-uncertainty-point",
    details: [{ label: t("gp.newObservationSd"), value: number(point.y) }] }));
  const xRange = paddedNumericRange(points.map((point) => point.x));
  return <InteractiveScatterChart chartId="gp-uncertainty" sourceKey={`${scope}:uncertainty`} title={t("gp.uncertaintyDiagnostics")} description={t("gp.newObservationSd")}
    annotations={[]} emptyLabel={t("charts.noData")} points={points}
    xLabel={t("gp.row")} yLabel={t("gp.newObservationSd")} yUnit={result.response.unit}
    xRange={xRange} xTicks={integerChartTicks(xRange)} yRange={paddedNumericRange([0, ...points.map((point) => point.y)])} />;
}

export function GpProfileChart({ profile, result, scope }: Props & { profile: GaussianProcessRegressionResult["conditional_profiles"][number] }) {
  const { t } = useI18n();
  const nominal = profile.kind === "nominal" || profile.points.some((point) => typeof point.value === "string");
  const points: InteractiveScatterPoint[] = profile.points.map((point, index) => ({ id: `value:${point.value}`, x: typeof point.value === "number" && !nominal ? point.value : index, y: point.predicted_mean,
    title: profile.display_name, ariaLabel: `${profile.display_name} ${valueText(point.value)}, ${number(point.predicted_mean)}`, className: "gp-profile-point",
    details: [{ label: profile.display_name, value: valueText(point.value) }, { label: t("gp.predictedMean"), value: number(point.predicted_mean) },
      { label: t("gp.predictiveInterval"), value: formatInterval(point.predictive_interval_95) }] }));
  const fixedDescription = result.predictors.flatMap((predictor, index) => predictor.column_id === profile.column_id ? [] : [`${predictor.display_name}=${valueText(profile.fixed_values[index])}`]).join("; ");
  return <figure className="gp-profile-chart"><figcaption>{profile.display_name}</figcaption>
    <InteractiveScatterChart chartId={`gp-profile-${profile.column_id}`} sourceKey={`${scope}:profile:${profile.column_id}`}
      title={`${t("gp.conditionalProfiles")}: ${profile.display_name}`} description={t("gp.extension.fixedNotice")} annotations={[t("gp.extension.fixedNotice"), fixedDescription]}
      emptyLabel={t("charts.noData")} points={points} connectPoints={nominal ? undefined : "line"}
      xTicks={nominal ? profile.points.map((point, index) => ({ value: index, label: String(point.value) })) : undefined}
      xLabel={profile.display_name} xUnit={result.predictors.find((column) => column.column_id === profile.column_id)?.unit}
      yLabel={`${t("gp.predictedMean")} ${result.response.display_name}`} yUnit={result.response.unit}
      xRange={paddedNumericRange(points.map((point) => point.x))} yRange={paddedNumericRange(profile.points.flatMap((point) => [point.predictive_interval_95.lower, point.predictive_interval_95.upper]))}
      intervals={nominal ? profile.points.map((point) => ({ id: `interval:${point.value}`, pointId: `value:${point.value}`, lower: point.predictive_interval_95.lower, upper: point.predictive_interval_95.upper, kind: "prediction_interval" as const })) : undefined}
      bands={nominal ? [] : [{ id: "observation-95", label: t("gp.predictiveInterval"), className: "gp-profile-band", points: profile.points.flatMap((point) => typeof point.value === "number" ? [{ x: point.value, lower: point.predictive_interval_95.lower, upper: point.predictive_interval_95.upper }] : []) }]} />
  </figure>;
}

export function GpSurfaceChart({ result, scope, analysisId }: Props & { analysisId?: string }) {
  const { t, locale } = useI18n();
  const [view, setView] = useState<"mean" | "latent_sd" | "predictive_sd">("mean");
  const initialSurface = result.two_predictor_surface;
  const numeric = result.training_ranges.filter((range) => range.kind !== "nominal");
  const defaultHolds = () => Object.fromEntries(result.training_ranges.map((range, index) => [range.column_id, String(initialSurface?.fixed_values[index] ?? (range.kind === "nominal" ? range.mode : range.median))]));
  const [xColumnId, setXColumnId] = useState(initialSurface?.x_column_id ?? numeric[0]?.column_id ?? "");
  const [yColumnId, setYColumnId] = useState(initialSurface?.y_column_id ?? numeric[1]?.column_id ?? "");
  const [holdDraft, setHoldDraft] = useState<Record<string, string>>(defaultHolds);
  const [storedSurface, setSurface] = useState(initialSurface);
  const [applied, setApplied] = useState<GpSurfaceRequestSnapshot | null>(null);
  const [isStale, setIsStale] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState<GaussianProcessPointPredictionResponse["saved_prediction"]>(undefined);
  const [error, setError] = useState<{ cause: unknown } | null>(null);
  const errorDisplay = error === null ? null : localizedErrorDisplay(error.cause, locale);
  const guard = useRef(createLatestRequestGuard()).current;
  const saveGuard = useRef(createLatestRequestGuard()).current;
  const manifest = result.model_manifest;
  const source = `${scope}:${manifest?.model_id ?? ""}:${manifest?.manifest_sha256 ?? ""}`;
  const surfaceOwner = useRef(source);
  const currentOwner = surfaceOwner.current === source;
  const surface = currentOwner ? storedSurface : initialSurface;
  const latestSource = useRef(source); latestSource.current = source;
  useEffect(() => {
    surfaceOwner.current = source;
    guard.cancel(); saveGuard.cancel(); setIsGenerating(false); setIsSaving(false); setError(null); setSaved(undefined); setIsStale(false); setView("mean");
    setApplied(initialSurface ? gpSurfaceRequest(result, initialSurface.x_column_id, initialSurface.y_column_id, Object.fromEntries(result.training_ranges.map((range, index) => [range.column_id, initialSurface.fixed_values[index]]))) : null);
    setXColumnId(initialSurface?.x_column_id ?? numeric[0]?.column_id ?? ""); setYColumnId(initialSurface?.y_column_id ?? numeric[1]?.column_id ?? ""); setSurface(initialSurface); setHoldDraft(defaultHolds());
    return () => { guard.cancel(); saveGuard.cancel(); };
    // A source change resets the view; locale and viewport changes do not.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [guard, saveGuard, initialSurface, source]);

  function invalidateDraft() { guard.cancel(); saveGuard.cancel(); setIsGenerating(false); setIsSaving(false); setSaved(undefined); setError(null); setIsStale(true); }
  function requestSnapshot() {
    const holds: Record<string, number | string> = {};
    for (const range of result.training_ranges) {
      if (range.column_id === xColumnId || range.column_id === yColumnId) continue;
      const raw = holdDraft[range.column_id] ?? "";
      if (range.kind === "nominal") holds[range.column_id] = raw;
      else {
        if (!raw.trim() || !/^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/.test(raw.trim())) return null;
        holds[range.column_id] = Number(raw);
      }
    }
    return gpSurfaceRequest(result, xColumnId, yColumnId, holds);
  }

  async function generateSurface() {
    const snapshot = requestSnapshot();
    if (snapshot === null) return;
    const token = guard.begin(); const requestSource = source;
    const current = () => guard.isCurrent(token) && latestSource.current === requestSource;
    setIsGenerating(true); setError(null);
    try {
      const response = await createGaussianProcessPointPredictions(snapshot.modelId, { expected_model_manifest_sha256: snapshot.manifestHash, rows: snapshot.rows });
      if (!current()) return;
      setSurface(joinGpSurfaceRows(snapshot, response)); setApplied(snapshot); setIsStale(false); setSaved(undefined);
    } catch (caught) {
      if (!current()) return;
      setError({ cause: caught });
    } finally { if (current()) setIsGenerating(false); }
  }
  async function saveView() {
    if (!applied || !currentOwner || isStale || !analysisId) return;
    const snapshot = applied; const token = saveGuard.begin(); const requestSource = source; const displayMode = view;
    const current = () => saveGuard.isCurrent(token) && latestSource.current === requestSource;
    setIsSaving(true); setError(null);
    try {
      const response = await createGaussianProcessPointPredictions(snapshot.modelId, { expected_model_manifest_sha256: snapshot.manifestHash, rows: snapshot.rows, save_result: true,
        surface_view: { x_column_id: snapshot.xColumnId, y_column_id: snapshot.yColumnId, hold_values: snapshot.holdValues ?? {}, grid_size: snapshot.gridSize, display_mode: displayMode } });
      if (!current()) return;
      joinGpSurfaceRows(snapshot, response);
      setSaved(savedPredictionDescriptor(response.saved_prediction, { saveResult: true, family: "gaussian_process", analysisId, modelId: snapshot.modelId, manifestSha256: snapshot.manifestHash }));
    } catch (caught) { if (current()) setError({ cause: caught }); }
    finally { if (current()) setIsSaving(false); }
  }
  if (numeric.length < 2) return <p className="notice-box">{t("gp.extension.surfaceUnavailable")}</p>;
  const valueLabel = t(view === "mean" ? "gp.predictedMean" : view === "latent_sd" ? "gp.latentSd" : "gp.newObservationSd");
  const fixedDescription = surface ? result.predictors.flatMap((predictor, index) => predictor.column_id === surface.x_column_id || predictor.column_id === surface.y_column_id ? [] : [`${predictor.display_name}=${valueText(surface.fixed_values[index])}`]).join("; ") : "";
  const displayedValue = (point: NonNullable<typeof surface>["points"][number]) => view === "mean" ? point.predicted_mean : view === "latent_sd" ? point.latent_standard_deviation : point.predictive_standard_deviation;
  const changeView = (mode: typeof view) => { saveGuard.cancel(); setIsSaving(false); setSaved(undefined); setView(mode); };
  return <section className="result-section gp-surface-result">
    <div className="section-heading-row"><h4>{t("gp.surface")}</h4><div className="segmented-control">
      <button aria-pressed={view === "mean"} onClick={() => changeView("mean")} type="button">{t("gp.surfaceMean")}</button>
      <button aria-pressed={view === "latent_sd"} disabled={!surface?.points.every((point) => point.latent_standard_deviation !== undefined)} onClick={() => changeView("latent_sd")} type="button">{t("gp.latentSd")}</button>
      <button aria-pressed={view === "predictive_sd"} onClick={() => changeView("predictive_sd")} type="button">{t("gp.newObservationSd")}</button>
    </div></div><p>{t("gp.extension.fixedNotice")}</p>
    <div className="gp-surface-controls">
      <label><span>{t("gp.surfaceX")}</span><select value={xColumnId} onChange={(event) => { invalidateDraft(); setXColumnId(event.currentTarget.value); }}>{numeric.map((predictor) => <option key={predictor.column_id} value={predictor.column_id} disabled={predictor.column_id === yColumnId}>{predictor.display_name}</option>)}</select></label>
      <label><span>{t("gp.surfaceY")}</span><select value={yColumnId} onChange={(event) => { invalidateDraft(); setYColumnId(event.currentTarget.value); }}>{numeric.map((predictor) => <option key={predictor.column_id} value={predictor.column_id} disabled={predictor.column_id === xColumnId}>{predictor.display_name}</option>)}</select></label>
      {result.training_ranges.filter((range) => range.column_id !== xColumnId && range.column_id !== yColumnId).map((range) => <label key={range.column_id}><span>{range.display_name} · {t("gp.extension.holdValue")}</span>{range.kind === "nominal" ? <select value={holdDraft[range.column_id] ?? ""} onChange={(event) => { invalidateDraft(); setHoldDraft({ ...holdDraft, [range.column_id]: event.currentTarget.value }); }}>{range.levels.map((level) => <option key={level} value={level}>{level}</option>)}</select> : <input type="text" inputMode="decimal" value={holdDraft[range.column_id] ?? ""} onChange={(event) => { invalidateDraft(); setHoldDraft({ ...holdDraft, [range.column_id]: event.currentTarget.value }); }} />}</label>)}
      <button type="button" disabled={manifest === undefined || requestSnapshot() === null || isGenerating || isSaving} onClick={() => void generateSurface()}>{isGenerating ? t("gp.generatingSurface") : t("gp.generateSurface")}</button>
      <button type="button" disabled={!applied || !currentOwner || !analysisId || isStale || isGenerating || isSaving} onClick={() => void saveView()}>{isSaving ? t("gp.extension.savingView") : t("gp.extension.saveView")}</button>
    </div>
    {isStale && <p className="notice-box warning" role="status">{t("gp.extension.surfaceStale")}</p>}
    {saved && currentOwner && <p className="notice-box" role="status">{t("gp.extension.viewSaved")} <a href="/reports?source_kind=regression_prediction">{t("prediction.openSaved")}</a></p>}
    {errorDisplay !== null && <div className="notice-box error" role="alert">{errorDisplay.message} ({errorDisplay.code})</div>}
    {surface && <><p>{fixedDescription}</p><InteractiveGridChart chartId="gp-surface" sourceKey={`${source}:${surface.x_column_id}:${surface.y_column_id}:${JSON.stringify(surface.fixed_values)}:${view}`} title={t("gp.surface")} description={t("gp.extension.fixedNotice")}
      xLabel={surface.x_display_name} yLabel={surface.y_display_name} valueLabel={valueLabel}
      xUnit={result.predictors.find((column) => column.column_id === surface.x_column_id)?.unit} yUnit={result.predictors.find((column) => column.column_id === surface.y_column_id)?.unit} valueUnit={result.response.unit}
      cells={surface.points.flatMap((point) => displayedValue(point) === undefined ? [] : [{ id: `cell:${point.x}:${point.y}`, x: point.x, y: point.y, value: displayedValue(point)!,
        title: valueLabel, details: [{ label: surface.x_display_name, value: number(point.x) }, { label: surface.y_display_name, value: number(point.y) },
          { label: valueLabel, value: number(displayedValue(point)) }, { label: t("gp.extension.holdValue"), value: fixedDescription }] }])} /></>}
  </section>;
}
