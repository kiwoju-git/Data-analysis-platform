import type { AugmentationRenewalLineage, AugmentationRenewalResponse, AugmentationSelectionResponse } from "../../api/types/boAugmentation";
import type { BayesianStudyResponse } from "../../api/types/bayesian";
import { sameDesirabilityJson } from "./desirabilityResponseGuard";
import { validAugmentationSelection } from "./boAugmentationDraft";
import { planningHash, planningId } from "./boPlanningDraft";

export function augmentationNeedsRenewal(selection: AugmentationSelectionResponse): boolean {
  return selection.calculation.selected_rows.some(row => "acquisition" in row && row.acquisition != null &&
    !Object.prototype.hasOwnProperty.call(row.acquisition, "numerical_policy"));
}

export function validRenewalLineage(value: AugmentationRenewalLineage, selection: AugmentationSelectionResponse): boolean {
  return value?.schema_version === 1 && value.study_version_id === selection.study_version_id &&
    value.renewed_selection_id === selection.selection_id && value.original_selection_id !== selection.selection_id &&
    planningId(value.original_selection_id) && planningHash(value.original_config_sha256) && planningHash(value.original_result_sha256) &&
    value.numerical_policy === "positive_beta_integral_v2" && value.created_at === selection.created_at;
}

export function validAugmentationRenewal(value: AugmentationRenewalResponse, study: BayesianStudyResponse, original: AugmentationSelectionResponse, requestId: string): boolean {
  const expected = { ...original.request, request_id: requestId };
  return value != null && validAugmentationSelection(value.selection, study, expected) &&
    sameDesirabilityJson(value.selection.request, expected) && value.selection.selection_id !== original.selection_id &&
    !augmentationNeedsRenewal(value.selection) && validRenewalLineage(value.lineage, value.selection) &&
    value.lineage.original_selection_id === original.selection_id &&
    value.lineage.original_config_sha256 === original.config_sha256 && value.lineage.original_result_sha256 === original.result_sha256;
}
