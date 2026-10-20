import { Maximize2, Minimize2 } from "lucide-react";
import { useState, type ReactNode } from "react";
import type { ChartLayout } from "../charts/chartLayout";
import { STANDARD_CHART_LAYOUT } from "../charts/chartLayout";
import { t } from "../i18n/translate";
import type { DoePlotStatus } from "./doePlotStatus";
import "./doeCompactPlots.css";

export const DOE_COMPACT_LAYOUT: ChartLayout = {
  width: 280, height: 210, maxWidth: 340,
  plot: { left: 58, top: 20, width: 206, height: 136 },
};

export function DoeCompactPlotGrid({ children }: { children: ReactNode }) {
  return <div className="doe-compact-scope"><div className="doe-compact-grid">{children}</div></div>;
}

export function DoeCompactPlotCard({ title, status, meanLabel, children }: {
  title: string; status: DoePlotStatus; meanLabel: string;
  children: (layout: ChartLayout) => ReactNode;
}) {
  const [expanded, setExpanded] = useState(false);
  const ExpandIcon = expanded ? Minimize2 : Maximize2;
  return <article className="doe-compact-plot" data-term-status={status} data-expanded={expanded}>
    <div className="doe-compact-heading">
      <h5>{title}</h5>
      <button type="button" className="icon-button" aria-expanded={expanded}
        aria-label={t(expanded ? "doe.plots.collapse" : "doe.plots.expand")}
        title={t(expanded ? "doe.plots.collapse" : "doe.plots.expand")}
        onClick={() => setExpanded((value) => !value)}><ExpandIcon aria-hidden="true" size={16} /></button>
    </div>
    <p className="doe-plot-status"><span>{t(`doe.plots.status.${status}`)}</span> · {meanLabel}</p>
    {children(expanded ? STANDARD_CHART_LAYOUT : DOE_COMPACT_LAYOUT)}
  </article>;
}
