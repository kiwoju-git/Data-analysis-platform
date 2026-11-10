import { describe, expect, it } from "vitest";
import type { CandidateRow, CandidatePage, PlanningModelDetail, PlanningEvaluationResponse } from "../../api/types/boPlanning";
import { buildDesirabilityRequest, defaultDesirabilityDraft } from "./bayesianDesirabilityDraft";
import { desirabilityFixture } from "./bayesianDesirability.fixture";
import { createPlanningCommitFence, createPlanningRequestFence, currentPlanningModel, emptyPlanningOrder, parsePlanningPaste, parsePlanningPoint, planningInteger, planningProfilePoints,
  planningResponseProfilePoints, planningStudyKey, redoPlanningOrder, undoPlanningOrder, updatePlanningOrder, validPlanningBatch, validPlanningBatchReportSource, validPlanningEvaluation, validPlanningModel, validPlanningPage } from "./boPlanningDraft";
import { planningBatchFixture } from "./boPlanning.fixture";

function fixture() {
  const { study, calculation } = desirabilityFixture();
  study.observation_history.history_revision_id = "11111111-1111-4111-8111-111111111111";
  const request = buildDesirabilityRequest(study, { ...defaultDesirabilityDraft(study), batchSize: "2" }).request;
  if (!request || request.schema_version === 4) throw new Error("synthetic_fit_request");
  const model: PlanningModelDetail = { schema_version: 1, model_id: "22222222-2222-4222-8222-222222222222", study_id: study.study_id,
    study_version_id: study.study_version_id, source_history_revision_id: study.observation_history.history_revision_id, history_sha256: study.observation_history.observation_history_sha256,
    definition_sha256: study.definition_sha256, snapshot_sha256: "a".repeat(64), config_sha256: "b".repeat(64), created_at: "2026-11-10", source_is_current: true,
    fit: request, objective: calculation.objective, response_models: calculation.shared_model.response_models,
    incumbent: calculation.incumbent, observation_view: calculation.observation_view, warnings: [], model_reusable_without_refit: true };
  const row: CandidateRow = { row_id: "c".repeat(64), source_row_number: 1, input_coordinates: { x: .4 }, actual_coordinates: { x: .4 },
    normalized_coordinates: { x: .4 }, canonical_level_indices: {}, constraint_evaluations: [], constraints_satisfied: true, nearest_existing_distance: .4, novel: true, eligible: true };
  const page: CandidatePage = { offset: 0, limit: 50, items: [row], revision: { schema_version: 1, candidate_set_id: "33333333-3333-4333-8333-333333333333",
    name: "Synthetic <table>", revision_id: "44444444-4444-4444-8444-444444444444", revision_number: 1, parent_revision_id: null,
    model_id: model.model_id, model_sha256: model.snapshot_sha256, rows_sha256: "e".repeat(64), config_sha256: "f".repeat(64), excluded_coordinates_sha256: "d".repeat(64),
    source_trial_count: 2, row_count: 1, eligible_count: 1, created_at: "2026-11-10", source_is_current: true } };
  const evaluation: PlanningEvaluationResponse = { schema_version: 1, model_id: model.model_id, model_sha256: model.snapshot_sha256,
    request_sha256: "1".repeat(64), items: [{ ...row, response_predictions: calculation.items[0].response_predictions,
      desirability_moments: calculation.items[0].desirability_moments, acquisition: calculation.items[0].acquisition, prediction_source: "completed_observations_base_posterior" }],
    source_is_current: true, eligibility_source_trial_count: 2, eligibility_coordinates_sha256: "2".repeat(64), eligibility_is_current: true, model_refit: false };
  return { study, model, row, page, evaluation };
}
describe("planning strict drafts and immutable ordered rows", () => {
  it.each(["", " ", "1e", "1.5", "10abc", "-1", "NaN", "Infinity"])("rejects invalid integer %s", value => {
    expect(planningInteger(value, 1, 10000)).toBeNull();
  });
  it("accepts complete finite numeric settings without coercing blank values", () => {
    const { study } = fixture();
    expect(parsePlanningPoint({ x: "0" }, study.factors)).toEqual({ x: 0 });
    expect(parsePlanningPoint({ x: "1e-5" }, study.factors)).toEqual({ x: 1e-5 });
    for (const x of ["", " ", "1e", "NaN", "Infinity", "0.5abc", "2"]) expect(parsePlanningPoint({ x }, study.factors)).toBeNull();
    expect(parsePlanningPoint({ x: ".5", extra: "1" }, study.factors)).toBeNull();
  });
  it("reuses quoted CSV/TSV parsing with explicit headers and no partial import", () => {
    const { study } = fixture();
    study.factors[0].name = "온도, raw";
    expect(parsePlanningPaste('"온도, raw"\r\n0\r\n1e-2', study.factors, true)).toEqual({ points: [{ x: 0 }, { x: .01 }], error: null });
    expect(parsePlanningPaste("0\n\n0.5", study.factors, false).points).toBeNull();
    expect(parsePlanningPaste("x\n0\n0", study.factors, true).error).toBe("duplicate");
    expect(parsePlanningPaste("wrong\n0", study.factors, true).error).toBe("header");
    expect(parsePlanningPaste("x\n0\nInfinity", study.factors, true).error).toBe("number");
    expect(parsePlanningPaste("0,1", study.factors, false).error).toBe("shape");
  });
  it("does not silently truncate imported rows", () => {
    const { study } = fixture();
    expect(parsePlanningPaste(Array.from({ length: 10001 }, (_, i) => String(i / 10001)).join("\n"), study.factors, false).points).toBeNull();
  });
  it("enforces discrete executable levels and never interpolates a categorical level", () => {
    const { study } = fixture();
    study.factors[0] = { ...study.factors[0], domain_kind: "discrete_numeric", step: .25 };
    expect(parsePlanningPoint({ x: ".3" }, study.factors)).toBeNull();
    expect(planningProfilePoints({ x: ".5" }, study.factors, "x")).toEqual([0, .25, .5, .75, 1].map(x => ({ x })));
    study.factors[0].step = .001;
    expect(planningProfilePoints({ x: ".5" }, study.factors, "x")).toBeNull();
  });
  it("preserves a decimal lattice anchored at 1000.1 with step 0.1", () => {
    const { study } = fixture();
    study.factors[0] = { ...study.factors[0], low: 1000.1, high: 1000.4, domain_kind: "discrete_numeric", step: .1 };
    expect(parsePlanningPoint({ x: "1000.3" }, study.factors)).toEqual({ x: 1000.3 });
    expect(parsePlanningPoint({ x: "1000.15" }, study.factors)).toBeNull();
    expect(planningProfilePoints({ x: "1000.2" }, study.factors, "x")).toEqual([1000.1, 1000.2, 1000.3, 1000.4].map(x => ({ x })));
    expect(parsePlanningPaste("1000.1\n1000.2\n1000.3\n1000.4", study.factors, false).points).toHaveLength(4);
  });
  it("preserves held settings, endpoints and complete point count in profiles", () => {
    const { study } = fixture();
    study.factors.push({ ...study.factors[0], factor_id: "other", low: 10, high: 20, order: 1 });
    const values = { x: ".25", other: "13" }, before = structuredClone(values);
    const points = planningProfilePoints(values, study.factors, "x")!;
    expect(points).toHaveLength(21); expect(points[0]).toEqual({ x: 0, other: 13 }); expect(points[20]).toEqual({ x: 1, other: 13 });
    expect(new Set(points.map(p => p.x)).size).toBe(21); expect(values).toEqual(before);
  });
  it("undo/redo changes ordered membership and is bounded without mutating rows", () => {
    const { row } = fixture(), original = structuredClone(row);
    const second = { ...row, row_id: "d".repeat(64), actual_coordinates: { x: .6 } };
    const one = updatePlanningOrder(emptyPlanningOrder(), [row]);
    const two = updatePlanningOrder(one, [row, second]);
    const moved = updatePlanningOrder(two, [second, row]);
    expect(undoPlanningOrder(moved).current).toEqual([row, second]);
    expect(redoPlanningOrder(undoPlanningOrder(moved)).current).toEqual([second, row]);
    expect(updatePlanningOrder(moved, [row, row])).toBe(moved);
    expect(updatePlanningOrder(moved, [{ ...row, eligible: false }])).toBe(moved);
    let many = emptyPlanningOrder();
    for (let i = 0; i < 40; i++) many = updatePlanningOrder(many, i % 2 ? [row] : [second]);
    expect(many.past.length).toBe(32); expect(row).toEqual(original);
  });
});
describe("planning source and response boundaries", () => {
  it("retains a committed outcome through draft invalidation but not a study A-B-A switch", async () => {
    const commit = createPlanningCommitFence(), compute = createPlanningRequestFence();
    commit.source("study-A:version"); compute.source("study-A:history1:options1");
    const confirmation = commit.begin()!, calculation = compute.begin();
    expect(commit.begin()).toBeNull();
    let resolve!: (id: string) => void;
    const response = new Promise<string>(done => { resolve = done; });
    let saved: string | null = null;
    const pending = response.then(id => { if (commit.current(confirmation)) saved = id; }).finally(() => commit.finish(confirmation));
    compute.source("study-A:history2:options2");
    expect(compute.current(calculation)).toBe(false); expect(commit.pending()).toBe(true);
    resolve("committed-batch"); await pending;
    expect(saved).toBe("committed-batch"); expect(commit.pending()).toBe(false);
    const old = commit.begin()!; commit.source("study-B:version"); commit.source("study-A:version");
    const fresh = commit.begin()!; commit.finish(old);
    expect(commit.current(old)).toBe(false); expect(commit.current(fresh)).toBe(true); expect(commit.pending()).toBe(true);
  });
  it("validates an exact schema8 saved batch without requiring it to be latest", () => {
    const { study, batch } = planningBatchFixture(), before = JSON.stringify(batch);
    expect(validPlanningBatch(batch, study, batch.batch_id)).toBe(true);
    study.observation_history.history_revision_id = "99999999-9999-4999-8999-999999999999";
    study.observation_history.observation_history_sha256 = "9".repeat(64);
    expect(validPlanningBatch({ ...batch, is_latest: false }, study, batch.batch_id)).toBe(true);
    expect(validPlanningBatch(batch, study, "different-id")).toBe(false);
    expect(validPlanningBatch({ ...batch, source: { ...batch.source, selection_id: study.study_id } }, study, batch.batch_id)).toBe(false);
    const changed = structuredClone(batch); changed.items[0].current_trial.actual_coordinates.x = .9;
    expect(validPlanningBatch(changed, study, batch.batch_id)).toBe(false);
    expect(JSON.stringify(batch)).toBe(before);
  });
  it("uses server-issued report hashes and rejects a different exact attachment", () => {
    const { batch, descriptor } = planningBatchFixture();
    expect(validPlanningBatchReportSource(descriptor, batch)).toBe(true);
    expect(descriptor.source_ref_sha256).not.toBe(batch.result_sha256);
    expect(validPlanningBatchReportSource({ ...descriptor, source_ref_sha256: "invented" }, batch)).toBe(false);
    if (descriptor.source.kind !== "bayesian_history_revision" || descriptor.source.attachment.kind !== "batch") throw new Error("fixture");
    expect(validPlanningBatchReportSource({ ...descriptor, source: { ...descriptor.source, attachment: { ...descriptor.source.attachment, batch_id: descriptor.source.study_id } } }, batch)).toBe(false);
    expect(validPlanningBatchReportSource({ ...descriptor, source: { ...descriptor.source, attachment: { ...descriptor.source.attachment, result_payload_sha256: "9".repeat(64) } } }, batch)).toBe(false);
  });
  it("blocks success, catch and finally after edits and source A-B-A changes", async () => {
    const guard = createPlanningRequestFence(); guard.source("A:options-1");
    const token = guard.begin();
    let resolve!: (value: number) => void;
    const response = new Promise<number>(done => { resolve = done; });
    const state = { result: "B", error: null as string | null, running: true };
    const waiting = (async () => {
      try { const value = await response; if (guard.current(token)) state.result = String(value); }
      catch { if (guard.current(token)) state.error = "old error"; }
      finally { if (guard.current(token)) state.running = false; }
    })();
    guard.source("B:options-1"); guard.source("A:options-1"); guard.begin();
    resolve(99); await waiting;
    expect(state).toEqual({ result: "B", error: null, running: true });
    const old = guard.begin(); guard.invalidate();
    expect(guard.current(old)).toBe(false);
    const current = guard.begin(); guard.source("A:options-2");
    expect(guard.current(current)).toBe(false);
  });
  it("does not let an old rejection or finally replace a newer result", async () => {
    const guard = createPlanningRequestFence(); guard.source("same-source"); const old = guard.begin();
    let reject!: (reason: Error) => void;
    const response = new Promise<void>((_, fail) => { reject = fail; });
    const state = { error: null as string | null, running: true };
    const waiting = response.catch(() => { if (guard.current(old)) state.error = "old"; }).finally(() => { if (guard.current(old)) state.running = false; });
    guard.begin(); reject(new Error("synthetic")); await waiting;
    expect(state).toEqual({ error: null, running: true });
  });
  it("tracks pending trials even before a new observation revision", () => {
    const { study } = fixture(), before = planningStudyKey(study);
    study.trials.push({ ...study.trials[0], trial_id: "new-pending", state: "pending" });
    expect(planningStudyKey(study)).not.toBe(before);
  });
  it("reads historical models but does not call them current", () => {
    const { study, model } = fixture();
    expect(validPlanningModel(model, study)).toBe(true); expect(currentPlanningModel(model, study)).toBe(true);
    study.observation_history.observation_history_sha256 = "e".repeat(64);
    expect(validPlanningModel(model, study)).toBe(true); expect(currentPlanningModel(model, study)).toBe(false);
    expect(validPlanningModel({ ...model, snapshot_sha256: "bad" }, study)).toBe(false);
  });
  it("rejects wrong model/hash, duplicate page identities and partial pages", () => {
    const { study, model, page } = fixture();
    expect(validPlanningPage(page, model, study.factors)).toBe(true);
    expect(validPlanningPage({ ...page, revision: { ...page.revision, model_sha256: "9".repeat(64) } }, model, study.factors)).toBe(false);
    expect(validPlanningPage({ ...page, revision: { ...page.revision, row_count: 2 } }, model, study.factors)).toBe(false);
    expect(validPlanningPage({ ...page, revision: { ...page.revision, row_count: 2 }, items: [...page.items, ...page.items] }, model, study.factors)).toBe(false);
  });
  it("requires exact evaluation request identity and separates model/eligibility freshness", () => {
    const { model, evaluation } = fixture(), points = [{ x: .4 }];
    expect(validPlanningEvaluation(evaluation, model, points)).toBe(true);
    expect(validPlanningEvaluation({ ...evaluation, eligibility_is_current: false }, model, points)).toBe(true);
    expect(validPlanningEvaluation(evaluation, model, [{ x: .6 }])).toBe(false);
    expect(validPlanningEvaluation({ ...evaluation, model_sha256: "d".repeat(64) }, model, points)).toBe(false);
    evaluation.items[0].desirability_moments.mean = NaN;
    expect(validPlanningEvaluation(evaluation, model, points)).toBe(false);
  });
  it("switches individual response curves using exact stored rows without changing their source", () => {
    const { evaluation } = fixture(), before = JSON.stringify(evaluation);
    const mean = planningResponseProfilePoints(evaluation, "x", "yield", "mean_raw");
    const latent = planningResponseProfilePoints(evaluation, "x", "yield", "latent_standard_deviation_raw");
    const predictive = planningResponseProfilePoints(evaluation, "x", "yield", "predictive_standard_deviation_raw");
    expect(mean).toEqual([{ rowId: evaluation.items[0].row_id, x: .4, value: 1e-8 }]);
    expect(latent[0].value).toBe(2e-8); expect(predictive[0].value).toBe(3e-8);
    expect(planningResponseProfilePoints(evaluation, "x", "cost", "mean_raw")[0].value).toBe(1000000000001);
    expect(() => planningResponseProfilePoints(evaluation, "x", "not-a-response", "mean_raw")).toThrow("bayesian_planning_response_mismatch");
    expect(JSON.stringify(evaluation)).toBe(before);
  });
});
