import * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DatasetVersionResponse } from "../../api";
import type { DatasetImportPreflightResponse } from "../../api/types/boDatasetImport";
import type { preflightDatasetImport, createDatasetStudy } from "../../api/boDatasetImport";
import { setCurrentLocale } from "../../i18n/store";
import { BayesianDatasetImportPanel } from "./BayesianDatasetImportPanel";

const api = vi.hoisted(() => ({ preflightDatasetImport: vi.fn<typeof preflightDatasetImport>(), createDatasetStudy: vi.fn<typeof createDatasetStudy>() }));
vi.mock("../../api/boDatasetImport", () => api);
type Props = Record<string, unknown>;
type Element = React.ReactElement<Props>;
type Slot = { value?: unknown; deps?: React.DependencyList; cleanup?: () => void };
const dispatcher = (React as unknown as { __SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED: { ReactCurrentDispatcher: { current: unknown } } }).__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentDispatcher;
const runners: Runner[] = [];

// Same node-only hook dispatcher pattern as gpPredictionRequestRace.test.tsx.
class Runner {
  private slots: Slot[] = [];
  private cursor = 0;
  private pending = true;
  output: React.ReactNode;
  constructor(private component: () => React.ReactNode) { runners.push(this); this.render(); }
  act(action: () => void) { action(); this.render(); }
  async flush() { for (let index = 0; index < 12; index++) { await Promise.resolve(); this.render(); } }
  unmount() { this.slots.forEach(slot => slot.cleanup?.()); }
  rerender() { this.pending = true; this.render(); }
  private slot() { const index = this.cursor++; return this.slots[index] ?? (this.slots[index] = {}); }
  private render() {
    while (this.pending) {
      this.pending = false; this.cursor = 0;
      const effects: (() => void)[] = [], previous = dispatcher.current;
      dispatcher.current = {
        useContext: () => null,
        useRef: (value: unknown) => { const slot = this.slot(); if (!("value" in slot)) slot.value = { current: value }; return slot.value; },
        useState: (initial: unknown) => {
          const slot = this.slot(); if (!("value" in slot)) slot.value = typeof initial === "function" ? (initial as () => unknown)() : initial;
          return [slot.value, (next: unknown) => { const value = typeof next === "function" ? (next as (old: unknown) => unknown)(slot.value) : next; if (!Object.is(value, slot.value)) { slot.value = value; this.pending = true; } }];
        },
        useEffect: (effect: React.EffectCallback, deps?: React.DependencyList) => {
          const slot = this.slot(); if (!slot.deps || !deps || deps.some((value, index) => !Object.is(value, slot.deps?.[index]))) effects.push(() => { slot.cleanup?.(); const cleanup = effect(); slot.cleanup = typeof cleanup === "function" ? cleanup : undefined; slot.deps = deps; });
        },
      };
      try { this.output = this.component(); } finally { dispatcher.current = previous; }
      effects.forEach(effect => effect());
    }
  }
}
function elements(node: React.ReactNode): Element[] {
  if (Array.isArray(node)) return node.flatMap(elements);
  if (!React.isValidElement<Props>(node)) return [];
  if (typeof node.type === "function" && (node.type.name === "BayesianConstraintEditor" || node.type.name === "BayesianCategoryCorrelationEditor")) return elements((node.type as (props: Props) => React.ReactNode)(node.props));
  return [node, ...elements(node.props.children as React.ReactNode)];
}
function find(runner: Runner, predicate: (element: Element) => boolean) { const result = elements(runner.output).find(predicate); if (!result) throw new Error("import_test_control_missing"); return result; }
function field(runner: Runner, label: string) { return find(runner, node => node.props["aria-label"] === label); }
function edit(runner: Runner, label: string, value: string) {
  runner.act(() => (field(runner, label).props.onChange as (event: { currentTarget: { value: string } }) => void)({ currentTarget: { value } }));
}
function click(runner: Runner, text: string) {
  const control = find(runner, node => node.type === "button" && (node.props["aria-label"] === text || React.Children.toArray(node.props.children as React.ReactNode).includes(text)));
  runner.act(() => (control.props.onClick as () => void)());
}
const version = {
  version_id: "version", schema_hash: "a".repeat(64), columns: [
    { column_id: "x", display_name: "온도", unit: "C" }, { column_id: "z", display_name: "촉매", unit: null }, { column_id: "y", display_name: "측정값", unit: "g" },
  ],
} as DatasetVersionResponse;
const preview: DatasetImportPreflightResponse = {
  schema_version: 1, source: { dataset_id: "synthetic-dataset", dataset_version_id: "version", schema_hash: version.schema_hash,
    canonical_sha256: "b".repeat(64), raw_sha256: "d".repeat(64), filter_sha256: "e".repeat(64) },
  preflight_sha256: "c".repeat(64), n_total: 2, n_filtered: 0, n_missing: 0, n_used: 2,
  unique_coordinate_count: 2, repeated_coordinate_count: 0, conflicting_coordinate_count: 0, warnings: [],
};
function mount() {
  setCurrentLocale("en");
  const outer = new Runner(() => BayesianDatasetImportPanel({ ownerKey: "synthetic", version, filterSnapshot: { expression_version: 1, conditions: [] }, disabled: false, onBusyChange: () => undefined, onCreated: () => undefined }));
  const form = outer.output as Element;
  return new Runner(() => (form.type as (props: Props) => React.ReactNode)(form.props));
}
function mapped() {
  const runner = mount(); edit(runner, "Import study name", "한글 연구"); edit(runner, "X 1", "x"); edit(runner, "X 1 low", "0"); edit(runner, "X 1 high", "10"); edit(runner, "Y", "y"); return runner;
}
function constrained(runner: Runner) { click(runner, "Add constraint"); edit(runner, "Coefficient constraint_1 factor_1", "1"); edit(runner, "Bound constraint_1", "8"); }
beforeEach(() => { api.preflightDatasetImport.mockReset(); api.createDatasetStudy.mockReset(); });
afterEach(() => { runners.splice(0).forEach(runner => runner.unmount()); setCurrentLocale("ko"); });

