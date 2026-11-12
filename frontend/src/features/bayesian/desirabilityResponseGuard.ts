import type { BayesianStudyResponse } from "../../api/types/bayesian";
import type { DesirabilityBatch, DesirabilityCalculation, DesirabilityReviewRequest } from "../../api/types/bayesianDesirability";

export function sameDesirabilityJson(left: unknown, right: unknown): boolean {
  if (Object.is(left, right)) return true;
  if (Array.isArray(left) && Array.isArray(right)) return left.length === right.length && left.every((item, i) => sameDesirabilityJson(item, right[i]));
  if (left === null || right === null || typeof left !== "object" || typeof right !== "object" || Array.isArray(left) || Array.isArray(right)) return false;
  const a = left as Record<string, unknown>, b = right as Record<string, unknown>;
  return Object.keys(a).length === Object.keys(b).length && Object.keys(a).every(key => Object.prototype.hasOwnProperty.call(b, key) && sameDesirabilityJson(a[key], b[key]));
}
const sameIds = (actual: string[], expected: string[]) => actual.length === expected.length && new Set(actual).size === expected.length && actual.every(id => expected.includes(id));
export function validDesirabilityCalculation(calculation: DesirabilityCalculation, study: BayesianStudyResponse, request?: DesirabilityReviewRequest): boolean {
  if (study.objective.goal_type !== "desirability" || !calculation || !Number.isInteger(calculation.batch_size) ||
    calculation.batch_size < 1 || calculation.batch_size > 8 || calculation.shared_model?.schema_version !== (calculation.schema_version >= 6 ? calculation.schema_version : 5) ||
    calculation.items?.length !== calculation.batch_size) return false;
  if (calculation.schema_version === 4) {
    if (calculation.batch_size !== 1 || calculation.policy !== "independent_latent_desirability_beta_ei_v1") return false;
  } else if (![5, 6, 7].includes(calculation.schema_version) || calculation.policy !== "conditional_mc_desirability_beta_marginal_v1") return false;
  if ((calculation.schema_version === 7) !== (study.objective.curve_policy === "per_response_target_gaussian_or_ds_v1") || calculation.shared_model.curve_policy !== study.objective.curve_policy) return false;
  const responseIds = study.objective.responses.map(r => r.response_id), factorIds = study.factors.map(f => f.factor_id);
  if (!sameDesirabilityJson(calculation.objective.responses, study.objective.responses) ||
    !sameIds(calculation.shared_model.response_ids, responseIds) || !sameIds(calculation.shared_model.factor_ids, factorIds) ||
    !sameIds(calculation.shared_model.response_models.map(r => r.response_id), responseIds)) return false;
  if (request && (calculation.schema_version !== request.schema_version || calculation.batch_size !== request.batch_size ||
    calculation.observation_view.mode !== request.observation_policy.mode || calculation.shared_model.response_models.some(saved => {
      const requested = request.response_models.find(r => r.response_id === saved.response_id);
      return !requested || saved.model.signal_kernel.family !== requested.kernel.kind || saved.model.noise.mode !== requested.surrogate.noise_mode;
    }))) return false;
  if (request && request.schema_version !== 4 && (calculation.schema_version === 4 || !sameDesirabilityJson(calculation.batch_options, request.batch_options))) return false;
  if (calculation.schema_version === 6 && calculation.shared_model.response_models.some(({ model }) =>
    model.schema_version !== 5 || model.fit_diagnostics?.policy !== "bounded_multiscale_starts_v1" ||
    (request?.schema_version === 6 && model.fit_diagnostics.deterministic_start_count !== request.fit_policy.deterministic_start_count))) return false;
  if (calculation.schema_version === 7 && calculation.shared_model.response_models.some(({model}) => {
    if (model.schema_version !== 4 && model.schema_version !== 5) return true;
    if (model.schema_version === 5 && model.fit_diagnostics?.policy !== "bounded_multiscale_starts_v1") return true;
    if (request?.schema_version !== 7) return false;
    return request.fit_policy === null ? model.schema_version !== 4 : model.schema_version !== 5 || model.fit_diagnostics.deterministic_start_count !== request.fit_policy.deterministic_start_count;
  })) return false;
  return calculation.items.every((item, index) => {
    const numericalPolicy = item.acquisition.numerical_policy;
    if (numericalPolicy !== undefined && numericalPolicy !== "positive_beta_integral_v2") return false;
    if (numericalPolicy !== calculation.items[0].acquisition.numerical_policy) return false;
    if (item.rank !== index + 1 || !sameIds(Object.keys(item.actual_coordinates), factorIds) ||
      !sameIds(Object.keys(item.normalized_coordinates), factorIds) || !sameIds(item.response_predictions.map(r => r.response_id), responseIds) ||
      (request && item.acquisition.xi_desirability !== request.xi_desirability)) return false;
    if (calculation.schema_version !== 4) {
      const planning = calculation.items[index].planning;
      if (planning?.sampler.numerical_policy !== numericalPolicy) return false;
      if (!planning || planning.sampler.batch_step !== index ||
        planning.sampler.representative_prediction_source !== "completed_observations_base_posterior" ||
        !sameDesirabilityJson(planning.sampler.conditioned_on_selected_ranks, Array.from({ length: index }, (_, i) => i + 1))) return false;
    }
    return true;
  });
}
export function validDesirabilitySaved(batch: DesirabilityBatch, study: BayesianStudyResponse, requestedId: string | null): boolean {
  const tuple = batch.result_schema_version === 4
    ? batch.config_schema_version === 4 && batch.item_schema_version === 3 && batch.method_version === "0.9.0" && batch.batch_size === 1
    : batch.result_schema_version === 5 ? batch.config_schema_version === 5 && batch.item_schema_version === 4 && batch.method_version === "0.10.0"
    : batch.result_schema_version === 6 ? batch.config_schema_version === 6 && batch.item_schema_version === 4 && batch.method_version === "0.11.0"
    : batch.result_schema_version === 7 && batch.config_schema_version === 7 && batch.item_schema_version === 4 && batch.method_version === "0.12.0";
  if (!tuple || batch.model_schema_version !== (batch.result_schema_version >= 6 ? batch.result_schema_version : 5) || batch.study_id !== study.study_id || batch.study_version_id !== study.study_version_id ||
    batch.definition_sha256 !== study.definition_sha256 || (requestedId !== null && batch.batch_id !== requestedId) ||
    batch.calculation.schema_version !== batch.result_schema_version || batch.batch_size !== batch.calculation.batch_size ||
    batch.batch_policy !== batch.calculation.policy || batch.items.length !== batch.batch_size ||
    new Set(batch.items.map(item => item.trial.trial_id)).size !== batch.batch_size ||
    !validDesirabilityCalculation(batch.calculation, study)) return false;
  const firstNumber = batch.items[0].trial.trial_number;
  return batch.items.every((item, index) => item.rank === index + 1 && item.batch_id === batch.batch_id &&
    item.trial.study_version_id === study.study_version_id && item.trial.trial_number === firstNumber + index &&
    item.current_trial.trial_id === item.trial.trial_id && item.current_trial.study_version_id === study.study_version_id &&
    sameDesirabilityJson(item.trial.actual_coordinates, batch.calculation.items[index].actual_coordinates) &&
    sameDesirabilityJson(item.trial.normalized_coordinates, batch.calculation.items[index].normalized_coordinates) &&
    sameDesirabilityJson(item.current_trial.actual_coordinates, item.trial.actual_coordinates) &&
    sameDesirabilityJson(item.current_trial.normalized_coordinates, item.trial.normalized_coordinates));
}
