import { describe, expect, it } from "vitest";
import { plsPredictionSnapshot } from "./plsPredictionSnapshot";
import type { PlsPointPredictionResponse } from "./api/types/regression";

describe("PLS separate completed prediction export", () => {
  const request = { expected_model_manifest_sha256: "sha", rows: [{ client_row_id: "row-1", values: { x: 1 } }] };
  const response: PlsPointPredictionResponse = { model_id: "model-1", model_manifest_sha256: "sha", response_column_id: "y", row_count: 1, intervals_supported: false, rows: [{ client_row_id: "row-1", predicted_value: 3.25, warnings: [] }] };
  it("preserves inputs and completed values without recalculation or original analysis mutation", () => {
    const snapshot = plsPredictionSnapshot("analysis-1", request, response, "2026-09-17T00:00:00Z");
    expect(snapshot.source_analysis_id).toBe("analysis-1");
    expect(snapshot.response.rows[0].predicted_value).toBe(3.25);
    expect(snapshot.prediction_recalculated_on_export).toBe(false);
    expect(snapshot.client_received_at).toBe("2026-09-17T00:00:00Z");
    const restored = JSON.parse(JSON.stringify(snapshot)) as typeof snapshot;
    expect(restored.request).toEqual(request);
  });
  it("rejects a result from another request", () => {
    expect(() => plsPredictionSnapshot("analysis-1", request, { ...response, model_manifest_sha256: "other" }, "now")).toThrow("pls_prediction_snapshot_mismatch");
  });
});
