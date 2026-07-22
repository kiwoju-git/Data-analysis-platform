import { InteractiveScatterChart, type InteractiveScatterPoint } from "./InteractiveScatterChart";
import { paddedNumericRange } from "./chartScale";

interface QqPoint {
  sample?: number;
  theoretical?: number;
}

interface InteractiveQqChartProps {
  chartId: string;
  columnName: string;
  nBasis: number;
  pointCount: number;
  points: QqPoint[];
  truncated: boolean;
}

export function InteractiveQqChart({
  chartId,
  columnName,
  nBasis,
  pointCount,
  points,
  truncated,
}: InteractiveQqChartProps) {
  const finitePoints = points
    .filter(
      (point): point is { theoretical: number; sample: number } =>
        typeof point.theoretical === "number" &&
        Number.isFinite(point.theoretical) &&
        typeof point.sample === "number" &&
        Number.isFinite(point.sample),
    )
    .slice(0, 500);
  const xRange = paddedNumericRange(finitePoints.map((point) => point.theoretical));
  const yRange = paddedNumericRange(finitePoints.map((point) => point.sample));
  const interactivePoints: InteractiveScatterPoint[] = finitePoints.map((point, index) => ({
    ariaLabel: `${columnName} Q-Q ${index + 1}, 이론 분위수 ${formatNumber(point.theoretical)}, 표본 분위수 ${formatNumber(point.sample)}`,
    className: "qq-point interactive-chart-point",
    details: [
      { label: "점 순번", value: String(index + 1) },
      { label: "이론 분위수", value: formatNumber(point.theoretical) },
      { label: "표본 분위수", value: formatNumber(point.sample) },
      { label: "표본-이론 차이", value: formatNumber(point.sample - point.theoretical) },
      { label: "컬럼", value: columnName },
      { label: "N 기준", value: nBasis.toLocaleString() },
    ],
    id: `${chartId}-point-${index}`,
    title: `Q-Q 점 ${index + 1}`,
    x: point.theoretical,
    y: point.sample,
  }));

  return (
    <InteractiveScatterChart
      annotations={[
        `표시 ${finitePoints.length.toLocaleString()} / payload ${pointCount.toLocaleString()}`,
        truncated ? "Q-Q point cap 적용" : "전체 bounded point 표시",
      ]}
      chartId={chartId}
      compact
      description={`${columnName}의 bounded Q-Q points. 마우스, 터치 또는 화살표 키로 값을 확인합니다.`}
      emptyLabel="Q-Q point 없음"
      formatValue={formatNumber}
      points={interactivePoints}
      referenceLines={[
        {
          label: "Q-Q 기준선",
          x1: xRange.min,
          x2: xRange.max,
          y1: yRange.min,
          y2: yRange.max,
        },
      ]}
      title={`${columnName} Q-Q Plot`}
      xLabel="Theoretical quantile"
      xRange={xRange}
      yLabel="Sample quantile"
      yRange={yRange}
    />
  );
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("ko-KR", { maximumSignificantDigits: 6 }).format(value);
}
