import type { BayesianDesirabilityObjective, BayesianLinearConstraintRequest } from "../../api/types/bayesian";
import type { MixedActualPoint, MixedCategoricalFactorResponse, MixedCorrelationPolicy, MixedEncodedPoint, MixedFactorRequest, MixedFactorResponse,
  MixedObservationBatchRequest, MixedObservationBatchResponse, MixedStudyCreateRequest, MixedStudyResponse } from "../../api/types/boMixed";
import { parseDoeResponseNumber } from "../../doe/doeResponsePaste";
import { isRsmOnLattice } from "../../doe/rsmRegion";
import { parsePastedTablePreview } from "../../pastedTablePreview";
import { planningHash, planningId, planningInteger } from "./boPlanningDraft";
import { vectorObservationEntries, type VectorObservationDraft } from "./bayesianVectorDraft";
import { sameDesirabilityJson } from "./desirabilityResponseGuard";

export interface MixedFactorDraft {
  key: number; factorId: string; name: string; unit: string; kind: "continuous" | "discrete_numeric" | "nominal" | "ordinal";
  low: string; high: string; step: string; decimals: string; levels: string[]; correlation: MixedCorrelationPolicy;
}
export interface MixedConstraintDraft { key: number; name: string; relation: "less_than_or_equal" | "greater_than_or_equal"; bound: string; coefficients: Record<string, string> }
export interface MixedStudyDraft { name: string; factors: MixedFactorDraft[]; constraints: MixedConstraintDraft[]; seed: string; size: string; objective: BayesianDesirabilityObjective }
export const isMixedCategory = (factor: MixedFactorResponse): factor is MixedCategoricalFactorResponse => factor.domain_kind === "nominal" || factor.domain_kind === "ordinal";
export function newMixedFactor(key: number, kind: MixedFactorDraft["kind"] = "continuous"): MixedFactorDraft {
  return { key, factorId: `factor_${key}`, name: `Factor ${key}`, unit: "", kind, low: "0", high: "1", step: "1", decimals: "", levels: ["A", "B"], correlation: "equal_positive_correlation_v1" };
}
export function buildMixedStudyRequest(draft: MixedStudyDraft): MixedStudyCreateRequest | string {
  const seed = planningInteger(draft.seed, 0, 2147483647), size = planningInteger(draft.size, Math.max(2, draft.factors.length + 1), 64);
  if (!draft.name.trim() || draft.name.trim().length > 120 || seed === null || size === null || draft.factors.length < 1 || draft.factors.length > 10) return "bayesian_mixed_study_input_invalid";
  const ids = new Set<string>(), factors: MixedFactorRequest[] = []; let categoryParameters = 0;
  for (const row of draft.factors) {
    if (!/^[A-Za-z][A-Za-z0-9_]{0,63}$/.test(row.factorId) || ids.has(row.factorId) || !row.name.trim() || row.name.trim().length > 80 || row.unit.trim().length > 40) return "bayesian_factor_domain_invalid";
    ids.add(row.factorId);
    const common = { factor_id: row.factorId, name: row.name.trim(), unit: row.unit.trim() || null };
    if (row.kind === "nominal" || row.kind === "ordinal") {
      if (row.levels.length < 2 || row.levels.length > 32 || row.levels.some(level => !level.trim() || level.length > 1024 || level.includes("\0")) || new Set(row.levels).size !== row.levels.length) return "bayesian_category_levels_invalid";
      if ((row.correlation === "ordinal_monotone_latent_rbf_v1" && row.kind !== "ordinal") || (row.correlation === "unequal_hyperspherical_correlation_v1" && row.levels.length > 8)) return "bayesian_category_correlation_policy_invalid";
      categoryParameters += row.correlation === "equal_positive_correlation_v1" ? 1 : row.correlation === "unequal_hyperspherical_correlation_v1" ? row.levels.length * (row.levels.length - 1) / 2 : row.levels.length - 1;
      factors.push({ ...common, domain_kind: row.kind, levels: [...row.levels], correlation_policy: row.correlation });
    } else {
      const low = parseDoeResponseNumber(row.low), high = parseDoeResponseNumber(row.high), step = row.kind === "discrete_numeric" ? parseDoeResponseNumber(row.step) : null;
      const decimals = row.decimals.trim() === "" ? null : planningInteger(row.decimals, 0, 12);
      if (low === null || high === null || low >= high || !Number.isFinite(high - low) || (row.decimals.trim() !== "" && decimals === null) ||
        (row.kind === "discrete_numeric" && (step === null || step <= 0 || !isRsmOnLattice(high, low, step)))) return "bayesian_factor_domain_invalid";
      factors.push({ ...common, domain_kind: row.kind, low, high, step, display_decimals: decimals });
    }
  }
  if (!factors.some(factor => factor.domain_kind === "nominal" || factor.domain_kind === "ordinal")) return "bayesian_mixed_factor_required";
  if (categoryParameters > 64) return "bayesian_category_parameter_budget_exceeded";
  if (draft.constraints.length > 16) return "bayesian_constraints_invalid";
  const constraints: BayesianLinearConstraintRequest[] = [];
  for (const row of draft.constraints) {
    const bound = parseDoeResponseNumber(row.bound), terms: BayesianLinearConstraintRequest["terms"] = [];
    if (!row.name.trim() || row.name.trim().length > 80 || bound === null) return "bayesian_constraints_invalid";
    for (const [id, raw] of Object.entries(row.coefficients)) {
      if (raw.trim() === "") continue;
      const factor = factors.find(item => item.factor_id === id), value = parseDoeResponseNumber(raw);
      if (!factor || factor.domain_kind === "nominal" || factor.domain_kind === "ordinal" || value === null) return "bayesian_constraints_invalid";
      if (value !== 0) terms.push({ factor_id: id, coefficient: value });
    }
    if (!terms.length) return "bayesian_constraints_invalid";
    constraints.push({ constraint_id: `constraint_${row.key}`, name: row.name.trim(), relation: row.relation, bound, terms });
  }
  return { schema_version: 7, name: draft.name.trim(), factors, constraints, objective: draft.objective, initial_design_seed: seed, initial_design_size: size,
    initial_design_policy: "sha256_counter_mixed_uniform_feasible_v1", predecessor_study_id: null };
}
export function mixedStudyKey(study: MixedStudyResponse): string {
  return JSON.stringify([study.study_id, study.study_version_id, study.definition_sha256, study.status, study.observation_history.history_revision_id,
    study.observation_history.observation_history_sha256, study.trials.map(row => [row.trial_id, row.state, row.coordinates_sha256])]);
}
export function validateMixedCoordinates(actual: MixedActualPoint, encoded: MixedEncodedPoint, factors: readonly MixedFactorResponse[]): boolean {
  return actual !== null && encoded !== null && typeof actual === "object" && typeof encoded === "object" && Object.keys(actual).length === factors.length && Object.keys(encoded).length === factors.length && factors.every(factor => {
    const value = actual[factor.factor_id], code = encoded[factor.factor_id];
    if (isMixedCategory(factor)) return typeof value === "string" && factor.levels.includes(value) && Number.isInteger(code) && factor.levels.indexOf(value) === code;
    if (typeof value !== "number" || !Number.isFinite(value) || value < factor.low || value > factor.high || !Number.isFinite(code) || code < 0 || code > 1 ||
      (factor.domain_kind === "discrete_numeric" && (factor.step == null || !isRsmOnLattice(value, factor.low, factor.step)))) return false;
    return Math.abs(code - (value - factor.low) / (factor.high - factor.low)) <= 32 * Number.EPSILON * Math.max(1, Math.abs(code));
  });
}
export function validMixedStudy(study: MixedStudyResponse, expectedId?: string): boolean {
  if (!study || study.study_schema_version !== 7 || !planningId(study.study_id) || (expectedId !== undefined && study.study_id !== expectedId) || !planningId(study.study_version_id) ||
    !planningHash(study.definition_sha256) || study.objective?.goal_type !== "desirability" || !Array.isArray(study.objective.responses) || study.objective.responses.length < 1 || study.objective.responses.length > 4 ||
    !planningId(study.observation_history?.history_revision_id) || !planningHash(study.observation_history?.observation_history_sha256) || study.observation_history.study_version_id !== study.study_version_id ||
    !Array.isArray(study.factors) || study.factors.length < 1 || study.factors.length > 10 || !study.factors.some(isMixedCategory) || new Set(study.factors.map(factor => factor.factor_id)).size !== study.factors.length ||
    !Array.isArray(study.trials) || study.trials.length !== study.trial_count || study.trial_count < 1 || study.trial_count > 200 || new Set(study.trials.map(row => row.trial_id)).size !== study.trial_count ||
    study.initial_design?.policy !== "sha256_counter_mixed_uniform_feasible_v1" || study.initial_design.coordinate_encoding !== "numeric_normalized_category_index_v1") return false;
  if (study.factors.some(factor => isMixedCategory(factor) ? factor.encoding_rule !== "declared_level_index_v1" || factor.levels.length < 2 || factor.levels.length > 32 ||
    new Set(factor.levels).size !== factor.levels.length || factor.levels.some(level => typeof level !== "string" || !level.trim()) :
    !Number.isFinite(factor.low) || !Number.isFinite(factor.high) || factor.low >= factor.high || !Number.isFinite(factor.high - factor.low))) return false;
  const responseIds = study.objective.responses.map(response => response.response_id);
  if (new Set(responseIds).size !== responseIds.length || study.pending_trial_count !== study.trials.filter(row => row.state === "pending").length ||
    study.completed_trial_count !== study.trials.filter(row => row.state === "completed").length || study.abandoned_trial_count !== study.trials.filter(row => row.state === "abandoned").length) return false;
  return study.trials.every(row => planningId(row.trial_id) && row.study_version_id === study.study_version_id && planningHash(row.coordinates_sha256) &&
    row.coordinate_encoding === "numeric_normalized_category_index_v1" && validateMixedCoordinates(row.actual_coordinates, row.encoded_coordinates, study.factors) && row.objective_value === null &&
    (row.state === "completed" ? row.response_values !== null && Object.keys(row.response_values).length === responseIds.length && responseIds.every(id => typeof row.response_values?.[id] === "number" && Number.isFinite(row.response_values[id])) : row.response_values === null));
}
export function parseMixedPoint(draft: Record<string, string>, factors: readonly MixedFactorResponse[]): MixedActualPoint | null {
  if (Object.keys(draft).length !== factors.length) return null;
  const point: MixedActualPoint = {};
  for (const factor of factors) {
    const raw = draft[factor.factor_id];
    if (typeof raw !== "string") return null;
    if (isMixedCategory(factor)) { if (!factor.levels.includes(raw)) return null; point[factor.factor_id] = raw; }
    else { const value = parseDoeResponseNumber(raw); if (value === null || value < factor.low || value > factor.high || (factor.domain_kind === "discrete_numeric" && (factor.step == null || !isRsmOnLattice(value, factor.low, factor.step)))) return null; point[factor.factor_id] = value; }
  }
  return point;
}
export function parseMixedCandidatePaste(content: string, factors: readonly MixedFactorResponse[], header: boolean): MixedActualPoint[] | null {
  if (!content.trim() || content.length > 2_000_000) return null;
  const parsed = parsePastedTablePreview(content, { maxRows: 10001, maxColumns: factors.length + 1, maxCells: 100010, maxScanCharacters: 2_000_000 });
  if (parsed.rawModeOnly || parsed.countsAreLowerBounds || parsed.truncatedRows || parsed.truncatedColumns || parsed.rows.some(row => row.length !== factors.length) ||
    (header && parsed.rows[0]?.some((name, index) => name !== factors[index].factor_id && name !== factors[index].name))) return null;
  const data = parsed.rows.slice(header ? 1 : 0), points: MixedActualPoint[] = [], seen = new Set<string>();
  if (data.length < 1 || data.length > 10000) return null;
  for (const row of data) { const point = parseMixedPoint(Object.fromEntries(factors.map((factor, index) => [factor.factor_id, row[index]])), factors);
    if (point === null) return null; const id = JSON.stringify(factors.map(factor => point[factor.factor_id])); if (seen.has(id)) return null; seen.add(id); points.push(point); }
  return points;
}
export function buildMixedObservations(study: MixedStudyResponse, draft: VectorObservationDraft, requestId: string): MixedObservationBatchRequest | string {
  const entries = vectorObservationEntries(study.trials.filter(row => row.state === "pending").map(row => row.trial_id), study.objective.responses.map(response => response.response_id), draft);
  if (typeof entries === "string" || study.status !== "active") return "bayesian_vector_observations_invalid";
  return { request_id: requestId, expected_study_version_id: study.study_version_id, expected_history_revision_id: study.observation_history.history_revision_id,
    expected_observation_history_sha256: study.observation_history.observation_history_sha256, observations: entries };
}
export function validMixedObservationCommit(value: MixedObservationBatchResponse, source: MixedStudyResponse, request: MixedObservationBatchRequest): boolean {
  return value?.batch_schema_version === 2 && value.request_id === request.request_id && validMixedStudy(value.study, source.study_id) &&
    value.study.study_version_id === source.study_version_id && value.study.definition_sha256 === source.definition_sha256 && value.completed_trial_count === request.observations.length &&
    value.completed_trial_ids.length === request.observations.length && new Set(value.completed_trial_ids).size === request.observations.length &&
    request.observations.every(row => value.completed_trial_ids.includes(row.trial_id) && value.study.trials.some(trial => trial.trial_id === row.trial_id && trial.state === "completed" && sameDesirabilityJson(trial.response_values, row.response_values))) &&
    sameDesirabilityJson(value.observation_history, value.study.observation_history);
}
