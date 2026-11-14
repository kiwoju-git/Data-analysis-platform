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
  it.each(["nominal", "ordinal"] as const)("shows %s category levels as disconnected points, not a fake numeric curve", kind => {
    setCurrentLocale("en"); const { study, model, selection } = mixedPlanningFixture(); if (selection.calculation.schema_version !== 2) throw new Error("fixture");
    const factor = study.factors.find(item => item.factor_id === "material")!;
    if (factor.domain_kind !== "nominal" && factor.domain_kind !== "ordinal") throw new Error("fixture");
    factor.domain_kind = kind;
    const rows = selection.calculation.items;
    const html = renderToStaticMarkup(<MixedProfileView study={study} profile={{ modelId: model.model_id, modelHash: model.snapshot_sha256, points: rows.map(row => row.actual_coordinates), axis: "material", rows }} />);
    expect(html).toContain("Declared category levels"); expect(html).toContain("001"); expect(html).toContain("한글 A"); expect(html).not.toContain('data-series-id="default"');
    expect(html).toContain("Profile quantity"); expect(html).toContain(model.snapshot_sha256);
  });
  it("keeps mixed numeric profiles on exact evaluated coordinates and omits grids for complete points", () => {
    setCurrentLocale("en"); const { study, model, selection } = mixedPlanningFixture();
    if (selection.calculation.schema_version !== 2) throw new Error("fixture");
    const rows = selection.calculation.items, profile = { modelId: model.model_id, modelHash: model.snapshot_sha256, points: rows.map(row => row.actual_coordinates), axis: "x", rows };
    const html = renderToStaticMarkup(<MixedProfileView study={study} profile={profile} />);
    expect(html).toContain('class="bo-profile-grid"'); expect(html).toContain('data-series-id="default"');
    expect((html.match(/data-point-id=/g) ?? [])).toHaveLength(rows.length * (study.objective.responses.length + 2));
    for (const row of rows) for (const prediction of row.response_predictions) expect(html).toContain(`data-x="${row.actual_coordinates.x}" data-y="${prediction.mean_raw}"`);
    const point = { ...profile, axis: null, points: [profile.points[0]], rows: [rows[0]] };
    expect(renderToStaticMarkup(<MixedProfileView study={study} profile={point} />)).not.toContain('class="bo-profile-grid"');
  });
  it("bounds dense long category ticks while preserving all evaluated levels in accessible maps and point details", () => {
    setCurrentLocale("en"); const { study, model, selection } = mixedPlanningFixture();
    if (selection.calculation.schema_version !== 2) throw new Error("fixture");
    const factor = study.factors.find(item => item.factor_id === "material")!;
    if (factor.domain_kind !== "nominal") throw new Error("fixture");
    factor.levels = Array.from({ length: 32 }, (_, index) => `한글로 된 긴 범주 전체 이름 ${index + 1} <raw>`);
    const firstRow = selection.calculation.items[0];
    const rows = factor.levels.map((level, index) => ({ ...firstRow, row_id: `row-${index}`, actual_coordinates: { x: .25, material: level } }));
    const profile = { modelId: model.model_id, modelHash: model.snapshot_sha256, axis: "material", points: rows.map(row => row.actual_coordinates), rows }, before = JSON.stringify(profile);
    const html = renderToStaticMarkup(<MixedProfileView study={study} profile={profile} />);
    expect((html.match(/class="bo-profile-levels"/g) ?? [])).toHaveLength(2);
    const texts = [...html.matchAll(/<text class="chart-tick-label"[^>]*>([^<]*)<\/text>/g)].map(match => match[1]);
    const categoryTicks = texts.filter(value => value.startsWith("#"));
    expect(categoryTicks).toHaveLength(8 * (study.objective.responses.length + 2));
    expect(texts.some(value => value.includes("한글로 된 긴"))).toBe(false);
    for (const level of factor.levels) expect(html).toContain(`<dd>${level.replace("<", "&lt;").replace(">", "&gt;")}</dd>`);
    expect((html.match(/data-point-id=/g) ?? [])).toHaveLength(32 * (study.objective.responses.length + 2));
    expect(html).toContain('data-x="31"'); expect(html).not.toContain('data-series-id="default"');
    expect(JSON.stringify(profile)).toBe(before);
  });
  it("keeps a valid desirability response distinct and shows every response in its own applied-axis chart", () => {
    setCurrentLocale("en"); const { study, model, selection } = mixedPlanningFixture();
    if (selection.calculation.schema_version !== 2) throw new Error("fixture");
    const original = study.objective.responses[0];
    study.objective.responses = [0, 1, 2, 3].map(index => ({ ...original, response_id: index === 0 ? "desirability" : `response_${index}`, name: `Response ${index}`, unit: ["mg", "s", "K", "%"][index] }));
    const rows = selection.calculation.items.map((row, index) => ({ ...row, response_predictions: study.objective.responses.map((response, at) => ({ ...row.response_predictions[0], response_id: response.response_id, mean_raw: at === 0 ? 0 : at * 100 + index, latent_standard_deviation_raw: at + .1, predictive_standard_deviation_raw: at + .2 })) }));
    const html = renderToStaticMarkup(<MixedProfileView study={study} profile={{ modelId: model.model_id, modelHash: model.snapshot_sha256, points: rows.map(row => row.actual_coordinates), axis: "material", rows }} />);
    expect(html).toContain('value="response:desirability"');
    expect(html).toContain("All responses at the evaluated factor");
    expect((html.match(/data-chart-id=/g) ?? [])).toHaveLength(6);
    expect((html.match(/data-point-id=/g) ?? [])).toHaveLength(rows.length * 6);
    for (const response of study.objective.responses) expect(html).toContain(`${response.name} (${response.unit})`);
    expect(html).toContain('data-x="0" data-y="0"');
    expect(html).toContain('data-x="1" data-y="301"');
    expect(html).not.toContain('data-series-id="default"');
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
    expect(markers).toHaveLength(rows.length * (study.objective.responses.length + 2));
    for (const marker of markers) {
      const radius = attribute(marker, "r"), cx = attribute(marker, "cx"), cy = attribute(marker, "cy");
      expect(cx - radius).toBeGreaterThan(left);
      expect(cx + radius).toBeLessThan(right);
      expect(cy - radius).toBeGreaterThan(top);
      expect(cy + radius).toBeLessThan(bottom);
    }
    expect(JSON.stringify(rows)).toBe(before);
  });
  it("marks constraint violations on the detailed mixed profile too", () => {
    setCurrentLocale("en"); const { study, model, selection } = mixedPlanningFixture();
    if (selection.calculation.schema_version !== 2) throw new Error("fixture");
    const rows = selection.calculation.items.map((row, index) => ({ ...row, constraints_satisfied: index !== 0 }));
    const before = JSON.stringify(rows);
    const html = renderToStaticMarkup(<MixedProfileView study={study} profile={{ modelId: model.model_id, modelHash: model.snapshot_sha256, axis: "x", points: rows.map(row => row.actual_coordinates), rows }} />);
    const markers = [...html.matchAll(/<(circle|polygon)\b[^>]*data-point-id="([^"]+)"[^>]*>/g)].filter(match => match[2] === rows[0].row_id);
    expect(markers).toHaveLength(study.objective.responses.length + 2);
    for (const marker of markers) {
      expect(marker[1]).toBe("polygon");
      expect(marker[0]).toContain("Outside the stored constraints.");
    }
    expect(JSON.stringify(rows)).toBe(before);
  });
});
