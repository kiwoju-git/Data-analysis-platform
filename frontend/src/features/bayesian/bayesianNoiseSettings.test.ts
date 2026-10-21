import { describe, expect, it } from "vitest";
import { buildNoisePolicy, defaultNoiseDraft, strictBoNumber } from "./boNoisePolicy";

describe("noise-aware BO request boundary", () => {
  it("defaults to estimated variance, raw observations and 64 joint samples", () => {
    const result = buildNoisePolicy(defaultNoiseDraft, [{ factor_id: "factor-a" }]);
    expect(result.errors).toEqual({});
    expect(result.payload?.surrogate).toEqual({ noise_mode: "estimate", initial_noise_variance_scaled: 0.01,
      lower_noise_variance_scaled: 1e-6, upper_noise_variance_scaled: 1, fixed_noise_sd: null });
    expect(result.payload?.observation_policy.mode).toBe("retain_raw");
    expect(result.payload?.batch_options).toEqual({ posterior_sample_count: 64, min_batch_distance_normalized: 0 });
  });
  it.each(["", " ", "NaN", "Infinity", "1abc", "0x10"])("rejects incomplete numeric input %s", value => {
    expect(strictBoNumber(value)).toBeNull();
  });
  it("never sorts reversed variance bounds or silently rounds sample counts", () => {
    expect(buildNoisePolicy({ ...defaultNoiseDraft, noiseLower: "1", noiseUpper: "1e-6" }, []).errors.noiseInitial).toBe("bounds");
    expect(buildNoisePolicy({ ...defaultNoiseDraft, sampleCount: "16.5" }, []).errors.sampleCount).toBe("samples");
  });
  it("uses raw-unit fixed SD only in fixed mode", () => {
    expect(buildNoisePolicy({ ...defaultNoiseDraft, noiseMode: "fixed", fixedNoiseSd: "1e-6" }, []).payload?.surrogate.fixed_noise_sd).toBe(1e-6);
    expect(buildNoisePolicy({ ...defaultNoiseDraft, noiseMode: "near_noiseless", fixedNoiseSd: "2" }, []).payload?.surrogate.fixed_noise_sd).toBeNull();
  });
  it("requires every factor tolerance, keeps factor identity and never changes the draft", () => {
    const id = "\uE000sensitive-label\uE001";
    const draft = { ...defaultNoiseDraft, observationMode: "nearby_diagnostics" as const, nearbyTolerances: { [id]: "0.01" } };
    const before = JSON.stringify(draft);
    expect(buildNoisePolicy(draft, [{ factor_id: id }, { factor_id: "b" }]).payload).toBeNull();
    const result = buildNoisePolicy(draft, [{ factor_id: id }]);
    expect(result.payload?.observation_policy.nearby_tolerances).toEqual({ [id]: 0.01 });
    expect(JSON.stringify(draft)).toBe(before);
  });
});
