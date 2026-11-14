import { afterEach, describe, expect, it, vi } from "vitest";
import { createMixtureCandidates, confirmMixtureSelection, type MixtureCandidateRequest } from "./boMixture";
import { fetchBayesianStudy } from "./bayesian";

describe("mixture transport source locks", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("uses the mixture route and preserves actual closure amounts and exact source hashes", async () => {
    const fetch = vi.fn<typeof globalThis.fetch>().mockImplementation(() => Promise.resolve(new Response("{}"))); vi.stubGlobal("fetch", fetch);
    const body: MixtureCandidateRequest = { schema_version: 4, request_id: "request", candidate_set_id: "set", name: "실제 혼합물", model_id: "model", expected_model_sha256: "a".repeat(64), expected_study_version_id: "version", expected_definition_sha256: "b".repeat(64), expected_history_revision_id: "history", expected_history_sha256: "c".repeat(64), expected_trial_count: 4, source: { kind: "explicit_rows", points: [{ a: .2, b: .8, lot: "001" }] }, time_budget_ms: 60000, max_moment_evaluations: 65536 };
    const before = JSON.stringify(body);
    await createMixtureCandidates("study/a", body);
    expect(fetch.mock.calls[0][0]).toContain("study%2Fa/mixture-candidate-revisions");
    expect(fetch.mock.calls[0][1]?.body).toBe(before);
    expect(JSON.stringify(body)).toBe(before);
    await confirmMixtureSelection("study/a", "selection/b", { expected_config_sha256: "d".repeat(64), expected_result_sha256: "e".repeat(64) });
    expect(fetch.mock.calls[1][0]).toContain("study%2Fa/mixture-selections/selection%2Fb/confirm");
    expect(JSON.parse(fetch.mock.calls[1][1]?.body as string)).toEqual({ expected_config_sha256: "d".repeat(64), expected_result_sha256: "e".repeat(64) });
  });
  it("requires explicit mixture-aware readers, keeping legacy numeric contracts narrow", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ study_schema_version: 8 })))));
    await expect(fetchBayesianStudy("study")).rejects.toThrow("bayesian_mixture_typed_reader_required");
    await expect(fetchBayesianStudy("study", { includeMixed: true })).rejects.toThrow("bayesian_mixture_typed_reader_required");
    await expect(fetchBayesianStudy("study", { includeMixture: true })).resolves.toMatchObject({ study_schema_version: 8 });
  });
});
