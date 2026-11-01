import type { GageRrResult } from "./api";

export function restoredGageRrOptions(
  result: Pick<GageRrResult, "replicate_mode" | "interaction_selection">,
) {
  return {
    replicateMode: result.replicate_mode ?? "explicit_column",
    interactionPolicy: result.interaction_selection?.requested_policy ?? "retain",
    interactionAlpha: String(result.interaction_selection?.alpha_to_remove_interaction ?? 0.05),
  };
}
