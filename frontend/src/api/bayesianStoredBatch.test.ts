import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchBayesianRecommendationBatch, fetchLatestBayesianRecommendationBatch } from "./bayesian";
import { desirabilityBatchFixture, desirabilityFixture } from "../features/bayesian/bayesianDesirability.fixture";

describe("generic stored Bayesian batch reads", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("keeps every schema5 item and partial overlay on generic exact/latest reads", async () => {
    const { batch } = desirabilityBatchFixture(); batch.batch_state = "partially_completed";
    batch.items[1].current_trial.state = "completed";
    batch.items[1].current_trial.response_values = { yield: 43, cost: 3 };
    const fetch = vi.fn<typeof globalThis.fetch>().mockResolvedValueOnce(new Response(JSON.stringify(batch)))
      .mockResolvedValueOnce(new Response(JSON.stringify({ item: batch })));
    vi.stubGlobal("fetch", fetch);
    expect(await fetchBayesianRecommendationBatch(batch.study_id, batch.batch_id)).toEqual(batch);
    expect(await fetchLatestBayesianRecommendationBatch(batch.study_id)).toEqual({ item: batch });
    expect(batch.items[1].trial.state).toBe("pending");
    expect(fetch.mock.calls.every(([, init]) => init?.body === undefined)).toBe(true);
  });

  it("preserves a vector result and its dynamic current-trial overlay without pretending it is scalar", async () => {
    const { batch } = desirabilityFixture();
    batch.batch_state = "completed";
    batch.items[0].current_trial = {
      ...batch.items[0].trial, state: "completed", closed_at: "2026-11-08T01:00:00Z",
      response_values: Object.fromEntries(batch.calculation.shared_model.response_ids.map((id, index) => [id, index + 1])),
    };
    const latest = { study_id: batch.study_id, study_version_id: batch.study_version_id, item: batch };
    const fetch = vi.fn<typeof globalThis.fetch>().mockResolvedValueOnce(new Response(JSON.stringify(batch)))
      .mockResolvedValueOnce(new Response(JSON.stringify(latest)));
    vi.stubGlobal("fetch", fetch);
    const exact = await fetchBayesianRecommendationBatch(batch.study_id, batch.batch_id);
    expect(exact).toEqual(batch);
    if (exact.result_schema_version !== 4) throw new Error("Expected vector response");
    expect(exact.calculation).toEqual(batch.calculation);
    expect(exact.items[0].current_trial).toEqual(batch.items[0].current_trial);
    expect(exact.items[0].trial.state).toBe("pending");
    expect(exact.result_sha256).toBe(batch.result_sha256);
    expect(await fetchLatestBayesianRecommendationBatch(batch.study_id)).toEqual(latest);
    expect(fetch.mock.calls.every(([, init]) => init?.method === undefined && init?.body === undefined)).toBe(true);
  });
});
