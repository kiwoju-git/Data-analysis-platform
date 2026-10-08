import { useId, type ReactNode } from "react";
import type { ChartLayout } from "./chartLayout";
import "./chartFrame.css";

export function ChartFrame({ chartId, title, description, layout, axes, children, overlay, footer, className = "" }: {
  chartId: string; title: string; description: string; layout: ChartLayout;
  axes?: ReactNode; children: ReactNode; overlay?: ReactNode; footer?: ReactNode; className?: string;
}) {
  const instanceId = useId().replace(/:/g, "");
  const titleId = `${chartId}-title-${instanceId}`;
  const descriptionId = `${chartId}-description-${instanceId}`;
  const clipId = `${chartId}-clip-${instanceId}`;
  return <section className={`chart-frame interactive-chart ${className}`.trim()} data-chart-id={chartId}>
    <div className="chart-frame-canvas" style={{ maxInlineSize: layout.maxWidth }}>
      <svg className="chart-frame-svg" viewBox={`0 0 ${layout.width} ${layout.height}`}
        preserveAspectRatio="xMidYMid meet" role="img" aria-labelledby={`${titleId} ${descriptionId}`}>
        <title id={titleId}>{title}</title><desc id={descriptionId}>{description}</desc>
        <defs><clipPath id={clipId}><rect x={layout.plot.left} y={layout.plot.top} width={layout.plot.width} height={layout.plot.height} /></clipPath></defs>
        {axes}<g clipPath={`url(#${clipId})`}>{children}</g>{overlay}
      </svg>
    </div>
    {footer}
  </section>;
}
