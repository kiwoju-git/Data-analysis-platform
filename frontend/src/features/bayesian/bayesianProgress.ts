import type { BayesianDesirabilityObjective, BayesianDesirabilityResponseGoal } from "../../api/types/bayesian";
import type { AnyBayesianStudyResponse } from "../../api/types/boMixed";

export interface ProgressRow {
  trialId: string; trialNumber: number; origin: string; value: number; best: number; distance: number | null;
}
export interface BayesianProgress {
  rows: ProgressRow[]; desirability: ProgressRow[] | null;
  name: string; unit: string | null; goal: string; target: number | null;
  invalidTrialCount: number; invalidDesirabilityCount: number; reason: string | null;
}
const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);

export function factorProgressSourceKey(study: AnyBayesianStudyResponse): string {
  // Completed-history hashes deliberately exclude pending and abandoned trials.
  return JSON.stringify([study.study_id, study.study_version_id, study.definition_sha256,
    study.observation_history.observation_history_sha256,
    [...study.trials].sort((a, b) => a.trial_number - b.trial_number).map(trial => [trial.trial_id, trial.state])]);
}

function fraction(value: number, low: number, high: number) {
  const delta = value - low, width = high - low;
  if (Number.isFinite(delta) && Number.isFinite(width)) return delta / width;
  const scale = Math.max(Math.abs(value), Math.abs(low), Math.abs(high), 1);
  return (value / scale - low / scale) / (high / scale - low / scale);
}

function goalLog(value: number, goal: BayesianDesirabilityResponseGoal, weight: number): number | null {
  if (!finite(value) || !finite(goal.target)) return null;
  const { lower, target, upper, curve } = goal;
  if (goal.goal !== "minimize" && (!finite(lower) || lower >= target || !finite(target - lower))) return null;
  if (goal.goal !== "maximize" && (!finite(upper) || upper <= target || !finite(upper - target))) return null;
  if (curve) {
    if (curve.policy !== "two_sided_gaussian_target_peak_one_v1" || goal.goal !== "match_target" ||
      !finite(curve.lower_desirability) || !finite(curve.upper_desirability) ||
      curve.lower_desirability <= 0 || curve.lower_desirability >= 1 || curve.upper_desirability <= 0 || curve.upper_desirability >= 1) return null;
    const ratio = value <= target ? fraction(value, target, lower!) : fraction(value, target, upper!);
    const rate = weight * Math.log(value <= target ? curve.lower_desirability : curve.upper_desirability);
    if (rate === 0) return null;
    const result = (rate * ratio) * ratio;
    return finite(result) ? result : null;
  }
  let score: number;
  if (goal.goal === "maximize") score = value <= lower! ? 0 : value >= target ? 1 : fraction(value, lower!, target);
  else if (goal.goal === "minimize") score = value <= target ? 1 : value >= upper! ? 0 : fraction(value, upper!, target);
  else if (goal.goal === "match_target") score = value <= lower! || value >= upper! ? 0 : value <= target
    ? fraction(value, lower!, target) : fraction(value, upper!, target);
  else return null;
  return finite(score) && score >= 0 && score <= 1 ? weight * Math.log(score) : null;
}

// Display projection of the stored goal policy, never a GP prediction or training response.
export function observedDesirability(objective: BayesianDesirabilityObjective, values: Record<string, number>): number | null {
  if (!["derringer_suich_linear_v1", "per_response_target_gaussian_or_ds_v1"].includes(objective.curve_policy)) return null;
  const goals = objective.responses;
  if (!goals.length || new Set(goals.map(goal => goal.response_id)).size !== goals.length ||
    Object.keys(values).length !== goals.length || goals.some(goal => !finite(goal.importance) || goal.importance <= 0 ||
      !finite(values[goal.response_id]) || (goal.curve && objective.curve_policy === "derringer_suich_linear_v1"))) return null;
  const maxWeight = Math.max(...goals.map(goal => goal.importance));
  const total = goals.reduce((sum, goal) => sum + goal.importance / maxWeight, 0);
  if (goals.some(goal => goal.importance / maxWeight / total <= 0)) return null;
  const logs = goals.map(goal => goalLog(values[goal.response_id], goal, goal.importance / maxWeight / total));
  if (logs.some(value => value === null)) return null;
  if (logs.includes(-Infinity)) return 0;
  const value = Math.exp(logs.reduce<number>((sum, log) => sum + log!, 0));
  return finite(value) && value > 0 && value <= 1 ? value : null;
}

