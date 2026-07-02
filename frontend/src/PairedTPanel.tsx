import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  PairedTResult,
} from "./api";

interface PairedTPanelProps {
  afterColumnId: string | null;
  afterColumns: DatasetColumnResponse[];
  alpha: number;
  alternative: string;
  analysisResult: AnalysisResultEnvelope | null;
  beforeColumnId: string | null;
  beforeColumns: DatasetColumnResponse[];
  confidenceLevel: number;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  methodId: string;
  nullDifference: number;
  result: PairedTResult | null;
  version: DatasetVersionResponse | null;
  onAfterColumnChange: (columnId: string) => void;
  onAlphaChange: (alpha: number) => void;
  onAlternativeChange: (alternative: string) => void;
  onBeforeColumnChange: (columnId: string) => void;
  onConfidenceLevelChange: (confidenceLevel: number) => void;
  onNullDifferenceChange: (nullDifference: number) => void;
  onRun: () => void;
}

export function PairedTPanel({
  afterColumnId,
  afterColumns,
  alpha,
  alternative,
  analysisResult,
  beforeColumnId,
  beforeColumns,
  confidenceLevel,
  filterValidationError,
  isRunningAnalysis,
  methodId,
  nullDifference,
  result,
  version,
  onAfterColumnChange,
  onAlphaChange,
  onAlternativeChange,
  onBeforeColumnChange,
  onConfidenceLevelChange,
  onNullDifferenceChange,
  onRun,
}: PairedTPanelProps) {
  const canRun =
    version !== null &&
    beforeColumnId !== null &&
    afterColumnId !== null &&
    beforeColumnId !== afterColumnId &&
    alpha > 0 &&
    alpha < 1 &&
    confidenceLevel > 0 &&
    confidenceLevel < 1 &&
    Number.isFinite(nullDifference) &&
    filterValidationError === null;

  return (
    <section className="analysis-run-panel" aria-labelledby="paired-t-title">
      <div className="panel-heading">
        <div>
          <h3 id="paired-t-title">대응표본 t-검정 실행</h3>
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
              <span>첫 번째 측정</span>
              <select
                value={beforeColumnId ?? ""}
                onChange={(event) => {
                  onBeforeColumnChange(event.currentTarget.value);
                }}
              >
                <option value="">선택</option>
                {beforeColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>두 번째 측정</span>
              <select
                value={afterColumnId ?? ""}
                onChange={(event) => {
                  onAfterColumnChange(event.currentTarget.value);
                }}
              >
                <option value="">선택</option>
                {afterColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>기준 차이</span>
              <input
                step="any"
                type="number"
                value={nullDifference}
                onChange={(event) => {
                  onNullDifferenceChange(Number(event.currentTarget.value));
                }}
              />
            </label>
            <label>
              <span>대립가설</span>
              <select
                value={alternative}
                onChange={(event) => {
                  onAlternativeChange(event.currentTarget.value);
                }}
              >
                <option value="two_sided">양측</option>
                <option value="greater">두 번째 - 첫 번째 &gt; 기준</option>
                <option value="less">두 번째 - 첫 번째 &lt; 기준</option>
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
            {isRunningAnalysis ? "실행 중" : "대응표본 t-검정 실행"}
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
              <div className="metadata-grid" aria-label="대응표본 t-검정 요약">
                <span>첫 번째 측정</span>
                <strong>{result.before.display_name}</strong>
                <span>두 번째 측정</span>
                <strong>{result.after.display_name}</strong>
                <span>사용 pair</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>제외 pair</span>
                <strong>
                  {(result.n_incomplete_pairs + result.n_non_numeric_pairs).toLocaleString()}
                </strong>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>평균 차이</th>
                      <th>CI</th>
                      <th>t</th>
                      <th>df</th>
                      <th>p-value</th>
                      <th>Cohen dz</th>
                      <th>결정</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{formatAnalysisNumber(result.contrast.estimate)}</td>
                      <td>{confidenceIntervalLabel(result)}</td>
                      <td>{formatAnalysisNumber(result.contrast.statistic)}</td>
                      <td>{formatAnalysisNumber(result.contrast.df)}</td>
                      <td>{formatAnalysisNumber(result.contrast.p_value)}</td>
                      <td>{formatAnalysisNumber(result.contrast.effect_size.cohen_dz)}</td>
                      <td>{result.contrast.reject_null ? "기각" : "기각 안 함"}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>첫 번째 평균</th>
                      <th>두 번째 평균</th>
                      <th>차이 SD</th>
                      <th>차이 중앙값</th>
                      <th>양/음/0 차이</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{formatAnalysisNumber(result.paired_sample.before_mean)}</td>
                      <td>{formatAnalysisNumber(result.paired_sample.after_mean)}</td>
                      <td>{formatAnalysisNumber(result.paired_sample.difference_std)}</td>
                      <td>{formatAnalysisNumber(result.paired_sample.median_difference)}</td>
                      <td>
                        {result.paired_sample.positive_difference_count}/
                        {result.paired_sample.negative_difference_count}/
                        {result.paired_sample.zero_difference_count}
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

function confidenceIntervalLabel(result: PairedTResult): string {
  const { lower, upper } = result.contrast.confidence_interval;
  if (lower === null) {
    return `(-inf, ${formatAnalysisNumber(upper)})`;
  }
  if (upper === null) {
    return `(${formatAnalysisNumber(lower)}, inf)`;
  }
  return `${formatAnalysisNumber(lower)} ~ ${formatAnalysisNumber(upper)}`;
}

function formatAnalysisNumber(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "-";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 6,
  }).format(value);
}
