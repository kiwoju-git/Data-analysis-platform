import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { AnalysisResultEnvelope, DatasetVersionResponse, PlsRegressionResult } from "./api";
import { PlsRegressionPanel } from "./PlsRegressionPanel";

describe("PlsRegressionPanel", () => {
  it("renders numeric roles and bounded component/CV controls", () => {
    const html = renderToString(
      <PlsRegressionPanel
        analysisResult={analysisEnvelope()}
        filterValidationError={null}
        isRunningAnalysis={false}
        methodId="regression.partial_least_squares"
        result={null}
        version={datasetVersion()}
        onRun={() => undefined}
      />,
    );

    expect(html).toContain("PLS 회귀 실행");
    expect(html).toContain("교차검증으로 자동 선택");
    expect(html).toContain("성분 수 직접 지정");
    expect(html).toContain("K-Fold");
    expect(html).toContain("Leave-One-Out");
    expect(html).toContain("temperature_c");
    expect(html).toContain("pressure_bar");
    expect(html).not.toContain("VIF");
  });

  it("renders model selection, latent diagnostics, and point-only prediction", () => {
    const html = renderToString(
      <PlsRegressionPanel
        analysisResult={analysisEnvelope()}
        filterValidationError={null}
        isRunningAnalysis={false}
        methodId="regression.partial_least_squares"
        result={resultFixture()}
        version={datasetVersion()}
        onRun={() => undefined}
      />,
    );

    expect(html).toContain("모형 선택");
    expect(html).toContain("예측 R²");
    expect(html).toContain("관측 반응과 적합값");
    expect(html).toContain("적재량");
    expect(html).toContain("점예측");
    expect(html).toContain("예측 불확실성 구간은 아직 지원하지 않습니다");
    expect(html).not.toContain("<th>p-value</th>");
    expect(html).toContain("OLS p-value를 제공하지 않습니다");
    expect(html).not.toContain("평균 신뢰구간");
  });
});

function datasetVersion(): DatasetVersionResponse {
  return {
    version_id: "version-pls",
    dataset_id: "dataset-pls",
    created_at: "2026-08-20T00:00:00Z",
    row_count: 12,
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

function resultFixture(): PlsRegressionResult {
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

function analysisEnvelope(): AnalysisResultEnvelope {
  return {
    analysis_id: "analysis-pls",
    method_id: "regression.partial_least_squares",
    method_version: "0.1.0",
    dataset_version_id: "version-pls",
    status: "succeeded",
    warnings: [],
    provenance: {
      method_id: "regression.partial_least_squares",
      method_version: "0.1.0",
      dataset_version_id: "version-pls",
      source_schema_hash: "b".repeat(64),
      app_version: "0.1.0",
    },
    result: null,
  };
}
