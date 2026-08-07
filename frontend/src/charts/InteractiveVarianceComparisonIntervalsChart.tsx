import type { EqualVarianceMultipleComparisons } from "../api/types/analysisResultsExploration";
import { ChartTooltip } from "./ChartTooltip";
import { paddedNumericRange, scaleChartValue } from "./chartScale";
import { useChartItemInteraction } from "./useChartItemInteraction";

const width = 680;
const rowHeight = 46;
const plot = { left: 140, right: 30, top: 40, bottom: 42 };

export function InteractiveVarianceComparisonIntervalsChart({
  chartId,
  groupName,
  result,
  responseName,
}: {
  chartId: string;
  groupName: string;
  result: EqualVarianceMultipleComparisons;
  responseName: string;
}) {
  const groups = result.groups;
  const ids = groups.map((group) => `${chartId}-group-${group.group_index}`);
  const interaction = useChartItemInteraction(ids);
  if (!result.computed || groups.length === 0) {
    return <div className="empty-state">다중 비교구간을 계산할 수 없습니다.</div>;
  }
  const height = plot.top + plot.bottom + rowHeight * groups.length;
  const range = paddedNumericRange(
    groups.flatMap((group) => [group.comparison_interval.lower, group.comparison_interval.upper]),
  );
  const activeIndex = ids.indexOf(interaction.activeItem?.id ?? "");
  const activeGroup = activeIndex >= 0 ? groups[activeIndex] : null;
  const details = activeGroup === null ? [] : groupDetails(activeGroup, result);
  const plotWidth = width - plot.left - plot.right;

  return (
    <div className="interactive-chart variance-comparison-chart">
      <svg
        aria-labelledby={`${chartId}-title ${chartId}-description`}
        className="chart-svg interactive-chart-svg"
        role="img"
        viewBox={`0 0 ${width} ${height}`}
      >
        <title id={`${chartId}-title`}>등분산 검정: {responseName} 대 {groupName}</title>
        <desc id={`${chartId}-description`}>
          표준편차 다중 비교구간입니다. Tab과 방향키로 그룹을 선택할 수 있습니다.
        </desc>
        <line
          className="chart-axis"
          x1={plot.left}
          x2={plot.left + plotWidth}
          y1={height - plot.bottom}
          y2={height - plot.bottom}
        />
        {groups.map((group, index) => {
          const id = ids[index];
          const y = plot.top + rowHeight * index + rowHeight / 2;
          const lowerX = scaleChartValue(
            group.comparison_interval.lower,
            range,
            plot.left,
            plot.left + plotWidth,
          );
          const upperX = scaleChartValue(
            group.comparison_interval.upper,
            range,
            plot.left,
            plot.left + plotWidth,
          );
          const estimateX = scaleChartValue(
            group.sample_standard_deviation,
            range,
            plot.left,
            plot.left + plotWidth,
          );
          const selected = interaction.activeItem?.id === id;
          return (
            <g
              aria-label={`${group.group_label}, 표준편차 ${formatNumber(group.sample_standard_deviation)}, 구간 ${formatNumber(group.comparison_interval.lower)}에서 ${formatNumber(group.comparison_interval.upper)}`}
              className={`variance-comparison-group chart-interactive-item${selected ? " chart-item-selected" : ""}`}
              data-selected={selected ? "true" : "false"}
              key={id}
              onBlur={() => interaction.clear(id)}
              onClick={() => interaction.activate(id, estimateX, y, "selection")}
              onFocus={() => interaction.activate(id, estimateX, y, "focus")}
              onKeyDown={(event) => interaction.handleKeyDown(event, id, estimateX, y)}
              onPointerEnter={(event) => interaction.move(id, event)}
              onPointerLeave={() => interaction.clear(id)}
              onPointerMove={(event) => interaction.move(id, event)}
              ref={(element) => interaction.itemRef(id, element)}
              role="img"
              tabIndex={interaction.tabIndexFor(id)}
            >
              <text className="chart-row-label" x={plot.left - 12} y={y + 4}>{group.group_label}</text>
              <line className="variance-interval-line" x1={lowerX} x2={upperX} y1={y} y2={y} />
              <line className="variance-interval-cap" x1={lowerX} x2={lowerX} y1={y - 8} y2={y + 8} />
              <line className="variance-interval-cap" x1={upperX} x2={upperX} y1={y - 8} y2={y + 8} />
              <circle className="variance-interval-estimate" cx={estimateX} cy={y} r="5" />
            </g>
          );
        })}
        <text className="chart-axis-label" x={plot.left} y={height - 14}>{formatNumber(range.min)}</text>
        <text className="chart-axis-label chart-axis-label-end" x={plot.left + plotWidth} y={height - 14}>{formatNumber(range.max)}</text>
        <text className="chart-axis-label chart-axis-label-center" x={plot.left + plotWidth / 2} y={height - 4}>표준편차</text>
      </svg>
      {interaction.activeItem !== null && activeGroup !== null ? (
        <ChartTooltip
          details={details}
          left={interaction.activeItem.left}
          title={activeGroup.group_label}
          top={interaction.activeItem.top}
        />
      ) : null}
      <div className="chart-selected-detail" aria-live="polite">
        {activeGroup === null ? (
          <span>그룹을 선택하면 표준편차와 비교구간을 확인할 수 있습니다.</span>
        ) : (
          <>
            <strong>{activeGroup.group_label}</strong>
            {details.map((detail) => <span key={detail.label}>{detail.label}: {detail.value}</span>)}
          </>
        )}
      </div>
    </div>
  );
}

function groupDetails(
  group: EqualVarianceMultipleComparisons["groups"][number],
  result: EqualVarianceMultipleComparisons,
) {
  const peers = result.non_overlapping_pairs
    .filter((pair) => pair.left_group === group.group_label || pair.right_group === group.group_label)
    .map((pair) => pair.left_group === group.group_label ? pair.right_group : pair.left_group);
  return [
    { label: "N", value: group.n.toLocaleString() },
    { label: "표본 표준편차", value: formatNumber(group.sample_standard_deviation) },
    { label: "구간 하한", value: formatNumber(group.comparison_interval.lower) },
    { label: "구간 상한", value: formatNumber(group.comparison_interval.upper) },
    { label: "겹치지 않는 그룹", value: peers.length > 0 ? peers.join(", ") : "없음" },
  ];
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("ko-KR", { maximumSignificantDigits: 7 }).format(value);
}
