import type { BayesianFactorResponse, BayesianStudyResponse } from "../../api/types/bayesian";
import type { CandidatePage, CandidateRow, PlanningBatchResponse, PlanningEvaluationResponse, PlanningModelDetail, PlanningSelectionResponse } from "../../api/types/boPlanning";
import type { ReportSourceDescriptor } from "../../api/types/reports";
import { parseDoeResponseNumber } from "../../doe/doeResponsePaste";
import { decimalLatticeValue, isRsmOnLattice } from "../../doe/rsmRegion";
import { parsePastedTablePreview } from "../../pastedTablePreview";
import { createLatestRequestGuard } from "../../latestRequest";
import { isReportSourceDescriptor } from "../../managedReportSource";
import { sameDesirabilityJson } from "./desirabilityResponseGuard";

export const planningHash = (value: unknown): value is string => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
export const planningId = (value: unknown): value is string => typeof value === "string" && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(value);
export function createPlanningRequestFence() {
  let source = "";
  const guard = createLatestRequestGuard();
  return {
    source(key: string) { if (key !== source) { source = key; guard.cancel(); } },
    invalidate() { guard.cancel(); },
    begin() { return guard.begin(); },
    current(token: symbol) { return guard.isCurrent(token); },
  };
}
export function createPlanningCommitFence() {
  let owner = "", pending: symbol | null = null;
  const guard = createLatestRequestGuard();
  return {
    source(key: string) { if (key !== owner) { owner = key; pending = null; guard.cancel(); } },
    begin() { if (pending !== null) return null; pending = guard.begin(); return pending; },
    current(token: symbol) { return pending === token && guard.isCurrent(token); },
    pending() { return pending !== null; },
    finish(token: symbol) { if (pending === token && guard.isCurrent(token)) { pending = null; guard.cancel(); } },
    cancel() { pending = null; guard.cancel(); },
  };
}
export const planningStudyKey = (study: BayesianStudyResponse) => JSON.stringify([
  study.study_id, study.study_version_id, study.definition_sha256, study.status,
  study.observation_history.history_revision_id, study.observation_history.observation_history_sha256,
  study.trials.map(row => [row.trial_id, row.state, row.coordinates_sha256]),
]);
export function planningInteger(raw: string, minimum: number, maximum: number): number | null {
  if (!/^\d+$/.test(raw.trim())) return null;
  const value = Number(raw.trim());
  return Number.isSafeInteger(value) && value >= minimum && value <= maximum ? value : null;
}
function executable(value: number, factor: BayesianFactorResponse): boolean {
  if (!Number.isFinite(value) || value < factor.low || value > factor.high) return false;
  if (factor.domain_kind !== "discrete_numeric") return true;
  if (factor.step == null || !Number.isFinite(factor.step) || factor.step <= 0) return false;
  return isRsmOnLattice(value, factor.low, factor.step);
}
export function parsePlanningPoint(draft: Record<string, string>, factors: readonly BayesianFactorResponse[]): Record<string, number> | null {
  if (Object.keys(draft).length !== factors.length) return null;
  const result: Record<string, number> = {};
  for (const factor of factors) {
    const value = typeof draft[factor.factor_id] === "string" ? parseDoeResponseNumber(draft[factor.factor_id]) : null;
    if (value === null || !executable(value, factor)) return null;
    result[factor.factor_id] = value;
  }
  return result;
}
export function parsePlanningPaste(content: string, factors: readonly BayesianFactorResponse[], hasHeader: boolean):
  { points: Record<string, number>[]; error: null } | { points: null; error: "empty" | "limit" | "shape" | "header" | "number" | "duplicate" } {
  if (!content.trim()) return { points: null, error: "empty" };
  if (content.length > 2_000_000 || factors.length < 1 || factors.length > 10) return { points: null, error: "limit" };
  const parsed = parsePastedTablePreview(content, { maxRows: 10001, maxColumns: factors.length + 1, maxCells: 100010, maxScanCharacters: 2_000_000 });
  if (parsed.rawModeOnly || parsed.countsAreLowerBounds || parsed.truncatedRows || parsed.truncatedColumns || parsed.rows.some(row => row.length !== factors.length)) return { points: null, error: "shape" };
  if (hasHeader && parsed.rows[0]?.some((value, i) => value.trim() !== factors[i].factor_id && value.trim() !== factors[i].name)) return { points: null, error: "header" };
  const data = parsed.rows.slice(hasHeader ? 1 : 0);
  if (data.length < 1 || data.length > 10000) return { points: null, error: "limit" };
  const points: Record<string, number>[] = [], seen = new Set<string>();
  for (const row of data) {
    const point = parsePlanningPoint(Object.fromEntries(factors.map((f, i) => [f.factor_id, row[i]])), factors);
    if (!point) return { points: null, error: "number" };
    const identity = JSON.stringify(factors.map(f => point[f.factor_id]));
    if (seen.has(identity)) return { points: null, error: "duplicate" };
    seen.add(identity); points.push(point);
  }
  return { points, error: null };
}
export interface OrderedPlanningRows { past: CandidateRow[][]; current: CandidateRow[]; future: CandidateRow[][] }
export const emptyPlanningOrder = (): OrderedPlanningRows => ({ past: [], current: [], future: [] });
export function updatePlanningOrder(state: OrderedPlanningRows, next: CandidateRow[]): OrderedPlanningRows {
  if (next.length > 8 || new Set(next.map(row => row.row_id)).size !== next.length || next.some(row => !row.eligible)) return state;
  if (state.current.map(r => r.row_id).join() === next.map(r => r.row_id).join()) return state;
  return { past: [...state.past.slice(-31), state.current], current: [...next], future: [] };
}
export function undoPlanningOrder(state: OrderedPlanningRows): OrderedPlanningRows {
  if (!state.past.length) return state;
  return { past: state.past.slice(0, -1), current: state.past[state.past.length - 1], future: [state.current, ...state.future] };
}
export function redoPlanningOrder(state: OrderedPlanningRows): OrderedPlanningRows {
  if (!state.future.length) return state;
  return { past: [...state.past, state.current], current: state.future[0], future: state.future.slice(1) };
}
export function planningProfilePoints(draft: Record<string, string>, factors: readonly BayesianFactorResponse[], axisId: string): Record<string, number>[] | null {
  const held = parsePlanningPoint(draft, factors), axis = factors.find(f => f.factor_id === axisId);
  if (!held || !axis) return null;
  let values: number[];
  if (axis.domain_kind === "discrete_numeric") {
    if (axis.step == null) return null;
    const count = Math.round((axis.high - axis.low) / axis.step) + 1;
    if (count > 100 || count < 2) return null;
    values = Array.from({ length: count }, (_, i) => decimalLatticeValue(axis.low, axis.step!, i) ?? NaN);
  } else {
    values = Array.from({ length: 21 }, (_, i) => axis.low + (axis.high - axis.low) * (i / 20));
    values[0] = axis.low; values[values.length - 1] = axis.high;
  }
  if (values.some(v => !Number.isFinite(v)) || new Set(values).size !== values.length) return null;
  return values.map(value => ({ ...held, [axisId]: value }));
}
export function validPlanningModel(value: PlanningModelDetail, study: BayesianStudyResponse): boolean {
  return value.schema_version === 1 && value.study_id === study.study_id && value.study_version_id === study.study_version_id &&
    value.definition_sha256 === study.definition_sha256 && planningId(value.model_id) && planningHash(value.snapshot_sha256) &&
    planningHash(value.history_sha256) && planningId(value.source_history_revision_id) && value.model_reusable_without_refit === true &&
    [5, 6, 7].includes(value.fit.schema_version) && value.fit.expected_history_revision_id === value.source_history_revision_id && value.fit.expected_history_sha256 === value.history_sha256;
}
export function currentPlanningModel(value: PlanningModelDetail, study: BayesianStudyResponse): boolean {
  return validPlanningModel(value, study) && value.source_is_current && value.source_history_revision_id === study.observation_history.history_revision_id && value.history_sha256 === study.observation_history.observation_history_sha256;
}
export function validPlanningPage(value: CandidatePage, model: PlanningModelDetail, factors: readonly BayesianFactorResponse[]): boolean {
  return value.revision.schema_version === 1 && planningId(value.revision.revision_id) && planningHash(value.revision.rows_sha256) &&
    value.revision.model_id === model.model_id && value.revision.model_sha256 === model.snapshot_sha256 && Number.isInteger(value.offset) && value.offset >= 0 &&
    Number.isInteger(value.revision.row_count) && value.revision.row_count >= 1 && value.revision.row_count <= 10000 && value.offset <= value.revision.row_count &&
    Number.isInteger(value.limit) && value.limit >= 1 && value.limit <= 100 && value.items.length <= value.limit &&
    value.items.length === Math.min(value.limit, value.revision.row_count - value.offset) &&
    new Set(value.items.map(row => row.row_id)).size === value.items.length && value.items.every(row => planningHash(row.row_id) &&
      row.eligible === (row.novel && row.constraints_satisfied) && parsePlanningPoint(Object.fromEntries(Object.entries(row.actual_coordinates).map(([key, v]) => [key, String(v)])), factors) !== null);
}
export function validPlanningEvaluation(value: PlanningEvaluationResponse, model: PlanningModelDetail, points: Record<string, number>[]): boolean {
  return value.schema_version === 1 && value.model_id === model.model_id && value.model_sha256 === model.snapshot_sha256 && value.model_refit === false &&
    planningHash(value.request_sha256) && planningHash(value.eligibility_coordinates_sha256) && value.items.length === points.length &&
    new Set(value.items.map(row => row.row_id)).size === value.items.length && value.items.every((row, i) => planningHash(row.row_id) &&
      Object.keys(row.input_coordinates).length === Object.keys(points[i]).length && Object.keys(row.actual_coordinates).length === Object.keys(points[i]).length &&
      Object.entries(points[i]).every(([key, v]) => row.input_coordinates[key] === v && Number.isFinite(row.actual_coordinates[key]) && Math.abs(row.actual_coordinates[key] - v) <= 8 * Number.EPSILON * Math.max(1, Math.abs(v))) &&
      Number.isFinite(row.desirability_moments.mean) && row.desirability_moments.mean >= 0 && row.desirability_moments.mean <= 1 &&
      Number.isFinite(row.desirability_moments.variance) && row.desirability_moments.variance >= 0 && row.desirability_moments.variance <= .25 &&
      Number.isFinite(row.acquisition.value) && row.acquisition.value >= 0 && row.acquisition.value <= 1 &&
      row.response_predictions.length === model.objective.responses.length && new Set(row.response_predictions.map(p => p.response_id)).size === model.objective.responses.length &&
      model.objective.responses.every(expected => row.response_predictions.some(p => p.response_id === expected.response_id)) &&
      row.response_predictions.every(p => [p.mean_raw, p.latent_standard_deviation_raw, p.predictive_standard_deviation_raw].every(Number.isFinite) && p.latent_standard_deviation_raw >= 0 && p.predictive_standard_deviation_raw >= p.latent_standard_deviation_raw));
}
export function validPlanningSelection(value: PlanningSelectionResponse, model: PlanningModelDetail, revisionId: string, rowsHash: string, rowIds: readonly string[]): boolean {
  return value.schema_version === 1 && planningId(value.selection_id) && value.study_id === model.study_id && value.study_version_id === model.study_version_id &&
    value.model_id === model.model_id && value.model_sha256 === model.snapshot_sha256 && value.candidate_revision_id === revisionId && value.rows_sha256 === rowsHash &&
    planningHash(value.config_sha256) && planningHash(value.result_sha256) && value.calculation.schema_version === 1 && value.calculation.model_refit === false &&
    value.calculation.selection_policy === "manual_ordered_fixed_model_v1" && value.request.row_ids.join() === rowIds.join() &&
    value.calculation.items.length === rowIds.length && value.calculation.items.every((item, i) => item.rank === i + 1 && item.row_id === rowIds[i] && item.eligible &&
      Number.isFinite(item.planning.score) && item.planning.score >= 0 && item.planning.score <= 1 && Number.isFinite(item.desirability_moments.mean) &&
      item.desirability_moments.mean >= 0 && item.desirability_moments.mean <= 1 && Number.isFinite(item.acquisition.value) && item.acquisition.value >= 0 && item.acquisition.value <= 1);
}
export function validPlanningBatch(value: PlanningBatchResponse, study: BayesianStudyResponse, batchId: string): boolean {
  if (!value || value.result_schema_version !== 8 || value.config_schema_version !== 8 || value.model_schema_version !== 8 || value.item_schema_version !== 4 ||
    value.method_version !== "0.13.0" || value.batch_policy !== "manual_ordered_fixed_model_v1" || value.batch_id !== batchId || !planningId(batchId) ||
    value.study_id !== study.study_id || value.study_version_id !== study.study_version_id || value.definition_sha256 !== study.definition_sha256 ||
    study.objective.goal_type !== "desirability" || !sameDesirabilityJson(value.objective.responses, study.objective.responses) ||
    !planningId(value.source_history_revision_id) || !planningHash(value.source_observation_history_sha256) || !planningHash(value.config_sha256) || !planningHash(value.result_sha256) ||
    !value.source || value.source.selection_id !== batchId || !planningId(value.source.model_id) || !planningId(value.source.candidate_revision_id) ||
    ![value.source.model_sha256, value.source.rows_sha256, value.source.selection_config_sha256, value.source.selection_result_sha256].every(planningHash) ||
    !Number.isInteger(value.batch_size) || value.batch_size < 1 || value.batch_size > 8 || !Array.isArray(value.items) || value.items.length !== value.batch_size ||
    value.calculation?.schema_version !== 1 || value.calculation.selection_policy !== "manual_ordered_fixed_model_v1" || value.calculation.model_refit !== false ||
    !Array.isArray(value.calculation.items) || value.calculation.items.length !== value.batch_size ||
    !Array.isArray(value.warnings) || value.warnings.some(code => typeof code !== "string")) return false;
  const rows = value.calculation.items, responses = study.objective.responses;
  if (new Set(rows.map(row => row.row_id)).size !== rows.length || new Set(value.items.map(item => item.trial.trial_id)).size !== rows.length) return false;
  return rows.every((row, index) => {
    const item = value.items[index];
    return row.rank === index + 1 && planningHash(row.row_id) && row.eligible && item.rank === index + 1 && item.batch_id === batchId && planningId(item.item_id) &&
      planningId(item.trial.trial_id) && item.current_trial.trial_id === item.trial.trial_id &&
      sameDesirabilityJson(item.trial.actual_coordinates, row.actual_coordinates) && sameDesirabilityJson(item.current_trial.actual_coordinates, row.actual_coordinates) &&
      parsePlanningPoint(Object.fromEntries(Object.entries(row.actual_coordinates).map(([key, value]) => [key, String(value)])), study.factors) !== null &&
      [row.desirability_moments.mean, row.acquisition.value, row.planning.score].every(number => Number.isFinite(number) && number >= 0 && number <= 1) &&
      Number.isFinite(row.desirability_moments.variance) && row.desirability_moments.variance >= 0 && row.desirability_moments.variance <= .25 &&
      row.response_predictions.length === responses.length && new Set(row.response_predictions.map(prediction => prediction.response_id)).size === responses.length && row.response_predictions.every(prediction =>
        responses.some(response => response.response_id === prediction.response_id) &&
        [prediction.mean_raw, prediction.latent_standard_deviation_raw, prediction.predictive_standard_deviation_raw].every(Number.isFinite) &&
        prediction.latent_standard_deviation_raw >= 0 && prediction.predictive_standard_deviation_raw >= prediction.latent_standard_deviation_raw);
  });
}
export function validPlanningBatchReportSource(descriptor: ReportSourceDescriptor, batch: PlanningBatchResponse): boolean {
  if (!isReportSourceDescriptor(descriptor) || descriptor.source.kind !== "bayesian_history_revision") return false;
  const source = descriptor.source;
  return source.study_id === batch.study_id && source.study_version_id === batch.study_version_id && source.definition_sha256 === batch.definition_sha256 &&
    source.history_revision_id === batch.source_history_revision_id && source.expected_source_sha256 === batch.source_observation_history_sha256 &&
    source.attachment.kind === "batch" && source.attachment.batch_id === batch.batch_id && source.attachment.result_payload_sha256 === batch.result_sha256;
}
export type PlanningProfileMetric = "mean_raw" | "latent_standard_deviation_raw" | "predictive_standard_deviation_raw";
export function planningResponseProfilePoints(response: PlanningEvaluationResponse, axisId: string, responseId: string, metric: PlanningProfileMetric): Array<{ rowId: string; x: number; value: number }> {
  return response.items.map(row => {
    const prediction = row.response_predictions.find(item => item.response_id === responseId);
    if (!prediction || !Number.isFinite(prediction[metric]) || !Number.isFinite(row.actual_coordinates[axisId])) throw new Error("bayesian_planning_response_mismatch");
    return { rowId: row.row_id, x: row.actual_coordinates[axisId], value: prediction[metric] };
  });
}
