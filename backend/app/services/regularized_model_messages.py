from app.services.regularized_model_report import regularized_warning_text

WARNING_MESSAGES = {
    code: regularized_warning_text(code, "en")
    for code in (
        "regularized_model_predictive_not_causal",
        "regularized_model_categorical_levelwise_penalty",
        "regularized_model_hierarchy_not_enforced",
        "lasso_correlated_predictor_instability",
        "lasso_all_or_most_coefficients_zero",
        "regularized_model_convergence_warning",
        "regularized_model_constant_fold_feature",
        "regularized_model_negative_predicted_r_squared",
        "regularized_model_training_cv_gap",
        "missing_values_excluded",
        "non_numeric_values_excluded",
    )
}
