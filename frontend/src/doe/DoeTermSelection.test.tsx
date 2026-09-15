import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, expect, it } from "vitest";
import { DoeTermSelection } from "./DoeTermSelection";
import { DoeSelectionStepMatrix } from "./DoeSelectionStepMatrix";
import { defaultDoeSelection } from "./factorialWorkflowPresentation";
import type { DoeAnalysisTerm, DoeModelSelectionResult } from "../api/types/doeModelWorkflow";
import { setCurrentLocale } from "../i18n/store";

afterEach(() => setCurrentLocale("en"));
const terms: DoeAnalysisTerm[] = [
  { term_id: "factor_1", label: "Temperature", kind: "main_effect", order: 1, df: 1, hierarchy_role: "factorial_term", factor_ids: ["factor_1"], hierarchy_dependencies: [], default_disposition: "candidate", estimable: true },
  { term_id: "factor_1:factor_2", label: "Temperature * pH", kind: "interaction", order: 2, df: 1, hierarchy_role: "factorial_term", factor_ids: ["factor_1", "factor_2"], hierarchy_dependencies: ["factor_1", "factor_2"], default_disposition: "candidate", estimable: true },
  { term_id: "center_curvature", label: "Center curvature", kind: "curvature", order: 0, df: 1, hierarchy_role: "independent_term", factor_ids: [], hierarchy_dependencies: [], default_disposition: "candidate", estimable: true },
];
it.each(["en", "ko"] as const)("shows server-owned terms, forced options and hierarchy in %s", (locale) => {
  setCurrentLocale(locale);
  const options = { ...defaultDoeSelection, method: "backward_elimination" as const, term_policies: terms.map((term) => ({ term_id: term.term_id, disposition: term.default_disposition })) };
  const html = renderToStaticMarkup(<DoeTermSelection value={options} onChange={() => {}} state={{ ready: true, error: false, terms, options }} />);
  expect(html).toContain('aria-label="Temperature"');
  expect(html).toContain('value="excluded" disabled');
  expect(html).toContain('value="forced"');
  expect(html).toContain('aria-label="Center curvature"');
  expect(html).toContain(locale === "en" ? "Independent of factor hierarchy" : "요인 계층과 독립");
});
it("shows current-model statistics, one-based steps and unavailable Cp without inventing values", () => {
  setCurrentLocale("en");
  const selection = { ...defaultDoeSelection, term_catalog: terms,
    method: "backward_elimination", tie_break_policy: "deterministic", initial_model_saturated: true,
    initial_parameter_count: 2, initial_residual_df: 0, target_pool_count: 1,
    initial_term_ids: ["factor_1"], pooled_term_ids: [], removed_term_ids: [], final_term_ids: ["factor_1"],
    fixed_term_ids: ["intercept"], stop_reason: "insufficient_residual_df", post_selection_inference: "exploratory",
    steps: [{ step: 0, active_term_ids: ["factor_1"], removed_term_id: null, residual_df: 0,
      term_statistics: [{ term_id: "factor_1", label: "Temperature", status: "active", df: 1, coefficient: 1.25, p_value: null, coefficients: [] }],
      mallows_cp: null, mallows_cp_unavailable_reason: "reference_full_model_mse_unavailable",
      phase: "initial_full_model", removal_df: null, removal_adjusted_ss: null, removal_p_value: null,
      stop_reason: null, coefficients: [], sse: 0, residual_standard_error: null,
      r_squared: 1, adjusted_r_squared: null, press: null, predicted_r_squared: null }],
  } satisfies DoeModelSelectionResult;
  const html = renderToStaticMarkup(<DoeSelectionStepMatrix selection={selection} multiDf={false} />);
  expect(html).toContain("Step 1"); expect(html).not.toContain("Step 0");
  expect(html).toContain('class="doe-step-mobile"');
  expect(html).toContain("Mallows Cp"); expect(html).toContain("no valid residual MSE");
  expect(html).toContain("1.25");
});
