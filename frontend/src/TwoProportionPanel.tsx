import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  TwoProportionResult,
} from "./api";

interface TwoProportionPanelProps {
  alpha: number;
  alternative: string;
  analysisResult: AnalysisResultEnvelope | null;
  confidenceLevel: number;
  eventLevel: string;
  filterValidationError: string | null;
  groupColumnId: string | null;
  groupColumns: DatasetColumnResponse[];
  isRunningAnalysis: boolean;
  methodId: string;
  responseColumnId: string | null;
  responseColumns: DatasetColumnResponse[];
  result: TwoProportionResult | null;
  version: DatasetVersionResponse | null;
  onAlphaChange: (alpha: number) => void;
  onAlternativeChange: (alternative: string) => void;
  onConfidenceLevelChange: (confidenceLevel: number) => void;
  onEventLevelChange: (eventLevel: string) => void;
  onGroupColumnChange: (columnId: string) => void;
  onResponseColumnChange: (columnId: string) => void;
  onRun: () => void;
}

export function TwoProportionPanel({
  alpha,
  alternative,
  analysisResult,
  confidenceLevel,
  eventLevel,
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
  onAlternativeChange,
  onConfidenceLevelChange,
  onEventLevelChange,
  onGroupColumnChange,
  onResponseColumnChange,
  onRun,
}: TwoProportionPanelProps) {
  const canRun =
    version !== null &&
    responseColumnId !== null &&
    groupColumnId !== null &&
    responseColumnId !== groupColumnId &&
    eventLevel.trim().length > 0 &&
    alpha > 0 &&
    alpha < 1 &&
    confidenceLevel > 0 &&
    confidenceLevel < 1 &&
    filterValidationError === null;

  return (
    <section className="analysis-run-panel" aria-labelledby="two-proportion-title">
      <div className="panel-heading">
        <div>
          <h3 id="two-proportion-title">2-비율 검정 실행</h3>
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
              <span>이진 반응 변수</span>
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
              <span>사건 수준</span>
              <input
                type="text"
                value={eventLevel}
                onChange={(event) => {
                  onEventLevelChange(event.currentTarget.value);
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
                <option value="greater">그룹 1 &gt; 그룹 2</option>
                <option value="less">그룹 1 &lt; 그룹 2</option>
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
          </div>
          <button
            className="primary-button"
            disabled={isRunningAnalysis || !canRun}
            onClick={() => {
              onRun();
            }}
            type="button"
          >
            {isRunningAnalysis ? "실행 중" : "2-비율 검정 실행"}
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
              <div className="metadata-grid" aria-label="2-비율 검정 요약">
                <span>사건 수준</span>
                <strong>{result.event_level}</strong>
                <span>사용 N</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>CI 방식</span>
                <strong>Newcombe-Wilson</strong>
                <span>결측 제외</span>
                <strong>
                  {(
                    result.n_excluded_missing_response + result.n_excluded_missing_group
                  ).toLocaleString()}
                </strong>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>차이</th>
                      <th>CI</th>
                      <th>p-value</th>
                      <th>odds ratio</th>
                      <th>risk ratio</th>
                      <th>결정</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{formatAnalysisNumber(result.difference.estimate)}</td>
                      <td>
                        {formatAnalysisNumber(result.difference.confidence_interval.lower)} -{" "}
                        {formatAnalysisNumber(result.difference.confidence_interval.upper)}
                      </td>
                      <td>{formatAnalysisNumber(result.test.p_value)}</td>
                      <td>{formatAnalysisNumber(result.effect_sizes.odds_ratio.estimate)}</td>
                      <td>{formatAnalysisNumber(result.effect_sizes.risk_ratio.estimate)}</td>
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
                      <th>event</th>
                      <th>non-event</th>
                      <th>total</th>
                      <th>비율</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.groups.map((group) => (
                      <tr key={group.group_label}>
                        <td>{group.group_label}</td>
                        <td>{group.event_count}</td>
                        <td>{group.non_event_count}</td>
                        <td>{group.total}</td>
                        <td>{formatAnalysisNumber(group.sample_proportion)}</td>
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

function formatAnalysisNumber(value: number | null): string {
  if (value === null) {
    return "-";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumSignificantDigits: 6,
  }).format(value);
}
