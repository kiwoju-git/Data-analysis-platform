import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { requestBoLoo, type BoLooView } from "../../api/boLoo";
import { setCurrentLocale } from "../../i18n/store";
import { InteractiveScatterChart, type InteractiveScatterChartProps } from "../../charts/InteractiveScatterChart";
import { BayesianLooPanel } from "./BayesianLooPanel";
import { MixedProfileView } from "./BayesianMixedPlanningPanel";
import { mixedPlanningFixture } from "./boMixedPlanning.test.fixture";

vi.mock("../../api/boLoo", () => ({ requestBoLoo: vi.fn() }));
type Element = React.ReactElement<Record<string, unknown>>;
type Slot = { value?: unknown; deps?: React.DependencyList; cleanup?: () => void };
const dispatcher = (React as unknown as { __SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED: { ReactCurrentDispatcher: { current: unknown } } }).__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentDispatcher;
const runners: Runner[] = [];

// Node-only interaction harness, following the existing prediction/import tests.
class Runner {
  private slots: Slot[] = []; private cursor = 0; private pending = true;
  output: React.ReactNode;
  constructor(private component: () => React.ReactNode) { runners.push(this); this.render(); }
  act(action: () => void) { action(); this.pending = true; this.render(); }
  async flush() { for (let index = 0; index < 8; index++) { await Promise.resolve(); this.render(); } }
  unmount() { this.slots.forEach(slot => slot.cleanup?.()); }
  private slot() { const index = this.cursor++; return this.slots[index] ?? (this.slots[index] = {}); }
  private render() {
    while (this.pending) {
      this.pending = false; this.cursor = 0;
      const effects: (() => void)[] = [], previous = dispatcher.current;
      dispatcher.current = {
        useContext: () => null,
        useRef: (value: unknown) => { const slot = this.slot(); if (!("value" in slot)) slot.value = { current: value }; return slot.value; },
        useState: (initial: unknown) => { const slot = this.slot(); if (!("value" in slot)) slot.value = typeof initial === "function" ? (initial as () => unknown)() : initial;
          return [slot.value, (next: unknown) => { slot.value = typeof next === "function" ? (next as (old: unknown) => unknown)(slot.value) : next; this.pending = true; }]; },
        useEffect: (effect: React.EffectCallback, deps?: React.DependencyList) => { const slot = this.slot(); if (!slot.deps || !deps || deps.some((value, index) => !Object.is(value, slot.deps?.[index]))) effects.push(() => { slot.cleanup?.(); const cleanup = effect(); slot.cleanup = typeof cleanup === "function" ? cleanup : undefined; slot.deps = deps; }); },
      };
      try { this.output = this.component(); } finally { dispatcher.current = previous; }
      effects.forEach(effect => effect());
    }
  }
}
function elements(node: React.ReactNode): Element[] {
  if (Array.isArray(node)) return node.flatMap(elements);
  if (!React.isValidElement<Record<string, unknown>>(node)) return [];
  return [node, ...elements(node.props.children as React.ReactNode)];
}
function charts(runner: Runner) { return elements(runner.output).filter(node => node.type === InteractiveScatterChart).map(node => node.props as unknown as InteractiveScatterChartProps); }
function edit(runner: Runner, label: string, value: string) { const control = elements(runner.output).find(node => node.props["aria-label"] === label); expect(control).toBeDefined(); runner.act(() => (control!.props.onChange as (event: { currentTarget: { value: string } }) => void)({ currentTarget: { value } })); }
afterEach(() => { runners.splice(0).forEach(runner => runner.unmount()); setCurrentLocale("ko"); vi.clearAllMocks(); vi.restoreAllMocks(); });

