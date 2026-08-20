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
