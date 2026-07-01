import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  EquivalenceTostResult,
} from "./api";

interface EquivalenceTostPanelProps {
  alpha: number;
  analysisResult: AnalysisResultEnvelope | null;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  lowerBound: number;
  methodId: string;
  referenceMean: number;
  responseColumnId: string | null;
  responseColumns: DatasetColumnResponse[];
  result: EquivalenceTostResult | null;
  upperBound: number;
  version: DatasetVersionResponse | null;
  onAlphaChange: (alpha: number) => void;
  onLowerBoundChange: (lowerBound: number) => void;
  onReferenceMeanChange: (referenceMean: number) => void;
  onResponseColumnChange: (columnId: string) => void;
  onRun: () => void;
  onUpperBoundChange: (upperBound: number) => void;
}

export function EquivalenceTostPanel({
  alpha,
  analysisResult,
  filterValidationError,
  isRunningAnalysis,
  lowerBound,
  methodId,
  referenceMean,
  responseColumnId,
  responseColumns,
  result,
  upperBound,
  version,
  onAlphaChange,
  onLowerBoundChange,
  onReferenceMeanChange,
  onResponseColumnChange,
  onRun,
  onUpperBoundChange,
}: EquivalenceTostPanelProps) {
  const confidenceLevel = 1 - 2 * alpha;
  const canRun =
    version !== null &&
    responseColumnId !== null &&
    Number.isFinite(referenceMean) &&
    Number.isFinite(lowerBound) &&
    Number.isFinite(upperBound) &&
    lowerBound < upperBound &&
    alpha > 0 &&
    alpha < 0.5 &&
    filterValidationError === null;

  return (
    <section className="analysis-run-panel" aria-labelledby="equivalence-tost-title">
      <div className="panel-heading">
        <div>
          <h3 id="equivalence-tost-title">동등성 검정 실행</h3>
          <p>{methodId}</p>
        </div>
        <span className="status-pill status-ready">사용 가능</span>
      </div>
      {version === null ? (
        <div className="notice-box">데이터셋 버전 생성 후 실행할 수 있습니다.</div>
      ) : (
        <>
          <div className="option-grid">
            <label>
              <span>반응 변수</span>
              <select
                value={responseColumnId ?? ""}
                onChange={(event) => {
                  onResponseColumnChange(event.currentTarget.value);
                }}
              >
                <option value="">선택</option>
                {responseColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>기준 평균</span>
              <input
                step="any"
                type="number"
                value={referenceMean}
                onChange={(event) => {
                  onReferenceMeanChange(Number(event.currentTarget.value));
                }}
              />
            </label>
            <label>
              <span>동등성 하한</span>
              <input
                step="any"
                type="number"
                value={lowerBound}
                onChange={(event) => {
                  onLowerBoundChange(Number(event.currentTarget.value));
                }}
              />
            </label>
            <label>
              <span>동등성 상한</span>
              <input
                step="any"
                type="number"
                value={upperBound}
                onChange={(event) => {
                  onUpperBoundChange(Number(event.currentTarget.value));
                }}
              />
            </label>
            <label>
              <span>유의수준 alpha</span>
              <input
                max="0.499"
                min="0.001"
                step="0.001"
                type="number"
                value={alpha}
                onChange={(event) => {
                  onAlphaChange(Number(event.currentTarget.value));
                }}
              />
            </label>
            <div className="readonly-field">
              <span>TOST CI 수준</span>
              <strong>{formatPercent(confidenceLevel)}</strong>
            </div>
          </div>
          <button
            className="primary-button"
            disabled={isRunningAnalysis || !canRun}
            onClick={() => {
              onRun();
            }}
            type="button"
          >
            {isRunningAnalysis ? "실행 중" : "동등성 검정 실행"}
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
              <div className="metadata-grid" aria-label="동등성 검정 요약">
                <span>반응 변수</span>
                <strong>{result.response.display_name}</strong>
                <span>사용 N</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>평균 차이</span>
                <strong>{formatAnalysisNumber(result.estimate.value)}</strong>
                <span>동등성 판정</span>
                <strong>{result.tost.equivalent ? "동등성 근거 있음" : "동등성 근거 부족"}</strong>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>검정</th>
                      <th>한계</th>
                      <th>t</th>
                      <th>df</th>
                      <th>p-value</th>
                      <th>결정</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>하한 단측</td>
                      <td>{formatAnalysisNumber(result.tests.lower.bound)}</td>
                      <td>{formatAnalysisNumber(result.tests.lower.statistic)}</td>
                      <td>{formatAnalysisNumber(result.tests.lower.df)}</td>
                      <td>{formatAnalysisNumber(result.tests.lower.p_value)}</td>
                      <td>{result.tests.lower.reject_null ? "기각" : "기각 안 함"}</td>
                    </tr>
                    <tr>
                      <td>상한 단측</td>
                      <td>{formatAnalysisNumber(result.tests.upper.bound)}</td>
                      <td>{formatAnalysisNumber(result.tests.upper.statistic)}</td>
                      <td>{formatAnalysisNumber(result.tests.upper.df)}</td>
                      <td>{formatAnalysisNumber(result.tests.upper.p_value)}</td>
                      <td>{result.tests.upper.reject_null ? "기각" : "기각 안 함"}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="metadata-grid" aria-label="동등성 한계와 신뢰구간">
                <span>동등성 구간</span>
                <strong>
                  {formatAnalysisNumber(result.equivalence_bounds.lower)} ~{" "}
                  {formatAnalysisNumber(result.equivalence_bounds.upper)}
                </strong>
                <span>{formatPercent(result.confidence_interval.level)} CI</span>
                <strong>
                  {formatAnalysisNumber(result.confidence_interval.lower)} ~{" "}
                  {formatAnalysisNumber(result.confidence_interval.upper)}
                </strong>
                <span>TOST p-value</span>
                <strong>{formatAnalysisNumber(result.tost.p_value)}</strong>
                <span>Cohen dz</span>
                <strong>{formatAnalysisNumber(result.effect_size.cohen_dz)}</strong>
              </div>
            </>
          ) : null}
        </>
      )}
    </section>
  );
}

function formatPercent(value: number): string {
  if (!Number.isFinite(value)) {
    return "-";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 1,
    style: "percent",
  }).format(value);
}

function formatAnalysisNumber(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "-";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 6,
  }).format(value);
}