describe("applied BO graph interactions", () => {
  it("selects a response named desirability and all three quantities without another request", () => {
    setCurrentLocale("en"); const { study, model, selection } = mixedPlanningFixture();
    if (selection.calculation.schema_version !== 2) throw new Error("fixture");
    study.objective.responses[0] = { ...study.objective.responses[0], response_id: "desirability", unit: "mg" };
    const rows = selection.calculation.items.map((row, index) => ({ ...row, response_predictions: row.response_predictions.map((prediction, at) => ({ ...prediction, response_id: at === 0 ? "desirability" : prediction.response_id, mean_raw: 10 + index, latent_standard_deviation_raw: 2 + index, predictive_standard_deviation_raw: 3 + index })) }));
    const profile = { modelId: model.model_id, modelHash: model.snapshot_sha256, points: rows.map(row => row.actual_coordinates), axis: "material", rows };
    const before = JSON.stringify(profile), fetch = vi.spyOn(globalThis, "fetch");
    const runner = new Runner(() => MixedProfileView({ study, profile }));
    edit(runner, "Profile quantity", "response:desirability");
    for (const [metric, start] of [["mean", 10], ["latent", 2], ["predictive", 3]] as const) {
      edit(runner, "Response display", metric);
      const chart = charts(runner)[0]; expect(chart.yUnit).toBe("mg");
      expect(chart.points.map(point => [point.x, point.y])).toEqual(rows.map((_, index) => [index, start + index]));
      const html = renderToStaticMarkup(<InteractiveScatterChart {...chart} />);
      expect(html).toContain(`data-x="0" data-y="${start}"`);
      expect(chart.sourceKey).toContain(model.snapshot_sha256); expect(chart.sourceKey).toContain("response:desirability");
    }
    runner.act(() => setCurrentLocale("ko"));
    expect(charts(runner)[0].yLabel).toContain("새 측정 예측 SD");
    expect(fetch).not.toHaveBeenCalled(); expect(JSON.stringify(profile)).toBe(before); fetch.mockRestore();
  });
  it.each(["en", "ko"] as const)("renders exact residual rows, zero line and constant response metadata in %s", async locale => {
    setCurrentLocale(locale);
    const { model } = mixedPlanningFixture();
    const points = [
      { trial_id: "repeat-1", observation_index: 1, observed: 5, predicted: 4, residual: 1 },
      { trial_id: "repeat-2", observation_index: 2, observed: 5, predicted: 6, residual: -1 },
      { trial_id: "singleton", observation_index: 3, observed: 5, predicted: 5, residual: 0 },
    ];
    const view: BoLooView = { schema_version: 1, study_id: model.study_id, model_id: model.model_id, model_sha256: model.snapshot_sha256, config_sha256: model.config_sha256,
      source_history_revision_id: model.source_history_revision_id, history_sha256: model.history_sha256, source_is_current: true, calculation_sha256: "f".repeat(64),
      calculation: { schema_version: 1, policy: "fixed_full_fit_parameters_row_loo_v1", evaluation_unit: "individual_observed_trial", normalization_policy: "frozen_full_fit_mean_scale", r_squared_policy: "one_minus_press_over_raw_centered_tss", model_refit: false, auto_routing_applied: false, warnings: [],
        responses: model.objective.responses.map((response, index) => ({ response_id: response.response_id, raw_observation_count: 3, effective_training_count: 2, n_scored: 3, rmse: index === 0 ? 1 : 0, r_squared: index === 0 ? -2 : null, r_squared_reason: index === 0 ? null : "constant_observations", points: index === 0 ? points : points.map(point => ({ ...point, predicted: 5, residual: 0 })) })) } };
    vi.mocked(requestBoLoo).mockResolvedValue(view);
    const outer = BayesianLooPanel({ studyId: model.study_id, model, contextKey: "source", mixed: true }) as React.ReactElement;
    const runner = new Runner(() => (outer.type as (props: unknown) => React.ReactNode)(outer.props));
    expect(charts(runner)).toHaveLength(0);
    const run = elements(runner.output).find(node => node.type === "button" && node.props.onClick);
    runner.act(() => (run!.props.onClick as () => void)()); await runner.flush();
    expect(charts(runner)).toHaveLength(model.objective.responses.length * 2);
    for (const [index, response] of view.calculation.responses.entries()) {
      const chart = charts(runner).find(item => item.chartId === `bo-loo-residual-${response.response_id}`)!;
      expect(chart).toBeDefined(); expect(chart.points.map(point => [point.id, point.x, point.y])).toEqual(response.points.map(point => [point.trial_id, point.predicted, point.residual]));
      expect(chart.yUnit).toBe(model.objective.responses[index].unit);
      expect(chart.sourceKey).toContain(view.calculation_sha256); expect(chart.sourceKey).toContain(view.model_sha256);
      expect(chart.referenceLines).toEqual([expect.objectContaining({ y1: 0, y2: 0 })]);
      const html = renderToStaticMarkup(<InteractiveScatterChart {...chart} />);
      expect(html).toContain('data-point-id="singleton" data-x="5" data-y="0"');
      expect(html).toContain('data-y1="0" data-y2="0"');
      expect(chart.description).toContain(locale === "en" ? "full-fit" : "전체 적합");
    }
    const html = renderToStaticMarkup(<>{runner.output}</>);
    expect(html).toContain(locale === "en" ? "constant observed response" : "관측 반응이 상수");
    expect(html).toContain("-2");
    runner.act(() => setCurrentLocale(locale === "en" ? "ko" : "en"));
    expect(requestBoLoo).toHaveBeenCalledTimes(1);
  });
});
