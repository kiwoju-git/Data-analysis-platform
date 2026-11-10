import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setCurrentLocale } from "../../i18n/store";
import { BayesianDesirabilityRecommendationPanel, DesirabilityCandidate, type DesirabilityRecommendationState } from "./BayesianDesirabilityRecommendationPanel";
import { defaultDesirabilityDraft } from "./bayesianDesirabilityDraft";
import { desirabilityBatchFixture, desirabilityFixture } from "./bayesianDesirability.fixture";

describe("multiresponse q1 presentation", () => {
  afterEach(() => setCurrentLocale("ko"));
  it.each(["en", "ko"] as const)("keeps raw predictions, measured D and latent incumbent separate in %s", locale => {
    setCurrentLocale(locale); const { study, review, calculation } = desirabilityFixture();
    const before = JSON.stringify({ study, calculation });
    const html = renderToStaticMarkup(<DesirabilityCandidate study={study} source={review} calculation={calculation} />);
    expect(html).toContain(locale === "en" ? "no experiment created" : "실험이 생성되지 않았습니다");
    expect(html).toContain("Yield &lt;raw&gt;"); expect(html).not.toContain("<raw>");
    expect(html).toContain("1e-8"); expect(html).toContain("1000000000001");
    expect(html).toContain(locale === "en" ? "Latent SD" : "잠재 SD");
    expect(html).toContain(locale === "en" ? "New-measurement predictive SD" : "새 측정 예측 SD");
    expect(html).toContain(locale === "en" ? "Best measured desirability" : "최상 실제 관측 만족도");
    expect(html).toContain("0.6"); expect(html).toContain("0.5"); expect(html).toContain("0.02");
    expect(html).toContain(review.source_history_revision_id);
    expect(html).not.toContain("value=\"1e-8\"");
    expect(JSON.stringify({ study, calculation })).toBe(before);
  });
  it("renders the exact historical result and separate completed measurements", () => {
    setCurrentLocale("en"); const { study, batch } = desirabilityFixture();
    batch.items[0].current_trial = { ...batch.items[0].current_trial, state: "completed", response_values: { yield: .77, cost: 1.99 } };
    batch.batch_state = "completed"; study.observation_history.observation_history_sha256 = "e".repeat(64);
    const html = renderToStaticMarkup(<DesirabilityCandidate study={study} source={batch} calculation={batch.calculation} />);
    expect(html).toContain("earlier observation history"); expect(html).toContain("Yield &lt;raw&gt;: 0.77");
    expect(html).toContain("1e-8"); expect(html).toContain(batch.result_sha256);
    expect(html).toContain("source_kind=bayesian_history_revision");
  });
  it("offers four per-response kernels, strict limits and q1 review/confirm separately", () => {
    setCurrentLocale("en"); const { study, review } = desirabilityFixture();
    const state: DesirabilityRecommendationState = { draft: defaultDesirabilityDraft(study), edit: vi.fn(), review, saved: null,
      requestReview: vi.fn(), confirm: vi.fn(), discard: vi.fn(), refresh: vi.fn(), error: null, errors: {},
      isReviewing: false, isConfirming: false, isRestoring: false, mayHaveCommitted: false };
    const html = renderToStaticMarkup(<BayesianDesirabilityRecommendationPanel study={study} state={state} disabled={false} onConfirm={vi.fn()} onRefresh={vi.fn()} />);
    expect(html).toContain("Review ordered batch"); expect(html).toContain("Confirm entire pending batch");
    expect(html.match(/value="gaussian"/g)).toHaveLength(2); expect(html.match(/value="exponential"/g)).toHaveLength(2);
    expect(html).toContain("Experiments in this batch (1-8)"); expect(html).not.toContain("parallel_batch"); expect(html).toContain("DS-linear");
    expect(html).toContain("2–2000"); expect(html).toContain("1000–60000");
    expect(html).not.toContain("JMP numerical equivalence or exact noisy EI. Predictions are measurements");
  });
  it.each(["en", "ko"] as const)("shows an explicit Gaussian precision rejection in %s", locale => {
    setCurrentLocale(locale); const {study} = desirabilityFixture();
    const state: DesirabilityRecommendationState = {draft: defaultDesirabilityDraft(study), edit: vi.fn(), review: null, saved: null,
      requestReview: vi.fn(), confirm: vi.fn(), discard: vi.fn(), refresh: vi.fn(), error: "bayesian_target_curve_precision_unsupported", errors: {},
      isReviewing: false, isConfirming: false, isRestoring: false, mayHaveCommitted: false};
    const html = renderToStaticMarkup(<BayesianDesirabilityRecommendationPanel study={study} state={state} disabled={false} onConfirm={vi.fn()} onRefresh={vi.fn()} />);
    expect(html).toContain("bayesian_target_curve_precision_unsupported");
    expect(html).toContain(locale === "en" ? "its uncertainty cannot be resolved" : "그 불확실성을 현재 수치 정밀도로");
    expect(html).toContain(locale === "en" ? "No experiment was created" : "실험은 생성되지 않았습니다");
  });
  it("shows uncertainty after failed confirmation and links bounded field errors", () => {
    setCurrentLocale("en"); const { study } = desirabilityFixture();
    const state: DesirabilityRecommendationState = { draft: defaultDesirabilityDraft(study), edit: vi.fn(), review: null, saved: null,
      requestReview: vi.fn(), confirm: vi.fn(), discard: vi.fn(), refresh: vi.fn(), error: "bayesian_desirability_settings_invalid", errors: { seed: "integer", "yield:lower": "bounds" },
      isReviewing: false, isConfirming: false, isRestoring: false, mayHaveCommitted: true };
    state.draft.models[0].noise = "near_noiseless";
    const html = renderToStaticMarkup(<BayesianDesirabilityRecommendationPanel study={study} state={state} disabled={false} onConfirm={vi.fn()} onRefresh={vi.fn()} />);
    expect(html).toMatch(/<details open="">/);
    expect(html).toContain("role=\"alert\""); expect(html).toContain("aria-invalid=\"true\""); expect(html).toContain("already have committed");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Review ordered batch/);
  });
  it.each(["en", "ko"] as const)("shows every ordered candidate, base and planning quantities, and partial measurements in %s", locale => {
    setCurrentLocale(locale); const { study, batch } = desirabilityBatchFixture("ordered", 8);
    batch.batch_state = "partially_completed";
    batch.items[7].current_trial = { ...batch.items[7].current_trial, state: "completed", response_values: { yield: 42.1234, cost: 3.4321 } };
    const html = renderToStaticMarkup(<DesirabilityCandidate study={study} calculation={batch.calculation} source={batch} />);
    expect(html.match(/data-candidate-rank="\d"/g)).toHaveLength(8);
    expect(html).toContain(locale === "en" ? "Partially completed" : "일부 완료");
    expect(html).toContain(locale === "en" ? "Conditional batch planning" : "조건부 배치 계획");
    expect(html).toContain("42.1234"); expect(html).toContain("3.4321");
    for (const item of batch.items) expect(html).toContain(item.trial.trial_id);
    expect(batch.items.every(item => item.trial.state === "pending")).toBe(true);
  });
});
