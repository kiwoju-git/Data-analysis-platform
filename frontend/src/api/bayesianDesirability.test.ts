import { afterEach, describe, expect, it, vi } from "vitest";
import { createDesirabilityReview, confirmDesirabilityReview, fetchDesirabilityBatch, fetchLatestDesirabilityBatch } from "./bayesianDesirability";
import { buildDesirabilityRequest, defaultDesirabilityDraft } from "../features/bayesian/bayesianDesirabilityDraft";
import { desirabilityFixture } from "../features/bayesian/bayesianDesirability.fixture";

describe("source-locked multiresponse transport", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("separates read-only review and confirmation, preserving the JSON body", async () => {
    const { study, review } = desirabilityFixture(); const request = buildDesirabilityRequest(study, defaultDesirabilityDraft(study)).request!;
    const fetch = vi.fn<typeof globalThis.fetch>().mockResolvedValue(new Response(JSON.stringify(review)));
    vi.stubGlobal("fetch", fetch);
    await createDesirabilityReview("owner/1", request);
    expect(fetch).toHaveBeenCalledExactlyOnceWith("/api/v1/bayesian-studies/owner%2F1/desirability-reviews", expect.objectContaining({ method: "POST", body: JSON.stringify(request) }));
    fetch.mockReset().mockRejectedValue(new TypeError("network"));
    await expect(confirmDesirabilityReview("owner/1", "review?2", "f".repeat(64))).rejects.toThrow();
    expect(fetch).toHaveBeenCalledExactlyOnceWith("/api/v1/bayesian-studies/owner%2F1/desirability-reviews/review%3F2/confirm", expect.objectContaining({ method: "POST", body: JSON.stringify({ expected_config_sha256: "f".repeat(64) }) }));
  });
  it("restores the exact saved ID without a POST or latest fallback", async () => {
    const { batch } = desirabilityFixture(); const fetch = vi.fn<typeof globalThis.fetch>().mockResolvedValueOnce(new Response(JSON.stringify(batch))).mockResolvedValueOnce(new Response(JSON.stringify({ item: null })));
    vi.stubGlobal("fetch", fetch);
    expect(await fetchDesirabilityBatch("owner", "batch/1")).toEqual(batch);
    expect(await fetchLatestDesirabilityBatch("owner")).toEqual({ item: null });
    expect(fetch.mock.calls[0][0]).toBe("/api/v1/bayesian-studies/owner/desirability-recommendations/batch%2F1");
    expect(fetch.mock.calls[1][0]).toBe("/api/v1/bayesian-studies/owner/desirability-recommendations/latest");
    expect(fetch.mock.calls.every(([, init]) => init?.method === undefined && init?.body === undefined)).toBe(true);
  });
});
