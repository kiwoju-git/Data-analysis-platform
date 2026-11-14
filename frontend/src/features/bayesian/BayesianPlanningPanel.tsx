import { useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowUp, ArrowLeft, ArrowRight, ChartLine, Check, ClipboardPaste, ListPlus, RefreshCw, RotateCcw, RotateCw, Save, Trash2 } from "lucide-react";
import type { BayesianStudyResponse } from "../../api/types/bayesian";
import type { DesirabilityReviewRequest } from "../../api/types/bayesianDesirability";
import type { PlanningModelDetail } from "../../api/types/boPlanning";
import { InteractiveScatterChart, type InteractiveScatterPoint } from "../../charts/InteractiveScatterChart";
import { paddedNumericRange } from "../../charts/chartScale";
import { useI18n } from "../../i18n/LocaleProvider";
import { planningMessages } from "../../i18n/boPlanning";
import { desirabilityMessages } from "../../i18n/boDesirability";
import { formatExactNumericValue as exact } from "../../statisticalNumberFormat";
import { parsePlanningPaste, parsePlanningPoint, planningInteger, planningProfilePoints, planningResponseProfilePoints, planningStudyKey, type PlanningProfileMetric } from "./boPlanningDraft";
import { useBayesianPlanning } from "./hooks/useBayesianPlanning";
import { boKernelLabel } from "./boKernelPolicy";
import { decimalLatticeValue } from "../../doe/rsmRegion";
import type { AugmentationManualSeed } from "./BayesianAugmentationPanel";
import "./boPlanning.css";
import { BayesianLooPanel } from "./BayesianLooPanel";
import { BayesianProfileGrid } from "./BayesianProfileGrid";

