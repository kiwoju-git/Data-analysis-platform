import { describe, expect, expectTypeOf, it } from "vitest";
import type { GaussianProcessPointPredictionResponse } from "./api/types/regression";
import {
  captureGpPredictionRequest,
  completeGpPredictionSnapshot,
  gpPredictionSourceKey,
  type GpPredictionDraftRow,
  type GpPredictionSource,
} from "./gpPredictionSnapshot";

function source(): GpPredictionSource {
  return { analysisId: "analysis-A", modelId: "model-A", manifestSha256: "a".repeat(64), responseColumnId: "y", predictorColumnIds: ["x1", "x2"] };
}
function drafts(): GpPredictionDraftRow[] {
  return [
    { id: "r1", values: { x1: "0", x2: "-2" } },
    { id: "r2", values: { x1: " 1.25 ", x2: "2e1" } },
    { id: "r3", values: { x1: "3", x2: "4" } },
  ];
}
function response(): GaussianProcessPointPredictionResponse {
  return { model_id: "model-A", model_manifest_sha256: "a".repeat(64), response_column_id: "y", row_count: 3, interval_kind: "latent_and_new_observation", confidence_level: .95,
    rows: [["r3", 303], ["r1", 101], ["r2", 202]].map(([id, value]) => {
      const mean = Number(value);
      return { client_row_id: String(id), predicted_mean: mean, latent_standard_deviation: .5, latent_interval_95: { lower: mean - 1, upper: mean + 1 }, predictive_standard_deviation: 1, predictive_interval_95: { lower: mean - 2, upper: mean + 2 }, warnings: ["gp_extrapolation"] };
    }) };
}
const receivedAt = "2026-10-18T04:00:00.000Z";

