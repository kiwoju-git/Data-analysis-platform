import { useEffect, useState } from "react";
import { BayesianLooPanel } from "./BayesianLooPanel";
import { BayesianProfileGrid, BayesianProfileLevelMap } from "./BayesianProfileGrid";
import { categoryDisplayTicks } from "./bayesianProgress";
import { BayesianAutoStrategyPanel } from "./BayesianAutoStrategyPanel";
import { ArrowDown, ArrowUp, Check, Redo2, RefreshCw, Undo2 } from "lucide-react";
import type { AugmentationPolicy } from "../../api/types/boAugmentation";
import type { EvaluatedMixedCandidateRow, MixedActualPoint, MixedCandidateRow, MixedModelDetail, MixedSelectionResponse, MixedStudyResponse } from "../../api/types/boMixed";
import { InteractiveScatterChart } from "../../charts/InteractiveScatterChart";
import { paddedNumericRange } from "../../charts/chartScale";
import { useI18n } from "../../i18n/LocaleProvider";
import { augmentationMessages, augmentationPolicyLabel } from "../../i18n/boAugmentation";
import { autoEvidenceMessages } from "../../i18n/boAutoEvidence";
import { mixedMessages } from "../../i18n/boMixed";
import { planningMessages } from "../../i18n/boPlanning";
import { formatExactNumericValue as exact } from "../../statisticalNumberFormat";
import { AugmentationTraceTable } from "./BayesianAugmentationPanel";
import { isMixedCategory, mixedStudyKey, parseMixedCandidatePaste, parseMixedPoint } from "./boMixedDraft";
import { mixedDefaultPoint, mixedProfilePoints, type MixedFitDraft } from "./boMixedPlanningDraft";
import { planningInteger } from "./boPlanningDraft";
import { strictBoNumber } from "./boNoisePolicy";
import { useMixedPlanning, type MixedProfile } from "./hooks/useMixedPlanning";
import "./boPlanning.css";

