import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type {
  AnalysisResultEnvelope,
  DatasetVersionResponse,
  GaussianProcessRegressionResult,
} from "./api";
import { GaussianProcessRegressionPanel } from "./GaussianProcessRegressionPanel";
import { GpKernelSelectionSettings, gpOptimizerStarts, gpPresets } from "./GpKernelSelectionSettings";
import { setCurrentLocale } from "./i18n/store";

describe("GaussianProcessRegressionPanel", () => {
  it("keeps candidate selection, WhiteKernel noise and the optimizer budget distinct", () => {
    for (const locale of ["en", "ko"] as const) {
      setCurrentLocale(locale);
      const value = { mode: "compare" as const, kernel_candidates: [...gpPresets], criterion: "cv_nlpd" as const, retain_candidate_details: true };
      const html = renderToString(<GpKernelSelectionSettings value={value} onChange={() => undefined} onModeChange={() => undefined} noiseMode="estimate" disabled={false} />);
      expect(html.match(/type="checkbox"/g)).toHaveLength(5);
      expect(html).toContain("WhiteKernel");
      expect(html).toContain("RBF ARD");
      expect(gpOptimizerStarts(value, 10, 5, 10)).toBe(284);
      expect(gpOptimizerStarts({ ...value, retain_candidate_details: false }, 10, 5, 10)).toBe(251);
      const fixed = renderToString(<GpKernelSelectionSettings value={value} onChange={() => undefined} onModeChange={() => undefined} noiseMode="fixed" disabled={false} />);
      expect(fixed).not.toContain("+ WhiteKernel");
    }
  });

  it("renders comparison failures without metrics and only selected-model prediction", () => {
    setCurrentLocale("en");
    const result = resultFixture();
    result.schema_version = 2;
    result.kernel_selection = { mode: "compare", criterion: "cv_nlpd", candidate_presets: ["matern_5_2_ard", "rbf_ard"], selected_preset: "matern_5_2_ard", retain_candidate_details: true, selection_is_external_validation: false, optimizer_starts: 20, tie_break_policy: "stable" };
    result.kernel_candidates = [
      { preset: "matern_5_2_ard", composed_kernel: "Constant * Matern + WhiteKernel", status: "succeeded", selected: true, selection_rank: 1, failure_code: null, elapsed_seconds: 1, converged_folds: 5, warnings: [], metrics: { predicted_r_squared: .8, press: 2, rmse: .4, mae: .3, nlpd: .7, interval_coverage_95: .95, mean_interval_width: 1 }, details: result },
      { preset: "rbf_ard", composed_kernel: "Constant * RBF + WhiteKernel", status: "failed", selected: false, selection_rank: null, failure_code: "gp_time_budget_exhausted", elapsed_seconds: 2, converged_folds: 0, warnings: [], metrics: null, details: null },
    ];
    const html = renderToString(<GaussianProcessRegressionPanel analysisResult={analysisEnvelope()} filterValidationError={null} isRunningAnalysis={false} methodId="regression.gaussian_process" result={result} version={datasetVersion()} onRun={() => undefined} />);
    expect(html).toContain("Kernel Comparison");
    expect(html).toContain("Candidate Failed");
    expect(html).toContain("independent");
    expect(html).not.toContain("NaN");
  });

  it("renders bounded numeric roles, kernels, noise, and validation controls", () => {
    setCurrentLocale("en");
    const html = renderToString(
      <GaussianProcessRegressionPanel
        analysisResult={null}
        filterValidationError={null}
        isRunningAnalysis={false}
        methodId="regression.gaussian_process"
        result={null}
        version={datasetVersion()}
        onRun={() => undefined}
      />,
    );

    expect(html).toContain("Run Gaussian Process Regression");
    expect(html).toContain("Matérn 5/2 ARD");
    expect(html).toContain("Rational Quadratic");
    expect(html).toContain("Estimate from data");
    expect(html).toContain("Leave-One-Out");
    expect(html).toContain("temperature_c");
    expect(html).toContain("pressure_bar");
    expect(html).not.toContain("VIF");
    expect(html).not.toContain("p-value");
  });

  it("renders validation, uncertainty diagnostics, profiles, surfaces, and prediction", () => {
    setCurrentLocale("en");
    const html = renderToString(
      <GaussianProcessRegressionPanel
        analysisResult={analysisEnvelope()}
        filterValidationError={null}
        isRunningAnalysis={false}
        methodId="regression.gaussian_process"
        result={resultFixture()}
        version={datasetVersion()}
        onRun={() => undefined}
      />,
    );

    expect(html).toContain("Kernel &amp; Hyperparameters");
    expect(html).toContain("Predicted R²");
    expect(html).toContain("Negative log predictive density");
    expect(html).toContain("Conditional Predictor Profiles");
    expect(html).toContain("Two-Predictor Surface");
    expect(html).toContain("New Condition Prediction");
    expect(html).toContain("Latent 95% interval");
    expect(html).toContain("New observation 95% interval");
    expect(html).not.toContain("Adjusted R");
  });
});

function datasetVersion(): DatasetVersionResponse {
  return {
    version_id: "version-gp",
    dataset_id: "dataset-gp",
    created_at: "2026-08-29T00:00:00Z",
    row_count: 16,
    column_count: 3,
    columns: [
      column("response", "yield_pct", 0, "response"),
      column("x1", "temperature_c", 1, "feature"),
      column("x2", "pressure_bar", 2, "feature"),
    ],
  } as unknown as DatasetVersionResponse;
}

function column(
  columnId: string,
  displayName: string,
  columnIndex: number,
  role: "response" | "feature",
) {
  return {
    column_id: columnId,
    display_name: displayName,
    source_name: displayName,
    column_index: columnIndex,
    data_type: "decimal" as const,
    measurement_level: "continuous" as const,
    role,
    unit: null,
  };
}

function resultFixture(): GaussianProcessRegressionResult {
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

function analysisEnvelope(): AnalysisResultEnvelope {
  return {
    analysis_id: "analysis-gp",
    method_id: "regression.gaussian_process",
    method_version: "0.1.0",
    result: resultFixture(),
  } as AnalysisResultEnvelope;
}
