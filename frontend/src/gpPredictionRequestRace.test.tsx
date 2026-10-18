import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { AnalysisResultEnvelope, GaussianProcessPointPredictionRequest, GaussianProcessPointPredictionResponse, GaussianProcessRegressionResult, PlsPointPredictionResponse, PlsRegressionResult } from "./api";
import { gpFixture, plsFixture } from "./charts/resultChartFixtures";
import { GpSurfaceChart } from "./charts/GaussianProcessCharts";
import { GaussianProcessRegressionPanel } from "./GaussianProcessRegressionPanel";
import { PlsRegressionPanel } from "./PlsRegressionPanel";
import { setCurrentLocale } from "./i18n/store";

const requests = vi.hoisted(() => ({ gp: vi.fn(), pls: vi.fn(), download: vi.fn() }));
vi.mock("./api/regression", async (importOriginal) => ({
  ...await importOriginal<typeof import("./api/regression")>(),
  createGaussianProcessPointPredictions: requests.gp,
  createPlsPointPredictions: requests.pls,
}));
vi.mock("./api/client", async (importOriginal) => ({
  ...await importOriginal<typeof import("./api/client")>(),
  triggerBrowserDownload: requests.download,
}));

type Props = Record<string, unknown>;
type Element = React.ReactElement<Props>;
type Component = (props: Props) => React.ReactNode;
type HookSlot = { value?: unknown; deps?: React.DependencyList; cleanup?: () => void; effect?: boolean };
const internals = (React as unknown as {
  __SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED: { ReactCurrentDispatcher: { current: unknown } };
}).__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED;
const runners: PredictionHookRunner[] = [];

// The existing node hook harness pattern, isolated from A05's concurrently owned file.
class PredictionHookRunner {
  private slots: HookSlot[] = [];
  private cursor = 0;
  private pending = true;
  private effects: Array<() => void> = [];
  output: React.ReactNode;

  constructor(private component: Component, private props: Props) {
    runners.push(this);
    this.render();
  }

  update(props: Props) { this.props = props; this.pending = true; this.render(); }
  unmount() { for (const slot of this.slots) if (slot.effect) slot.cleanup?.(); }
  async flush() { for (let index = 0; index < 12; index += 1) { await Promise.resolve(); this.render(); } }
  act(action: () => void) { action(); this.render(); }

  private slot() { const index = this.cursor++; return this.slots[index] ?? (this.slots[index] = {}); }
  private changed(slot: HookSlot, deps?: React.DependencyList) {
    return !slot.deps || !deps || slot.deps.length !== deps.length || deps.some((value, index) => !Object.is(value, slot.deps?.[index]));
  }
  private memo(factory: () => unknown, deps?: React.DependencyList) {
    const slot = this.slot();
    if (this.changed(slot, deps)) { slot.value = factory(); slot.deps = deps; }
    return slot.value;
  }
  private effect(create: React.EffectCallback, deps?: React.DependencyList) {
    const slot = this.slot(); slot.effect = true;
    if (this.changed(slot, deps)) this.effects.push(() => {
      slot.cleanup?.(); const cleanup = create(); slot.cleanup = typeof cleanup === "function" ? cleanup : undefined; slot.deps = deps;
    });
  }
  private render() {
    while (this.pending) {
      this.pending = false; this.cursor = 0; this.effects = [];
      const previous = internals.ReactCurrentDispatcher.current;
      internals.ReactCurrentDispatcher.current = {
        useContext: () => null,
        useRef: (value: unknown) => {
          const slot = this.slot(); if (!("value" in slot)) slot.value = { current: value }; return slot.value;
        },
        useState: (initial: unknown) => {
          const slot = this.slot();
          if (!("value" in slot)) slot.value = typeof initial === "function" ? (initial as () => unknown)() : initial;
          return [slot.value, (next: unknown) => {
            const value = typeof next === "function" ? (next as (previous: unknown) => unknown)(slot.value) : next;
            if (!Object.is(slot.value, value)) { slot.value = value; this.pending = true; }
          }];
        },
        useMemo: (factory: () => unknown, deps?: React.DependencyList) => this.memo(factory, deps),
        useCallback: (callback: unknown, deps?: React.DependencyList) => this.memo(() => callback, deps),
        useEffect: (create: React.EffectCallback, deps?: React.DependencyList) => this.effect(create, deps),
        useLayoutEffect: (create: React.EffectCallback, deps?: React.DependencyList) => this.effect(create, deps),
      };
      try { this.output = this.component(this.props); }
      finally { internals.ReactCurrentDispatcher.current = previous; }
      for (const effect of this.effects) effect();
    }
  }
}