interface Props { study: BayesianStudyResponse; fitRequest: DesirabilityReviewRequest | null; disabled?: boolean; onConfirmed: (batchId: string) => void; onConfirmingChange?: (busy: boolean) => void; manualSeed?: AugmentationManualSeed | null }
function initialHolds(study: BayesianStudyResponse): Record<string, string> {
  return Object.fromEntries(study.factors.map(factor => {
    const value = factor.domain_kind === "discrete_numeric" && factor.step != null
      ? decimalLatticeValue(factor.low, factor.step, Math.floor((factor.high - factor.low) / factor.step / 2))
      : factor.low / 2 + factor.high / 2;
    return [factor.factor_id, value === null ? "" : String(value)];
  }));
}
export function BayesianPlanningPanel({ study, fitRequest, disabled = false, onConfirmed, onConfirmingChange, manualSeed }: Props) {
  const { locale } = useI18n(), text = planningMessages(locale);
  const state = useBayesianPlanning({ study, fitRequest, disabled, onConfirmed });
  const consumedSeed = useRef<string | null>(null), manualAction = useRef(state.startManual); manualAction.current = state.startManual;
  useEffect(() => {
    if (!manualSeed || manualSeed.studyId !== study.study_id || consumedSeed.current === manualSeed.id || disabled) return;
    consumedSeed.current = manualSeed.id;
    void manualAction.current(manualSeed.modelId, manualSeed.points, `${text.selected} ${manualSeed.id.slice(0, 8)}`);
  }, [manualSeed, study.study_id, disabled, text.selected]);
  useEffect(() => { onConfirmingChange?.(state.isConfirming); return () => onConfirmingChange?.(false); }, [state.isConfirming, onConfirmingChange]);
  const sourceKey = `${planningStudyKey(study)}:${state.model?.model_id ?? "none"}:${state.model?.snapshot_sha256 ?? "none"}`;
  const [name, setName] = useState("");
  const [count, setCount] = useState(String(Math.min(study.factors.length * 1000, 10000)));
  const [seed, setSeed] = useState("0"), [content, setContent] = useState(""), [header, setHeader] = useState(false);
  const [budget, setBudget] = useState(String(fitRequest?.total_trial_budget ?? Math.min(200, study.trial_count + 8)));
  const [pastePreview, setPastePreview] = useState<{ sourceKey: string; content: string; header: boolean; points: Record<string, number>[] } | null>(null);
  const [inputError, setInputError] = useState(false);
  const [holds, setHolds] = useState(() => initialHolds(study));
  const [axis, setAxis] = useState(study.factors[0]?.factor_id ?? "");
  const latestStudy = useRef(study); latestStudy.current = study;
  useEffect(() => {
    setPastePreview(null); setInputError(false); setContent(""); setHolds(initialHolds(latestStudy.current));
    setAxis(latestStudy.current.factors[0]?.factor_id ?? "");
  }, [sourceKey]);
  const supported = study.objective.goal_type === "desirability" && [5, 6].includes(study.study_schema_version);
  if (!supported) return <section className="bo-planning"><h3>{text.title}</h3><p>{text.unsupported}</p></section>;
  const busy = state.busy !== null, page = state.page, model = state.model;
  const canEdit = state.canMutate && page?.revision.source_is_current === true && page.revision.source_trial_count === study.trial_count;
  const countValue = planningInteger(count, 1, 10000), seedValue = planningInteger(seed, 0, 2147483647);
  const fitIsCurrent = fitRequest !== null && fitRequest.expected_history_revision_id === study.observation_history.history_revision_id && fitRequest.expected_history_sha256 === study.observation_history.observation_history_sha256;
  const budgetValue = planningInteger(budget, Math.max(2, study.trial_count + state.order.current.length), 200);
  const point = parsePlanningPoint(holds, study.factors), curve = planningProfilePoints(holds, study.factors, axis);
  const preview = pastePreview?.sourceKey === sourceKey && pastePreview.content === content && pastePreview.header === header ? pastePreview : null;
  const evaluatedRows = new Map(state.pageEvaluation?.items.map(row => [row.row_id, row]));
  const coordinates = (values: Record<string, number>) => study.factors.map(f => `${f.name}: ${exact(values[f.factor_id])}${f.unit ? ` ${f.unit}` : ""}`).join("; ");
  function editInput(action: () => void) { if (state.invalidateDraft()) { setInputError(false); action(); } }
  function validatePaste() {
    const parsed = parsePlanningPaste(content, study.factors, header);
    setInputError(parsed.error !== null);
    setPastePreview(parsed.points === null ? null : { sourceKey, content, header, points: parsed.points });
  }
  function generate(replace: boolean) {
    if (countValue === null || seedValue === null || !name.trim()) { setInputError(true); return; }
    state.createCandidates(name, { kind: "seeded_uniform", count: countValue, seed: seedValue }, replace);
  }
  function importRows(replace: boolean) {
    if (!preview || !name.trim()) { setInputError(true); return; }
    state.createCandidates(name, { kind: "explicit_rows", points: preview.points }, replace);
  }
  return <section className="bo-planning" aria-label={text.title}>
    <h3>{text.title}</h3><p>{text.meaning}</p>
    {state.isConfirming && <p role="status" className="notice-box">{text.confirmLock}</p>}
    <fieldset className="bo-planning-confirm-lock" disabled={state.isConfirming} aria-label={text.title}>
    <div className="bo-planning-actions">
      <button type="button" className="secondary-button" disabled={disabled || busy || !fitRequest || !fitIsCurrent || fitRequest.schema_version === 4 || study.status !== "active"} onClick={state.createModel}><Save size={16} aria-hidden="true" />{text.fit}</button>
      <button type="button" className="secondary-button" disabled={state.catalogLoading} onClick={() => void state.refreshCatalog()}><RefreshCw size={16} aria-hidden="true" />{text.refresh}</button>
      {busy && <span role="status">{text.busy}</span>}
    </div>
    <div className="bo-planning-fields">
      <label>{text.models}<select aria-label={text.models} value={model?.model_id ?? ""} onChange={event => { const value = event.currentTarget.value; if (value) state.openModel(value); }}><option value="">{text.choose}</option>{state.catalog.models.map(item => <option key={item.model_id} value={item.model_id}>{item.created_at} · {item.source_is_current ? text.current : text.historical}</option>)}</select></label>
      <label>{text.sets}<select aria-label={text.sets} value={page?.revision.revision_id ?? ""} onChange={event => { const value = event.currentTarget.value; if (value) state.openPage(value); }}><option value="">{text.choose}</option>{state.catalog.candidates.map(item => <option key={item.revision_id} value={item.revision_id}>{item.name} · {text.revision} {item.revision_number}</option>)}</select></label>
      <label>{text.savedSelections}<select aria-label={text.savedSelections} value={state.selection?.selection_id ?? ""} onChange={event => { const value = event.currentTarget.value; if (value) state.openSelection(value); }}><option value="">{text.choose}</option>{state.catalog.selections.map(item => <option key={item.selection_id} value={item.selection_id}>{item.created_at} · {item.selected_count}</option>)}</select></label>
    </div>
    {state.error && <div role="alert" className="notice-box notice-warning"><p>{text.error}</p><code>{state.error}</code></div>}
    {state.uncertain && <p role="status" className="notice-box notice-warning">{text.uncertain}</p>}
    {state.canRetry && <button type="button" className="secondary-button" disabled={busy || disabled} onClick={state.retry}><RefreshCw size={16} aria-hidden="true" />{text.retry}</button>}
    {(study.pending_trial_count > 0 || study.status !== "active") && <p className="notice-box">{text.pending}</p>}
    {model && <>
      <details><summary>{text.source}</summary><dl className="bo-planning-source">
        <div><dt>{text.model}</dt><dd>{model.model_id}</dd></div><div><dt>{text.modelHash}</dt><dd>{model.snapshot_sha256}</dd></div>
        <div><dt>{text.history}</dt><dd>{model.history_sha256}</dd></div>{page && <div><dt>{text.rowsHash}</dt><dd>{page.revision.rows_sha256}</dd></div>}
      </dl><p>{model.source_is_current ? text.current : text.historical}</p></details>
      <PlanningFitSummary model={model} />
      <BayesianLooPanel studyId={study.study_id} model={model} contextKey={sourceKey} disabled={disabled || busy} />
      {!state.canMutate && <p className="notice-box">{text.stale}</p>}
      <section aria-label={text.candidates}><h4>{text.candidates}</h4>
        <div className="bo-planning-fields">
          <label>{text.name}<input value={name} maxLength={120} onChange={event => { const value = event.currentTarget.value; editInput(() => setName(value)); }} /></label>
          <label>{text.count}<input inputMode="numeric" value={count} onChange={event => { const value = event.currentTarget.value; editInput(() => setCount(value)); }} /></label>
          <label>{text.seed}<input inputMode="numeric" value={seed} onChange={event => { const value = event.currentTarget.value; editInput(() => setSeed(value)); }} /></label>
        </div>
        <div className="bo-planning-actions"><button type="button" className="secondary-button" disabled={!state.canMutate || busy} onClick={() => generate(false)}><ListPlus size={16} aria-hidden="true" />{text.generate}</button>
          <button type="button" className="secondary-button" disabled={!canEdit || busy} onClick={() => generate(true)}><Save size={16} aria-hidden="true" />{text.replace}</button></div>
        <details><summary>{text.importTitle}</summary><p>{text.order}: {study.factors.map(f => `${f.factor_id} (${f.name})`).join(", ")}</p>
          <label className="bo-planning-label">{text.content}<textarea value={content} onChange={event => { const value = event.currentTarget.value; editInput(() => { setContent(value); setPastePreview(null); }); }} /></label>
          <label><input type="checkbox" checked={header} onChange={event => { const value = event.currentTarget.checked; editInput(() => { setHeader(value); setPastePreview(null); }); }} />{text.header}</label>
          <div className="bo-planning-actions"><button type="button" className="secondary-button" onClick={validatePaste}><Check size={16} aria-hidden="true" />{text.preview}</button>
            <button type="button" className="secondary-button" disabled={!state.canMutate || !preview || busy} onClick={() => importRows(false)}><ClipboardPaste size={16} aria-hidden="true" />{text.apply}</button>
            <button type="button" className="secondary-button" disabled={!canEdit || !preview || busy} onClick={() => importRows(true)}><ClipboardPaste size={16} aria-hidden="true" />{text.replaceImport}</button></div>
          {preview && <><p role="status">{text.previewReady}: {preview.points.length}</p><div className="table-wrap"><table className="result-table"><thead><tr>{study.factors.map(f => <th key={f.factor_id}>{f.name}</th>)}</tr></thead><tbody>{preview.points.slice(0, 5).map((row, index) => <tr key={index}>{study.factors.map(f => <td key={f.factor_id}>{exact(row[f.factor_id])}</td>)}</tr>)}</tbody></table></div></>}
        </details>
        {inputError && <p role="alert">{text.inputError}</p>}
        {page ? <>
          <div className="bo-planning-actions"><strong>{page.revision.name} · {text.revision} {page.revision.revision_number}</strong>
            <button type="button" className="secondary-button" disabled={busy || page.offset === 0} aria-label={text.previous} title={text.previous} onClick={() => state.openPage(page.revision.revision_id, Math.max(0, page.offset - page.limit))}><ArrowLeft size={16} aria-hidden="true" /></button>
            <span>{page.offset + 1}–{Math.min(page.offset + page.items.length, page.revision.row_count)} / {page.revision.row_count}</span>
            <button type="button" className="secondary-button" disabled={busy || page.offset + page.limit >= page.revision.row_count} aria-label={text.next} title={text.next} onClick={() => state.openPage(page.revision.revision_id, page.offset + page.limit)}><ArrowRight size={16} aria-hidden="true" /></button>
            <button type="button" className="secondary-button" disabled={busy || disabled || !page.items.length} onClick={state.evaluatePage}><ChartLine size={16} aria-hidden="true" />{text.evaluate}</button></div>
          {state.pageEvaluation && !state.pageEvaluation.eligibility_is_current && <p className="notice-box">{text.eligibilityOld}</p>}
          <div className="table-wrap"><table className="result-table"><caption className="bo-planning-caption">{text.candidates}</caption><thead><tr><th>{text.select}</th><th>{text.row}</th>{study.factors.map(f => <th key={f.factor_id}>{f.name}{f.unit ? ` (${f.unit})` : ""}</th>)}<th>{text.eligibility}</th><th>{text.expected}</th><th>{text.sd}</th><th>{text.ei}</th><th>{text.distance}</th></tr></thead>
            <tbody>{page.items.map(row => { const evaluated = evaluatedRows.get(row.row_id), chosen = state.order.current.some(item => item.row_id === row.row_id); return <tr key={row.row_id}>
              <td><input type="checkbox" aria-label={`${text.select}: ${row.source_row_number}`} checked={chosen} disabled={!canEdit || !row.eligible || (!chosen && state.order.current.length >= 8)} onChange={() => state.selectRow(row)} /></td>
              <th scope="row">{row.source_row_number}</th>{study.factors.map(f => <td key={f.factor_id}>{exact(row.actual_coordinates[f.factor_id])}</td>)}<td>{row.eligible ? text.yes : <details><summary>{text.no}</summary>{!row.novel && <p>{text.notNovel}</p>}{!row.constraints_satisfied && <p>{text.constraintFailure}</p>}</details>}</td>
              <td>{evaluated ? exact(evaluated.desirability_moments.mean) : text.none}</td><td>{evaluated ? exact(Math.sqrt(evaluated.desirability_moments.variance)) : text.none}</td><td>{evaluated ? exact(evaluated.acquisition.value) : text.none}</td><td>{row.nearest_existing_distance === null ? "-" : exact(row.nearest_existing_distance)}</td>
            </tr>; })}</tbody></table></div>
        </> : <p>{text.empty}</p>}
      </section>
      <section aria-label={text.selected}><h4>{text.selected}</h4><p>{text.selectionMeaning}</p>
        <div className="bo-planning-actions">{([{ label: text.undo, icon: RotateCcw, action: state.undo, enabled: state.order.past.length > 0 }, { label: text.redo, icon: RotateCw, action: state.redo, enabled: state.order.future.length > 0 }, { label: text.clear, icon: Trash2, action: state.clearSelection, enabled: state.order.current.length > 0 }]).map(({ label, icon: Icon, action, enabled }) => <button key={label} type="button" className="secondary-button bo-planning-icon" title={label} aria-label={label} disabled={!canEdit || !enabled} onClick={action}><Icon size={16} aria-hidden="true" /></button>)}</div>
        <ol className="bo-planning-selection">{state.order.current.map((row, index) => <li key={row.row_id}><strong>{index + 1}.</strong><span className="bo-planning-coordinates">{coordinates(row.actual_coordinates)}</span>
          <button type="button" className="secondary-button bo-planning-icon" disabled={!canEdit || index === 0} title={text.up} aria-label={`${text.up}: ${index + 1}`} onClick={() => state.moveRow(index, -1)}><ArrowUp size={16} aria-hidden="true" /></button>
          <button type="button" className="secondary-button bo-planning-icon" disabled={!canEdit || index === state.order.current.length - 1} title={text.down} aria-label={`${text.down}: ${index + 1}`} onClick={() => state.moveRow(index, 1)}><ArrowDown size={16} aria-hidden="true" /></button></li>)}</ol>
        {!state.order.current.length && <p>{text.noSelection}</p>}
        <label className="bo-planning-label">{text.totalBudget}<input inputMode="numeric" value={budget} onChange={event => { const value = event.currentTarget.value; editInput(() => setBudget(value)); }} /></label>
        <div className="bo-planning-actions"><button type="button" className="secondary-button" disabled={!canEdit || busy || !state.order.current.length || budgetValue === null} onClick={() => { if (budgetValue !== null) state.saveSelection(budgetValue); }}><Save size={16} aria-hidden="true" />{text.review}</button>
          <button type="button" className="secondary-button" disabled={!canEdit || busy || !state.order.current.length || !page} onClick={() => { if (page) state.createCandidates(page.revision.name, { kind: "remove_rows", row_ids: state.order.current.map(row => row.row_id) }, true); }}><Trash2 size={16} aria-hidden="true" />{text.remove}</button></div>
        {state.selection && <><h4>{text.reviewed}</h4><div className="table-wrap"><table className="result-table"><thead><tr><th>{text.rank}</th><th>{text.expected}</th><th>{text.ei}</th><th>{text.marginal}</th></tr></thead><tbody>{state.selection.calculation.items.map(item => <tr key={item.row_id}><th>{item.rank}</th><td>{exact(item.desirability_moments.mean)}</td><td>{exact(item.acquisition.value)}</td><td>{exact(item.planning.score)}</td></tr>)}</tbody></table></div>
          {state.selection.confirmed_batch_id ? <div className="bo-planning-actions"><span>{text.confirmed}: <code>{state.selection.confirmed_batch_id}</code></span><button type="button" className="secondary-button" onClick={() => { if (state.selection?.confirmed_batch_id) onConfirmed(state.selection.confirmed_batch_id); }}>{text.openBatch}</button></div> : <button type="button" className="primary-button" disabled={!canEdit || busy || !state.selection.source_is_current || state.selection.request.expected_trial_count !== study.trial_count} onClick={state.confirm}><Check size={16} aria-hidden="true" />{text.confirm}</button>}
        </>}
      </section>
      <section aria-label={text.profiler}><h4>{text.profiler}</h4><p>{text.profileMeaning}</p>
        <fieldset><legend>{text.holds}</legend><div className="bo-planning-fields">{study.factors.map(factor => <label key={factor.factor_id}>{factor.name}{factor.unit ? ` (${factor.unit})` : ""}
          <input inputMode="decimal" value={holds[factor.factor_id] ?? ""} onChange={event => { const value = event.currentTarget.value; if (state.invalidateProfile()) setHolds(previous => ({ ...previous, [factor.factor_id]: value })); }} /></label>)}</div></fieldset>
        <label className="bo-planning-label">{text.axis}<select aria-label={text.axis} value={axis} onChange={event => { const value = event.currentTarget.value; if (state.invalidateProfile()) setAxis(value); }}>{study.factors.map(f => <option key={f.factor_id} value={f.factor_id}>{f.name}</option>)}</select></label>
        <div className="bo-planning-actions"><button type="button" className="secondary-button" disabled={disabled || busy || !point} onClick={() => { if (point) state.evaluateProfile([point], null); }}><ChartLine size={16} aria-hidden="true" />{text.point}</button>
          <button type="button" className="secondary-button" disabled={disabled || busy || !curve} onClick={() => { if (curve) state.evaluateProfile(curve, axis); }}><ChartLine size={16} aria-hidden="true" />{text.curve}</button></div>
        {(!point || !curve) && <p>{text.profileInvalid}</p>}
        {state.profile && <>
          {!state.profile.response.eligibility_is_current && <p>{text.eligibilityOld}</p>}
          {state.profile.axis && <PlanningProfileChart profile={state.profile} study={study} sourceKey={`${model.model_id}:${model.snapshot_sha256}:${state.profile.response.request_sha256}`} />}
          <div className="table-wrap"><table className="result-table"><caption className="bo-planning-caption">{text.evaluated}</caption><thead><tr><th>{text.holds}</th><th>{text.response}</th><th>{text.mean}</th><th>{text.latent}</th><th>{text.predictive}</th></tr></thead><tbody>{state.profile.response.items.flatMap(row => row.response_predictions.map(response => <tr key={`${row.row_id}:${response.response_id}`}><td>{coordinates(row.actual_coordinates)}</td><th scope="row">{study.objective.goal_type === "desirability" ? study.objective.responses.find(r => r.response_id === response.response_id)?.name ?? response.response_id : response.response_id}</th><td>{exact(response.mean_raw)}</td><td>{exact(response.latent_standard_deviation_raw)}</td><td>{exact(response.predictive_standard_deviation_raw)}</td></tr>))}</tbody></table></div>
          {state.profile.axis === null && <button type="button" className="secondary-button" disabled={!canEdit || busy || !page || !state.profile.response.eligibility_is_current} onClick={() => { if (page && state.profile) state.createCandidates(page.revision.name, { kind: "append_rows", points: state.profile.points }, true); }}><ListPlus size={16} aria-hidden="true" />{text.append}</button>}
        </>}
      </section>
    </>}
    </fieldset>
  </section>;
}

