import { ChartTooltip } from "./ChartTooltip";
import { paddedNumericRange, scaleChartValue } from "./chartScale";
import { useChartItemInteraction } from "./useChartItemInteraction";

export interface InteractiveHistogramBin {
  count: number;
  include_lower: boolean;
  include_upper: boolean;
  lower: number;
  upper: number;
}

interface InteractiveHistogramChartProps {
  bins: InteractiveHistogramBin[];
  chartId: string;
  columnName: string;
  nBasis: number;
}

const width = 360;
const height = 210;
const plot = { left: 38, right: 12, top: 16, bottom: 36 };

export function InteractiveHistogramChart({
  bins,
  chartId,
  columnName,
  nBasis,
}: InteractiveHistogramChartProps) {
  const ids = bins.map((_, index) => `${chartId}-bin-${index}`);
  const interaction = useChartItemInteraction(ids);
  if (bins.length === 0) return <EmptyChart label="숫자 데이터 없음" />;

  const plotWidth = width - plot.left - plot.right;
  const plotHeight = height - plot.top - plot.bottom;
  const range = paddedNumericRange(bins.flatMap((bin) => [bin.lower, bin.upper]));
  const maxCount = Math.max(1, ...bins.map((bin) => bin.count));
  const activeIndex = ids.indexOf(interaction.activeItem?.id ?? "");
  const activeBin = activeIndex >= 0 ? bins[activeIndex] : null;
  const details = activeBin === null ? [] : binDetails(activeBin, activeIndex, nBasis);

  return (
    <div className="interactive-chart">
      <svg
        aria-labelledby={`${chartId}-title ${chartId}-description`}
        className="chart-svg interactive-chart-svg"
        role="img"
        viewBox={`0 0 ${width} ${height}`}
      >
        <title id={`${chartId}-title`}>{`${columnName} 히스토그램`}</title>
        <desc id={`${chartId}-description`}>막대 하나에 Tab으로 진입한 뒤 화살표 키로 bin을 이동합니다.</desc>
        <line className="chart-axis" x1={plot.left} x2={plot.left} y1={plot.top} y2={plot.top + plotHeight} />
        <line className="chart-axis" x1={plot.left} x2={plot.left + plotWidth} y1={plot.top + plotHeight} y2={plot.top + plotHeight} />
        {bins.map((bin, index) => {
          const id = ids[index];
          const x1 = scaleChartValue(bin.lower, range, plot.left, plot.left + plotWidth);
          const x2 = scaleChartValue(bin.upper, range, plot.left, plot.left + plotWidth);
          const barWidth = Math.max(1, x2 - x1 - 1);
          const barHeight = (bin.count / maxCount) * plotHeight;
          const selected = interaction.activeItem?.id === id;
          return (
            <rect
              aria-label={`${columnName} bin ${index + 1}, ${formatNumber(bin.lower)}부터 ${formatNumber(bin.upper)}, count ${bin.count}`}
              className={`histogram-bar chart-interactive-item${selected ? " chart-item-selected" : ""}`}
              data-selected={selected ? "true" : "false"}
              height={barHeight}
              key={id}
              onBlur={() => interaction.clear(id)}
              onClick={() => interaction.activate(id, x1 + barWidth / 2, plot.top + plotHeight - barHeight, "selection")}
              onFocus={() => interaction.activate(id, x1 + barWidth / 2, plot.top + plotHeight - barHeight, "focus")}
              onKeyDown={(event) => interaction.handleKeyDown(event, id, x1 + barWidth / 2, plot.top + plotHeight - barHeight)}
              onPointerEnter={(event) => interaction.move(id, event)}
              onPointerLeave={() => interaction.clear(id)}
              onPointerMove={(event) => interaction.move(id, event)}
              ref={(element) => interaction.itemRef(id, element)}
              role="img"
              tabIndex={interaction.tabIndexFor(id)}
              width={barWidth}
              x={x1}
              y={plot.top + plotHeight - barHeight}
            >
              <title>{`${formatNumber(bin.lower)} ~ ${formatNumber(bin.upper)}: ${bin.count}`}</title>
            </rect>
          );
        })}
        <text className="chart-axis-label" x={plot.left} y={height - 10}>{formatNumber(range.min)}</text>
        <text className="chart-axis-label chart-axis-label-end" x={plot.left + plotWidth} y={height - 10}>{formatNumber(range.max)}</text>
        <text className="chart-axis-label" x={plot.left - 8} y={plot.top + 8}>{maxCount}</text>
      </svg>
      {interaction.activeItem !== null && activeBin !== null ? (
        <ChartTooltip details={details} left={interaction.activeItem.left} title={`Bin ${activeIndex + 1}`} top={interaction.activeItem.top} />
      ) : null}
      <Detail title={activeBin === null ? null : `Bin ${activeIndex + 1}`} details={details} empty="막대에 마우스를 올리거나 Tab과 화살표 키로 bin 값을 확인할 수 있습니다." />
    </div>
  );
}

function binDetails(bin: InteractiveHistogramBin, index: number, nBasis: number) {
  return [
    { label: "Bin", value: String(index + 1) },
    { label: "하한", value: formatNumber(bin.lower) },
    { label: "상한", value: formatNumber(bin.upper) },
    { label: "하한 포함", value: bin.include_lower ? "예" : "아니요" },
    { label: "상한 포함", value: bin.include_upper ? "예" : "아니요" },
    { label: "Count", value: bin.count.toLocaleString() },
    { label: "비율", value: nBasis > 0 ? `${formatNumber((bin.count / nBasis) * 100)}%` : "-" },
  ];
}

function Detail({ title, details, empty }: { title: string | null; details: Array<{ label: string; value: string }>; empty: string }) {
  return <div className="chart-selected-detail" aria-live="polite">{title === null ? <span>{empty}</span> : <><strong>{title}</strong>{details.map((detail) => <span key={detail.label}>{detail.label}: {detail.value}</span>)}</>}</div>;
}

function EmptyChart({ label }: { label: string }) {
  return <div className="empty-state">{label}</div>;
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("ko-KR", { maximumSignificantDigits: 6 }).format(value);
}
