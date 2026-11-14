import type { BoLooView } from "../../api/boLoo";
import type { BoSavedView, BoViewEvaluationRequest, BoViewPayload, BoViewReceipt } from "../../api/boViews";
import type { ProfileMatrixView } from "./boProfileMatrix";
import { sameDesirabilityJson } from "./desirabilityResponseGuard";

export interface BoViewExpected { studyId: string; modelId: string; modelHash: string; historyHash: string; responseIds: string[]; factorIds: string[] }
const digest = (value: unknown) => typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
export function validBoViewPayload(payload: BoViewPayload, expected: BoViewExpected): boolean {
  const source = payload?.source;
  if (!source || ![1, 2].includes(payload.schema_version) || payload.model_refit !== false || source.study_id !== expected.studyId || source.model_id !== expected.modelId || source.model_sha256 !== expected.modelHash || source.history_sha256 !== expected.historyHash || !digest(source.model_config_sha256) || !digest(source.definition_sha256)
    || !sameDesirabilityJson(payload.responses.map(row => row.response_id), expected.responseIds)) return false;
  if (payload.kind === "conditional_loo") return digest(payload.calculation_sha256) && payload.calculation?.model_refit === false && payload.calculation.policy === "fixed_full_fit_parameters_row_loo_v1" && sameDesirabilityJson(payload.calculation.responses.map(row => row.response_id), expected.responseIds)
    && payload.calculation.responses.every(row => row.points.length === row.n_scored && row.points.every(point => [point.observed, point.predicted, point.residual].every(Number.isFinite)));
  if (payload.kind !== "profiler_matrix") return false;
  const mixture = payload.policy === "source_locked_mixture_profiler_matrix_v1";
  if (mixture !== (payload.schema_version === 2) || mixture !== !!payload.mixture_domain || (!mixture && payload.policy !== "source_locked_conditional_profiler_matrix_v1") || !sameDesirabilityJson(payload.axes.map(axis => axis.factor_id), expected.factorIds) || payload.point_count !== payload.axes.reduce((total, axis) => total + axis.points.length, 0) || payload.point_count > 1000) return false;
  return payload.axes.every(axis => (mixture ? !!axis.path && Boolean(axis.points.length) !== Boolean(axis.path.unavailable_reason) && ["excess_above_lower", "deficit_below_upper", "held_mixture_process_axis_v1"].includes(axis.path.policy) : !axis.path && axis.kind !== "mixture_component" && axis.points.length >= 2) && axis.points.length <= 100 && new Set(axis.points.map(row => row.row_id)).size === axis.points.length
    && (!["nominal", "ordinal"].includes(axis.kind) || axis.available_level_count === axis.points.length)
    && axis.points.every(row => row.prediction_source === "completed_observations_base_posterior" && typeof row.constraints_satisfied === "boolean" && sameDesirabilityJson(Object.keys(row.actual_coordinates).sort(), [...expected.factorIds].sort())
      && sameDesirabilityJson(row.response_predictions.map(value => value.response_id), expected.responseIds) && Number.isFinite(row.desirability_moments.mean)
      && row.response_predictions.every(value => [value.mean_raw, value.latent_standard_deviation_raw, value.predictive_standard_deviation_raw].every(Number.isFinite) && value.latent_standard_deviation_raw >= 0 && value.predictive_standard_deviation_raw >= value.latent_standard_deviation_raw)));
}
export function validBoViewReceipt(receipt: BoViewReceipt, expected: BoViewExpected, request: BoViewEvaluationRequest): boolean {
  return typeof receipt?.receipt_id === "string" && digest(receipt.request_sha256) && digest(receipt.view_sha256) && validBoViewPayload(receipt.payload, expected) && request.kind === receipt.payload.kind
    && (request.kind !== "profiler_matrix" || receipt.payload.kind === "profiler_matrix" && sameDesirabilityJson(request.holds, receipt.payload.holds));
}
export function validSavedView(view: BoSavedView, studyId: string): boolean {
  return view.schema_version === 1 && view.source.study_id === studyId && view.kind === view.payload.kind && sameDesirabilityJson(view.source, view.payload.source) && digest(view.request_sha256) && digest(view.view_sha256)
    && validBoViewPayload(view.payload, { studyId, modelId: view.source.model_id, modelHash: view.source.model_sha256, historyHash: view.source.history_sha256, responseIds: view.payload.responses.map(row => row.response_id), factorIds: view.payload.kind === "profiler_matrix" ? view.payload.axes.map(axis => axis.factor_id) : [] });
}
export function matrixFromPayload(payload: BoViewPayload): ProfileMatrixView {
  if (payload.kind !== "profiler_matrix") throw Error("bayesian_view_kind_invalid");
  return { modelId: payload.source.model_id, modelHash: payload.source.model_sha256, historyHash: payload.source.history_sha256, holds: payload.holds, responses: payload.responses,
    axes: payload.axes.map(axis => ({ factor_id: axis.factor_id, name: axis.name, unit: axis.unit, category: axis.kind === "nominal" || axis.kind === "ordinal", rows: axis.points,
      pathPolicy: axis.path?.policy, unavailableReason: axis.path?.unavailable_reason ?? undefined,
      ...(axis.path?.feasible_interval ? { range: { min: axis.path.feasible_interval[0], max: axis.path.feasible_interval[1] } } : {}) })) };
}
export function matrixFromReceipt(receipt: BoViewReceipt): ProfileMatrixView { return matrixFromPayload(receipt.payload); }
export function looFromPayload(payload: BoViewPayload, current = false): BoLooView {
  if (payload.kind !== "conditional_loo") throw Error("bayesian_view_kind_invalid");
  return { schema_version: 1, study_id: payload.source.study_id, model_id: payload.source.model_id, model_sha256: payload.source.model_sha256, config_sha256: payload.source.model_config_sha256,
    source_history_revision_id: payload.source.history_revision_id, history_sha256: payload.source.history_sha256, source_is_current: current, calculation_sha256: payload.calculation_sha256, calculation: payload.calculation };
}
