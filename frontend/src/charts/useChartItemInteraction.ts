import { useContext, useEffect, useId, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { ChartSourceContext } from "./chartSourceContext";
import { elementCenterToViewport, pointerToViewport, svgPointToViewport, type ViewportAnchor } from "./chartCoordinates";
import { adjacentChartItem, chartActiveId, initialChartInteraction, reconcileChartInteraction,
  reduceChartInteraction, type ChartInteractionAction } from "./chartInteractionState";

export interface ActiveChartItem {
  id: string;
  source: "focus" | "pointer" | "selection";
  anchor: ViewportAnchor | null;
}

export interface ChartInteractionOptions {
  sourceKey?: string;
  selectedId?: string | null;
  onSelect?: (id: string) => void;
  onClear?: () => void;
  onActivate?: (id: string) => void;
}

export function useChartItemInteraction(itemIds: readonly string[], options: ChartInteractionOptions = {}) {
  const resultSourceKey = useContext(ChartSourceContext);
  const sourceKey = JSON.stringify([resultSourceKey, options.sourceKey ?? ""]);
  const controlled = options.selectedId !== undefined;
  const [stored, setStored] = useState(() => initialChartInteraction(sourceKey, itemIds));
  const reconciled = reconcileChartInteraction(stored, sourceKey, itemIds);
  const sourceChanged = stored.sourceKey !== sourceKey;
  const previousControlledId = useRef(options.selectedId);
  const externalSelectionChanged = controlled && previousControlledId.current !== options.selectedId;
  const pinnedId = controlled
    ? !sourceChanged && (!reconciled.dismissed || externalSelectionChanged) && options.selectedId != null && itemIds.includes(options.selectedId)
      ? options.selectedId : null
    : reconciled.pinnedId;
  const state = { ...reconciled, pinnedId, dismissed: externalSelectionChanged ? false : reconciled.dismissed };
  const activeId = chartActiveId(state);
  const source = state.hoveredId !== null ? "pointer" : state.focusedId !== null ? "focus" : "selection";
  const itemRefs = useRef(new Map<string, SVGElement>());
  const tooltipId = `chart-tooltip-${useId().replace(/:/g, "")}`;
  const callbacks = useRef(options);
  callbacks.current = options;
  const previousSelection = useRef({ id: pinnedId, sourceKey });
  const [elementAnchor, setElementAnchor] = useState<{ id: string; sourceKey: string; anchor: ViewportAnchor | null } | null>(null);


  useEffect(() => {
    setStored((current) => {
      const next = reconcileChartInteraction(current, sourceKey, itemIds);
      return externalSelectionChanged && options.selectedId != null && itemIds.includes(options.selectedId)
        ? reduceChartInteraction(next, { type: "controlledPin", id: options.selectedId }) : next;
    });
    previousControlledId.current = options.selectedId;
    const previous = previousSelection.current;
    if (previous.id !== null && (previous.sourceKey !== sourceKey || !itemIds.includes(previous.id))) {
      callbacks.current.onClear?.();
    }
    previousSelection.current = { id: pinnedId, sourceKey };
  }, [itemIds, sourceKey, pinnedId, externalSelectionChanged, options.selectedId]);

  useEffect(() => {
    if (activeId === null || source === "pointer") return;
    let frame: number | null = null;
    const update = () => {
      frame = null;
      const target = itemRefs.current.get(activeId);
      const anchor = target ? elementCenterToViewport(target) : null;
      setElementAnchor((current) => current?.id === activeId && current.sourceKey === sourceKey &&
        current.anchor?.clientX === anchor?.clientX && current.anchor?.clientY === anchor?.clientY
        ? current : { id: activeId, sourceKey, anchor });
    };
    const schedule = () => { if (frame === null) frame = requestAnimationFrame(update); };
    const target = itemRefs.current.get(activeId);
    const observer = new ResizeObserver(schedule);
    // Moving an existing SVG point changes geometry but not necessarily its size.
    const geometryObserver = new MutationObserver(schedule);
    if (target) {
      observer.observe(target);
      geometryObserver.observe(target.ownerSVGElement ?? target, {
        attributes: true, subtree: true,
        attributeFilter: ["cx", "cy", "r", "x", "y", "width", "height", "points", "d", "transform", "viewBox"],
      });
      if (target.ownerSVGElement) {
        observer.observe(target.ownerSVGElement);
        if (target.ownerSVGElement.parentElement) observer.observe(target.ownerSVGElement.parentElement);
      }
    }
    update();
    window.addEventListener("resize", schedule);
    window.addEventListener("scroll", schedule, true);
    return () => {
      observer.disconnect();
      geometryObserver.disconnect();
      window.removeEventListener("resize", schedule);
      window.removeEventListener("scroll", schedule, true);
      if (frame !== null) cancelAnimationFrame(frame);
    };
  }, [activeId, source, sourceKey]);

  function dispatch(action: ChartInteractionAction) {
    setStored((current) => reduceChartInteraction(reconcileChartInteraction(current, sourceKey, itemIds), action));
  }
  function pin(id: string) {
    if (!itemIds.includes(id)) return;
    dispatch({ type: controlled ? "controlledPin" : "pin", id });
    callbacks.current.onSelect?.(id);
  }
  function activateItem(id: string, activationSource: ActiveChartItem["source"]) {
    if (!itemIds.includes(id)) return;
    if (activationSource === "selection") pin(id);
    else {
      if (activationSource === "focus") dispatch({ type: "focus", id });
      else dispatch({ type: "hover", id, anchor: itemRefs.current.has(id)
        ? elementCenterToViewport(itemRefs.current.get(id)!) : null });
      callbacks.current.onActivate?.(id);
    }
  }
  // Compatibility coordinates are SVG user units, never CSS pixels.
  function activate(id: string, x: number, y: number, activationSource: ActiveChartItem["source"]) {
    if (activationSource !== "pointer") return activateItem(id, activationSource);
    const svg = itemRefs.current.get(id)?.ownerSVGElement;
    dispatch({ type: "hover", id, anchor: svg ? svgPointToViewport(svg, x, y) : null });
    callbacks.current.onActivate?.(id);
  }
  function move<T extends SVGElement>(id: string, event: PointerEvent<T>) {
    if (!itemIds.includes(id)) return;
    if (state.hoveredId !== id) callbacks.current.onActivate?.(id);
    dispatch({ type: "hover", id, anchor: pointerToViewport(event) });
  }
  function clearAll() {
    dispatch({ type: "clear" });
    callbacks.current.onClear?.();
  }
  function handleKeyDown(event: KeyboardEvent<Element>, id?: string, ...legacyCoordinates: number[]) {
    void legacyCoordinates;
    if (event.defaultPrevented) return;
    if (event.key === "Escape") { event.preventDefault(); clearAll(); return; }
    if (id === undefined) return;
    if (event.key === "Enter" || event.key === " ") { event.preventDefault(); pin(id); return; }
    const nextId = adjacentChartItem(itemIds, id, event.key);
    if (nextId === null) return;
    event.preventDefault();
    dispatch({ type: "roving", id: nextId });
    itemRefs.current.get(nextId)?.focus();
  }
  const anchor = source === "pointer" ? state.pointerAnchor
    : elementAnchor?.id === activeId && elementAnchor.sourceKey === sourceKey ? elementAnchor.anchor : null;
  const activeItem: ActiveChartItem | null = activeId === null ? null : { id: activeId, source, anchor };
  return {
    activeItem, pinnedId, detailId: pinnedId ?? state.focusedId, tooltipId,
    activate, activateItem, move, pin, clearAll,
    clearHover: (id: string) => dispatch({ type: "leave", id }),
    clearFocus: (id: string) => dispatch({ type: "blur", id }),
    handleKeyDown,
    itemRef: (id: string, element: SVGElement | null) => {
      if (element === null) itemRefs.current.delete(id);
      else itemRefs.current.set(id, element);
    },
    tabIndexFor: (id: string) => id === state.rovingId ? 0 : -1,
    describedBy: (id: string) => id === activeId && anchor !== null ? tooltipId : undefined,
    stateClass: (id: string) => [
      id === pinnedId ? "chart-point-selected" : "",
      id === state.hoveredId ? "chart-point-hovered" : "",
      id === state.focusedId ? "chart-point-focused" : "",
    ].filter(Boolean).join(" "),
  };
}
