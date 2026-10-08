import type { PrincipalComponentsResult, PlsRegressionResult, GaussianProcessRegressionResult } from "../api";

function column(column_id: string, display_name: string, column_index: number, role: "response" | "feature") {
  return { column_id, display_name, source_name: display_name, column_index, role,
    data_type: "decimal" as const, measurement_level: "continuous" as const, unit: null };
}

// Synthetic browser fixtures. No application route imports these values.
export function pcaFixture(): PrincipalComponentsResult {
  const scoreRows = [
    { source_row_number: 1, scores: [-1, 0.2], mahalanobis_distance_squared: 1.1, outlier: false },
    { source_row_number: 2, scores: [1, -0.2], mahalanobis_distance_squared: 7.1, outlier: true },
  ];
  return {
    schema_version: 1,
    summary_type: "principal_components_analysis",
    method: "sample_correlation_eigendecomposition",
    missing_policy: "complete_case",
    sample: { n_total: 2, n_used: 2, n_excluded: 0, n_excluded_missing: 0, n_excluded_non_numeric: 0, variable_count: 2 },
    variables: [
      { column_id: "x1", display_name: "temperature_c", unit: null, mean: 2, sample_standard_deviation: 1 },
      { column_id: "x2", display_name: "pressure_bar", unit: null, mean: 4, sample_standard_deviation: 2 },
    ],
    preprocessing: { matrix_type: "correlation", centered: true, standardized: true, degrees_of_freedom: 1 },
    matrix: [[1, 0.8], [0.8, 1]],
    component_selection: { mode: "all", requested_component_count: null, cumulative_threshold: 0.9, maximum_components: 2, selected_components: 2, selected_cumulative_proportion: 1 },
    eigenanalysis: [
      { component: 1, eigenvalue: 1.8, proportion: 0.9, cumulative_proportion: 0.9, selected: true },
      { component: 2, eigenvalue: 0.2, proportion: 0.1, cumulative_proportion: 1, selected: true },
    ],
    eigenvectors: [
      { column_id: "x1", display_name: "temperature_c", values: [0.707, 0.707] },
      { column_id: "x2", display_name: "pressure_bar", values: [0.707, -0.707] },
    ],
    loadings: [
      { column_id: "x1", display_name: "temperature_c", values: [0.95, 0.32] },
      { column_id: "x2", display_name: "pressure_bar", values: [0.95, -0.32] },
    ],
    scores: scoreRows,
    plot: { point_limit: 5000, point_count: 2, sampled: false, sampling_policy: "outliers_then_evenly_spaced", points: scoreRows },
    outliers: { alpha: 0.05, method: "chi_square_squared_mahalanobis_selected_components", degrees_of_freedom: 2, reference_value: 5.99, count: 1 },
    warnings: [],
    provenance: { algorithm: "numpy.linalg.eigh", sign_policy: "largest_absolute_eigenvector_entry_positive_first_on_tie", score_equation: "transformed_X @ eigenvectors" },
  };
}


export function plsFixture(): PlsRegressionResult {
  return {
    schema_version: 1,
    summary_type: "partial_least_squares_regression",
    method: {
      name: "PLS1 regression",
      engine: "sklearn.cross_decomposition.PLSRegression",
      engine_version: "1.7.2",
      component_selection: "automatic_cv",
      cv_method: "k_fold",
      cv_folds: 5,
      cv_shuffle: true,
      cv_seed: 20260820,
      scale: true,
      max_iter: 500,
      tol: 1e-6,
      missing_policy: "complete_case",
    },
    response: column("response", "yield_pct", 0, "response"),
    predictors: [
      column("x1", "temperature_c", 1, "feature"),
      column("x2", "pressure_bar", 2, "feature"),
    ],
    sample: {
      n_total: 12,
      n_used: 12,
      n_excluded: 0,
      n_excluded_missing: 0,
      n_excluded_non_numeric: 0,
      predictor_count: 2,
    },
    component_selection: {
      selected_components: 1,
      evaluated_components: 2,
      maximum_allowed_components: 2,
      tie_tolerance: 1e-12,
      rows: [
        {
          components: 1,
          x_variance: 0.94,
          training_sse: 1.25,
          training_r_squared: 0.96,
          press: 2.5,
          predicted_r_squared: 0.91,
          cv_rmse: 0.46,
          iterations: [3],
          converged: true,
        },
        {
          components: 2,
          x_variance: 1,
          training_sse: 0.9,
          training_r_squared: 0.97,
          press: 2.8,
          predicted_r_squared: 0.89,
          cv_rmse: 0.49,
          iterations: [3, 4],
          converged: true,
        },
      ],
    },
    model_summary: {
      selected_components: 1,
      training_r_squared: 0.96,
      predicted_r_squared: 0.91,
      press: 2.5,
      cv_rmse: 0.46,
      cumulative_x_variance: 0.94,
    },
    coefficients: [
      {
        column_id: "x1",
        display_name: "temperature_c",
        coefficient: 0.7,
        standardized_coefficient: 0.72,
        direction: "positive",
      },
      {
        column_id: "x2",
        display_name: "pressure_bar",
        coefficient: -0.2,
        standardized_coefficient: -0.18,
        direction: "negative",
      },
    ],
    latent_components: {
      x_weights: [[0.7], [0.7]],
      y_weights: [[0.9]],
      x_loadings: [[0.72], [0.68]],
      y_loadings: [[0.9]],
      x_rotations: [[0.7], [0.7]],
      score_row_indices: [0, 1],
      x_scores: [[-1.2], [1.1]],
      y_scores: [[-1.1], [1.2]],
    },
    diagnostics: {
      point_limit: 2000,
      point_count_total: 12,
      truncated: false,
      points: [
        {
          row_index: 0,
          observed: 80,
          fitted: 80.2,
          cross_validated_fitted: 80.4,
          residual: -0.2,
          cross_validated_residual: -0.4,
        },
        {
          row_index: 1,
          observed: 82,
          fitted: 81.8,
          cross_validated_fitted: 81.7,
          residual: 0.2,
          cross_validated_residual: 0.3,
        },
      ],
    },
    training_ranges: [
      { column_id: "x1", minimum: 70, maximum: 100 },
      { column_id: "x2", minimum: 5, maximum: 15 },
    ],
    warnings: ["pls_predictive_not_causal", "pls_no_classical_coefficient_p_values"],
    model_manifest: {
      model_id: "model-pls",
      manifest_schema_version: 1,
      manifest_sha256: "a".repeat(64),
    },
  };
}

