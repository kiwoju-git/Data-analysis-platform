import type { BayesianDesirabilityObjective, BayesianDesirabilityResponseGoal, BayesianStudyResponse } from "../../api";
import { parseDoeResponseNumber } from "../../doe/doeResponsePaste";

export interface ResponseGoalDraft {
  key: number;
  responseId: string;
  name: string;
  unit: string;
  goal: BayesianDesirabilityResponseGoal["goal"];
  lower: string;
  target: string;
  upper: string;
  importance: string;
  curve?: "linear" | "gaussian_target";
  lowerDesirability?: string;
  upperDesirability?: string;
}

export function newResponseDraft(key: number): ResponseGoalDraft {
  return { key, responseId: `response_${key}`, name: `Response ${key}`, unit: "",
    goal: "maximize", lower: "", target: "", upper: "", importance: "1",
    curve: "linear", lowerDesirability: "0.0183", upperDesirability: "0.0183" };
}

export function buildVectorObjective(name: string, drafts: readonly ResponseGoalDraft[]): BayesianDesirabilityObjective | string {
  if (!name.trim() || name.trim().length > 80 || drafts.length < 1 || drafts.length > 4) return "bayesian_vector_goals_invalid";
  const responses: BayesianDesirabilityResponseGoal[] = [];
  const ids = new Set<string>();
  for (const draft of drafts) {
    const responseId = draft.responseId.trim();
    const target = parseDoeResponseNumber(draft.target);
    const importance = parseDoeResponseNumber(draft.importance);
    const lower = draft.goal === "minimize" ? null : parseDoeResponseNumber(draft.lower);
    const upper = draft.goal === "maximize" ? null : parseDoeResponseNumber(draft.upper);
    if (!/^[A-Za-z][A-Za-z0-9_]{0,63}$/.test(responseId) || ids.has(responseId) ||
      !draft.name.trim() || draft.name.trim().length > 80 || draft.unit.trim().length > 40 ||
      target === null || importance === null || importance <= 0 ||
      (draft.goal !== "minimize" && (lower === null || lower >= target || !Number.isFinite(target - lower))) ||
      (draft.goal !== "maximize" && (upper === null || target >= upper || !Number.isFinite(upper - target)))) return "bayesian_vector_goals_invalid";
    ids.add(responseId);
    responses.push({ response_id: responseId, name: draft.name.trim(), unit: draft.unit.trim() || null,
      goal: draft.goal, lower, target, upper, importance });
    if (draft.goal === "match_target" && draft.curve === "gaussian_target") {
      const left = parseDoeResponseNumber(draft.lowerDesirability ?? "");
      const right = parseDoeResponseNumber(draft.upperDesirability ?? "");
      if (left === null || right === null || left <= 0 || left >= 1 || right <= 0 || right >= 1) return "bayesian_vector_goals_invalid";
      responses[responses.length - 1].curve = { policy: "two_sided_gaussian_target_peak_one_v1", lower_desirability: left, upper_desirability: right };
    }
  }
  // The server also rejects weights that cannot be represented after normalization.
  const largest = Math.max(...responses.map(r => r.importance));
  const weightSum = responses.reduce((sum, r) => sum + r.importance / largest, 0);
  if (responses.some(r => (r.importance / largest) / weightSum === 0)) return "bayesian_vector_goals_invalid";
  return { name: name.trim(), goal_type: "desirability", curve_policy: responses.some(r => r.curve) ? "per_response_target_gaussian_or_ds_v1" : "derringer_suich_linear_v1",
    observation_policy: "complete_response_vector", responses,
    unit: null, direction: null, target_value: null, target_tolerance: null };
}

export type VectorObservationDraft = Record<string, Record<string, string>>;
export function vectorDraftCell(draft: VectorObservationDraft, trialId: string, responseId: string): string {
  if (!Object.prototype.hasOwnProperty.call(draft, trialId)) return "";
  const row = draft[trialId];
  return Object.prototype.hasOwnProperty.call(row, responseId) && typeof row[responseId] === "string" ? row[responseId] : "";
}
export function vectorObservationEntries(pendingIds: readonly string[], responseIds: readonly string[], draft: VectorObservationDraft) {
  const entries: { trial_id: string; response_values: Record<string, number> }[] = [];
  for (const [trialId, values] of Object.entries(draft)) {
    if (!pendingIds.includes(trialId) || Object.keys(values).some(id => !responseIds.includes(id))) return "bayesian_vector_observations_invalid";
    if (Object.values(values).every(value => value.trim() === "")) continue;
    const parsed: [string, number][] = [];
    for (const id of responseIds) {
      const value = parseDoeResponseNumber(vectorDraftCell(draft, trialId, id));
      if (value === null) return "bayesian_vector_observations_invalid";
      parsed.push([id, value]);
    }
    entries.push({ trial_id: trialId, response_values: Object.fromEntries(parsed) });
  }
  return entries.length ? entries : "bayesian_vector_observations_invalid";
}

export function vectorStudySourceKey(study: BayesianStudyResponse) {
  return [study.study_id, study.study_version_id, study.definition_sha256, study.status,
    study.observation_history.history_revision_id, study.observation_history.observation_history_sha256].join(":");
}