export function PlanningProfileChart({ profile, study, sourceKey }: { profile: NonNullable<ReturnType<typeof useBayesianPlanning>["profile"]>; study: BayesianStudyResponse; sourceKey: string }) {
  const { locale } = useI18n(), text = planningMessages(locale);
  const [view, setView] = useState("desirability");
  const [metric, setMetric] = useState<PlanningProfileMetric>("mean_raw");
  const responses = study.objective.goal_type === "desirability" ? study.objective.responses : [];
  const selected = responses.find(response => view === `response:${response.response_id}`);
  const factor = study.factors.find(f => f.factor_id === profile.axis);
  if (!factor) return null;
  const metricLabels = { mean_raw: text.mean, latent_standard_deviation_raw: text.latent, predictive_standard_deviation_raw: text.predictive };
  const constraints = new Map(profile.response.items.map(row => [row.row_id, row.constraints_satisfied]));
  const constraintLabel = (satisfied: boolean) => satisfied ? text.constraintsSatisfied : text.constraintFailure;
  const points: InteractiveScatterPoint[] = selected ? planningResponseProfilePoints(profile.response, factor.factor_id, selected.response_id, metric).map(row => {
    const satisfied = constraints.get(row.rowId) === true, constraint = constraintLabel(satisfied);
    return {
    id: `${row.rowId}:${selected.response_id}:${metric}`, seriesId: "response", x: row.x, y: row.value,
    marker: satisfied ? "circle" : "diamond", warning: !satisfied, markerRadius: 3, className: "bo-planning-profile-mean", title: metricLabels[metric],
    ariaLabel: `${factor.name}: ${exact(row.x)}, ${selected.name}: ${exact(row.value)}${selected.unit ? ` ${selected.unit}` : ""}, ${text.constraintStatus}: ${constraint}`,
    details: [{ label: factor.name, value: exact(row.x) }, { label: `${selected.name}: ${metricLabels[metric]}`, value: `${exact(row.value)}${selected.unit ? ` ${selected.unit}` : ""}` }, { label: text.constraintStatus, value: constraint }],
  }; }) : profile.response.items.flatMap(row => (["mean", "sd"] as const).map((kind, i) => {
    const value = kind === "mean" ? row.desirability_moments.mean : Math.sqrt(row.desirability_moments.variance);
    const label = kind === "mean" ? text.expected : text.sd, constraint = constraintLabel(row.constraints_satisfied);
    return { id: `${row.row_id}:${kind}`, seriesId: kind, x: row.actual_coordinates[factor.factor_id], y: value,
      marker: !row.constraints_satisfied ? "diamond" : i === 0 ? "circle" : "square", warning: !row.constraints_satisfied, markerRadius: 3, className: `bo-planning-profile-${kind}`,
      title: label, ariaLabel: `${factor.name}: ${exact(row.actual_coordinates[factor.factor_id])}, ${label}: ${exact(value)}, ${text.constraintStatus}: ${constraint}`,
      details: [{ label: factor.name, value: exact(row.actual_coordinates[factor.factor_id]) }, { label, value: exact(value) }, { label: text.constraintStatus, value: constraint }], };
  }));
  const series = selected ? [{ id: "response", label: metricLabels[metric], className: "bo-planning-profile-mean", connect: "line" as const, pointIds: points.map(point => point.id) }]
    : (["mean", "sd"] as const).map(kind => ({ id: kind, label: kind === "mean" ? text.expected : text.sd, className: `bo-planning-profile-${kind}`, connect: "line" as const, pointIds: points.filter(p => p.seriesId === kind).map(p => p.id) }));
  return <><div className="bo-planning-fields"><label>{text.profileQuantity}<select aria-label={text.profileQuantity} value={selected ? view : "desirability"} onChange={event => setView(event.currentTarget.value)}><option value="desirability">{text.desirability}</option>{responses.map(response => <option key={response.response_id} value={`response:${response.response_id}`}>{response.name}</option>)}</select></label>
    {selected && <label>{text.profileMetric}<select aria-label={text.profileMetric} value={metric} onChange={event => setMetric(event.currentTarget.value as PlanningProfileMetric)}>{(Object.keys(metricLabels) as PlanningProfileMetric[]).map(key => <option key={key} value={key}>{metricLabels[key]}</option>)}</select></label>}</div>
    <div className="bo-profile-detail"><InteractiveScatterChart chartId="bo-planning-profile" sourceKey={`${sourceKey}:${selected ? `response:${selected.response_id}` : "composite"}:${metric}`} title={selected ? `${selected.name}: ${metricLabels[metric]}` : text.profiler} description={text.profileMeaning}
      points={points} annotations={[]} emptyLabel="-" xLabel={factor.name} xUnit={factor.unit} yLabel={selected?.name ?? text.desirability} yUnit={selected?.unit ?? null}
      xRange={{ min: factor.low, max: factor.high }} yRange={selected ? paddedNumericRange(points.map(point => point.y)) : { min: 0, max: 1 }} series={series} collapsibleDetails /></div>
    <BayesianProfileGrid sourceKey={sourceKey} axis={{ ...factor, category: false, range: { min: factor.low, max: factor.high } }} responses={responses} rows={profile.response.items} /></>;
}

