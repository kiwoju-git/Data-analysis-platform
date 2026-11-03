import type { KeyboardEvent, PointerEvent, ReactNode } from "react";
import { ChartAxes } from "./ChartAxes";
import { ChartFrame } from "./ChartFrame";
import { ChartItemFeedback, type ChartDetailItem } from "./ChartItemFeedback";
import { STANDARD_CHART_LAYOUT } from "./chartLayout";
import { scaleChartValue, type NumericRange } from "./chartScale";
import { useChartItemInteraction } from "./useChartItemInteraction";

export interface SummaryBar extends ChartDetailItem {
  category: number;
  series: number;
  value: number;
  className: string;
}
export interface SummaryBox extends ChartDetailItem {
  category: number;
  q1: number; median: number; q3: number;
  lowerWhisker: number; upperWhisker: number; mean: number;
  className: string;
}
export interface SummaryDot extends ChartDetailItem {
  x: number; value: number; className: string; outlier?: boolean;
}
interface SummaryChartProps {
  chartId: string; sourceKey: string; title: string; description: string;
  xLabel: string; yLabel: string; yUnit?: string | null;
  categories: readonly { value: number; label: string }[];
  yRange: NumericRange;
  footer?: ReactNode;
}

function itemProps(interaction: ReturnType<typeof useChartItemInteraction>, item: ChartDetailItem) {
  return {
    role: "img", "aria-label": `${item.title}; ${item.details.map((detail) => `${detail.label}: ${detail.value}`).join("; ")}`,
    "aria-describedby": interaction.describedBy(item.id), "data-item-id": item.id,
    "data-selected": interaction.pinnedId === item.id ? "true" : "false",
    tabIndex: interaction.tabIndexFor(item.id),
    ref: (element: SVGElement | null) => interaction.itemRef(item.id, element),
    onFocus: () => interaction.activateItem(item.id, "focus"), onBlur: () => interaction.clearFocus(item.id),
    onPointerEnter: (event: PointerEvent<SVGElement>) => interaction.move(item.id, event),
    onPointerMove: (event: PointerEvent<SVGElement>) => interaction.move(item.id, event),
    onPointerLeave: () => interaction.clearHover(item.id), onClick: () => interaction.pin(item.id),
    onKeyDown: (event: KeyboardEvent<SVGElement>) => interaction.handleKeyDown(event, item.id),
  };
}

export function InteractiveGroupedBarChart({ bars, ...props }: SummaryChartProps & { bars: readonly SummaryBar[] }) {
  const interaction = useChartItemInteraction(bars.map((bar) => bar.id), { sourceKey: props.sourceKey });
  const layout = STANDARD_CHART_LAYOUT;
  const range = { min: -0.5, max: Math.max(0.5, props.categories.length - 0.5) };
  const x = (value: number) => scaleChartValue(value, range, layout.plot.left, layout.plot.left + layout.plot.width);
  const y = (value: number) => scaleChartValue(value, props.yRange, layout.plot.top + layout.plot.height, layout.plot.top);
  const width = layout.plot.width / Math.max(1, props.categories.length) * 0.3;
  return <ChartFrame chartId={props.chartId} title={props.title} description={props.description} layout={layout}
    axes={<ChartAxes layout={layout} x={{ label: props.xLabel, range, ticks: props.categories }} y={{ label: props.yLabel, unit: props.yUnit, range: props.yRange }} />}
    footer={<>{props.footer}<ChartItemFeedback interaction={interaction} items={bars} collapsible /></>}>
    {bars.map((bar) => {
      const left = x(bar.category) + (bar.series === 0 ? -width - 1 : 1);
      const height = Math.abs(y(bar.value) - y(0));
      return <g key={bar.id} data-category={bar.category} data-series={bar.series} data-value={bar.value}>
        <rect className={bar.className} x={left} y={Math.min(y(bar.value), y(0))} width={width} height={height} />
        <rect {...itemProps(interaction, bar)} className={`chart-summary-hit ${interaction.stateClass(bar.id)}`}
          x={left} y={Math.min(y(bar.value), y(0)) - (height === 0 ? 3 : 0)} width={width} height={Math.max(6, height)}><title>{bar.title}</title></rect>
      </g>;
    })}
  </ChartFrame>;
}

export function InteractiveVerticalBoxplotChart({ boxes, dots, ...props }: SummaryChartProps & { boxes: readonly SummaryBox[]; dots: readonly SummaryDot[] }) {
  const items: ChartDetailItem[] = [...boxes, ...dots];
  const interaction = useChartItemInteraction(items.map((item) => item.id), { sourceKey: props.sourceKey });
  const layout = STANDARD_CHART_LAYOUT;
  const range = { min: -0.5, max: Math.max(0.5, props.categories.length - 0.5) };
  const x = (value: number) => scaleChartValue(value, range, layout.plot.left, layout.plot.left + layout.plot.width);
  const y = (value: number) => scaleChartValue(value, props.yRange, layout.plot.top + layout.plot.height, layout.plot.top);
  const width = Math.min(54, layout.plot.width / Math.max(1, boxes.length) * 0.4);
  return <ChartFrame chartId={props.chartId} title={props.title} description={props.description} layout={layout}
    axes={<ChartAxes layout={layout} x={{ label: props.xLabel, range, ticks: props.categories }} y={{ label: props.yLabel, unit: props.yUnit, range: props.yRange }} />}
    footer={<>{props.footer}<ChartItemFeedback interaction={interaction} items={items} collapsible /></>}>
    {boxes.map((box) => <g key={box.id} className={`chart-summary-box ${box.className}`} data-box-id={box.id}
      data-q1={box.q1} data-median={box.median} data-q3={box.q3} data-mean={box.mean}
      data-lower-whisker={box.lowerWhisker} data-upper-whisker={box.upperWhisker}>
      <line x1={x(box.category)} x2={x(box.category)} y1={y(box.lowerWhisker)} y2={y(box.upperWhisker)} />
      {[box.lowerWhisker, box.upperWhisker].map((value, index) => <line key={index} x1={x(box.category) - width / 3} x2={x(box.category) + width / 3} y1={y(value)} y2={y(value)} />)}
      <rect x={x(box.category) - width / 2} y={y(box.q3)} width={width} height={Math.max(0, y(box.q1) - y(box.q3))} />
      <line className="chart-box-median" x1={x(box.category) - width / 2} x2={x(box.category) + width / 2} y1={y(box.median)} y2={y(box.median)} />
      <path className="chart-box-mean" d={`M ${x(box.category)} ${y(box.mean) - 5} l 5 5 l -5 5 l -5 -5 Z`} />
      <rect {...itemProps(interaction, box)} className={`chart-summary-hit ${interaction.stateClass(box.id)}`}
        x={x(box.category) - width / 2} y={y(box.q3) - (box.q1 === box.q3 ? 3 : 0)} width={width} height={Math.max(6, y(box.q1) - y(box.q3))}><title>{box.title}</title></rect>
    </g>)}
    {dots.map((dot) => <circle key={dot.id} {...itemProps(interaction, dot)}
      className={`chart-summary-dot ${dot.className} ${interaction.stateClass(dot.id)}`} cx={x(dot.x)} cy={y(dot.value)} r={dot.outlier ? 3.5 : 2.5}
      data-value={dot.value} data-outlier={dot.outlier ? "true" : "false"}><title>{dot.title}</title></circle>)}
  </ChartFrame>;
}
