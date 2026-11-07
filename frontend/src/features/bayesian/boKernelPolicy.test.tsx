import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import type { BayesianCurrentBatchResponse, BayesianKernelBatchResponse, BayesianKernelKind, BayesianStudyResponse } from "../../api";
import { getCurrentLocale, setCurrentLocale } from "../../i18n/store";
import { BayesianRecommendationPanel } from "./BayesianRecommendationPanel";
import { BayesianSurrogateSummary } from "./BayesianSurrogateSummary";
import { BO_KERNEL_OPTIONS, DEFAULT_BO_KERNEL, parseBoKernelKind, savedBoKernelKind } from "./boKernelPolicy";

describe("BO numeric kernel policy and presentation", () => {
  const initialLocale = getCurrentLocale();
  afterEach(() => setCurrentLocale(initialLocale));

  it("admits exactly the four supported kernels and preserves the legacy default", () => {
    expect(DEFAULT_BO_KERNEL).toBe("matern_5_2");
    expect(BO_KERNEL_OPTIONS.map(option => option.kind)).toEqual(["matern_5_2", "matern_3_2", "gaussian", "exponential"]);
    for (const option of BO_KERNEL_OPTIONS) expect(parseBoKernelKind(option.kind)).toBe(option.kind);
    for (const value of ["rbf", "Gaussian", "cubic", " matern_5_2", "", null, {}, 1]) expect(parseBoKernelKind(value)).toBeNull();
    const legacy = { schema_version: 3, signal_kernel: { kind: "constant_times_matern_5_2_ard" } } as BayesianCurrentBatchResponse["shared_model"];
    expect(savedBoKernelKind(legacy)).toBe("matern_5_2");
  });

  it.each(["ko", "en"] as const)("keeps saved factor mapping and fitted values in %s", locale => {
    setCurrentLocale(locale);
    const model = modelFixture("gaussian");
    const before = JSON.stringify(model);
    const html = renderToStaticMarkup(<BayesianSurrogateSummary model={model} factors={[
      { factor_id: "b", name: "Pressure <user>" }, { factor_id: "a", name: "사용자 온도" },
    ]} />);
    expect(html).toContain("Gaussian (RBF)");
    expect(html).toContain("2.75");
    expect(html).toContain("0.025");
    expect(html.indexOf("사용자 온도")).toBeLessThan(html.indexOf("Pressure &lt;user&gt;"));
    expect(html).toContain(locale === "ko" ? "길이 척도" : "Length scale");
    expect(html).toContain("radial_scaled_euclidean_v1");
    expect(JSON.stringify(model)).toBe(before);
  });

  it.each(BO_KERNEL_OPTIONS)("renders the applied $label instead of the current selector default", ({ kind, label }) => {
    const html = renderToStaticMarkup(<BayesianSurrogateSummary model={modelFixture(kind)} />);
    expect(html).toContain(label);
  });

  it.each(["ko", "en"] as const)("provides a labeled native selector without changing the draft in %s", locale => {
    setCurrentLocale(locale);
    const study = {
      status: "active", trial_count: 4, recommendation_hard_trial_limit: 200, recommendation_available: true,
      factors: [], objective: { name: "사용자 반응", goal_type: "maximize", unit: "mg" },
    } as unknown as BayesianStudyResponse;
    const html = renderToStaticMarkup(<BayesianRecommendationPanel study={study} batch={null} recommendation={null}
      kernelKind="exponential" executionMode="sequential_single" batchSize="1" explorationProfile="balanced"
      customXi="0.01" totalTrialBudget="50" isRecommending={false} actionsDisabled={false}
      onExecutionModeChange={() => undefined} onBatchSizeChange={() => undefined} onExplorationProfileChange={() => undefined}
      onCustomXiChange={() => undefined} onBudgetChange={() => undefined} onRecommend={() => undefined} />);
    expect(html).toContain('for="bayesian-kernel-kind"');
    expect(html).toContain('<option value="exponential" selected="">Exponential</option>');
    expect(html).toContain(locale === "ko" ? "연속형 신호 커널" : "Continuous signal kernel");
    expect(html).toContain("사용자 반응");
  });
});

function modelFixture(family: BayesianKernelKind): BayesianKernelBatchResponse["shared_model"] {
  return {
    schema_version: 4, policy_version: "bo_noise_latent_kernels_v3", factor_ids: ["a", "b"],
    signal_kernel: { kind: "constant_times_radial_ard", family, convention: "radial_scaled_euclidean_v1",
      coordinate_system: "factor_bounds_normalized_0_1", amplitude: 2.75, length_scales: [0.025, 0.25],
      amplitude_bounds: [1e-3, 1e3], length_scale_bounds: [1e-2, 1e2], initial_amplitude: 1, initial_length_scales: [1, 1] },
  } as BayesianKernelBatchResponse["shared_model"];
}