function elements(node: React.ReactNode): Element[] {
  if (Array.isArray(node)) return node.flatMap(elements);
  if (!React.isValidElement<Props>(node)) return [];
  return [node, ...elements(node.props.children as React.ReactNode)];
}
function find(node: React.ReactNode, predicate: (element: Element) => boolean): Element {
  const match = elements(node).find(predicate);
  if (!match) throw new Error("prediction_test_element_missing");
  return match;
}
function nestedComponent(node: React.ReactNode, name: string): Element {
  return find(node, (element) => typeof element.type === "function" && element.type.name === name);
}
function mountPrediction(kind: "gp" | "pls") {
  const result = kind === "gp" ? gpFixture() : plsFixture();
  const analysisId = `analysis-${kind}`;
  const common = { analysisResult: { analysis_id: analysisId } as AnalysisResultEnvelope, filterValidationError: null, isRunningAnalysis: false, version: null, onRun: () => undefined };
  const panel = new PredictionHookRunner(() => kind === "gp"
    ? GaussianProcessRegressionPanel({ ...common, result: result as GaussianProcessRegressionResult, methodId: "regression.gaussian_process" })
    : PlsRegressionPanel({ ...common, result: result as PlsRegressionResult, methodId: "regression.partial_least_squares" }), {});
  const results = nestedComponent(panel.output, kind === "gp" ? "GaussianProcessResults" : "PlsResults");
  const resultRunner = new PredictionHookRunner(results.type as Component, results.props);
  const prediction = nestedComponent(resultRunner.output, kind === "gp" ? "GaussianProcessPrediction" : "PlsPointPrediction");
  const runner = new PredictionHookRunner(prediction.type as Component, { ...prediction.props, analysisId });
  for (const predictor of result.predictors) edit(runner, `${predictor.display_name} 1`, "1");
  return { runner, result, analysisId };
}
function edit(runner: PredictionHookRunner, label: string, value: string) {
  const input = find(runner.output, (element) => element.type === "input" && element.props["aria-label"] === label);
  runner.act(() => (input.props.onChange as (event: { currentTarget: { value: string } }) => void)({ currentTarget: { value } }));
}
function predictButton(runner: PredictionHookRunner) {
  return find(runner.output, (element) => element.type === "button" && element.props.className === "primary-button");
}
function start(runner: PredictionHookRunner) { runner.act(() => (predictButton(runner).props.onClick as () => void)()); }
function state(runner: PredictionHookRunner) { return find(runner.output, (element) => element.type === "section").props["data-prediction-state"]; }
function clickAction(runner: PredictionHookRunner, predicate: (element: Element) => boolean) {
  const button = find(runner.output, (element) => element.type === "button" && predicate(element));
  runner.act(() => (button.props.onClick as () => void)());
}
function exports(runner: PredictionHookRunner) { return elements(runner.output).filter((element) => element.props["data-action"] === "download-prediction-snapshot"); }
function mean(runner: PredictionHookRunner, predictorCount = 2) {
  const body = find(runner.output, (element) => element.type === "tbody");
  const row = find(body.props.children as React.ReactNode, (element) => element.type === "tr");
  const cells = elements(row.props.children as React.ReactNode).filter((element) => element.type === "td");
  return renderToStaticMarkup(<>{cells[predictorCount + 1].props.children as React.ReactNode}</>);
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (cause: unknown) => void;
  const promise = new Promise<T>((accept, fail) => { resolve = accept; reject = fail; });
  return { promise, resolve, reject };
}
function gpResponse(request: GaussianProcessPointPredictionRequest, modelId = "model-gp"): GaussianProcessPointPredictionResponse {
  return { model_id: modelId, model_manifest_sha256: request.expected_model_manifest_sha256, response_column_id: "response", row_count: request.rows.length, interval_kind: "latent_and_new_observation", confidence_level: .95,
    rows: request.rows.map((row) => ({ client_row_id: row.client_row_id, predicted_mean: 101, latent_standard_deviation: .5, predictive_standard_deviation: 1, latent_interval_95: { lower: 100, upper: 102 }, predictive_interval_95: { lower: 99, upper: 103 }, warnings: [] })) };
}

