import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { BayesianStudyResponse } from "./api";
import { getMethodCardTags } from "./analysisMethodGuidance";
import { buildBayesianStudyRequest } from "./bayesianStudyDraft";
import { BayesianRecommendationPanel } from "./features/bayesian/BayesianRecommendationPanel";
import { LatinHypercubePanel } from "./LatinHypercubePanel";

describe("Bayesian batch and DOE presentation", () => {
  it("separates batch size, trial budget, acquisition, and exploration controls", () => {
    const html = renderToStaticMarkup(
      <BayesianRecommendationPanel
        study={studyFixture()}
        batch={null}
        recommendation={null}
        executionMode="parallel_batch"
        batchSize="4"
        explorationProfile="exploration"
        customXi="0.1"
        totalTrialBudget="50"
        isRecommending={false}
        actionsDisabled={false}
        onExecutionModeChange={() => undefined}
        onBatchSizeChange={() => undefined}
        onExplorationProfileChange={() => undefined}
        onCustomXiChange={() => undefined}
        onBudgetChange={() => undefined}
        onRecommend={() => undefined}
      />,
    );

    expect(html).toContain("여러 실험을 동시에 수행");
    expect(html).toContain("한 번에 추천할 실험 수");
    expect(html).toContain("전체 trial 예산");
    expect(html).toContain("Expected Improvement (EI)");
    expect(html).toContain("탐색 우선");
    expect(html).toContain("posterior-mean fantasy");
  });

  it("uses target goal fields without accepting executable objective code", () => {
    const request = buildBayesianStudyRequest({
      studyName: "Target study",
      factors: [
        {
          key: 1,
          factorId: "x",
          name: "Input",
          low: "0",
          high: "1",
          unit: "",
        },
      ],
      constraints: [],
      objectiveName: "pH",
      objectiveUnit: "",
      goalType: "match_target",
      targetValue: "7",
      targetTolerance: "0.2",
      initialDesignSize: "2",
      initialDesignSeed: "17",
      initialDesignPolicy: "latin_hypercube_random_cd_v1",
    });

    expect(typeof request).toBe("object");
    if (typeof request === "string") return;
    expect(request.objective).toMatchObject({
      goal_type: "match_target",
      target_value: 7,
      target_tolerance: 0.2,
    });
    expect(request.objective).not.toHaveProperty("expression");
  });

  it("renders aligned LHS setting groups and a randomization card", () => {
    const html = renderToStaticMarkup(<LatinHypercubePanel />);

    expect(html).toContain('class="doe-compact-section"');
    expect(html).toContain('class="doe-settings-matrix"');
    expect(html).toContain('class="doe-advanced-settings"');
    expect(html).toContain("doe-factor-editor");
    expect(html).toContain('class="doe-action-bar"');
    expect(html).not.toContain('class="doe-form-section"');
    expect(html).toContain("lhs-randomization-card is-selected");
    expect(html).toContain("실행 순서 무작위화");
    expect(html).toContain("compact-button");
  });

  it("keeps equivalence and Wilcoxon selection tags to four concise items", () => {
    const equivalence = getMethodCardTags("hypothesis.equivalence_tost");
    const wilcoxon = getMethodCardTags("hypothesis.one_sample_wilcoxon");

    expect(equivalence.map((tag) => tag.label)).toEqual([
      "연속형 수치",
      "한 모집단",
      "평균과 기준값 비교",
      "동등성 한계 사전 지정",
    ]);
    expect(getMethodCardTags("hypothesis.two_sample_equivalence_tost")).toHaveLength(4);
    expect(getMethodCardTags("hypothesis.paired_equivalence_tost")).toHaveLength(4);
    expect(wilcoxon.map((tag) => tag.label)).toEqual([
      "순서형·연속형",
      "한 모집단",
      "순위 기반 비교",
      "대칭성·동률 확인",
    ]);
  });
});

function studyFixture(): BayesianStudyResponse {
  return {
    study_id: "00000000-0000-4000-8000-000000000001",
    study_version_id: "00000000-0000-4000-8000-000000000002",
    name: "Yield study",
    status: "active",
    objective: {
      name: "Yield",
      unit: "%",
      goal_type: "maximize",
      target_value: null,
      target_tolerance: null,
      direction: "maximize",
      observation_policy: "manual_single_observation",
    },
    trial_count: 12,
    recommendation_hard_trial_limit: 200,
    recommendation_available: true,
    recommendation_blockers: [],
    recommendation_minimum_completed_observations: 4,
  } as unknown as BayesianStudyResponse;
}
