import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  DescriptiveStatisticsResult,
} from "./api";

interface DescriptiveAnalysisPanelProps {
  analysisResult: AnalysisResultEnvelope | null;
  descriptiveColumns: DatasetColumnResponse[];
  descriptiveResult: DescriptiveStatisticsResult | null;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  methodId: string;
  selectedColumnIds: string[];
  version: DatasetVersionResponse | null;
  onRun: () => void;
  onToggleColumn: (columnId: string, checked: boolean) => void;
}

export function DescriptiveAnalysisPanel({
  analysisResult,
  descriptiveColumns,
  descriptiveResult,
  filterValidationError,
  isRunningAnalysis,
  methodId,
  selectedColumnIds,
  version,
  onRun,
  onToggleColumn,
}: DescriptiveAnalysisPanelProps) {
  return (
    <section className="analysis-run-panel" aria-labelledby="descriptive-title">
      <div className="panel-heading">
        <div>
          <h3 id="descriptive-title">기술통계 실행</h3>
          <p>{methodId}</p>
        </div>
        <span className="status-pill status-ready">사용 가능</span>
      </div>
      {version === null ? (
        <div className="notice-box">데이터셋 버전 생성 후 실행할 수 있습니다.</div>
      ) : (
        <>
          <div className="column-picker" aria-label="기술통계 컬럼 선택">
            {descriptiveColumns.map((column) => (
              <label key={column.column_id}>
                <input
                  checked={selectedColumnIds.includes(column.column_id)}
                  type="checkbox"
                  onChange={(event) => {
                    onToggleColumn(column.column_id, event.currentTarget.checked);
                  }}
                />
                <span>{column.display_name}</span>
              </label>
            ))}
          </div>
          <button
            className="primary-button"
            disabled={
              isRunningAnalysis ||
              selectedColumnIds.length === 0 ||
              filterValidationError !== null
            }
            onClick={() => {
              onRun();
            }}
            type="button"
          >
            {isRunningAnalysis ? "실행 중" : "기술통계 실행"}
          </button>
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
          {descriptiveResult !== null ? (
            <div className="table-wrap">
              <table className="result-table">
                <thead>
                  <tr>
                    <th>컬럼</th>
                    <th>N</th>
                    <th>결측</th>
                    <th>평균</th>
                    <th>표준편차</th>
                    <th>최소</th>
                    <th>Q1</th>
                    <th>중앙값</th>
                    <th>Q3</th>
                    <th>최대</th>
                  </tr>
                </thead>
                <tbody>
                  {descriptiveResult.columns.map((column) => (
                    <tr key={column.column_id}>
                      <td>{column.display_name}</td>
                      <td>{column.n_used}</td>
                      <td>{column.n_missing}</td>
                      <td>{formatAnalysisNumber(column.mean)}</td>
                      <td>{formatAnalysisNumber(column.std)}</td>
                      <td>{formatAnalysisNumber(column.min)}</td>
                      <td>{formatAnalysisNumber(column.q1)}</td>
                      <td>{formatAnalysisNumber(column.median)}</td>
                      <td>{formatAnalysisNumber(column.q3)}</td>
                      <td>{formatAnalysisNumber(column.max)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
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
    maximumFractionDigits: 6,
  }).format(value);
}
