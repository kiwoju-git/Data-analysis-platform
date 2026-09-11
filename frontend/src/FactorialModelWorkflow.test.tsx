import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { DoeModelSelectionSettings } from "./doe/DoeModelSelectionSettings";
import { defaultDoeSelection, interactionOrderLabel, factorialWorkflowMessage, factorialMarginalMean } from "./doe/factorialWorkflowPresentation";
import { DoeResponsePasteDialog } from "./doe/DoeResponsePasteDialog";
import { FactorialResidualPlots } from "./FactorialResidualPlots";
import { FactorialPredictionResults } from "./FactorialPredictionPanel";
import type { DoeFinalModelWorkflow, DoePredictionResponse } from "./api/types/doeModelWorkflow";
import { setCurrentLocale } from "./i18n/store";
import { translateKnownSource } from "./i18n/translate";

afterEach(() => setCurrentLocale("en"));

describe("factorial model workflow presentation", () => {
  it.each(["en", "ko"] as const)("keeps none default and exposes backward settings in %s", (locale) => {
    setCurrentLocale(locale);
    const props = { confidence: 0.95, onConfidenceChange: () => {}, onChange: () => {} };
    const full = renderToStaticMarkup(<DoeModelSelectionSettings {...props} value={defaultDoeSelection} />);
    expect(full).toContain('value="none" selected');
    expect(full).not.toContain('value="0.05"');
    const backward = renderToStaticMarkup(<DoeModelSelectionSettings {...props} value={{ ...defaultDoeSelection, method: "backward_elimination" }} />);
    expect(backward).toContain('value="0.05"');
    expect(backward).toContain('aria-describedby=');
    expect(backward).toContain(locale === "en" ? "smallest adjusted" : "조정제곱합");
    const blocked = renderToStaticMarkup(<DoeModelSelectionSettings {...props} aliased value={defaultDoeSelection} />);
    expect(blocked).toContain('value="backward_elimination" disabled');
    expect(blocked).toContain("Plackett-Burman");
  });
  it("uses complete interaction-order labels and fixes context-sensitive statistical translations", () => {
    setCurrentLocale("en");
    expect([1, 2, 3].map(interactionOrderLabel)).toEqual(["Main effects only", "Up to 2-way interactions", "Up to 3-way interactions"]);
    for (const [source, translated] of [["검정", "Test"], ["열", "columns"], ["항", "Term"], ["센터점", "Center points"], ["절대 효과 순위", "Absolute effect ranking"]]) {
      expect(translateKnownSource(source, "en")).toBe(translated);
    }
  });
  it("keeps locked response paste unavailable and initially collapsed", () => {
    const html = renderToStaticMarkup(<DoeResponsePasteDialog disabled runOrders={[1, 2]} onApply={() => { throw new Error("must not save"); }} />);
    expect(html).toContain('aria-expanded="false"');
    expect(html).toContain("disabled");
    expect(html).not.toContain("textarea");
  });
  it("marginalizes fitted cells equally and raw means by observed counts", () => {
    const cells = [{ settings: { A: -1, B: -1 }, fitted_mean: 10, data_mean: 8, n: 1 },
      { settings: { A: -1, B: 1 }, fitted_mean: 20, data_mean: 20, n: 3 },
      { settings: { A: 1, B: 1 }, fitted_mean: 30, data_mean: null, n: 0 }];
    expect(factorialMarginalMean(cells, { A: -1 }, "fitted_mean")).toBe(15);
    expect(factorialMarginalMean(cells, { A: -1 }, "data_mean")).toBe(17);
    expect(factorialMarginalMean(cells, { A: 1 }, "data_mean")).toBeNull();
  });
  it("renders four interactive diagnostics with saved full-N histogram bins", () => {
    const view = { n: 12, histogram: [{ lower: -1, upper: 1, count: 12 }],
      qq_points: [{ run_order: 3, theoretical_quantile: -1, residual: -0.5 }, { run_order: 7, theoretical_quantile: 1, residual: 0.5 }],
      reference_line: { slope: 0.5, intercept: 0 }, points: [{ run_order: 3, fitted: 10, residual: -0.5 }, { run_order: 7, fitted: 12, residual: 0.5 }] };
    const plots: DoeFinalModelWorkflow["residual_plots"] = { raw: view, standardized: view, n_total: 12, point_limit: 2, truncated: true, points: [] };
    const html = renderToStaticMarkup(<FactorialResidualPlots plots={plots} />);
    expect(html.match(/<svg/g)).toHaveLength(4);
    expect(html).toContain("N = 12");
    expect(html).toContain("Residuals versus Run Order");
    expect(html).toContain('tabindex="0"');
    expect(html).toContain("<desc");
  });
  it("does not invent prediction intervals without residual variance", () => {
    const result: DoePredictionResponse = { schema_version: 1, prediction_id: "prediction", design_id: "design", analysis_id: "analysis", response_revision_id: "revision", response_revision_sha256: "a", source_analysis_sha256: "b", created_at: "2026-09-12", warnings: [],
      rows: [{ row_id: "one", factor_settings: { "<script>": "A" }, block_index: null, fitted_mean: 4, standard_error_fit: null,
        mean_confidence_interval: null, individual_prediction_interval: null, interval_unavailability_reason: "doe_factorial_prediction_variance_unavailable", domain_status: "in_domain" }] };
    const html = renderToStaticMarkup(<FactorialPredictionResults result={result} />);
    expect(html).toContain("Point prediction only");
    expect(html).not.toContain("<script>");
    expect(html).toContain("&lt;script&gt;");
    expect(factorialWorkflowMessage("doe_factorial_prediction_center_curvature_domain_invalid")).toContain("only corner");
  });
});
