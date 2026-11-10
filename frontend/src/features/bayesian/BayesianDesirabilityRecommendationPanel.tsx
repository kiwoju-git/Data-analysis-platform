import { Fragment, useEffect, useId, useRef } from "react";
import type { BayesianStudyResponse } from "../../api/types/bayesian";
import type { DesirabilityBatch, DesirabilityCalculation, DesirabilityReview } from "../../api/types/bayesianDesirability";
import { useI18n } from "../../i18n/LocaleProvider";
import { desirabilityMessages } from "../../i18n/boDesirability";
import { formatExactNumericValue as exact } from "../../statisticalNumberFormat";
import { BO_KERNEL_OPTIONS, boKernelLabel } from "./boKernelPolicy";
import { BayesianFitDiagnostics } from "./BayesianFitDiagnostics";
import { BayesianCurveSummary } from "./BayesianCurvePolicy";
import type { DesirabilityDraft, DesirabilityModelDraft } from "./bayesianDesirabilityDraft";
import type { useBayesianDesirabilityRecommendation } from "./hooks/useBayesianDesirabilityRecommendation";
import "./bayesianDesirability.css";

export type DesirabilityRecommendationState = ReturnType<typeof useBayesianDesirabilityRecommendation>;
interface Props {
  study: BayesianStudyResponse;
  state: DesirabilityRecommendationState;
  disabled: boolean;
  onConfirm: () => void;
  onRefresh: () => void;
}
export function BayesianDesirabilityRecommendationPanel({ study, state, disabled, onConfirm, onRefresh }: Props) {
  const { locale } = useI18n();
  const text = desirabilityMessages(locale);
  const id = useId();
  const errorRef = useRef<HTMLDivElement>(null);
  useEffect(() => { if (state.error) errorRef.current?.focus(); }, [state.error]);
  if (study.objective.goal_type !== "desirability") return null;
  const busy = state.isReviewing || state.isConfirming || state.isRestoring;
  const blocked = !study.recommendation_available;
  const fieldId = (key: string) => `${id}-${key.replace(/:/g, "-")}`;
  const fieldError = (key: string) => state.errors[key] ? <span id={`${fieldId(key)}-error`} className="field-error">{text[state.errors[key]]}</span> : null;
  function input(key: string, label: string, value: string, edit: (next: string) => void, integer = false) {
    return <label className="field" htmlFor={fieldId(key)}><span>{label}</span>
      <input id={fieldId(key)} value={value} inputMode={integer ? "numeric" : "decimal"}
        aria-invalid={Boolean(state.errors[key])} aria-describedby={state.errors[key] ? `${fieldId(key)}-error` : undefined}
        onChange={event => edit(event.target.value)} />{fieldError(key)}</label>;
  }
  const update = (key: Exclude<keyof DesirabilityDraft, "models">, value: string) => state.edit({ ...state.draft, [key]: value });
  const updateModel = (responseId: string, key: keyof DesirabilityModelDraft, value: string) => state.edit({
    ...state.draft, models: state.draft.models.map(model => model.responseId === responseId ? { ...model, [key]: value } : model),
  });
  return <section className="bo-desirability" aria-label={text.title}>
    <div className="panel-heading"><h4>{text.title}</h4><button type="button" className="secondary-button" disabled={busy || disabled} onClick={onRefresh}>{text.refresh}</button></div>
    <p className="notice-box">{text.limitation}</p>
    {state.error ? <div ref={errorRef} tabIndex={-1} className="error-box" role="alert">
      <strong>{Object.keys(state.errors).length ? text.errors : state.error.includes("precision_unsupported") ? text.precision : text.genericError}</strong>
      {Object.keys(state.errors).length ? <ul>{Object.entries(state.errors).map(([key, code]) => <li key={key}><a href={`#${fieldId(key)}`}>{key}: {text[code]}</a></li>)}</ul> : null}
      <code>{state.error}</code>
    </div> : null}
    {state.mayHaveCommitted ? <p className="notice-box" role="status">{text.uncertain}</p> : null}
    <fieldset className="bo-desirability-form" disabled={disabled || study.status !== "active"}>
      <legend>{text.settings}</legend><p className="muted">{text.currentDraft}</p>
      <div className="table-wrap"><table className="result-table bo-desirability-models">
        <thead><tr><th scope="col">{text.response}</th><th scope="col">{text.kernel}</th><th scope="col">{text.noise}</th><th scope="col">{text.fixedSd}</th></tr></thead>
        <tbody>{state.draft.models.map(model => {
          const response = study.objective.goal_type === "desirability" ? study.objective.responses.find(r => r.response_id === model.responseId) : undefined;
          return <Fragment key={model.responseId}><tr>
            <th scope="row">{response?.name ?? model.responseId}{response?.unit ? ` [${response.unit}]` : ""}</th>
            <td><select aria-label={`${response?.name ?? model.responseId}: ${text.kernel}`} id={fieldId(`${model.responseId}:kernel`)} value={model.kernel} onChange={e => updateModel(model.responseId, "kernel", e.target.value)}>
              {BO_KERNEL_OPTIONS.map(option => <option key={option.kind} value={option.kind}>{option.label}</option>)}
            </select></td>
            <td><select aria-label={`${response?.name ?? model.responseId}: ${text.noise}`} value={model.noise} onChange={e => updateModel(model.responseId, "noise", e.target.value)}>
              <option value="estimate">{text.estimate}</option><option value="fixed">{text.fixed}</option><option value="near_noiseless">{text.near}</option>
            </select></td>
            <td>{model.noise === "fixed" ? input(`${model.responseId}:fixedSd`, response?.unit ?? text.fixed, model.fixedSd, value => updateModel(model.responseId, "fixedSd", value)) : "-"}</td>
          </tr>{model.noise === "estimate" || state.errors[`${model.responseId}:initial`] || state.errors[`${model.responseId}:lower`] || state.errors[`${model.responseId}:upper`] ? <tr><td colSpan={4}><details open={Boolean(state.errors[`${model.responseId}:initial`] || state.errors[`${model.responseId}:lower`] || state.errors[`${model.responseId}:upper`]) || undefined}>
            <summary>{response?.name ?? model.responseId}: {text.advanced}</summary>
            <div className="option-grid bo-desirability-settings">
              {input(`${model.responseId}:initial`, text.initial, model.initial, value => updateModel(model.responseId, "initial", value))}
              {input(`${model.responseId}:lower`, text.lower, model.lower, value => updateModel(model.responseId, "lower", value))}
              {input(`${model.responseId}:upper`, text.upper, model.upper, value => updateModel(model.responseId, "upper", value))}
            </div></details></td></tr> : null}</Fragment>;
        })}</tbody>
      </table></div>
      <div className="option-grid bo-desirability-settings">
        <label className="field" htmlFor={fieldId("batchSize")}><span id={`${fieldId("batchSize")}-label`}>{text.batchSize}</span><select aria-labelledby={`${fieldId("batchSize")}-label`} id={fieldId("batchSize")} value={state.draft.batchSize} onChange={e => update("batchSize", e.target.value)}>
          {Array.from({ length: 8 }, (_, i) => <option key={i + 1} value={String(i + 1)}>{i + 1}</option>)}
        </select>{fieldError("batchSize")}</label>
        <label className="field"><span>{text.aggregation}</span><select id={fieldId("aggregation")} value={state.draft.aggregation} onChange={e => update("aggregation", e.target.value)}><option value="retain_raw">{text.raw}</option><option value="exact_replicates">{text.exact}</option></select></label>
        {input("xi", text.xi, state.draft.xi, value => update("xi", value))}
        {input("totalBudget", text.total, state.draft.totalBudget, value => update("totalBudget", value), true)}
        {input("seed", text.seed, state.draft.seed, value => update("seed", value), true)}
        {input("timeMs", text.time, state.draft.timeMs, value => update("timeMs", value), true)}
        {input("modelEvaluations", text.evaluations, state.draft.modelEvaluations, value => update("modelEvaluations", value), true)}
        <label className="field" htmlFor={fieldId("fitPolicy")}><span id={`${fieldId("fitPolicy")}-label`}>{text.fitPolicy}</span><select id={fieldId("fitPolicy")} aria-labelledby={`${fieldId("fitPolicy")}-label`} value={state.draft.fitPolicy} onChange={e => update("fitPolicy", e.target.value)}>
          <option value="legacy">{text.legacyFit}</option><option value="bounded_multiscale_starts_v1">{text.multiscaleFit}</option>
        </select></label>
        {state.draft.fitPolicy !== "legacy" ? input("deterministicStarts", text.deterministicStarts, state.draft.deterministicStarts, value => update("deterministicStarts", value), true) : null}
        {input("randomRestarts", text.randomRestarts, state.draft.randomRestarts, value => update("randomRestarts", value), true)}
      </div>
      {state.draft.fitPolicy !== "legacy" ? <p className="muted">{text.fitNote}</p> : null}
      {state.draft.batchSize !== "1" || state.draft.fitPolicy !== "legacy" || study.objective.curve_policy === "per_response_target_gaussian_or_ds_v1" ? <fieldset className="bo-desirability-form"><legend>{text.batchSettings}</legend>
        <div className="option-grid bo-desirability-settings">
          {input("sampleCount", text.sampleCount, state.draft.sampleCount, value => update("sampleCount", value), true)}
          {input("momentBudget", text.momentBudget, state.draft.momentBudget, value => update("momentBudget", value), true)}
          {input("candidateBudget", text.candidateBudget, state.draft.candidateBudget, value => update("candidateBudget", value), true)}
          {input("minDistance", text.minDistance, state.draft.minDistance, value => update("minDistance", value))}
        </div><p className="muted">{text.batchBudgetNote}</p>
      </fieldset> : null}
      {blocked ? <p className="muted">{text.blocked}</p> : null}
      <div className="bo-vector-actions"><button type="button" className="primary-button" disabled={busy || blocked || state.mayHaveCommitted} onClick={() => void state.requestReview()}>{state.isReviewing ? text.reviewing : text.review}</button></div>
    </fieldset>
    {state.isRestoring ? <p role="status">{text.restore}</p> : null}
    {state.review ? <>
      <DesirabilityCandidate study={study} calculation={state.review.calculation} source={state.review} />
      <div className="bo-vector-actions"><button type="button" className="primary-button" disabled={busy || disabled || blocked} onClick={onConfirm}>{state.isConfirming ? text.confirming : text.confirm}</button>
        <button type="button" className="secondary-button" disabled={state.isConfirming} onClick={state.discard}>{text.discard}</button></div>
    </> : state.saved ? <DesirabilityCandidate study={study} calculation={state.saved.calculation} source={state.saved} />
      : !state.isRestoring ? <p className="muted">{text.noSaved}</p> : null}
  </section>;
}