interface Props { study: MixedStudyResponse; disabled: boolean; onConfirmed: (id: string) => void; onConfirmingChange: (busy: boolean) => void }
const policies: AugmentationPolicy[] = ["greedy_mixed_maximin_v1", "refine_ei_alternating_desirability_response_sd_v2", "confirm_mean_then_competitive_sd_v1"];
export function BayesianMixedPlanningPanel(props: Props) {
  const state = useMixedPlanning(props), { study, onConfirmingChange } = props, { locale } = useI18n(), text = mixedMessages(locale), common = planningMessages(locale), auto = augmentationMessages(locale);
  const key = mixedStudyKey(study), locked = props.disabled || state.busy !== null || state.isConfirming;
  const [candidateDraft, setCandidateDraft] = useState({ key, name: "", count: "60", seed: "42", tolerance: ".000001", ordinal: false, content: "", header: true });
  const [preview, setPreview] = useState<{ source: string; content: string; header: boolean; points: MixedActualPoint[] } | null>(null), [inputError, setInputError] = useState(false);
  const candidate = candidateDraft.key === key ? candidateDraft : { key, name: "", count: "60", seed: "42", tolerance: ".000001", ordinal: false, content: "", header: true };
  const [profileDraft, setProfileDraft] = useState({ key, holds: mixedDefaultPoint(study), axis: study.factors[0].factor_id });
  const profileInput = profileDraft.key === key ? profileDraft : { key, holds: mixedDefaultPoint(study), axis: study.factors[0].factor_id };
  const point = parseMixedPoint(profileInput.holds, study.factors), profilePoints = point ? mixedProfilePoints(study, point, profileInput.axis) : null;
  const tolerance = strictBoNumber(candidate.tolerance), count = planningInteger(candidate.count, 1, 10000), seed = planningInteger(candidate.seed, 0, 2147483647);
  const validCandidates = count !== null && seed !== null && tolerance !== null && tolerance >= 1e-12 && tolerance <= .1 && candidate.name.trim().length > 0 && candidate.name.trim().length <= 120;
  useEffect(() => { onConfirmingChange(state.isConfirming); return () => onConfirmingChange(false); }, [onConfirmingChange, state.isConfirming]);
  function editCandidate<K extends keyof typeof candidate>(field: K, value: typeof candidate[K]) {
    if (!state.invalidate()) return; setCandidateDraft({ ...candidate, [field]: value }); setPreview(null); setInputError(false);
  }
  function editHold(id: string, value: string) { if (state.invalidate(false)) setProfileDraft({ ...profileInput, holds: { ...profileInput.holds, [id]: value } }); }
  function importPreview() {
    const points = parseMixedCandidatePaste(candidate.content, study.factors, candidate.header);
    setInputError(points === null); setPreview(points === null ? null : { source: key, content: candidate.content, header: candidate.header, points });
  }
  function applyImport() {
    if (preview?.source !== key || preview.content !== candidate.content || preview.header !== candidate.header || tolerance === null || tolerance < 1e-12 || tolerance > .1 || !candidate.name.trim()) { setInputError(true); return; }
    state.createCandidates(candidate.name, { kind: "explicit_rows", points: preview.points }, tolerance, candidate.ordinal);
  }
  const selectedModel = state.model;
  return <section className="bo-planning" aria-label={text.planning}>
    <h3>{text.planning}</h3><p>{common.meaning}</p>
    <button type="button" className="secondary-button" disabled={locked || state.loading} onClick={() => void state.refresh()}><RefreshCw size={16} aria-hidden="true" />{common.refresh}</button>
    {state.isConfirming && <p role="status">{common.confirmLock}</p>}
    {state.error && <div className="notice-box notice-warning" role="alert"><p>{common.error}</p><code>{state.error}</code>{state.canRetry && <><p>{common.uncertain}</p><button type="button" disabled={locked} onClick={state.retry}>{common.retry}</button></>}</div>}
    {state.busy && <p role="status">{common.busy}</p>}
    <fieldset className="bo-planning-fieldset" disabled={locked}>
      <legend>{text.fitSettings}</legend>
      <MixedFitSettings draft={state.fitDraft} onChange={state.updateFit} study={study} />
      <button type="button" className="primary-button" disabled={!state.canFit} onClick={state.fit}>{text.fit}</button>
      <label>{common.models}<select aria-label={common.models} value={selectedModel?.model_id ?? ""} onChange={event => state.openModel(event.currentTarget.value)}><option value="">{common.choose}</option>{state.models.map(model => <option key={model.model_id} value={model.model_id}>{model.created_at} · {model.source_is_current ? common.current : common.historical}</option>)}</select></label>
    </fieldset>
    {selectedModel && <MixedFitReceipt model={selectedModel} study={study} />}
    {selectedModel && <BayesianLooPanel studyId={study.study_id} model={selectedModel} contextKey={key} mixed disabled={locked || state.busy !== null} />}
    <fieldset className="bo-planning-fieldset" disabled={locked || study.status !== "active"}>
      <legend>{common.candidates}</legend>
      <div className="bo-planning-controls">
        <DraftInput label={common.name} value={candidate.name} onChange={value => editCandidate("name", value)} />
        <DraftInput label={common.count} value={candidate.count} onChange={value => editCandidate("count", value)} />
        <DraftInput label={common.seed} value={candidate.seed} onChange={value => editCandidate("seed", value)} />
        <DraftInput label={text.tolerance} value={candidate.tolerance} onChange={value => editCandidate("tolerance", value)} />
      </div>
      {study.factors.some(factor => factor.domain_kind === "ordinal") && <label><input type="checkbox" checked={candidate.ordinal} onChange={event => editCandidate("ordinal", event.currentTarget.checked)} />{text.ordinalDistance}</label>}
      <p>{text.categoryMeaning}</p>
      <button type="button" disabled={!validCandidates} onClick={() => { if (count !== null && seed !== null && tolerance !== null) state.createCandidates(candidate.name, { kind: "seeded_uniform", count, seed }, tolerance, candidate.ordinal); }}>{common.generate}</button>
      <details><summary>{common.importTitle}</summary><p>{common.order}: {study.factors.map(factor => factor.name).join(" · ")}</p>
        <label>{common.content}<textarea value={candidate.content} onChange={event => editCandidate("content", event.currentTarget.value)} rows={5} /></label>
        <label><input type="checkbox" checked={candidate.header} onChange={event => editCandidate("header", event.currentTarget.checked)} />{common.header}</label>
        <div className="bo-planning-actions"><button type="button" onClick={importPreview}>{common.preview}</button><button type="button" disabled={!preview || preview.source !== key || !candidate.name.trim()} onClick={applyImport}>{common.apply}</button></div>
        {preview?.source === key && <p>{text.previewRows}: {preview.points.length}</p>}{inputError && <p role="alert">{common.inputError}</p>}
      </details>
    </fieldset>
    <label>{common.sets}<select aria-label={common.sets} disabled={locked} value={state.page?.revision.revision_id ?? ""} onChange={event => state.openPage(event.currentTarget.value)}><option value="">{common.choose}</option>{state.candidates.map(item => <option key={item.revision_id} value={item.revision_id}>{item.name} · {item.revision_number} · {item.source_is_current ? common.current : common.historical}</option>)}</select></label>
    {state.page && <>
      <p>{common.rowsHash}: <code>{state.page.revision.rows_sha256}</code></p><p>{auto.displayLimit}</p>
      <div className="bo-planning-actions"><button type="button" disabled={locked || state.page.offset === 0} onClick={() => state.openPage(state.page!.revision.revision_id, Math.max(0, state.page!.offset - state.page!.limit))}>{common.previous}</button>
        <span>{state.page.offset + 1}–{state.page.offset + state.page.items.length} / {state.page.revision.row_count}</span>
        <button type="button" disabled={locked || state.page.offset + state.page.items.length >= state.page.revision.row_count} onClick={() => state.openPage(state.page!.revision.revision_id, state.page!.offset + state.page!.limit)}>{common.next}</button>
        <button type="button" disabled={locked || !selectedModel} onClick={state.evaluatePage}>{common.evaluate}</button></div>
      <div className="table-wrap"><table className="result-table"><caption className="bo-planning-caption">{common.candidates}</caption><thead><tr><th>{common.select}</th><th>{common.row}</th>{study.factors.map(factor => <th key={factor.factor_id}>{factor.name}{factor.unit ? ` (${factor.unit})` : ""}</th>)}<th>{common.eligibility}</th><th>{common.distance}</th><th>{common.expected}</th><th>{common.sd}</th><th>{common.ei}</th></tr></thead>
        <tbody>{state.page.items.map((row, index) => { const prediction = state.evaluatedPage && state.page && state.evaluatedPage.revision === state.page.revision.revision_id && state.evaluatedPage.offset === state.page.offset && state.evaluatedPage.model === selectedModel?.model_id ? state.evaluatedPage.rows[index] : null; return <tr key={row.row_id}>
          <td><input type="checkbox" aria-label={`${common.select} ${row.source_row_number}`} checked={state.selectedIds.includes(row.row_id)} disabled={locked || !row.eligible || (state.selectedIds.length >= 8 && !state.selectedIds.includes(row.row_id)) || state.draft.kind !== "manual_ordered"} onChange={event => state.reorder(event.currentTarget.checked ? [...state.selectedIds, row.row_id] : state.selectedIds.filter(id => id !== row.row_id))} /></td>
          <th scope="row">{row.source_row_number}</th>{study.factors.map(factor => <td key={factor.factor_id}>{mixedValue(row.actual_coordinates[factor.factor_id])}</td>)}<td>{row.eligible ? common.yes : common.no}{!row.novel && <p>{common.notNovel}</p>}{!row.constraints_satisfied && <p>{common.constraintFailure}</p>}</td><td>{exact(row.nearest_existing_distance)}</td><td>{prediction ? exact(prediction.desirability_moments.mean) : common.none}</td><td>{prediction ? exact(Math.sqrt(prediction.desirability_moments.variance)) : common.none}</td><td>{prediction?.acquisition ? exact(prediction.acquisition.value) : common.none}</td>
        </tr>; })}</tbody></table></div>
    </>}
    <fieldset className="bo-planning-fieldset" disabled={locked}>
      <legend>{common.selected}</legend>
      {selectedModel && <BayesianAutoStrategyPanel studyId={study.study_id} model={selectedModel} mixed
        contextKey={`${key}:${state.page?.revision.revision_id ?? ""}:${JSON.stringify(state.draft)}:${JSON.stringify(state.selectedIds)}`} kinds={study.factors.map(factor => factor.domain_kind)}
        disabled={locked} onApply={state.applyAuto} onAdviceEdit={() => state.invalidate()} />}
      {state.autoReference && <p role="status">{autoEvidenceMessages(locale).attached}: {exact(state.autoReference.r_squared_threshold)}</p>}
      <label>{text.selectionKind}<select aria-label={text.selectionKind} value={state.draft.kind} onChange={event => state.updateDraft({ ...state.draft, kind: event.currentTarget.value as "manual_ordered" | "augmentation" })}><option value="manual_ordered">{text.manual}</option><option value="augmentation">{text.automatic}</option></select></label>
      {state.draft.kind === "augmentation" ? <><label>{auto.policy}<select value={state.draft.policy} onChange={event => state.updateDraft({ ...state.draft, policy: event.currentTarget.value as AugmentationPolicy })}>{policies.map(policy => <option key={policy} value={policy}>{augmentationPolicyLabel(policy, locale)}</option>)}</select></label><p>{auto.policyMeaning}</p><p>{state.draft.policy === "greedy_mixed_maximin_v1" ? auto.maximinMeaning : state.draft.policy === "confirm_mean_then_competitive_sd_v1" ? auto.confirmMeaning : auto.refineMeaning}</p><DraftInput label={auto.batch} value={state.draft.batchSize} onChange={value => state.updateDraft({ ...state.draft, batchSize: value })} /></> : <>
        <p>{common.selectionMeaning}</p><div className="bo-planning-actions"><button type="button" title={common.undo} aria-label={common.undo} disabled={!state.canUndo} onClick={state.undo}><Undo2 size={16} /></button><button type="button" title={common.redo} aria-label={common.redo} disabled={!state.canRedo} onClick={state.redo}><Redo2 size={16} /></button><button type="button" disabled={!state.selectedIds.length} onClick={() => state.reorder([])}>{common.clear}</button></div>
        <ol className="bo-planning-order">{state.selectedIds.map((id, index) => <li key={id}><code>{id}</code><button type="button" title={common.up} aria-label={`${common.up} ${index + 1}`} disabled={index === 0} onClick={() => { const ids = [...state.selectedIds]; [ids[index - 1], ids[index]] = [ids[index], ids[index - 1]]; state.reorder(ids); }}><ArrowUp size={16} /></button><button type="button" title={common.down} aria-label={`${common.down} ${index + 1}`} disabled={index === state.selectedIds.length - 1} onClick={() => { const ids = [...state.selectedIds]; [ids[index + 1], ids[index]] = [ids[index], ids[index + 1]]; state.reorder(ids); }}><ArrowDown size={16} /></button></li>)}</ol>
        {state.page && <button type="button" disabled={!state.selectedIds.length} onClick={() => state.createCandidates(state.page!.revision.name, { kind: "remove_rows", row_ids: state.selectedIds }, state.page!.revision.duplicate_tolerance, state.page!.revision.ordinal_rank_distance, true)}>{common.remove}</button>}
      </>}
      <div className="bo-planning-controls">{([['budget', common.totalBudget], ['distance', text.minimumDistance], ['samples', text.samples], ['evaluations', auto.evaluations], ['moments', text.moments], ['seconds', text.seconds]] as const).map(([field, label]) => <DraftInput key={field} label={label} value={state.draft[field]} onChange={value => state.updateDraft({ ...state.draft, [field]: value })} />)}</div>
      <button type="button" disabled={!state.canReview} onClick={state.review}>{state.draft.kind === "augmentation" ? auto.review : common.review}</button>{!state.canReview && <p>{auto.invalid}</p>}
      <label>{common.savedSelections}<select aria-label={common.savedSelections} value={state.selection?.selection_id ?? ""} onChange={event => state.openSelection(event.currentTarget.value)}><option value="">{common.choose}</option>{state.selections.map(selection => <option key={selection.selection_id} value={selection.selection_id}>{selection.created_at} · {selection.kind === "manual_ordered" ? text.manual : text.automatic} · {selection.selected_count}</option>)}</select></label>
    </fieldset>
    {state.selection && <><MixedSelectionDetails selection={state.selection} study={study} /><button type="button" className="primary-button" disabled={locked || !state.canConfirm} onClick={state.confirm}><Check size={16} aria-hidden="true" />{common.confirm}</button>{state.selection.confirmed_batch_id && <button type="button" onClick={() => props.onConfirmed(state.selection!.confirmed_batch_id!)}>{common.openBatch}</button>}</>}
    {selectedModel && <section aria-label={text.profile}><h4>{text.profile}</h4><p>{common.profileMeaning}</p><p>{text.profileDraft}</p><fieldset className="bo-planning-fieldset" disabled={locked}>
      <legend>{text.hold}</legend><div className="bo-planning-controls">{study.factors.map(factor => <label key={factor.factor_id}>{factor.name}{factor.unit ? ` (${factor.unit})` : ""}{isMixedCategory(factor) ? <select value={profileInput.holds[factor.factor_id]} onChange={event => editHold(factor.factor_id, event.currentTarget.value)}>{factor.levels.map(level => <option key={level} value={level}>{level}</option>)}</select> : <input type="text" value={profileInput.holds[factor.factor_id]} onChange={event => editHold(factor.factor_id, event.currentTarget.value)} />}</label>)}</div>
      <label>{common.axis}<select aria-label={common.axis} value={profileInput.axis} onChange={event => { const axis = event.currentTarget.value; if (state.invalidate(false)) setProfileDraft({ ...profileInput, axis }); }}>{study.factors.map(factor => <option key={factor.factor_id} value={factor.factor_id}>{factor.name}</option>)}</select></label>
      <div className="bo-planning-actions"><button type="button" disabled={!point} onClick={() => { if (point) void state.evaluate([point], null); }}>{common.point}</button><button type="button" disabled={!profilePoints} onClick={() => { if (profilePoints) void state.evaluate(profilePoints, profileInput.axis); }}>{isMixedCategory(study.factors.find(factor => factor.factor_id === profileInput.axis)!) ? text.levelProfile : common.curve}</button></div>{!profilePoints && <p>{common.profileInvalid}</p>}
    </fieldset>{state.profile && <><MixedProfileView profile={state.profile} study={study} />{state.profile.points.length === 1 && state.page && <button type="button" disabled={locked || study.status !== "active"} onClick={() => state.createCandidates(state.page!.revision.name, { kind: "append_rows", points: state.profile!.points }, state.page!.revision.duplicate_tolerance, state.page!.revision.ordinal_rank_distance, true)}>{common.append}</button>}</>}</section>}
  </section>;
}

function DraftInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) { return <label>{label}<input type="text" value={value} onChange={event => onChange(event.currentTarget.value)} /></label>; }
function mixedValue(value: string | number | null | undefined) { return typeof value === "string" ? value : exact(value); }
function MixedFitSettings({ draft, onChange, study }: { draft: MixedFitDraft; onChange: (draft: MixedFitDraft) => void; study: MixedStudyResponse }) {
  const { locale } = useI18n(), text = mixedMessages(locale);
  return <>{draft.models.map((model, index) => { const response = study.objective.responses.find(item => item.response_id === model.responseId); const change = <K extends keyof typeof model>(key: K, value: typeof model[K]) => onChange({ ...draft, models: draft.models.map((row, at) => at === index ? { ...row, [key]: value } : row) }); return <fieldset className="bo-planning-fieldset" key={model.responseId}><legend>{response?.name}{response?.unit ? ` (${response.unit})` : ""}</legend><div className="bo-planning-controls">
    <label>{text.kernel}<select aria-label={text.kernel} value={model.kernel} onChange={event => change("kernel", event.currentTarget.value as typeof model.kernel)}><option value="matern_5_2">Matérn 5/2</option><option value="matern_3_2">Matérn 3/2</option><option value="gaussian">Gaussian / RBF</option><option value="exponential">Exponential</option></select></label>
    <label>{text.noise}<select aria-label={text.noise} value={model.noise} onChange={event => change("noise", event.currentTarget.value as typeof model.noise)}><option value="estimate">{text.estimate}</option><option value="fixed">{text.fixed}</option><option value="near_noiseless">{text.nearNoiseless}</option></select></label>
    {model.noise === "fixed" && <DraftInput label={text.fixedSd} value={model.fixedSd} onChange={value => change("fixedSd", value)} />}{model.noise === "estimate" && <>{([['initial', text.initialNoise], ['lower', text.lowerNoise], ['upper', text.upperNoise]] as const).map(([key, label]) => <DraftInput key={key} label={label} value={model[key]} onChange={value => change(key, value)} />)}</>}
  </div></fieldset>; })}<div className="bo-planning-controls"><label>{text.aggregation}<select value={draft.aggregation} onChange={event => onChange({ ...draft, aggregation: event.currentTarget.value as MixedFitDraft["aggregation"] })}><option value="retain_raw">{text.retainRaw}</option><option value="exact_replicates">{text.exactReplicates}</option></select></label>
    {([['xi', text.xi], ['seed', text.modelSeed], ['seconds', text.seconds], ['evaluations', text.evaluations], ['starts', text.starts], ['restarts', text.restarts], ['moments', text.moments]] as const).map(([key, label]) => <DraftInput key={key} label={label} value={draft[key]} onChange={value => onChange({ ...draft, [key]: value })} />)}</div></>;
}
export function MixedFitReceipt({ model, study }: { model: Pick<MixedModelDetail, "model_id" | "snapshot_sha256" | "source_is_current" | "response_models" | "warnings">; study: MixedStudyResponse }) {
  const { locale } = useI18n(), text = mixedMessages(locale), common = planningMessages(locale);
  return <section aria-label={text.model}><h4>{text.model}</h4><p>{model.source_is_current ? common.current : common.historical}</p><p>{text.fitApplied}</p><dl className="bo-planning-source"><div><dt>{common.model}</dt><dd>{model.model_id}</dd></div><div><dt>{common.modelHash}</dt><dd>{model.snapshot_sha256}</dd></div></dl>
    <div className="table-wrap"><table className="result-table"><thead><tr><th>{text.response}</th><th>{common.rawCount}</th><th>{common.effectiveCount}</th><th>{text.sigmaNoise}</th><th>{common.jitter}</th><th>{text.fitStatus}</th></tr></thead><tbody>{model.response_models.map(response => { const starts = objects(record(response.model.optimizer).starts); return <tr key={response.response_id}><th scope="row">{study.objective.responses.find(item => item.response_id === response.response_id)?.name ?? response.response_id}</th>{[response.model.raw_observation_count, response.model.effective_training_count, response.model.observation_noise_sd_raw, response.model.jitter].map((value, index) => <td key={index}>{typeof value === "number" ? exact(value) : "-"}</td>)}<td>{starts.length > 0 ? starts.map((start, index) => <div key={index}>{index + 1}: {start.success === true ? common.yes : common.no} · {typeof start.status === "number" ? start.status : "-"}</div>) : "-"}</td></tr>; })}</tbody></table></div>
    {model.warnings.length > 0 && <details open><summary>{common.fitWarnings}</summary><ul>{model.warnings.map((warning, index) => <li key={`${index}:${warning}`}>{common.unknownWarning} <code>{warning}</code></li>)}</ul></details>}
    <details><summary>{text.coverage}</summary>{model.response_models.map(response => <div key={response.response_id}><strong>{study.objective.responses.find(item => item.response_id === response.response_id)?.name}</strong><MixedCoverage metadata={response.model.training_level_coverage} study={study} /></div>)}</details>
    <details><summary>{text.parameters}</summary>{model.response_models.map(response => { const diagnostics = record(response.model.fit_diagnostics), selected = record(diagnostics.selected), parameters = Array.isArray(selected.log_parameters) ? selected.log_parameters : [], descriptors = objects(response.model.parameter_descriptors); return <div key={response.response_id}><h5>{study.objective.responses.find(item => item.response_id === response.response_id)?.name}</h5><div className="table-wrap"><table className="result-table"><thead><tr><th>{text.rawCode}</th><th>{text.factor}</th><th>{text.parameterValue}</th></tr></thead><tbody>{descriptors.map((descriptor, index) => <tr key={index}><th scope="row"><code>{typeof descriptor.role === "string" ? descriptor.role : "-"}</code></th><td>{study.factors.find(item => item.factor_id === descriptor.factor_id)?.name ?? "-"}</td><td>{typeof parameters[index] === "number" && Number.isFinite(parameters[index]) ? exact(Math.exp(parameters[index])) : "-"}</td></tr>)}</tbody></table></div></div>; })}</details>
  </section>;
}
function MixedCoverage({ metadata, study }: { metadata: unknown; study: MixedStudyResponse }) {
  const values = objects(metadata);
  return <ul>{study.factors.filter(isMixedCategory).map(factor => { const counts = values.find(item => item.factor_id === factor.factor_id)?.raw_observation_counts; return <li key={factor.factor_id}>{factor.name}: {Array.isArray(counts) && counts.length === factor.levels.length && counts.every(value => typeof value === "number" && Number.isFinite(value)) ? counts.map((count, index) => <span key={index}>{factor.levels[index]}: {count}; </span>) : "-"}</li>; })}</ul>;
}
function record(value: unknown): Record<string, unknown> { return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : {}; }
function objects(value: unknown): Record<string, unknown>[] { return Array.isArray(value) ? value.filter(item => typeof item === "object" && item !== null && !Array.isArray(item)) as Record<string, unknown>[] : []; }
export function MixedSelectionDetails({ selection, study }: { selection: Pick<MixedSelectionResponse, "selection_id" | "result_sha256" | "calculation" | "request">; study: MixedStudyResponse }) {
  const { locale } = useI18n(), text = mixedMessages(locale), common = planningMessages(locale);
  return <section aria-label={common.reviewed}><h4>{common.reviewed}</h4><p>{selection.selection_id}</p><p><code>{selection.result_sha256}</code></p>{selection.calculation.schema_version !== 2 ? <><p>{text.automaticMeaning}</p><AugmentationTraceTable calculation={selection.calculation} study={study} /></> : <>
    <MixedPredictionTable rows={selection.calculation.items} study={study} /><div className="table-wrap"><table className="result-table"><thead><tr><th>{common.rank}</th><th>{common.marginal}</th></tr></thead><tbody>{selection.calculation.items.map(row => <tr key={row.row_id}><th scope="row">{row.rank}</th><td>{exact(row.planning.score)}</td></tr>)}</tbody></table></div>
  </>}</section>;
}
function MixedPredictionTable({ rows, study }: { rows: (MixedCandidateRow | EvaluatedMixedCandidateRow)[]; study: MixedStudyResponse }) {
  const { locale } = useI18n(), text = planningMessages(locale);
  return <><div className="table-wrap"><table className="result-table"><caption className="bo-planning-caption">{text.evaluated}</caption><thead><tr><th>{text.rank}</th>{study.factors.map(factor => <th key={factor.factor_id}>{factor.name}{factor.unit ? ` (${factor.unit})` : ""}</th>)}<th>{text.expected}</th><th>{text.sd}</th><th>{text.ei}</th></tr></thead><tbody>{rows.map((row, index) => <tr key={row.row_id}><th scope="row">{index + 1}</th>{study.factors.map(factor => <td key={factor.factor_id}>{mixedValue(row.actual_coordinates[factor.factor_id])}</td>)}<td>{"desirability_moments" in row ? exact(row.desirability_moments.mean) : text.none}</td><td>{"desirability_moments" in row ? exact(Math.sqrt(row.desirability_moments.variance)) : text.none}</td><td>{"acquisition" in row && row.acquisition ? exact(row.acquisition.value) : text.none}</td></tr>)}</tbody></table></div>
    <div className="table-wrap"><table className="result-table"><thead><tr><th>{text.rank}</th><th>{text.response}</th><th>{text.mean}</th><th>{text.latent}</th><th>{text.predictive}</th></tr></thead><tbody>{rows.flatMap((row, index) => "response_predictions" in row ? row.response_predictions.map(prediction => { const response = study.objective.responses.find(item => item.response_id === prediction.response_id); return <tr key={`${row.row_id}:${prediction.response_id}`}><td>{index + 1}</td><th scope="row">{response?.name}{response?.unit ? ` (${response.unit})` : ""}</th><td>{exact(prediction.mean_raw)}</td><td>{exact(prediction.latent_standard_deviation_raw)}</td><td>{exact(prediction.predictive_standard_deviation_raw)}</td></tr>; }) : [])}</tbody></table></div></>;
}
export function MixedProfileView({ profile, study }: { profile: MixedProfile; study: MixedStudyResponse }) {
  const { locale } = useI18n(), text = planningMessages(locale), mixed = mixedMessages(locale), [quantity, setQuantity] = useState("desirability"), [metric, setMetric] = useState<"mean" | "latent" | "predictive">("mean");
  const factor = study.factors.find(item => item.factor_id === profile.axis), response = study.objective.responses.find(item => `response:${item.response_id}` === quantity), category = factor ? isMixedCategory(factor) : false;
  const points = profile.rows.map((row, index) => { const prediction = row.response_predictions.find(item => item.response_id === response?.response_id); const y = quantity === "desirability" ? row.desirability_moments.mean : metric === "latent" ? prediction?.latent_standard_deviation_raw : metric === "predictive" ? prediction?.predictive_standard_deviation_raw : prediction?.mean_raw;
    const label = factor ? mixedValue(row.actual_coordinates[factor.factor_id]) : String(index + 1), value = y ?? NaN;
    const constraint = row.constraints_satisfied ? text.constraintsSatisfied : text.constraintFailure;
    return { id: row.row_id, x: factor && !category ? Number(row.actual_coordinates[factor.factor_id]) : index, y: value, ariaLabel: `${label}: ${exact(value)}, ${text.constraintStatus}: ${constraint}`, title: label,
      marker: row.constraints_satisfied ? "circle" as const : "diamond" as const, warning: !row.constraints_satisfied,
      className: "interactive-data-point", details: [{ label: factor?.name ?? text.rank, value: label }, { label: quantity === "desirability" ? text.expected : metric === "latent" ? text.latent : metric === "predictive" ? text.predictive : text.mean, value: exact(value) }, { label: text.constraintStatus, value: constraint }] };
  });
  const categoryTicks = category ? points.map(point => ({ value: point.x, label: point.title })) : undefined;
  return <section><p>{text.modelHash}: <code>{profile.modelHash}</code></p><dl className="bo-planning-source">{study.factors.filter(item => item.factor_id !== profile.axis).map(item => <div key={item.factor_id}><dt>{item.name}{item.unit ? ` (${item.unit})` : ""}</dt><dd>{mixedValue(profile.points[0][item.factor_id])}</dd></div>)}</dl>
    <div className="bo-planning-controls"><label>{text.profileQuantity}<select aria-label={text.profileQuantity} value={quantity} onChange={event => setQuantity(event.currentTarget.value)}><option value="desirability">{text.desirability}</option>{study.objective.responses.map(item => <option key={item.response_id} value={`response:${item.response_id}`}>{item.name}</option>)}</select></label>{quantity !== "desirability" && <label>{text.profileMetric}<select aria-label={text.profileMetric} value={metric} onChange={event => setMetric(event.currentTarget.value as typeof metric)}><option value="mean">{text.mean}</option><option value="latent">{text.latent}</option><option value="predictive">{text.predictive}</option></select></label>}</div>
    {factor && <><div className="bo-profile-detail"><InteractiveScatterChart annotations={[text.profileMeaning, category ? mixed.categoryMeaning : mixed.numericCurve]} chartId={`mixed-profile-${profile.modelId}`} sourceKey={`${profile.modelHash}:${profile.axis}:${JSON.stringify(profile.points)}:${quantity}:${metric}`} description={text.profileMeaning} title={category ? mixed.levelProfile : mixed.numericCurve} emptyLabel={text.none}
      points={points} connectPoints={category ? undefined : "line"} xLabel={factor.name} xUnit={factor.unit} xRange={paddedNumericRange(points.map(point => point.x))}
      xTicks={categoryDisplayTicks(categoryTicks)} yLabel={quantity === "desirability" ? text.expected : `${response?.name ?? quantity}: ${metric === "latent" ? text.latent : metric === "predictive" ? text.predictive : text.mean}`} yUnit={quantity === "desirability" ? null : response?.unit}
      yRange={paddedNumericRange(points.map(point => point.y))} />{categoryTicks && <BayesianProfileLevelMap ticks={categoryTicks} />}</div>
      <BayesianProfileGrid sourceKey={`${profile.modelId}:${profile.modelHash}:${JSON.stringify(profile.points)}`} axis={{ ...factor, category, meaning: category ? mixed.categoryMeaning : mixed.numericCurve }} responses={study.objective.responses} rows={profile.rows} /></>}
    <MixedPredictionTable rows={profile.rows} study={study} />
  </section>;
}
