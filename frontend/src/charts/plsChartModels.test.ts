import { describe, expect, it } from "vitest";
import type { PlsRegressionResult } from "../api";
import { plsLoadingModel, plsResponseModel, plsScoreModel, plsSelectionModel } from "./plsChartModels";

const latent: PlsRegressionResult["latent_components"] = {
  x_weights: [], y_weights: [], x_loadings: [[-0.5], [0.8]], y_loadings: [], x_rotations: [],
  score_row_indices: [2, 8], x_scores: [[1], [-2]], y_scores: [],
};
describe("PLS stored chart adapters", () => {
  it("keeps training and negative predicted R squared in separate series", () => {
    const rows = [{ components: 1, training_r_squared: 0.8, predicted_r_squared: -0.4, press: 4, cv_rmse: 2, training_sse: 1, x_variance: 0.9, iterations: [1], converged: true }];
    const points = plsSelectionModel({ component_selection: { selected_components: 1, evaluated_components: 1, maximum_allowed_components: 1, tie_tolerance: 1e-9, rows } });
    expect(points.map(({ id, y }) => [id, y])).toEqual([["training:1", 0.8], ["cv:1", -0.4]]);
  });
  it("uses stored row identities and does not fabricate a second score", () => {
    const model = plsScoreModel({ latent_components: latent });
    expect(model.dimensions).toBe(1);
    expect(model.points.map(({ x, y }) => [x, y])).toEqual([[3, 1], [9, -2]]);
    const invalid = plsScoreModel({ latent_components: { ...latent, score_row_indices: [], x_scores: [[1, 2]] } });
    expect(invalid.points[0].x).toBeNaN();
  });
  it("uses column IDs rather than duplicate labels for loading identity", () => {
    const predictors = ["x1", "x2"].map((column_id, column_index) => ({ column_id, column_index, display_name: "same", unit: null,
      data_type: "decimal" as const, measurement_level: "continuous" as const, role: "feature" as const }));
    expect(plsLoadingModel({ predictors, latent_components: latent }, 1)).toEqual([
      { id: "x1", label: "same", value: -0.5 }, { id: "x2", label: "same", value: 0.8 },
    ]);
    expect(plsLoadingModel({ predictors, latent_components: latent }, 2)[0].value).toBeNaN();
  });
  it("preserves stored residuals and distinguishes fitted and OOF rows", () => {
    const points = plsResponseModel({ diagnostics: { point_limit: 10, point_count_total: 1, truncated: false,
      points: [{ row_index: 7, observed: 2, fitted: 1, residual: 0.75, cross_validated_fitted: 3, cross_validated_residual: -0.5 }] } });
    expect(points.map(({ id, residual }) => [id, residual])).toEqual([["fitted:7", 0.75], ["cv:7", -0.5]]);
  });
});
