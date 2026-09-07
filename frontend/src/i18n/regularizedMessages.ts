import type { TranslationKey } from "./translate";

export const regularizedErrorKeys: Readonly<Record<string, TranslationKey>> = {
  regularized_model_estimator_invalid: "reg.error.generic",
  regularized_model_alpha_invalid: "reg.error.alpha",
  regularized_model_l1_ratio_invalid: "reg.error.ratio",
  regularized_model_cv_folds_invalid: "reg.error.folds",
  regularized_model_usable_rows_too_few: "reg.error.rows",
  regularized_model_row_count_limit: "reg.error.rows",
  regularized_model_feature_count_limit: "reg.error.features",
  regularized_model_search_budget_exceeded: "reg.error.budget",
  regularized_model_time_budget_exhausted: "reg.error.budget",
  regularized_model_leave_one_out_limit: "reg.error.budget",
  regularized_model_worker_busy: "reg.error.busy",
  regularized_model_fit_failed: "reg.error.generic",
  regularized_model_cv_failed: "reg.error.generic",
  regularized_model_prediction_interval_unavailable: "reg.pointOnly",
};

export const regularizedWarningKeys: Readonly<Record<string, TranslationKey>> = {
  regularized_model_convergence_warning: "reg.warning.convergence",
  regularized_model_constant_fold_feature: "reg.warning.constant",
  regularized_model_negative_predicted_r_squared: "reg.warning.negative",
  regularized_model_training_cv_gap: "reg.warning.gap",
  lasso_all_or_most_coefficients_zero: "reg.warning.zero",
  lasso_correlated_predictor_instability: "reg.warning.instability",
  regularized_model_predictive_not_causal: "reg.assumptions",
  regularized_model_hierarchy_not_enforced: "reg.assumptions",
  regularized_model_categorical_levelwise_penalty: "reg.assumptions",
  regularized_model_prediction_interval_unavailable: "reg.pointOnly",
};
