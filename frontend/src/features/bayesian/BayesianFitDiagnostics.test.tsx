import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, expect, it } from "vitest";
import type { DesirabilityFitCalculation } from "../../api/types/bayesianDesirability";
import { setCurrentLocale } from "../../i18n/store";
import { BayesianFitDiagnostics } from "./BayesianFitDiagnostics";
import { desirabilityBatchFixture } from "./bayesianDesirability.fixture";
import { buildDesirabilityRequest, defaultDesirabilityDraft } from "./bayesianDesirabilityDraft";
import { validDesirabilityCalculation } from "./desirabilityResponseGuard";

afterEach(() => setCurrentLocale("ko"));
it("keeps the old default and explicitly sends the new policy for q1 and q2", () => {
  const { study } = desirabilityBatchFixture();
  const draft = defaultDesirabilityDraft(study);
  expect(buildDesirabilityRequest(study, draft).request?.schema_version).toBe(4);
  for (const size of ["1", "2"]) {
    const changed = { ...draft, batchSize: size, fitPolicy: "bounded_multiscale_starts_v1" as const, randomRestarts: "2", deterministicStarts: "3" };
    const request = buildDesirabilityRequest(study, changed).request;
    expect(request?.schema_version).toBe(6);
    expect(request).toHaveProperty("fit_policy.deterministic_start_count", 3);
    expect(request?.search.hyperparameter_restart_count).toBe(2);
    expect(buildDesirabilityRequest(study, { ...changed, deterministicStarts: "1.5" }).request).toBeNull();
    expect(buildDesirabilityRequest(study, { ...changed, randomRestarts: "4" }).request).toBeNull();
  }
});
it.each(["en", "ko"] as const)("renders saved start comparisons without modifying data (%s)", locale => {
  setCurrentLocale(locale);
  const original = desirabilityBatchFixture();
  // Synthetic display fixture, not likelihood/reference evidence.
  const calculation: DesirabilityFitCalculation = { ...original.calculation, schema_version: 6,
    shared_model: { ...original.calculation.shared_model, schema_version: 6,
      response_models: original.calculation.shared_model.response_models.map(row => ({ ...row, model: {
        ...row.model, schema_version: 5, policy_version: "bo_noise_latent_fit_v4", log_marginal_likelihood: -1.23456789,
        optimizer: { ...row.model.optimizer, max_evaluations: 1000, max_iterations: 80, starts: [{
          success: false, status: 1, termination_reason: "synthetic limit", iterations: 2, evaluations: 3,
          initial_log_parameters: [0, 0, -4], final_log_parameters: [0, 1, -4], negative_log_likelihood: 2,
        }] },
        fit_diagnostics: { schema_version: 1, policy: "bounded_multiscale_starts_v1", deterministic_start_count: 1,
          screening: [{ log_parameters: [0, 0, -4], negative_log_likelihood: 3 }], refined_screen_indices: [0],
          start_initial_negative_log_likelihoods: [3], start_best_evaluations: [{ log_parameters: [0, .5, -4], negative_log_likelihood: 1.23456789, evaluation_index: 1 }],
          selected: { stage: "local_evaluation", screen_index: null, start_index: 0, log_parameters: [0, .5, -4], negative_log_likelihood: 1.23456789 },
          bound_hits: [], global_optimum_guaranteed: false,
        },
      } })),
    } };
  const before = JSON.stringify(calculation);
  const html = renderToStaticMarkup(<BayesianFitDiagnostics calculation={calculation} sourceKey="immutable-source" />);
  expect(html).toContain("-1.23456789");
  expect(html).toContain("Yield &lt;raw&gt;");
  expect(html).toContain(locale === "en" ? "Start numbers are not iteration history" : "시작점 번호는 반복 이력이 아닙니다");
  expect(html).toContain('data-y="-1.23456789"');
  expect(JSON.stringify(calculation)).toBe(before);
  expect(validDesirabilityCalculation(calculation, original.study)).toBe(true);
});
