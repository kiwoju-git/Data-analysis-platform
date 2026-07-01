import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  OneSampleTResult,
} from "./api";

interface OneSampleTPanelProps {
  alpha: number;
  alternative: string;
  analysisResult: AnalysisResultEnvelope | null;
  confidenceLevel: number;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  methodId: string;
  nullMean: number;
  responseColumnId: string | null;
  responseColumns: DatasetColumnResponse[];
  result: OneSampleTResult | null;
  version: DatasetVersionResponse | null;
  onAlphaChange: (alpha: number) => void;
  onAlternativeChange: (alternative: string) => void;
  onConfidenceLevelChange: (confidenceLevel: number) => void;
  onNullMeanChange: (nullMean: number) => void;
  onResponseColumnChange: (columnId: string) => void;
  onRun: () => void;
}

export function OneSampleTPanel({
  alpha,
  alternative,
  analysisResult,
  confidenceLevel,
  filterValidationError,
  isRunningAnalysis,
  methodId,
  nullMean,
  responseColumnId,
  responseColumns,
  result,
  version,
  onAlphaChange,
  onAlternativeChange,
  onConfidenceLevelChange,
  onNullMeanChange,
  onResponseColumnChange,
  onRun,
}: OneSampleTPanelProps) {
  const canRun =
    version !== null &&
    responseColumnId !== null &&
    alpha > 0 &&
    alpha < 1 &&
    confidenceLevel > 0 &&
    confidenceLevel < 1 &&
    Number.isFinite(nullMean) &&
    filterValidationError === null;

  return (
    <section className="analysis-run-panel" aria-labelledby="one-sample-t-title">
      <div className="panel-heading">
        <div>
          <h3 id="one-sample-t-title">1-표본 t-검정 실행</h3>
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
                value={nullMean}
                onChange={(event) => {
                  onNullMeanChange(Number(event.currentTarget.value));
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
                <option value="greater">평균 - 기준 &gt; 0</option>
                <option value="less">평균 - 기준 &lt; 0</option>
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
            {isRunningAnalysis ? "실행 중" : "1-표본 t-검정 실행"}
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
              <div className="metadata-grid" aria-label="1-표본 t-검정 요약">
                <span>반응 변수</span>
                <strong>{result.response.display_name}</strong>
                <span>사용 N</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>기준 평균</span>
                <strong>{formatAnalysisNumber(result.null_mean)}</strong>
                <span>표본 평균</span>
                <strong>{formatAnalysisNumber(result.sample.mean)}</strong>
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
            </>
          ) : null}
        </>
      )}
    </section>
  );
}

function confidenceIntervalLabel(result: OneSampleTResult): string {
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
