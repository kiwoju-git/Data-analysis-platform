import type { ReactNode } from "react";

import type { GraphicalSummaryResult } from "./api";
import { InteractiveBoxplotChart } from "./charts/InteractiveBoxplotChart";
import { InteractiveHistogramChart } from "./charts/InteractiveHistogramChart";
import { InteractiveQqChart } from "./charts/InteractiveQqChart";
import {
  InteractiveScatterChart,
  type InteractiveScatterPoint,
} from "./charts/InteractiveScatterChart";
import { paddedNumericRange } from "./charts/chartScale";

type GraphicalSummaryColumn = GraphicalSummaryResult["columns"][number];

interface GraphicalSummaryColumnVisualsProps {
  column: GraphicalSummaryColumn;
  mode: "quick" | "full";
}

export function GraphicalSummaryColumnVisuals({
  column,
  mode,
}: GraphicalSummaryColumnVisualsProps) {
  return (
    <section
      className={`graphical-summary-card graphical-summary-card-${mode}`}
      aria-label={`${column.display_name} 그래프 요약`}
    >
      <div className="graphical-card-heading">
        <div>
          <h5>{column.display_name}</h5>
          <p>
            N {column.n_used.toLocaleString()} · missing {column.n_missing.toLocaleString()}
          </p>
        </div>
        {column.warnings.length > 0 ? (
          <span className="chart-warning-count">{column.warnings.length} warning</span>
        ) : null}
      </div>
      <div className="chart-grid">
        <ChartPanel title="히스토그램">
          <InteractiveHistogramChart
            bins={column.histogram.bins}
            chartId={`graphical-histogram-${mode}-${column.column_id}`}
            columnName={column.display_name}
            nBasis={column.n_used}
          />
        </ChartPanel>
        <ChartPanel title="박스플롯">
          <InteractiveBoxplotChart
            boxplot={column.boxplot}
            chartId={`graphical-boxplot-${mode}-${column.column_id}`}
            columnName={column.display_name}
          />
        </ChartPanel>
        {mode === "full" ? (
          <>
            <ChartPanel title="Q-Q Plot">
              <InteractiveQqChart
                chartId={`graphical-qq-${column.column_id}`}
                columnName={column.display_name}
                nBasis={column.n_used}
                pointCount={column.qq_plot.point_count}
                points={column.qq_plot.points}
                truncated={column.qq_plot.points_truncated}
              />
            </ChartPanel>
            <ChartPanel title="ECDF">{renderEcdf(column)}</ChartPanel>
          </>
        ) : null}
      </div>
      {column.warnings.length > 0 ? (
        <ul className="inline-warning-list" aria-label={`${column.display_name} 그래프 경고`}>
          {column.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function ChartPanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="chart-panel">
      <div className="chart-panel-title">{title}</div>
      {children}
    </div>
  );
}

function renderEcdf(column: GraphicalSummaryColumn) {
  const points = column.ecdf.points
    .filter(
      (point): point is { x: number; probability: number } =>
        typeof point.x === "number" && typeof point.probability === "number",
    )
    .slice(0, 500)
    .sort((left, right) => left.x - right.x || left.probability - right.probability);
  if (points.length === 0) {
    return <div className="empty-state">ECDF point 없음</div>;
  }
  const xRange = paddedNumericRange(points.map((point) => point.x));
  const interactivePoints: InteractiveScatterPoint[] = points.map((point, index) => ({
    ariaLabel: `${column.display_name} ECDF ${index + 1}, 값 ${formatAnalysisNumber(point.x)}, 누적확률 ${formatAnalysisNumber(point.probability)}`,
    className: "ecdf-point interactive-chart-point",
    details: [
      { label: "점 순번", value: String(index + 1) },
      { label: "X 값", value: formatAnalysisNumber(point.x) },
      { label: "누적확률", value: formatAnalysisNumber(point.probability) },
      {
        label: "근사 순위",
        value: `${Math.max(1, Math.round(point.probability * column.n_used))} / ${column.n_used}`,
      },
      { label: "N 기준", value: column.n_used.toLocaleString() },
    ],
    id: `graphical-ecdf-${column.column_id}-${index}`,
    title: `ECDF 점 ${index + 1}`,
    x: point.x,
    y: point.probability,
  }));
  return (
    <InteractiveScatterChart
      annotations={[
        `표시 ${points.length.toLocaleString()} / payload ${column.ecdf.point_count.toLocaleString()}`,
        column.ecdf.points_truncated ? "ECDF point cap 적용" : "전체 bounded point 표시",
      ]}
      chartId={`graphical-ecdf-${column.column_id}`}
      compact
      connectPoints="step"
      description={`${column.display_name}의 bounded ECDF points`}
      emptyLabel="ECDF point 없음"
      formatValue={(value) => formatAnalysisNumber(value)}
      points={interactivePoints}
      title={`${column.display_name} ECDF`}
      xLabel="Value"
      xRange={xRange}
      yLabel="Cumulative probability"
      yRange={{ min: 0, max: 1 }}
    />
  );
}

function formatAnalysisNumber(value: number | null): string {
  if (value === null) {
    return "-";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 6,
  }).format(value);
}