export function PlanningFitSummary({ model: source }: { model: Pick<PlanningModelDetail, "model_id" | "snapshot_sha256" | "objective" | "response_models" | "warnings"> }) {
  const { locale } = useI18n(), text = planningMessages(locale), fit = desirabilityMessages(locale);
  const warnings: Record<string, string> = {
    bayesian_optimization_model_convergence_warning: text.convergenceWarning,
    bayesian_surrogate_signal_bound: text.signalBoundWarning,
    bayesian_surrogate_noise_bound: text.noiseBoundWarning,
    bayesian_optimization_constant_objective: text.constantWarning,
  };
  return <section aria-label={fit.fitTitle}>
    <h4>{fit.fitTitle}</h4><p>{fit.fitMeaning}</p>
    {source.warnings.length > 0 && <div className="notice-box notice-warning" role="status"><h5>{text.fitWarnings}</h5><ul>{[...new Set(source.warnings)].map(code => <li key={code}>{warnings[code] ?? text.unknownWarning} <code>{code}</code></li>)}</ul></div>}
    {source.response_models.map(({ response_id, model }) => {
      const response = source.objective.responses.find(item => item.response_id === response_id);
      return <section key={response_id} aria-label={`${fit.fitTitle}: ${response?.name ?? response_id}`}>
        <h5>{response?.name ?? response_id}</h5><dl className="bo-planning-source">
          <div><dt>{fit.kernel}</dt><dd>{boKernelLabel(model.signal_kernel.family)}</dd></div>
          <div><dt>{fit.noise}</dt><dd>{model.noise.mode === "estimate" ? fit.estimate : model.noise.mode === "fixed" ? fit.fixed : fit.near}</dd></div>
          <div><dt>{fit.fittedNoise}</dt><dd>{exact(model.observation_noise_sd_raw)}{response?.unit ? ` ${response.unit}` : ""}</dd></div>
          <div><dt>{text.jitter}</dt><dd>{exact(model.jitter)}</dd></div>
          <div><dt>{fit.selectedLml}</dt><dd>{exact(model.log_marginal_likelihood)}</dd></div>
          <div><dt>{fit.fitEvaluations}</dt><dd>{model.optimizer.evaluations}{model.schema_version === 5 ? ` / ${model.optimizer.max_evaluations}` : ""}</dd></div>
          <div><dt>{text.rawCount}</dt><dd>{model.raw_observation_count}</dd></div><div><dt>{text.effectiveCount}</dt><dd>{model.effective_training_count}</dd></div>
          <div><dt>{text.optimized}</dt><dd>{model.optimizer.optimized ? fit.yes : fit.no}</dd></div>
          <div><dt>{fit.randomRestarts}</dt><dd>{model.optimizer.restarts}</dd></div>
        </dl>
        <div className="table-wrap"><table className="result-table"><caption className="bo-planning-caption">{text.optimizer}: {model.optimizer.name}</caption><thead><tr><th>{fit.start}</th><th>{fit.converged}</th><th>{text.termination}</th></tr></thead><tbody>{model.optimizer.starts.map((start, index) => <tr key={index}><th scope="row">{index + 1}</th><td>{start.success ? fit.yes : fit.no}</td><td><code>{start.termination_reason}</code></td></tr>)}</tbody></table></div>
        {model.schema_version === 5 ? <>
          <p>{fit.deterministicStarts}: {model.fit_diagnostics.deterministic_start_count}</p>
          <div className="table-wrap"><table className="result-table"><caption className="bo-planning-caption">{fit.fitTitle}</caption><thead><tr><th>{fit.start}</th><th>{fit.initialLml}</th><th>{fit.bestLml}</th><th>{fit.finalLml}</th><th>{fit.fitEvaluations}</th></tr></thead><tbody>{model.optimizer.starts.map((start, index) => <tr key={index}><th scope="row">{index + 1}</th><td>{exact(-model.fit_diagnostics.start_initial_negative_log_likelihoods[index])}</td><td>{exact(-model.fit_diagnostics.start_best_evaluations[index].negative_log_likelihood)}</td><td>{exact(-start.negative_log_likelihood)}</td><td>{start.evaluations}</td></tr>)}</tbody></table></div>
          <details><summary>{fit.boundaryHits}</summary>{model.fit_diagnostics.bound_hits.length > 0 ? <ul>{model.fit_diagnostics.bound_hits.map((hit, index) => <li key={index}>{hit.parameter === "signal_amplitude" ? fit.signalAmplitude : hit.parameter === "measurement_variance" ? fit.measurementVariance : `${fit.lengthScale} ${(hit.factor_index ?? 0) + 1}`}: {hit.side === "lower" ? fit.lowerBound : fit.upperBound} = {exact(hit.value)}</li>)}</ul> : <p>{fit.noBoundHits}</p>}</details>
          <details><summary>{fit.fitScreening}</summary><div className="table-wrap"><table className="result-table"><thead><tr><th>{fit.start}</th><th>{fit.logParameters}</th><th>LML</th></tr></thead><tbody>{model.fit_diagnostics.screening.map((row, index) => <tr key={index}><th scope="row">{index + 1}</th><td>{row.log_parameters.map(value => exact(value)).join(", ")}</td><td>{exact(-row.negative_log_likelihood)}</td></tr>)}</tbody></table></div><code>{model.fit_diagnostics.policy}</code></details>
        </> : <p>{text.legacyFitDiagnostics}</p>}
      </section>;
    })}
  </section>;
}
