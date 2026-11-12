import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { setCurrentLocale } from "../../i18n/store";
import { desirabilityFixture } from "./bayesianDesirability.fixture";
import { BayesianProgressCharts } from "./BayesianProgressCharts";
import { mixedStudyFixture } from "./boMixed.test.fixture";

describe("shared BO progress chart presentation", () => {
  afterEach(() => setCurrentLocale("ko"));
  it.each(["en", "ko"] as const)("renders measured and derived views without altering user text in %s", locale => {
    setCurrentLocale(locale);
    const { study } = desirabilityFixture();
    study.factors.push({ ...study.factors[0], factor_id: "second", name: "한글 요인 <data>", order: 1 });
    study.trials.forEach(trial => { trial.actual_coordinates.second = trial.trial_number / 2; });
    const before = JSON.stringify(study);
    const html = renderToStaticMarkup(<BayesianProgressCharts study={study} />);
    expect(html).toContain('data-chart-id="bo-progress-observed"');
    expect(html).toContain('data-chart-id="bo-progress-desirability"');
    expect(html).toContain('data-chart-id="bo-progress-space"');
    expect(html).toContain(locale === "en" ? "Trial number" : "실험 번호");
    expect(html).toContain(locale === "en" ? "not measurement time" : "실제 측정 시간순이 아닙니다");
    expect(html).toContain("한글 요인 &lt;data&gt;");
    expect(JSON.stringify(study)).toBe(before);
  });
  it("does not fabricate desirability for a scalar objective or factor2 for a one-factor study", () => {
    setCurrentLocale("en"); const { study } = desirabilityFixture();
    study.objective = { name: "Y", goal_type: "maximize", direction: "maximize", observation_policy: "manual_single_observation",
      unit: "mg", target_value: null, target_tolerance: null };
    study.trials.forEach(trial => { trial.objective_value = 1e-8; });
    const html = renderToStaticMarkup(<BayesianProgressCharts study={study} />);
    expect(html).toContain("No desirability limits"); expect(html).toContain("Two factors are required");
    expect(html).toContain('data-y="1e-8"'); expect(html).not.toContain('data-chart-id="bo-progress-desirability"');
  });
  it("retains both markers at exactly the same measured and cumulative-best coordinates", () => {
    const { study } = desirabilityFixture();
    study.objective = { name: "Y", goal_type: "maximize", direction: "maximize", observation_policy: "manual_single_observation",
      unit: "mg", target_value: null, target_tolerance: null };
    study.trials.forEach((trial, index) => { trial.objective_value = index + 1; });
    const before = JSON.stringify(study);
    const html = renderToStaticMarkup(<BayesianProgressCharts study={study} />);
    const chart = html.split('data-chart-id="bo-progress-observed"')[1].split("</svg>")[0];
    const measured = [...chart.matchAll(/<circle[^>]*data-point-id="([^"]+):measured"[^>]*>/g)];
    const best = [...chart.matchAll(/<rect[^>]*data-point-id="([^"]+):best"[^>]*>/g)];
    expect(measured.length).toBeGreaterThan(0);
    expect(best).toHaveLength(measured.length);
    const attribute = (tag: string, name: string) => Number(tag.match(new RegExp(` ${name}="([^"]+)"`))![1]);
    for (const [index, point] of measured.entries()) {
      const square = best[index];
      expect(square[1]).toBe(point[1]);
      expect(attribute(square[0], "data-x")).toBe(attribute(point[0], "data-x"));
      expect(attribute(square[0], "data-y")).toBe(attribute(point[0], "data-y"));
      expect(attribute(square[0], "x") + attribute(square[0], "width") / 2).toBe(attribute(point[0], "cx"));
      expect(attribute(square[0], "y") + attribute(square[0], "height") / 2).toBe(attribute(point[0], "cy"));
    }
    expect(JSON.stringify(study)).toBe(before);
  });
  it("keeps a target outside the observations inside the plot range", () => {
    const { study } = desirabilityFixture();
    study.objective = { name: "Y", goal_type: "match_target", direction: null, observation_policy: "manual_single_observation",
      unit: "mg", target_value: 100, target_tolerance: null };
    study.trials.forEach(trial => { trial.objective_value = 1; });
    const html = renderToStaticMarkup(<BayesianProgressCharts study={study} />);
    const line = html.match(/<line[^>]+data-y1="100"[^>]+>/)?.[0] ?? "";
    const y = Number(line.match(/ y1="([^"]+)"/)?.[1]);
    expect(Number.isFinite(y)).toBe(true); expect(y).toBeGreaterThanOrEqual(0);
  });
  it("keeps declared category ticks visible when observations occupy a sparse subset", () => {
    const mixed = mixedStudyFixture();
    const category = mixed.factors[1];
    if (!("levels" in category)) throw new Error("synthetic category required");
    category.levels = Array.from({ length: 32 }, (_, index) => `Very long category ${index}`);
    mixed.trials.forEach(trial => { trial.actual_coordinates.material = category.levels[2]; trial.encoded_coordinates.material = 2; });
    const html = renderToStaticMarkup(<BayesianProgressCharts study={mixed} />);
    const chart = html.split('data-chart-id="bo-progress-space"')[1].split("</svg>")[0];
    expect(chart).toMatch(/class="chart-tick-label"[^>]*>#1</);
    expect(chart).toMatch(/class="chart-tick-label"[^>]*>#32</);
    expect(chart).toContain('data-y="2"');
  });
});
