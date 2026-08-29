import { ApiRequestError } from "../api/client";
import { t, type TranslationKey } from "./translate";
import type { AppLocale } from "./types";

export interface LocalizedErrorDisplay {
  code: string;
  correlationId: string | null;
  message: string;
}

const errorKeys: Readonly<Record<string, TranslationKey>> = {
  api_unreachable: "errors.apiUnreachable",
  invalid_gaussian_process_options: "errors.gpGeneric",
  gp_response_required: "errors.gpResponseRequired",
  gp_predictor_required: "errors.gpPredictorRequired",
  gp_predictors_too_few: "errors.gpPredictorRequired",
  gp_predictor_type_unsupported: "errors.gpPredictorRequired",
  gp_response_type_unsupported: "errors.gpResponseRequired",
  gp_duplicate_predictor: "errors.gpGeneric",
  gp_response_in_predictors: "errors.gpGeneric",
  gp_predictor_count_limit: "errors.gpGeneric",
  gp_constant_response: "errors.gpFitFailed",
  gp_constant_predictor: "errors.gpFitFailed",
  gp_kernel_policy_invalid: "errors.gpGeneric",
  gp_noise_mode_invalid: "errors.gpGeneric",
  gp_noise_value_invalid: "errors.gpGeneric",
  gp_jitter_invalid: "errors.gpGeneric",
  gp_cv_fold_invalid: "errors.gpGeneric",
  gp_leave_one_out_limit: "errors.gpGeneric",
  gp_cross_validation_failed: "errors.gpFitFailed",
  gp_time_budget_exhausted: "errors.gpFitFailed",
  gp_usable_rows_too_few: "errors.gpUsableRowsTooFew",
  gp_usable_rows_limit: "errors.gpUsableRowsLimit",
  gp_fit_failed: "errors.gpFitFailed",
  gp_not_converged: "errors.gpFitFailed",
  gp_hyperparameter_optimization_failed: "errors.gpFitFailed",
  gp_covariance_not_positive_definite: "errors.gpFitFailed",
  gp_prediction_failed: "errors.gpPredictionFailed",
  gp_prediction_input_invalid: "errors.gpPredictionFailed",
  gp_prediction_model_stale: "errors.gpPredictionFailed",
  gp_model_manifest_invalid: "errors.gpManifestInvalid",
  gp_model_manifest_checksum_mismatch: "errors.gpManifestInvalid",
  gp_model_artifact_checksum_mismatch: "errors.gpManifestInvalid",
  gp_model_artifact_invalid: "errors.gpManifestInvalid",
  invalid_pls_options: "errors.plsInvalidOptions",
  pls_calculation_timeout: "errors.plsCalculationTimeout",
  pls_component_count_invalid: "errors.plsComponentCountInvalid",
  pls_cross_validation_failed: "errors.plsCrossValidationFailed",
  pls_cv_fold_count_invalid: "errors.plsCvFoldCountInvalid",
  pls_cv_group_invalid: "errors.plsCvGroupInvalid",
  pls_leave_one_out_limit: "errors.plsLeaveOneOutLimit",
  pls_model_fit_failed: "errors.plsModelFitFailed",
  pls_model_manifest_invalid: "errors.plsManifestInvalid",
  pls_model_manifest_checksum_mismatch: "errors.plsManifestChecksumMismatch",
  pls_model_not_converged: "errors.plsModelNotConverged",
  pls_prediction_model_stale: "errors.plsModelStale",
  pls_prediction_duplicate_row_id: "errors.plsPredictionDuplicateRow",
  pls_prediction_failed: "errors.plsPredictionFailed",
  pls_prediction_predictor_mapping_invalid: "errors.plsPredictionMappingInvalid",
  pls_prediction_value_invalid: "errors.plsPredictionValueInvalid",
  pls_predictor_type_unsupported: "errors.plsPredictorTypeUnsupported",
  pls_predictors_too_few: "errors.plsPredictorsTooFew",
  pls_response_required: "errors.plsResponseRequired",
  pls_response_type_unsupported: "errors.plsResponseTypeUnsupported",
  pls_usable_rows_limit: "errors.plsUsableRowsLimit",
  pls_usable_rows_too_few: "errors.plsUsableRowsTooFew",
};

export function localizedErrorDisplay(
  error: unknown,
  locale: AppLocale,
): LocalizedErrorDisplay {
  const code = error instanceof ApiRequestError
    ? error.code
    : error instanceof Error && /^[a-z][a-z0-9_]+$/u.test(error.message)
      ? error.message
      : "unknown_error";
  return {
    code,
    correlationId: error instanceof ApiRequestError ? error.correlationId : null,
    message: t(errorKeys[code] ?? "errors.generic", {}, locale),
  };
}
