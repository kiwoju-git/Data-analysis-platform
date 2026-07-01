import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  OneProportionResult,
} from "./api";

interface OneProportionPanelProps {
  alpha: number;
  alternative: string;
  analysisResult: AnalysisResultEnvelope | null;
  ciMethod: string;
  confidenceLevel: number;
  eventLevel: string;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  methodId: string;
  nullProportion: number;
  responseColumnId: string | null;
  responseColumns: DatasetColumnResponse[];
  result: OneProportionResult | null;
  version: DatasetVersionResponse | null;
  onAlphaChange: (alpha: number) => void;
  onAlternativeChange: (alternative: string) => void;
  onCiMethodChange: (ciMethod: string) => void;
  onConfidenceLevelChange: (confidenceLevel: number) => void;
  onEventLevelChange: (eventLevel: string) => void;
  onNullProportionChange: (nullProportion: number) => void;
  onResponseColumnChange: (columnId: string) => void;
  onRun: () => void;
}

export function OneProportionPanel({
  alpha,
  alternative,
  analysisResult,
  ciMethod,
  confidenceLevel,
  eventLevel,
  filterValidationError,
  isRunningAnalysis,
  methodId,
  nullProportion,
  responseColumnId,
  responseColumns,
  result,
  version,
  onAlphaChange,
  onAlternativeChange,
  onCiMethodChange,
  onConfidenceLevelChange,
  onEventLevelChange,
  onNullProportionChange,
  onResponseColumnChange,
  onRun,
}: OneProportionPanelProps) {
  const canRun =
    version !== null &&
    responseColumnId !== null &&
    eventLevel.trim().length > 0 &&
    nullProportion > 0 &&
    nullProportion < 1 &&
    alpha > 0 &&
    alpha < 1 &&
    confidenceLevel > 0 &&
    confidenceLevel < 1 &&
    filterValidationError === null;

  return (
    <section className="analysis-run-panel" aria-labelledby="one-proportion-title">
      <div className="panel-heading">
        <div>
          <h3 id="one-proportion-title">1-비율 검정 실행</h3>
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
              <span>기준 비율 p0</span>
              <input
                max="0.999"
                min="0.001"
                step="0.001"
                type="number"
                value={nullProportion}
                onChange={(event) => {
                  onNullProportionChange(Number(event.currentTarget.value));
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
                <option value="greater">p &gt; p0</option>
                <option value="less">p &lt; p0</option>
              </select>
            </label>
            <label>
              <span>신뢰구간</span>
              <select
                value={ciMethod}
                onChange={(event) => {
                  onCiMethodChange(event.currentTarget.value);
                }}
              >
                <option value="wilson">Wilson score</option>
                <option value="clopper_pearson">Clopper-Pearson exact</option>
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
            {isRunningAnalysis ? "실행 중" : "1-비율 검정 실행"}
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
              <div className="metadata-grid" aria-label="1-비율 검정 요약">
                <span>사건 수준</span>
                <strong>{result.event_level}</strong>
                <span>사용 N</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>CI 방식</span>
                <strong>{ciMethodLabel(result.ci_method)}</strong>
                <span>결측 제외</span>
                <strong>{result.n_missing.toLocaleString()}</strong>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>event</th>
                      <th>total</th>
                      <th>비율</th>
                      <th>차이 p-p0</th>
                      <th>CI</th>
                      <th>p-value</th>
                      <th>Cohen h</th>
                      <th>결정</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{result.sample.event_count}</td>
                      <td>{result.sample.total}</td>
                      <td>{formatAnalysisNumber(result.sample.sample_proportion)}</td>
                      <td>
                        {formatAnalysisNumber(result.sample.difference_from_null)}
                      </td>
                      <td>
                        {formatAnalysisNumber(result.confidence_interval.lower)} -{" "}
                        {formatAnalysisNumber(result.confidence_interval.upper)}
                      </td>
                      <td>{formatAnalysisNumber(result.test.p_value)}</td>
                      <td>{formatAnalysisNumber(result.effect_size.cohen_h)}</td>
                      <td>{result.test.reject_null ? "기각" : "기각 안 함"}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>수준</th>
                      <th>count</th>
                      <th>event</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.levels.map((level) => (
                      <tr key={level.level}>
                        <td>{level.level}</td>
                        <td>{level.count}</td>
                        <td>{level.is_event ? "예" : "아니오"}</td>
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

function ciMethodLabel(method: string): string {
  if (method === "wilson") {
    return "Wilson score";
  }
  if (method === "clopper_pearson") {
    return "Clopper-Pearson exact";
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
