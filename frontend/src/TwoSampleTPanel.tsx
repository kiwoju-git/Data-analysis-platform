import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  TwoSampleTResult,
} from "./api";

interface TwoSampleTPanelProps {
  alpha: number;
  alternative: string;
  analysisResult: AnalysisResultEnvelope | null;
  confidenceLevel: number;
  filterValidationError: string | null;
  groupColumnId: string | null;
  groupColumns: DatasetColumnResponse[];
  isRunningAnalysis: boolean;
  methodId: string;
  responseColumnId: string | null;
  responseColumns: DatasetColumnResponse[];
  result: TwoSampleTResult | null;
  varianceAssumption: string;
  version: DatasetVersionResponse | null;
  onAlphaChange: (alpha: number) => void;
  onAlternativeChange: (alternative: string) => void;
  onConfidenceLevelChange: (confidenceLevel: number) => void;
  onGroupColumnChange: (columnId: string) => void;
  onResponseColumnChange: (columnId: string) => void;
  onRun: () => void;
  onVarianceAssumptionChange: (varianceAssumption: string) => void;
}

export function TwoSampleTPanel({
  alpha,
  alternative,
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
  varianceAssumption,
  version,
  onAlphaChange,
  onAlternativeChange,
  onConfidenceLevelChange,
  onGroupColumnChange,
  onResponseColumnChange,
  onRun,
  onVarianceAssumptionChange,
}: TwoSampleTPanelProps) {
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
    <section className="analysis-run-panel" aria-labelledby="two-sample-t-title">
      <div className="panel-heading">
        <div>
          <h3 id="two-sample-t-title">2-표본 t-검정 실행</h3>
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
              <span>분산 가정</span>
              <select
                value={varianceAssumption}
                onChange={(event) => {
                  onVarianceAssumptionChange(event.currentTarget.value);
                }}
              >
                <option value="welch">Welch 기본</option>
                <option value="pooled">Pooled Student</option>
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
                <option value="greater">그룹1 - 그룹2 &gt; 0</option>
                <option value="less">그룹1 - 그룹2 &lt; 0</option>
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
            {isRunningAnalysis ? "실행 중" : "2-표본 t-검정 실행"}
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
              <div className="metadata-grid" aria-label="2-표본 t-검정 요약">
                <span>비교 방향</span>
                <strong>
                  {result.contrast.group_1_label} - {result.contrast.group_2_label}
                </strong>
                <span>사용 N</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>방법</span>
                <strong>{methodLabel(result.variance_assumption)}</strong>
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
                      <th>Hedges g</th>
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
                      <td>{formatAnalysisNumber(result.contrast.effect_size.hedges_g)}</td>
                      <td>{result.contrast.reject_null ? "기각" : "기각 안 함"}</td>
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
                      <th>평균</th>
                      <th>표준편차</th>
                      <th>분산</th>
                      <th>범위</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.groups.map((group) => (
                      <tr key={`${group.group_index}-${group.group_label}`}>
                        <td>{group.group_label}</td>
                        <td>{group.n}</td>
                        <td>{formatAnalysisNumber(group.mean)}</td>
                        <td>{formatAnalysisNumber(group.std)}</td>
                        <td>{formatAnalysisNumber(group.variance)}</td>
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

function methodLabel(varianceAssumption: string): string {
  if (varianceAssumption === "welch") {
    return "Welch";
  }
  if (varianceAssumption === "pooled") {
    return "Pooled Student";
  }
  return varianceAssumption;
}

function confidenceIntervalLabel(result: TwoSampleTResult): string {
  const interval = result.contrast.confidence_interval;
  return `${formatAnalysisNumber(interval.lower)} - ${formatAnalysisNumber(interval.upper)}`;
}

function formatAnalysisNumber(value: number | null): string {
  if (value === null) {
    return "-";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumSignificantDigits: 6,
  }).format(value);
}
