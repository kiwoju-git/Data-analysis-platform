import { describe, expect, it, vi, afterEach } from "vitest";
import { evaluateBoView, saveBoView, type BoViewReceipt } from "../../api/boViews";
import { matrixFromReceipt, validBoViewReceipt } from "./boSavedViews";
import { viewSource, viewRequest, receiptFixture } from "./boSavedViews.test.fixture";
const expected = { studyId: "study", modelId: "model", modelHash: viewSource.model_sha256, historyHash: viewSource.history_sha256, responseIds: ["desirability"], factorIds: ["x", "category"] };

afterEach(() => vi.unstubAllGlobals());
describe("server-owned exact diagnostic receipt", () => {
  it("preserves a mixture co-varying axis and an explicitly unavailable fixed component", () => {
    const receipt = receiptFixture();
    if (receipt.payload.kind !== "profiler_matrix") throw Error("fixture");
    const payload = receipt.payload;
    Object.assign(payload, { schema_version: 2, policy: "source_locked_mixture_profiler_matrix_v1", mixture_domain: { policy: "stored-mixture" }, point_count: 2 });
    Object.assign(payload.axes[0], { kind: "mixture_component", path: { policy: "excess_above_lower", feasible_interval: [0, 1], unavailable_reason: null } });
    Object.assign(payload.axes[1], { kind: "mixture_component", available_level_count: null, points: [], path: { policy: "excess_above_lower", feasible_interval: null, unavailable_reason: "fixed_component" } });
    expect(validBoViewReceipt(receipt, expected, viewRequest)).toBe(true);
    const matrix = matrixFromReceipt(receipt);
    expect(matrix.axes[1]).toMatchObject({ unavailableReason: "fixed_component", rows: [] });
    expect(matrix.axes[0]).toMatchObject({ pathPolicy: "excess_above_lower" });
    Object.assign(payload.axes[1], { path: null });
    expect(validBoViewReceipt(receipt, expected, viewRequest)).toBe(false);
  });
  it("preserves original Unicode, small numbers, fixed constraints and all factor/response axes", () => {
    const receipt = receiptFixture(), before = JSON.stringify(receipt);
    expect(validBoViewReceipt(receipt, expected, viewRequest)).toBe(true);
    const matrix = matrixFromReceipt(receipt);
    expect(matrix.responses[0].name).toBe("실제 반응");
    expect(matrix.axes.map(axis => axis.category)).toEqual([false, true]);
    expect(matrix.axes[0].rows[0].response_predictions[0].mean_raw).toBe(1e-6);
    expect(matrix.axes[0].rows[0].constraints_satisfied).toBe(false);
    expect(JSON.stringify(receipt)).toBe(before);
  });
  it("rejects wrong owner/hash/holds/incomplete axes/prediction source without fabricating a graph", () => {
    for (const mutate of [
      (r: BoViewReceipt) => { r.payload.source.model_sha256 = "0".repeat(64); },
      (r: BoViewReceipt) => { r.payload.source.study_id = "other"; },
      (r: BoViewReceipt) => { if (r.payload.kind === "profiler_matrix") r.payload.holds.x = 8; },
      (r: BoViewReceipt) => { if (r.payload.kind === "profiler_matrix") r.payload.axes.pop(); },
      (r: BoViewReceipt) => { if (r.payload.kind === "profiler_matrix") Object.assign(r.payload.axes[0].points[0], { prediction_source: "fantasy" }); },
    ]) {
      const value = structuredClone(receiptFixture()); mutate(value);
      expect(validBoViewReceipt(value, expected, viewRequest)).toBe(false);
    }
  });
  it("transports save identity only, never rendered points or translated data", async () => {
    const receipt = receiptFixture(), fetch = vi.fn<typeof globalThis.fetch>().mockResolvedValue(new Response(JSON.stringify(receipt))); vi.stubGlobal("fetch", fetch);
    fetch.mockImplementation(() => Promise.resolve(new Response(JSON.stringify(receipt))));
    await evaluateBoView("study", "model", viewRequest);
    const body = { request_id: "request", receipt_id: receipt.receipt_id, expected_model_sha256: viewSource.model_sha256, expected_request_sha256: receipt.request_sha256, expected_view_sha256: receipt.view_sha256 };
    await saveBoView("study", body);
    const savedBody = fetch.mock.calls[1][1]?.body;
    const evaluatedBody = fetch.mock.calls[0][1]?.body;
    if (typeof savedBody !== "string" || typeof evaluatedBody !== "string") throw new Error("Expected JSON string request bodies");
    expect(JSON.parse(savedBody)).toEqual(body);
    expect(savedBody).not.toContain("response_predictions");
    expect(JSON.parse(evaluatedBody)).toEqual(viewRequest);
  });
});