describe("import advanced controls", () => {
  it("keeps mixture toggles in inline native checkbox labels", () => {
    const runner = mount();
    const checkboxLabel = (caption: string, index = 0) => elements(runner.output).filter(node => node.type === "label" && React.Children.toArray(node.props.children as React.ReactNode).includes(caption))[index];
    const toggle = checkboxLabel("Mixture study");
    expect(toggle.props.className).toBe("checkbox-label");
    const input = elements(toggle).find(node => node.type === "input" && node.props.type === "checkbox")!;
    expect(input.props.checked).toBe(false);
    runner.act(() => (input.props.onChange as (event: { currentTarget: { checked: boolean } }) => void)({ currentTarget: { checked: true } }));
    expect(elements(runner.output).filter(node => node.type === "input" && node.props.type === "checkbox")).toHaveLength(3);
    for (let index = 0; index < 2; index++) {
      const component = checkboxLabel("Mixture components", index);
      expect(component.props.className).toBe("checkbox-label");
      expect(elements(component).some(node => node.type === "input" && node.props.type === "checkbox")).toBe(true);
    }
  });
  it("guards only referenced factor removal, kind and mapped column, preserving constraints and the goal", async () => {
    const runner = mapped(); edit(runner, "Goal", "minimize"); click(runner, "Add predictor"); edit(runner, "X 2", "z"); edit(runner, "X 2 low", "0"); edit(runner, "X 2 high", "1"); constrained(runner);
    expect(field(runner, "X 1").props.disabled).toBe(true); expect(field(runner, "X 1 type").props.disabled).toBe(true);
    expect(field(runner, "Remove predictor 1").props.disabled).toBe(true);
    edit(runner, "X 1", "z"); edit(runner, "X 1 type", "nominal"); click(runner, "Remove predictor 1");
    expect(field(runner, "X 1").props.value).toBe("x"); expect(field(runner, "X 1 type").props.value).toBe("continuous");
    expect(field(runner, "X 2").props.disabled).not.toBe(true);
    click(runner, "Remove predictor 2");
    api.preflightDatasetImport.mockRejectedValue(new Error("bayesian_import_failed")); click(runner, "Preflight import"); await runner.flush();
    expect(api.preflightDatasetImport.mock.calls[0][0]).toMatchObject({ name: "한글 연구", objective: { goal_type: "minimize" }, constraints: [{ bound: 8, terms: [{ factor_id: "factor_1", coefficient: 1 }] }] });
    click(runner, "Remove constraint constraint_1"); expect(field(runner, "X 1").props.disabled).not.toBe(true);
  });
  it("offers policies by category kind and blocks an ordinal-only policy after nominal switch", () => {
    const runner = mapped(); edit(runner, "X 1 type", "ordinal"); edit(runner, "X 1 levels", "낮음\n높음");
    const options = () => elements(field(runner, "X 1 Category correlation policy")).filter(node => node.type === "option").map(node => node.props.value);
    expect(options()).toEqual(["equal_positive_correlation_v1", "unequal_hyperspherical_correlation_v1", "ordinal_monotone_latent_rbf_v1"]);
    edit(runner, "X 1 Category correlation policy", "ordinal_monotone_latent_rbf_v1"); edit(runner, "X 1 type", "nominal");
    expect(field(runner, "X 1 Category correlation policy").props["aria-invalid"]).toBe(true);
    expect(elements(runner.output).filter(node => node.type === "td").some(node => elements(node).some(child => child.type === "p" && child.props.role === "alert"))).toBe(true);
    click(runner, "Preflight import"); expect(api.preflightDatasetImport).not.toHaveBeenCalled();
    edit(runner, "X 1 Category correlation policy", "unequal_hyperspherical_correlation_v1");
    expect(field(runner, "X 1 Category correlation policy").props["aria-invalid"]).not.toBe(true);
    expect(options()).not.toContain("ordinal_monotone_latent_rbf_v1");
  });
  it("renders only numeric coefficient controls, bounds the constraint count and describes invalid numbers", () => {
    const runner = mapped(); click(runner, "Add predictor"); edit(runner, "X 2", "z"); edit(runner, "X 2 type", "nominal");
    constrained(runner);
    expect(elements(runner.output).filter(node => node.type === "input" && String(node.props["aria-label"]).startsWith("Coefficient constraint_1"))).toHaveLength(1);
    edit(runner, "Coefficient constraint_1 factor_1", "1abc");
    const coefficient = field(runner, "Coefficient constraint_1 factor_1");
    expect(coefficient.props["aria-invalid"]).toBe(true);
    expect(coefficient.props["aria-describedby"]).toBeTruthy();
    for (let index = 1; index < 16; index++) click(runner, "Add constraint");
    expect(find(runner, node => node.type === "button" && React.Children.toArray(node.props.children as React.ReactNode).includes("Add constraint")).props.disabled).toBe(true);
  });
  it("invalidates a held real-hook preflight on advanced edits and preserves values after locale rerender", async () => {
    const runner = mapped(); constrained(runner);
    let resolve!: (value: DatasetImportPreflightResponse) => void;
    api.preflightDatasetImport.mockReturnValue(new Promise<DatasetImportPreflightResponse>(accept => { resolve = accept; }));
    click(runner, "Preflight import"); const request = api.preflightDatasetImport.mock.calls[0][0];
    edit(runner, "Bound constraint_1", "1abc");
    resolve(preview); await runner.flush();
    expect(elements(runner.output).some(node => node.props["aria-label"] === "Import review")).toBe(false);
    expect(field(runner, "Bound constraint_1").props.value).toBe("1abc");
    expect(request.constraints[0].bound).toBe(8);
    setCurrentLocale("ko"); runner.rerender(); expect(field(runner, "우변 constraint_1").props.value).toBe("1abc");
    expect(field(runner, "가져오기 Study 이름").props.value).toBe("한글 연구");
  });
  it("submits the selected category policy and invalidates reviewed preflight on policy edit", async () => {
    const runner = mapped(); edit(runner, "X 1 type", "ordinal"); edit(runner, "X 1 levels", "낮음\n높음");
    edit(runner, "Response objective", "vector"); edit(runner, "Y 1", "y");
    const goalEditor = find(runner, node => typeof node.type === "function" && node.type.name === "BayesianResponseGoals").props.draft as { updateResponseGoal: (key: number, field: "lower" | "target", value: string) => void };
    runner.act(() => { goalEditor.updateResponseGoal(1, "lower", "0"); goalEditor.updateResponseGoal(1, "target", "10"); });
    edit(runner, "X 1 Category correlation policy", "unequal_hyperspherical_correlation_v1");
    api.preflightDatasetImport.mockResolvedValue(preview);
    click(runner, "Preflight import"); await runner.flush();
    expect(api.preflightDatasetImport.mock.calls[0][0]).toMatchObject({ factor_mappings: [{ column_id: "x", factor: { levels: ["낮음", "높음"], correlation_policy: "unequal_hyperspherical_correlation_v1" } }] });
    expect(elements(runner.output).some(node => node.props["aria-label"] === "Import review")).toBe(true);
    edit(runner, "X 1 Category correlation policy", "ordinal_monotone_latent_rbf_v1");
    expect(elements(runner.output).some(node => node.props["aria-label"] === "Import review")).toBe(false);
  });
});
