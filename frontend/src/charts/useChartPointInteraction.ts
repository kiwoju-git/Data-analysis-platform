import { useState, type KeyboardEvent, type PointerEvent } from "react";

export interface ActiveChartPoint {
  id: string;
  left: number;
  source: "focus" | "pointer" | "selection";
  top: number;
}

export function useChartPointInteraction() {
  const [activePoint, setActivePoint] = useState<ActiveChartPoint | null>(null);

  function activate(
    id: string,
    left: number,
    top: number,
    source: ActiveChartPoint["source"],
  ) {
    setActivePoint({ id, left, top, source });
  }

  function move(id: string, event: PointerEvent<SVGCircleElement>) {
    const bounds = event.currentTarget.ownerSVGElement?.getBoundingClientRect();
    if (bounds === undefined) return;
    const left = event.clientX - bounds.left;
    const top = event.clientY - bounds.top;
    setActivePoint((current) => {
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
    setActivePoint((current) =>
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
    }
  }

  return { activePoint, activate, clear, handleKeyDown, move };
}
