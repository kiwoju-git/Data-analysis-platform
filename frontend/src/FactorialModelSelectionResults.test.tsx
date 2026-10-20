import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, expect, it } from "vitest";
import { FactorialModelSelectionResults } from "./FactorialModelSelectionResults";
import type { DoeFinalModelWorkflow, DoeModelSelectionResult } from "./api/types/doeModelWorkflow";
import { defaultDoeSelection } from "./doe/factorialWorkflowPresentation";
import { setCurrentLocale } from "./i18n/store";

afterEach(() => setCurrentLocale("en"));
const emptyView = { n: 8, histogram: [], qq_points: [], reference_line: null, points: [] };
const model: DoeFinalModelWorkflow = {
  equation: { scale: "coded", response_name: "Synthetic", intercept: 1, terms: [], display_equation: "Synthetic = 1" },
  coded_coefficients: [],
  prediction_basis: { schema_version: 1, coding: "coded", features: [], coefficients: [], xtx_inverse: [],
    residual_mean_square: 1, residual_df: 4, confidence_level: 0.95, block_levels: [null], center_settings: [] },
  press: null, predicted_r_squared: null,
  residual_plots: { raw: emptyView, standardized: emptyView, points: [], n_total: 8, point_limit: 8, truncated: false },
  factorial_plots: { cells: [], available: false, reason: "fixture", marginalization: "equal_level_and_block_weights" },
  warnings: [],
};
const selection: DoeModelSelectionResult = {
  ...defaultDoeSelection, tie_break_policy: "deterministic", initial_model_saturated: false,
  initial_parameter_count: 2, initial_residual_df: 6, target_pool_count: 0,
  initial_term_ids: ["factor_1"], pooled_term_ids: [], removed_term_ids: [], final_term_ids: ["factor_1"],
  fixed_term_ids: ["intercept"], stop_reason: "not_requested", steps: [], post_selection_inference: "not_selected",
  term_catalog: [{ term_id: "factor_1", label: "Long synthetic factor <>& ".repeat(12), kind: "main_effect",
    order: 1, factor_ids: ["factor_2"], hierarchy_dependencies: [], hierarchy_role: "factorial_term",
    default_disposition: "candidate", df: 1, estimable: true }],
};

it.each(["en", "ko"] as const)("separates explanatory values and exposes full term names in %s", (locale) => {
  setCurrentLocale(locale);
  const html = renderToStaticMarkup(<FactorialModelSelectionResults selection={selection} model={model} fit={{ r_squared: 0.5, adjusted_r_squared: 0.4 }} n={8} factorNames={["factor_2"]} />);
  expect(html).toContain('class="doe-selection-description"');
  expect(html).toContain('class="doe-selection-description-wide"');
  expect(html).toContain(locale === "en" ? "Keep specified model" : "지정 모형 유지");
  expect(html).toContain(locale === "en" ? "Selection not requested" : "모형 선택을 요청하지 않음");
  expect(html).toContain("<summary>A</summary>");
  expect(html).toContain("Long synthetic factor &lt;&gt;&amp;");
  expect(html).not.toContain("<textarea");
});
