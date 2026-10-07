import { describe, expect, it } from "vitest";
import { adjacentChartItem, chartActiveId, initialChartInteraction, reconcileChartInteraction, reduceChartInteraction } from "./chartInteractionState";

const ids = ["row:2", "row:4", "row:8"];
describe("chart interaction state", () => {
  it("keeps explicit selection while hovering and leaving another point", () => {
    let state = initialChartInteraction("analysis:1", ids);
    state = reduceChartInteraction(state, { type: "pin", id: ids[0] });
    state = reduceChartInteraction(state, { type: "hover", id: ids[1], anchor: { clientX: 10, clientY: 20 } });
    expect(chartActiveId(state)).toBe(ids[1]);
    expect(state.pinnedId).toBe(ids[0]);
    expect(state.rovingId).toBe(ids[0]);
    state = reduceChartInteraction(state, { type: "leave", id: ids[1] });
    expect(chartActiveId(state)).toBe(ids[0]);
    state = reduceChartInteraction(state, { type: "focus", id: ids[2] });
    expect(chartActiveId(state)).toBe(ids[2]);
    state = reduceChartInteraction(state, { type: "blur", id: ids[2] });
    expect(state.pinnedId).toBe(ids[0]);
  });

  it("Escape dismisses display without moving the roving focus", () => {
    let state = reduceChartInteraction(initialChartInteraction("a", ids), { type: "focus", id: ids[1] });
    state = reduceChartInteraction(state, { type: "pin", id: ids[1] });
    state = reduceChartInteraction(state, { type: "clear" });
    expect(chartActiveId(state)).toBeNull();
    expect(state.pinnedId).toBeNull();
    expect(state.rovingId).toBe(ids[1]);
    expect(chartActiveId(reconcileChartInteraction(state, "a", [...ids]))).toBeNull();
    expect(chartActiveId(reduceChartInteraction(state, { type: "focus", id: ids[1] }))).toBe(ids[1]);
  });

  it("invalidates missing IDs immediately, preserves existing IDs, and resets on source replacement", () => {
    const state = reduceChartInteraction(initialChartInteraction("a", ids), { type: "pin", id: ids[1] });
    expect(reconcileChartInteraction(state, "a", [...ids])).toBe(state);
    expect(reconcileChartInteraction(state, "a", [ids[0]]).pinnedId).toBeNull();
    expect(reconcileChartInteraction(state, "b", ids)).toEqual(initialChartInteraction("b", ids));
  });

  it("navigates ordered items without trapping Tab or wrapping at endpoints", () => {
    expect(adjacentChartItem(ids, ids[0], "ArrowRight")).toBe(ids[1]);
    expect(adjacentChartItem(ids, ids[1], "End")).toBe(ids[2]);
    expect(adjacentChartItem(ids, ids[2], "Home")).toBe(ids[0]);
    expect(adjacentChartItem(ids, ids[0], "ArrowLeft")).toBe(ids[0]);
    expect(adjacentChartItem(ids, ids[1], "Tab")).toBeNull();
    expect(adjacentChartItem([], "missing", "Home")).toBeNull();
  });
});
