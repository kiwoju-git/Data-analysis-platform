import type { DoeFinalModelWorkflow, DoeModelSelectionOptions } from "../api/types/doeModelWorkflow";
import { t } from "../i18n/translate";

type Cell = DoeFinalModelWorkflow["factorial_plots"]["cells"][number];
type Means = "fitted_mean" | "data_mean";

export function factorialNumber(value: number | null | undefined): string {
  return value === null || value === undefined || !Number.isFinite(value) ? "-" : Number(value.toPrecision(6)).toLocaleString();
}

export const defaultDoeSelection: DoeModelSelectionOptions = {
  method: "none", alpha_to_remove: 0.05, hierarchy_policy: "strong",
  saturated_start_policy: "pool_smallest_adjusted_ss", display_step_details: true,
};

export function interactionOrderLabel(order: number): string {
  return t(order === 1 ? "doe.interactionOrder.mainEffectsOnly" : order === 2
    ? "doe.interactionOrder.upToTwoWay" : "doe.interactionOrder.upToThreeWay");
}

export function factorialWorkflowMessage(code: string): string {
  if (code.includes("center_curvature_domain")) return t("doe.prediction.centerPolicy");
  if (code.includes("outside_domain")) return t("doe.prediction.outside");
  if (code.includes("unknown_level")) return t("doe.prediction.level");
  if (code.includes("numeric_required")) return t("doe.prediction.numeric");
  if (code.includes("variance_unavailable")) return t("doe.prediction.noVariance");
  if (code.includes("checksum") || code.includes("stale") || code.includes("source_changed")) return t("doe.prediction.source");
  if (code.includes("post_selection")) return t("doe.selection.exploratory");
  if (code.includes("initial_pooling")) return t("doe.selection.poolingWarning");
  if (code.includes("press_unavailable")) return t("doe.model.pressUnavailable");
  if (code.includes("vif_unavailable")) return t("doe.model.unavailable");
  if (code.startsWith("Numeric factor levels")) return t("doe.prediction.generalPolicy");
  if (code.startsWith("Residual degrees")) return t("doe.prediction.noVariance");
  if (code.startsWith("Repeated factor combinations")) return t("doe.model.pureErrorUnavailable");
  return t("doe.workflow.error");
}

export function factorialMarginalMean(cells: Cell[], settings: Record<string, number>, means: Means): number | null {
  const matched = cells.filter((cell) => Object.entries(settings).every(([name, value]) => cell.settings[name] === value) && cell[means] !== null);
  const weight = (cell: Cell) => means === "data_mean" ? cell.n : 1;
  const total = matched.reduce((sum, cell) => sum + weight(cell), 0);
  return total === 0 ? null : matched.reduce((sum, cell) => sum + (cell[means] ?? 0) * weight(cell), 0) / total;
}

