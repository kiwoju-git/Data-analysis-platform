import type { ReactNode } from "react";

import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  GraphicalSummaryResult,
} from "./api";
import { InteractiveBoxplotChart } from "./charts/InteractiveBoxplotChart";
import { InteractiveHistogramChart } from "./charts/InteractiveHistogramChart";
import { InteractiveQqChart } from "./charts/InteractiveQqChart";
import {
  InteractiveScatterChart,
  type InteractiveScatterPoint,
} from "./charts/InteractiveScatterChart";
import { paddedNumericRange } from "./charts/chartScale";

interface GraphicalSummaryPanelProps {
  analysisResult: AnalysisResultEnvelope | null;
  filterValidationError: string | null;
  graphicalColumns: DatasetColumnResponse[];
  graphicalResult: GraphicalSummaryResult | null;
  isRunningAnalysis: boolean;
  methodId: string;
  selectedColumnIds: string[];
  version: DatasetVersionResponse | null;
  onRun: () => void;
  onToggleColumn: (columnId: string, checked: boolean) => void;
}

const maxGraphicalColumns = 20;

export function GraphicalSummaryPanel({
  analysisResult,
  filterValidationError,
  graphicalColumns,
  graphicalResult,
  isRunningAnalysis,
  methodId,
  selectedColumnIds,
  version,
  onRun,
  onToggleColumn,
}: GraphicalSummaryPanelProps) {
  return (
    <section className="analysis-run-panel" aria-labelledby="graphical-summary-title">
      <div className="panel-heading">
        <div>
          <h3 id="graphical-summary-title">그래프 요약 실행</h3>
          <p>{methodId}</p>
        </div>
        <span className="status-pill status-ready">사용 가능</span>
      </div>
      {version === null ? (
        <div className="notice-box">데이터셋 버전 생성 후 실행할 수 있습니다.</div>
      ) : (
        <>
          <div className="column-picker" aria-label="그래프 요약 컬럼 선택">
            {graphicalColumns.map((column) => (
              <label key={column.column_id}>
                <input
                  checked={selectedColumnIds.includes(column.column_id)}
                  type="checkbox"
                  onChange={(event) => {
                    onToggleColumn(column.column_id, event.currentTarget.checked);
                  }}
                />
                <span>{column.display_name}</span>
              </label>
            ))}
          </div>
          <button
            className="primary-button"
            disabled={
              isRunningAnalysis ||
              selectedColumnIds.length === 0 ||
              selectedColumnIds.length > maxGraphicalColumns ||
              filterValidationError !== null
            }
            onClick={() => {
              onRun();
            }}
            type="button"
          >
            {isRunningAnalysis ? "실행 중" : "그래프 요약 실행"}
          </button>
          {analysisResult?.provenance.row_count_included !== undefined &&
          analysisResult.provenance.row_count_included !== null ? (
            <div className="metadata-grid" aria-label="분석 대상 행">
              <span>사용 행</span>
              <strong>
                {analysisResult.provenance.row_count_included.toLocaleString()} /{" "}
                {(
                  analysisResult.provenance.row_count_total ??
                  analysisResult.provenance.row_count_included
                ).toLocaleString()}
              </strong>
            </div>
          ) : null}
          {analysisResult?.warnings.length ? (
            <ul className="warning-list" aria-label="분석 경고">
              {analysisResult.warnings.map((warning, index) => (
                <li key={`${warning.code}-${index}`}>{warning.message}</li>
              ))}
            </ul>
          ) : null}
          {graphicalResult !== null ? (
            <div className="graphical-summary-results" aria-label="그래프 요약 결과">
              <div className="result-section">
                <div className="panel-heading">
                  <div>
                    <h4>분포 시각화</h4>
                    <p>
                      {graphicalResult.histogram_method} histogram ·{" "}
                      {graphicalResult.boxplot_method} boxplot · point cap{" "}
                      {graphicalResult.point_limit.toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="graphical-summary-grid">
                  {graphicalResult.columns.map((column) => (
                    <GraphicalSummaryVisualCard key={column.column_id} column={column} />
                  ))}
                </div>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>컬럼</th>
                      <th>N</th>
                      <th>결측</th>
                      <th>최소</th>
                      <th>Q1</th>
                      <th>중앙값</th>
                      <th>Q3</th>
                      <th>최대</th>
                      <th>Bins</th>
                      <th>Outliers</th>
                      <th>Q-Q</th>
                      <th>ECDF</th>
                    </tr>
                  </thead>
                  <tbody>
                    {graphicalResult.columns.map((column) => (
                      <tr key={column.column_id}>
                        <td>{column.display_name}</td>
                        <td>{column.n_used}</td>
                        <td>{column.n_missing}</td>
                        <td>{formatAnalysisNumber(column.min)}</td>
                        <td>{formatAnalysisNumber(column.q1)}</td>
                        <td>{formatAnalysisNumber(column.median)}</td>
                        <td>{formatAnalysisNumber(column.q3)}</td>
                        <td>{formatAnalysisNumber(column.max)}</td>
                        <td>{column.histogram.bin_count}</td>
                        <td>{column.boxplot.outlier_count}</td>
                        <td>{column.qq_plot.point_count}</td>
                        <td>{column.ecdf.point_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}

function GraphicalSummaryVisualCard({
  column,
}: {
  column: GraphicalSummaryResult["columns"][number];
}) {
  return (
    <section className="graphical-summary-card" aria-label={`${column.display_name} 그래프 요약`}>
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
        <ChartPanel title="히스토그램">{renderHistogram(column)}</ChartPanel>
        <ChartPanel title="박스플롯">{renderBoxplot(column)}</ChartPanel>
        <ChartPanel title="Q-Q Plot">{renderQqPlot(column)}</ChartPanel>
        <ChartPanel title="ECDF">{renderEcdf(column)}</ChartPanel>
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

function renderHistogram(column: GraphicalSummaryResult["columns"][number]) {
  return (
    <InteractiveHistogramChart
      bins={column.histogram.bins}
      chartId={`graphical-histogram-${column.column_id}`}
      columnName={column.display_name}
      nBasis={column.n_used}
    />
  );
}

function renderBoxplot(column: GraphicalSummaryResult["columns"][number]) {
  return (
    <InteractiveBoxplotChart
      boxplot={column.boxplot}
      chartId={`graphical-boxplot-${column.column_id}`}
      columnName={column.display_name}
    />
  );
}

function renderQqPlot(column: GraphicalSummaryResult["columns"][number]) {
  return (
    <InteractiveQqChart
      chartId={`graphical-qq-${column.column_id}`}
      columnName={column.display_name}
      nBasis={column.n_used}
      pointCount={column.qq_plot.point_count}
      points={column.qq_plot.points}
      truncated={column.qq_plot.points_truncated}
    />
  );
}

function renderEcdf(column: GraphicalSummaryResult["columns"][number]) {
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
      { label: "근사 순위", value: `${Math.max(1, Math.round(point.probability * column.n_used))} / ${column.n_used}` },
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
