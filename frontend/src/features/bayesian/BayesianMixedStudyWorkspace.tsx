import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Check, RefreshCw, Save, X } from "lucide-react";
import type { BayesianStudyCloseRequest } from "../../api/types/bayesian";
import type { MixedStudyResponse } from "../../api/types/boMixed";
import { useI18n } from "../../i18n/LocaleProvider";
import { mixedCorrelationLabel, mixedMessages } from "../../i18n/boMixed";
import { formatExactNumericValue as exact } from "../../statisticalNumberFormat";
import { isMixedCategory, mixedStudyKey } from "./boMixedDraft";
import { planningInteger } from "./boPlanningDraft";
import { vectorDraftCell } from "./bayesianVectorDraft";
import { BayesianCurveSummary } from "./BayesianCurvePolicy";
import { useMixedStudyActions } from "./hooks/useMixedStudyActions";
import "./boPlanning.css";

interface Props { study: MixedStudyResponse; disabled: boolean; onCommitted: (study: MixedStudyResponse, expectedHistory: string) => void; onRefresh: () => void; onBusyChange: (value: boolean) => void }
export function BayesianMixedStudyWorkspace({ study, disabled, onCommitted, onRefresh, onBusyChange }: Props) {
  const { locale } = useI18n(), text = mixedMessages(locale);
  const state = useMixedStudyActions({ study, disabled, onCommitted, onRefresh });
  const [offset, setOffset] = useState(0), [replicateTrial, setReplicateTrial] = useState(""), [count, setCount] = useState("1"), [budget, setBudget] = useState("200"), [intent, setIntent] = useState(false);
  const [closingIntent, setClosingIntent] = useState(false), [closeTarget, setCloseTarget] = useState<"completed" | "abandoned">("completed");
  const [reason, setReason] = useState<BayesianStudyCloseRequest["reason_code"]>("confirmation_complete"), [note, setNote] = useState("");
  const sourceKey = mixedStudyKey(study);
  useEffect(() => { setOffset(0); setReplicateTrial(""); setIntent(false); setClosingIntent(false); setNote(""); }, [sourceKey]);
  useEffect(() => { onBusyChange(state.busy); return () => onBusyChange(false); }, [state.busy, onBusyChange]);
  const locked = disabled || state.busy, readOnly = locked || study.status !== "active";
  const states = { pending: text.pending, completed: text.completed, abandoned: text.abandoned }, rows = study.trials.slice(offset, offset + 25);
  const counts = { count: planningInteger(count, 1, 8), budget: planningInteger(budget, 2, 200) };
  const reasons = { objective_satisfied: text.objectiveSatisfied, budget_reached: text.budgetReached, confirmation_complete: text.confirmationComplete,
    unsafe_or_infeasible: text.unsafe, resources_unavailable: text.resources, study_cancelled: text.cancelled };
  const closeReasons: BayesianStudyCloseRequest["reason_code"][] = closeTarget === "completed" ? ["objective_satisfied", "budget_reached", "confirmation_complete"] : ["unsafe_or_infeasible", "resources_unavailable", "study_cancelled"];
  const previewTrialId = state.preview && "trialId" in state.preview ? state.preview.trialId : null;
  const previewTrialNumber = previewTrialId === null ? null : study.trials.find(row => row.trial_id === previewTrialId)?.trial_number;
  function edit(action: () => void) { if (state.cancel()) action(); }
  return <section className="bo-planning" aria-label={text.title}><h3>{study.name}</h3><p>{text.categoryMeaning}</p>
    <button type="button" className="secondary-button" disabled={locked} onClick={onRefresh}><RefreshCw size={16} aria-hidden="true" />{text.refresh}</button>
    <details><summary>{text.source}</summary><dl className="bo-planning-source"><div><dt>{text.definition}</dt><dd>{study.definition_sha256}</dd></div><div><dt>{text.history}</dt><dd>{study.observation_history.observation_history_sha256}</dd></div><div><dt>{text.coordinate}</dt><dd>numeric_normalized_category_index_v1</dd></div></dl></details>
    <div className="table-wrap"><table className="result-table"><caption className="bo-planning-caption">{text.factors}</caption><thead><tr><th>{text.factorName}</th><th>{text.kind}</th><th>{text.levels}</th><th>{text.correlation}</th></tr></thead><tbody>{study.factors.map(factor => <tr key={factor.factor_id}><th scope="row">{factor.name}{factor.unit ? ` (${factor.unit})` : ""}</th><td>{factor.domain_kind === "nominal" ? text.nominal : factor.domain_kind === "ordinal" ? text.ordinal : factor.domain_kind === "discrete_numeric" ? text.discrete : text.continuous}</td>
      <td>{isMixedCategory(factor) ? <ol>{factor.levels.map((level, index) => <li key={index}>{level}</li>)}</ol> : `${exact(factor.low)} – ${exact(factor.high)}${factor.step == null ? "" : ` / ${text.step}: ${exact(factor.step)}`}`}</td>
      <td>{isMixedCategory(factor) ? mixedCorrelationLabel(factor.correlation_policy, locale) : "-"}</td></tr>)}</tbody></table></div>
    <details><summary>{text.initial}</summary><p>{text.initialPolicy}</p><p>{text.size}: {study.initial_design.generated_size} · {text.seed}: {study.initial_design.seed}</p>
      {study.factors.filter(isMixedCategory).map(factor => <div key={factor.factor_id}><strong>{factor.name}</strong><ul>{factor.levels.map((level, index) => <li key={index}>{level}: {study.initial_design.category_level_counts[factor.factor_id]?.[index] ?? "-"}</li>)}</ul>
        {(study.initial_design.unobserved_level_indices[factor.factor_id]?.length ?? 0) > 0 && <p>{text.uncovered}: {study.initial_design.unobserved_level_indices[factor.factor_id].map(index => factor.levels[index]).join("; ")}</p>}</div>)}<p>{text.prior}</p></details>
    <BayesianCurveSummary responses={study.objective.responses} />
    <h4>{text.observations}</h4><p>{text.partial}</p>
    <fieldset className="bo-planning-confirm-lock" disabled={readOnly}><div className="table-wrap"><table className="result-table"><caption className="bo-planning-caption">{text.observations}</caption><thead><tr><th>{text.trial}</th>{study.factors.map(factor => <th key={factor.factor_id}>{factor.name}</th>)}<th>{text.state}</th>{study.objective.responses.map(response => <th key={response.response_id}>{response.name}{response.unit ? ` (${response.unit})` : ""}</th>)}<th>{text.abandon}</th></tr></thead>
      <tbody>{rows.map(row => <tr key={row.trial_id}><th scope="row">{row.trial_number}</th>{study.factors.map(factor => <td key={factor.factor_id}>{typeof row.actual_coordinates[factor.factor_id] === "string" ? row.actual_coordinates[factor.factor_id] : exact(row.actual_coordinates[factor.factor_id] as number)}</td>)}<td>{states[row.state]}</td>
        {study.objective.responses.map(response => <td key={response.response_id}>{row.state === "pending" ? <input inputMode="decimal" aria-label={`${text.trial} ${row.trial_number}: ${response.name}`} value={vectorDraftCell(state.draft, row.trial_id, response.response_id)} onChange={event => state.update(row.trial_id, response.response_id, event.currentTarget.value)} /> : row.response_values === null ? "-" : exact(row.response_values[response.response_id])}</td>)}
        <td>{row.state === "pending" && <button type="button" className="secondary-button" onClick={() => state.requestAbandon(row.trial_id, closingIntent)}><X size={16} aria-hidden="true" />{text.abandon}</button>}</td></tr>)}</tbody></table></div>
      <label className="checkbox-label"><input type="checkbox" checked={closingIntent} onChange={event => { const value = event.currentTarget.checked; edit(() => setClosingIntent(value)); }} />{text.closingIntent}</label>
      <button type="button" className="secondary-button" disabled={study.pending_trial_count === 0} onClick={state.reviewObservations}><Check size={16} aria-hidden="true" />{text.review}</button>
    </fieldset>
    <div className="bo-planning-actions"><button type="button" className="secondary-button" disabled={locked || offset === 0} onClick={() => setOffset(Math.max(0, offset - 25))}><ArrowLeft size={16} aria-hidden="true" />{text.previous}</button><span>{offset + 1}–{Math.min(offset + 25, study.trial_count)} / {study.trial_count}</span><button type="button" className="secondary-button" disabled={locked || offset + 25 >= study.trial_count} onClick={() => setOffset(offset + 25)}>{text.next}<ArrowRight size={16} aria-hidden="true" /></button></div>
    <details><summary>{text.replicate}</summary><p>{text.replicateMeaning}</p><fieldset className="bo-planning-confirm-lock" disabled={readOnly || study.pending_trial_count > 0}>
      <div className="bo-planning-fields"><label>{text.trial}<select value={replicateTrial} onChange={event => { const value = event.currentTarget.value; edit(() => setReplicateTrial(value)); }}><option value="">-</option>{study.trials.filter(row => row.state === "completed").map(row => <option key={row.trial_id} value={row.trial_id}>{row.trial_number}</option>)}</select></label>
        <label>{text.replicateCount}<input inputMode="numeric" value={count} onChange={event => { const value = event.currentTarget.value; edit(() => setCount(value)); }} /></label><label>{text.totalBudget}<input inputMode="numeric" value={budget} onChange={event => { const value = event.currentTarget.value; edit(() => setBudget(value)); }} /></label></div>
      <label className="checkbox-label"><input type="checkbox" checked={intent} onChange={event => { const value = event.currentTarget.checked; edit(() => setIntent(value)); }} />{text.replicateIntent}</label>
      <button type="button" className="secondary-button" disabled={!intent || !replicateTrial || counts.count === null || counts.budget === null || counts.budget < study.trial_count + counts.count} onClick={() => { if (counts.count !== null && counts.budget !== null) state.requestReplicates(replicateTrial, counts.count, counts.budget, intent); }}><Save size={16} aria-hidden="true" />{text.replicate}</button>
    </fieldset></details>
    <details><summary>{text.close}</summary><p>{text.closePending}</p><fieldset className="bo-planning-confirm-lock" disabled={readOnly || study.pending_trial_count > 0}><div className="bo-planning-fields">
      <label>{text.closeTarget}<select value={closeTarget} onChange={event => { const value = event.currentTarget.value as typeof closeTarget; edit(() => { setCloseTarget(value); setReason(value === "completed" ? "confirmation_complete" : "study_cancelled"); }); }}><option value="completed">{text.completed}</option><option value="abandoned">{text.abandoned}</option></select></label>
      <label>{text.closeReason}<select value={reason} onChange={event => { const value = event.currentTarget.value as typeof reason; edit(() => setReason(value)); }}>{closeReasons.map(code => <option key={code} value={code}>{reasons[code]}</option>)}</select></label>
      <label>{text.note}<input value={note} maxLength={2000} onChange={event => { const value = event.currentTarget.value; edit(() => setNote(value)); }} /></label></div><button type="button" className="secondary-button" onClick={() => state.requestClose(closeTarget, reason, note)}>{text.close}</button></fieldset></details>
    {state.preview && <section className="notice-box" aria-label={text.reviewed}><h4>{text.reviewed}</h4>
      {state.preview.kind === "observations" ? <div className="table-wrap"><table className="result-table"><thead><tr><th>{text.trial}</th>{study.objective.responses.map(response => <th key={response.response_id}>{response.name}</th>)}</tr></thead><tbody>{state.preview.request.observations.map(row => <tr key={row.trial_id}><th scope="row">{study.trials.find(trial => trial.trial_id === row.trial_id)?.trial_number}</th>{study.objective.responses.map(response => <td key={response.response_id}>{exact(row.response_values[response.response_id])}</td>)}</tr>)}</tbody></table></div> :
        state.preview.kind === "replicates" ? <p>{text.replicate}: {state.preview.request.count} · {text.trial}: {previewTrialNumber}</p> :
        state.preview.kind === "abandon" ? <p>{text.confirmAbandon}: {previewTrialNumber}</p> : <p>{text.confirmClose}: {state.preview.request.target_status === "completed" ? text.completed : text.abandoned}</p>}
      <div className="bo-planning-actions"><button type="button" className="primary-button" disabled={locked} onClick={state.confirm}><Save size={16} aria-hidden="true" />{state.preview.kind === "observations" ? text.confirmObservations : text.confirm}</button><button type="button" className="secondary-button" disabled={locked} onClick={state.cancel}>{text.cancel}</button></div>
    </section>}
    {state.error && <div role="alert" className="notice-box notice-warning"><p>{text.error}</p><code>{state.error}</code>{state.canRetry && <><p>{text.uncertain}</p><button type="button" className="secondary-button" disabled={locked} onClick={state.retry}><RefreshCw size={16} aria-hidden="true" />{text.retry}</button></>}</div>}
    {state.busy && <p role="status">{text.working}</p>}
  </section>;
}
