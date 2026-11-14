import { evaluatePlanningModel } from "../../api/boPlanning";
import { evaluateMixedModel } from "../../api/boMixed";
import type { PlanningModelDetail } from "../../api/types/boPlanning";
import type { MixedActualPoint, MixedModelDetail, MixedStudyResponse } from "../../api/types/boMixed";
import { validPlanningEvaluation } from "./boPlanningDraft";
import { validMixedPrediction } from "./boMixedPlanningDraft";
import { sameDesirabilityJson } from "./desirabilityResponseGuard";

export async function numericMatrixChunk(studyId: string, model: PlanningModelDetail, points: Record<string, number>[], time_budget_ms: number) {
  const response = await evaluatePlanningModel(studyId, model.model_id, { expected_model_sha256: model.snapshot_sha256, points, time_budget_ms });
  if (!validPlanningEvaluation(response, model, points) || response.items.some(row => typeof row.constraints_satisfied !== "boolean" || row.prediction_source !== "completed_observations_base_posterior")) throw Error("bayesian_profile_response_mismatch");
  return response.items;
}
export async function mixedMatrixChunk(study: MixedStudyResponse, model: MixedModelDetail, points: MixedActualPoint[], time_budget_ms: number) {
  const response = await evaluateMixedModel(study.study_id, model.model_id, { expected_model_sha256: model.snapshot_sha256, points, time_budget_ms, max_moment_evaluations: 65536 });
  if (response.model_id !== model.model_id || response.snapshot_sha256 !== model.snapshot_sha256 || response.model_refit !== false || response.items.length !== points.length || new Set(response.items.map(row => row.row_id)).size !== points.length || response.items.some((row, index) => !validMixedPrediction(row, study) || !sameDesirabilityJson(row.input_coordinates, points[index]))) throw Error("bayesian_profile_response_mismatch");
  return response.items;
}
