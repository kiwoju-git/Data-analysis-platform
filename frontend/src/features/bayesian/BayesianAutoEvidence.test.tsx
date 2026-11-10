import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import type { AutoStrategyEvidence } from "../../api/types/boAugmentation";
import { setCurrentLocale } from "../../i18n/store";
import { BayesianAutoEvidence } from "./BayesianAutoEvidence";
import { augmentationFixture } from "./boAugmentation.fixture";
import { validAugmentationBatch, validAugmentationSelection } from "./boAugmentationDraft";

function fixture() {
  const base = augmentationFixture(), { model, selection, study, batch } = base;
  const responses = model.objective.responses;
  const evidence: AutoStrategyEvidence = { schema_version: 1, decision_sha256: "f".repeat(64),
    diagnostic: { schema_version: 1, study_id: study.study_id, model_id: model.model_id, model_sha256: model.snapshot_sha256,
      config_sha256: model.config_sha256, history_sha256: model.history_sha256, source_history_revision_id: model.source_history_revision_id,
      calculation_sha256: "e".repeat(64), calculation: { schema_version: 1, policy: "fixed_full_fit_parameters_row_loo_v1",
        evaluation_unit: "individual_observed_trial", normalization_policy: "frozen_full_fit_mean_scale", r_squared_policy: "one_minus_press_over_raw_centered_tss",
        model_refit: false, auto_routing_applied: false, warnings: [], responses: responses.map(row => ({ response_id: row.response_id,
          raw_observation_count: 3, effective_training_count: 3, n_scored: 3, r_squared: -.125, r_squared_reason: null, rmse: 1e-8, points: [] })) } },
    decision: { schema_version: 1, policy: "conditional_loo_any_low_explore_else_refine_v1", threshold: .25, comparison: "strictly_less_than",
      recommended_policy: selection.request.policy, reason: "any_response_below_threshold", response_ids: responses.map(row => row.response_id),
      below_threshold_response_ids: responses.map(row => row.response_id), unavailable_response_ids: [], ordinal_rank_distance_requires_consent: false, warnings: [] } };
  selection.schema_version = 4;
  selection.request = { ...selection.request, schema_version: 4, auto_strategy: { schema_version: 1, routing_model_id: model.model_id,
    expected_model_sha256: model.snapshot_sha256, r_squared_threshold: .25, expected_decision_sha256: evidence.decision_sha256 } };
  selection.calculation = { ...selection.calculation, schema_version: 2, auto_evidence: evidence };
  batch.method_version = "0.16.0"; batch.config_schema_version = batch.result_schema_version = batch.model_schema_version = 11;
  batch.selection_request = selection.request; batch.calculation = selection.calculation;
  return { ...base, evidence };
}

describe("saved Auto evidence", () => {
  afterEach(() => setCurrentLocale("ko"));
  it("accepts versioned evidence without inventing a prediction model", () => {
    const { study, selection, batch } = fixture();
    expect(selection.model_id).toBeNull(); expect(batch.model).toBeNull();
    expect(validAugmentationSelection(selection, study)).toBe(true);
    expect(validAugmentationBatch(batch, study, batch.batch_id)).toBe(true);
  });
  it.each(["threshold", "policy", "history", "routing", "digest", "version", "unavailable"])("rejects inconsistent %s", kind => {
    const { study, selection, evidence } = fixture();
    if (kind === "threshold") evidence.decision.threshold = .5;
    if (kind === "policy") evidence.decision.recommended_policy = "confirm_mean_then_competitive_sd_v1";
    if (kind === "history") evidence.diagnostic.history_sha256 = "0".repeat(64);
    if (kind === "routing") evidence.diagnostic.model_id = "wrong-model";
    if (kind === "digest") evidence.decision_sha256 = "0".repeat(64);
    if (kind === "version") selection.schema_version = 2;
    if (kind === "unavailable") evidence.diagnostic.calculation.responses[0].r_squared = null;
    expect(validAugmentationSelection(selection, study)).toBe(false);
  });
  it.each(["en", "ko"] as const)("renders exact negative R² and nonzero RMSE; escapes user text in %s", locale => {
    setCurrentLocale(locale);
    const { evidence } = fixture();
    const html = renderToStaticMarkup(<BayesianAutoEvidence evidence={evidence}
      responses={evidence.decision.response_ids.map(response_id => ({ response_id, name: "원문 <script>" }))} />);
    expect(html).toContain("-0.125"); expect(html).toContain("1e-8");
    expect(html).toContain("원문 &lt;script&gt;"); expect(html).not.toContain("<script>");
    expect(html).toContain(locale === "en" ? "Saved Auto decision evidence" : "저장된 Auto 판단 근거");
    expect(html).toContain(evidence.decision_sha256);
  });
  it("keeps the legacy request/result branch readable and unchanged", () => {
    const { study, selection, batch } = augmentationFixture();
    const before = JSON.stringify({ selection, batch });
    expect(validAugmentationSelection(selection, study)).toBe(true);
    expect(validAugmentationBatch(batch, study, batch.batch_id)).toBe(true);
    expect(JSON.stringify({ selection, batch })).toBe(before);
  });
});
