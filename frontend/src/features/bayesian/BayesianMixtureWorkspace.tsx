import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Check, ChartScatter, Plus, RefreshCw, Save, X } from "lucide-react";
import * as api from "../../api/boMixture";
import { ApiRequestError } from "../../api/client";
import type { BayesianKernelKind } from "../../api/types/bayesian";
import type { BayesianStudyCloseRequest } from "../../api/types/bayesian";
import { useI18n } from "../../i18n/LocaleProvider";
import { mixtureMessages } from "../../i18n/boMixture";
import { parseDoeResponseNumber } from "../../doe/doeResponsePaste";
import { formatExactNumericValue as exact } from "../../statisticalNumberFormat";
import { augmentationFailureCode } from "./boAugmentationDraft";
import { createPlanningRequestFence, planningInteger } from "./boPlanningDraft";
import { bayesianRequestId } from "./bayesianRequestId";
import { currentMixtureModel, mixtureFit, mixtureSource, mixtureSourceKey, mixtureReviewDraftKey, parseMixturePoints, validMixtureModel, validMixturePage, validMixtureSelection, validMixtureStudy } from "./boMixtureDraft";
import { BayesianMixtureDiagnostics } from "./BayesianMixtureDiagnostics";
import { BayesianCurveSummary } from "./BayesianCurvePolicy";
import { BayesianMixtureProgress } from "./BayesianMixtureProgress";
import { BayesianDatasetSourceSummary } from "./BayesianDatasetSourceSummary";
import { validDatasetImportedInitialDesign } from "./boDatasetSource";
import { createMixtureReview, fetchMixtureReviewPage, restoreMixtureReview, runMixtureTask, validMixtureSelectionConfig } from "./boMixtureReview";

