import { afterEach, describe, expect, it, vi } from "vitest";
import { renewAugmentation } from "../../api/boAugmentation";
import { augmentationFixture } from "./boAugmentation.fixture";
import { augmentationNeedsRenewal, validAugmentationRenewal } from "./boAugmentationRenewal";

describe("explicit historical augmentation renewal", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("detects absent policy, not schema age or confirm-only/model-free results", () => {
    const { selection } = augmentationFixture(true);
    for (const row of selection.calculation.selected_rows) {
      if ("acquisition" in row && row.acquisition) delete row.acquisition.numerical_policy;
    }
    expect(augmentationNeedsRenewal(selection)).toBe(true);
    for (const row of selection.calculation.selected_rows) {
      if ("acquisition" in row && row.acquisition) row.acquisition.numerical_policy = "positive_beta_integral_v2";
    }
    expect(augmentationNeedsRenewal(selection)).toBe(false);
    expect(augmentationNeedsRenewal(augmentationFixture().selection)).toBe(false);
  });
  it("uses only explicit parent hashes and preserves request id across manual retries", async () => {
    const { selection, study } = augmentationFixture(true);
    const body = { request_id: study.study_id, expected_config_sha256: selection.config_sha256, expected_result_sha256: selection.result_sha256 };
    const fetch = vi.fn<typeof globalThis.fetch>().mockRejectedValueOnce(new TypeError("offline")).mockResolvedValue(new Response("{}"));
    vi.stubGlobal("fetch", fetch);
    await expect(renewAugmentation("study/one", selection.selection_id, body)).rejects.toThrow("api_unreachable");
    expect(fetch).toHaveBeenCalledTimes(1);
    await renewAugmentation("study/one", selection.selection_id, body);
    expect(fetch.mock.calls[0][0]).toBe(`/api/v1/bayesian-studies/study%2Fone/augmentations/${selection.selection_id}/renew`);
    expect(fetch.mock.calls[0][1]?.body).toBe(JSON.stringify(body));
    expect(fetch.mock.calls[1][1]?.body).toBe(JSON.stringify(body));
  });
  it("rejects changed original options, forged lineage and old-policy new results", () => {
    const { selection: original, study } = augmentationFixture(true);
    const requestId = "a1111111-1111-4111-8111-111111111111";
    const selected = structuredClone(original);
    selected.selection_id = "b1111111-1111-4111-8111-111111111111";
    selected.request.request_id = requestId;
    for (const row of selected.calculation.selected_rows) {
      if ("acquisition" in row && row.acquisition) row.acquisition.numerical_policy = "positive_beta_integral_v2";
    }
    const value = { selection: selected, lineage: {
      schema_version: 1 as const, study_version_id: study.study_version_id,
      renewed_selection_id: selected.selection_id, original_selection_id: original.selection_id,
      original_config_sha256: original.config_sha256, original_result_sha256: original.result_sha256,
      numerical_policy: "positive_beta_integral_v2" as const, created_at: selected.created_at,
    } };
    expect(validAugmentationRenewal(value, study, original, requestId)).toBe(true);
    const bad = structuredClone(value); bad.selection.request.batch_size += 1;
    expect(validAugmentationRenewal(bad, study, original, requestId)).toBe(false);
    expect(validAugmentationRenewal({ ...value, lineage: { ...value.lineage, original_result_sha256: "f".repeat(64) } }, study, original, requestId)).toBe(false);
    for (const row of value.selection.calculation.selected_rows) {
      if ("acquisition" in row && row.acquisition) delete row.acquisition.numerical_policy;
    }
    expect(validAugmentationRenewal(value, study, original, requestId)).toBe(false);
  });
});
