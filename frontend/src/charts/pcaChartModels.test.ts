import { describe, expect, it } from "vitest";
import { availablePcaComponents, pcaBiplotModel, pcaLoadingModel, pcaOutlierModel, pcaScoreModel, pcaSymmetricRange, validPcaPair } from "./pcaChartModels";

function fixture(dimensions = 2) {
  return {
    eigenanalysis: [1, 2].map((component) => ({ component, eigenvalue: 3 - component, proportion: component === 1 ? 0.8 : 0.2, cumulative_proportion: component === 1 ? 0.8 : 1, selected: component === 1 })),
    loadings: [{ column_id: "x1", display_name: "Duplicate", values: [0.4, -0.3].slice(0, dimensions) }, { column_id: "x2", display_name: "Duplicate", values: [0.5, 0.2].slice(0, dimensions) }],
    plot: { point_limit: 2, point_count: 2, sampled: true, sampling_policy: "stored",
      points: [2, 17].map((source_row_number, index) => ({ source_row_number, scores: [index ? 2 : -2, index ? 0.5 : -0.5].slice(0, dimensions), mahalanobis_distance_squared: index ? 7 : 1, outlier: index === 1 })) },
    outliers: { alpha: 0.05, method: "chi_square", degrees_of_freedom: dimensions, reference_value: 5.99, count: 1 },
  };
}

describe("saved PCA chart adapters", () => {
  it("uses stored dimensions, not eigenanalysis count or selected component count", () => {
    expect(availablePcaComponents(fixture())).toEqual([1, 2]);
    expect(availablePcaComponents(fixture(1))).toEqual([1]);
    expect(validPcaPair([1], 2, 3)).toEqual({ x: 1, y: null });
    expect(validPcaPair([1, 2, 3], 3, 2)).toEqual({ x: 3, y: 2 });
  });
  it("represents one component against actual saved row numbers without fake PC2", () => {
    const points = pcaScoreModel(fixture(1), 1, null);
    expect(points.map((point) => [point.id, point.x, point.y])).toEqual([["row:2", 2, -2], ["row:17", 17, 2]]);
  });
  it("keeps source row gaps and D squared without changing reference values", () => {
    const result = fixture();
    const before = JSON.stringify(result);
    expect(pcaOutlierModel(result).map((point) => [point.x, point.y])).toEqual([[2, 1], [17, 7]]);
    expect(JSON.stringify(result)).toBe(before);
  });
  it("separates raw loadings from their established display multiplier", () => {
    const model = pcaBiplotModel(fixture(), 1, 2);
    expect(model.loadingDisplayScale).toBeCloseTo(2 * 1.08, 12);
    expect(model.rawLoadingVectors[0]).toMatchObject({ id: "variable:x1", x: 0.4, y: -0.3 });
    expect(model.displayedLoadingVectors[0].x).toBeCloseTo(0.4 * 2 * 1.08, 12);
    expect(pcaLoadingModel(fixture(), 1, 2).map((point) => point.id)).toEqual(["variable:x1", "variable:x2"]);
    expect(pcaSymmetricRange([-3, 1])).toEqual({ min: -3.24, max: 3.24 });
  });
});
