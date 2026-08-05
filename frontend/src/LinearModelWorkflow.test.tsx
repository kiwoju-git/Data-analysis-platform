import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { LinearModelFitResults } from "./LinearModelFitResults";
import { RegressionManualPredictionPanel } from "./RegressionManualPredictionPanel";
import { RegressionPastedPredictionPanel } from "./RegressionPastedPredictionPanel";
import { parseRegressionPastedPredictionPreview } from "./regressionPastedPredictionPreview";
import type { LinearModelResult } from "./api";

function resultFixture(): LinearModelResult {
  return {
    schema_version: 5,
    sample: { n_used: 12, df_residual: 10 },
    predictors: [
      {
        column_id: "afucose",
        display_name: "afucose",
        predictor_kind: "numeric",
      },
    ],
    equation: {
      response_label: "adcc",
      intercept: 21.3,
      terms: [],
      display_equation: "adcc = 21.3 + 13.8 * afucose",
      coefficient_precision: "full_stored_double",
      categorical_reference_levels: [],
    },
    fit: {
      residual_standard_error: 1.1,
      r_squared: 0.91,
      adjusted_r_squared: 0.9,
      predicted_r_squared: -0.12,
      press: 14.5,
    },
    coefficients: [
      {
        term: "Intercept",
        term_kind: "intercept",
        estimate: 21.3,
        standard_error: 0.2,
        statistic: 10,
        p_value: 0.001,
        vif: null,
        reference_level: null,
        coding: null,
        confidence_interval: { level: 0.95, lower: 20.8, upper: 21.8 },
      },
    ],
    anova: {
      method: "adjusted_partial_sums_of_squares",
      rows: [
        {
          row_kind: "regression",
          source: "Regression",
          df: 1,
          adjusted_ss: 10,
          adjusted_ms: 10,
          f_statistic: 8,
          p_value: 0.02,
        },
      ],
      lack_of_fit: {
        available: false,
        reason: "no_replicated_predictor_settings",
      },
    },
    model_selection: {
      method: "backward_elimination",
      alpha_to_remove: 0.1,
      hierarchy_policy: "strong",
      initial_terms: ["afucose", "noise"],
      final_terms: ["afucose"],
      stop_reason: "all_removal_p_values_at_or_below_alpha",
      steps: [
        {
          step: 1,
          active_terms: ["afucose"],
          removed_term: "noise",
          removal_p_value: 0.65,
          s: 1.1,
          r_squared: 0.91,
          adjusted_r_squared: 0.9,
          press: 14.5,
          predicted_r_squared: -0.12,
          mallows_cp: 2,
          aicc: 30,
          bic: 31,
        },
      ],
    },
    residual_plots: {
      residual_type_available: ["raw", "standardized"],
    },
    diagnostics: {
      max_vif: 1,
      condition_number: 2,
      residual_summary: {
        max_abs_standardized: 1.5,
        large_standardized_count: 0,
      },
      leverage: { max: 0.2, high_count: 0, threshold: 0.5 },
      influence: {
        cooks_distance_max: 0.1,
        high_cooks_distance_count: 0,
        cooks_distance_threshold: 0.33,
      },
      diagnostic_points: { points: [] },
    },
    model_manifest: {
      model_id: "00000000-0000-4000-8000-000000000001",
      manifest_schema_version: 3,
      manifest_sha256: "a".repeat(64),
    },
  } as unknown as LinearModelResult;
}

describe("complete linear model workflow presentation", () => {
  it("renders the final model sections in the required order", () => {
    const html = renderToStaticMarkup(<LinearModelFitResults result={resultFixture()} />);
    const sectionIds = [
      "linear-model-selection-title",
      "linear-model-equation-title",
      "linear-model-summary-title",
      "linear-model-coefficients-title",
      "linear-model-anova-title",
      "linear-model-residual-plots-title",
      "linear-model-diagnostics-title",
      "linear-model-unusual-title",
    ];

    for (let index = 1; index < sectionIds.length; index += 1) {
      expect(html.indexOf(`id="${sectionIds[index - 1]}"`)).toBeLessThan(
        html.indexOf(`id="${sectionIds[index]}"`),
      );
    }
    expect(html).toContain("adcc = 21.3 + 13.8 * afucose");
    expect(html).toContain("음수 Predicted R²");
    expect(html).toContain("탐색적으로 해석해야 합니다");
    expect(html).toContain("반복된 predictor 조합이 없어");
    expect(html).toContain('aria-expanded="false"');
  });

  it("renders a model-bound, accessible pasted-input preflight form", () => {
    const html = renderToStaticMarkup(
      <RegressionPastedPredictionPanel modelResult={resultFixture()} onSelectDataset={() => undefined} />,
    );

    expect(html).toContain("직접 입력·붙여넣기");
    expect(html).toContain("예측 사전점검");
    expect(html).toContain("afucose");
    expect(html).toContain("첫 행에 열 이름 포함");
    expect(html).toContain("구분자");
    expect(html).toContain("textarea");
  });

  it("distinguishes a header-only paste from one usable data row", () => {
    const headerOnly = parseRegressionPastedPredictionPreview("88", "auto", true);
    const oneRow = parseRegressionPastedPredictionPreview("88", "auto", false);

    expect(headerOnly).toMatchObject({
      nonEmptyLineCount: 1,
      headerRowCount: 1,
      dataRowCount: 0,
      inferredHeaderState: "header_only",
      validationCode: "regression_pasted_prediction_header_without_data",
    });
    expect(oneRow).toMatchObject({
      dataRowCount: 1,
      inferredHeaderState: "data",
      validationCode: null,
    });
  });

  it("renders contextual prediction as one editable row grid without a dataset selector", () => {
    const html = renderToStaticMarkup(
      <RegressionManualPredictionPanel modelResult={resultFixture()} />,
    );

    expect(html).toContain("예측 조건 입력");
    expect(html).toContain("regression-manual-grid");
    expect(html).toContain("행 추가");
    expect(html).toContain("붙여넣기 가져오기");
    expect(html).toContain("전체 사전점검");
    expect(html).toContain("전체 예측 실행");
    expect(html).not.toContain("예측 대상 데이터셋 버전");
  });

  it("blocks manual prediction when the stored model is unavailable", () => {
    const html = renderToStaticMarkup(
      <RegressionManualPredictionPanel
        modelAvailable={false}
        modelResult={resultFixture()}
      />,
    );

    expect(html).toContain("저장 모델을 사용할 수 없어 새 예측을 실행할 수 없습니다.");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>전체 사전점검<\/button>/);
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>전체 예측 실행<\/button>/);
  });
});
