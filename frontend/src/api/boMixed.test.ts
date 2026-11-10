import { afterEach, describe, expect, it, vi } from "vitest";
import { abandonMixedTrial, closeMixedStudy, confirmMixedSelection, createMixedCandidateRevision, createMixedReplicates, createMixedSelection, fetchMixedBatch, fetchMixedBatchReportSource, fetchMixedCandidatePage, fetchMixedSelection, recordMixedObservations } from "./boMixed";
import { mixedPlanningFixture } from "../features/bayesian/boMixedPlanning.test.fixture";
import { mixedSource } from "../features/bayesian/boMixedPlanningDraft";
import { fetchBayesianStudy } from "./bayesian";

describe("mixed source transport stays separate from numeric workflows", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("preserves exact nominal text and model-free identities", async () => {
    const { study, page } = mixedPlanningFixture(), fetch = vi.fn<typeof globalThis.fetch>().mockResolvedValue(new Response("{}")); vi.stubGlobal("fetch", fetch);
    const body = { ...mixedSource(study), schema_version: 3 as const, request_id: study.study_id, candidate_set_id: page.revision.candidate_set_id, name: '한글 "raw" \uE000keep\uE001', expected_head_revision_id: null,
      model_id: null, expected_model_sha256: null, duplicate_tolerance: 1e-6, ordinal_rank_distance: false, include_constraint_violations: true, source: { kind: "explicit_rows" as const, points: [{ x: .2, material: "001" }] } };
    const before = JSON.stringify(body); await createMixedCandidateRevision("study/a", body);
    expect(fetch.mock.calls[0][0]).toContain("study%2Fa/mixed-candidate-revisions"); expect(fetch.mock.calls[0][1]?.body).toBe(before); expect(JSON.stringify(body)).toBe(before);
  });
  it("keeps observation vector zero and uses the existing batch lifecycle route", async () => {
    const { study } = mixedPlanningFixture(), fetch = vi.fn<typeof globalThis.fetch>().mockResolvedValue(new Response("{}")); vi.stubGlobal("fetch", fetch);
    const body = { request_id: study.study_id, expected_study_version_id: study.study_version_id, expected_history_revision_id: study.observation_history.history_revision_id, expected_observation_history_sha256: study.observation_history.observation_history_sha256,
      observations: [{ trial_id: study.trials[0].trial_id, response_values: { yield: 0, cost: -1e-8 } }] };
    await recordMixedObservations(study.study_id, body);
    expect(fetch.mock.calls[0][0]).toBe(`/api/v1/bayesian-studies/${study.study_id}/observations/batch`);
    expect(fetch.mock.calls[0][1]?.method).toBe("PUT");
    expect(fetch.mock.calls[0][1]?.body).toBe(JSON.stringify(body));
  });
  it("never auto-retries review/confirm POST after a lost connection", async () => {
    const { selection } = mixedPlanningFixture(), fetch = vi.fn<typeof globalThis.fetch>().mockRejectedValue(new TypeError("offline")); vi.stubGlobal("fetch", fetch);
    await expect(createMixedSelection("study", selection.request)).rejects.toThrow("api_unreachable"); expect(fetch).toHaveBeenCalledTimes(1);
    const body = { expected_config_sha256: selection.config_sha256, expected_result_sha256: selection.result_sha256 };
    await expect(confirmMixedSelection("study", selection.selection_id, body)).rejects.toThrow("api_unreachable"); expect(fetch).toHaveBeenCalledTimes(2);
    await expect(confirmMixedSelection("study", selection.selection_id, body)).rejects.toThrow("api_unreachable"); expect(fetch.mock.calls[1][1]?.body).toBe(fetch.mock.calls[2][1]?.body);
  });
  it("uses the declared POST methods and exact payloads for replicate, abandon and close", async () => {
    const { study } = mixedPlanningFixture(), fetch = vi.fn<typeof globalThis.fetch>().mockImplementation(() => Promise.resolve(new Response("{}"))); vi.stubGlobal("fetch", fetch);
    const replicate = { request_id: study.study_id, expected_history_revision_id: study.observation_history.history_revision_id,
      expected_history_sha256: study.observation_history.observation_history_sha256, count: 2, total_trial_budget: 200, confirm_replicate_intent: true as const };
    const abandon = { expected_history_revision_id: study.observation_history.history_revision_id, intent: "continue_study" as const };
    const close = { request_id: study.study_id, expected_study_version_id: study.study_version_id, expected_history_revision_id: study.observation_history.history_revision_id,
      expected_observation_history_sha256: study.observation_history.observation_history_sha256, target_status: "completed" as const, reason_code: "confirmation_complete" as const, note: "Synthetic explicit closure" };
    await createMixedReplicates("study/a", "trial/b", replicate);
    await abandonMixedTrial("study/a", "trial/b", abandon);
    await closeMixedStudy("study/a", close);
    expect(fetch.mock.calls.map(call => call[0])).toEqual(["/api/v1/bayesian-studies/study%2Fa/trials/trial%2Fb/replicates", "/api/v1/bayesian-studies/study%2Fa/trials/trial%2Fb/abandon", "/api/v1/bayesian-studies/study%2Fa/close"]);
    expect(fetch.mock.calls.map(call => call[1]?.method)).toEqual(["POST", "POST", "POST"]);
    expect(fetch.mock.calls.map(call => call[1]?.body)).toEqual([replicate, abandon, close].map(body => JSON.stringify(body)));
  });
  it("does not automatically resend an observation PUT after disconnect", async () => {
    const { study } = mixedPlanningFixture(), fetch = vi.fn<typeof globalThis.fetch>().mockRejectedValue(new TypeError("offline")); vi.stubGlobal("fetch", fetch);
    const body = { request_id: study.study_id, expected_study_version_id: study.study_version_id, expected_history_revision_id: study.observation_history.history_revision_id,
      expected_observation_history_sha256: study.observation_history.observation_history_sha256, observations: [{ trial_id: study.trials[0].trial_id, response_values: { yield: 0, cost: 1 } }] };
    await expect(recordMixedObservations("study", body)).rejects.toThrow("api_unreachable");
    expect(fetch).toHaveBeenCalledTimes(1); expect(fetch.mock.calls[0][1]?.method).toBe("PUT"); expect(fetch.mock.calls[0][1]?.body).toBe(JSON.stringify(body));
  });
  it("opens exact schema10 source and server-issued report descriptor with GET", async () => {
    const fetch = vi.fn<typeof globalThis.fetch>().mockImplementation(() => Promise.resolve(new Response("{}"))); vi.stubGlobal("fetch", fetch);
    await fetchMixedSelection("study/a", "selection/b"); await fetchMixedCandidatePage("study/a", "revision/b", 50); await fetchMixedBatch("study/a", "batch/b"); await fetchMixedBatchReportSource("study/a", "batch/b");
    expect(fetch.mock.calls.map(call => call[0])).toEqual(["/api/v1/bayesian-studies/study%2Fa/mixed-selections/selection%2Fb", "/api/v1/bayesian-studies/study%2Fa/mixed-candidate-revisions/revision%2Fb?offset=50&limit=50", "/api/v1/bayesian-studies/study%2Fa/mixed-planning-batches/batch%2Fb", "/api/v1/bayesian-studies/study%2Fa/mixed-planning-batches/batch%2Fb/report-source"]);
    expect(fetch.mock.calls.every(call => call[1]?.method === undefined && call[1]?.body === undefined)).toBe(true);
  });
  it("requires explicit typed opt-in before a generic study reader accepts schema7", async () => {
    const { study } = mixedPlanningFixture(), fetch = vi.fn<typeof globalThis.fetch>().mockImplementation(() => Promise.resolve(new Response(JSON.stringify(study)))); vi.stubGlobal("fetch", fetch);
    await expect(fetchBayesianStudy(study.study_id)).rejects.toThrow("bayesian_mixed_typed_reader_required");
    expect((await fetchBayesianStudy(study.study_id, { includeMixed: true })).study_schema_version).toBe(7);
  });
});
