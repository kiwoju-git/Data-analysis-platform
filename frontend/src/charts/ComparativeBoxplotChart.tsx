import type { GraphicalSummaryColumn } from "../api";
import { ChartTooltip } from "./ChartTooltip";
import { paddedNumericRange, scaleChartValue } from "./chartScale";
import { useChartItemInteraction } from "./useChartItemInteraction";

interface ComparativeBoxplotChartProps {
  chartId: string;
  columns: GraphicalSummaryColumn[];
}

const width = 700;
const margin = { left: 145, right: 28, top: 28, bottom: 42 };

export function ComparativeBoxplotChart({
  chartId,
  columns,
}: ComparativeBoxplotChartProps) {
  const computed = columns.filter(
    (column) =>
      column.boxplot.lower_whisker !== null &&
      column.boxplot.q1 !== null &&
      column.boxplot.median !== null &&
      column.boxplot.q3 !== null &&
      column.boxplot.upper_whisker !== null,
  );
  const ids = computed.map((column) => `${chartId}-${column.column_id}`);
  const interaction = useChartItemInteraction(ids);
  if (computed.length === 0) {
    return <div className="empty-state">표시할 Box Plot이 없습니다.</div>;
  }
  const values = computed.flatMap((column) => [
    column.boxplot.lower_fence ?? column.boxplot.lower_whisker ?? 0,
    column.boxplot.upper_fence ?? column.boxplot.upper_whisker ?? 0,
  ]);
  const range = paddedNumericRange(values);
  const rowHeight = 64;
  const height = margin.top + margin.bottom + computed.length * rowHeight;
  const plotWidth = width - margin.left - margin.right;
  const x = (value: number) =>
    scaleChartValue(value, range, margin.left, margin.left + plotWidth);
  const active =
    computed.find(
      (column) => `${chartId}-${column.column_id}` === interaction.activeItem?.id,
    ) ?? null;
  const details =
    active === null
      ? []
      : [
          { label: "Lower whisker", value: formatNumber(active.boxplot.lower_whisker) },
          { label: "Q1", value: formatNumber(active.boxplot.q1) },
          { label: "Median", value: formatNumber(active.boxplot.median) },
          { label: "Q3", value: formatNumber(active.boxplot.q3) },
          { label: "Upper whisker", value: formatNumber(active.boxplot.upper_whisker) },
          { label: "Outlier count", value: active.boxplot.outlier_count.toLocaleString() },
          { label: "N", value: active.n_used.toLocaleString() },
        ];

  return (
    <div className="interactive-chart">
      <svg
        aria-labelledby={`${chartId}-title ${chartId}-description`}
        className="chart-svg chart-svg-wide interactive-chart-svg"
        role="img"
        viewBox={`0 0 ${width} ${height}`}
      >
        <title id={`${chartId}-title`}>변수 비교 Box Plot</title>
        <desc id={`${chartId}-description`}>
          각 box는 공통 원자료 축을 사용합니다. 방향키로 box를 이동하고 Enter 또는 Space로
          상세 값을 고정할 수 있습니다.
        </desc>
        <line
          className="chart-axis"
          x1={margin.left}
          x2={margin.left + plotWidth}
          y1={height - margin.bottom}
          y2={height - margin.bottom}
        />
        {computed.map((column, index) => {
          const boxplot = column.boxplot;
          const lower = boxplot.lower_whisker as number;
          const q1 = boxplot.q1 as number;
          const median = boxplot.median as number;
          const q3 = boxplot.q3 as number;
          const upper = boxplot.upper_whisker as number;
          const y = margin.top + rowHeight * index + rowHeight / 2;
          const id = `${chartId}-${column.column_id}`;
          const selected = interaction.activeItem?.id === id;
          return (
            <g key={id}>
              <text className="chart-axis-label" textAnchor="end" x={margin.left - 12} y={y + 4}>
                {column.display_name}
              </text>
              <line className="boxplot-line" x1={x(lower)} x2={x(upper)} y1={y} y2={y} />
              <line className="boxplot-line" x1={x(lower)} x2={x(lower)} y1={y - 12} y2={y + 12} />
              <line className="boxplot-line" x1={x(upper)} x2={x(upper)} y1={y - 12} y2={y + 12} />
              <rect
                className="boxplot-box"
                height="34"
                width={Math.max(1, x(q3) - x(q1))}
                x={x(q1)}
                y={y - 17}
              />
              <line className="boxplot-median" x1={x(median)} x2={x(median)} y1={y - 17} y2={y + 17} />
              <rect
                aria-label={`${column.display_name}, median ${formatNumber(
                  median,
                )}, Q1 ${formatNumber(q1)}, Q3 ${formatNumber(q3)}`}
                className={`chart-hit-target${selected ? " chart-hit-target-selected" : ""}`}
                height="50"
                onBlur={() => interaction.clear(id)}
                onClick={() => interaction.activate(id, x(median), y, "selection")}
                onFocus={() => interaction.activate(id, x(median), y, "focus")}
                onKeyDown={(event) => interaction.handleKeyDown(event, id, x(median), y)}
                onPointerEnter={(event) => interaction.move(id, event)}
                onPointerLeave={() => interaction.clear(id)}
                onPointerMove={(event) => interaction.move(id, event)}
                ref={(element) => interaction.itemRef(id, element)}
                role="img"
                tabIndex={interaction.tabIndexFor(id)}
                width={plotWidth}
                x={margin.left}
                y={y - 25}
              />
            </g>
          );
        })}
        <text className="chart-axis-label" x={margin.left} y={height - 12}>
          {formatNumber(range.min)}
        </text>
        <text className="chart-axis-label chart-axis-label-end" x={margin.left + plotWidth} y={height - 12}>
          {formatNumber(range.max)}
        </text>
      </svg>
      {interaction.activeItem !== null && active !== null ? (
        <ChartTooltip
          details={details}
          left={interaction.activeItem.left}
          title={active.display_name}
          top={interaction.activeItem.top}
        />
      ) : null}
      <div className="chart-selected-detail" aria-live="polite">
        {active === null ? (
          <span>Tab과 방향키로 각 변수의 quartile과 whisker를 확인할 수 있습니다.</span>
        ) : (
          <>
            <strong>{active.display_name}</strong>
            {details.map((detail) => (
              <span key={detail.label}>
                {detail.label}: {detail.value}
              </span>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

function formatNumber(value: number | null): string {
  return value === null
    ? "-"
    : new Intl.NumberFormat("ko-KR", { maximumSignificantDigits: 6 }).format(value);
}
