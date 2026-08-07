import type { ReactNode } from "react";

import type { GraphicalSummaryResult } from "./api";
import { InteractiveBoxplotChart } from "./charts/InteractiveBoxplotChart";
import { InteractiveDistributionCiChart } from "./charts/InteractiveDistributionCiChart";
import { InteractiveHistogramChart } from "./charts/InteractiveHistogramChart";
import { InteractiveQqChart } from "./charts/InteractiveQqChart";
import {
  InteractiveScatterChart,
  type InteractiveScatterPoint,
} from "./charts/InteractiveScatterChart";
import { paddedNumericRange } from "./charts/chartScale";

type GraphicalSummaryColumn = GraphicalSummaryResult["columns"][number];

interface GraphicalSummaryColumnVisualsProps {
  charts?: Array<"boxplot" | "ecdf" | "histogram" | "qq">;
  column: GraphicalSummaryColumn;
  mode: "quick" | "full";
}

export function GraphicalSummaryColumnVisuals({
  charts,
  column,
  mode,
}: GraphicalSummaryColumnVisualsProps) {
  const visibleCharts =
    charts ?? (mode === "quick" ? ["histogram", "boxplot"] : ["histogram", "boxplot", "qq", "ecdf"]);
  const chartGridClassName =
    visibleCharts.length === 1 ? "chart-grid chart-grid-single" : "chart-grid";
  if (mode === "full" && charts === undefined) {
    return <FullGraphicalSummaryColumn column={column} />;
  }
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
      <div className={chartGridClassName}>
        {visibleCharts.includes("histogram") ? (
          <ChartPanel title="히스토그램">
            <InteractiveHistogramChart
              bins={column.histogram.bins}
              chartId={`graphical-histogram-${mode}-${column.column_id}`}
              columnName={column.display_name}
              nBasis={column.n_used}
            />
          </ChartPanel>
        ) : null}
        {visibleCharts.includes("boxplot") ? (
          <ChartPanel title="박스플롯">
            <InteractiveBoxplotChart
              boxplot={column.boxplot}
              chartId={`graphical-boxplot-${mode}-${column.column_id}`}
              columnName={column.display_name}
            />
          </ChartPanel>
        ) : null}
        {visibleCharts.includes("qq") ? (
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
        ) : null}
        {visibleCharts.includes("ecdf") ? (
          <ChartPanel title="ECDF">{renderEcdf(column)}</ChartPanel>
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

function FullGraphicalSummaryColumn({ column }: { column: GraphicalSummaryColumn }) {
  return (
    <section className="graphical-summary-card graphical-summary-card-full" aria-label={`${column.display_name} 그래프 요약`}>
      <div className="graphical-card-heading">
        <div>
          <h5>{column.display_name}</h5>
          <p>N {column.n_used.toLocaleString()} · 결측 {column.n_missing.toLocaleString()}</p>
        </div>
      </div>
      <div className="graphical-summary-primary-grid">
        <ChartPanel title="히스토그램 + 적합 정규곡선">
          <InteractiveHistogramChart
            bins={column.histogram.bins}
            chartId={`graphical-histogram-full-${column.column_id}`}
            columnName={column.display_name}
            nBasis={column.n_used}
            normalFitPoints={column.normal_fit_curve?.computed ? column.normal_fit_curve.points : []}
          />
        </ChartPanel>
        <GraphicalStatisticsPanel column={column} />
      </div>
      <div className="chart-grid">
        <ChartPanel title="박스플롯">
          <InteractiveBoxplotChart
            boxplot={column.boxplot}
            chartId={`graphical-boxplot-full-${column.column_id}`}
            columnName={column.display_name}
          />
        </ChartPanel>
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
      </div>
      {column.confidence_intervals ? (
        <ChartPanel title="신뢰구간">
          <InteractiveDistributionCiChart
            chartId={`graphical-ci-${column.column_id}`}
            columnName={column.display_name}
            intervals={column.confidence_intervals}
          />
        </ChartPanel>
      ) : null}
      <details className="graphical-summary-extra">
        <summary>추가 그래프: ECDF</summary>
        <ChartPanel title="ECDF">{renderEcdf(column)}</ChartPanel>
      </details>
      {column.warnings.length > 0 ? (
        <ul className="inline-warning-list" aria-label={`${column.display_name} 그래프 경고`}>
          {column.warnings.map((warning) => <li key={warning}>{warning}</li>)}
        </ul>
      ) : null}
    </section>
  );
}

function GraphicalStatisticsPanel({ column }: { column: GraphicalSummaryColumn }) {
  const ad = column.anderson_darling;
  return (
    <section className="graphical-statistics-panel" aria-label={`${column.display_name} 통계 요약`}>
      <h6>Anderson-Darling 정규성 검정</h6>
      <DefinitionRows rows={[
        ["A²", formatAnalysisNumber(ad?.statistic ?? null)],
        ["보정 A²", formatAnalysisNumber(ad?.adjusted_statistic ?? null)],
        ["p-value", formatAnalysisNumber(ad?.p_value ?? null)],
      ]} />
      <h6>기술통계</h6>
      <DefinitionRows rows={[
        ["평균", formatAnalysisNumber(column.mean ?? null)],
        ["표준편차", formatAnalysisNumber(column.standard_deviation ?? null)],
        ["분산", formatAnalysisNumber(column.variance ?? null)],
        ["왜도", formatAnalysisNumber(column.skewness ?? null)],
        ["첨도", formatAnalysisNumber(column.kurtosis_excess ?? null)],
        ["N", column.n_used.toLocaleString()],
      ]} />
      <h6>5수치 요약</h6>
      <DefinitionRows rows={[
        ["최소", formatAnalysisNumber(column.min)],
        ["Q1", formatAnalysisNumber(column.q1)],
        ["중앙값", formatAnalysisNumber(column.median)],
        ["Q3", formatAnalysisNumber(column.q3)],
        ["최대", formatAnalysisNumber(column.max)],
      ]} />
    </section>
  );
}

function DefinitionRows({ rows }: { rows: Array<[string, string]> }) {
  return <dl className="graphical-statistics-list">{rows.map(([label, value]) => (
    <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
  ))}</dl>;
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
