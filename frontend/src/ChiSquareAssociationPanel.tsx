import type {
  AnalysisResultEnvelope,
  ChiSquareAssociationResult,
  DatasetColumnResponse,
  DatasetVersionResponse,
} from "./api";

interface ChiSquareAssociationPanelProps {
  alpha: number;
  analysisResult: AnalysisResultEnvelope | null;
  columnColumnId: string | null;
  columnColumns: DatasetColumnResponse[];
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  methodId: string;
  result: ChiSquareAssociationResult | null;
  rowColumnId: string | null;
  rowColumns: DatasetColumnResponse[];
  version: DatasetVersionResponse | null;
  onAlphaChange: (alpha: number) => void;
  onColumnColumnChange: (columnId: string) => void;
  onRowColumnChange: (columnId: string) => void;
  onRun: () => void;
}

export function ChiSquareAssociationPanel({
  alpha,
  analysisResult,
  columnColumnId,
  columnColumns,
  filterValidationError,
  isRunningAnalysis,
  methodId,
  result,
  rowColumnId,
  rowColumns,
  version,
  onAlphaChange,
  onColumnColumnChange,
  onRowColumnChange,
  onRun,
}: ChiSquareAssociationPanelProps) {
  const canRun =
    version !== null &&
    rowColumnId !== null &&
    columnColumnId !== null &&
    rowColumnId !== columnColumnId &&
    alpha > 0 &&
    alpha < 1 &&
    filterValidationError === null;

  return (
    <section className="analysis-run-panel" aria-labelledby="chi-square-title">
      <div className="panel-heading">
        <div>
          <h3 id="chi-square-title">카이제곱 독립성 검정 실행</h3>
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
              <span>행 변수</span>
              <select
                value={rowColumnId ?? ""}
                onChange={(event) => {
                  onRowColumnChange(event.currentTarget.value);
                }}
              >
                <option value="">선택</option>
                {rowColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>열 변수</span>
              <select
                value={columnColumnId ?? ""}
                onChange={(event) => {
                  onColumnColumnChange(event.currentTarget.value);
                }}
              >
                <option value="">선택</option>
                {columnColumns.map((column) => (
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
              Pearson 카이제곱만 계산하며 Fisher exact로 자동 전환하지 않습니다.
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
            {isRunningAnalysis ? "실행 중" : "카이제곱 검정 실행"}
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
              <div className="metadata-grid" aria-label="카이제곱 독립성 검정 요약">
                <span>사용 N</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>수준 수</span>
                <strong>
                  {result.row_levels.length} x {result.column_levels.length}
                </strong>
                <span>최소 기대도수</span>
                <strong>
                  {formatAnalysisNumber(result.expected_count_summary.min_expected)}
                </strong>
                <span>Cramer's V</span>
                <strong>{formatAnalysisNumber(result.effect_size.cramers_v)}</strong>
              </div>
              <div className="result-section" aria-label="카이제곱 잔차 Heatmap 결과">
                <div className="panel-heading">
                  <div>
                    <h4>표준화 잔차 Heatmap</h4>
                    <p>Observed vs expected · Pearson standardized residual</p>
                  </div>
                </div>
                <ChiSquareResidualHeatmap result={result} />
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>chi-square</th>
                      <th>df</th>
                      <th>p-value</th>
                      <th>결정</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{formatAnalysisNumber(result.test.statistic)}</td>
                      <td>{result.test.df}</td>
                      <td>{formatAnalysisNumber(result.test.p_value)}</td>
                      <td>{result.test.reject_null ? "기각" : "기각 안 함"}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>행</th>
                      {result.contingency_table.column_levels.map((columnLevel) => (
                        <th key={columnLevel}>{columnLevel}</th>
                      ))}
                      <th>합계</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.contingency_table.rows.map((row) => (
                      <tr key={row.row_level}>
                        <td>{row.row_level}</td>
                        {row.cells.map((cell) => (
                          <td key={`${row.row_level}-${cell.column_level}`}>
                            {cell.observed.toLocaleString()}
                            <span className="cell-subtext">
                              exp {formatAnalysisNumber(cell.expected)}
                            </span>
                          </td>
                        ))}
                        <td>{row.row_total.toLocaleString()}</td>
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

function ChiSquareResidualHeatmap({ result }: { result: ChiSquareAssociationResult }) {
  const gridTemplateColumns = `minmax(112px, 1.1fr) repeat(${result.contingency_table.column_levels.length}, minmax(108px, 1fr))`;

  return (
    <div
      className="heatmap-grid"
      role="grid"
      style={{ gridTemplateColumns }}
      aria-label="카이제곱 표준화 잔차 heatmap"
    >
      <div className="heatmap-axis-label heatmap-corner" role="columnheader">
        행 \\ 열
      </div>
      {result.contingency_table.column_levels.map((columnLevel) => (
        <div key={columnLevel} className="heatmap-axis-label" role="columnheader">
          {columnLevel}
        </div>
      ))}
      {result.contingency_table.rows.flatMap((row) => [
        <div key={`${row.row_level}-label`} className="heatmap-axis-label" role="rowheader">
          {row.row_level}
        </div>,
        ...row.cells.map((cell) => (
          <div
            key={`${row.row_level}-${cell.column_level}`}
            className="heatmap-cell"
            role="gridcell"
            style={residualCellStyle(cell.standardized_residual)}
            title={`${row.row_level} / ${cell.column_level}: residual ${formatAnalysisNumber(
              cell.standardized_residual,
            )}`}
          >
            <strong>{formatAnalysisNumber(cell.standardized_residual)}</strong>
            <span>
              obs {cell.observed.toLocaleString()} · exp {formatAnalysisNumber(cell.expected)}
            </span>
          </div>
        )),
      ])}
    </div>
  );
}

function residualCellStyle(value: number | null): { backgroundColor?: string; color?: string } {
  if (value === null || !Number.isFinite(value)) {
    return {};
  }
  const magnitude = Math.min(1, Math.abs(value) / 3);
  const alpha = 0.16 + magnitude * 0.58;
  if (value >= 0) {
    return {
      backgroundColor: `rgba(138, 47, 34, ${alpha})`,
      color: magnitude >= 0.74 ? "#ffffff" : "#172033",
    };
  }
  return {
    backgroundColor: `rgba(47, 111, 159, ${alpha})`,
    color: magnitude >= 0.74 ? "#ffffff" : "#172033",
  };
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
