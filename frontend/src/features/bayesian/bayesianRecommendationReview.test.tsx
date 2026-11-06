import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import type { BayesianRecommendationReviewResponse, BayesianStudyResponse } from "../../api";
import { getCurrentLocale, setCurrentLocale } from "../../i18n/store";
import { BayesianRecommendationReview } from "./BayesianRecommendationReview";
import { bayesianReviewErrorDetails } from "./bayesianReviewErrors";

describe("BO candidate review presentation", () => {
  const initialLocale = getCurrentLocale();
  afterEach(() => setCurrentLocale(initialLocale));

  it.each(["ko", "en"] as const)("shows uncommitted values and explicit confirm in %s without inventing trials", locale => {
    setCurrentLocale(locale);
    const review = fixture();
    const study = { factors: [{ factor_id: "x", name: "온도 <raw>", unit: "K" }], objective: { unit: "mg" } } as BayesianStudyResponse;
    const before = JSON.stringify({ review, study });
    const html = renderToStaticMarkup(<BayesianRecommendationReview review={review} study={study}
      disabled={false} isConfirming={false} onConfirm={() => undefined} onDiscard={() => undefined} />);
    expect(html).toContain(locale === "ko" ? "미확정" : "Not committed");
    expect(html).toContain(locale === "ko" ? "이 후보로 실험 확정" : "Confirm these experiments");
    expect(html).toContain("온도 &lt;raw&gt;");
    expect(html).toContain("1e-6");
    expect(html).toContain("2e-6");
    expect(html).toContain("3e-6");
    expect(html).toContain("Latent SD");
    expect(html).toContain(locale === "ko" ? "새 관측 predictive SD" : "New-observation predictive SD");
    expect(html).toContain(locale === "ko" ? "수치적으로 0" : "numerically zero");
    expect(html).not.toContain('type="checkbox"');
    expect(html).not.toContain("pending_trial");
    expect(JSON.stringify({ review, study })).toBe(before);
  });

  it("disables confirmation and dismissal during an active commit", () => {
    const html = renderToStaticMarkup(<BayesianRecommendationReview review={fixture()}
      study={{ factors: [], objective: { unit: null } } as unknown as BayesianStudyResponse}
      disabled={false} isConfirming onConfirm={() => undefined} onDiscard={() => undefined} />);
    expect(html.match(/disabled=""/g)).toHaveLength(2);
  });

  it.each(["bayesian_review_expired", "bayesian_review_mismatch", "bayesian_review_size_exceeded", "bayesian_review_busy", "bayesian_recommendation_confirm_failed"])("has actionable English and Korean %s messages", code => {
    const en = bayesianReviewErrorDetails(code, "en");
    const ko = bayesianReviewErrorDetails(code, "ko");
    expect(en?.action.length).toBeGreaterThan(10);
    expect(ko?.action.length).toBeGreaterThan(10);
    expect(JSON.stringify(en)).not.toMatch(/[가-힣]/);
    expect(en).not.toEqual(ko);
    expect(bayesianReviewErrorDetails("user-owned text <raw>", "en")).toBeNull();
  });
});

function fixture(): BayesianRecommendationReviewResponse {
  return {
    review_id: "synthetic-review", expires_at: "2026-11-07T10:20:00Z",
    calculation: {
      items: [{ rank: 1, actual_coordinates: { x: 1000 }, predicted_objective_mean: 1e-6,
        latent_standard_deviation: 2e-6, predictive_standard_deviation: 3e-6,
        acquisition_value_raw: 1e-8, constraint_evaluations: [] }],
      search_budget: { searches: [{ all_acquisitions_zero: true }] }, warnings: [],
    },
  } as unknown as BayesianRecommendationReviewResponse;
}
