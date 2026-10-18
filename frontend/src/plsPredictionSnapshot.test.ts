import { describe, expect, it } from "vitest";
import { plsPredictionSnapshot } from "./plsPredictionSnapshot";
import type { PlsPointPredictionResponse } from "./api/types/regression";

describe("PLS separate completed prediction export", () => {
  const request = { expected_model_manifest_sha256: "sha", rows: [{ client_row_id: "row-1", values: { x: 1 } }] };
  const source = { modelId: "model-1", responseColumnId: "y" };
  const response: PlsPointPredictionResponse = { model_id: "model-1", model_manifest_sha256: "sha", response_column_id: "y", row_count: 1, intervals_supported: false, rows: [{ client_row_id: "row-1", predicted_value: 3.25, warnings: [] }] };
  it("preserves inputs and completed values without recalculation or original analysis mutation", () => {
    const snapshot = plsPredictionSnapshot("analysis-1", request, response, "2026-09-17T00:00:00Z", source);
    expect(snapshot.source_analysis_id).toBe("analysis-1");
    expect(snapshot.response.rows[0].predicted_value).toBe(3.25);
    expect(snapshot.prediction_recalculated_on_export).toBe(false);
    expect(snapshot.client_received_at).toBe("2026-09-17T00:00:00Z");
    const restored = JSON.parse(JSON.stringify(snapshot)) as typeof snapshot;
    expect(restored.request).toEqual(request);
  });
  it("rejects a result from another request", () => {
    expect(() => plsPredictionSnapshot("analysis-1", request, { ...response, model_manifest_sha256: "other" }, "now", source)).toThrow("pls_prediction_snapshot_mismatch");
  });
  it.each([
    { model_id: "other" }, { response_column_id: "other" }, { row_count: 2 },
    { rows: [{ ...response.rows[0], client_row_id: "foreign" }] },
    { rows: [{ ...response.rows[0], predicted_value: NaN }] },
    { rows: [{ ...response.rows[0], predicted_value: Infinity }] },
    { rows: [] },
  ])("rejects wrong provenance, row identity, or values %s", (change) => {
    expect(() => plsPredictionSnapshot("analysis-1", request, { ...response, ...change }, "now", source)).toThrow("pls_prediction_snapshot_mismatch");
  });
  it("accepts shuffled rows by ID and detaches saved input/warnings", () => {
    const originalRequest = { ...request, rows: [...request.rows.map((row) => ({ ...row, values: { ...row.values } })), { client_row_id: "row-2", values: { x: 2 } }] };
    const originalResponse = { ...response, row_count: 2, rows: [{ client_row_id: "row-2", predicted_value: 8.5, warnings: ["unknown_warning"] }, { ...response.rows[0], warnings: [...response.rows[0].warnings] }] };
    const snapshot = plsPredictionSnapshot("analysis-1", originalRequest, originalResponse, "now", source);
    expect(snapshot.response.rows.map((row) => [row.client_row_id, row.predicted_value])).toEqual([["row-2", 8.5], ["row-1", 3.25]]);
    originalResponse.rows[0].warnings.push("changed"); originalRequest.rows[0].values.x = 999;
    expect(snapshot.response.rows[0].warnings).toEqual(["unknown_warning"]);
    expect(snapshot.request.rows[0].values.x).toBe(1);
    expect(() => plsPredictionSnapshot("analysis-1", originalRequest, { ...originalResponse, rows: [originalResponse.rows[0], originalResponse.rows[0]] }, "now", source)).toThrow("pls_prediction_snapshot_mismatch");
  });
});
