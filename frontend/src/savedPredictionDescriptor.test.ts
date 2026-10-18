import { describe, expect, it } from "vitest";
import { savedPredictionDescriptor } from "./savedPredictionDescriptor";
import { plsPredictionSnapshot } from "./plsPredictionSnapshot";
import type { SavedPredictionDescriptor } from "./api/types/reports";

const expected = { saveResult: true, family: "pls" as const, analysisId: "analysis-A", modelId: "model-A", manifestSha256: "a".repeat(64) };
const saved: SavedPredictionDescriptor = { source: { kind: "regression_prediction", prediction: {
  storage: "completed_prediction", family: "pls", source_analysis_id: "analysis-A", source_result_sha256: "b".repeat(64),
  model_id: "model-A", model_manifest_sha256: "a".repeat(64), prediction_artifact_id: "10000000-0000-4000-8000-000000000001", expected_source_sha256: "c".repeat(64),
} }, created_at: "2026-10-18T04:00:00Z" };

describe("completed prediction persistence descriptor", () => {
  it("accepts only an explicitly requested, exact server-owned descriptor and detaches it", () => {
    const result = savedPredictionDescriptor(saved, expected);
    expect(result).toEqual(saved);
    expect(result?.source).not.toBe(saved.source);
    expect(savedPredictionDescriptor(null, { ...expected, saveResult: false })).toBeNull();
    expect(() => savedPredictionDescriptor(saved, { ...expected, saveResult: false })).toThrow("prediction_saved_result_invalid");
    expect(() => savedPredictionDescriptor(null, expected)).toThrow("prediction_saved_result_invalid");
  });
  it.each(["family", "modelId", "analysisId", "manifestSha256"] as const)("rejects a foreign %s", (field) => {
    expect(() => savedPredictionDescriptor(saved, { ...expected, [field]: field === "family" ? "gaussian_process" : "other" })).toThrow("prediction_saved_result_invalid");
  });
  it("retains the PLS point-only result and explicit save flag in a separate local snapshot", () => {
    const request = { expected_model_manifest_sha256: expected.manifestSha256, save_result: true, rows: [{ client_row_id: "r1", values: { x: 2 } }] };
    const response = { model_id: expected.modelId, model_manifest_sha256: expected.manifestSha256, response_column_id: "y", row_count: 1, intervals_supported: false as const, rows: [{ client_row_id: "r1", predicted_value: 4.5, warnings: ["\uE000user-value\uE001"] }], saved_prediction: saved };
    const result = plsPredictionSnapshot(expected.analysisId, request, response, saved.created_at, { modelId: expected.modelId, responseColumnId: "y" });
    expect(result.request.save_result).toBe(true);
    expect(result.response).toEqual(response);
    expect(result.response.saved_prediction).not.toBe(saved);
    expect(result.prediction_recalculated_on_export).toBe(false);
    expect(result.response.rows[0]).not.toHaveProperty("prediction_interval");
  });
});