export function gpFixture(): GaussianProcessRegressionResult {
  const interval = { lower: 79, upper: 81 };
  return {
    schema_version: 1,
    summary_type: "gaussian_process_regression",
    method: {
      name: "Gaussian Process Regression",
      engine: "sklearn.gaussian_process.GaussianProcessRegressor",
      engine_version: "1.7.2",
      kernel_preset: "matern_5_2_ard",
      noise_mode: "estimate",
      standardize_predictors: true,
      normalize_response: true,
      jitter: 1e-8,
      optimizer_restarts: 3,
      cv_optimizer_restarts: 0,
      random_seed: 20260829,
      validation_method: "k_fold",
      cv_folds: 5,
      cv_shuffle: true,
      missing_policy: "complete_case",
      execution_mode: "bounded_inline",
      elapsed_seconds: 0.5,
    },
    response: column("response", "yield_pct", 0, "response"),
    predictors: [
      column("x1", "temperature_c", 1, "feature"),
      column("x2", "pressure_bar", 2, "feature"),
    ],
    sample: {
      n_total: 16,
      n_used: 16,
      n_excluded: 0,
      n_excluded_missing: 0,
      n_excluded_non_numeric: 0,
      predictor_count: 2,
    },
    model_summary: {
      training_r_squared: 0.98,
      training_rmse: 0.2,
      training_mae: 0.15,
      predicted_r_squared: 0.91,
      press: 2.1,
      cv_rmse: 0.4,
      cv_mae: 0.32,
      negative_log_predictive_density: 0.7,
      interval_coverage_95: 0.94,
      mean_predictive_interval_width: 1.6,
      log_marginal_likelihood: -3.2,
      fitted_noise_standard_deviation: 0.12,
    },
    kernel: {
      preset: "matern_5_2_ard",
      fitted_kernel: "1.2**2 * Matern(length_scale=[0.7, 1.1], nu=2.5) + WhiteKernel",
      signal_kernel: {},
      observation_noise_variance: 0.0144,
      observation_noise_standard_deviation: 0.12,
      log_marginal_likelihood: -3.2,
      converged: true,
      parameters: [
        {
          parameter: "length_scale",
          column_id: "x1",
          estimate: 0.7,
          lower_bound: 0.01,
          upper_bound: 100,
          near_bound: false,
        },
      ],
    },
    diagnostics: {
      point_limit: 1000,
      point_count_total: 16,
      truncated: false,
      points: [
        {
          row_index: 0,
          observed: 80,
          fitted: 80.1,
          residual: -0.1,
          latent_standard_deviation: 0.2,
          predictive_standard_deviation: 0.25,
          predictive_interval_95: interval,
          cross_validated_fitted: 80.3,
          cross_validated_residual: -0.3,
          cross_validated_predictive_standard_deviation: 0.4,
          standardized_predictive_residual: -0.75,
        },
      ],
    },
    conditional_profiles: [
      {
        column_id: "x1",
        display_name: "temperature_c",
        fixed_values: [85, 10],
        points: [
          {
            value: 70,
            predicted_mean: 79,
            latent_standard_deviation: 0.2,
            latent_interval_95: interval,
            predictive_standard_deviation: 0.25,
            predictive_interval_95: interval,
          },
          {
            value: 100,
            predicted_mean: 84,
            latent_standard_deviation: 0.3,
            latent_interval_95: interval,
            predictive_standard_deviation: 0.35,
            predictive_interval_95: interval,
          },
        ],
      },
    ],
    two_predictor_surface: {
      x_column_id: "x1",
      x_display_name: "temperature_c",
      y_column_id: "x2",
      y_display_name: "pressure_bar",
      grid_size: 1,
      fixed_values: [85, 10],
      points: [{ x: 85, y: 10, predicted_mean: 82, predictive_standard_deviation: 0.3 }],
    },
    training_ranges: [
      { column_id: "x1", display_name: "temperature_c", minimum: 70, maximum: 100, median: 85 },
      { column_id: "x2", display_name: "pressure_bar", minimum: 5, maximum: 15, median: 10 },
    ],
    warnings: ["gp_uncertainty_conditional_on_kernel"],
    model_manifest: {
      model_id: "model-gp",
      manifest_schema_version: 1,
      manifest_sha256: "a".repeat(64),
    },
  } as GaussianProcessRegressionResult;
}