beforeEach(() => { vi.resetAllMocks(); setCurrentLocale("en"); });
afterEach(() => { for (const runner of runners.splice(0)) runner.unmount(); setCurrentLocale("ko"); });

describe("direct prediction request ownership regressions", () => {
  it.each(["ko", "en"] as const)("pilot preserves small GP predictions and distinct intervals in %s", async (locale) => {
    setCurrentLocale(locale);
    requests.gp.mockImplementation((_model: string, request: GaussianProcessPointPredictionRequest) => {
      const response = gpResponse(request);
      response.rows[0] = { ...response.rows[0], predicted_mean: 1e-6, latent_standard_deviation: 2e-6,
        predictive_standard_deviation: 0.0004, latent_interval_95: { lower: 1e-6, upper: 2e-6 },
        predictive_interval_95: { lower: 1000.000001, upper: 1000.000002 } };
      return Promise.resolve(response);
    });
    const { runner, result, analysisId } = mountPrediction("gp"); start(runner); await runner.flush();
    expect(mean(runner)).toBe("1e-6");
    const html = renderToStaticMarkup(<>{runner.output}</>);
    expect(html).toContain("2e-6"); expect(html).toContain("4e-4");
    expect(html).toContain("[1e-6, 2e-6]");
    expect(html).toContain("[1,000.000001, 1,000.000002]");
    setCurrentLocale(locale === "ko" ? "en" : "ko"); runner.update({ result, analysisId });
    expect(mean(runner)).toBe("1e-6"); expect(requests.gp).toHaveBeenCalledTimes(1);
    clickAction(runner, (element) => element.props["data-action"] === "download-prediction-snapshot");
    const saved = JSON.parse(await (requests.download.mock.calls[0][0] as Blob).text()) as { response: GaussianProcessPointPredictionResponse };
    expect(saved.response.rows[0].predicted_mean).toBe(1e-6);
    expect(saved.response.rows[0].predictive_interval_95.upper).toBe(1000.000002);
  });
  it.each([-1e-6, 0])("pilot preserves actual GP mean %s", async (value) => {
    requests.gp.mockImplementation((_model: string, request: GaussianProcessPointPredictionRequest) => {
      const response = gpResponse(request); response.rows[0].predicted_mean = value; return Promise.resolve(response);
    });
    const { runner } = mountPrediction("gp"); start(runner); await runner.flush();
    expect(mean(runner)).toBe(String(value === 0 ? 0 : "-1e-6"));
  });
  it.each(["gp", "pls"] as const)("captures the explicit %s save choice without locale/edit side effects", (kind) => {
    requests[kind].mockReturnValue(new Promise(() => undefined));
    const { runner, result, analysisId } = mountPrediction(kind);
    const control = () => nestedComponent(runner.output, "PredictionSaveControl");
    expect(control().props.checked).toBe(false);
    start(runner);
    expect((requests[kind].mock.calls[0][1] as GaussianProcessPointPredictionRequest).save_result).toBe(false);
    edit(runner, "temperature_c 1", "2");
    runner.act(() => (control().props.onChange as (value: boolean) => void)(true));
    setCurrentLocale("ko"); runner.update({ result, analysisId });
    expect(control().props.checked).toBe(true);
    expect(requests[kind]).toHaveBeenCalledTimes(1);
    start(runner);
    expect((requests[kind].mock.calls[1][1] as GaussianProcessPointPredictionRequest).save_result).toBe(true);
    expect((requests[kind].mock.calls[0][1] as GaussianProcessPointPredictionRequest).save_result).toBe(false);
    expect(control().props.disabled).toBe(true);
    runner.update({ result, analysisId: `${analysisId}-replacement` });
    expect(control().props.checked).toBe(false);
    expect(requests[kind]).toHaveBeenCalledTimes(2);
  });
  it("does not attach a late GP response to an edited input with the same client row ID", async () => {
    const response = deferred<GaussianProcessPointPredictionResponse>(); requests.gp.mockReturnValue(response.promise);
    const { runner } = mountPrediction("gp"); start(runner);
    const request = requests.gp.mock.calls[0][1] as GaussianProcessPointPredictionRequest;
    edit(runner, "temperature_c 1", "2");
    response.resolve(gpResponse(request)); await runner.flush();
    expect(mean(runner)).toBe("-");
    expect(state(runner)).toBe("stale");
    expect(renderToStaticMarkup(<>{runner.output}</>)).toContain("Prediction inputs changed");
  });

  it("releases the old busy state immediately after GP input invalidation", () => {
    requests.gp.mockReturnValue(new Promise(() => undefined));
    const { runner } = mountPrediction("gp"); start(runner);
    edit(runner, "temperature_c 1", "2");
    expect(predictButton(runner).props.disabled).toBe(false);
  });

  it("does not publish an old GP model's response after source replacement", async () => {
    const response = deferred<GaussianProcessPointPredictionResponse>(); requests.gp.mockReturnValue(response.promise);
    const { runner, result } = mountPrediction("gp"); start(runner);
    const request = requests.gp.mock.calls[0][1] as GaussianProcessPointPredictionRequest;
    const replacement = { ...result, model_manifest: { ...result.model_manifest!, model_id: "model-gp-next", manifest_sha256: "b".repeat(64) } };
    runner.update({ result: replacement, analysisId: "analysis-gp-next" });
    response.resolve(gpResponse(request)); await runner.flush();
    expect(mean(runner)).toBe("-");
  });

  it("rejects a GP result whose model identity does not match the submitted model", async () => {
    requests.gp.mockImplementation((_model: string, request: GaussianProcessPointPredictionRequest) => Promise.resolve(gpResponse(request, "foreign-model")));
    const { runner } = mountPrediction("gp"); start(runner); await runner.flush();
    expect(mean(runner)).toBe("-");
    expect(renderToStaticMarkup(<>{runner.output}</>)).toContain("gp_prediction_response_invalid");
  });

  it("does not publish a PLS response before snapshot validation succeeds", async () => {
    requests.pls.mockImplementation((_model: string, request: GaussianProcessPointPredictionRequest): Promise<PlsPointPredictionResponse> => Promise.resolve({ model_id: "model-pls", model_manifest_sha256: "b".repeat(64), response_column_id: "response", row_count: 1, intervals_supported: false, rows: [{ client_row_id: request.rows[0].client_row_id, predicted_value: 101, warnings: [] }] }));
    const { runner } = mountPrediction("pls"); start(runner); await runner.flush();
    expect(mean(runner)).toBe("-");
    expect(renderToStaticMarkup(<>{runner.output}</>)).toContain("pls_prediction_snapshot_mismatch");
  });

  it.each(["add", "delete"])("invalidates a pending GP batch immediately on row %s", async (action) => {
    const response = deferred<GaussianProcessPointPredictionResponse>(); requests.gp.mockReturnValue(response.promise);
    const { runner } = mountPrediction("gp"); start(runner);
    const request = requests.gp.mock.calls[0][1] as GaussianProcessPointPredictionRequest;
    clickAction(runner, (element) => action === "add" ? element.props.className === "secondary-button" : typeof element.props["aria-label"] === "string");
    expect(state(runner)).toBe("stale");
    response.resolve(gpResponse(request)); await runner.flush();
    expect(mean(runner)).toBe("-");
    expect(exports(runner)).toHaveLength(0);
  });

  it("keeps a superseded GP failure/finally from clearing a newer request", async () => {
    const first = deferred<GaussianProcessPointPredictionResponse>(); const second = deferred<GaussianProcessPointPredictionResponse>();
    requests.gp.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const { runner } = mountPrediction("gp"); start(runner);
    edit(runner, "temperature_c 1", "2"); start(runner);
    first.reject(new Error("gp_prediction_failed")); await runner.flush();
    expect(state(runner)).toBe("running");
    expect(renderToStaticMarkup(<>{runner.output}</>)).not.toContain("gp_prediction_failed");
    second.resolve(gpResponse(requests.gp.mock.calls[1][1] as GaussianProcessPointPredictionRequest)); await runner.flush();
    expect(state(runner)).toBe("ready");
    expect(mean(runner)).toBe("101");
  });

  it("rejects an initial GP response after source A-B-A transitions", async () => {
    const response = deferred<GaussianProcessPointPredictionResponse>(); requests.gp.mockReturnValue(response.promise);
    const { runner, result, analysisId } = mountPrediction("gp"); start(runner);
    const request = requests.gp.mock.calls[0][1] as GaussianProcessPointPredictionRequest;
    runner.update({ result, analysisId: "analysis-B" });
    runner.update({ result, analysisId });
    response.resolve(gpResponse(request)); await runner.flush();
    expect(mean(runner)).toBe("-");
    expect(state(runner)).toBe("empty");
  });

  it("exports only a completed exact GP snapshot and disables it after edits", async () => {
    requests.gp.mockImplementation((_model: string, request: GaussianProcessPointPredictionRequest) => Promise.resolve(gpResponse(request)));
    const { runner } = mountPrediction("gp"); start(runner); await runner.flush();
    clickAction(runner, (element) => element.props["data-action"] === "download-prediction-snapshot");
    const blob = requests.download.mock.calls[0][0] as Blob;
    const snapshot = JSON.parse(await blob.text()) as { predictor_column_ids: string[]; request: GaussianProcessPointPredictionRequest; response: GaussianProcessPointPredictionResponse; source_analysis_id: string; prediction_recalculated_on_export: boolean };
    expect(snapshot.source_analysis_id).toBe("analysis-gp");
    expect(snapshot.predictor_column_ids).toEqual(["x1", "x2"]);
    expect(snapshot.request).toEqual(requests.gp.mock.calls[0][1]);
    expect(snapshot.response).toEqual(gpResponse(snapshot.request));
    expect(snapshot.prediction_recalculated_on_export).toBe(false);
    expect(requests.gp).toHaveBeenCalledTimes(1);
    edit(runner, "temperature_c 1", "3");
    expect(exports(runner)).toHaveLength(0);
    expect(state(runner)).toBe("stale");
  });

  it("re-renders GP errors in the current locale without changing drafts or refetching", async () => {
    requests.gp.mockRejectedValue(new Error("gp_prediction_failed"));
    const { runner, result, analysisId } = mountPrediction("gp"); start(runner); await runner.flush();
    const before = renderToStaticMarkup(<>{runner.output}</>);
    setCurrentLocale("ko"); runner.update({ result, analysisId });
    const after = renderToStaticMarkup(<>{runner.output}</>);
    expect(before).not.toBe(after);
    expect(before).toContain("gp_prediction_failed"); expect(after).toContain("gp_prediction_failed");
    expect(find(runner.output, (element) => element.type === "input" && element.props["aria-label"] === "temperature_c 1").props.value).toBe("1");
    expect(requests.gp).toHaveBeenCalledTimes(1);
  });

  it("does not restore a completed GP snapshot after unmount", async () => {
    const response = deferred<GaussianProcessPointPredictionResponse>(); requests.gp.mockReturnValue(response.promise);
    const { runner } = mountPrediction("gp"); start(runner);
    const before = runner.output;
    runner.unmount();
    response.resolve(gpResponse(requests.gp.mock.calls[0][1] as GaussianProcessPointPredictionRequest)); await runner.flush();
    expect(runner.output).toBe(before);
    expect(exports(runner)).toHaveLength(0);
  });

  it("invalidates a GP request when only its saved manifest checksum changes", async () => {
    const response = deferred<GaussianProcessPointPredictionResponse>(); requests.gp.mockReturnValue(response.promise);
    const { runner, result, analysisId } = mountPrediction("gp"); start(runner);
    const request = requests.gp.mock.calls[0][1] as GaussianProcessPointPredictionRequest;
    runner.update({ analysisId, result: { ...result, model_manifest: { ...result.model_manifest!, manifest_sha256: "b".repeat(64) } } });
    response.resolve(gpResponse(request)); await runner.flush();
    expect(mean(runner)).toBe("-"); expect(exports(runner)).toHaveLength(0);
  });

  it("uses the current locale when an in-flight GP request fails after a locale switch", async () => {
    const response = deferred<GaussianProcessPointPredictionResponse>(); requests.gp.mockReturnValue(response.promise);
    const { runner, result, analysisId } = mountPrediction("gp"); start(runner);
    setCurrentLocale("ko"); runner.update({ result, analysisId });
    expect(state(runner)).toBe("running");
    response.reject(new Error("gp_prediction_failed")); await runner.flush();
    const korean = renderToStaticMarkup(<>{runner.output}</>);
    setCurrentLocale("en"); runner.update({ result, analysisId });
    const english = renderToStaticMarkup(<>{runner.output}</>);
    expect(korean).toContain("gp_prediction_failed"); expect(english).toContain("gp_prediction_failed");
    expect(korean).not.toBe(english); expect(requests.gp).toHaveBeenCalledTimes(1);
  });

  it("clears a previous PLS export before retry and publishes no mismatched retry response", async () => {
    const retry = deferred<PlsPointPredictionResponse>();
    requests.pls.mockImplementationOnce((_model: string, request: GaussianProcessPointPredictionRequest): Promise<PlsPointPredictionResponse> => Promise.resolve({ model_id: "model-pls", model_manifest_sha256: request.expected_model_manifest_sha256, response_column_id: "response", row_count: 1, intervals_supported: false, rows: [{ client_row_id: request.rows[0].client_row_id, predicted_value: 10, warnings: [] }] })).mockReturnValueOnce(retry.promise);
    const { runner } = mountPrediction("pls"); start(runner); await runner.flush();
    expect(exports(runner)).toHaveLength(1); expect(mean(runner)).toBe("10");
    start(runner);
    expect(exports(runner)).toHaveLength(0); expect(mean(runner)).toBe("-");
    const request = requests.pls.mock.calls[1][1] as GaussianProcessPointPredictionRequest;
    retry.resolve({ model_id: "foreign-model", model_manifest_sha256: request.expected_model_manifest_sha256, response_column_id: "response", row_count: 1, intervals_supported: false, rows: [{ client_row_id: request.rows[0].client_row_id, predicted_value: 99, warnings: [] }] });
    await runner.flush();
    expect(state(runner)).toBe("error"); expect(exports(runner)).toHaveLength(0); expect(mean(runner)).toBe("-");
  });

  it("re-renders PLS request errors without resetting input or calling prediction", async () => {
    requests.pls.mockRejectedValue(new Error("pls_prediction_failed"));
    const { runner, result, analysisId } = mountPrediction("pls"); start(runner); await runner.flush();
    const english = renderToStaticMarkup(<>{runner.output}</>);
    setCurrentLocale("ko"); runner.update({ result, analysisId });
    const korean = renderToStaticMarkup(<>{runner.output}</>);
    expect(english).not.toBe(korean);
    expect(korean).toContain("pls_prediction_failed");
    expect(find(runner.output, (element) => element.type === "input" && element.props["aria-label"] === "temperature_c 1").props.value).toBe("1");
    expect(requests.pls).toHaveBeenCalledTimes(1);
  });

  it("re-renders a surface response mismatch while preserving its original validated grid", async () => {
    const result = gpFixture(); result.two_predictor_surface!.grid_size = 2;
    const before = structuredClone(result.two_predictor_surface);
    requests.gp.mockImplementation((_model: string, request: GaussianProcessPointPredictionRequest) => {
      const response = gpResponse(request); response.rows[0].client_row_id = "wrong-cell"; return Promise.resolve(response);
    });
    const runner = new PredictionHookRunner((props) => GpSurfaceChart(props as unknown as { result: GaussianProcessRegressionResult; scope: string }), { result, scope: "analysis-gp:selected" });
    clickAction(runner, (element) => !("aria-pressed" in element.props)); await runner.flush();
    const english = renderToStaticMarkup(<>{runner.output}</>);
    setCurrentLocale("ko"); runner.update({ result, scope: "analysis-gp:selected" });
    const korean = renderToStaticMarkup(<>{runner.output}</>);
    expect(english).toContain("gp_surface_response_invalid"); expect(korean).toContain("gp_surface_response_invalid");
    expect(english).not.toBe(korean); expect(result.two_predictor_surface).toEqual(before);
    expect(requests.gp).toHaveBeenCalledTimes(1);
  });

  it("shows unknown GP warnings verbatim as safe text instead of a Ready status", async () => {
    const warning = 'unknown_<script>alert("x")</script>_\uE000gp.predictiveSd\uE001';
    requests.gp.mockImplementation((_model: string, request: GaussianProcessPointPredictionRequest) => {
      const response = gpResponse(request); response.rows[0].warnings = [warning]; return Promise.resolve(response);
    });
    const { runner } = mountPrediction("gp"); start(runner); await runner.flush();
    const html = renderToStaticMarkup(<>{runner.output}</>);
    expect(html).toContain("unknown_&lt;script&gt;");
    expect(html).toContain("\uE000gp.predictiveSd\uE001");
    expect(html).not.toContain("<script>"); expect(html).not.toContain(">Ready<");
    clickAction(runner, (element) => element.props["data-action"] === "download-prediction-snapshot");
    const snapshot = JSON.parse(await (requests.download.mock.calls[0][0] as Blob).text()) as { response: GaussianProcessPointPredictionResponse };
    expect(snapshot.response.rows[0].warnings).toEqual([warning]);
  });
});
