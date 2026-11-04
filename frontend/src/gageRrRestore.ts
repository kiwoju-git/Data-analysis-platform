import type { GageRrResult } from "./api";

export function isGageRrResult(value: unknown): value is GageRrResult {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return candidate.summary_type === "gage_rr"
    && (candidate.schema_version === 1 || candidate.schema_version === 2 || candidate.schema_version === 3 || candidate.schema_version === 4)
    && Array.isArray(candidate.anova_table)
    && typeof candidate.variance_components === "object" && candidate.variance_components !== null;
}

export function restoredGageRrOptions(
  result: Pick<GageRrResult, "replicate_mode" | "interaction_selection">,
) {
  return {
    replicateMode: result.replicate_mode ?? "explicit_column",
    interactionPolicy: result.interaction_selection?.requested_policy ?? "retain",
    interactionAlpha: String(result.interaction_selection?.alpha_to_remove_interaction ?? 0.05),
  };
}
