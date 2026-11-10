import { describe, expect, it } from "vitest";
import { augmentationFailureCode, augmentationRequest, initialAugmentationDraft, validAugmentationBatch, validAugmentationPage, validAugmentationReportSource, validAugmentationSelection } from "./boAugmentationDraft";
import { augmentationFixture } from "./boAugmentation.fixture";
import { createPlanningCommitFence, createPlanningRequestFence } from "./boPlanningDraft";

describe("source-owned augmentation drafts", () => {
  it("does not expose unknown errors containing synthetic private data", () => {
    expect(augmentationFailureCode(new Error("Private raw cell /secret/file?token=abc"))).toBe("bayesian_augmentation_request_failed");
    expect(augmentationFailureCode(new Error("bayesian_candidate_source_changed"))).toBe("bayesian_candidate_source_changed");
  });
  it("creates model-free selection without a fitted state or fabricated predictions", () => {
    const { study, page, draft, selection, batch } = augmentationFixture();
    const before = JSON.stringify({ study, page, selection, batch });
    expect(augmentationRequest(study, page, null, draft, selection.request.request_id)?.model_id).toBeNull();
    expect(validAugmentationPage(page, study)).toBe(true);
    expect(validAugmentationSelection(selection, study, selection.request)).toBe(true);
    expect(validAugmentationBatch(batch, study, batch.batch_id)).toBe(true);
    expect(selection.calculation.prediction_evaluations).toBe(0);
    expect(selection.calculation.selected_rows.some(row => "response_predictions" in row)).toBe(false);
    expect(JSON.stringify({ study, page, selection, batch })).toBe(before);
  });
  it("uses the saved candidate tolerance, not a guessed default", () => {
    const { study, page, draft } = augmentationFixture();
    expect(page.revision.schema_version).toBe(2);
    if (page.revision.schema_version === 2) page.revision.duplicate_tolerance = .00023;
    expect(augmentationRequest(study, page, null, draft, "request")?.duplicate_tolerance).toBe(.00023);
  });
  it.each(["", " ", "1.5", "2e0", "2abc", "-2", "9", "NaN"])("rejects invalid batch draft %s", value => {
    const { study, page, draft } = augmentationFixture();
    expect(augmentationRequest(study, page, null, { ...draft, batchSize: value }, "request")).toBeNull();
  });
  it("enforces remaining trial, evaluation, distance and time budgets without truncation", () => {
    const { study, page, draft } = augmentationFixture();
    for (const patch of [{ budget: "3" }, { evaluations: "100001" }, { moments: "65537" }, { seconds: "61" }, { seconds: "1.2" }, { distance: "" }, { distance: "2" }, { distance: "-1" }])
      expect(augmentationRequest(study, page, null, { ...draft, ...patch }, "request")).toBeNull();
    expect(augmentationRequest(study, page, null, { ...draft, distance: "1e-4" }, "request")?.min_batch_distance_normalized).toBe(.0001);
  });
  it("requires an explicit alternative to MaxPro for discrete factors", () => {
    const { study, page, draft } = augmentationFixture();
    study.factors[0] = { ...study.factors[0], domain_kind: "discrete_numeric", step: .1 };
    expect(initialAugmentationDraft(study).policy).toBe("greedy_mixed_maximin_v1");
    expect(augmentationRequest(study, page, null, draft, "request")).toBeNull();
    expect(augmentationRequest(study, page, null, { ...draft, policy: "greedy_mixed_maximin_v1" }, "request")?.policy).toBe("greedy_mixed_maximin_v1");
  });
  it("requires a current saved model for Refine and Confirm", () => {
    const { study, page, model, draft, selection, batch } = augmentationFixture(true);
    expect(validAugmentationSelection(selection, study)).toBe(true); expect(validAugmentationBatch(batch, study, batch.batch_id)).toBe(true);
    expect(augmentationRequest(study, page, null, draft, "request")).toBeNull();
    expect(augmentationRequest(study, page, { ...model, source_is_current: false }, draft, "request")).toBeNull();
    expect(augmentationRequest(study, page, model, draft, "request")?.model_id).toBe(model.model_id);
    expect(augmentationRequest(study, page, model, { ...draft, policy: "confirm_mean_then_competitive_sd_v1" }, "request")?.policy).toBe("confirm_mean_then_competitive_sd_v1");
  });
  it("does not reuse stale candidate eligibility or pending/closed lifecycle", () => {
    const { study, page, draft } = augmentationFixture();
    expect(augmentationRequest({ ...study, pending_trial_count: 1 }, page, null, draft, "request")).toBeNull();
    expect(augmentationRequest({ ...study, status: "completed" }, page, null, draft, "request")).toBeNull();
    expect(augmentationRequest({ ...study, trial_count: study.trial_count + 1 }, page, null, draft, "request")).toBeNull();
    page.revision.source_is_current = false;
    expect(augmentationRequest(study, page, null, draft, "request")).toBeNull();
  });
  it("rejects damaged IDs, row ordering, predictions and source hashes", () => {
    const { study, selection, page } = augmentationFixture();
    for (const change of [
      (v: typeof selection) => { v.calculation.augmentation.steps.reverse(); },
      (v: typeof selection) => { v.calculation.selected_rows[0].actual_coordinates.x = NaN; },
      (v: typeof selection) => { v.calculation.augmentation.source.history_sha256 = "f".repeat(64); },
      (v: typeof selection) => { v.calculation.augmentation.steps[0].score = Infinity; },
      (v: typeof selection) => { v.calculation.prediction_evaluations = 1; },
    ]) { const altered = structuredClone(selection); change(altered); expect(validAugmentationSelection(altered, study)).toBe(false); }
    const wrong = structuredClone(page); wrong.items[0].normalized_coordinates.x = .99;
    expect(validAugmentationPage(wrong, study)).toBe(false);
  });
  it("reopens exact historical batches and uses server-issued report attachment hashes", () => {
    const { study, batch, descriptor } = augmentationFixture();
    study.observation_history = { ...study.observation_history, history_revision_id: "99999999-9999-4999-8999-999999999999", observation_history_sha256: "9".repeat(64) };
    expect(validAugmentationBatch({ ...batch, is_latest: false }, study, batch.batch_id)).toBe(true);
    expect(validAugmentationReportSource(descriptor, batch)).toBe(true);
    expect(validAugmentationBatch(batch, study, study.study_id)).toBe(false);
    const wrong = structuredClone(descriptor);
    if (wrong.source.kind === "bayesian_history_revision" && wrong.source.attachment.kind === "batch") wrong.source.attachment.result_payload_sha256 = "f".repeat(64);
    expect(validAugmentationReportSource(wrong, batch)).toBe(false);
  });
  it("keeps same-study confirmed writes through draft changes while blocking A-B-A and old finally", async () => {
    const commit = createPlanningCommitFence(), computation = createPlanningRequestFence();
    commit.source("study-A"); computation.source("A:history1");
    const a = commit.begin()!, oldCompute = computation.begin();
    computation.source("A:history2"); expect(computation.current(oldCompute)).toBe(false); expect(commit.current(a)).toBe(true);
    let finish!: () => void; const pending = new Promise<void>(resolve => { finish = resolve; });
    const oldFinally = pending.finally(() => commit.finish(a));
    commit.source("study-B"); commit.source("study-A"); const fresh = commit.begin()!;
    finish(); await oldFinally; expect(commit.current(fresh)).toBe(true); expect(commit.current(a)).toBe(false);
  });
});
