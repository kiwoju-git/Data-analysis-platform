import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { t } from "../i18n/translate";
import { ChartAxes } from "./ChartAxes";
import { ChartFrame } from "./ChartFrame";
import { ChartItemFeedback, type ChartDetailItem } from "./ChartItemFeedback";
import { paddedNumericRange, scaleChartValue } from "./chartScale";
import { useChartItemInteraction } from "./useChartItemInteraction";

export interface HorizontalBarItem extends ChartDetailItem { value: number; label: string; className?: string }

export function InteractiveHorizontalBarChart({ chartId, title, description, items, xLabel, yLabel, sourceKey, pageSize = 12 }: {
  chartId: string; title: string; description: string; items: readonly HorizontalBarItem[];
  xLabel: string; yLabel: string; sourceKey?: string; pageSize?: number;
}) {
  const valid = items.filter((item) => Number.isFinite(item.value));
  const size = Math.max(1, Math.min(12, Math.floor(pageSize)));
  const [page, setPage] = useState(0);
  const lastPage = Math.max(0, Math.ceil(valid.length / size) - 1);
  const visiblePage = Math.min(page, lastPage);
  useEffect(() => setPage((current) => Math.min(current, lastPage)), [lastPage]);
  const visible = valid.slice(visiblePage * size, (visiblePage + 1) * size);
  const interaction = useChartItemInteraction(visible.map((item) => item.id), { sourceKey });
  const range = paddedNumericRange([0, ...valid.map((item) => item.value)]);
  const layout = { width: 480, height: 88 + visible.length * 26, maxWidth: 640,
    plot: { left: 160, top: 18, width: 296, height: Math.max(26, visible.length * 26) } };
  const x = (value: number) => scaleChartValue(value, range, layout.plot.left, layout.plot.left + layout.plot.width);
  return <ChartFrame chartId={chartId} title={title} description={description} layout={layout}
    axes={<><text className="chart-visible-axis-title" x={layout.plot.left - 8} y={12} textAnchor="end">{yLabel}</text><ChartAxes layout={layout} x={{ label: xLabel, range }} y={{ label: "",
      range: { min: -0.5, max: Math.max(0.5, visible.length - 0.5) },
      ticks: visible.map((item, index) => ({ value: visible.length - index - 1, label: item.label.length > 21 ? `${item.label.slice(0, 18)}...` : item.label })) }} /></>}
    footer={<>
      {valid.length !== items.length && <p>{t("charts.invalidData", { count: items.length - valid.length })}</p>}
      {valid.length > size && <div className="chart-page-controls">
        <button type="button" className="icon-button" title={t("charts.previous")} aria-label={t("charts.previous")} disabled={visiblePage === 0} onClick={() => setPage(visiblePage - 1)}><ChevronLeft size={16} /></button>
        <span>{t("charts.pageRange", { start: visiblePage * size + 1, end: Math.min(valid.length, (visiblePage + 1) * size), total: valid.length })}</span>
        <button type="button" className="icon-button" title={t("charts.next")} aria-label={t("charts.next")} disabled={visiblePage === lastPage} onClick={() => setPage(visiblePage + 1)}><ChevronRight size={16} /></button>
      </div>}
      <ChartItemFeedback interaction={interaction} items={visible} />
    </>}>
    <line className="reference-line" x1={x(0)} x2={x(0)} y1={layout.plot.top} y2={layout.plot.top + layout.plot.height} />
    {visible.map((item, index) => <rect key={item.id}
      className={`${item.className ?? "histogram-bar"} ${interaction.stateClass(item.id)}`}
      x={Math.min(x(0), x(item.value))} y={layout.plot.top + index * 26 + 5}
      width={Math.max(1, Math.abs(x(item.value) - x(0)))} height={16}
      role="img" aria-label={`${item.label}: ${item.value}`} aria-describedby={interaction.describedBy(item.id)}
      tabIndex={interaction.tabIndexFor(item.id)} ref={(element) => interaction.itemRef(item.id, element)}
      onFocus={() => interaction.activateItem(item.id, "focus")} onBlur={() => interaction.clearFocus(item.id)}
      onPointerEnter={(event) => interaction.move(item.id, event)} onPointerMove={(event) => interaction.move(item.id, event)} onPointerLeave={() => interaction.clearHover(item.id)}
      onClick={() => interaction.pin(item.id)} onKeyDown={(event) => interaction.handleKeyDown(event, item.id)}>
      <title>{`${item.label}: ${item.value}`}</title>
    </rect>)}
  </ChartFrame>;
}