export function DesirabilityCandidate({ study, calculation, source }: {
  study: BayesianStudyResponse; calculation: DesirabilityCalculation; source: DesirabilityReview | DesirabilityBatch;
}) {
  const { locale } = useI18n(); const text = desirabilityMessages(locale);
  const saved = "batch_id" in source ? source : null;
  const oldHistory = source.source_observation_history_sha256 !== study.observation_history.observation_history_sha256;
  const trialStateLabel = (value: string) => value === "completed" ? text.completed : value === "abandoned" ? text.abandoned : text.pending;
  const stateLabel = saved?.batch_state === "partially_completed" ? text.partial : saved?.batch_state === "closed_mixed" ? text.mixed : trialStateLabel(saved?.batch_state ?? "pending");
  return <section className="bo-desirability-result" aria-label={saved ? text.saved : text.temporary}>
    <h5>{saved ? `${text.saved}: ${stateLabel}` : text.temporary}</h5>
    {saved ? <p><a href="/reports?source_kind=bayesian_history_revision">{text.reports}</a></p> : null}
    {oldHistory ? <p className="notice-box">{text.stale}</p> : null}
    {calculation.warnings.includes("bayesian_acquisition_numerically_zero") ? <p className="notice-box">{text.allZero}</p> : null}
    <dl className="bo-desirability-summary">
      {[[text.observedBest, calculation.incumbent.best_observed_desirability], [text.incumbent, calculation.incumbent.latent_incumbent_value]]
        .map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{exact(value as number)}</dd></div>)}
    </dl>
    <p>{text.batchMeaning}</p>
    <p>{text.basePosterior}</p>
    {calculation.batch_size > 1 ? <div className="table-wrap"><table className="result-table bo-desirability-overview"><caption>{text.ordered}</caption>
      <thead><tr><th scope="col">{text.rank}</th>{study.factors.map(factor => <th scope="col" key={factor.factor_id}>{factor.name}{factor.unit ? ` [${factor.unit}]` : ""}</th>)}
        <th scope="col">{text.meanD}</th><th scope="col">{text.marginal}</th>{saved ? <th scope="col">{text.state}</th> : null}</tr></thead>
      <tbody>{calculation.items.map((candidate, index) => <tr key={candidate.rank} data-candidate-rank={candidate.rank}>
        <th scope="row">{candidate.rank}</th>{study.factors.map(factor => <td key={factor.factor_id}>{exact(candidate.actual_coordinates[factor.factor_id])}</td>)}
        <td>{exact(candidate.desirability_moments.mean)}</td><td>{exact("planning" in candidate ? candidate.planning.score : candidate.acquisition.value)}</td>
        {saved ? <td>{trialStateLabel(saved.items[index].current_trial.state)}</td> : null}
      </tr>)}</tbody></table></div> : null}
    {calculation.items.map((candidate, index) => <section className="bo-desirability-candidate" key={candidate.rank} aria-label={`${text.rank} ${candidate.rank}`}>
    <h6>{text.rank} {candidate.rank}</h6>
    <dl className="bo-desirability-summary">{[[text.meanD, candidate.desirability_moments.mean], [text.varianceD, candidate.desirability_moments.variance],
      [text.ei, candidate.acquisition.value], [text.nearest, candidate.nearest_existing_distance]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{exact(value as number)}</dd></div>)}</dl>
    <div className="table-wrap"><table className="result-table"><caption>{text.coordinates}</caption><thead><tr><th scope="col">{text.factor}</th><th scope="col">{text.value}</th></tr></thead>
      <tbody>{study.factors.map(factor => <tr key={factor.factor_id}><th scope="row">{factor.name}{factor.unit ? ` [${factor.unit}]` : ""}</th><td>{exact(candidate.actual_coordinates[factor.factor_id])}</td></tr>)}</tbody>
    </table></div>
    <div className="table-wrap"><table className="result-table"><caption>{text.prediction}</caption><thead><tr><th scope="col">{text.response}</th><th scope="col">{text.mean}</th><th scope="col">{text.latent}</th><th scope="col">{text.predictive}</th></tr></thead>
      <tbody>{calculation.objective.responses.map(response => {
        const prediction = candidate.response_predictions.find(row => row.response_id === response.response_id);
        return <tr key={response.response_id}><th scope="row">{response.name}{response.unit ? ` [${response.unit}]` : ""}</th><td>{exact(prediction?.mean_raw)}</td><td>{exact(prediction?.latent_standard_deviation_raw)}</td><td>{exact(prediction?.predictive_standard_deviation_raw)}</td></tr>;
      })}</tbody>
    </table></div>
    {saved ? <><p>{text.state}: {trialStateLabel(saved.items[index].current_trial.state)}</p><p>{text.actual}: {saved.items[index].current_trial.state === "completed"
      ? calculation.objective.responses.map(response => `${response.name}: ${exact(saved.items[index].current_trial.response_values?.[response.response_id])}`).join("; ") : "-"}</p></> : null}
    {"planning" in candidate ? <details><summary>{text.planning}</summary>
      <dl className="bo-desirability-summary">
        <div><dt>{text.marginal}</dt><dd>{exact(candidate.planning.score)}</dd></div>
        <div><dt>{text.mcse}</dt><dd>{exact(candidate.planning.mc_standard_error)}</dd></div>
        <div><dt>{text.nearestSelected}</dt><dd>{exact(candidate.nearest_selected_distance)}</dd></div>
        <div><dt>{text.conditioned}</dt><dd>{candidate.planning.sampler.conditioned_on_selected_ranks.join(", ") || "-"}</dd></div>
        <div><dt>{text.samples}</dt><dd>{candidate.planning.sampler.effective_sample_count} / {candidate.planning.sampler.requested_sample_count}</dd></div>
        {calculation.objective.responses.map(response => <div key={response.response_id}><dt>{response.name}: {text.conditionalVariance}</dt><dd>{exact(candidate.planning.conditional_variance_raw[response.response_id])}</dd></div>)}
      </dl><p>{text.seed}: {candidate.planning.sampler.root_seed}; {candidate.planning.search_seed}</p>
    </details> : null}
    {candidate.constraint_evaluations.length ? <details><summary>{text.constraints}</summary><ul>{candidate.constraint_evaluations.map(check => <li key={check.constraint_id}>{check.name}: {exact(check.lhs)} {check.relation === "less_than_or_equal" ? "<=" : ">="} {exact(check.bound)} ({check.satisfied ? text.satisfied : text.violated})</li>)}</ul></details> : null}
    </section>)}
    <p>{text.observations}: {calculation.observation_view.raw_observation_count} / {calculation.observation_view.unique_condition_count} / {calculation.observation_view.effective_training_count}</p>
    <BayesianCurveSummary responses={calculation.objective.responses} />
    {calculation.schema_version === 6 || calculation.schema_version === 7 ? <BayesianFitDiagnostics calculation={calculation} sourceKey={saved?.result_sha256 ?? source.config_sha256} /> : null}
    <details><summary>{text.models}</summary><div className="table-wrap"><table className="result-table"><thead><tr><th scope="col">{text.response}</th><th scope="col">{text.kernel}</th><th scope="col">{text.noise}</th><th scope="col">{text.fittedNoise}</th><th scope="col">{text.weight}</th></tr></thead>
      <tbody>{calculation.shared_model.response_models.map(row => {
        const response = calculation.objective.responses.find(r => r.response_id === row.response_id);
        return <tr key={row.response_id}><th scope="row">{response?.name ?? row.response_id}</th><td>{boKernelLabel(row.model.signal_kernel.family)}</td><td>{row.model.noise.mode}</td><td>{exact(row.model.observation_noise_sd_raw)}</td><td>{exact(calculation.shared_model.normalized_importance.find(w => w.response_id === row.response_id)?.weight)}</td></tr>;
      })}</tbody></table></div></details>
    <details className="technical-details"><summary>{text.source}</summary>
      <p>Study: {source.study_id}</p><p>History: {source.source_history_revision_id}</p><p>History SHA-256: {source.source_observation_history_sha256}</p><p>Config SHA-256: {source.config_sha256}</p>
      {saved ? <><p>Batch: {saved.batch_id}</p><p>Result SHA-256: {saved.result_sha256}</p>{saved.items.map(item => <p key={item.item_id}>Trial {item.rank}: {item.trial.trial_id}</p>)}</> : <><p>Review: {(source as DesirabilityReview).review_id}</p><p>{text.expires}: {(source as DesirabilityReview).expires_at}</p></>}
      <p>Curve: {calculation.shared_model.curve_policy}</p><p>Acquisition: {calculation.policy}</p>
      {calculation.schema_version !== 4 ? <p>{text.momentBudget}: {calculation.search_budget.moment_evaluations} / {calculation.batch_options.max_moment_evaluations}; {text.minDistance}: {exact(calculation.batch_options.min_batch_distance_normalized)}</p> : null}
      <p>{text.budgetUsed}: {calculation.search_budget.evaluations_consumed} / {calculation.search_budget.model_evaluations_consumed}</p>
      <p>{calculation.search_budget.termination_reason}</p>
    </details>
    <details><summary>{text.warnings}</summary><p>{text.limitation}</p><ul>{[...new Set([...calculation.warnings, ...calculation.limitations])].map(code => <li key={code}><code>{code}</code></li>)}</ul></details>
  </section>;
}