export function categoryDisplayTicks(ticks: { value: number; label: string }[] | undefined) {
  if (!ticks || (ticks.length <= 6 && ticks.every(tick => Array.from(tick.label).length <= 6))) return ticks;
  const count = Math.min(8, ticks.length);
  return Array.from({ length: count }, (_, index) => ticks[Math.round(index * (ticks.length - 1) / (count - 1 || 1))])
    .map(tick => ({ value: tick.value, label: `#${tick.value + 1}` }));
}

export function buildBayesianProgress(study: AnyBayesianStudyResponse, responseId?: string): BayesianProgress {
  const objective = study.objective;
  const response = objective.goal_type === "desirability"
    ? objective.responses.find(goal => goal.response_id === (responseId ?? objective.responses[0]?.response_id)) : null;
  const goal = response?.goal ?? objective.goal_type;
  const target = response?.target ?? objective.target_value ?? null;
  const output: BayesianProgress = { rows: [], desirability: objective.goal_type === "desirability" ? [] : null,
    name: response?.name ?? objective.name, unit: response?.unit ?? objective.unit, goal, target: goal === "match_target" ? target : null,
    invalidTrialCount: 0, invalidDesirabilityCount: 0, reason: null };
  if (objective.goal_type === "desirability" && !response) return { ...output, reason: "response_unavailable" };
  if (goal === "match_target" && !finite(target)) return { ...output, reason: "target_unavailable" };
  let best: number | null = null, bestDesirability = 0;
  const ids = new Set<string>(), numbers = new Set<number>();
  for (const trial of [...study.trials].sort((a, b) => a.trial_number - b.trial_number)) {
    if (ids.has(trial.trial_id) || numbers.has(trial.trial_number) || !Number.isInteger(trial.trial_number) || trial.trial_number < 1)
      return { ...output, rows: [], desirability: null, reason: "trial_identity_invalid" };
    ids.add(trial.trial_id); numbers.add(trial.trial_number);
    if (trial.state !== "completed") continue;
    const value = response ? trial.response_values?.[response.response_id] : trial.objective_value;
    const distance = goal === "match_target" && finite(value) ? Math.abs(value - target!) : null;
    if (!finite(value) || (goal === "match_target" && !finite(distance))) { output.invalidTrialCount++; continue; }
    const metric = distance ?? value;
    best = best === null ? metric : goal === "maximize" ? Math.max(best, metric) : Math.min(best, metric);
    const row = { trialId: trial.trial_id, trialNumber: trial.trial_number, origin: trial.origin, value, best, distance };
    output.rows.push(row);
    if (objective.goal_type === "desirability") {
      const score = trial.response_values ? observedDesirability(objective, trial.response_values) : null;
      if (score === null) output.invalidDesirabilityCount++;
      else { bestDesirability = Math.max(bestDesirability, score); output.desirability!.push({ ...row, value: score, best: bestDesirability, distance: null }); }
    }
  }
  return output;
}

export function projectBayesianFactors(study: AnyBayesianStudyResponse, xId: string, yId: string) {
  const xFactor = study.factors.find(factor => factor.factor_id === xId), yFactor = study.factors.find(factor => factor.factor_id === yId);
  const ticks = (factor: typeof xFactor) => factor && "levels" in factor ? factor.levels.map((label, value) => ({ value, label })) : undefined;
  const output = { points: [] as Array<{ trialId: string; trialNumber: number; x: number; y: number; state: string; origin: string;
    actualX: string | number; actualY: string | number }>, xFactor, yFactor, xTicks: ticks(xFactor), yTicks: ticks(yFactor), invalidTrialCount: 0, reason: null as string | null };
  if (xId === yId) return { ...output, reason: "distinct_factors_required" };
  if (!xFactor || !yFactor) return { ...output, reason: "factor_unavailable" };
  function coordinate(factor: NonNullable<typeof xFactor>, value: unknown) {
    if ("levels" in factor) { const index = typeof value === "string" ? factor.levels.indexOf(value) : -1; return index >= 0 ? index : null; }
    return finite(value) ? value : null;
  }
  for (const trial of study.trials) {
    const actualX = trial.actual_coordinates[xId], actualY = trial.actual_coordinates[yId];
    const x = coordinate(xFactor, actualX), y = coordinate(yFactor, actualY);
    if (x === null || y === null) { output.invalidTrialCount++; continue; }
    output.points.push({ trialId: trial.trial_id, trialNumber: trial.trial_number, x, y, actualX, actualY, state: trial.state, origin: trial.origin });
  }
  return output;
}
