import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Check, FolderOpen, ListPlus, RefreshCw } from "lucide-react";
import type { BayesianStudyResponse } from "../../api/types/bayesian";
import type { AugmentationCalculation, AugmentationPolicy, AugmentationSelectionResponse } from "../../api/types/boAugmentation";
import type { MixedAugmentationCalculation, MixedStudyResponse } from "../../api/types/boMixed";
import { useI18n } from "../../i18n/LocaleProvider";
import { augmentationCriterionLabel, augmentationMessages, augmentationPolicyLabel, augmentationWarningLabel } from "../../i18n/boAugmentation";
import { parseDoeResponseNumber } from "../../doe/doeResponsePaste";
import { planningMessages } from "../../i18n/boPlanning";
import { formatExactNumericValue as exact } from "../../statisticalNumberFormat";
import { augmentationSource, modelFreeAugmentation } from "./boAugmentationDraft";
import { currentPlanningModel, parsePlanningPaste, planningId, planningInteger, planningStudyKey } from "./boPlanningDraft";
import { useBayesianAugmentation } from "./hooks/useBayesianAugmentation";
import { PlanningFitSummary } from "./BayesianPlanningPanel";
import { BayesianAutoStrategyPanel } from "./BayesianAutoStrategyPanel";
import { BayesianAutoEvidence } from "./BayesianAutoEvidence";
import { autoEvidenceMessages } from "../../i18n/boAutoEvidence";
import "./boPlanning.css";

