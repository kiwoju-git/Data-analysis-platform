import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { RegularizationSettingsPanel, regularizationDefaults, regularizationValid } from "./RegularizationSettingsPanel";
import { RegressionPredictionResultsTable } from "./RegressionPredictionResultsTable";
import { setCurrentLocale } from "./i18n/store";
import { RegularizedLinearModelResults } from "./RegularizedLinearModelResults";
import type { RegularizedEstimator, RegularizedLinearModelResult } from "./api";

afterEach(() => setCurrentLocale("ko"));

describe("regularized model controls", () => {
  it.each(["ridge", "lasso", "elastic_net"] as const)("renders %s diagnostics without classical inference", (kind) => {
    for (const locale of ["en", "ko"] as const) {
      setCurrentLocale(locale);
      const html = renderToStaticMarkup(<RegularizedLinearModelResults result={regularizedFixture(kind)} />);
      expect(html).toContain("regularization-cv-curve-title");
      expect(html).toContain("regularization-coefficient-path-title");
      expect(html).toContain("PRESS");
      expect(html).toContain("-0.2");
      expect(html).not.toMatch(/<th[^>]*>(SE|t|p-value|VIF|ANOVA)/);
      // Legacy chart text is localized by the production Vite transform, disabled in Vitest.
      if (locale === "en") expect(html.match(/<(?:h4|th)[^>]*>.*?<\/(?:h4|th)>/g)?.join("")).not.toMatch(/[가-힣]/);
      expect(html).toContain(locale === "en" ? "Coefficients Shrunk to Zero" : "0으로 축소된 계수");
    }
  });
  it.each(["ridge", "lasso", "elastic_net"] as const)("keeps %s defaults valid and bounded", (estimator) => {
    const config = regularizationDefaults(estimator);
    expect(regularizationValid(config)).toBe(true);
    expect(config.regularization.mode).toBe("automatic_cv");
    expect(config.regularization.outer_folds).toBe(5);
    expect(config.regularization.inner_folds).toBe(5);
    expect(config.regularization.alpha_min).toBeGreaterThan(0);
    expect(config.l1_ratio_candidates?.includes(1) ?? false).toBe(false);
    const html = renderToStaticMarkup(<RegularizationSettingsPanel config={config} onChange={() => undefined} />);
    expect(html).toContain("regularization-settings");
    expect(html).toContain("<details>");
    expect(html).not.toContain("Alpha to remove");
  });

  it("rejects zero alpha, invalid ratios, non-integer folds and impossible validation", () => {
    const config = regularizationDefaults("elastic_net");
    const fixed = { ...config, regularization: { ...config.regularization, mode: "fixed" as const } };
    expect(regularizationValid({ ...fixed, fixed_alpha: 0 })).toBe(false);
    expect(regularizationValid({ ...fixed, fixed_l1_ratio: 1 })).toBe(false);
    expect(regularizationValid({ ...fixed, fixed_l1_ratio: 0 })).toBe(false);
    expect(regularizationValid({ ...config, regularization: { ...config.regularization, outer_folds: 2.5 } })).toBe(false);
    expect(regularizationValid({ ...config, regularization: { ...config.regularization, validation: "none" } })).toBe(false);
  });

  it("renders English and Korean settings without OLS-only inference controls", () => {
    for (const locale of ["en", "ko"] as const) {
      setCurrentLocale(locale);
      const html = renderToStaticMarkup(<RegularizationSettingsPanel config={regularizationDefaults("elastic_net")} onChange={() => undefined} />);
      expect(html).toContain(locale === "en" ? "L1 Ratio Selection" : "L1 혼합 비율 선택");
      if (locale === "en") expect(html).not.toMatch(/[가-힣]/);
      expect(html).not.toMatch(/confidence.level|p-value|backward/i);
    }
  });

  it("does not advertise classical interval columns for point-only predictions", () => {
    const row = { row_index: 0, predicted_mean: 3, mean_confidence_interval: null,
      prediction_interval: null, warnings: [], predictor_values: { x: 1 } };
    const html = renderToStaticMarkup(<RegressionPredictionResultsTable rows={[row]} />);
    expect(html).not.toContain("평균 신뢰구간");
    expect(html).not.toContain("개별 예측구간");
    expect(html).toContain(">3</td>");
    const ols = renderToStaticMarkup(<RegressionPredictionResultsTable rows={[{ ...row,
      mean_confidence_interval: { level: 0.95, lower: 2, upper: 4, method: "t" },
      prediction_interval: { level: 0.95, lower: 1, upper: 5, method: "t" } }]} />);
    expect(ols).toContain("평균 신뢰구간");
    expect(ols).toContain("개별 예측구간");
  });
});