interface Props { study: api.MixtureStudy; disabled: boolean; onRefresh: () => void; onBusyChange: (value: boolean) => void; initialSelectionId?: string | null; onConfirmed?: (batchId: string) => void }
export function BayesianMixtureWorkspace(props: Props) {
  return <MixtureSourceWorkspace key={mixtureSourceKey(props.study)} {...props} />;
}
function MixtureSourceWorkspace({ study, disabled, onRefresh, onBusyChange, initialSelectionId, onConfirmed }: Props) {
  const { locale } = useI18n(), text = mixtureMessages(locale);
  const sourceKey = mixtureSourceKey(study), guard = useRef(createPlanningRequestFence()).current; guard.source(sourceKey);
  const running = useRef(false), retry = useRef<((current: () => boolean) => Promise<void>) | null>(null);
  const [busy, setBusy] = useState(false), [uncertain, setUncertain] = useState(false), [error, setError] = useState<string | null>(null);
  const [models, setModels] = useState<api.MixtureModel[]>([]), [model, setModel] = useState<api.MixtureModel | null>(null);
  const [kernel, setKernel] = useState<BayesianKernelKind>("matern_5_2"), [seconds, setSeconds] = useState("60"), [seed, setSeed] = useState("42");
  const [page, setPage] = useState<api.MixturePage | null>(null), [selected, setSelected] = useState<string[]>([]), [selection, setSelection] = useState<api.MixtureSelection | null>(null);
  const [count, setCount] = useState("32"), [batch, setBatch] = useState("1"), [budget, setBudget] = useState("200"), [distance, setDistance] = useState("0"), [manual, setManual] = useState(true), [paste, setPaste] = useState("");
  const [intent, setIntent] = useState(false), [replicateIntent, setReplicateIntent] = useState(false), [closeIntent, setCloseIntent] = useState(false);
  const [observations, setObservations] = useState<Record<string, string>>({});
  const [replicateTrial, setReplicateTrial] = useState(""), [replicateCount, setReplicateCount] = useState("1");
  const [restoreId, setRestoreId] = useState(initialSelectionId ?? "");
  const [abandonId, setAbandonId] = useState<string | null>(null);
  const [closeTarget, setCloseTarget] = useState<"completed" | "abandoned">("completed");
  const [reviewedDraftKey, setReviewedDraftKey] = useState<string | null>(null);
  const draftKey = mixtureReviewDraftKey({ seed, budget, distance, batch, manual, selected });
  const applyStoredReview = useCallback((restored: NonNullable<Awaited<ReturnType<typeof restoreMixtureReview>>>) => {
    const { draft } = restored;
    setModel(restored.model); setSelection(restored.selection); setPage(null);
    setSeed(draft.seed); setBudget(draft.budget); setDistance(draft.distance); setBatch(draft.batch);
    setManual(draft.manual); setSelected(draft.selected); setReviewedDraftKey(restored.draftKey); setIntent(false);
  }, []);
  function editSelectionInput(field: "seed" | "budget" | "distance" | "batch", value: string) {
    ({ seed: setSeed, budget: setBudget, distance: setDistance, batch: setBatch })[field](value);
    setSelection(null); setIntent(false); setReviewedDraftKey(null); setReplicateIntent(false);
  }
  useEffect(() => () => guard.invalidate(), [guard]);
  useEffect(() => { onBusyChange(busy); return () => onBusyChange(false); }, [busy, onBusyChange]);
  useEffect(() => {
    const token = guard.begin(); setBusy(true); running.current = true;
    void api.listMixtureModels(study.study_id).then(async result => {
      if (!guard.current(token)) return;
      if (!Array.isArray(result.items) || !result.items.every(item => validMixtureModel(item, study))) throw Error("bayesian_mixture_source_mismatch");
      setModels(result.items); setModel(result.items.find(item => currentMixtureModel(item, study)) ?? result.items[0] ?? null);
      if (initialSelectionId) {
        const restored = await restoreMixtureReview(study, initialSelectionId, () => guard.current(token));
        if (restored) applyStoredReview(restored);
      }
    }).catch(caught => { if (guard.current(token)) setError(augmentationFailureCode(caught)); })
      .finally(() => { if (guard.current(token)) { setBusy(false); running.current = false; } });
    return () => guard.invalidate();
  }, [applyStoredReview, guard, initialSelectionId, study]);
  async function run(task: (current: () => boolean) => Promise<void>, mutating = false) {
    if (running.current) return;
    running.current = true; setBusy(true); setError(null);
    if (mutating) retry.current = task;
    await runMixtureTask(guard, task, {
      success: () => { retry.current = null; setUncertain(false); },
      error: caught => { setError(augmentationFailureCode(caught)); setUncertain(mutating && !(caught instanceof ApiRequestError && caught.status >= 400 && caught.status < 500)); },
      settled: () => { running.current = false; setBusy(false); },
    });
  }
  const locked = busy || disabled || uncertain, active = study.status === "active";
  const current = model !== null && currentMixtureModel(model, study);
  const reviewCurrent = selection !== null && reviewedDraftKey === draftKey;
  const effectiveCoding = study.design_domain.mixture !== null && typeof study.design_domain.mixture === "object" && "effective_coding" in study.design_domain.mixture && typeof study.design_domain.mixture.effective_coding === "string" ? study.design_domain.mixture.effective_coding : "-";
  async function fit() {
    if (locked || !active || study.pending_trial_count > 0) return;
    const fit = mixtureFit(study, kernel, seconds, seed);
    if (!fit) { setError("bayesian_mixture_fit_input_invalid"); return; }
    const body = { ...mixtureSource(study), request_id: bayesianRequestId(), fit };
    await run(async current => {
      const value = await api.createMixtureModel(study.study_id, body);
      if (!current()) return;
      if (!validMixtureModel(value, study)) throw Error("bayesian_mixture_source_mismatch");
      setModel(value); setModels(current => [value, ...current.filter(item => item.model_id !== value.model_id)]); setPage(null); setSelected([]); setSelection(null);
    }, true);
  }
  async function candidates() {
    if (locked || !model || !current || !active) return;
    const amount = planningInteger(count, 1, 10000), random = planningInteger(seed, 0, 2147483647);
    const points = paste.trim() ? parseMixturePoints(paste, study) : null;
    if (amount === null || random === null || typeof points === "string") { setError(typeof points === "string" ? points : "bayesian_mixture_candidate_input_invalid"); return; }
    const captured = model;
    const body: api.MixtureCandidateRequest = { ...mixtureSource(study), schema_version: 4, request_id: bayesianRequestId(), candidate_set_id: bayesianRequestId(), name: "Mixture candidates", model_id: model.model_id, expected_model_sha256: model.snapshot_sha256, source: points ? { kind: "explicit_rows", points } : { kind: "seeded_uniform", seed: random, count: amount }, time_budget_ms: 60000, max_moment_evaluations: 65536 };
    await run(async current => { const value = await api.createMixtureCandidates(study.study_id, body); if (!current()) return; if (!validMixturePage(value, study, captured)) throw Error("bayesian_mixture_source_mismatch"); setPage(value); setSelected([]); setSelection(null); setIntent(false); }, true);
  }
  async function review() {
    if (locked || !model || !page || !page.source_is_current || !current || !active || study.pending_trial_count > 0) return;
    const size = manual ? selected.length : planningInteger(batch, 1, 8), total = planningInteger(budget, study.trial_count + (size ?? 1), 200), minimum = parseDoeResponseNumber(distance);
    if (!size || size > 8 || total === null || minimum === null || minimum < 0) { setError("bayesian_mixture_selection_invalid"); return; }
    const captured = model;
    const body: api.MixtureSelectionRequest = { ...mixtureSource(study), schema_version: 6, request_id: bayesianRequestId(), candidate_revision_id: page.revision.revision_id, expected_rows_sha256: page.revision.rows_sha256, model_id: model.model_id, expected_model_sha256: model.snapshot_sha256, policy: manual ? "manual_mixture_base_posterior_v1" : "greedy_mixture_maximin_v1", row_ids: manual ? [...selected] : [], batch_size: size, total_trial_budget: total, min_batch_distance: minimum, time_budget_ms: 60000, max_moment_evaluations: 65536 };
    await run(async current => { const value = await createMixtureReview(study, captured, body, current); if (!value) return; setSelection(value); setReviewedDraftKey(draftKey); setIntent(false); setRestoreId(value.selection_id); replaceSelection(value.selection_id); }, true);
  }
  async function confirm() {
    if (locked || !selection || !reviewCurrent || !model || !intent || !current || !active || study.pending_trial_count > 0 || !validMixtureSelectionConfig(selection.config) || !validMixtureSelection(selection, study, model)) return;
    const captured = selection, body = { expected_config_sha256: captured.config_sha256, expected_result_sha256: captured.result_sha256 };
    await run(async current => { const value = await api.confirmMixtureSelection(study.study_id, captured.selection_id, body); if (!current()) return; if (value.batch_id !== captured.selection_id || value.config_sha256 !== captured.config_sha256 || value.result_sha256 !== captured.result_sha256) throw Error("bayesian_mixture_source_mismatch"); onConfirmed?.(captured.selection_id); onRefresh(); }, true);
  }
  async function saveObservations() {
    if (locked || !active) return;
    const rows = [];
    for (const trial of study.trials.filter(row => row.state === "pending")) {
      const values: Record<string, number> = {};
      for (const response of study.objective.responses) { const value = parseDoeResponseNumber(observations[`${trial.trial_id}:${response.response_id}`] ?? ""); if (value === null) { setError("bayesian_observation_value_invalid"); return; } values[response.response_id] = value; }
      rows.push({ trial_id: trial.trial_id, response_values: values });
    }
    if (!rows.length) return;
    const body = { request_id: bayesianRequestId(), expected_study_version_id: study.study_version_id, expected_history_revision_id: study.observation_history.history_revision_id, expected_observation_history_sha256: study.observation_history.observation_history_sha256, observations: rows };
    await run(async current => { const value = await api.recordMixtureObservations(study.study_id, body); if (!current()) return; if (!validMixtureStudy(value.study, study.study_id) || value.request_id !== body.request_id) throw Error("bayesian_mixture_source_mismatch"); onRefresh(); }, true);
  }
  async function paginate(offset: number) {
    if (locked || !page || !model) return;
    const captured = model, revision = page.revision;
    await run(async current => { const value = await fetchMixtureReviewPage(study, captured, revision, offset, current); if (value) setPage(value); });
  }
  async function restoreSelection() {
    if (locked || !restoreId.trim()) return;
    await run(async current => { const restored = await restoreMixtureReview(study, restoreId.trim(), current); if (restored) applyStoredReview(restored); });
  }
  async function replicate() {
    const amount = planningInteger(replicateCount, 1, 8), total = planningInteger(budget, study.trial_count + (amount ?? 1), 200);
    if (locked || !active || !replicateIntent || study.pending_trial_count > 0 || !study.trials.some(t => t.trial_id === replicateTrial && t.state === "completed") || amount === null || total === null) return;
    const body = { request_id: bayesianRequestId(), expected_history_revision_id: study.observation_history.history_revision_id, expected_history_sha256: study.observation_history.observation_history_sha256, count: amount, total_trial_budget: total, confirm_replicate_intent: true as const };
    await run(async current => { const value = await api.replicateMixtureTrial(study.study_id, replicateTrial, body); if (!current()) return; if (value.study_id !== study.study_id || value.request_id !== body.request_id) throw Error("bayesian_mixture_source_mismatch"); onRefresh(); }, true);
  }
  async function close() {
    if (locked || !active || !closeIntent || study.pending_trial_count > 0) return;
    const body: BayesianStudyCloseRequest = { request_id: bayesianRequestId(), target_status: closeTarget, reason_code: closeTarget === "completed" ? "confirmation_complete" : "study_cancelled", note: null, expected_study_version_id: study.study_version_id, expected_history_revision_id: study.observation_history.history_revision_id, expected_observation_history_sha256: study.observation_history.observation_history_sha256 };
    await run(async current => { const value = await api.closeMixtureStudy(study.study_id, body); if (!current()) return; if (!validMixtureStudy(value.study, study.study_id) || value.study.status !== body.target_status) throw Error("bayesian_mixture_source_mismatch"); onRefresh(); }, true);
  }
  async function abandon() {
    if (locked || !active || !abandonId || !study.trials.some(trial => trial.trial_id === abandonId && trial.state === "pending")) return;
    const id = abandonId, body = { expected_history_revision_id: study.observation_history.history_revision_id, intent: "continue_study" as const };
    await run(async current => { const value = await api.abandonMixtureTrial(study.study_id, id, body); if (!current()) return; if (value.study_id !== study.study_id || value.trial.trial_id !== id || value.trial.state !== "abandoned") throw Error("bayesian_mixture_source_mismatch"); onRefresh(); }, true);
  }
  return <section className="bo-planning" aria-label={text.title}><h3>{study.name}</h3><p>{text.closure}</p><p>{text.unsupported}</p>
    <dl><dt>{text.total}</dt><dd>{exact(study.mixture.total)} {study.mixture.components[0]?.unit}</dd><dt>{text.coding}</dt><dd>{study.mixture.coding}</dd><dt>{locale === "ko" ? "Study 상태" : "Study status"}</dt><dd>{study.status}</dd><dt>{locale === "ko" ? "관측 이력" : "Observation history"}</dt><dd><code>{study.observation_history.observation_history_sha256}</code></dd></dl>
    <dl className="bo-planning-source"><dt>{locale === "ko" ? "적용 코딩" : "Effective coding"}</dt><dd>{effectiveCoding}</dd><dt>Study version</dt><dd>{study.study_version_id}</dd><dt>Definition SHA-256</dt><dd><code>{study.definition_sha256}</code></dd><dt>N completed / pending / total</dt><dd>{study.completed_trial_count} / {study.pending_trial_count} / {study.trial_count}</dd></dl>
    <div className="table-wrap"><table><thead><tr><th>{text.process}</th><th>{text.kind}</th><th>{locale === "ko" ? "선언 영역" : "Declared domain"}</th><th>{text.unit}</th></tr></thead><tbody>{study.process_factors.map(factor => <tr key={factor.factor_id}><th>{factor.name}</th><td>{factor.domain_kind}</td><td>{"levels" in factor ? `${factor.levels.join("; ")} (${factor.correlation_policy})` : `${exact(factor.low)} - ${exact(factor.high)}${factor.step ? `; step ${exact(factor.step)}` : ""}`}</td><td>{factor.unit ?? "-"}</td></tr>)}</tbody></table></div>
    {study.constraints.length > 0 && <ul>{study.constraints.map(constraint => <li key={constraint.constraint_id}>{constraint.name}: {constraint.terms.map(term => `${exact(term.coefficient)} * ${term.factor_id}`).join(" + ")} {constraint.relation} {exact(constraint.bound)}</li>)}</ul>}
    <div className="table-wrap"><table><thead><tr><th>{text.components}</th><th>{text.lower}</th><th>{text.upper}</th><th>{text.unit}</th></tr></thead><tbody>{study.mixture.components.map(c => <tr key={c.factor_id}><th>{c.name}</th><td>{exact(c.low)}</td><td>{exact(c.high)}</td><td>{c.unit}</td></tr>)}</tbody></table></div>
    <BayesianCurveSummary responses={study.objective.responses} />
    {validDatasetImportedInitialDesign(study.initial_design, undefined, undefined, 2) && <BayesianDatasetSourceSummary receipt={study.initial_design} expectedVersion={2} />}
    <BayesianMixtureProgress study={study} />
    <h4>{text.observations}</h4><div className="table-wrap"><table><thead><tr><th>ID</th><th>{locale === "ko" ? "상태" : "State"}</th>{study.factors.map(f => <th key={f.factor_id}>{f.name} {f.unit}</th>)}{study.objective.responses.map(r => <th key={r.response_id}>{r.name} {r.unit}</th>)}</tr></thead><tbody>{study.trials.map(trial => <tr key={trial.trial_id}><th>{trial.trial_number}</th><td>{trial.state}</td>{study.factors.map(f => <td key={f.factor_id}>{typeof trial.actual_coordinates[f.factor_id] === "number" ? exact(trial.actual_coordinates[f.factor_id] as number) : trial.actual_coordinates[f.factor_id]}</td>)}{study.objective.responses.map(r => <td key={r.response_id}>{trial.state === "pending" ? <input aria-label={`${trial.trial_number}: ${r.name}`} inputMode="decimal" disabled={locked || !active} value={observations[`${trial.trial_id}:${r.response_id}`] ?? ""} onChange={e => { const value = e.currentTarget.value; setObservations(current => ({ ...current, [`${trial.trial_id}:${r.response_id}`]: value })); }} /> : trial.response_values?.[r.response_id] === undefined ? "-" : exact(trial.response_values[r.response_id])}</td>)}</tr>)}</tbody></table></div>
    <button type="button" className="secondary-button" disabled={locked || !active || study.pending_trial_count === 0} onClick={() => void saveObservations()}><Save size={16} aria-hidden="true" />{text.save}</button>
    {active && study.pending_trial_count > 0 && <div className="bo-planning-fields"><label>{locale === "ko" ? "중단할 미완료 실험" : "Pending trial to abandon"}<select aria-label={locale === "ko" ? "중단할 미완료 실험" : "Pending trial to abandon"} value={abandonId ?? ""} disabled={locked} onChange={e => setAbandonId(e.currentTarget.value || null)}><option value="">{text.none}</option>{study.trials.filter(t => t.state === "pending").map(t => <option key={t.trial_id} value={t.trial_id}>{t.trial_number}</option>)}</select></label>{abandonId && <button type="button" className="secondary-button" disabled={locked} onClick={() => void abandon()}><X size={16} aria-hidden="true" />{locale === "ko" ? "선택한 실험 중단 확정" : "Confirm abandoning selected trial"}</button>}</div>}
    <h4>{locale === "ko" ? "저장 모형 및 새 적합 설정" : "Saved models and new fit settings"}</h4><fieldset disabled={locked}><div className="bo-planning-fields"><label>{text.models}<select aria-label={text.models} value={model?.model_id ?? ""} onChange={e => { setModel(models.find(item => item.model_id === e.currentTarget.value) ?? null); setPage(null); setSelection(null); setSelected([]); }}><option value="">{text.none}</option>{models.map(item => <option key={item.model_id} value={item.model_id}>{item.created_at} {item.snapshot_sha256.slice(0, 12)}{currentMixtureModel(item, study) ? "" : ` (${text.stale})`}</option>)}</select></label>
      <label>{locale === "ko" ? "커널" : "Kernel"}<select aria-label="Kernel" value={kernel} onChange={e => setKernel(e.currentTarget.value as BayesianKernelKind)}>{["matern_5_2", "matern_3_2", "gaussian", "exponential"].map(value => <option key={value} value={value}>{value}</option>)}</select></label>
      <label>{text.seed}<input inputMode="numeric" value={seed} onChange={e => editSelectionInput("seed", e.currentTarget.value)} /></label><label>{locale === "ko" ? "적합 시간 예산 (초)" : "Fit time budget (seconds)"}<input inputMode="numeric" value={seconds} onChange={e => setSeconds(e.currentTarget.value)} /></label></div>
      <dl className="bo-planning-source"><dt>{locale === "ko" ? "관측 정책" : "Observation policy"}</dt><dd>retain_raw</dd><dt>{locale === "ko" ? "노이즈 정책" : "Noise policy"}</dt><dd>estimate</dd><dt>{locale === "ko" ? "적합 평가 예산 / 시작점" : "Fit evaluation budget / starts"}</dt><dd>1000 / 3</dd><dt>{locale === "ko" ? "모멘트 평가 예산" : "Moment evaluation budget"}</dt><dd>8192</dd></dl>
      <button type="button" className="secondary-button" disabled={!active || study.pending_trial_count > 0 || !study.surrogate_available} onClick={() => void fit()}><ChartScatter size={16} aria-hidden="true" />{text.fit}</button>
    </fieldset>
    {model && <><p><code>{model.snapshot_sha256}</code> {!current && text.stale}</p><div className="table-wrap"><table><caption>{locale === "ko" ? "저장 모형의 적용 설정" : "Applied settings of saved model"}</caption><thead><tr><th>{locale === "ko" ? "반응" : "Response"}</th><th>{locale === "ko" ? "커널" : "Kernel"}</th><th>{locale === "ko" ? "노이즈" : "Noise"}</th></tr></thead><tbody>{model.fit.response_models.map(response => <tr key={response.response_id}><th>{study.objective.responses.find(row => row.response_id === response.response_id)?.name ?? response.response_id}</th><td>{response.kernel.kind}</td><td>{response.surrogate.noise_mode}</td></tr>)}</tbody></table></div><p>{model.fit.observation_policy.mode}; seed={model.fit.search.random_seed}; evaluations={model.fit.search.model_max_evaluations}; time_budget_ms={model.fit.search.time_budget_ms}</p>{model.warnings.map(code => <p key={code} className="notice-box notice-warning"><code>{code}</code></p>)}
      <fieldset disabled={locked || !current || !active}><legend>{text.candidates}</legend><div className="bo-planning-fields"><label>{text.candidateCount}<input inputMode="numeric" value={count} onChange={e => setCount(e.currentTarget.value)} /></label><label>{locale === "ko" ? "후보 붙여넣기 (ID 머리글)" : "Paste candidate rows (ID headers)"}<textarea value={paste} onChange={e => setPaste(e.currentTarget.value)} placeholder={study.factors.map(f => f.factor_id).join("\t")} /></label></div><button type="button" className="secondary-button" onClick={() => void candidates()}><Plus size={16} aria-hidden="true" />{text.generate}</button></fieldset>
      {page && <><CandidateTable rows={page.items} study={study} selected={selected} disabled={locked || !current || !active} onSelect={id => { setSelected(current => current.includes(id) ? current.filter(value => value !== id) : current.length < 8 ? [...current, id] : current); setSelection(null); setIntent(false); }} />
        <div className="bo-planning-actions"><button type="button" className="secondary-button bo-planning-icon" title={text.previous} aria-label={text.previous} disabled={locked || page.offset === 0} onClick={() => void paginate(Math.max(0, page.offset - 50))}><ArrowLeft size={16} /></button><span>{page.offset + 1}-{page.offset + page.items.length} / {page.revision.row_count}</span><button type="button" className="secondary-button bo-planning-icon" title={text.next} aria-label={text.next} disabled={locked || page.offset + page.items.length >= page.revision.row_count} onClick={() => void paginate(page.offset + 50)}><ArrowRight size={16} /></button></div>
        <fieldset disabled={locked || !current || !active || !page.source_is_current || study.pending_trial_count > 0}><div className="bo-planning-fields"><label>{text.policy}<select aria-label={text.policy} value={manual ? "manual" : "maximin"} onChange={e => { setManual(e.currentTarget.value === "manual"); setSelection(null); setIntent(false); setReviewedDraftKey(null); }}><option value="manual">{text.manual}</option><option value="maximin">{text.maximin}</option></select></label><label>{text.batch}<input inputMode="numeric" value={manual ? String(selected.length) : batch} disabled={manual} onChange={e => editSelectionInput("batch", e.currentTarget.value)} /></label><label>{text.budget}<input inputMode="numeric" value={budget} onChange={e => editSelectionInput("budget", e.currentTarget.value)} /></label><label>{locale === "ko" ? "최소 배치 거리 (설계 정규화 단위)" : "Minimum batch distance (design-normalized units)"}<input inputMode="decimal" value={distance} onChange={e => editSelectionInput("distance", e.currentTarget.value)} /></label></div><button type="button" className="secondary-button" onClick={() => void review()}><Check size={16} aria-hidden="true" />{text.review}</button></fieldset>
      </>}
      <BayesianMixtureDiagnostics key={`${model.model_id}:${model.snapshot_sha256}`} study={study} model={model} disabled={locked} />
    </>}
    <div className="bo-planning-fields"><label>{locale === "ko" ? "저장 선택 ID" : "Saved selection ID"}<input value={restoreId} disabled={locked} onChange={e => setRestoreId(e.currentTarget.value)} /></label><button type="button" className="secondary-button" disabled={locked || !restoreId.trim()} onClick={() => void restoreSelection()}><RefreshCw size={16} aria-hidden="true" />{text.review}</button></div>
    {selection && <section><h4>{text.review}</h4><p>{locale === "ko" ? "저장된 검토 조건만 확정합니다. 선택 입력 변경 시 다시 검토해야 합니다." : "Confirmation uses this stored review only. Changing selection inputs requires a new review."}</p><MixtureAppliedSelectionSettings config={selection.config} /><code>{selection.config_sha256}</code><br /><code>{selection.result_sha256}</code><CandidateTable rows={selection.result.items} study={study} selected={[]} disabled onSelect={() => undefined} /><label><input type="checkbox" checked={intent} disabled={locked || !reviewCurrent || !current || !active} onChange={e => setIntent(e.currentTarget.checked)} />{text.confirmIntent}</label><button type="button" className="primary-button" disabled={locked || !intent || !reviewCurrent || !current || !active || study.pending_trial_count > 0} onClick={() => void confirm()}><Check size={16} aria-hidden="true" />{text.confirm}</button></section>}
    <label>{locale === "ko" ? "종료 상태 및 사유" : "Closing status and reason"}<select aria-label={locale === "ko" ? "종료 상태 및 사유" : "Closing status and reason"} value={closeTarget} disabled={locked || !active || study.pending_trial_count > 0} onChange={e => { setCloseTarget(e.currentTarget.value as typeof closeTarget); setCloseIntent(false); }}><option value="completed">completed: confirmation_complete</option><option value="abandoned">abandoned: study_cancelled</option></select></label>
    <fieldset disabled={locked || !active || study.pending_trial_count > 0}>
      <details><summary>{text.replicate}</summary><div className="bo-planning-fields"><label>{text.replicate}<select aria-label={text.replicate} value={replicateTrial} onChange={e => { setReplicateTrial(e.currentTarget.value); setReplicateIntent(false); }}><option value="">{text.none}</option>{study.trials.filter(t => t.state === "completed").map(t => <option key={t.trial_id} value={t.trial_id}>{t.trial_number}</option>)}</select></label><label>{locale === "ko" ? "반복 수" : "Replicate count"}<input inputMode="numeric" value={replicateCount} onChange={e => { setReplicateCount(e.currentTarget.value); setReplicateIntent(false); }} /></label><label>{text.budget}<input inputMode="numeric" value={budget} onChange={e => editSelectionInput("budget", e.currentTarget.value)} /></label></div><label><input type="checkbox" checked={replicateIntent} onChange={e => setReplicateIntent(e.currentTarget.checked)} />{text.confirmIntent}</label><button type="button" className="secondary-button" disabled={!replicateIntent || !replicateTrial} onClick={() => void replicate()}><Plus size={16} />{text.replicate}</button></details>
      <label><input type="checkbox" checked={closeIntent} onChange={e => setCloseIntent(e.currentTarget.checked)} />{text.close}</label><button type="button" className="secondary-button" disabled={!closeIntent} onClick={() => void close()}><Check size={16} />{text.close}</button>
    </fieldset>
    {busy && <p role="status">{text.working}</p>}{error && <div role="alert" className="notice-box notice-warning"><p>{uncertain ? text.uncertain : text.invalid}</p><code>{error}</code>{uncertain && retry.current && <button type="button" className="secondary-button" disabled={busy} onClick={() => void run(retry.current!, true)}><RefreshCw size={16} />{text.retry}</button>}</div>}
    <button type="button" className="secondary-button" disabled={busy} onClick={onRefresh}><RefreshCw size={16} />{text.refresh}</button>
  </section>;
}

