import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { TwoVariancesPanel, TwoVariancesResults } from "./TwoVariancesPanel";
import type { TwoVariancesResult } from "./api/types/twoVariances";
import { setCurrentLocale } from "./i18n/store";
import { ANALYSIS_DOMAINS } from "./analysisDomains";
import { visiblePlannedWorkflows } from "./plannedWorkflowVisibility";

const result: TwoVariancesResult = {
  schema_version: 1, summary_type: "two_variances_test", method: "brown_forsythe",
  response: { column_id: "y", display_name: "Yield <test>", unit: "g" }, group_column: { column_id: "g", display_name: "Group", unit: null },
  sample: { n_total: 10, n_used: 10, n_excluded: 0, missing_policy: "complete_case" },
  groups: [{ key: "A", label: "A", role: "numerator", n: 5, mean: 3, variance: 2.5, standard_deviation: Math.sqrt(2.5) }, { key: "B", label: "B", role: "denominator", n: 5, mean: 5, variance: 10, standard_deviation: Math.sqrt(10) }],
  ratio_estimate: { scale: "variance", value: .25, variance: .25, standard_deviation: .5 }, hypothesis: { ratio: 1, alternative: "two_sided", confidence_level: .95 },
  test: { statistic: 72 / 35, df1: 1, df2: 8, p_value: .189403661093321, alpha: .05, reject: false },
  ratio_interval: { available: false, reason: "not_provided_by_selected_method" },
  plot: { row_identity: "filtered_analysis_row", point_limit_per_group: 500, groups: [{ key: "A", n_total: 5, n_displayed: 2, points: [{ row_number: 1, value: 1 }, { row_number: 5, value: 5 }] }, { key: "B", n_total: 5, n_displayed: 2, points: [{ row_number: 6, value: 1 }, { row_number: 10, value: 9 }] }] },
  warnings: ["two_variances_independence_required", "two_variances_ratio_ci_unavailable"], package_versions: {},
};
describe("Two Variances", () => {
  it("defaults to constrained BF and requires preflight before execution", () => {
    setCurrentLocale("en");
    const html = renderToStaticMarkup(<TwoVariancesPanel version={null} filterDrafts={[]} filterValidationError={null} isRunningAnalysis={false} analysisResult={null} result={null} onRun={() => undefined} />);
    expect(html).toContain('value="brown_forsythe" selected');
    expect(html).toContain("Check groups");
    expect(html).toContain("Minimum 3 observations");
    expect(html).toMatch(/class="primary-button" disabled/);
  });
  it("preserves BF result without fabricated intervals and escapes labels", () => {
    setCurrentLocale("en");
    const html = renderToStaticMarkup(<TwoVariancesResults result={result} />);
    expect(html).toContain("0.25"); expect(html).toContain("0.18940366");
    expect(html).toContain("Yield &lt;test&gt; (g)");
    expect(html).not.toContain('data-chart-id="two-variances-ratio"');
    expect(html).toContain("Not provided by the selected method");
  });
  it("shows a stored one-sided F bound, never JSON Infinity", () => {
    setCurrentLocale("ko");
    const html = renderToStaticMarkup(<TwoVariancesResults result={{ ...result, method: "normal_f", ratio_interval: { available: true, reason: null, confidence_level: .95, lower: { kind: "finite", value: .1 }, upper: { kind: "unbounded", value: null } } }} />);
    expect(html).toContain("두 분산 비교"); expect(html).toContain("0.1 - ∞");
    expect(html).toContain('data-chart-id="two-variances-ratio"'); expect(html).not.toContain("NaN");
  });
  it("hides only roadmap items without mutating definitions or contextual entries", () => {
    const workflows = ANALYSIS_DOMAINS.flatMap((domain) => domain.families.flatMap((family) => family.plannedWorkflows ?? []));
    expect(workflows.map((item) => item.id)).toContain("hypothesis.comparability_assessment");
    const before = JSON.stringify(workflows);
    expect(visiblePlannedWorkflows(workflows).map((item) => item.id)).not.toContain("hypothesis.comparability_assessment");
    expect(visiblePlannedWorkflows(workflows).map((item) => item.id)).not.toContain("quality.multivariate_monitoring");
    expect(JSON.stringify(workflows)).toBe(before);
    expect(ANALYSIS_DOMAINS.flatMap((domain) => domain.families.flatMap((family) => family.methodIds)).filter((id) => id === "quality.two_variances")).toHaveLength(1);
  });
});
