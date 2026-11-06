import { afterEach, describe, expect, it, vi } from "vitest";
import { confirmBayesianRecommendationReview, createBayesianRecommendationReview } from "./bayesian";
import type { BayesianNoiseBatchCreateRequest } from "./types";
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
});
