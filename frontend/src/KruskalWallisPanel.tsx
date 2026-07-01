import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  KruskalWallisResult,
} from "./api";

interface KruskalWallisPanelProps {
  alpha: number;
  analysisResult: AnalysisResultEnvelope | null;
  filterValidationError: string | null;
  groupColumnId: string | null;
  groupColumns: DatasetColumnResponse[];
  isRunningAnalysis: boolean;
  methodId: string;
  responseColumnId: string | null;
  responseColumns: DatasetColumnResponse[];
  result: KruskalWallisResult | null;
  version: DatasetVersionResponse | null;
  onAlphaChange: (alpha: number) => void;
  onGroupColumnChange: (columnId: string) => void;
  onResponseColumnChange: (columnId: string) => void;
  onRun: () => void;
}

export function KruskalWallisPanel({
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
}: KruskalWallisPanelProps) {
  const canRun =
    version !== null &&
    responseColumnId !== null &&
    groupColumnId !== null &&
    responseColumnId !== groupColumnId &&
    alpha > 0 &&
    alpha < 1 &&
    filterValidationError === null;

  return (
    <section className="analysis-run-panel" aria-labelledby="kruskal-wallis-title">
      <div className="panel-heading">
        <div>
          <h3 id="kruskal-wallis-title">Kruskal-Wallis 실행</h3>
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
            <div className="option-note">
              Dunn 사후검정은 overall 검정이 유의한 경우에만 Holm 보정과 함께 실행합니다.
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
            {isRunningAnalysis ? "실행 중" : "Kruskal-Wallis 실행"}
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
              <div className="metadata-grid" aria-label="Kruskal-Wallis 요약">
                <span>사용 N</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>그룹 수</span>
                <strong>{result.group_count.toLocaleString()}</strong>
                <span>동률</span>
                <strong>{result.has_ties ? "있음" : "없음"}</strong>
                <span>Dunn/Holm</span>
                <strong>{posthocLabel(result.posthoc.performed, result.posthoc.reason)}</strong>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>H</th>
                      <th>df</th>
                      <th>p-value</th>
                      <th>epsilon squared</th>
                      <th>결정</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{formatAnalysisNumber(result.test.h_statistic)}</td>
                      <td>{result.test.df}</td>
                      <td>{formatAnalysisNumber(result.test.p_value)}</td>
                      <td>
                        {formatAnalysisNumber(result.test.effect_size.epsilon_squared)}
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
                      <th>IQR</th>
                      <th>평균 rank</th>
                      <th>rank 합</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.groups.map((group) => (
                      <tr key={`${group.group_index}-${group.group_label}`}>
                        <td>{group.group_label}</td>
                        <td>{group.n}</td>
                        <td>{formatAnalysisNumber(group.median)}</td>
                        <td>{formatAnalysisNumber(group.iqr)}</td>
                        <td>{formatAnalysisNumber(group.mean_rank)}</td>
                        <td>{formatAnalysisNumber(group.rank_sum)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {result.posthoc.comparisons.length > 0 ? (
                <div className="table-wrap">
                  <table className="result-table">
                    <thead>
                      <tr>
                        <th>비교</th>
                        <th>rank 차이</th>
                        <th>z</th>
                        <th>raw p</th>
                        <th>Holm p</th>
                        <th>결정</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.posthoc.comparisons.map((comparison) => (
                        <tr
                          key={`${comparison.group_1_label}-${comparison.group_2_label}`}
                        >
                          <td>
                            {comparison.group_1_label} vs {comparison.group_2_label}
                          </td>
                          <td>
                            {formatAnalysisNumber(comparison.mean_rank_difference)}
                          </td>
                          <td>{formatAnalysisNumber(comparison.z_statistic)}</td>
                          <td>{formatAnalysisNumber(comparison.raw_p_value)}</td>
                          <td>{formatAnalysisNumber(comparison.adjusted_p_value)}</td>
                          <td>{comparison.reject_holm ? "기각" : "기각 안 함"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </>
          ) : null}
        </>
      )}
    </section>
  );
}

function posthocLabel(performed: boolean, reason: string | null): string {
  if (performed) {
    return "실행됨";
  }
  if (reason === "overall_not_significant") {
    return "overall 비유의로 생략";
  }
  if (reason === "not_requested") {
    return "요청 안 함";
  }
  return "생략";
}

function formatAnalysisNumber(value: number | null): string {
  if (value === null) {
    return "-";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumSignificantDigits: 6,
  }).format(value);
}
