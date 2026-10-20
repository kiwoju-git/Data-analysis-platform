import type { DoeFractionalEstimability, DoeModelSelectionResult } from "../api/types/doeModelWorkflow";

export type DoePlotStatus = "retained" | "backward_removed" | "pooled" | "user_excluded" | "alias_nonestimable" | "not_requested" | "unknown";

export function doePlotStatus(
  termId: string,
  selection?: DoeModelSelectionResult | null,
  estimability?: DoeFractionalEstimability | null,
): DoePlotStatus {
  if (!selection) return "unknown";
  if (selection.final_term_ids.includes(termId)) return "retained";
  if (selection.removed_term_ids.includes(termId)) return "backward_removed";
  if (selection.pooled_term_ids.includes(termId)) return "pooled";
  if (selection.initially_excluded_term_ids?.includes(termId)) return "user_excluded";
  if (estimability?.exclusions.some((item) => item.term_id === termId)) return "alias_nonestimable";
  if (selection.term_catalog && !selection.term_catalog.some((term) => term.term_id === termId)) return "not_requested";
  return "unknown";
}
