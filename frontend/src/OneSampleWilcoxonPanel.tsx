import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  OneSampleWilcoxonResult,
} from "./api";

interface OneSampleWilcoxonPanelProps {
  alpha: number;
  alternative: string;
  analysisResult: AnalysisResultEnvelope | null;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  method: string;
  methodId: string;
  nullLocation: number;
  responseColumnId: string | null;
  responseColumns: DatasetColumnResponse[];
  result: OneSampleWilcoxonResult | null;
  version: DatasetVersionResponse | null;
  zeroMethod: string;
  onAlphaChange: (alpha: number) => void;
  onAlternativeChange: (alternative: string) => void;
  onMethodChange: (method: string) => void;
  onNullLocationChange: (nullLocation: number) => void;
  onResponseColumnChange: (columnId: string) => void;
  onRun: () => void;
  onZeroMethodChange: (zeroMethod: string) => void;
}

export function OneSampleWilcoxonPanel({
  alpha,
  alternative,
  analysisResult,
  filterValidationError,
  isRunningAnalysis,
  method,
  methodId,
  nullLocation,
  responseColumnId,
  responseColumns,
  result,
  version,
  zeroMethod,
  onAlphaChange,
  onAlternativeChange,
  onMethodChange,
  onNullLocationChange,
  onResponseColumnChange,
  onRun,
  onZeroMethodChange,
}: OneSampleWilcoxonPanelProps) {
  const canRun =
    version !== null &&
    responseColumnId !== null &&
    alpha > 0 &&
    alpha < 1 &&
    Number.isFinite(nullLocation) &&
    filterValidationError === null;

  return (
    <section className="analysis-run-panel" aria-labelledby="one-sample-wilcoxon-title">
      <div className="panel-heading">
        <div>
          <h3 id="one-sample-wilcoxon-title">1-표본 Wilcoxon 실행</h3>
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
              <span>기준 위치</span>
              <input
                step="any"
                type="number"
                value={nullLocation}
                onChange={(event) => {
                  onNullLocationChange(Number(event.currentTarget.value));
                }}
              />
            </label>
            <label>
              <span>p-value 방식</span>
              <select
                value={method}
                onChange={(event) => {
                  onMethodChange(event.currentTarget.value);
                }}
              >
                <option value="auto">자동</option>
                <option value="exact">Exact</option>
                <option value="asymptotic">Asymptotic</option>
              </select>
            </label>
            <label>
              <span>zero 처리</span>
              <select
                value={zeroMethod}
                onChange={(event) => {
                  onZeroMethodChange(event.currentTarget.value);
                }}
              >
                <option value="wilcox">wilcox</option>
                <option value="pratt">pratt</option>
                <option value="zsplit">zsplit</option>
              </select>
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
                <option value="greater">차이 &gt; 0</option>
                <option value="less">차이 &lt; 0</option>
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
          </div>
          <button
            className="primary-button"
            disabled={isRunningAnalysis || !canRun}
            onClick={() => {
              onRun();
            }}
            type="button"
          >
            {isRunningAnalysis ? "실행 중" : "1-표본 Wilcoxon 실행"}
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
              <div className="metadata-grid" aria-label="1-표본 Wilcoxon 요약">
                <span>반응 변수</span>
                <strong>{result.response.display_name}</strong>
                <span>사용 N</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>기준 위치</span>
                <strong>{formatAnalysisNumber(result.null_location)}</strong>
                <span>비zero N</span>
                <strong>{result.n_nonzero.toLocaleString()}</strong>
                <span>p-value 방식</span>
                <strong>{methodLabel(result.resolved_method)}</strong>
                <span>zero 처리</span>
                <strong>{result.zero_method}</strong>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>W</th>
                      <th>p-value</th>
                      <th>rank-biserial</th>
                      <th>양의 rank 합</th>
                      <th>음의 rank 합</th>
                      <th>결정</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{formatAnalysisNumber(result.test.w_statistic)}</td>
                      <td>{formatAnalysisNumber(result.test.p_value)}</td>
                      <td>
                        {formatAnalysisNumber(result.test.effect_size.rank_biserial)}
                      </td>
                      <td>{formatAnalysisNumber(result.test.positive_rank_sum)}</td>
                      <td>{formatAnalysisNumber(result.test.negative_rank_sum)}</td>
                      <td>{result.test.reject_null ? "기각" : "기각 안 함"}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>표본 중앙값</th>
                      <th>차이 중앙값</th>
                      <th>양의 차이</th>
                      <th>음의 차이</th>
                      <th>zero 차이</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{formatAnalysisNumber(result.sample.median)}</td>
                      <td>{formatAnalysisNumber(result.sample.median_difference)}</td>
                      <td>{result.sample.positive_difference_count}</td>
                      <td>{result.sample.negative_difference_count}</td>
                      <td>{result.sample.zero_difference_count}</td>
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

function methodLabel(method: string): string {
  if (method === "exact") {
    return "Exact";
  }
  if (method === "asymptotic") {
    return "Asymptotic";
  }
  return method;
}

function formatAnalysisNumber(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "-";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumSignificantDigits: 6,
  }).format(value);
}
