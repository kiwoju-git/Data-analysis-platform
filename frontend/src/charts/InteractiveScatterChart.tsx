import { useId } from "react";

import { ChartItemFeedback } from "./ChartItemFeedback";
import { scaleChartValue, type NumericRange } from "./chartScale";
import { useChartPointInteraction } from "./useChartPointInteraction";

export interface InteractiveScatterPoint {
  ariaLabel: string;
  className: string;
  details: Array<{ label: string; value: string }>;
  id: string;
  title: string;
  warning?: boolean;
  x: number;
  y: number;
}

export interface ScatterReferenceLine {
  className?: string;
  label: string;
  x1: number;
  x2: number;
  y1: number;
  y2: number;
}

interface InteractiveScatterChartProps {
  annotations: string[];
  chartId: string;
  compact?: boolean;
  connectPoints?: "line" | "step";
  description: string;
  emptyLabel: string;
  formatValue: (value: number) => string;
  points: InteractiveScatterPoint[];
  referenceLines?: ScatterReferenceLine[];
  square?: boolean;
  title: string;
  xLabel: string;
  xRange: NumericRange;
  yLabel: string;
  yRange: NumericRange;
  selectedPointId?: string | null;
  onPointSelect?: (pointId: string) => void;
  onPointActivate?: (pointId: string) => void;
  onSelectionClear?: () => void;
  sourceKey?: string;
}

const margins = { left: 54, right: 18, top: 22, bottom: 50 };

export function InteractiveScatterChart({
  annotations,
  chartId,
  compact = false,
  connectPoints,
  description,
  emptyLabel,
  formatValue,
  points,
  referenceLines = [],
  square = false,
  title,
  xLabel,
  xRange,
  yLabel,
  yRange,
  selectedPointId,
  onPointSelect,
  onPointActivate,
  onSelectionClear,
  sourceKey,
}: InteractiveScatterChartProps) {
  const instanceId = useId();
  const interaction = useChartPointInteraction(points.map((point) => point.id), {
    sourceKey, selectedId: selectedPointId, onSelect: onPointSelect,
    onActivate: onPointActivate, onClear: onSelectionClear,
  });
  const width = square || compact ? 360 : 440;
  const height = square ? 360 : compact ? 210 : 280;
  const plotWidth = width - margins.left - margins.right;
  const plotHeight = height - margins.top - margins.bottom;
  const x = (value: number) =>
    scaleChartValue(value, xRange, margins.left, margins.left + plotWidth);
  const y = (value: number) =>
    scaleChartValue(value, yRange, margins.top + plotHeight, margins.top);
  const titleId = `${chartId}-title-${instanceId}`;
  const descriptionId = `${chartId}-description-${instanceId}`;
  const connectedPath = connectPoints === undefined ? null : pointPath(points, x, y, connectPoints);

  if (points.length === 0) {
    return <div className="empty-state">{emptyLabel}</div>;
  }

  return (
    <div
      className={square ? "interactive-chart interactive-chart-square" : "interactive-chart"}
      onKeyDown={(event) => interaction.handleKeyDown(event)}
    >
      <svg
        aria-labelledby={`${titleId} ${descriptionId}`}
        className="chart-svg chart-svg-wide interactive-chart-svg"
        role="img"
        viewBox={`0 0 ${width} ${height}`}
      >
        <title id={titleId}>{title}</title>
        <desc id={descriptionId}>{description}</desc>
        <line className="chart-axis" x1={margins.left} x2={margins.left} y1={margins.top} y2={margins.top + plotHeight} />
        <line className="chart-axis" x1={margins.left} x2={margins.left + plotWidth} y1={margins.top + plotHeight} y2={margins.top + plotHeight} />
        {referenceLines.map((line) => (
          <g key={line.label}>
            <line
              className={`reference-line ${line.className ?? ""}`.trim()}
              x1={x(line.x1)}
              x2={x(line.x2)}
              y1={y(line.y1)}
              y2={y(line.y2)}
            />
            <title>{line.label}</title>
          </g>
        ))}
        {connectedPath === null ? null : <path className="interactive-data-line" d={connectedPath} />}
        {points.map((point) => {
          const cx = x(point.x);
          const cy = y(point.y);
          const selected =
            interaction.pinnedId === point.id;
          return (
            <g key={point.id}>
              {point.warning ? (
                <circle className="chart-warning-ring" cx={cx} cy={cy} r="6" />
              ) : null}
              <circle
                aria-label={point.ariaLabel}
                className={`${point.className} ${interaction.stateClass(point.id)}`}
                cx={cx}
                cy={cy}
                data-selected={selected ? "true" : "false"}
                onBlur={() => interaction.clearFocus(point.id)}
                onClick={() => {
                  interaction.activate(point.id, cx, cy, "selection");
                }}
                onFocus={() => interaction.activate(point.id, cx, cy, "focus")}
                onKeyDown={(event) => interaction.handleKeyDown(event, point.id, cx, cy)}
                onPointerEnter={(event) => interaction.move(point.id, event)}
                onPointerLeave={() => interaction.clearHover(point.id)}
                onPointerMove={(event) => interaction.move(point.id, event)}
                r="3.5"
                role="img"
                aria-describedby={interaction.describedBy(point.id)}
                tabIndex={interaction.tabIndexFor(point.id)}
                ref={(element) => interaction.itemRef(point.id, element)}
              >
                <title>{point.ariaLabel}</title>
              </circle>
            </g>
          );
        })}
        <text className="chart-axis-label" x={margins.left} y={height - 12}>{formatValue(xRange.min)}</text>
        <text className="chart-axis-label chart-axis-label-end" x={margins.left + plotWidth} y={height - 12}>{formatValue(xRange.max)}</text>
        <text className="chart-axis-label" x={margins.left - 8} y={margins.top + 8}>{formatValue(yRange.max)}</text>
        <text className="chart-axis-title" x={margins.left + plotWidth / 2} y={height - 28}>{xLabel}</text>
        <text className="chart-axis-title chart-axis-title-y" transform={`translate(16 ${margins.top + plotHeight / 2}) rotate(-90)`}>{yLabel}</text>
      </svg>
      <div className="chart-annotations" aria-label={`${title} 요약`}>
        {annotations.map((annotation) => <span key={annotation}>{annotation}</span>)}
      </div>
      <ChartItemFeedback interaction={interaction} items={points} />
    </div>
  );
}

function pointPath(
  points: InteractiveScatterPoint[],
  x: (value: number) => number,
  y: (value: number) => number,
  mode: "line" | "step",
): string {
  if (points.length === 0) return "";
  const first = points[0];
  const parts = [`M ${x(first.x)} ${y(first.y)}`];
  let previousY = y(first.y);
  for (const point of points.slice(1)) {
    const nextX = x(point.x);
    const nextY = y(point.y);
    if (mode === "step") parts.push(`L ${nextX} ${previousY}`);
    parts.push(`L ${nextX} ${nextY}`);
    previousY = nextY;
  }
  return parts.join(" ");
}
