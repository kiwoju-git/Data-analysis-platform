import { useEffect, useRef, useState } from "react";
import { Play, Save, RefreshCw } from "lucide-react";
import type { DoeResponseSurfaceAnalysisResponse, ResponseSurfaceDesignResponse } from "../api";
import { createRsmPlotView, fetchRsmPlotSource, fetchRsmPlotViews, fetchRsmPlotView, saveRsmPlotView } from "../api/rsmPlots";
import type { RsmPlotSettings, RsmPlotSource, RsmPlotView, RsmPlotViewDescriptor } from "../api/types/rsmPlots";
import { useI18n } from "../i18n/LocaleProvider";
import { createLatestRequestGuard } from "../latestRequest";
import { ResponseSurfaceContourChart } from "../charts/ResponseSurfaceContourChart";
import { parseDoeResponseNumber } from "./doeResponsePaste";
import { strictRsmInteger } from "./rsmDesignDraft";
import { DoeCompactPlotCard, DoeCompactPlotGrid } from "./DoeCompactPlotGrid";
import { doePlotStatus } from "./doePlotStatus";
import { paddedNumericRange } from "../charts/chartScale";
import { rsmViewMatchesSnapshot } from "./rsmPlotSnapshot";

export function RsmPlotOptions({ analysis, design }: {
  analysis: DoeResponseSurfaceAnalysisResponse; design: ResponseSurfaceDesignResponse;
}) {
  const { t } = useI18n();
  const original = analysis.result.plot_bundle!;
  const [draft, setDraft] = useState(original.settings);
  const [holds, setHolds] = useState<Record<string, string>>(Object.fromEntries(
    design.factors.map((factor, index) => [`factor_${index + 1}`, String(factor.low / 2 + factor.high / 2)])));
  const [levels, setLevels] = useState("");
  const [levelCount, setLevelCount] = useState("6");
  const [gridSize, setGridSize] = useState("21");
  const [view, setView] = useState<RsmPlotView | null>(null);
  const [source, setSource] = useState<RsmPlotSource | null>(null);
  const [saved, setSaved] = useState<RsmPlotViewDescriptor[]>([]);
  const [running, setRunning] = useState(false);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [overview, setOverview] = useState(false);
  const guard = useRef(createLatestRequestGuard()).current;
  const listGuard = useRef(createLatestRequestGuard()).current;
  const sourceGuard = useRef(createLatestRequestGuard()).current;
  useEffect(() => {
    const token = sourceGuard.begin();
    void fetchRsmPlotSource(design.design_id, analysis.analysis_id).then((next) => {
      if (!sourceGuard.isCurrent(token)) return;
      if (next.response_revision_id !== analysis.response_revision_id ||
        next.response_revision_sha256 !== analysis.response_revision_sha256) throw new Error("doe_rsm_plot_source_changed");
      setSource(next);
    }).catch((caught: unknown) => {
      if (sourceGuard.isCurrent(token)) setError(caught instanceof Error ? caught.message : "doe_rsm_plot_invalid");
    });
    const list = listGuard.begin();
    void fetchRsmPlotViews(design.design_id, analysis.analysis_id).then((items) => {
      if (listGuard.isCurrent(list)) setSaved(items);
    }).catch(() => { if (listGuard.isCurrent(list)) setError("doe_rsm_plot_history_unavailable"); });
    return () => { sourceGuard.cancel(token); listGuard.cancel(list); guard.cancel(); };
  }, [analysis.analysis_id, analysis.response_revision_id, analysis.response_revision_sha256,
    design.design_id, attempt, guard, listGuard, sourceGuard]);
  function invalidate() {
    guard.cancel();
    setRunning(false); setSaving(false); setDirty(true); setSavedId(null); setError(null);
  }
  function edit(values: Partial<RsmPlotSettings>) { invalidate(); setDraft((current) => ({ ...current, ...values })); }
  function parseSettings(): RsmPlotSettings | null {
    const grid = strictRsmInteger(gridSize); const count = strictRsmInteger(levelCount);
    const thresholds = levels.trim() ? levels.split(",").map(parseDoeResponseNumber) : null;
    if (grid === null || grid < 11 || grid > 51 || grid % 2 === 0 ||
      count === null || count < 2 || count > 11 ||
      (thresholds && (thresholds.length < 2 || thresholds.length > 11 ||
        thresholds.some((value, index) => value === null || (index > 0 && value <= thresholds[index - 1]!))))) return null;
    const held: Record<string, number> = {};
    for (const [index, factor] of design.factors.entries()) {
      const id = `factor_${index + 1}`;
      if (id === draft.x_factor_id || id === draft.y_factor_id) continue;
      const value = parseDoeResponseNumber(holds[id] ?? "");
      if (value === null || value < factor.low || value > factor.high) return null;
      held[id] = value;
    }
    if (draft.plot_kind !== "main_effect" && draft.x_factor_id === draft.y_factor_id) return null;
    return { ...draft, grid_size: grid, held_actual_values: held,
      contour_levels: { count, thresholds: thresholds as number[] | null } };
  }
  async function generate() {
    const settings = parseSettings();
    if (!settings || !source) { setError("doe_rsm_plot_invalid"); return; }
    const snapshot = { settings, source, design: design.design_id, analysis: analysis.analysis_id };
    const token = guard.begin(); setRunning(true); setError(null); setSavedId(null);
    try {
      const result = await createRsmPlotView(snapshot.design, snapshot.analysis, snapshot.source, snapshot.settings);
      if (guard.isCurrent(token)) {
        if (!rsmViewMatchesSnapshot(result, snapshot)) throw new Error("doe_rsm_plot_source_changed");
        setView(result); setDirty(false);
      }
    } catch (caught) {
      if (guard.isCurrent(token)) setError(caught instanceof Error ? caught.message : "doe_rsm_plot_invalid");
    } finally { if (guard.isCurrent(token)) setRunning(false); }
  }
  async function save() {
    if (!view || dirty) return;
    listGuard.cancel();
    const snapshot = view; const token = guard.begin(); setSaving(true); setError(null);
    try {
      const result = await saveRsmPlotView(snapshot);
      if (guard.isCurrent(token)) {
        if (!rsmViewMatchesSnapshot(result.view, { source: snapshot, settings: snapshot.bundle.settings,
          design: snapshot.design_id, analysis: snapshot.analysis_id }) ||
          result.view.view_sha256 !== snapshot.view_sha256) throw new Error("doe_rsm_plot_source_changed");
        const descriptor = { asset_id: result.asset_id, sha256: result.sha256, created_at: result.created_at };
        setSaved((items) => [descriptor, ...items.filter((item) => item.asset_id !== result.asset_id)]);
        setSavedId(result.asset_id);
      }
    } catch (caught) {
      if (guard.isCurrent(token)) setError(caught instanceof Error ? caught.message : "doe_rsm_plot_invalid");
    } finally { if (guard.isCurrent(token)) setSaving(false); }
  }
  async function restore(item: RsmPlotViewDescriptor) {
    invalidate();
    const token = guard.begin(); setRunning(true);
    try {
      const stored = await fetchRsmPlotView(design.design_id, analysis.analysis_id, item.asset_id);
      if (!guard.isCurrent(token)) return;
      if (stored.sha256 !== item.sha256 || !source ||
        !rsmViewMatchesSnapshot(stored.view, { source, settings: stored.view.bundle.settings,
          design: design.design_id, analysis: analysis.analysis_id })) {
        throw new Error("doe_rsm_plot_source_changed");
      }
      const settings = stored.view.bundle.settings;
      setView(stored.view); setDraft(settings);
      setHolds({ ...Object.fromEntries(design.factors.map((factor, index) =>
        [`factor_${index + 1}`, String(factor.low / 2 + factor.high / 2)])),
        ...Object.fromEntries(Object.entries(settings.held_actual_values).map(([key, value]) => [key, String(value)])) });
      setGridSize(String(settings.grid_size)); setLevelCount(String(settings.contour_levels.count));
      setLevels(settings.contour_levels.thresholds?.join(", ") ?? "");
      setDirty(false); setSavedId(item.asset_id);
    } catch (caught) {
      if (guard.isCurrent(token)) setError(caught instanceof Error ? caught.message : "doe_rsm_plot_invalid");
    } finally { if (guard.isCurrent(token)) setRunning(false); }
  }
  const bundle = view?.bundle ?? original;
  const overviews = analysis.result.plot_overview ?? [];
  const ranges = Object.fromEntries((["main_effect", "interaction"] as const).map((kind) => [
    kind, paddedNumericRange(overviews.filter((item) => item.settings.plot_kind === kind)
      .flatMap((item) => item.points.map((point) => point.predicted)), .05),
  ]));
  return <section className="rsm-plot-options" aria-label={t("rsm.plot.title")}>
    <h5>{t("rsm.plot.title")}</h5>
    <div className="form-grid">
      <label>{t("rsm.plot.kind")}<select value={draft.plot_kind} onChange={(event) => {
        const kind = event.target.value as RsmPlotSettings["plot_kind"];
        edit({ plot_kind: kind, y_factor_id: kind === "main_effect" ? null
          : draft.y_factor_id ?? (draft.x_factor_id === "factor_1" ? "factor_2" : "factor_1") });
      }}><option value="contour">{t("rsm.plot.contour")}</option><option value="main_effect">{t("rsm.plot.main")}</option>
        <option value="interaction">{t("rsm.plot.interaction")}</option></select></label>
      <label>{t("rsm.plot.x")}<select value={draft.x_factor_id} onChange={(event) => edit({ x_factor_id: event.target.value })}>
        {design.factors.map((factor, index) => <option key={index} value={`factor_${index + 1}`}>{factor.name}</option>)}</select></label>
      {draft.plot_kind !== "main_effect" && <label>{t("rsm.plot.y")}<select value={draft.y_factor_id ?? ""}
        onChange={(event) => edit({ y_factor_id: event.target.value })}>
        {design.factors.map((factor, index) => <option key={index} value={`factor_${index + 1}`}>{factor.name}</option>)}</select></label>}
      <label>{t("rsm.plot.scale")}<select value={draft.axis_scale}
        onChange={(event) => edit({ axis_scale: event.target.value as "actual" | "coded" })}>
        <option value="actual">{t("rsm.plot.actual")}</option><option value="coded">{t("charts.coded")}</option></select></label>
      {design.factors.map((factor, index) => {
        const id = `factor_${index + 1}`;
        return id === draft.x_factor_id || id === draft.y_factor_id ? null : <label key={id}>
          {t("rsm.plot.hold")} {factor.name} {factor.unit ? `(${factor.unit})` : ""}
          <input value={holds[id] ?? ""} inputMode="decimal" onChange={(event) => {
            invalidate(); setHolds((current) => ({ ...current, [id]: event.target.value }));
          }} /></label>;
      })}
      <label>{t("rsm.plot.grid")}<input type="number" min="11" max="51" step="2" value={gridSize}
        onChange={(event) => { invalidate(); setGridSize(event.target.value); }} /></label>
      {draft.plot_kind === "contour" && <>
        <label>{t("rsm.plot.levelCount")}<input type="number" min="2" max="11" value={levelCount}
          onChange={(event) => { invalidate(); setLevelCount(event.target.value); }} /></label>
        <label>{t("rsm.plot.levels")}<input value={levels} onChange={(event) => {
          invalidate(); setLevels(event.target.value);
        }} /></label>
      </>}
    </div>
    {draft.plot_kind === "contour" && <div className="checkbox-row">
      {(["filled", "lines", "design_points"] as const).map((key) => <label key={key}>
        <input type="checkbox" checked={draft[key]} onChange={(event) => edit({ [key]: event.target.checked })} />
        {t(`rsm.plot.${key}`)}</label>)}
    </div>}
    <div className="action-row">
      <button type="button" className="secondary-button" disabled={!source || running || saving} onClick={() => void generate()}>
        <Play size={16} aria-hidden="true" />{t(running ? "rsm.plot.generating" : "rsm.plot.generate")}</button>
      <button type="button" className="secondary-button" disabled={!view || dirty || running || saving || Boolean(savedId)}
        onClick={() => void save()}><Save size={16} aria-hidden="true" />{t(saving ? "rsm.plot.saving" : "rsm.plot.save")}</button>
      <label><input type="checkbox" checked={overview} onChange={(event) => setOverview(event.target.checked)} />
        {t("rsm.plot.overview")}</label>
    </div>
    {dirty && <p role="status">{t("rsm.plot.unapplied")}</p>}
    {savedId && <p role="status">{t("rsm.plot.saved")}</p>}
    {error && <div role="alert"><p>{t("rsm.plot.error")} <code>{error}</code></p>
      <button type="button" className="secondary-button" onClick={() => setAttempt((value) => value + 1)}>
        <RefreshCw size={16} aria-hidden="true" />{t("rsm.plot.retry")}</button></div>}
    {saved.length > 0 && <label>{t("rsm.plot.savedViews")}<select value={savedId ?? ""}
      disabled={!source || running || saving}
      onChange={(event) => {
        const item = saved.find((candidate) => candidate.asset_id === event.target.value);
        if (item) void restore(item);
      }}><option value="">{t("rsm.plot.current")}</option>{saved.map((item) =>
        <option key={item.asset_id} value={item.asset_id}>{item.created_at} · {item.asset_id.slice(0, 8)}</option>)}</select></label>}
    {overview ? <DoeCompactPlotGrid>{overviews.map((item) => {
      const term = [item.settings.x_factor_id, item.settings.y_factor_id].filter(Boolean).join(":");
      return <DoeCompactPlotCard key={term} title={[item.x_axis.name, item.y_axis?.name].filter(Boolean).join(" / ")}
        status={doePlotStatus(term, analysis.result.model_selection)} meanLabel={t("rsm.plot.conditional")}>
        {(layout) => <ResponseSurfaceContourChart bundle={item} layout={layout}
          yRange={ranges[item.settings.plot_kind]} sourceKey={`${analysis.analysis_id}:overview:${term}`} />}
      </DoeCompactPlotCard>;
    })}</DoeCompactPlotGrid> : <ResponseSurfaceContourChart bundle={bundle}
      sourceKey={`${analysis.analysis_id}:${view?.view_sha256 ?? "default"}`} />}
  </section>;
}
