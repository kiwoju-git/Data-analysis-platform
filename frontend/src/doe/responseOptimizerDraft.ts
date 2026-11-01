import type {
  DoeResponseSurfaceAnalysisResponse, ResponseOptimizerCreateRequest,
  ResponseOptimizerGoal, ResponseOptimizerResponse, ResponseSurfaceDesignResponse,
} from "../api";
import { parseDoeResponseNumber } from "./doeResponsePaste";
import { strictRsmInteger } from "./rsmDesignDraft";
import { isRsmOnLattice, type RsmBounds, type RsmRegionMode } from "./rsmRegion";

export interface BoundDraft { lower: string; upper: string }
export interface ThresholdDraft extends BoundDraft { target: string }
export function optimizerBoundError(draft: BoundDraft | undefined, permitted: RsmBounds,
  lattice?: { anchor: number; step: number | null | undefined }): "number" | "order" | "range" | "lattice" | null {
  const lower = parseDoeResponseNumber(draft?.lower ?? "");
  const upper = parseDoeResponseNumber(draft?.upper ?? "");
  if (lower === null || upper === null) return "number";
  if (lower >= upper) return "order";
  if (lower < permitted.lower || upper > permitted.upper) return "range";
  if (lattice && (!isRsmOnLattice(lower, lattice.anchor, lattice.step) || !isRsmOnLattice(upper, lattice.anchor, lattice.step))) return "lattice";
  return null;
}
export interface OptimizerDraft {
  regionMode?: RsmRegionMode;
  goal: ResponseOptimizerGoal;
  thresholds: ThresholdDraft;
  lowerWeight: string; upperWeight: string; importance: string;
  bounds: Record<string, BoundDraft>;
  linearEnabled: boolean;
  linearName?: string;
  additionalLinearConstraints?: ResponseOptimizerCreateRequest["linear_constraints"];
  linearRelation: "less_than_or_equal" | "greater_than_or_equal";
  linearBound: string; linearCoefficients: Record<string, string>;
  randomSeed: string; randomCandidates: string; multiStarts: string;
  maxIterations: string; maxEvaluations: string; timeBudgetMs: string;
}

export function optimizerSourceKey(design: ResponseSurfaceDesignResponse,
  analysis: DoeResponseSurfaceAnalysisResponse, saved: ResponseOptimizerResponse | null): string {
  return JSON.stringify([design.design_id, design.design_version_id, design.design_sha256,
    analysis.analysis_id, analysis.response_revision_id, analysis.response_revision_sha256,
    saved?.optimization_id ?? null]);
}

export function defaultThresholds(goal: ResponseOptimizerGoal, minimum: number, maximum: number): ThresholdDraft {
  const spread = Math.max(maximum - minimum, Math.max(Math.abs(minimum), Math.abs(maximum), 1) * 0.1);
  if (goal === "maximize") return { lower: String(minimum), target: String(maximum), upper: "" };
  if (goal === "minimize") return { lower: "", target: String(minimum), upper: String(maximum) };
  if (goal === "target") return { lower: String(minimum), target: String(minimum / 2 + maximum / 2), upper: String(maximum) };
  return { lower: String(minimum - spread * 0.1), target: "", upper: String(maximum + spread * 0.1) };
}

