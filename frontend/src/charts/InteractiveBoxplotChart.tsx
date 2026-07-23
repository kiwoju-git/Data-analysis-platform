import { ChartTooltip } from "./ChartTooltip";
import { layoutBoxplotMarkers } from "./boxplotMarkerLayout";
import { paddedNumericRange, scaleChartValue } from "./chartScale";
import { useChartItemInteraction } from "./useChartItemInteraction";

interface BoxplotSummary {
  lower_fence: number | null;
  lower_whisker: number | null;
  median: number | null;
  outlier_count: number;
  q1: number | null;
  q3: number | null;
  upper_fence: number | null;
  upper_whisker: number | null;
}

interface InteractiveBoxplotChartProps {
  boxplot: BoxplotSummary;
  chartId: string;
  columnName: string;
}

const width = 420;
const height = 230;
const plot = { left: 46, right: 18, top: 18, bottom: 70 };

export function InteractiveBoxplotChart({
  boxplot,
  chartId,
  columnName,
}: InteractiveBoxplotChartProps) {
  const numericEntries = [
    ["lower-fence", "Lower fence", boxplot.lower_fence],
    ["lower-whisker", "Lower whisker", boxplot.lower_whisker],
    ["q1", "Q1", boxplot.q1],
    ["median", "Median", boxplot.median],
    ["q3", "Q3", boxplot.q3],
    ["upper-whisker", "Upper whisker", boxplot.upper_whisker],
    ["upper-fence", "Upper fence", boxplot.upper_fence],
  ] as const;
  const computed = !numericEntries.some((entry) => entry[2] === null);
  const entries = computed
    ? numericEntries.map(([key, label, value]) => ({
        id: `${chartId}-${key}`,
        key,
        label,
        value: value as number,
      }))
    : [];
  const outlierEntry = {
    id: `${chartId}-outliers`,
    key: "outliers",
    label: "Outlier count",
    value: boxplot.outlier_count,
  };
  const ids = computed ? [...entries.map((entry) => entry.id), outlierEntry.id] : [];
  const interaction = useChartItemInteraction(ids);
  if (!computed) {
    return <div className="empty-state">숫자 데이터 없음</div>;
  }

  const active =
    [...entries, outlierEntry].find((entry) => entry.id === interaction.activeItem?.id) ?? null;
  const range = paddedNumericRange(entries.map((entry) => entry.value));
  const plotWidth = width - plot.left - plot.right;
  const plotHeight = height - plot.top - plot.bottom;
  const y = plot.top + plotHeight / 2;
  const axisY = plot.top + plotHeight;
  const x = (value: number) => scaleChartValue(value, range, plot.left, plot.left + plotWidth);
  const q1 = boxplot.q1 as number;
  const q3 = boxplot.q3 as number;
  const median = boxplot.median as number;
  const lower = boxplot.lower_whisker as number;
  const upper = boxplot.upper_whisker as number;
  const markerEntries = [
    { key: "lower-whisker", label: "Lower whisker", value: lower, x: x(lower) },
    { key: "q1", label: "Q1", value: q1, x: x(q1) },
    { key: "median", label: "Median", value: median, x: x(median) },
    { key: "q3", label: "Q3", value: q3, x: x(q3) },
    { key: "upper-whisker", label: "Upper whisker", value: upper, x: x(upper) },
  ];
  const markerLabels = layoutBoxplotMarkers(
    markerEntries,
    52,
    plot.left,
    plot.left + plotWidth,
  );
  const details =
    active === null
      ? []
      : [
          {
            label: active.label,
            value:
              active.id === outlierEntry.id
                ? active.value.toLocaleString()
                : formatNumber(active.value),
          },
          { label: "IQR", value: formatNumber(q3 - q1) },
        ];
  const summaryDescription = markerEntries
    .map((marker) => `${marker.label} ${formatNumber(marker.value)}`)
    .join(", ");

  return (
    <div className="interactive-chart">
      <svg
        aria-labelledby={`${chartId}-title ${chartId}-description`}
        className="chart-svg interactive-chart-svg"
        role="img"
        viewBox={`0 0 ${width} ${height}`}
      >
        <title id={`${chartId}-title`}>{`${columnName} 박스플롯`}</title>
        <desc id={`${chartId}-description`}>
          {summaryDescription}. 개별 outlier 값 없이 quartile, whisker, fence와 outlier count
          집계만 표시합니다.
        </desc>
        <line
          className="chart-axis"
          x1={plot.left}
          x2={plot.left + plotWidth}
          y1={axisY}
          y2={axisY}
        />
        <line
          className="boxplot-fence"
          x1={x(boxplot.lower_fence as number)}
          x2={x(boxplot.lower_fence as number)}
          y1={y - 30}
          y2={y + 30}
        />
        <line
          className="boxplot-fence"
          x1={x(boxplot.upper_fence as number)}
          x2={x(boxplot.upper_fence as number)}
          y1={y - 30}
          y2={y + 30}
        />
        <line className="boxplot-line" x1={x(lower)} x2={x(upper)} y1={y} y2={y} />
        <line className="boxplot-line" x1={x(lower)} x2={x(lower)} y1={y - 16} y2={y + 16} />
        <line className="boxplot-line" x1={x(upper)} x2={x(upper)} y1={y - 16} y2={y + 16} />
        <rect
          className="boxplot-box"
          height={44}
          width={Math.max(1, x(q3) - x(q1))}
          x={x(q1)}
          y={y - 22}
        />
        <line
          className="boxplot-median"
          x1={x(median)}
          x2={x(median)}
          y1={y - 22}
          y2={y + 22}
        />
        {markerEntries.map((marker) => (
          <line
            className="boxplot-value-tick"
            data-marker={marker.key}
            key={marker.key}
            x1={marker.x}
            x2={marker.x}
            y1={axisY}
            y2={axisY + 8}
          />
        ))}
        {markerLabels.map((marker) => (
          <g key={marker.keys.join("-")}>
            {Math.abs(marker.x - marker.markerX) > 0.5 ? (
              <line
                className="boxplot-value-guide"
                x1={marker.markerX}
                x2={marker.x}
                y1={axisY + 8}
                y2={axisY + 15}
              />
            ) : null}
            <text
              aria-label={`${marker.label}: ${formatNumber(marker.value)}`}
              className="boxplot-value-label"
              data-marker-label={marker.keys.join(",")}
              textAnchor={marker.anchor}
              x={marker.x}
              y={axisY + 30}
            >
              {formatNumber(marker.value)}
            </text>
          </g>
        ))}
        {[...entries, outlierEntry].map((entry) => {
          const itemX = entry.id === outlierEntry.id ? plot.left + 42 : x(entry.value);
          const itemY = entry.id === outlierEntry.id ? plot.top + 14 : y;
          const selected = interaction.activeItem?.id === entry.id;
          return (
            <rect
              aria-label={`${columnName} ${entry.label}: ${
                entry.id === outlierEntry.id ? entry.value : formatNumber(entry.value)
              }`}
              className={`chart-hit-target${selected ? " chart-hit-target-selected" : ""}`}
              data-selected={selected ? "true" : "false"}
              height={entry.id === outlierEntry.id ? 24 : 64}
              key={entry.id}
              onBlur={() => interaction.clear(entry.id)}
              onClick={() => interaction.activate(entry.id, itemX, itemY, "selection")}
              onFocus={() => interaction.activate(entry.id, itemX, itemY, "focus")}
              onKeyDown={(event) => interaction.handleKeyDown(event, entry.id, itemX, itemY)}
              onPointerEnter={(event) => interaction.move(entry.id, event)}
              onPointerLeave={() => interaction.clear(entry.id)}
              onPointerMove={(event) => interaction.move(entry.id, event)}
              ref={(element) => interaction.itemRef(entry.id, element)}
              role="img"
              tabIndex={interaction.tabIndexFor(entry.id)}
              width={entry.id === outlierEntry.id ? 84 : 18}
              x={itemX - (entry.id === outlierEntry.id ? 42 : 9)}
              y={itemY - (entry.id === outlierEntry.id ? 12 : 32)}
            >
              <title>{entry.label}</title>
            </rect>
          );
        })}
        {boxplot.outlier_count > 0 ? (
          <text className="chart-note" x={plot.left} y={plot.top + 20}>
            outliers {boxplot.outlier_count}
          </text>
        ) : null}
      </svg>
      {interaction.activeItem !== null && active !== null ? (
        <ChartTooltip
          details={details}
          left={interaction.activeItem.left}
          title={active.label}
          top={interaction.activeItem.top}
        />
      ) : null}
      <div className="chart-selected-detail" aria-live="polite">
        {active === null ? (
          <span>Tab과 방향키로 quartile, whisker, fence와 outlier count를 확인할 수 있습니다.</span>
        ) : (
          <>
            <strong>{active.label}</strong>
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

function formatNumber(value: number): string {
  return new Intl.NumberFormat("ko-KR", { maximumSignificantDigits: 6 }).format(value);
}
