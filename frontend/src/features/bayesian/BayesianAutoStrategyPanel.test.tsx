import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setCurrentLocale } from "../../i18n/store";
import { requestAutoStrategy, validAutoStrategy, type AutoStrategySource, type AutoStrategyView } from "../../api/boAutoStrategy";
import { BayesianAutoStrategyPanel } from "./BayesianAutoStrategyPanel";

vi.mock("../../api/boAutoStrategy", async importOriginal => ({ ...await importOriginal<typeof import("../../api/boAutoStrategy")>(), requestAutoStrategy: vi.fn() }));
const model: AutoStrategySource = { model_id: "model", snapshot_sha256: "a".repeat(64), config_sha256: "b".repeat(64), history_sha256: "c".repeat(64), source_history_revision_id: "history", source_is_current: true,
  objective: { responses: [{ response_id: "y", name: "원문 <yield>", unit: null }] } };
function receipt(): AutoStrategyView {
  return {
    schema_version: 1, decision_only: true, selection_created: false, apply_allowed: true, decision_sha256: "d".repeat(64),
    diagnostic: { schema_version: 1, study_id: "study", model_id: model.model_id, model_sha256: model.snapshot_sha256, config_sha256: model.config_sha256, history_sha256: model.history_sha256,
      source_history_revision_id: model.source_history_revision_id, source_is_current: true, calculation_sha256: "e".repeat(64),
      calculation: { schema_version: 1, policy: "fixed_full_fit_parameters_row_loo_v1", evaluation_unit: "individual_observed_trial", normalization_policy: "frozen_full_fit_mean_scale",
        r_squared_policy: "one_minus_press_over_raw_centered_tss", model_refit: false, auto_routing_applied: false, warnings: [],
        responses: [{ response_id: "y", raw_observation_count: 2, effective_training_count: 2, n_scored: 2, rmse: 1, r_squared: -.1, r_squared_reason: null, points: [] }] } },
    decision: { schema_version: 1, policy: "conditional_loo_any_low_explore_else_refine_v1", threshold: .25, comparison: "strictly_less_than", recommended_policy: "greedy_incremental_maxpro_v1",
      reason: "any_response_below_threshold", response_ids: ["y"], below_threshold_response_ids: ["y"], unavailable_response_ids: [], ordinal_rank_distance_requires_consent: false, warnings: [] },
  };
}
describe("Auto advice boundary", () => {
  afterEach(() => { setCurrentLocale("ko"); vi.clearAllMocks(); });
  it.each(["en", "ko"] as const)("does not calculate or apply on first render in %s", locale => {
    setCurrentLocale(locale); const apply = vi.fn();
    const html = renderToStaticMarkup(<BayesianAutoStrategyPanel studyId="study" model={model} contextKey="source" kinds={["continuous"]} disabled={false} onApply={apply} />);
    expect(html).toContain('value="0.25"');
    expect(html).toContain(locale === "en" ? "Confirm remains a manual choice" : "사용자가 선택합니다");
    expect(html).toContain(locale === "en" ? "not independent external validation" : "독립 외부 검증이나");
    expect(requestAutoStrategy).not.toHaveBeenCalled(); expect(apply).not.toHaveBeenCalled();
  });
  it("validates numeric policy and exact source before display", () => {
    const original = receipt();
    expect(validAutoStrategy(original, "study", model, ["continuous"], .25)).toBe(true);
    for (const field of ["model_sha256", "config_sha256", "history_sha256", "source_history_revision_id"] as const) {
      const changed = structuredClone(original); changed.diagnostic[field] = "wrong";
      expect(validAutoStrategy(changed, "study", model, ["continuous"], .25)).toBe(false);
    }
    expect(validAutoStrategy(original, "study", model, ["continuous"], .3)).toBe(false);
    expect(validAutoStrategy(original, "study", model, ["nominal"], .25)).toBe(false);
    original.decision.recommended_policy = "confirm_mean_then_competitive_sd_v1";
    expect(validAutoStrategy(original, "study", model, ["continuous"], .25)).toBe(false);
  });
  it("rejects null/NaN or missing responses hidden behind a low score", () => {
    const value = receipt();
    value.diagnostic.calculation.responses[0].r_squared = null;
    expect(validAutoStrategy(value, "study", model, ["continuous"], .25)).toBe(false);
    value.diagnostic.calculation.responses[0].r_squared = NaN;
    expect(validAutoStrategy(value, "study", model, ["continuous"], .25)).toBe(false);
    value.diagnostic.calculation.responses = [];
    expect(validAutoStrategy(value, "study", model, ["continuous"], .25)).toBe(false);
  });
  it("rejects historical receipt marked applicable", () => {
    const value = receipt(); value.diagnostic.source_is_current = false;
    expect(validAutoStrategy(value, "study", model, ["continuous"], .25)).toBe(false);
    value.apply_allowed = false;
    expect(validAutoStrategy(value, "study", model, ["continuous"], .25)).toBe(true);
  });
});
