import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { setCurrentLocale } from "../../i18n/store";
import { MixedFitReceipt, MixedProfileView, MixedSelectionDetails } from "./BayesianMixedPlanningPanel";
import { mixedPlanningFixture } from "./boMixedPlanning.test.fixture";

describe("mixed persisted output presentation", () => {
  afterEach(() => setCurrentLocale("ko"));
  it.each(["ko", "en"] as const)("preserves string levels, units and exact stored selection in %s", locale => {
    setCurrentLocale(locale); const { study, selection } = mixedPlanningFixture(), before = JSON.stringify(selection);
    const html = renderToStaticMarkup(<MixedSelectionDetails study={study} selection={selection} />);
    expect(html).toContain("001"); expect(html).toContain("한글 A"); expect(html).toContain("Catalyst &lt;raw&gt;");
    expect(html).toContain(locale === "en" ? "Latent SD" : "잠재 SD"); expect(html).toContain(locale === "en" ? "New-measurement predictive SD" : "새 측정 예측 SD");
    expect(html).toContain(selection.result_sha256); expect(html).not.toContain("<input"); expect(JSON.stringify(selection)).toBe(before);
  });
  it("shows category levels as disconnected points, not a fake numeric curve", () => {
    setCurrentLocale("en"); const { study, model, selection } = mixedPlanningFixture(); if (selection.calculation.schema_version !== 2) throw new Error("fixture");
    const rows = selection.calculation.items;
    const html = renderToStaticMarkup(<MixedProfileView study={study} profile={{ modelId: model.model_id, modelHash: model.snapshot_sha256, points: rows.map(row => row.actual_coordinates), axis: "material", rows }} />);
    expect(html).toContain("Declared category levels"); expect(html).toContain("001"); expect(html).toContain("한글 A"); expect(html).not.toContain('data-series-id="default"');
    expect(html).toContain("Profile quantity"); expect(html).toContain(model.snapshot_sha256);
  });
  it("exposes fitted warnings, coverage, optimizer starts and category parameter role without re-labelling it ARD", () => {
    setCurrentLocale("en"); const { model, study } = mixedPlanningFixture(); model.warnings = ["bayesian_category_unobserved_level_prior_dependent"];
    const html = renderToStaticMarkup(<MixedFitReceipt model={model} study={study} />);
    expect(html).toContain("bayesian_category_unobserved_level_prior_dependent"); expect(html).toContain("category_mismatch"); expect(html).toContain("Training category coverage"); expect(html).toContain("001");
    expect(html).toContain("1e-8"); expect(html).not.toContain("ARD");
  });
  it("keeps complete profile markers inside the clip without changing stored coordinates", () => {
    const { study, model, selection } = mixedPlanningFixture();
    if (selection.calculation.schema_version !== 2) throw new Error("fixture");
    const rows = selection.calculation.items, before = JSON.stringify(rows);
    const html = renderToStaticMarkup(<MixedProfileView study={study} profile={{ modelId: model.model_id, modelHash: model.snapshot_sha256, points: rows.map(row => row.actual_coordinates), axis: "material", rows }} />);
    const clip = html.match(/<clipPath[^>]*><rect[^>]*>/)?.[0];
    expect(clip).toBeDefined();
    const attribute = (element: string, name: string) => Number(element.match(new RegExp(`\\b${name}="([^"]+)"`))?.[1]);
    const left = attribute(clip!, "x"), top = attribute(clip!, "y");
    const right = left + attribute(clip!, "width"), bottom = top + attribute(clip!, "height");
    const markers = [...html.matchAll(/<circle\b[^>]*data-point-id="[^"]*"[^>]*>/g)].map(match => match[0]);
    expect(markers).toHaveLength(rows.length);
    for (const marker of markers) {
      const radius = attribute(marker, "r"), cx = attribute(marker, "cx"), cy = attribute(marker, "cy");
      expect(cx - radius).toBeGreaterThan(left);
      expect(cx + radius).toBeLessThan(right);
      expect(cy - radius).toBeGreaterThan(top);
      expect(cy + radius).toBeLessThan(bottom);
    }
    expect(JSON.stringify(rows)).toBe(before);
  });
});
