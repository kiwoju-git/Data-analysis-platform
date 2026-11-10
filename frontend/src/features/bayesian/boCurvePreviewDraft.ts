import type { CurvePreviewRequest } from "../../api/types/boCurvePreview";
import { parseDoeResponseNumber as parse } from "../../doe/doeResponsePaste";
import type { ResponseGoalDraft } from "./bayesianVectorDraft";

export const initialCurvePreviewDraft = () => ({ lower: "0.0183", upper: "0.0183", assumed: false,
  mean: "", sd: "", incumbent: "", xi: "0" });
export type CurvePreviewDraft = ReturnType<typeof initialCurvePreviewDraft>;

export function curvePreviewRequest(goal: ResponseGoalDraft | undefined, draft: CurvePreviewDraft): CurvePreviewRequest | null {
  if (!goal || goal.goal !== "match_target") return null;
  const lower = parse(goal.lower), target = parse(goal.target), upper = parse(goal.upper);
  const dLower = parse(draft.lower), dUpper = parse(draft.upper);
  if (lower === null || target === null || upper === null || !(lower < target && target < upper) ||
    dLower === null || dUpper === null || !(dLower > 0 && dLower < 1 && dUpper > 0 && dUpper < 1)) return null;
  const padding = (upper - lower) / 4;
  const plotLower = lower - padding, plotUpper = upper + padding;
  if (![padding, plotLower, plotUpper, plotUpper - plotLower].every(Number.isFinite)) return null;
  let assumed: CurvePreviewRequest["assumed_distribution"] = null;
  if (draft.assumed) {
    const mean = parse(draft.mean), sd = parse(draft.sd), incumbent = parse(draft.incumbent), xi = parse(draft.xi);
    if (mean === null || sd === null || sd < 0 || incumbent === null || incumbent < 0 || incumbent > 1 || xi === null || xi < 0 || xi > 1) return null;
    assumed = { mean, standard_deviation: sd, incumbent, xi };
  }
  return { schema_version: 1, controls: { lower, target, upper, lower_desirability: dLower, upper_desirability: dUpper, peak: 1 },
    plot_lower: plotLower, plot_upper: plotUpper, assumed_distribution: assumed };
}
