import { useRef, useState, type KeyboardEvent, type PointerEvent } from "react";

export interface ActiveChartItem {
  id: string;
  left: number;
  source: "focus" | "pointer" | "selection";
  top: number;
}

export function useChartItemInteraction(itemIds: string[]) {
  const [activeItem, setActiveItem] = useState<ActiveChartItem | null>(null);
  const [rovingId, setRovingId] = useState<string | null>(itemIds[0] ?? null);
  const itemRefs = useRef(new Map<string, SVGElement>());
  const effectiveRovingId =
    rovingId !== null && itemIds.includes(rovingId) ? rovingId : (itemIds[0] ?? null);

  function activate(
    id: string,
    left: number,
    top: number,
    source: ActiveChartItem["source"],
  ) {
    setRovingId(id);
    setActiveItem({ id, left, top, source });
  }

  function move<T extends SVGElement>(id: string, event: PointerEvent<T>) {
    const bounds = event.currentTarget.ownerSVGElement?.getBoundingClientRect();
    if (bounds === undefined) return;
    const left = event.clientX - bounds.left;
    const top = event.clientY - bounds.top;
    setRovingId(id);
    setActiveItem((current) => {
      if (
        current?.id === id &&
        current.source === "pointer" &&
        Math.abs(current.left - left) < 3 &&
        Math.abs(current.top - top) < 3
      ) {
        return current;
      }
      return { id, left, top, source: "pointer" };
    });
  }

  function clear(id?: string) {
    setActiveItem((current) =>
      id === undefined || current?.id === id ? null : current,
    );
  }

  function handleKeyDown(
    event: KeyboardEvent<Element>,
    id?: string,
    left?: number,
    top?: number,
  ) {
    if (event.key === "Escape") {
      event.preventDefault();
      clear();
      return;
    }
    if ((event.key === "Enter" || event.key === " ") && id !== undefined) {
      event.preventDefault();
      activate(id, left ?? 0, top ?? 0, "selection");
      return;
    }
    if (id === undefined || itemIds.length === 0) return;

    const currentIndex = Math.max(0, itemIds.indexOf(id));
    let nextIndex: number | null = null;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      nextIndex = Math.min(itemIds.length - 1, currentIndex + 1);
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      nextIndex = Math.max(0, currentIndex - 1);
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = itemIds.length - 1;
    }
    if (nextIndex === null) return;

    event.preventDefault();
    const nextId = itemIds[nextIndex];
    setRovingId(nextId);
    itemRefs.current.get(nextId)?.focus();
  }

  function itemRef(id: string, element: SVGElement | null) {
    if (element === null) itemRefs.current.delete(id);
    else itemRefs.current.set(id, element);
  }

  return {
    activeItem,
    activate,
    clear,
    handleKeyDown,
    itemRef,
    move,
    tabIndexFor: (id: string) => (id === effectiveRovingId ? 0 : -1),
  };
}
