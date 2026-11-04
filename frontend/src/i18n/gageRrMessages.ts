import type { ApiNoticeMessageKeys } from "./apiNoticePresentation";

// This dictionary is applied only at the Gage display boundary, never to stored DTOs.
export const gageRrNoticeKeys: ApiNoticeMessageKeys = {
  gage_rr_balanced_crossed_anova_assumed: "gage.notice.balancedAnova",
  gage_rr_interaction_not_pooled: "gage.notice.interactionRetained",
  gage_rr_interaction_pooled: "gage.notice.interactionPooled",
  gage_rr_independence_not_proven: "gage.notice.independence",
  gage_rr_labels_redacted: "gage.notice.labelsRedacted",
  gage_rr_operator_replicate_labels_redacted: "gage.notice.operatorReplicateLabelsRedacted",
  gage_rr_negative_variance_component_clamped: "gage.notice.negativeComponent",
  gage_rr_identifier_missing_excluded: "gage.notice.missingIdentifiers",
  gage_rr_preflight_only_no_variance_components: "gage.notice.preflightOnly",
  gage_rr_requires_balanced_crossed_design: "gage.notice.designRequired",
  gage_rr_no_usable_measurements: "gage.notice.noMeasurements",
  gage_rr_part_count_too_small: "gage.notice.partsTooFew",
  gage_rr_operator_count_too_small: "gage.notice.operatorsTooFew",
  gage_rr_replicate_count_too_small: "gage.notice.repeatsTooFew",
  gage_rr_crossed_cells_missing: "gage.notice.missingCells",
  gage_rr_unbalanced_crossed_design: "gage.notice.unbalanced",
  gage_rr_duplicate_replicates_per_cell: "gage.notice.duplicateReplicates",
  gage_rr_zero_total_variation: "gage.notice.zeroVariation",
  missing_values_excluded: "gage.notice.missingMeasurements",
  non_numeric_values_excluded: "gage.notice.nonNumericMeasurements",
};
