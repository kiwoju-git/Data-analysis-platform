import { afterEach, describe, expect, it, vi } from "vitest";
import { createCandidateRevision, createPlanningModel, fetchCandidatePage, fetchPlanningBatch, fetchPlanningBatchReportSource, listPlanningSelections } from "./boPlanning";
import type { CandidateRevisionCreateRequest, PlanningModelCreateRequest } from "./types/boPlanning";

describe("planning transport", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("preserves request bytes and does not retry a failed POST", async () => {
    const fetch = vi.fn<typeof globalThis.fetch>().mockRejectedValue(new TypeError("offline")); vi.stubGlobal("fetch", fetch);
    const body = { request_id: "same-id", fit: { schema_version: 7 } } as PlanningModelCreateRequest;
    await expect(createPlanningModel("study", body)).rejects.toThrow("api_unreachable");
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][1]?.body).toBe(JSON.stringify(body));
  });
  it("does not translate user names or private-use tokens in candidate payloads", async () => {
    const fetch = vi.fn<typeof globalThis.fetch>().mockResolvedValue(new Response("{}", { headers: { "Content-Type": "application/json" } })); vi.stubGlobal("fetch", fetch);
    const body: CandidateRevisionCreateRequest = { name: '한글 "raw" \\ \n \uE000keep\uE001', request_id: "id", source: { kind: "explicit_rows", points: [{ x: .25 }] },
      model_id: "model", expected_model_sha256: "a".repeat(64), expected_history_revision_id: "history", expected_history_sha256: "b".repeat(64),
      expected_trial_count: 4, candidate_set_id: "set", expected_head_revision_id: null, include_constraint_violations: true };
    const original = JSON.stringify(body);
    await createCandidateRevision("study/one", body);
    expect(fetch.mock.calls[0][0]).toContain("study%2Fone/candidate-revisions");
    expect(fetch.mock.calls[0][1]?.body).toBe(original); expect(JSON.stringify(body)).toBe(original);
  });
  it("requests bounded pages without whole-table state transfer", async () => {
    const fetch = vi.fn<typeof globalThis.fetch>().mockResolvedValue(new Response("{}")); vi.stubGlobal("fetch", fetch);
    await fetchCandidatePage("study", "revision", 50, 50);
    expect(fetch.mock.calls[0][0]).toContain("candidate-revisions/revision?offset=50&limit=50");
    expect(fetch.mock.calls[0][1]?.method).toBeUndefined();
  });
  it("reads selection summaries without a calculation or proof payload", async () => {
    const summary = { selection_id: "selection", study_id: "study", study_version_id: "version", model_id: "model",
      candidate_revision_id: "revision", config_sha256: "a".repeat(64), result_sha256: "b".repeat(64), selected_count: 2,
      created_at: "2026-11-10", source_is_current: true, confirmed_batch_id: null };
    const fetch = vi.fn<typeof globalThis.fetch>().mockResolvedValue(new Response(JSON.stringify({ items: [summary] }))); vi.stubGlobal("fetch", fetch);
    const result = await listPlanningSelections("study");
    expect(result.items).toEqual([summary]); expect(result.items[0].selected_count).toBe(2);
    expect(result.items[0]).not.toHaveProperty("calculation"); expect(fetch).toHaveBeenCalledTimes(1);
  });
  it("reads the exact saved batch and its server-issued report descriptor without posting", async () => {
    const fetch = vi.fn<typeof globalThis.fetch>().mockImplementation(() => Promise.resolve(new Response("{}"))); vi.stubGlobal("fetch", fetch);
    await fetchPlanningBatch("study/one", "batch/exact");
    await fetchPlanningBatchReportSource("study/one", "batch/exact");
    expect(fetch.mock.calls.map(call => call[0])).toEqual([
      "/api/v1/bayesian-studies/study%2Fone/planning-batches/batch%2Fexact",
      "/api/v1/bayesian-studies/study%2Fone/planning-batches/batch%2Fexact/report-source",
    ]);
    expect(fetch.mock.calls.every(call => call[1]?.method === undefined && call[1]?.body === undefined)).toBe(true);
  });
});
