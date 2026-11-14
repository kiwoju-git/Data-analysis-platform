import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { setCurrentLocale } from "../../i18n/store";
import { planningMessages } from "../../i18n/boPlanning";
import { boViewMessages } from "../../i18n/boViews";
import { BayesianProfileMatrix } from "./BayesianProfileMatrix";
import type { ProfileMatrixView } from "./boProfileMatrix";

describe("whole-factor profiler matrix display", () => {
  afterEach(() => setCurrentLocale("ko"));
  it.each(["ko", "en"] as const)("shows co-varying semantics and fixed-component unavailability without invented points in %s", locale => {
    setCurrentLocale(locale);
    const view: ProfileMatrixView = { modelId: "m", modelHash: "hash", historyHash: "history", holds: { a: .2, fixed: .1 }, responses: [{ response_id: "y", name: "Actual response", unit: "g" }], axes: [
      { factor_id: "a", name: "Component A", unit: "g", category: false, pathPolicy: "excess_above_lower", rows: [.2, .3].map(a => ({ row_id: String(a), actual_coordinates: { a, fixed: .1 }, constraints_satisfied: true, desirability_moments: { mean: .5 }, response_predictions: [{ response_id: "y", mean_raw: 1e-6, latent_standard_deviation_raw: 1e-8, predictive_standard_deviation_raw: 2e-8 }] })) },
      { factor_id: "fixed", name: "Fixed <component>", unit: "g", category: false, pathPolicy: "excess_above_lower", unavailableReason: "fixed_component", rows: [] },
    ] };
    const before = JSON.stringify(view), html = renderToStaticMarkup(<BayesianProfileMatrix view={view} />);
    expect(html).toContain(boViewMessages(locale).coVary);
    expect(html).toContain(boViewMessages(locale).fixedComponent);
    expect(html).toContain("Fixed &lt;component&gt;");
    expect((html.match(/data-point-id=/g) ?? [])).toHaveLength(4);
    expect(JSON.stringify(view)).toBe(before);
  });
  it.each(["ko", "en"] as const)("renders every response including desirability ID, category labels and constraint cues in %s", locale => {
    setCurrentLocale(locale);
    const view: ProfileMatrixView = { modelId: "model", modelHash: "exact-hash", historyHash: "history", holds: { x: 4, category: "Full <level>" }, responses: [{ response_id: "desirability", name: "User response", unit: "mg" }, { response_id: "r2", name: "Second response", unit: null }], axes: [
      { factor_id: "x", name: "Numeric", unit: "C", category: false, rows: [] }, { factor_id: "category", name: "Category", unit: null, category: true, rows: [] },
    ] };
    view.axes.forEach((axis, a) => { axis.rows = [0, 1].map(index => ({ row_id: `${a}-${index}`, actual_coordinates: { x: index, category: index ? "Second" : "Full <level>" }, constraints_satisfied: index === 0, desirability_moments: { mean: .5 }, response_predictions: [{ response_id: "desirability", mean_raw: a * 100 + index, latent_standard_deviation_raw: 2, predictive_standard_deviation_raw: 3 }, { response_id: "r2", mean_raw: index, latent_standard_deviation_raw: 4, predictive_standard_deviation_raw: 5 }] })); });
    const before = JSON.stringify(view), html = renderToStaticMarkup(<BayesianProfileMatrix view={view} />);
    expect(html).toContain(planningMessages(locale).profileMatrix);
    expect(html).toContain('class="bo-profile-matrix-pagination"');
    expect((html.match(/bo-planning-icon/g) ?? [])).toHaveLength(2);
    expect(html).toContain('data-response-id="desirability"'); expect(html).toContain('data-response-id="r2"');
    expect(html).toContain('data-profile-kind="composite"'); expect(html).toContain("Full &lt;level&gt;");
    expect(html).toContain("exact-hash"); expect(html).toContain(planningMessages(locale).appliedHolds);
    expect((html.match(/data-point-id=/g) ?? [])).toHaveLength(12);
    expect(html).toMatch(/<polygon[^>]*data-point-id="0-1"/);
    expect(JSON.stringify(view)).toBe(before);
  });
});
