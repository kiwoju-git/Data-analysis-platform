import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import type { BayesianStudyResponse } from "../../api";
import { getCurrentLocale, setCurrentLocale } from "../../i18n/store";
import { BayesianVectorStudySnapshot } from "./BayesianVectorStudySnapshot";

describe("stored response-vector boundary", () => {
  const initialLocale = getCurrentLocale();
  afterEach(() => setCurrentLocale(initialLocale));

  it.each(["ko", "en"] as const)("preserves exact response identity and values in %s", locale => {
    setCurrentLocale(locale);
    const study = fixture();
    const before = JSON.stringify(study);
    const html = renderToStaticMarkup(<BayesianVectorStudySnapshot study={study} />);
    expect(html).toContain(locale === "ko" ? "검토는 실험을 만들지 않으며" : "Review creates no experiments");
    expect(html).toContain(locale === "ko" ? "대기 배치 전체를 한 번에 생성" : "entire pending batch atomically");
    expect(html).toContain("수율 &lt;raw&gt;");
    expect(html).toContain("1e-8");
    expect(html).toContain("1000000000001");
    expect(html).toContain("history-hash");
    expect(html).not.toContain("<input");
    expect(html).not.toContain("<button");
    expect(html).not.toContain("Expected Improvement");
    expect(JSON.stringify(study)).toBe(before);
  });

  it("does not render scalar studies as vector results", () => {
    const study = fixture();
    study.objective = { name: "Yield", unit: null, goal_type: "maximize", target_value: null,
      target_tolerance: null, direction: "maximize", observation_policy: "manual_single_observation" };
    expect(renderToStaticMarkup(<BayesianVectorStudySnapshot study={study} />)).toBe("");
  });
});

function fixture(): BayesianStudyResponse {
  return {
    study_id: "source-id", name: "Synthetic vector", definition_sha256: "definition-hash",
    completed_trial_count: 1, trial_count: 2,
    observation_history: { history_revision_id: "history-id", observation_history_sha256: "history-hash" },
    objective: { name: "Joint goals", goal_type: "desirability", observation_policy: "complete_response_vector",
      curve_policy: "derringer_suich_linear_v1", unit: null, direction: null, target_value: null, target_tolerance: null,
      responses: [{ response_id: "y", name: "수율 <raw>", unit: "mg", goal: "maximize", lower: 0, target: 1, upper: null, importance: 1 },
        { response_id: "c", name: "Cost", unit: "USD", goal: "minimize", lower: null, target: 1, upper: 2, importance: 1 }] },
    factors: [{ factor_id: "x", name: "온도", unit: "C" }],
    trials: [{ trial_id: "trial", trial_number: 1, state: "completed", objective_value: null,
      actual_coordinates: { x: 0.5 }, response_values: { c: 1000000000001, y: 1e-8 } }],
  } as unknown as BayesianStudyResponse;
}
