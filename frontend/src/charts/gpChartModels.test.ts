import { describe, expect, it } from "vitest";
import type { GaussianProcessPointPredictionResponse, GaussianProcessRegressionResult } from "../api";
import { gpResidualModel, gpScatterModel, gpSurfaceRequest, gpUncertaintyModel, joinGpSurfaceRows, type GpSurfaceRequestSnapshot } from "./gpChartModels";

const snapshot: GpSurfaceRequestSnapshot = {
  modelId: "model", manifestHash: "hash", responseId: "y", xColumnId: "x1", yColumnId: "x2",
  xName: "Temperature", yName: "Pressure", gridSize: 2, fixedValues: [0, 0],
  rows: [{ client_row_id: "a", values: { x1: 10, x2: 1 } }, { client_row_id: "b", values: { x1: 20, x2: 2 } }],
};
function response(): GaussianProcessPointPredictionResponse {
  return { model_id: "model", model_manifest_sha256: "hash", response_column_id: "y", row_count: 2,
    interval_kind: "latent_and_new_observation", confidence_level: 0.95,
    rows: ["b", "a"].map((client_row_id, i) => ({ client_row_id, predicted_mean: 100 + i,
      latent_standard_deviation: 0.1, predictive_standard_deviation: 0.3,
      latent_interval_95: { lower: 99, upper: 102 }, predictive_interval_95: { lower: 98, upper: 103 }, warnings: [] })) };
}
describe("GP stored chart adapters", () => {
  it("uses numeric axes and exact category/numeric held values without mutating result", () => {
    const result = { response: { column_id: "y" }, model_manifest: { model_id: "m", manifest_sha256: "h" }, two_predictor_surface: { grid_size: 2 }, training_ranges: [
      { column_id: "category", display_name: "Category", kind: "nominal", levels: ["01", "1"], mode: "01" },
      { column_id: "x", display_name: "X", minimum: 0, maximum: 1, median: .5 },
      { column_id: "z", display_name: "Z", minimum: 10, maximum: 20, median: 15 },
    ] } as GaussianProcessRegressionResult;
    const before = JSON.stringify(result);
    const captured = gpSurfaceRequest(result, "x", "z", { category: "1" });
    expect(captured?.rows[0].values).toEqual({ category: "1", x: 0, z: 10 });
    expect(captured?.fixedValues).toEqual(["1", .5, 15]);
    expect(gpSurfaceRequest(result, "category", "x")).toBeNull();
    expect(gpSurfaceRequest(result, "x", "z", { category: "unknown" })).toBeNull();
    expect(JSON.stringify(result)).toBe(before);
  });
  it("joins shuffled prediction responses by client ID and snapshot axis names", () => {
    const surface = joinGpSurfaceRows(snapshot, response());
    expect(surface.points.map(({ x, y, predicted_mean }) => [x, y, predicted_mean])).toEqual([[10, 1, 101], [20, 2, 100]]);
    expect(surface.x_display_name).toBe("Temperature");
  });
  it("rejects duplicate, unknown, missing and wrong-source responses", () => {
    for (const mutate of [
      (r: GaussianProcessPointPredictionResponse) => { r.rows[1].client_row_id = "b"; },
      (r: GaussianProcessPointPredictionResponse) => { r.rows[1].client_row_id = "other"; },
      (r: GaussianProcessPointPredictionResponse) => { r.rows.pop(); },
      (r: GaussianProcessPointPredictionResponse) => { r.model_manifest_sha256 = "stale"; },
      (r: GaussianProcessPointPredictionResponse) => { r.rows[0].predicted_mean = Infinity; },
    ]) { const value = response(); mutate(value); expect(() => joinGpSurfaceRows(snapshot, value)).toThrow("gp_surface_response_invalid"); }
  });
  it("uses stored residuals, real row gaps and observation rather than latent SD", () => {
    const point = { row_index: 8, observed: 2, fitted: 1, residual: 0.75, latent_standard_deviation: 0.1,
      predictive_standard_deviation: 0.4, standardized_predictive_residual: 1.5, cross_validated_fitted: null,
      cross_validated_residual: null, cross_validated_predictive_standard_deviation: null };
    const source = { diagnostics: { points: [point] } } as Pick<GaussianProcessRegressionResult, "diagnostics">;
    expect(gpScatterModel(source, "cv")).toEqual([]);
    expect(gpResidualModel(source)[0].y).toBe(0.75);
    expect(gpUncertaintyModel(source)[0]).toEqual({ id: "row:8", x: 9, y: 0.4 });
  });
});