function regularizedFixture(kind: RegularizedEstimator): RegularizedLinearModelResult {
  const column = { column_id: "x", column_index: 1, display_name: "x", data_type: "decimal" as const,
    measurement_level: "continuous" as const, role: "factor" as const, unit: null };
  const ratio = kind === "elastic_net" ? 0.5 : null;
  return {
    schema_version: 6, summary_type: "linear_model", method: `regularized_${kind}`,
    missing_policy: "complete_case", estimator: { kind, penalty: kind === "ridge" ? "l2" : kind === "lasso" ? "l1" : "elastic_net" },
    response: { ...column, column_id: "y", display_name: "y", column_index: 0, role: "response" },
    predictors: [column], model_specification: { intercept: true, terms: [] },
    sample: { n_total: 5, n_used: 5, n_excluded_missing: 0, n_excluded_non_numeric: 0, feature_count: 1 },
    fit: { r_squared: 0.2, sse: 4, tss: 5, rmse: 0.9, mae: 0.8 },
    coefficients: [{ term: "Intercept", term_kind: "intercept", column_id: null, source_column_ids: [], estimate: 2, standardized_estimate: 2, is_zero: false,
      level: null, reference_level: null, coding: null },
    { term: "x", term_kind: "numeric_main_effect", column_id: "x", source_column_ids: ["x"], estimate: 0,
      standardized_estimate: 0, is_zero: true, level: null, reference_level: null, coding: null }],
    validation: { method: "k_fold", nested: true, outer_folds: 5, inner_folds: 2, shuffle: true,
      random_seed: 7, press: 6, predicted_r_squared: -0.2, rmse: 1.1, mae: 1, row_indices: [0], oof_predictions: [2] },
    regularization: { mode: "automatic_cv", selected_alpha: 0.1, selected_l1_ratio: ratio,
      standardization: "all_design_features_ddof_0_fold_local", response_scale: "original",
      scaler_means: [0], scaler_scales: [1], alpha_min: 0.1, alpha_max: 1, alpha_candidates: 2,
      cv_curve: [0.1, 1].map((alpha) => ({ alpha, l1_ratio: ratio, mean_squared_error: 1, fold_error_sd: 0.1 })),
      coefficient_path: [0.1, 1].map((alpha) => ({ alpha, l1_ratio: ratio, standardized_coefficients: [0] })),
      feature_order: ["x"], zero_coefficient_count: 1, max_iter: 10000, tolerance: 1e-6, converged: true,
      iterations: 5, dual_gap: 0, elapsed_seconds: 0.1, estimated_fit_count: 10, completed_fit_count: 10, time_budget_seconds: 120 },
    diagnostics: { points: [{ row_index: 0, observed: 1, fitted: 2, residual: -1, oof_predicted: 2, oof_residual: -1 }],
      point_count_total: 5, truncated: false, histogram: { bins: [{ lower: -2, upper: 0, count: 5 }] },
      qq_plot: { points: [{ row_index: 0, residual: -1, theoretical_quantile: 0 }] } },
    warnings: ["regularized_model_predictive_not_causal"], package_versions: { numpy: "2.2.6", scipy: "1.15.3" },
  };
}
