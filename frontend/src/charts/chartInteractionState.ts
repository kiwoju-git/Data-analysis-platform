import type { ViewportAnchor } from "./chartCoordinates";

export interface ChartInteractionState {
  sourceKey: string;
  hoveredId: string | null;
  focusedId: string | null;
  pinnedId: string | null;
  rovingId: string | null;
  pointerAnchor: ViewportAnchor | null;
  dismissed: boolean;
}

export type ChartInteractionAction =
  | { type: "hover"; id: string; anchor: ViewportAnchor | null }
  | { type: "focus" | "pin" | "roving" | "controlledPin"; id: string }
  | { type: "leave" | "blur"; id: string }
  | { type: "clear" };

export function initialChartInteraction(sourceKey: string, ids: readonly string[]): ChartInteractionState {
  return {
    sourceKey, hoveredId: null, focusedId: null, pinnedId: null,
    rovingId: ids[0] ?? null, pointerAnchor: null, dismissed: false,
  };
}

export function reconcileChartInteraction(
  state: ChartInteractionState, sourceKey: string, ids: readonly string[],
): ChartInteractionState {
  if (sourceKey !== state.sourceKey) return initialChartInteraction(sourceKey, ids);
  const valid = (id: string | null) => id !== null && ids.includes(id) ? id : null;
  const hoveredId = valid(state.hoveredId);
  const focusedId = valid(state.focusedId);
  const pinnedId = valid(state.pinnedId);
  const rovingId = valid(state.rovingId) ?? ids[0] ?? null;
  if (hoveredId === state.hoveredId && focusedId === state.focusedId &&
      pinnedId === state.pinnedId && rovingId === state.rovingId) return state;
  return { ...state, hoveredId, focusedId, pinnedId, rovingId,
    pointerAnchor: hoveredId === null ? null : state.pointerAnchor };
}

export function reduceChartInteraction(
  state: ChartInteractionState, action: ChartInteractionAction,
): ChartInteractionState {
  switch (action.type) {
    case "hover": return { ...state, hoveredId: action.id, pointerAnchor: action.anchor, dismissed: false };
    case "focus": return { ...state, focusedId: action.id, rovingId: action.id, dismissed: false };
    case "pin": return { ...state, pinnedId: action.id, rovingId: action.id, dismissed: false };
    case "controlledPin": return { ...state, rovingId: action.id, dismissed: false };
    case "roving": return { ...state, rovingId: action.id };
    case "leave": return state.hoveredId === action.id
      ? { ...state, hoveredId: null, pointerAnchor: null } : state;
    case "blur": return state.focusedId === action.id ? { ...state, focusedId: null } : state;
    case "clear": return { ...state, hoveredId: null, focusedId: null, pinnedId: null,
      pointerAnchor: null, dismissed: true };
  }
}

export function chartActiveId(state: ChartInteractionState): string | null {
  return state.dismissed ? null : state.hoveredId ?? state.focusedId ?? state.pinnedId;
}

export function adjacentChartItem(ids: readonly string[], id: string, key: string): string | null {
  if (ids.length === 0) return null;
  const index = Math.max(0, ids.indexOf(id));
  if (key === "Home") return ids[0];
  if (key === "End") return ids[ids.length - 1];
  if (key === "ArrowRight" || key === "ArrowDown") return ids[Math.min(ids.length - 1, index + 1)];
  if (key === "ArrowLeft" || key === "ArrowUp") return ids[Math.max(0, index - 1)];
  return null;
}
