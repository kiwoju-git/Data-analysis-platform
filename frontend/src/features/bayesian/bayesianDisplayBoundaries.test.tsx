import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";

import type { BayesianRecommendationBatchItemResponse, BayesianRecommendationResponse, BayesianStudyResponse } from "../../api";
import { bayesianRecommendationStatus } from "../../bayesianStudyDraft";
import { getCurrentLocale, setCurrentLocale } from "../../i18n/store";
import { BayesianRecommendationPanel } from "./BayesianRecommendationPanel";
import { BayesianStudySummary } from "./BayesianStudySummary";
import { BayesianTrialTable } from "./BayesianTrialTable";
import { batchReasonText, constraintText, coordinateText } from "./bayesianDisplay";

const rawName = "\uE000doe.interactionOrder.mainEffectsOnly\uE001";
const noop = () => undefined;

describe("Bayesian static display boundaries", () => {
  const originalLocale = getCurrentLocale();
  afterEach(() => setCurrentLocale(originalLocale));

  it("renders exploration labels in the current locale without translating the objective name or changing form values", () => {
    const study = studyFixture();
    const before = JSON.stringify(study);
    const render = () => renderToStaticMarkup(<BayesianRecommendationPanel
      study={study} batch={null} recommendation={null} executionMode="parallel_batch" batchSize="4"
      explorationProfile="exploration" customXi="0.1" totalTrialBudget="50" isRecommending={false}
      actionsDisabled={false} onExecutionModeChange={noop} onBatchSizeChange={noop}
      onExplorationProfileChange={noop} onCustomXiChange={noop} onBudgetChange={noop} onRecommend={noop}
    />);
    setCurrentLocale("ko");
    expect(render()).toContain("탐색 우선");
    expect(render()).toContain(`${rawName} 최대화`);
    setCurrentLocale("en");
    const english = render();
    expect(english).toContain("Exploration priority");
    expect(english).toContain(`${rawName} maximize`);
    expect(english).toContain('value="exploration"');
    expect(english).toContain('value="50"');
    expect(JSON.stringify(study)).toBe(before);
    setCurrentLocale("ko");
    expect(render()).toContain(`${rawName} 최대화`);
  });

  it("localizes study phase and trial states while preserving user names, factor IDs, and observation drafts", () => {
    const study = studyFixture();
    const observations = { "trial-a": "01.2300" };
    const renderTrials = () => renderToStaticMarkup(<BayesianTrialTable
      study={study} observations={observations} pendingTransition={null} pendingObservationBatch={false}
      isSaving={false} actionsDisabled={false} onObservationChange={noop} onObservationBatchApply={noop}
      onRequestTransition={noop} onRequestObservationBatch={noop} onConfirmTransition={noop}
      onConfirmObservationBatch={noop} onCancelTransition={noop} onCancelObservationBatch={noop}
    />);
    setCurrentLocale("ko");
    expect(renderToStaticMarkup(<BayesianStudySummary study={study} />)).toContain("초기 실험 수행 및 반응 입력");
    expect(renderTrials()).toContain(">대기<");
    setCurrentLocale("en");
    const summary = renderToStaticMarkup(<BayesianStudySummary study={study} />);
    expect(summary).toContain(rawName);
    expect(summary).not.toContain("초기 실험 수행 및 반응 입력");
    expect(renderTrials()).not.toContain(">대기<");
    expect(renderTrials()).toContain('value="01.2300"');
    expect(renderTrials()).toContain(`${rawName}=1.25000`);
    expect(observations).toEqual({ "trial-a": "01.2300" });
    expect(study.objective.name).toBe(rawName);
  });

  it("localizes recommendation state and reason independently from saved enums", () => {
    const recommendation = { is_latest: false, trial: { state: "pending" }, current_trial: { state: "completed" } } as BayesianRecommendationResponse;
    expect(bayesianRecommendationStatus(recommendation, "ko").description).toContain("completed입니다.");
    expect(bayesianRecommendationStatus(recommendation, "en").description).toBe("This is a historical recommendation snapshot. Linked trial state: completed.");
    expect(recommendation.current_trial?.state).toBe("completed");
    const item = { rank: 3, reason_code: "target_distance_reduction" } as BayesianRecommendationBatchItemResponse;
    expect(batchReasonText(item, "ko")).toContain("후보 3은");
    expect(batchReasonText(item, "en")).toContain("candidate 3 was chosen");
    expect(item).toEqual({ rank: 3, reason_code: "target_distance_reduction" });
  });

  it("never treats coordinate or constraint factor identity as system text", () => {
    for (const locale of ["ko", "en"] as const) {
      setCurrentLocale(locale);
      expect(coordinateText({ [rawName]: 1.25 })).toBe(`${rawName}=1.25000`);
      expect(constraintText({ terms: [{ factor_id: rawName, coefficient: 2 }], relation: "less_than_or_equal", bound: 3 }))
        .toBe(`2.00000×${rawName} ≤ 3.00000`);
    }
  });
});

function studyFixture(): BayesianStudyResponse {
  return {
    study_id: "00000000-0000-4000-8000-000000000001", study_version_id: "00000000-0000-4000-8000-000000000002",
    name: rawName, status: "active", objective: { name: rawName, unit: "%", goal_type: "maximize", target_value: null, target_tolerance: null },
    trial_count: 1, completed_trial_count: 0, recommendation_hard_trial_limit: 200, recommendation_available: true,
    recommendation_blockers: [], recommendation_minimum_completed_observations: 4, predecessor_study_id: null,
    factors: [{ factor_id: rawName, name: rawName, order: 1, domain_kind: "continuous", low: 0, high: 2, unit: null }],
    trials: [{ trial_id: "trial-a", trial_number: 1, origin: "initial_design", state: "pending", actual_coordinates: { [rawName]: 1.25 }, objective_value: null }],
    constraints: [], initial_design: { policy: "latin_hypercube_random_cd_v1", generated_size: 1, seed: 17 },
    observation_history: { history_revision_id: "history-a" }, method_version: "0.1.0", study_schema_version: 1,
    definition_sha256: "hash", app_version: "test",
  } as unknown as BayesianStudyResponse;
}
