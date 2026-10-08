import { scaleChartValue, type NumericRange } from "./chartScale";
import { axisTitle, numericChartTicks, wrapAxisTitle, type ChartLayout } from "./chartLayout";

export interface AxisSpec {
  label: string;
  unit?: string | null;
  range: NumericRange;
  ticks?: ReadonlyArray<{ value: number; label: string }>;
}

export function ChartAxes({ x, y, layout, grid = true }: {
  x: AxisSpec; y: AxisSpec; layout: ChartLayout; grid?: boolean;
}) {
  const { plot } = layout;
  const xAt = (value: number) => scaleChartValue(value, x.range, plot.left, plot.left + plot.width);
  const yAt = (value: number) => scaleChartValue(value, y.range, plot.top + plot.height, plot.top);
  const xTitle = axisTitle(x.label, x.unit);
  const yTitle = axisTitle(y.label, y.unit);
  const xTicks = (x.ticks ?? numericChartTicks(x.range)).filter((tick) => Number.isFinite(tick.value) && tick.value >= x.range.min && tick.value <= x.range.max);
  const yTicks = (y.ticks ?? numericChartTicks(y.range)).filter((tick) => Number.isFinite(tick.value) && tick.value >= y.range.min && tick.value <= y.range.max);
  return <g className="chart-axes">
    {xTicks.map((tick, index) => <g key={`${tick.value}-${index}`}>
      {grid && <line className="chart-grid-line" x1={xAt(tick.value)} x2={xAt(tick.value)} y1={plot.top} y2={plot.top + plot.height} />}
      <text className="chart-tick-label" textAnchor="middle" x={xAt(tick.value)} y={plot.top + plot.height + 17}>{tick.label}</text>
    </g>)}
    {yTicks.map((tick, index) => <g key={`${tick.value}-${index}`}>
      {grid && <line className="chart-grid-line" x1={plot.left} x2={plot.left + plot.width} y1={yAt(tick.value)} y2={yAt(tick.value)} />}
      <text className="chart-tick-label" textAnchor="end" x={plot.left - 8} y={yAt(tick.value) + 3}>{tick.label}</text>
    </g>)}
    <line className="chart-axis" x1={plot.left} x2={plot.left} y1={plot.top} y2={plot.top + plot.height} />
    <line className="chart-axis" x1={plot.left} x2={plot.left + plot.width} y1={plot.top + plot.height} y2={plot.top + plot.height} />
    <text className="chart-visible-axis-title" textAnchor="middle" x={plot.left + plot.width / 2} y={plot.top + plot.height + 39}>
      <title>{xTitle}</title>{wrapAxisTitle(xTitle, 48).map((line, index) => <tspan key={index} x={plot.left + plot.width / 2} dy={index === 0 ? 0 : 14}>{line}</tspan>)}
    </text>
    <text className="chart-visible-axis-title" textAnchor="middle" transform={`translate(16 ${plot.top + plot.height / 2}) rotate(-90)`}>
      <title>{yTitle}</title>{wrapAxisTitle(yTitle, Math.floor(plot.height / 6)).map((line, index) => <tspan key={index} x={0} dy={index === 0 ? 0 : 14}>{line}</tspan>)}
    </text>
  </g>;
}