export interface AugmentationManualSeed { id: string; studyId: string; modelId: string; points: Record<string, number>[] }
interface Props { study: BayesianStudyResponse; disabled: boolean; onConfirmed: (id: string) => void; onConfirmingChange: (value: boolean) => void; onManual?: (seed: AugmentationManualSeed) => void }
export function BayesianAugmentationPanel(props: Props) {
  return <AugmentationBody {...props} />;
}
function AugmentationBody({ study, disabled, onConfirmed, onConfirmingChange, onManual }: Props) {
  const state = useBayesianAugmentation({ study, disabled, onConfirmed });
  const { locale } = useI18n(), text = augmentationMessages(locale), common = planningMessages(locale);
  const [name, setName] = useState(""), [count, setCount] = useState("128"), [seed, setSeed] = useState("42"), [tolerance, setTolerance] = useState("0.000001");
  const [content, setContent] = useState(""), [header, setHeader] = useState(false);
  const [previewSnapshot, setPreview] = useState<{ sourceKey: string; content: string; header: boolean; points: Record<string, number>[] } | null>(null);
  const [inputError, setInputError] = useState(false), [savedId, setSavedId] = useState("");
  const manualSequence = useRef(0);
  const sourceKey = planningStudyKey(study);
  const preview = previewSnapshot?.sourceKey === sourceKey && previewSnapshot.content === content && previewSnapshot.header === header ? previewSnapshot.points : null;
  useEffect(() => { setName(""); setCount("128"); setSeed("42"); setTolerance("0.000001"); setContent(""); setHeader(false); setPreview(null); setInputError(false); setSavedId(""); }, [sourceKey]);
  const lock = disabled || state.busy !== null || state.isConfirming;
  useEffect(() => { onConfirmingChange(state.isConfirming); return () => onConfirmingChange(false); }, [state.isConfirming, onConfirmingChange]);
  function edit(action: () => void) { if (state.invalidateDraft()) { action(); setInputError(false); } }
  function generate(replace: boolean) {
    const size = planningInteger(count, 1, 10000), randomSeed = planningInteger(seed, 0, 2147483647);
    const epsilon = parseDoeResponseNumber(tolerance);
    if (size === null || randomSeed === null || epsilon === null || epsilon < 1e-12 || epsilon > .1) { setInputError(true); return; }
    state.createCandidates(name.trim() || text.defaults, { kind: "seeded_uniform", count: size, seed: randomSeed }, tolerance, replace);
  }
  function validateImport() { const parsed = parsePlanningPaste(content, study.factors, header); setPreview(parsed.points === null ? null : { sourceKey, content, header, points: parsed.points }); setInputError(parsed.error !== null); }
  function importRows(replace: boolean) { const epsilon = parseDoeResponseNumber(tolerance); if (epsilon === null || epsilon < 1e-12 || epsilon > .1) { setInputError(true); return; } if (preview) state.createCandidates(name.trim() || text.defaults, { kind: "explicit_rows", points: preview }, tolerance, replace); }
  const page = state.page, modelFree = modelFreeAugmentation(state.draft.policy);
  const allContinuous = study.factors.every(factor => factor.domain_kind !== "discrete_numeric");
  const strategies: AugmentationPolicy[] = [...(allContinuous ? ["greedy_incremental_maxpro_v1" as const] : []), "greedy_mixed_maximin_v1", "refine_ei_alternating_desirability_response_sd_v2", "confirm_mean_then_competitive_sd_v1"];
  if (!strategies.includes(state.draft.policy)) strategies.push(state.draft.policy);
  const meaning = state.draft.policy === "greedy_incremental_maxpro_v1" ? text.maxproMeaning : state.draft.policy === "greedy_mixed_maximin_v1" ? text.maximinMeaning : state.draft.policy === "confirm_mean_then_competitive_sd_v1" ? text.confirmMeaning : text.refineMeaning;
  const manualAvailable = state.selection !== null && state.model !== null && currentPlanningModel(state.model, study) && state.selection.source_is_current;
  return <section className="bo-planning bo-augmentation" aria-label={text.title}>
    <h3>{text.title}</h3><p>{text.policyMeaning}</p>
    <button type="button" className="secondary-button" disabled={lock || state.catalogLoading} onClick={() => void state.refresh()}><RefreshCw size={16} aria-hidden="true" />{common.refresh}</button>
    {state.isConfirming && <p role="status">{common.confirmLock}</p>}
    {state.error && <div className="notice-box notice-warning" role="alert"><p>{common.error}</p><code>{state.error}</code>{state.canRetry && <><p>{common.uncertain}</p><button className="secondary-button" type="button" disabled={lock} onClick={state.retry}><RefreshCw size={16} aria-hidden="true" />{common.retry}</button></>}</div>}
    <fieldset disabled={lock} className="bo-planning-fieldset"><legend>{text.candidates}</legend>
      <div className="bo-planning-fields"><label>{common.name}<input value={name} maxLength={120} placeholder={text.defaults} onChange={event => { const value = event.currentTarget.value; edit(() => setName(value)); }} /></label>
        <label>{common.count}<input inputMode="numeric" value={count} onChange={event => { const value = event.currentTarget.value; edit(() => setCount(value)); }} /></label>
        <label>{common.seed}<input inputMode="numeric" value={seed} onChange={event => { const value = event.currentTarget.value; edit(() => setSeed(value)); }} /></label>
        <label>{text.duplicate}<input inputMode="decimal" value={tolerance} onChange={event => { const value = event.currentTarget.value; edit(() => setTolerance(value)); }} /></label></div>
      <div className="bo-planning-actions"><button type="button" className="secondary-button" disabled={study.status !== "active"} onClick={() => generate(false)}><ListPlus size={16} aria-hidden="true" />{common.generate}</button>
        <button type="button" className="secondary-button" disabled={!page || study.status !== "active"} onClick={() => generate(true)}>{common.replace}</button></div>
      <details><summary>{common.importTitle}</summary><p>{common.order}: {study.factors.map(factor => factor.name).join(" / ")}</p>
        <label>{common.content}<textarea rows={5} value={content} onChange={event => { const value = event.currentTarget.value; edit(() => { setContent(value); setPreview(null); }); }} /></label>
        <label className="checkbox-label"><input type="checkbox" checked={header} onChange={event => { const value = event.currentTarget.checked; edit(() => { setHeader(value); setPreview(null); }); }} />{common.header}</label>
        <div className="bo-planning-actions"><button type="button" className="secondary-button" onClick={validateImport}><Check size={16} aria-hidden="true" />{common.preview}</button>
          <button type="button" className="secondary-button" disabled={!preview || study.status !== "active"} onClick={() => importRows(false)}>{common.apply}</button>
          <button type="button" className="secondary-button" disabled={!preview || !page || study.status !== "active"} onClick={() => importRows(true)}>{common.replaceImport}</button></div>
        {preview && <p>{common.previewReady}: {preview.length}</p>}</details>
      {inputError && <p role="alert">{common.inputError}</p>}
      <label>{common.sets}<select aria-label={common.sets} value={page?.revision.revision_id ?? ""} onChange={event => state.openPage(event.currentTarget.value)}><option value="">{common.choose}</option>{state.catalog.candidates.map(item => <option key={item.revision_id} value={item.revision_id}>{item.name} / {item.revision_number} / {item.source_is_current ? common.current : common.historical}</option>)}</select></label>
    </fieldset>
    {page && <><p>{text.displayLimit}</p><p>{common.revision}: {page.revision.revision_number} · {page.revision.eligible_count}/{page.revision.row_count} · {page.revision.source_is_current ? common.current : common.historical}</p>
      <div className="table-wrap"><table className="result-table"><caption className="bo-planning-caption">{text.candidates}</caption><thead><tr><th>{common.row}</th>{study.factors.map(factor => <th key={factor.factor_id}>{factor.name}{factor.unit ? ` (${factor.unit})` : ""}</th>)}<th>{text.constraint}</th><th>{text.novelty}</th><th>{common.distance}</th></tr></thead>
        <tbody>{page.items.map(row => <tr key={row.row_id}><th scope="row">{row.source_row_number}</th>{study.factors.map(factor => <td key={factor.factor_id}>{exact(row.actual_coordinates[factor.factor_id])}</td>)}<td>{row.constraints_satisfied ? common.yes : common.no}</td><td>{row.novel ? common.yes : common.no}</td><td>{row.nearest_existing_distance === null ? "-" : exact(row.nearest_existing_distance)}</td></tr>)}</tbody></table></div>
      <div className="bo-planning-actions"><button type="button" className="secondary-button" disabled={lock || page.offset === 0} onClick={() => state.openPage(page.revision.revision_id, Math.max(0, page.offset - page.limit))}><ArrowLeft size={16} aria-hidden="true" />{common.previous}</button>
        <span>{page.offset + 1}–{page.offset + page.items.length} / {page.revision.row_count}</span><button type="button" className="secondary-button" disabled={lock || page.offset + page.items.length >= page.revision.row_count} onClick={() => state.openPage(page.revision.revision_id, page.offset + page.limit)}>{common.next}<ArrowRight size={16} aria-hidden="true" /></button></div></>}
    <fieldset disabled={lock} className="bo-planning-fieldset"><legend>{text.policy}</legend>
      <label>{text.policy}<select aria-label={text.policy} value={state.draft.policy} onChange={event => state.updateDraft("policy", event.currentTarget.value as AugmentationPolicy)}>{strategies.map(policy => <option key={policy} value={policy}>{augmentationPolicyLabel(policy, locale)}</option>)}</select></label>
      <p>{meaning}</p>{modelFree && <p>{text.noModel}</p>}<label>{common.models}<select aria-label={common.models} value={state.model?.model_id ?? ""} onChange={event => state.openModel(event.currentTarget.value)}><option value="">{common.choose}</option>{state.catalog.models.map(item => <option key={item.model_id} value={item.model_id}>{item.model_id} / {item.source_is_current ? common.current : common.historical}</option>)}</select></label>{!modelFree && <p>{text.modelRequired}</p>}
      {state.model && <BayesianAutoStrategyPanel studyId={study.study_id} model={state.model}
        contextKey={`${sourceKey}:${page?.revision.revision_id ?? ""}:${JSON.stringify(state.draft)}`} kinds={study.factors.map(factor => factor.domain_kind ?? "continuous")}
        disabled={lock} onApply={state.applyAuto} onAdviceEdit={state.clearAuto} />}
      {state.autoReference && <p role="status">{autoEvidenceMessages(locale).attached}: {exact(state.autoReference.r_squared_threshold)}</p>}
      <div className="bo-planning-fields">{([ ["batchSize", text.batch], ["budget", common.totalBudget], ["distance", text.spacing], ["evaluations", text.evaluations], ["moments", text.moments], ["seconds", text.seconds] ] as const).map(([field, label]) => <label key={field}>{label}<input inputMode={field === "distance" ? "decimal" : "numeric"} value={state.draft[field]} onChange={event => state.updateDraft(field, event.currentTarget.value)} /></label>)}</div>
      {!state.canReview && <p>{study.pending_trial_count > 0 ? text.pending : text.invalid}</p>}
      <button type="button" className="secondary-button" disabled={!state.canReview} onClick={state.review}><ListPlus size={16} aria-hidden="true" />{text.review}</button>
    </fieldset>
    {state.model && !modelFree && <PlanningFitSummary model={state.model} />}
    <details><summary>{text.openReview}</summary><label>{text.reviewId}<input value={savedId} disabled={lock} onChange={event => setSavedId(event.currentTarget.value)} /></label><button type="button" className="secondary-button" disabled={lock || !planningId(savedId)} onClick={() => state.openSelection(savedId)}><FolderOpen size={16} aria-hidden="true" />{text.openReview}</button></details>
    {state.selection && <><AugmentationSelectionDetails selection={state.selection} study={study} /><div className="bo-planning-actions">
      <button type="button" className="primary-button" disabled={lock || !state.canConfirm} onClick={state.confirm}><Check size={16} aria-hidden="true" />{common.confirm}</button>
      {state.selection.confirmed_batch_id && <button type="button" className="secondary-button" onClick={() => onConfirmed(state.selection!.confirmed_batch_id!)}>{common.openBatch}</button>}
      {onManual && <button type="button" className="secondary-button" disabled={lock || !manualAvailable} onClick={() => { if (state.selection && state.model) onManual({ id: `${state.selection.selection_id}:${++manualSequence.current}`, studyId: study.study_id, modelId: state.model.model_id, points: state.selection.calculation.selected_rows.map(row => ({ ...row.actual_coordinates })) }); }}><ListPlus size={16} aria-hidden="true" />{text.manual}</button>}
    </div></>}
    {state.busy && <p role="status">{common.busy}</p>}
  </section>;
}

