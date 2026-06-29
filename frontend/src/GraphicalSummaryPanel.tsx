import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  GraphicalSummaryResult,
} from "./api";

interface GraphicalSummaryPanelProps {
  analysisResult: AnalysisResultEnvelope | null;
  filterValidationError: string | null;
  graphicalColumns: DatasetColumnResponse[];
  graphicalResult: GraphicalSummaryResult | null;
  isRunningAnalysis: boolean;
  methodId: string;
  selectedColumnIds: string[];
  version: DatasetVersionResponse | null;
  onRun: () => void;
  onToggleColumn: (columnId: string, checked: boolean) => void;
}

const maxGraphicalColumns = 20;

export function GraphicalSummaryPanel({
  analysisResult,
  filterValidationError,
  graphicalColumns,
  graphicalResult,
  isRunningAnalysis,
  methodId,
  selectedColumnIds,
  version,
  onRun,
  onToggleColumn,
}: GraphicalSummaryPanelProps) {
  return (
    <section className="analysis-run-panel" aria-labelledby="graphical-summary-title">
      <div className="panel-heading">
        <div>
          <h3 id="graphical-summary-title">그래프 요약 실행</h3>
          <p>{methodId}</p>
        </div>
        <span className="status-pill status-ready">사용 가능</span>
      </div>
      {version === null ? (
        <div className="notice-box">데이터셋 버전 생성 후 실행할 수 있습니다.</div>
      ) : (
        <>
          <div className="column-picker" aria-label="그래프 요약 컬럼 선택">
            {graphicalColumns.map((column) => (
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
              selectedColumnIds.length > maxGraphicalColumns ||
              filterValidationError !== null
            }
            onClick={() => {
              onRun();
            }}
            type="button"
          >
            {isRunningAnalysis ? "실행 중" : "그래프 요약 실행"}
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
          {graphicalResult !== null ? (
            <div className="table-wrap">
              <table className="result-table">
                <thead>
                  <tr>
                    <th>컬럼</th>
                    <th>N</th>
                    <th>결측</th>
                    <th>최소</th>
                    <th>Q1</th>
                    <th>중앙값</th>
                    <th>Q3</th>
                    <th>최대</th>
                    <th>Bins</th>
                    <th>Outliers</th>
                    <th>Q-Q</th>
                    <th>ECDF</th>
                  </tr>
                </thead>
                <tbody>
                  {graphicalResult.columns.map((column) => (
                    <tr key={column.column_id}>
                      <td>{column.display_name}</td>
                      <td>{column.n_used}</td>
                      <td>{column.n_missing}</td>
                      <td>{formatAnalysisNumber(column.min)}</td>
                      <td>{formatAnalysisNumber(column.q1)}</td>
                      <td>{formatAnalysisNumber(column.median)}</td>
                      <td>{formatAnalysisNumber(column.q3)}</td>
                      <td>{formatAnalysisNumber(column.max)}</td>
                      <td>{column.histogram.bin_count}</td>
                      <td>{column.boxplot.outlier_count}</td>
                      <td>{column.qq_plot.point_count}</td>
                      <td>{column.ecdf.point_count}</td>
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