export function MixtureAppliedSelectionSettings({ config }: { config: api.MixtureSelectionRequest }) {
  const { locale } = useI18n(), text = mixtureMessages(locale);
  return <div className="table-wrap"><table><caption>{locale === "ko" ? "저장된 선택의 적용 설정" : "Applied settings of stored selection"}</caption><tbody>{[
    [text.policy, config.policy], [text.batch, config.batch_size], [text.budget, config.total_trial_budget],
    [locale === "ko" ? "최소 배치 거리 (설계 정규화 단위)" : "Minimum batch distance (design-normalized units)", config.min_batch_distance],
    [locale === "ko" ? "시간 예산 (ms)" : "Time budget (ms)", config.time_budget_ms],
    [locale === "ko" ? "모멘트 평가 예산" : "Moment evaluation budget", config.max_moment_evaluations],
    ["Request ID", config.request_id], ["Candidate revision", config.candidate_revision_id], ["Candidate SHA-256", config.expected_rows_sha256],
  ].map(([label, value]) => <tr key={String(label)}><th>{label}</th><td>{typeof value === "number" ? exact(value) : value}</td></tr>)}</tbody></table></div>;
}
function CandidateTable({ rows, study, selected, disabled, onSelect }: { rows: api.MixtureRow[]; study: api.MixtureStudy; selected: string[]; disabled: boolean; onSelect: (id: string) => void }) {
  const { locale } = useI18n(), text = mixtureMessages(locale);
  return <div className="table-wrap"><table><thead><tr><th>{text.selected}</th>{study.factors.map(f => <th key={f.factor_id}>{f.name} {f.unit}</th>)}<th>{text.eligible}</th>{study.objective.responses.map(r => <th key={r.response_id}>{r.name} {r.unit}: Mean / Latent SD / Predictive SD</th>)}<th>{locale === "ko" ? "종합 만족도" : "Composite desirability"}</th></tr></thead><tbody>{rows.map(row => <tr key={row.row_id}><td><input type="checkbox" aria-label={`${text.selected} ${row.row_id}`} checked={selected.includes(row.row_id)} disabled={disabled || !row.eligible} onChange={() => onSelect(row.row_id)} />{selected.includes(row.row_id) && selected.indexOf(row.row_id) + 1}</td>{study.factors.map(f => <td key={f.factor_id}>{typeof row.actual_coordinates[f.factor_id] === "number" ? exact(row.actual_coordinates[f.factor_id] as number) : row.actual_coordinates[f.factor_id]}</td>)}<td>{row.eligible ? text.eligible : text.excluded}{!row.constraints_satisfied && " (constraint)"}{!row.novel && " (existing)"}</td>{row.response_predictions.map(r => <td key={r.response_id}>{exact(r.mean_raw)} / {exact(r.latent_standard_deviation_raw)} / {exact(r.predictive_standard_deviation_raw)}</td>)}<td>{exact(row.desirability_moments.mean)}</td></tr>)}</tbody></table></div>;
}
function replaceSelection(id: string) {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  for (const key of ["batch_id", "recommendation_id", "planning_batch_id", "augmentation_batch_id", "mixed_planning_batch_id"]) url.searchParams.delete(key);
  url.searchParams.set("mixture_selection_id", id); window.history.replaceState({}, "", url);
}
