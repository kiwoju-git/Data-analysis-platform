import type { IndividualValuePreviewPoint } from "../api";
import {
  InteractiveScatterChart,
  type InteractiveScatterPoint,
} from "./InteractiveScatterChart";
import { paddedNumericRange } from "./chartScale";

export function InteractiveIndividualValueChart({
  chartId,
  points,
}: {
  chartId: string;
  points: IndividualValuePreviewPoint[];
}) {
  const series = Array.from(new Set(points.map((point) => point.series_label)));
  const interactivePoints: InteractiveScatterPoint[] = points.map((point, index) => {
    const seriesIndex = series.indexOf(point.series_label);
    const jitter = deterministicJitter(point.canonical_position, index);
    return {
      ariaLabel: `${point.series_label} ${point.point_index}, 값 ${formatNumber(point.value)}`,
      className: "interactive-chart-point individual-value-point",
      details: [
        { label: "변수/그룹", value: point.series_label },
        { label: "점 순번", value: point.point_index.toLocaleString() },
        { label: "값", value: formatNumber(point.value) },
      ],
      id: `${chartId}-${index}`,
      title: `${point.series_label} 관측 ${point.point_index}`,
      x: seriesIndex + 1 + jitter,
      y: point.value,
    };
  });
  return (
    <InteractiveScatterChart
      annotations={[
        `표시 ${points.length.toLocaleString()}점`,
        "자동 표본추출 없음",
        `series ${series.length.toLocaleString()}개`,
      ]}
      chartId={chartId}
      description="실제 관측값을 변수 또는 그룹별 point strip으로 표시합니다."
      emptyLabel="표시할 관측값이 없습니다."
      formatValue={formatNumber}
      points={interactivePoints}
      title="Individual Value Plot"
      xLabel="변수 또는 그룹"
      xRange={{ min: 0.5, max: Math.max(1.5, series.length + 0.5) }}
      yLabel="Value"
      yRange={paddedNumericRange(points.map((point) => point.value))}
    />
  );
}

function deterministicJitter(canonicalPosition: number, index: number): number {
  const bucket = ((canonicalPosition * 37 + index * 17) % 21) - 10;
  return bucket / 50;
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("ko-KR", { maximumSignificantDigits: 6 }).format(value);
}
