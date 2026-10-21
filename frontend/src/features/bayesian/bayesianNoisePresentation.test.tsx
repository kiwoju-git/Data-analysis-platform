import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import type { BayesianNoiseBatchResponse, BayesianStudyResponse } from "../../api";
import { getCurrentLocale, setCurrentLocale } from "../../i18n/store";
import { BayesianNoiseBatchResult } from "./BayesianNoiseBatchResult";
import { BayesianNoiseSettings } from "./BayesianNoiseSettings";
import { defaultNoiseDraft } from "./boNoisePolicy";

describe("BO V2 presentation", () => {
  const originalLocale = getCurrentLocale();
  afterEach(() => setCurrentLocale(originalLocale));
  it.each(["ko", "en"] as const)("separates actual evidence and planning uncertainty in %s without mutating values", locale => {
    setCurrentLocale(locale);
    const batch = fixture();
    const before = JSON.stringify(batch);
    const html = renderToStaticMarkup(<BayesianNoiseBatchResult batch={batch} study={{ objective: { unit: "mg" } }} />);
    expect(html).toContain("Latent SD");
    expect(html).toContain(locale === "ko" ? "새 관측 predictive SD" : "New-observation predictive SD");
    expect(html).toContain(locale === "ko" ? "계획상 조건부 latent SD" : "Planning conditional latent SD");
    expect(html).toContain("18446744073709551615");
    expect(html).toContain("1e-6");
    expect(html).toContain("2e-6");
    expect(html).toContain("&lt;synthetic&gt;");
    expect(html).toContain(locale === "ko" ? "학습 데이터 변경 없음" : "training data unchanged");
    expect(html).toContain("synthetic-warning");
    expect(JSON.stringify(batch)).toBe(before);
  });
  it("links invalid bounds to their fields and preserves full factor identity", () => {
    setCurrentLocale("en");
    const study = { factors: [{ factor_id: "<raw>", name: "Full factor <name>", unit: "mg" }], objective: { unit: "mg" } } as unknown as BayesianStudyResponse;
    const html = renderToStaticMarkup(<BayesianNoiseSettings study={study} disabled={false} onChange={() => undefined}
      draft={{ ...defaultNoiseDraft, noiseLower: "1", noiseUpper: "0.1", observationMode: "nearby_diagnostics" }} />);
    expect(html).toContain('aria-describedby="bo-policy-noiseUpper-error"');
    expect(html).toContain('id="bo-policy-noiseUpper-error"');
    expect(html).toContain("Full factor &lt;name&gt;");
    expect(html).toContain('aria-invalid="true"');
  });
});

function fixture(): BayesianNoiseBatchResponse {
  return {
    result_schema_version: 2, batch_state: "pending", source_history_revision_id: "synthetic-history",
    shared_model: { observation_noise_sd_raw: 1e-6, noise: { mode: "estimate", fitted_variance_scaled: 1e-2, bounds_scaled: [1e-6, 1] }, jitter: 1e-8,
      optimizer: { name: "L-BFGS-B", evaluations: 20, restarts: 1, starts: [{ success: true, termination_reason: "converged" }] } },
    incumbent: { best_observed_objective: 4e-6, latent_incumbent_value_raw: 3e-6, latent_incumbent_distance_raw: null, xi_standardized: 0.01 },
    observation_view: { mode: "nearby_diagnostics", raw_observation_count: 3, unique_condition_count: 2, effective_training_count: 3,
      groups: [{ member_trial_ids: ["one", "two"], n: 2, mean: 1e-6, within_ss: 2e-12 }],
      nearby_diagnostics: { changes_training_data: false, units: "actual", groups: [{ member_trial_ids: ["one", "three"], maximum_normalized_distance: 0.1,
        maximum_axis_distances: { "<synthetic>": 0.1 }, response_range: [1e-6, 2e-6], response_sample_variance: 5e-13 }] } },
    items: [{ item_id: "item", rank: 1, actual_coordinates: { "<synthetic>": 0.25 }, predicted_objective_mean: 1e-6, latent_standard_deviation: 1e-6,
      predictive_standard_deviation: 2e-6, acquisition_value_raw: 2e-8, acquisition_value_standardized: 0.01,
      current_trial: { state: "pending" }, nearest_existing_distance: 0.1, nearest_selected_distance: null, constraint_evaluations: [],
      planning: { effective_sample_count: 0, requested_sample_count: 64, conditional_latent_sd_scaled: 0.1, conditioned_on_selected_ranks: [], sample_seed: "18446744073709551615" } }],
    search_budget: { searches: [{ termination_reason: "budget", all_acquisitions_zero: true }] }, warnings: ["synthetic-warning"], limitations: ["Plug-in, not qNEI"],
  } as unknown as BayesianNoiseBatchResponse;
}
