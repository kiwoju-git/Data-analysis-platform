import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setCurrentLocale } from "../../i18n/store";
import { BayesianPlanningPanel, PlanningFitSummary, PlanningProfileChart } from "./BayesianPlanningPanel";
import { desirabilityFixture } from "./bayesianDesirability.fixture";
import { planningBatchFixture } from "./boPlanning.fixture";
import type { PlanningEvaluationResponse } from "../../api/types/boPlanning";

describe("planning panel initial display boundary", () => {
  afterEach(() => setCurrentLocale("ko"));
  it.each(["ko", "en"] as const)("renders source controls without issuing a fit in %s", locale => {
    setCurrentLocale(locale);
    const { study } = desirabilityFixture();
    const html = renderToStaticMarkup(<BayesianPlanningPanel study={study} fitRequest={null} onConfirmed={vi.fn()} />);
    expect(html).toContain(locale === "en" ? "Saved model, candidates and profiler" : "저장 모형 · 후보표 · Profiler");
    expect(html).toContain(locale === "en" ? "predictions are not measurements" : "예측값은 측정 결과가 아닙니다");
    expect(html).toContain(locale === "en" ? "Saved selections" : "저장 선택");
    expect(html).not.toContain("<svg onload");
    expect(html).toMatch(/disabled=""[^>]*><svg[^]*?Fit and save model|disabled=""[^>]*><svg[^]*?모형 적합 및 저장/);
  });
  it("does not silently turn a scalar study into desirability", () => {
    setCurrentLocale("en"); const { study } = desirabilityFixture();
    study.study_schema_version = 4;
    const before = JSON.stringify(study);
    const html = renderToStaticMarkup(<BayesianPlanningPanel study={study} fitRequest={null} onConfirmed={vi.fn()} />);
    expect(html).toContain("Existing single-response studies remain unchanged");
    expect(html).not.toContain("Fit and save model"); expect(JSON.stringify(study)).toBe(before);
  });
  it.each(["continuous", "discrete_numeric"] as const)("uses only applied %s rows for separate response mean charts", domain => {
    setCurrentLocale("en"); const { study, batch } = planningBatchFixture();
    study.factors[0].domain_kind = domain;
    if (domain === "discrete_numeric") study.factors[0].step = .25;
    const items = batch.calculation.items.map(row => ({ ...row, prediction_source: "completed_observations_base_posterior" as const }));
    const response: PlanningEvaluationResponse = { schema_version: 1, model_id: batch.source.model_id, model_sha256: batch.source.model_sha256, request_sha256: "e".repeat(64), items,
      source_is_current: true, eligibility_source_trial_count: 4, eligibility_coordinates_sha256: "d".repeat(64), eligibility_is_current: true, model_refit: false };
    const profile = { axis: "x", points: items.map(row => row.actual_coordinates), response }, before = JSON.stringify(profile);
    const html = renderToStaticMarkup(<PlanningProfileChart profile={profile} study={study} sourceKey={`${batch.source.model_sha256}:${response.request_sha256}`} />);
    expect(html).toContain('class="bo-profile-detail"'); expect(html).toContain('class="bo-profile-grid"');
    expect((html.match(/data-profile-kind="response"/g) ?? [])).toHaveLength(batch.objective.responses.length);
    expect((html.match(/data-profile-kind="composite"/g) ?? [])).toHaveLength(1);
    for (const definition of batch.objective.responses) {
      expect(html).toContain(`data-response-id="${definition.response_id}"`);
      expect(html).toContain(`${definition.name.replace("<", "&lt;").replace(">", "&gt;")} (${definition.unit})`);
      for (const row of items) {
        const value = row.response_predictions.find(item => item.response_id === definition.response_id)!.mean_raw;
        expect(html).toContain(`data-x="${row.actual_coordinates.x}" data-y="${value}"`);
      }
    }
    expect(JSON.stringify(profile)).toBe(before);
    expect(renderToStaticMarkup(<PlanningProfileChart profile={{ ...profile, axis: null }} study={study} sourceKey="same" />)).toBe("");
  });
  it.each(["en", "ko"] as const)("keeps stored optimizer warnings and metadata visible in %s", locale => {
    setCurrentLocale(locale); const { calculation } = desirabilityFixture();
    const model = { model_id: "model", snapshot_sha256: "a".repeat(64), objective: calculation.objective,
      response_models: calculation.shared_model.response_models, warnings: ["bayesian_optimization_model_convergence_warning", "bayesian_surrogate_noise_bound", "unknown_saved_warning"] };
    const before = JSON.stringify(model);
    const html = renderToStaticMarkup(<PlanningFitSummary model={model} />);
    expect(html).toContain(locale === "en" ? "Saved fit warnings" : "저장된 적합 경고");
    expect(html).toContain(locale === "en" ? "did not converge" : "수렴하지 않았습니다");
    expect(html).toContain(locale === "en" ? "measurement variance reached" : "측정 분산이 적합 경계");
    expect(html).toContain("unknown_saved_warning"); expect(html).toContain("role=\"status\"");
    expect(html).toContain("Yield &lt;raw&gt;"); expect(html).toContain("L-BFGS-B"); expect(html).toContain("converged");
    expect(html).toContain(locale === "en" ? "Numerical jitter (not measurement noise)" : "수치 안정화 jitter");
    expect(html).toContain("1e-8"); expect(html).not.toContain("<details");
    expect(JSON.stringify(model)).toBe(before);
  });
});
