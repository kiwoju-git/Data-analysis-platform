import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { tooltipPosition, type ViewportAnchor } from "./chartCoordinates";

export interface ChartTooltipProps {
  id: string;
  title: string;
  details: ReadonlyArray<{ label: string; value: string }>;
  anchor: ViewportAnchor;
}

export function ChartTooltip({ id, title, details, anchor }: ChartTooltipProps) {
  const { clientX, clientY } = anchor;
  const ref = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState<{ left: number; top: number } | null>(null);
  useEffect(() => {
    let frame: number | null = null;
    const update = () => {
      frame = null;
      const rect = ref.current?.getBoundingClientRect();
      if (!rect) return;
      const next = tooltipPosition({ clientX, clientY }, rect.width, rect.height, window.innerWidth, window.innerHeight);
      setPosition((current) => current?.left === next.left && current.top === next.top ? current : next);
    };
    const schedule = () => { if (frame === null) frame = requestAnimationFrame(update); };
    const observer = new ResizeObserver(schedule);
    if (ref.current) observer.observe(ref.current);
    update();
    window.addEventListener("resize", schedule);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", schedule);
      if (frame !== null) cancelAnimationFrame(frame);
    };
  }, [clientX, clientY]);
  if (typeof document === "undefined") return null;
  return createPortal(
    <div id={id} ref={ref} className="chart-tooltip-portal" role="tooltip"
      style={{ left: position?.left ?? 0, top: position?.top ?? 0, visibility: position === null ? "hidden" : "visible" }}>
      <strong>{title}</strong>
      <dl>{details.map((detail, index) => <div key={`${detail.label}-${index}`}>
        <dt>{detail.label}</dt><dd>{detail.value}</dd>
      </div>)}</dl>
    </div>, document.body,
  );
}
