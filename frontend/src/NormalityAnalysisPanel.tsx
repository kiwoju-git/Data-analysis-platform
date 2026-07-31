import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  NormalityResult,
} from "./api";
import { InteractiveQqChart } from "./charts/InteractiveQqChart";
import {
  andersonDecisionDisplay,
  andersonPValueLabel,
} from "./normalityDisplay";

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
    <section className="analysis-run-panel" data-analysis-execution={methodId}>
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
                    <NormalityQqCard
                      alpha={normalityResult.alpha}
                      key={column.column_id}
                      column={column}
                    />
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
                      <th>AD p (근사)</th>
                      <th>AD 해석</th>
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
                        <td>{andersonPValueLabel(column.anderson_darling)}</td>
                        <td>
                          <NormalityDecision
                            decision={column.anderson_darling.decision_at_alpha}
                          />
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

function NormalityQqCard({
  alpha,
  column,
}: {
  alpha: number;
  column: NormalityResult["columns"][number];
}) {
  const decision = andersonDecisionDisplay(
    column.anderson_darling.decision_at_alpha,
  );
  return (
    <section className="graphical-summary-card" aria-label={`${column.display_name} 정규성 Q-Q Plot`}>
      <div className="graphical-card-heading">
        <div>
          <h5>{column.display_name}</h5>
          <p>
            N {column.n_used.toLocaleString()} · Shapiro p{" "}
            {formatAnalysisNumber(column.shapiro_wilk.p_value)} · AD p (근사){" "}
            {andersonPValueLabel(column.anderson_darling)} · alpha{" "}
            {formatAnalysisNumber(alpha)}
          </p>
        </div>
        <span className={`normality-decision-badge is-${decision.tone}`}>
          <small>AD</small>
          <strong>{decision.shortLabel}</strong>
        </span>
      </div>
      <div className="chart-grid chart-grid-single">
        <div className="chart-panel">
          <div className="chart-panel-title">Q-Q Plot</div>
          <InteractiveQqChart
            chartId={`normality-qq-${column.column_id}`}
            columnName={column.display_name}
            nBasis={column.n_used}
            pointCount={column.qq_plot.point_count}
            points={column.qq_plot.points}
            truncated={column.qq_plot.points_truncated}
          />
        </div>
      </div>
      <p className="analysis-note">
        {decision.detail} AD p는 Stephens 정규성 근사값입니다. Shapiro와 AD 중
        유리한 결과만 골라 후속 분석을 자동 전환하지 않습니다.
      </p>
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

function NormalityDecision({
  decision,
}: {
  decision: NormalityResult["columns"][number]["anderson_darling"]["decision_at_alpha"];
}) {
  const display = andersonDecisionDisplay(decision);
  return (
    <span
      className={`normality-decision-label is-${display.tone}`}
      title={display.detail}
    >
      {display.shortLabel}
    </span>
  );
}

function formatAnalysisNumber(value: number | null): string {
  if (value === null) {
    return "-";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumSignificantDigits: 6,
  }).format(value);
}
