import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  MannWhitneyResult,
} from "./api";

interface MannWhitneyPanelProps {
  alpha: number;
  alternative: string;
  analysisResult: AnalysisResultEnvelope | null;
  filterValidationError: string | null;
  groupColumnId: string | null;
  groupColumns: DatasetColumnResponse[];
  isRunningAnalysis: boolean;
  method: string;
  methodId: string;
  responseColumnId: string | null;
  responseColumns: DatasetColumnResponse[];
  result: MannWhitneyResult | null;
  version: DatasetVersionResponse | null;
  onAlphaChange: (alpha: number) => void;
  onAlternativeChange: (alternative: string) => void;
  onGroupColumnChange: (columnId: string) => void;
  onMethodChange: (method: string) => void;
  onResponseColumnChange: (columnId: string) => void;
  onRun: () => void;
}

export function MannWhitneyPanel({
  alpha,
  alternative,
  analysisResult,
  filterValidationError,
  groupColumnId,
  groupColumns,
  isRunningAnalysis,
  method,
  methodId,
  responseColumnId,
  responseColumns,
  result,
  version,
  onAlphaChange,
  onAlternativeChange,
  onGroupColumnChange,
  onMethodChange,
  onResponseColumnChange,
  onRun,
}: MannWhitneyPanelProps) {
  const canRun =
    version !== null &&
    responseColumnId !== null &&
    groupColumnId !== null &&
    responseColumnId !== groupColumnId &&
    alpha > 0 &&
    alpha < 1 &&
    filterValidationError === null;

  return (
    <section className="analysis-run-panel" aria-labelledby="mann-whitney-title">
      <div className="panel-heading">
        <div>
          <h3 id="mann-whitney-title">Mann-Whitney U 실행</h3>
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
              <span>그룹 변수</span>
              <select
                value={groupColumnId ?? ""}
                onChange={(event) => {
                  onGroupColumnChange(event.currentTarget.value);
                }}
              >
                <option value="">선택</option>
                {groupColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
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
              <span>대립가설</span>
              <select
                value={alternative}
                onChange={(event) => {
                  onAlternativeChange(event.currentTarget.value);
                }}
              >
                <option value="two_sided">양측</option>
                <option value="greater">그룹1 &gt; 그룹2</option>
                <option value="less">그룹1 &lt; 그룹2</option>
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
            {isRunningAnalysis ? "실행 중" : "Mann-Whitney U 실행"}
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
              <div className="metadata-grid" aria-label="Mann-Whitney U 요약">
                <span>비교 방향</span>
                <strong>
                  {result.test.group_1_label} vs {result.test.group_2_label}
                </strong>
                <span>사용 N</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>p-value 방식</span>
                <strong>{methodLabel(result.resolved_method)}</strong>
                <span>동률</span>
                <strong>{result.has_ties ? "있음" : "없음"}</strong>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>U</th>
                      <th>p-value</th>
                      <th>rank-biserial</th>
                      <th>공통언어 확률</th>
                      <th>결정</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{formatAnalysisNumber(result.test.u_statistic)}</td>
                      <td>{formatAnalysisNumber(result.test.p_value)}</td>
                      <td>
                        {formatAnalysisNumber(result.test.effect_size.rank_biserial)}
                      </td>
                      <td>
                        {formatAnalysisNumber(
                          result.test.effect_size.common_language_probability,
                        )}
                      </td>
                      <td>{result.test.reject_null ? "기각" : "기각 안 함"}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>그룹</th>
                      <th>N</th>
                      <th>중앙값</th>
                      <th>평균 rank</th>
                      <th>rank 합</th>
                      <th>범위</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.groups.map((group) => (
                      <tr key={`${group.group_index}-${group.group_label}`}>
                        <td>{group.group_label}</td>
                        <td>{group.n}</td>
                        <td>{formatAnalysisNumber(group.median)}</td>
                        <td>{formatAnalysisNumber(group.mean_rank)}</td>
                        <td>{formatAnalysisNumber(group.rank_sum)}</td>
                        <td>
                          {formatAnalysisNumber(group.min)} -{" "}
                          {formatAnalysisNumber(group.max)}
                        </td>
                      </tr>
                    ))}
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
  if (value === null) {
    return "-";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumSignificantDigits: 6,
  }).format(value);
}