export function optimizerRequest(input: OptimizerDraft & {
  analysis: Pick<DoeResponseSurfaceAnalysisResponse, "analysis_id">;
  design: Pick<ResponseSurfaceDesignResponse, "factors">;
  acknowledgedSourceWarningCodes: string[];
  permittedBounds?: Readonly<Record<string, RsmBounds>>;
}): ResponseOptimizerCreateRequest | string {
  const number = (raw: string | undefined) => parseDoeResponseNumber(raw ?? "");
  const lower = input.goal === "minimize" ? null : number(input.thresholds.lower);
  const target = input.goal === "range" ? null : number(input.thresholds.target);
  const upper = input.goal === "maximize" ? null : number(input.thresholds.upper);
  const lowerWeight = number(input.lowerWeight), upperWeight = number(input.upperWeight), importance = number(input.importance);
  if ((input.goal !== "minimize" && lower === null) || (input.goal !== "range" && target === null) ||
    (input.goal !== "maximize" && upper === null) || lowerWeight === null || upperWeight === null || importance === null ||
    [lowerWeight, upperWeight, importance].some((value) => value <= 0 || value > 10)) return "response_optimizer_objective_invalid";
  if ((lower !== null && target !== null && lower >= target) ||
    (target !== null && upper !== null && target >= upper) ||
    (lower !== null && upper !== null && lower >= upper)) return "response_optimizer_objective_thresholds_invalid";
  const factorBounds: ResponseOptimizerCreateRequest["factor_bounds"] = [];
  for (const factor of input.design.factors) {
    const lo = number(input.bounds[factor.name]?.lower), hi = number(input.bounds[factor.name]?.upper);
    const permitted = input.permittedBounds?.[factor.name] ?? { lower: factor.low, upper: factor.high };
    const lattice = factor.domain_kind === "discrete_numeric" ? { anchor: factor.low, step: factor.step } : undefined;
    if (lo === null || hi === null || optimizerBoundError(input.bounds[factor.name], permitted, lattice)) return "response_optimizer_factor_bound_invalid";
    factorBounds.push({ factor_name: factor.name, lower: lo, upper: hi });
  }
  const linearConstraints: ResponseOptimizerCreateRequest["linear_constraints"] = [];
  if (input.linearEnabled) {
    const coefficients: Record<string, number> = {};
    for (const factor of input.design.factors) {
      const value = number(input.linearCoefficients[factor.name]);
      if (value === null) return "response_optimizer_linear_constraint_invalid";
      coefficients[factor.name] = value;
    }
    const bound = number(input.linearBound);
    if (bound === null || Object.values(coefficients).every((value) => value === 0)) return "response_optimizer_linear_constraint_invalid";
    linearConstraints.push({ name: input.linearName ?? "UI linear constraint", coefficients, relation: input.linearRelation, bound });
    for (const constraint of input.additionalLinearConstraints ?? []) {
      if (!Number.isFinite(constraint.bound) || Object.values(constraint.coefficients).some((value) => !Number.isFinite(value))) {
        return "response_optimizer_linear_constraint_invalid";
      }
      linearConstraints.push({ ...constraint, coefficients: { ...constraint.coefficients } });
    }
  }
  const search = [input.randomSeed, input.randomCandidates, input.multiStarts, input.maxIterations,
    input.maxEvaluations, input.timeBudgetMs].map(strictRsmInteger);
  if (search.some((value) => value === null)) return "response_optimizer_search_budget_invalid";
  const [seed, candidates, starts, iterations, evaluations, time] = search as number[];
  if (seed > 2_147_483_647 || candidates > 4096 || starts < 1 || starts > 32 ||
    iterations < 1 || iterations > 500 || evaluations < 32 || evaluations > 100_000 ||
    time < 100 || time > 30_000) return "response_optimizer_search_budget_invalid";
  return { region_mode: input.regionMode ?? "legacy_input_bounds_v1",
    objectives: [{ source_analysis_id: input.analysis.analysis_id, goal: input.goal, lower, target, upper,
    lower_weight: lowerWeight, upper_weight: upperWeight, importance }], factor_bounds: factorBounds,
    linear_constraints: linearConstraints,
    search: { random_seed: seed, random_candidate_count: candidates, multi_start_count: starts,
      max_iterations: iterations, max_evaluations: evaluations, time_budget_ms: time },
    acknowledged_source_warning_codes: [...input.acknowledgedSourceWarningCodes] };
}

export function restoreOptimizerDraft(saved: ResponseOptimizerResponse): OptimizerDraft {
  const { result } = saved;
  const objective = result.objectives[0];
  const constraint = result.factor_region.linear_constraints[0];
  const text = (value: number | null) => value === null ? "" : String(value);
  return {
    regionMode: result.factor_region.region_mode ?? "legacy_input_bounds_v1",
    goal: objective.goal, thresholds: { lower: text(objective.lower), target: text(objective.target), upper: text(objective.upper) },
    lowerWeight: String(objective.lower_weight), upperWeight: String(objective.upper_weight), importance: String(objective.importance),
    bounds: Object.fromEntries(result.factor_region.search_bounds.map((bound) => [bound.factor_name, { lower: String(bound.lower), upper: String(bound.upper) }])),
    linearEnabled: constraint !== undefined, linearRelation: constraint?.relation ?? "less_than_or_equal",
    linearName: constraint?.name,
    additionalLinearConstraints: result.factor_region.linear_constraints.slice(1).map((item) => ({ ...item, coefficients: { ...item.coefficients } })),
    linearBound: String(constraint?.bound ?? 0),
    linearCoefficients: Object.fromEntries(result.factor_region.design_bounds.map((factor) => [factor.factor_name, String(constraint?.coefficients[factor.factor_name] ?? 0)])),
    randomSeed: String(result.search.random_seed), randomCandidates: String(result.search.random_candidate_count),
    multiStarts: String(result.search.multi_start_count), maxIterations: String(result.search.max_iterations),
    maxEvaluations: String(result.search.max_evaluations), timeBudgetMs: String(result.search.time_budget_ms),
  };
}