describe("GP completed prediction snapshot", () => {
  it("captures exact numeric request values with detached source and inputs", () => {
    const originalSource = source(); const originalDrafts = drafts();
    const captured = captureGpPredictionRequest(originalSource, originalDrafts);
    expect(captured.request).toEqual({ expected_model_manifest_sha256: "a".repeat(64), rows: [
      { client_row_id: "r1", values: { x1: 0, x2: -2 } },
      { client_row_id: "r2", values: { x1: 1.25, x2: 20 } },
      { client_row_id: "r3", values: { x1: 3, x2: 4 } },
    ] });
    (originalSource.predictorColumnIds as string[])[0] = "changed";
    (originalDrafts[0].values as Record<string, string>).x1 = "999";
    expect(captured.source.predictorColumnIds).toEqual(["x1", "x2"]);
    expect(captured.request.rows[0].values.x1).toBe(0);
  });

  it("validates shuffled rows by independent IDs without recomputing stored intervals", () => {
    const captured = captureGpPredictionRequest(source(), drafts()); const originalResponse = response();
    const completed = completeGpPredictionSnapshot(captured, originalResponse, receivedAt);
    const byId = new Map(completed.response.rows.map((row) => [row.client_row_id, row]));
    expect([byId.get("r1")?.predicted_mean, byId.get("r2")?.predicted_mean, byId.get("r3")?.predicted_mean]).toEqual([101, 202, 303]);
    expect(byId.get("r1")?.latent_interval_95).toEqual({ lower: 100, upper: 102 });
    expect(byId.get("r1")?.predictive_interval_95).toEqual({ lower: 99, upper: 103 });
    expect(completed.response).toEqual(originalResponse);
    expect(completed.response.rows.map((row) => row.client_row_id)).toEqual(["r3", "r1", "r2"]);
    expect(completed.schema_version).toBe(1);
    expect(completed.artifact_kind).toBe("gaussian_process_point_prediction_snapshot");
    expect(completed.source_analysis_id).toBe("analysis-A");
    expect(completed.predictor_column_ids).toEqual(["x1", "x2"]);
    expect(completed.client_received_at).toBe(receivedAt);
    expect(completed.prediction_recalculated_on_export).toBe(false);
    expectTypeOf(completed.schema_version).toEqualTypeOf<1>();
    expectTypeOf(completed.prediction_recalculated_on_export).toEqualTypeOf<false>();
    expect(JSON.parse(JSON.stringify(completed))).toEqual(completed);
  });

  it("detaches response intervals and warnings, and the exported request", () => {
    const captured = captureGpPredictionRequest(source(), drafts()); const original = response();
    const completed = completeGpPredictionSnapshot(captured, original, receivedAt);
    original.rows[0].latent_interval_95.lower = -999;
    original.rows[0].predictive_interval_95.upper = 999;
    original.rows[0].warnings.push("changed");
    captured.request.rows[0].values.x1 = 999;
    (captured.source.predictorColumnIds as string[])[0] = "changed";
    expect(completed.response.rows[0].latent_interval_95.lower).toBe(302);
    expect(completed.response.rows[0].predictive_interval_95.upper).toBe(305);
    expect(completed.response.rows[0].warnings).toEqual(["gp_extrapolation"]);
    expect(completed.request.rows[0].values.x1).toBe(0);
    expect(completed.predictor_column_ids).toEqual(["x1", "x2"]);
  });

  it("preserves valid zero uncertainty and private-use marker strings", () => {
    const marker = 'quoted"\\\n\uE000gp.predictiveSd\uE001';
    const captured = captureGpPredictionRequest({ ...source(), predictorColumnIds: [marker] }, [{ id: "__proto__", values: { [marker]: "0" } }]);
    const original = { ...response(), row_count: 1, rows: [{ client_row_id: "__proto__", predicted_mean: 0, latent_standard_deviation: 0, predictive_standard_deviation: 0, latent_interval_95: { lower: 0, upper: 0 }, predictive_interval_95: { lower: 0, upper: 0 }, warnings: [marker, "unknown_future_warning"] }] };
    const completed = completeGpPredictionSnapshot(captured, original, receivedAt);
    expect(completed.response).toEqual(original);
    expect(Object.keys(completed.request.rows[0].values)).toEqual([marker]);
  });

  it.each([
    ["wrong model", { model_id: "foreign" }],
    ["wrong hash", { model_manifest_sha256: "b".repeat(64) }],
    ["wrong response", { response_column_id: "other" }],
    ["wrong count", { row_count: 2 }],
    ["string count", { row_count: "3" }],
    ["wrong interval", { interval_kind: "mean_ci" }],
    ["wrong confidence", { confidence_level: .9 }],
    ["missing rows", { rows: undefined }],
  ])("rejects %s before any completed snapshot exists", (_label, change) => {
    expect(() => completeGpPredictionSnapshot(captureGpPredictionRequest(source(), drafts()), { ...response(), ...change }, receivedAt)).toThrow("gp_prediction_response_invalid");
  });

  it.each(["duplicate", "missing", "extra", "unknown"])("rejects %s response row IDs", (corruption) => {
    const original = response();
    if (corruption === "duplicate") original.rows[0].client_row_id = original.rows[1].client_row_id;
    if (corruption === "missing") original.rows.pop();
    if (corruption === "extra") original.rows.push({ ...original.rows[0], client_row_id: "extra" });
    if (corruption === "unknown") original.rows[0].client_row_id = "unknown";
    expect(() => completeGpPredictionSnapshot(captureGpPredictionRequest(source(), drafts()), original, receivedAt)).toThrow("gp_prediction_response_invalid");
  });

  it.each([
    ["null mean", { predicted_mean: null }],
    ["string mean", { predicted_mean: "101" }],
    ["NaN mean", { predicted_mean: NaN }],
    ["infinite mean", { predicted_mean: Infinity }],
    ["negative latent SD", { latent_standard_deviation: -1 }],
    ["nonfinite predictive SD", { predictive_standard_deviation: Infinity }],
    ["missing interval", { latent_interval_95: null }],
    ["inverted interval", { latent_interval_95: { lower: 3, upper: 2 } }],
    ["nonfinite endpoint", { predictive_interval_95: { lower: 1, upper: NaN } }],
    ["string endpoint", { predictive_interval_95: { lower: "1", upper: 2 } }],
    ["missing warnings", { warnings: undefined }],
    ["nonstring warning", { warnings: [false] }],
  ])("rejects %s without converting it into a display value", (_label, change) => {
    const original = response();
    const malformed = { ...original, rows: [{ ...original.rows[0], ...change }, ...original.rows.slice(1)] };
    expect(() => completeGpPredictionSnapshot(captureGpPredictionRequest(source(), drafts()), malformed, receivedAt)).toThrow("gp_prediction_response_invalid");
  });

  it.each([null, undefined, false, "result", [], 1])("rejects a non-response value %s", (value) => {
    expect(() => completeGpPredictionSnapshot(captureGpPredictionRequest(source(), drafts()), value, receivedAt)).toThrow("gp_prediction_response_invalid");
  });

  it.each(["", " ", "NaN", "Infinity", "-Infinity", "invalid"])("rejects invalid draft value %s without changing the input", (value) => {
    const input = [{ id: "r1", values: { x1: value, x2: "2" } }];
    const before = JSON.stringify(input);
    expect(() => captureGpPredictionRequest(source(), input)).toThrow("gp_prediction_input_invalid");
    expect(JSON.stringify(input)).toBe(before);
  });

  it("enforces the existing 2000-row boundary and unique IDs", () => {
    const rows = Array.from({ length: 2000 }, (_, index) => ({ id: `r${index}`, values: { x1: "1", x2: "2" } }));
    expect(captureGpPredictionRequest(source(), rows).request.rows).toHaveLength(2000);
    expect(() => captureGpPredictionRequest(source(), [...rows, { ...rows[0], id: "extra" }])).toThrow("gp_prediction_input_invalid");
    expect(() => captureGpPredictionRequest(source(), [rows[0], rows[0]])).toThrow("gp_prediction_input_invalid");
    expect(() => captureGpPredictionRequest(source(), [])).toThrow("gp_prediction_input_invalid");
  });

  it("rejects missing/extra predictor mappings and duplicate source IDs", () => {
    expect(() => captureGpPredictionRequest(source(), [{ id: "r1", values: { x1: "1" } }])).toThrow("gp_prediction_input_invalid");
    expect(() => captureGpPredictionRequest(source(), [{ id: "r1", values: { x1: "1", x2: "2", extra: "3" } }])).toThrow("gp_prediction_input_invalid");
    expect(() => captureGpPredictionRequest({ ...source(), predictorColumnIds: ["x1", "x1"] }, drafts())).toThrow("gp_model_manifest_invalid");
  });

  it("uses structural source identity without delimiter collisions", () => {
    const a = { ...source(), analysisId: "analysis:model", modelId: "rest" };
    const b = { ...source(), analysisId: "analysis", modelId: "model:rest" };
    expect(gpPredictionSourceKey(a)).not.toBe(gpPredictionSourceKey(b));
    expect(gpPredictionSourceKey(source())).toBe(gpPredictionSourceKey({ ...source() }));
    expect(gpPredictionSourceKey(source())).not.toBe(gpPredictionSourceKey({ ...source(), predictorColumnIds: ["x2", "x1"] }));
  });
});
