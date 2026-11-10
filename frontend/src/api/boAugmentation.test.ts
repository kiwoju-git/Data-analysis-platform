import { afterEach, describe, expect, it, vi } from "vitest";
import { createAugmentationCandidates, createAugmentation, confirmAugmentation, fetchAugmentation, fetchAugmentationBatch, fetchAugmentationReportSource } from "./boAugmentation";
import type { CandidateRevisionCreateRequestV2 } from "./types/boAugmentation";
import { augmentationFixture } from "../features/bayesian/boAugmentation.fixture";
import { augmentationSource } from "../features/bayesian/boAugmentationDraft";

describe("augmentation explicit versioned transport", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("preserves model-free null identities and user text byte meaning", async () => {
    const { study, page } = augmentationFixture();
    const fetch = vi.fn<typeof globalThis.fetch>().mockResolvedValue(new Response("{}")); vi.stubGlobal("fetch", fetch);
    const body: CandidateRevisionCreateRequestV2 = { ...augmentationSource(study), schema_version: 2, request_id: study.study_id,
      candidate_set_id: page.revision.candidate_set_id, expected_head_revision_id: null, name: '한글 "raw" \\ \n \uE000keep\uE001',
      model_id: null, expected_model_sha256: null, source: { kind: "explicit_rows", points: [{ x: .125 }] }, duplicate_tolerance: .0003, include_constraint_violations: true };
    const before = JSON.stringify(body); await createAugmentationCandidates("study/one", body);
    expect(fetch.mock.calls[0][0]).toContain("study%2Fone/candidate-revisions"); expect(fetch.mock.calls[0][1]?.body).toBe(before);
    expect(JSON.stringify(body)).toBe(before);
  });
  it("never automatically retries a selection POST after disconnect", async () => {
    const { request } = augmentationFixture();
    const fetch = vi.fn<typeof globalThis.fetch>().mockRejectedValue(new TypeError("offline")); vi.stubGlobal("fetch", fetch);
    await expect(createAugmentation("study", request)).rejects.toThrow("api_unreachable");
    expect(fetch).toHaveBeenCalledTimes(1); expect(fetch.mock.calls[0][1]?.body).toBe(JSON.stringify(request));
  });
  it("retries confirmation only when explicitly called, with identical source hashes", async () => {
    const { selection } = augmentationFixture(), body = { expected_config_sha256: selection.config_sha256, expected_result_sha256: selection.result_sha256 };
    const fetch = vi.fn<typeof globalThis.fetch>().mockRejectedValueOnce(new TypeError("offline")).mockResolvedValue(new Response("{}")); vi.stubGlobal("fetch", fetch);
    await expect(confirmAugmentation("study", selection.selection_id, body)).rejects.toThrow("api_unreachable"); expect(fetch).toHaveBeenCalledTimes(1);
    await confirmAugmentation("study", selection.selection_id, body); expect(fetch).toHaveBeenCalledTimes(2);
    expect(fetch.mock.calls[0][1]?.body).toBe(fetch.mock.calls[1][1]?.body);
  });
  it("opens exact source and report descriptor without creating another selection", async () => {
    const fetch = vi.fn<typeof globalThis.fetch>().mockImplementation(() => Promise.resolve(new Response("{}"))); vi.stubGlobal("fetch", fetch);
    await fetchAugmentation("study/one", "selection/exact"); await fetchAugmentationBatch("study/one", "batch/exact"); await fetchAugmentationReportSource("study/one", "batch/exact");
    expect(fetch.mock.calls.map(call => call[0])).toEqual([
      "/api/v1/bayesian-studies/study%2Fone/augmentations/selection%2Fexact",
      "/api/v1/bayesian-studies/study%2Fone/augmentation-batches/batch%2Fexact",
      "/api/v1/bayesian-studies/study%2Fone/augmentation-batches/batch%2Fexact/report-source",
    ]);
    expect(fetch.mock.calls.every(call => call[1]?.method === undefined && call[1]?.body === undefined)).toBe(true);
  });
});
