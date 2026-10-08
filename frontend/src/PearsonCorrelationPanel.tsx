import { PearsonResultChart } from "./charts/PearsonResultChart";
import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  PearsonCorrelationResult,
} from "./api";

interface PearsonCorrelationPanelProps {
  alpha: number;
  analysisResult: AnalysisResultEnvelope | null;
  confidenceLevel: number;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  methodId: string;
  result: PearsonCorrelationResult | null;
  version: DatasetVersionResponse | null;
  xColumnId: string | null;
  xColumns: DatasetColumnResponse[];
  yColumnId: string | null;
  yColumns: DatasetColumnResponse[];
  onAlphaChange: (alpha: number) => void;
  onConfidenceLevelChange: (confidenceLevel: number) => void;
  onRun: () => void;
  onXColumnChange: (columnId: string) => void;
  onYColumnChange: (columnId: string) => void;
}

export function PearsonCorrelationPanel({
  alpha,
  analysisResult,
  confidenceLevel,
  filterValidationError,
  isRunningAnalysis,
  methodId,
  result,
  version,
  xColumnId,
  xColumns,
  yColumnId,
  yColumns,
  onAlphaChange,
  onConfidenceLevelChange,
  onRun,
  onXColumnChange,
  onYColumnChange,
}: PearsonCorrelationPanelProps) {
  const canRun =
    version !== null &&
    xColumnId !== null &&
    yColumnId !== null &&
    xColumnId !== yColumnId &&
    alpha > 0 &&
    alpha < 1 &&
    confidenceLevel > 0 &&
    confidenceLevel < 1 &&
    filterValidationError === null;

  return (
    <section className="analysis-run-panel" data-analysis-execution={methodId}>
      {version === null ? (
        <div className="notice-box">데이터셋 버전 생성 후 실행할 수 있습니다.</div>
      ) : (
        <>
          <div className="option-grid">
            <label>
              <span>X 변수</span>
              <select
                value={xColumnId ?? ""}
                onChange={(event) => {
                  onXColumnChange(event.currentTarget.value);
                }}
              >
                <option value="">선택</option>
                {xColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Y 변수</span>
              <select
                value={yColumnId ?? ""}
                onChange={(event) => {
                  onYColumnChange(event.currentTarget.value);
                }}
              >
                <option value="">선택</option>
                {yColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
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
            <label>
              <span>신뢰수준</span>
              <input
                max="0.999"
                min="0.5"
                step="0.001"
                type="number"
                value={confidenceLevel}
                onChange={(event) => {
                  onConfidenceLevelChange(Number(event.currentTarget.value));
                }}
              />
            </label>
          </div>
          <button
            className="primary-button"
            disabled={isRunningAnalysis || !canRun}
            onClick={() => {
              onRun();
            }}
            type="button"
          >
            {isRunningAnalysis ? "실행 중" : "Pearson 상관 실행"}
          </button>
          {analysisResult?.warnings.length ? (
            <ul className="warning-list" aria-label="분석 경고">
              {analysisResult.warnings.map((warning, index) => (
                <li key={`${warning.code}-${index}`}>{warning.message}</li>
              ))}
            </ul>
          ) : null}
          {result !== null ? (
            <>
              <div className="metadata-grid" aria-label="Pearson 상관 요약">
                <span>변수</span>
                <strong>
                  {result.x.display_name} / {result.y.display_name}
                </strong>
                <span>사용 N</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>결측 제외</span>
                <strong>
                  {(result.n_excluded_missing_x + result.n_excluded_missing_y).toLocaleString()}
                </strong>
                <span>비숫자 제외</span>
                <strong>
                  {(
                    result.n_excluded_non_numeric_x + result.n_excluded_non_numeric_y
                  ).toLocaleString()}
                </strong>
              </div>
              <div className="result-section" aria-label="Pearson 산점도 결과">
                <div className="panel-heading">
                  <div>
                    <h4>산점도</h4>
                    <p>
                      {result.scatterplot.points.length.toLocaleString()} /{" "}
                      {result.scatterplot.point_count.toLocaleString()} points
                      {result.scatterplot.points_truncated ? " · capped" : ""}
                    </p>
                  </div>
                </div>
                <div className="chart-grid chart-grid-single analysis-result-grid">
                  <div className="chart-panel">
                    <div className="chart-panel-title">
                      {result.x.display_name} vs {result.y.display_name}
                    </div>
                    <PearsonResultChart result={result} />
                  </div>
                </div>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>r</th>
                      <th>CI</th>
                      <th>p-value</th>
                      <th>r²</th>
                      <th>공분산</th>
                      <th>결정</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{formatAnalysisNumber(result.association.correlation)}</td>
                      <td>{confidenceIntervalLabel(result)}</td>
                      <td>{formatAnalysisNumber(result.test.p_value)}</td>
                      <td>{formatAnalysisNumber(result.association.r_squared)}</td>
                      <td>{formatAnalysisNumber(result.association.covariance)}</td>
                      <td>{result.test.reject_null ? "기각" : "기각 안 함"}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>변수</th>
                      <th>N</th>
                      <th>평균</th>
                      <th>표준편차</th>
                      <th>범위</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{result.x.display_name}</td>
                      <td>{result.x_summary.n.toLocaleString()}</td>
                      <td>{formatAnalysisNumber(result.x_summary.mean)}</td>
                      <td>{formatAnalysisNumber(result.x_summary.std)}</td>
                      <td>
                        {formatAnalysisNumber(result.x_summary.min)} -{" "}
                        {formatAnalysisNumber(result.x_summary.max)}
                      </td>
                    </tr>
                    <tr>
                      <td>{result.y.display_name}</td>
                      <td>{result.y_summary.n.toLocaleString()}</td>
                      <td>{formatAnalysisNumber(result.y_summary.mean)}</td>
                      <td>{formatAnalysisNumber(result.y_summary.std)}</td>
                      <td>
                        {formatAnalysisNumber(result.y_summary.min)} -{" "}
                        {formatAnalysisNumber(result.y_summary.max)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </>
          ) : null}
        </>
      )}
    </section>
  );
}

function confidenceIntervalLabel(result: PearsonCorrelationResult): string {
  const { lower, upper, level } = result.confidence_interval;
  if (lower === null || upper === null) {
    return "계산 불가";
  }
  return `${formatPercent(level)} CI ${formatAnalysisNumber(lower)} - ${formatAnalysisNumber(
    upper,
  )}`;
}

function formatPercent(value: number): string {
  return `${Math.round(value * 1000) / 10}%`;
}

function formatAnalysisNumber(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "NA";
  }
  return value.toLocaleString("ko-KR", {
    maximumFractionDigits: 6,
    minimumFractionDigits: 0,
  });
}
