import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  EqualVariancesResult,
} from "./api";

interface EqualVariancesPanelProps {
  alpha: number;
  analysisResult: AnalysisResultEnvelope | null;
  filterValidationError: string | null;
  groupColumnId: string | null;
  groupColumns: DatasetColumnResponse[];
  isRunningAnalysis: boolean;
  methodId: string;
  responseColumnId: string | null;
  responseColumns: DatasetColumnResponse[];
  result: EqualVariancesResult | null;
  version: DatasetVersionResponse | null;
  onAlphaChange: (alpha: number) => void;
  onGroupColumnChange: (columnId: string) => void;
  onResponseColumnChange: (columnId: string) => void;
  onRun: () => void;
}

export function EqualVariancesPanel({
  alpha,
  analysisResult,
  filterValidationError,
  groupColumnId,
  groupColumns,
  isRunningAnalysis,
  methodId,
  responseColumnId,
  responseColumns,
  result,
  version,
  onAlphaChange,
  onGroupColumnChange,
  onResponseColumnChange,
  onRun,
}: EqualVariancesPanelProps) {
  const canRun =
    version !== null &&
    responseColumnId !== null &&
    groupColumnId !== null &&
    responseColumnId !== groupColumnId &&
    alpha > 0 &&
    alpha < 1 &&
    filterValidationError === null;

  return (
    <section className="analysis-run-panel" aria-labelledby="equal-variances-title">
      <div className="panel-heading">
        <div>
          <h3 id="equal-variances-title">등분산 검정 실행</h3>
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
            {isRunningAnalysis ? "실행 중" : "등분산 검정 실행"}
          </button>
          {responseColumnId !== null && responseColumnId === groupColumnId ? (
            <div className="error-box">반응 변수와 그룹 변수는 서로 달라야 합니다.</div>
          ) : null}
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
          {result !== null ? (
            <>
              <div className="metadata-grid" aria-label="등분산 검정 요약">
                <span>반응/그룹</span>
                <strong>
                  {result.response.display_name} / {result.group.display_name}
                </strong>
                <span>사용 N</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>그룹 수</span>
                <strong>{result.group_count.toLocaleString()}</strong>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>방법</th>
                      <th>중심</th>
                      <th>통계량</th>
                      <th>p-value</th>
                      <th>alpha</th>
                      <th>결정</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.tests.map((test) => (
                      <tr key={test.method}>
                        <td>{methodLabel(test.method)}</td>
                        <td>{centerLabel(test.center)}</td>
                        <td>{formatAnalysisNumber(test.statistic)}</td>
                        <td>{formatAnalysisNumber(test.p_value)}</td>
                        <td>{formatAnalysisNumber(test.alpha)}</td>
                        <td>{decisionLabel(test.reject_equal_variances)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>그룹</th>
                      <th>N</th>
                      <th>평균</th>
                      <th>중앙값</th>
                      <th>분산</th>
                      <th>표준편차</th>
                      <th>범위</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.groups.map((group) => (
                      <tr key={`${group.group_index}-${group.group_label}`}>
                        <td>{group.group_label}</td>
                        <td>{group.n}</td>
                        <td>{formatAnalysisNumber(group.mean)}</td>
                        <td>{formatAnalysisNumber(group.median)}</td>
                        <td>{formatAnalysisNumber(group.variance)}</td>
                        <td>{formatAnalysisNumber(group.std)}</td>
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
  if (method === "brown_forsythe") {
    return "Brown-Forsythe";
  }
  if (method === "levene_mean") {
    return "Levene";
  }
  return method;
}

function centerLabel(center: string): string {
  if (center === "median") {
    return "중앙값";
  }
  if (center === "mean") {
    return "평균";
  }
  return center;
}

function decisionLabel(rejectEqualVariances: boolean | null): string {
  if (rejectEqualVariances === null) {
    return "-";
  }
  return rejectEqualVariances ? "등분산 기각" : "기각 안 함";
}

function formatAnalysisNumber(value: number | null): string {
  if (value === null) {
    return "-";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumSignificantDigits: 6,
  }).format(value);
}