export function AugmentationSelectionDetails({ selection, study }: { selection: AugmentationSelectionResponse; study: BayesianStudyResponse }) {
  const { locale } = useI18n(), text = augmentationMessages(locale), common = planningMessages(locale);
  const current = sameSource(selection, study);
  return <section aria-label={text.saved}><h4>{text.saved}</h4><p>{text.immutable}</p><dl className="bo-planning-source">
    <div><dt>{text.reviewId}</dt><dd>{selection.selection_id}</dd></div><div><dt>{common.selectionHash}</dt><dd>{selection.result_sha256}</dd></div><div><dt>{common.rowsHash}</dt><dd>{selection.request.expected_rows_sha256}</dd></div>
    <div><dt>{common.model}</dt><dd>{selection.model_id ?? text.noModel}</dd></div><div><dt>{common.history}</dt><dd>{selection.request.expected_history_sha256}</dd></div></dl>
    <p>{current ? common.current : common.historical}</p><AugmentationTraceTable calculation={selection.calculation} study={study} />
  </section>;
}
function sameSource(selection: AugmentationSelectionResponse, study: BayesianStudyResponse) {
  const source = augmentationSource(study);
  return selection.source_is_current && selection.request.expected_history_revision_id === source.expected_history_revision_id && selection.request.expected_history_sha256 === source.expected_history_sha256 && selection.request.expected_trial_count === source.expected_trial_count;
}
export function AugmentationTraceTable({ calculation, study }: { calculation: AugmentationCalculation | MixedAugmentationCalculation; study: BayesianStudyResponse | MixedStudyResponse }) {
  const { locale } = useI18n(), text = augmentationMessages(locale), common = planningMessages(locale), trace = calculation.augmentation;
  return <><p>{augmentationPolicyLabel(trace.policy, locale)}</p><div className="table-wrap"><table className="result-table"><caption className="bo-planning-caption">{text.trace}</caption><thead><tr><th>{common.rank}</th>{study.factors.map(factor => <th key={factor.factor_id}>{factor.name}{factor.unit ? ` (${factor.unit})` : ""}</th>)}<th>{text.criterion}</th><th>{text.score}</th><th>{common.distance}</th><th>{text.selectedDistance}</th><th>{text.compared}</th><th>{text.threshold}</th><th>{common.expected}</th><th>{common.sd}</th></tr></thead>
    <tbody>{trace.steps.map((step, index) => { const row = calculation.selected_rows[index]; return <tr key={step.row_id}><th scope="row">{step.rank}</th>{study.factors.map(factor => { const value = row.actual_coordinates[factor.factor_id]; return <td key={factor.factor_id}>{typeof value === "string" ? value : exact(value)}</td>; })}<td>{augmentationCriterionLabel(step.criterion, locale)}</td><td>{exact(step.score)}<br />{step.score_scale === "natural_log" ? text.log : text.original} · {step.optimization_direction === "minimize" ? text.minimize : text.maximize}</td><td>{exact(step.nearest_existing_distance)}</td><td>{step.nearest_selected_distance === null ? "-" : exact(step.nearest_selected_distance)}</td><td>{step.compared_candidate_count}</td><td>{step.competitive_threshold === null ? "-" : exact(step.competitive_threshold)}</td><td>{"desirability_moments" in row ? exact(row.desirability_moments.mean) : text.unavailable}</td><td>{"desirability_moments" in row ? exact(Math.sqrt(row.desirability_moments.variance)) : text.unavailable}</td></tr>; })}</tbody></table></div>
    <dl className="bo-planning-source"><div><dt>{text.referenceCount}</dt><dd>{trace.reference_count}</dd></div><div><dt>{text.collisions}</dt><dd>{trace.projection_collisions}</dd></div><div><dt>{text.evaluations}</dt><dd>{trace.evaluations} / {trace.max_evaluations}</dd></div><div><dt>{text.moments}</dt><dd>{calculation.prediction_evaluations} / {calculation.max_moment_evaluations}</dd></div></dl>
    {calculation.selected_rows.some(row => "response_predictions" in row) && <div className="table-wrap"><table className="result-table"><caption className="bo-planning-caption">{common.evaluated}</caption><thead><tr><th>{common.rank}</th><th>{common.response}</th><th>{common.mean}</th><th>{common.latent}</th><th>{common.predictive}</th></tr></thead><tbody>{calculation.selected_rows.flatMap((row, index) => "response_predictions" in row ? row.response_predictions.map(prediction => { const response = study.objective.goal_type === "desirability" ? study.objective.responses.find(item => item.response_id === prediction.response_id) : null; return <tr key={`${row.row_id}:${prediction.response_id}`}><td>{index + 1}</td><th scope="row">{response?.name ?? prediction.response_id}{response?.unit ? ` (${response.unit})` : ""}</th><td>{exact(prediction.mean_raw)}</td><td>{exact(prediction.latent_standard_deviation_raw)}</td><td>{exact(prediction.predictive_standard_deviation_raw)}</td></tr>; }) : [])}</tbody></table></div>}
    {"auto_evidence" in calculation && calculation.auto_evidence && study.objective.goal_type === "desirability" && <BayesianAutoEvidence evidence={calculation.auto_evidence} responses={study.objective.responses} />}
    {trace.warnings.length > 0 && <details><summary>{text.warnings}</summary><ul>{trace.warnings.map((code, index) => <li key={`${index}:${code}`}>{augmentationWarningLabel(code, locale)} <code>{code}</code></li>)}</ul></details>}
  </>;
}
