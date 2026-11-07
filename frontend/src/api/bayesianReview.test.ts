import { afterEach, describe, expect, it, vi } from "vitest";
import { confirmBayesianRecommendationReview, createBayesianRecommendationReview } from "./bayesian";
import type { BayesianKernelBatchCreateRequest, BayesianNoiseBatchCreateRequest } from "./types";
import { apiRoutes } from "./routes";

describe("BO review transport", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("encodes owners and separates review generation from confirmation", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ review_id: "review-1" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const body = { schema_version: 2, expected_history_sha256: "a".repeat(64) } as BayesianNoiseBatchCreateRequest;
    await createBayesianRecommendationReview("study/1", body);
    expect(fetchMock).toHaveBeenCalledExactlyOnceWith("/api/v1/bayesian-studies/study%2F1/recommendation-reviews",
      expect.objectContaining({ method: "POST", body: JSON.stringify(body) }));
    expect(apiRoutes.bayesianRecommendationReviewConfirm("study/1", "review?2")).toBe(
      "/api/v1/bayesian-studies/study%2F1/recommendation-reviews/review%3F2/confirm",
    );
  });

  it("sends only the exact review hash once, without automatic network retry", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("network failure"));
    vi.stubGlobal("fetch", fetchMock);
    const body = { expected_config_sha256: "b".repeat(64) };
    await expect(confirmBayesianRecommendationReview("study-1", "review-1", body)).rejects.toThrow();
    expect(fetchMock).toHaveBeenCalledExactlyOnceWith("/api/v1/bayesian-studies/study-1/recommendation-reviews/review-1/confirm",
      expect.objectContaining({ method: "POST", body: JSON.stringify(body) }));
  });

  it.each(["matern_5_2", "matern_3_2", "gaussian", "exponential"] as const)("transmits schema3 %s without rewriting its configuration", async kind => {
    const response = { schema_version: 1, review_id: "review-3", calculation: { schema_version: 3, shared_model: { schema_version: 4, signal_kernel: { family: kind } } } };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(response), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const body = { schema_version: 3, kernel: { kind }, expected_history_sha256: "d".repeat(64) } as BayesianKernelBatchCreateRequest;
    const before = JSON.stringify(body);
    expect(await createBayesianRecommendationReview("study", body)).toEqual(response);
    expect(fetchMock).toHaveBeenCalledExactlyOnceWith("/api/v1/bayesian-studies/study/recommendation-reviews",
      expect.objectContaining({ body: before }));
    expect(JSON.stringify(body)).toBe(before);
  });

  it.each([2, 3] as const)("keeps schema%s confirmed results unchanged", async schema => {
    const response = { result_schema_version: schema, model_schema_version: schema + 1, source_observation_history_sha256: "a".repeat(64) };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(response), { status: 200 })));
    expect(await confirmBayesianRecommendationReview("study", "review", { expected_config_sha256: "c".repeat(64) })).toEqual(response);
  });
});
