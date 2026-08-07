import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  EqualVarianceTestResult,
  EqualVariancesResult,
} from "./api";
import { InteractiveVarianceComparisonIntervalsChart } from "./charts/InteractiveVarianceComparisonIntervalsChart";

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
    <section className="analysis-run-panel" data-analysis-execution={methodId}>
      {version === null ? (
        <div className="notice-box">데이터셋 버전을 생성한 뒤 실행할 수 있습니다.</div>
      ) : (
        <>
          <div className="option-grid">
            <label>
              <span>반응 변수</span>
              <select value={responseColumnId ?? ""} onChange={(event) => onResponseColumnChange(event.currentTarget.value)}>
                <option value="">선택</option>
                {responseColumns.map((column) => <option key={column.column_id} value={column.column_id}>{column.display_name}</option>)}
              </select>
            </label>
            <label>
              <span>그룹 변수</span>
              <select value={groupColumnId ?? ""} onChange={(event) => onGroupColumnChange(event.currentTarget.value)}>
                <option value="">선택</option>
                {groupColumns.map((column) => <option key={column.column_id} value={column.column_id}>{column.display_name}</option>)}
              </select>
            </label>
            <label>
              <span>유의수준 alpha</span>
              <input max="0.5" min="0.001" step="0.001" type="number" value={alpha} onChange={(event) => onAlphaChange(Number(event.currentTarget.value))} />
            </label>
          </div>
          <button className="primary-button" disabled={isRunningAnalysis || !canRun} onClick={onRun} type="button">
            {isRunningAnalysis ? "실행 중" : "등분산 검정 실행"}
          </button>
          {responseColumnId !== null && responseColumnId === groupColumnId ? (
            <div className="error-box">반응 변수와 그룹 변수는 서로 달라야 합니다.</div>
          ) : null}
          {analysisResult?.provenance.row_count_included !== undefined && analysisResult.provenance.row_count_included !== null ? (
            <div className="metadata-grid" aria-label="분석 사용 행">
              <span>사용 행</span>
              <strong>{analysisResult.provenance.row_count_included.toLocaleString()} / {(analysisResult.provenance.row_count_total ?? analysisResult.provenance.row_count_included).toLocaleString()}</strong>
            </div>
          ) : null}
          {analysisResult?.warnings.length ? (
            <ul className="warning-list" aria-label="분석 경고">
              {analysisResult.warnings.map((warning, index) => <li key={`${warning.code}-${index}`}>{warning.message}</li>)}
            </ul>
          ) : null}
          {result !== null ? <EqualVarianceResults result={result} /> : null}
        </>
      )}
    </section>
  );
}

function EqualVarianceResults({ result }: { result: EqualVariancesResult }) {
  const isCurrent = result.schema_version >= 2 && result.multiple_comparisons && result.levene;
  return (
    <>
      <div className="metadata-grid" aria-label="등분산 검정 요약">
        <span>반응 / 그룹</span><strong>{result.response.display_name} / {result.group.display_name}</strong>
        <span>사용 N</span><strong>{result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}</strong>
        <span>그룹 수</span><strong>{result.group_count.toLocaleString()}</strong>
      </div>
      <div className="table-wrap">
        <table className="result-table equal-variances-method-table">
          <thead><tr><th>방법</th><th>검정 통계량</th><th>p-value</th><th>alpha</th><th>해석</th></tr></thead>
          <tbody>
            {isCurrent ? (
              <>
                <tr>
                  <td>다중 비교</td><td>-</td>
                  <td>{formatAnalysisNumber(result.multiple_comparisons!.p_value)}</td>
                  <td>{formatAnalysisNumber(result.multiple_comparisons!.alpha)}</td>
                  <td>{decisionLabel(result.multiple_comparisons!.reject_equal_variances)}</td>
                </tr>
                <TestRow label="Levene 검정 (Brown-Forsythe)" test={result.levene!} />
              </>
            ) : result.tests.map((test) => <TestRow key={test.method} label={legacyMethodLabel(test)} test={test} />)}
          </tbody>
        </table>
      </div>
      {isCurrent && result.multiple_comparisons!.computed ? (
        <section className="result-section equal-variances-interval-section">
          <h4>표준편차 다중 비교구간</h4>
          <p>다중 비교구간 · alpha = {formatAnalysisNumber(result.alpha)}</p>
          <InteractiveVarianceComparisonIntervalsChart
            chartId="equal-variances-comparison-intervals"
            groupName={result.group.display_name}
            result={result.multiple_comparisons!}
            responseName={result.response.display_name}
          />
          <div className="notice-box">
            다중 비교 방법이 연구에 적합한 경우, 두 구간이 겹치지 않으면 해당 두 그룹의 표준편차 차이가 유의하다고 해석합니다. 작은 표본의 매우 치우치거나 꼬리가 두꺼운 데이터에서 Levene 방법을 기준으로 판단한다면 이 구간으로 개별 쌍을 판단하지 마세요.
          </div>
        </section>
      ) : null}
      {isCurrent && result.additional_tests?.length ? (
        <details className="technical-details">
          <summary>추가 검정</summary>
          <div className="table-wrap"><table className="result-table"><thead><tr><th>방법</th><th>중심</th><th>통계량</th><th>p-value</th></tr></thead><tbody>
            {result.additional_tests.map((test) => <tr key={test.method}><td>고전 Levene 검정 (평균 중심)</td><td>평균</td><td>{formatAnalysisNumber(test.statistic)}</td><td>{formatAnalysisNumber(test.p_value)}</td></tr>)}
          </tbody></table></div>
        </details>
      ) : null}
      <div className="table-wrap">
        <table className="result-table"><thead><tr><th>그룹</th><th>N</th><th>평균</th><th>중앙값</th><th>분산</th><th>표준편차</th><th>범위</th></tr></thead><tbody>
          {result.groups.map((group) => <tr key={`${group.group_index}-${group.group_label}`}><td>{group.group_label}</td><td>{group.n}</td><td>{formatAnalysisNumber(group.mean)}</td><td>{formatAnalysisNumber(group.median)}</td><td>{formatAnalysisNumber(group.variance)}</td><td>{formatAnalysisNumber(group.std)}</td><td>{formatAnalysisNumber(group.min)} - {formatAnalysisNumber(group.max)}</td></tr>)}
        </tbody></table>
      </div>
    </>
  );
}

function TestRow({ label, test }: { label: string; test: EqualVarianceTestResult }) {
  return <tr><td>{label}</td><td>{formatAnalysisNumber(test.statistic)}</td><td>{formatAnalysisNumber(test.p_value)}</td><td>{formatAnalysisNumber(test.alpha)}</td><td>{decisionLabel(test.reject_equal_variances)}</td></tr>;
}

function legacyMethodLabel(test: EqualVarianceTestResult): string {
  if (test.method === "brown_forsythe") return "Brown-Forsythe";
  if (test.method === "levene_mean") return "Levene (평균 중심, legacy)";
  return test.method;
}

function decisionLabel(rejectEqualVariances: boolean | null): string {
  if (rejectEqualVariances === null) return "계산 불가";
  return rejectEqualVariances ? "등분산 기각" : "기각하지 않음";
}

function formatAnalysisNumber(value: number | null): string {
  if (value === null) return "-";
  return new Intl.NumberFormat("ko-KR", { maximumSignificantDigits: 7 }).format(value);
}
