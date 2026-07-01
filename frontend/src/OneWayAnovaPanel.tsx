import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  OneWayAnovaResult,
} from "./api";

interface OneWayAnovaPanelProps {
  alpha: number;
  analysisResult: AnalysisResultEnvelope | null;
  confidenceLevel: number;
  filterValidationError: string | null;
  groupColumnId: string | null;
  groupColumns: DatasetColumnResponse[];
  isRunningAnalysis: boolean;
  methodId: string;
  responseColumnId: string | null;
  responseColumns: DatasetColumnResponse[];
  result: OneWayAnovaResult | null;
  version: DatasetVersionResponse | null;
  onAlphaChange: (alpha: number) => void;
  onConfidenceLevelChange: (confidenceLevel: number) => void;
  onGroupColumnChange: (columnId: string) => void;
  onResponseColumnChange: (columnId: string) => void;
  onRun: () => void;
}

export function OneWayAnovaPanel({
  alpha,
  analysisResult,
  confidenceLevel,
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
  onConfidenceLevelChange,
  onGroupColumnChange,
  onResponseColumnChange,
  onRun,
}: OneWayAnovaPanelProps) {
  const canRun =
    version !== null &&
    responseColumnId !== null &&
    groupColumnId !== null &&
    responseColumnId !== groupColumnId &&
    alpha > 0 &&
    alpha < 1 &&
    confidenceLevel > 0 &&
    confidenceLevel < 1 &&
    filterValidationError === null;

  return (
    <section className="analysis-run-panel" aria-labelledby="one-way-anova-title">
      <div className="panel-heading">
        <div>
          <h3 id="one-way-anova-title">일원분산분석 실행</h3>
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
            <label>
              <span>신뢰수준</span>
              <input
                max="0.999"
                min="0.001"
                step="0.001"
                type="number"
                value={confidenceLevel}
                onChange={(event) => {
                  onConfidenceLevelChange(Number(event.currentTarget.value));
                }}
              />
            </label>
            <div className="option-note">
              표준 ANOVA가 유의한 경우에만 Tukey-Kramer 사후비교를 실행합니다.
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
            {isRunningAnalysis ? "실행 중" : "일원분산분석 실행"}
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
              <div className="metadata-grid" aria-label="일원분산분석 요약">
                <span>사용 N</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>그룹 수</span>
                <strong>{result.group_count.toLocaleString()}</strong>
                <span>ANOVA</span>
                <strong>standard</strong>
                <span>Tukey-Kramer</span>
                <strong>{posthocLabel(result.posthoc.performed, result.posthoc.reason)}</strong>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>F</th>
                      <th>df</th>
                      <th>p-value</th>
                      <th>omega squared</th>
                      <th>eta squared</th>
                      <th>결정</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{formatAnalysisNumber(result.test.f_statistic)}</td>
                      <td>
                        {result.test.df_between}, {result.test.df_within}
                      </td>
                      <td>{formatAnalysisNumber(result.test.p_value)}</td>
                      <td>
                        {formatAnalysisNumber(result.test.effect_size.omega_squared)}
                      </td>
                      <td>{formatAnalysisNumber(result.test.effect_size.eta_squared)}</td>
                      <td>{result.test.reject_null ? "기각" : "기각 안 함"}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>source</th>
                      <th>SS</th>
                      <th>df</th>
                      <th>MS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.anova_table.rows.map((row) => (
                      <tr key={row.source}>
                        <td>{row.source}</td>
                        <td>{formatAnalysisNumber(row.sum_squares)}</td>
                        <td>{row.df}</td>
                        <td>{formatAnalysisNumber(row.mean_square)}</td>
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
                      <th>SD</th>
                      <th>평균 CI</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.groups.map((group) => (
                      <tr key={`${group.group_index}-${group.group_label}`}>
                        <td>{group.group_label}</td>
                        <td>{group.n}</td>
                        <td>{formatAnalysisNumber(group.mean)}</td>
                        <td>{formatAnalysisNumber(group.std)}</td>
                        <td>
                          {formatAnalysisNumber(group.mean_confidence_interval.lower)} -{" "}
                          {formatAnalysisNumber(group.mean_confidence_interval.upper)}
                        </td>
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
                        <th>평균 차이</th>
                        <th>CI</th>
                        <th>raw p</th>
                        <th>Tukey p</th>
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
                          <td>{formatAnalysisNumber(comparison.mean_difference)}</td>
                          <td>
                            {formatAnalysisNumber(comparison.confidence_interval.lower)} -{" "}
                            {formatAnalysisNumber(comparison.confidence_interval.upper)}
                          </td>
                          <td>{formatAnalysisNumber(comparison.raw_p_value)}</td>
                          <td>{formatAnalysisNumber(comparison.adjusted_p_value)}</td>
                          <td>{comparison.reject_adjusted ? "기각" : "기각 안 함"}</td>
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
    return "overall 비유의";
  }
  if (reason === "not_requested") {
    return "요청 안 함";
  }
  return "대기";
}

function formatAnalysisNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "-";
  }
  if (!Number.isFinite(value)) {
    return "-";
  }
  if (Math.abs(value) >= 1000 || (Math.abs(value) > 0 && Math.abs(value) < 0.001)) {
    return value.toExponential(3);
  }
  return value.toLocaleString(undefined, {
    maximumFractionDigits: 6,
  });
}
