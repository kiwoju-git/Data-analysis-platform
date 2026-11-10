import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import type { AutoStrategyEvidence } from "../../api/types/boAugmentation";
import { setCurrentLocale } from "../../i18n/store";
import { MixedSelectionDetails } from "./BayesianMixedPlanningPanel";
import { augmentationFixture } from "./boAugmentation.fixture";
import { mixedPlanningFixture } from "./boMixedPlanning.test.fixture";
import { initialMixedSelection, mixedSelectionRequest, validMixedBatch, validMixedSelection } from "./boMixedPlanningDraft";

function fixture() {
  const original = mixedPlanningFixture(), { study, model, selection, batch, page } = original;
  const policy = "greedy_mixed_maximin_v1" as const;
  const evidence: AutoStrategyEvidence = { schema_version: 1, decision_sha256: "d".repeat(64),
    diagnostic: { schema_version: 1, study_id: study.study_id, model_id: model.model_id, model_sha256: model.snapshot_sha256,
      config_sha256: model.config_sha256, history_sha256: model.history_sha256, source_history_revision_id: model.source_history_revision_id,
      calculation_sha256: "e".repeat(64), calculation: { schema_version: 1, policy: "fixed_full_fit_parameters_row_loo_v1",
        evaluation_unit: "individual_observed_trial", normalization_policy: "frozen_full_fit_mean_scale", r_squared_policy: "one_minus_press_over_raw_centered_tss",
        model_refit: false, auto_routing_applied: false, warnings: [], responses: study.objective.responses.map(row => ({ response_id: row.response_id,
          raw_observation_count: 4, effective_training_count: 4, n_scored: 4, r_squared: -.125, r_squared_reason: null, rmse: 1e-8, points: [] })) } },
    decision: { schema_version: 1, policy: "conditional_loo_any_low_explore_else_refine_v1", threshold: .25, comparison: "strictly_less_than",
      recommended_policy: policy, reason: "any_response_below_threshold", response_ids: study.objective.responses.map(row => row.response_id),
      below_threshold_response_ids: study.objective.responses.map(row => row.response_id), unavailable_response_ids: [], ordinal_rank_distance_requires_consent: false, warnings: [] } };
  const request = { ...selection.request, schema_version: 5 as const, kind: "augmentation" as const, policy,
    model_id: null, expected_model_sha256: null, row_ids: [], auto_strategy: { schema_version: 1 as const,
      routing_model_id: model.model_id, expected_model_sha256: model.snapshot_sha256,
      r_squared_threshold: .25, expected_decision_sha256: evidence.decision_sha256 } };
  const rows = page.items.map(row => Object.fromEntries(Object.entries(row).filter(([key]) =>
    !["response_predictions", "desirability_moments", "acquisition", "prediction_source", "rank", "planning", "nearest_selected_distance"].includes(key))) as typeof row);
  const template = augmentationFixture().selection.calculation;
  const trace = { ...template.augmentation, policy, selected_row_ids: rows.map(row => row.row_id),
    source: { ...template.augmentation.source, model_snapshot_id: null, model_snapshot_sha256: null,
      candidate_revision_id: page.revision.revision_id, candidate_revision_sha256: page.revision.rows_sha256,
      history_sha256: model.history_sha256 }, steps: rows.map((row, index) => ({ ...template.augmentation.steps[0], rank: index + 1, row_id: row.row_id })) };
  selection.schema_version = 5; selection.model_id = null; selection.request = request;
  selection.calculation = { schema_version: 4, augmentation: trace, selected_rows: rows, auto_evidence: evidence,
    source_row_count: page.revision.row_count, prediction_evaluations: 0, max_moment_evaluations: request.max_moment_evaluations, time_budget_ms: request.time_budget_ms, model_refit: false };
  batch.method_version = "0.16.0"; batch.config_schema_version = batch.result_schema_version = batch.model_schema_version = 12;
  batch.source.model_id = null; batch.source.model_sha256 = null; batch.response_models = null; batch.incumbent = null;
  batch.selection_request = request; batch.calculation = selection.calculation;
  return { ...original, evidence, request };
}

describe("mixed Auto evidence ownership", () => {
  afterEach(() => setCurrentLocale("ko"));
  it("keeps category data and model-free provenance in new selection and batch versions", () => {
    const { selection, batch, study } = fixture();
    expect(validMixedSelection(selection, study)).toBe(true);
    expect(validMixedBatch(batch, study, batch.batch_id)).toBe(true);
    expect(selection.model_id).toBeNull(); expect(batch.response_models).toBeNull();
  });
  it.each(["threshold", "history", "policy", "model", "digest", "version"])("rejects a changed %s", change => {
    const { selection, study, evidence } = fixture();
    if (change === "threshold") evidence.decision.threshold = .5;
    if (change === "history") evidence.diagnostic.history_sha256 = "f".repeat(64);
    if (change === "policy") evidence.decision.recommended_policy = "greedy_incremental_maxpro_v1";
    if (change === "model") evidence.diagnostic.model_id = "wrong-owner";
    if (change === "digest") evidence.decision_sha256 = "0".repeat(64);
    if (change === "version") selection.schema_version = 3;
    expect(validMixedSelection(selection, study)).toBe(false);
  });
  it("requires a current routing model only for explicitly attached evidence", () => {
    const { model, page, study, request } = fixture();
    const draft = { ...initialMixedSelection(), kind: "augmentation" as const, batchSize: "1" };
    expect(mixedSelectionRequest(study, page, model, [], draft, request.request_id, request.auto_strategy)?.schema_version).toBe(5);
    expect(mixedSelectionRequest(study, page, null, [], draft, request.request_id, request.auto_strategy)).toBeNull();
    expect(mixedSelectionRequest(study, page, null, [], draft, request.request_id)?.schema_version).toBe(3);
  });
  it.each(["en", "ko"] as const)("renders saved evidence and original category text in %s", locale => {
    setCurrentLocale(locale);
    const { study, selection } = fixture();
    const html = renderToStaticMarkup(<MixedSelectionDetails study={study} selection={selection} />);
    expect(html).toContain(locale === "en" ? "Saved Auto decision evidence" : "저장된 Auto 판단 근거");
    expect(html).toContain("-0.125"); expect(html).toContain("1e-8"); expect(html).toContain("001");
  });
  it("keeps legacy manual selection and batch bytes unchanged", () => {
    const { study, selection, batch } = mixedPlanningFixture(), before = JSON.stringify({ selection, batch });
    expect(validMixedSelection(selection, study)).toBe(true); expect(validMixedBatch(batch, study, batch.batch_id)).toBe(true);
    expect(JSON.stringify({ selection, batch })).toBe(before);
  });
});
