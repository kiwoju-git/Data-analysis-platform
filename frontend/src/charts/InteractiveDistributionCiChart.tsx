import type { GraphicalConfidenceInterval } from "../api/types/analysisResultsExploration";
import { ChartTooltip } from "./ChartTooltip";
import { paddedNumericRange, scaleChartValue } from "./chartScale";
import { useChartItemInteraction } from "./useChartItemInteraction";

interface IntervalItem {
  id: string;
  label: string;
  interval: GraphicalConfidenceInterval;
  scale: "location" | "spread";
}

const width = 560;
const height = 250;
const plot = { left: 110, right: 24 };

export function InteractiveDistributionCiChart({
  chartId,
  columnName,
  intervals,
}: {
  chartId: string;
  columnName: string;
  intervals: {
    mean: GraphicalConfidenceInterval;
    median: GraphicalConfidenceInterval;
    standard_deviation: GraphicalConfidenceInterval;
  };
}) {
  const items: IntervalItem[] = [
    { id: `${chartId}-mean`, label: "평균", interval: intervals.mean, scale: "location" },
    { id: `${chartId}-median`, label: "중앙값", interval: intervals.median, scale: "location" },
    {
      id: `${chartId}-standard-deviation`,
      label: "표준편차",
      interval: intervals.standard_deviation,
      scale: "spread",
    },
  ];
  const computedItems = items.filter(
    (item) =>
      item.interval.computed &&
      item.interval.estimate !== null &&
      item.interval.lower !== null &&
      item.interval.upper !== null,
  );
  const interaction = useChartItemInteraction(computedItems.map((item) => item.id));
  if (computedItems.length === 0) {
    return <div className="empty-state">신뢰구간을 계산할 수 없습니다.</div>;
  }

  const locationValues = computedItems
    .filter((item) => item.scale === "location")
    .flatMap((item) => [item.interval.lower!, item.interval.upper!]);
  const spreadValues = computedItems
    .filter((item) => item.scale === "spread")
    .flatMap((item) => [item.interval.lower!, item.interval.upper!]);
  const locationRange = paddedNumericRange(locationValues.length > 0 ? locationValues : [0, 1]);
  const spreadRange = paddedNumericRange(spreadValues.length > 0 ? spreadValues : [0, 1]);
  const activeIndex = computedItems.findIndex((item) => item.id === interaction.activeItem?.id);
  const activeItem = activeIndex >= 0 ? computedItems[activeIndex] : null;
  const details = activeItem === null ? [] : intervalDetails(activeItem);

  return (
    <div className="interactive-chart">
      <svg
        aria-labelledby={`${chartId}-title ${chartId}-description`}
        className="chart-svg interactive-chart-svg"
        role="img"
        viewBox={`0 0 ${width} ${height}`}
      >
        <title id={`${chartId}-title`}>{columnName} 신뢰구간</title>
        <desc id={`${chartId}-description`}>
          평균과 중앙값은 원자료 단위 축, 표준편차는 별도 축에 표시됩니다.
        </desc>
        <text className="chart-panel-subtitle" x={plot.left} y="18">위치 모수</text>
        <line className="chart-axis" x1={plot.left} x2={width - plot.right} y1="112" y2="112" />
        <text className="chart-panel-subtitle" x={plot.left} y="152">산포 모수</text>
        <line className="chart-axis" x1={plot.left} x2={width - plot.right} y1="214" y2="214" />
        {computedItems.map((item, index) => {
          const range = item.scale === "location" ? locationRange : spreadRange;
          const y = item.scale === "location" ? 48 + index * 42 : 181;
          const lowerX = scaleChartValue(item.interval.lower!, range, plot.left, width - plot.right);
          const upperX = scaleChartValue(item.interval.upper!, range, plot.left, width - plot.right);
          const estimateX = scaleChartValue(
            item.interval.estimate!,
            range,
            plot.left,
            width - plot.right,
          );
          const selected = interaction.activeItem?.id === item.id;
          return (
            <g
              aria-label={`${item.label} ${formatNumber(item.interval.estimate!)} 신뢰구간 ${formatNumber(item.interval.lower!)}에서 ${formatNumber(item.interval.upper!)}`}
              className={`distribution-ci-item chart-interactive-item${selected ? " chart-item-selected" : ""}`}
              data-selected={selected ? "true" : "false"}
              key={item.id}
              onBlur={() => interaction.clear(item.id)}
              onClick={() => interaction.activate(item.id, estimateX, y, "selection")}
              onFocus={() => interaction.activate(item.id, estimateX, y, "focus")}
              onKeyDown={(event) => interaction.handleKeyDown(event, item.id, estimateX, y)}
              onPointerEnter={(event) => interaction.move(item.id, event)}
              onPointerLeave={() => interaction.clear(item.id)}
              onPointerMove={(event) => interaction.move(item.id, event)}
              ref={(element) => interaction.itemRef(item.id, element)}
              role="img"
              tabIndex={interaction.tabIndexFor(item.id)}
            >
              <text className="chart-row-label" x={plot.left - 12} y={y + 4}>{item.label}</text>
              <line className="distribution-ci-line" x1={lowerX} x2={upperX} y1={y} y2={y} />
              <line className="distribution-ci-cap" x1={lowerX} x2={lowerX} y1={y - 7} y2={y + 7} />
              <line className="distribution-ci-cap" x1={upperX} x2={upperX} y1={y - 7} y2={y + 7} />
              <circle className="distribution-ci-estimate" cx={estimateX} cy={y} r="4" />
            </g>
          );
        })}
        <text className="chart-axis-label" x={plot.left} y="130">{formatNumber(locationRange.min)}</text>
        <text className="chart-axis-label chart-axis-label-end" x={width - plot.right} y="130">{formatNumber(locationRange.max)}</text>
        <text className="chart-axis-label" x={plot.left} y="233">{formatNumber(spreadRange.min)}</text>
        <text className="chart-axis-label chart-axis-label-end" x={width - plot.right} y="233">{formatNumber(spreadRange.max)}</text>
      </svg>
      {interaction.activeItem !== null && activeItem !== null ? (
        <ChartTooltip
          details={details}
          left={interaction.activeItem.left}
          title={activeItem.label}
          top={interaction.activeItem.top}
        />
      ) : null}
      <div className="chart-selected-detail" aria-live="polite">
        {activeItem === null ? (
          <span>Tab과 방향키로 구간을 확인할 수 있습니다.</span>
        ) : (
          <>
            <strong>{activeItem.label}</strong>
            {details.map((detail) => <span key={detail.label}>{detail.label}: {detail.value}</span>)}
          </>
        )}
      </div>
    </div>
  );
}

function intervalDetails(item: IntervalItem) {
  return [
    { label: "추정값", value: formatNumber(item.interval.estimate!) },
    { label: "하한", value: formatNumber(item.interval.lower!) },
    { label: "상한", value: formatNumber(item.interval.upper!) },
    { label: "신뢰수준", value: `${formatNumber(item.interval.confidence_level * 100)}%` },
    { label: "방법", value: item.interval.method },
  ];
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("ko-KR", { maximumSignificantDigits: 7 }).format(value);
}
