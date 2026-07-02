import type { ReactNode } from "react";

import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  NormalityResult,
} from "./api";

interface NormalityAnalysisPanelProps {
  alpha: number;
  analysisResult: AnalysisResultEnvelope | null;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  methodId: string;
  normalityColumns: DatasetColumnResponse[];
  normalityResult: NormalityResult | null;
  selectedColumnIds: string[];
  version: DatasetVersionResponse | null;
  onAlphaChange: (alpha: number) => void;
  onRun: () => void;
  onToggleColumn: (columnId: string, checked: boolean) => void;
}

const maxNormalityColumns = 20;
const chartWidth = 360;
const chartHeight = 210;
const plot = {
  left: 38,
  right: 12,
  top: 16,
  bottom: 36,
};
const plotWidth = chartWidth - plot.left - plot.right;
const plotHeight = chartHeight - plot.top - plot.bottom;

export function NormalityAnalysisPanel({
  alpha,
  analysisResult,
  filterValidationError,
  isRunningAnalysis,
  methodId,
  normalityColumns,
  normalityResult,
  selectedColumnIds,
  version,
  onAlphaChange,
  onRun,
  onToggleColumn,
}: NormalityAnalysisPanelProps) {
  return (
    <section className="analysis-run-panel" aria-labelledby="normality-title">
      <div className="panel-heading">
        <div>
          <h3 id="normality-title">정규성 검정 실행</h3>
          <p>{methodId}</p>
        </div>
        <span className="status-pill status-ready">사용 가능</span>
      </div>
      {version === null ? (
        <div className="notice-box">데이터셋 버전 생성 후 실행할 수 있습니다.</div>
      ) : (
        <>
          <div className="column-picker" aria-label="정규성 검정 컬럼 선택">
            {normalityColumns.map((column) => (
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
          <label className="inline-field">
            <span>유의수준 alpha</span>
            <input
              max="0.5"
              min="0.001"
              step="0.001"
              type="number"
              value={alpha}
              onChange={(event) => {
                onAlphaChange(Number(event.currentTarget.value));
              }}
            />
          </label>
          <button
            className="primary-button"
            disabled={
              isRunningAnalysis ||
              selectedColumnIds.length === 0 ||
              selectedColumnIds.length > maxNormalityColumns ||
              alpha <= 0 ||
              alpha >= 1 ||
              filterValidationError !== null
            }
            onClick={() => {
              onRun();
            }}
            type="button"
          >
            {isRunningAnalysis ? "실행 중" : "정규성 검정 실행"}
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
          {normalityResult !== null ? (
            <div className="graphical-summary-results" aria-label="정규성 검정 결과">
              <div className="result-section">
                <div className="panel-heading">
                  <div>
                    <h4>Q-Q Plot</h4>
                    <p>
                      {normalityResult.qq_plot_distribution} ·{" "}
                      {normalityResult.qq_plotting_position}
                    </p>
                  </div>
                </div>
                <div className="graphical-summary-grid">
                  {normalityResult.columns.map((column) => (
                    <NormalityQqCard key={column.column_id} column={column} />
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
                      <th>평균</th>
                      <th>표준편차</th>
                      <th>Shapiro W</th>
                      <th>Shapiro p</th>
                      <th>AD</th>
                      <th>AD 결정</th>
                      <th>Q-Q</th>
                    </tr>
                  </thead>
                  <tbody>
                    {normalityResult.columns.map((column) => (
                      <tr key={column.column_id}>
                        <td>{column.display_name}</td>
                        <td>{column.n_used}</td>
                        <td>{column.n_missing}</td>
                        <td>{formatAnalysisNumber(column.mean)}</td>
                        <td>{formatAnalysisNumber(column.std)}</td>
                        <td>{formatAnalysisNumber(column.shapiro_wilk.statistic)}</td>
                        <td>{formatAnalysisNumber(column.shapiro_wilk.p_value)}</td>
                        <td>{formatAnalysisNumber(column.anderson_darling.statistic)}</td>
                        <td>
                          {andersonDecisionLabel(
                            column.anderson_darling.decision_at_alpha,
                          )}
                        </td>
                        <td>{column.qq_plot.point_count}</td>
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

function NormalityQqCard({ column }: { column: NormalityResult["columns"][number] }) {
  return (
    <section className="graphical-summary-card" aria-label={`${column.display_name} 정규성 Q-Q Plot`}>
      <div className="graphical-card-heading">
        <div>
          <h5>{column.display_name}</h5>
          <p>
            N {column.n_used.toLocaleString()} · Shapiro p{" "}
            {formatAnalysisNumber(column.shapiro_wilk.p_value)}
          </p>
        </div>
        <span className="chart-warning-count">
          AD {andersonDecisionLabel(column.anderson_darling.decision_at_alpha)}
        </span>
      </div>
      <div className="chart-grid chart-grid-single">
        <ChartPanel title="Q-Q Plot">{renderQqPlot(column)}</ChartPanel>
      </div>
      {column.warnings.length > 0 ? (
        <ul className="inline-warning-list" aria-label={`${column.display_name} 정규성 경고`}>
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

function renderQqPlot(column: NormalityResult["columns"][number]) {
  const points = column.qq_plot.points
    .filter(
      (point): point is { theoretical: number; sample: number } =>
        typeof point.theoretical === "number" && typeof point.sample === "number",
    )
    .slice(0, 500);
  if (points.length === 0) {
    return <EmptyChart label="Q-Q point 없음" />;
  }

  const xRange = paddedRange(points.map((point) => point.theoretical));
  const yRange = paddedRange(points.map((point) => point.sample));
  return (
    <svg
      aria-label={`${column.display_name} normality Q-Q plot`}
      className="chart-svg"
      role="img"
      viewBox={`0 0 ${chartWidth} ${chartHeight}`}
    >
      {chartAxes()}
      <line
        className="reference-line"
        x1={plot.left}
        x2={plot.left + plotWidth}
        y1={plot.top + plotHeight}
        y2={plot.top}
      />
      {points.map((point, index) => (
        <circle
          key={`${point.theoretical}-${point.sample}-${index}`}
          className="qq-point"
          cx={scale(point.theoretical, xRange.min, xRange.max, plot.left, plot.left + plotWidth)}
          cy={scale(point.sample, yRange.min, yRange.max, plot.top + plotHeight, plot.top)}
          r="2"
        />
      ))}
      {chartTickLabels(formatAnalysisNumber(xRange.min), formatAnalysisNumber(xRange.max))}
      <text className="chart-axis-label" x={plot.left - 8} y={plot.top + 8}>
        {formatAnalysisNumber(yRange.max)}
      </text>
    </svg>
  );
}

function EmptyChart({ label }: { label: string }) {
  return (
    <svg
      aria-label={label}
      className="chart-svg chart-svg-empty"
      role="img"
      viewBox={`0 0 ${chartWidth} ${chartHeight}`}
    >
      <rect className="empty-chart-bg" height={plotHeight} width={plotWidth} x={plot.left} y={plot.top} />
      <text className="empty-chart-text" x={chartWidth / 2} y={chartHeight / 2}>
        {label}
      </text>
    </svg>
  );
}

function chartAxes() {
  return (
    <>
      <line
        className="chart-axis"
        x1={plot.left}
        x2={plot.left}
        y1={plot.top}
        y2={plot.top + plotHeight}
      />
      <line
        className="chart-axis"
        x1={plot.left}
        x2={plot.left + plotWidth}
        y1={plot.top + plotHeight}
        y2={plot.top + plotHeight}
      />
      <line
        className="chart-grid-line"
        x1={plot.left}
        x2={plot.left + plotWidth}
        y1={plot.top}
        y2={plot.top}
      />
    </>
  );
}

function chartTickLabels(leftLabel: string, rightLabel: string) {
  return (
    <>
      <text className="chart-axis-label" x={plot.left} y={chartHeight - 10}>
        {leftLabel}
      </text>
      <text className="chart-axis-label chart-axis-label-end" x={plot.left + plotWidth} y={chartHeight - 10}>
        {rightLabel}
      </text>
    </>
  );
}

function paddedRange(values: number[]): { min: number; max: number } {
  const finiteValues = values.filter((value) => Number.isFinite(value));
  if (finiteValues.length === 0) {
    return { min: 0, max: 1 };
  }
  const min = Math.min(...finiteValues);
  const max = Math.max(...finiteValues);
  if (min === max) {
    const padding = Math.max(1, Math.abs(min) * 0.1);
    return { min: min - padding, max: max + padding };
  }
  const padding = (max - min) * 0.04;
  return { min: min - padding, max: max + padding };
}

function scale(
  value: number,
  domainMin: number,
  domainMax: number,
  rangeMin: number,
  rangeMax: number,
): number {
  if (domainMin === domainMax) {
    return (rangeMin + rangeMax) / 2;
  }
  return rangeMin + ((value - domainMin) / (domainMax - domainMin)) * (rangeMax - rangeMin);
}

function andersonDecisionLabel(
  decision: NormalityResult["columns"][number]["anderson_darling"]["decision_at_alpha"],
): string {
  if (decision === null || decision.reject_normality === null) {
    return "-";
  }
  return decision.reject_normality ? "기각" : "기각 안 함";
}

function formatAnalysisNumber(value: number | null): string {
  if (value === null) {
    return "-";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumSignificantDigits: 6,
  }).format(value);
}
