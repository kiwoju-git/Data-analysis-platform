import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  GageRrPreflightResponse,
  GageRrResult,
} from "./api";

interface GageRrPreflightPanelProps {
  analysisResult: AnalysisResultEnvelope | null;
  error: string | null;
  filterValidationError: string | null;
  isRunning: boolean;
  measurementColumnId: string | null;
  measurementColumns: DatasetColumnResponse[];
  methodId: string;
  operatorColumnId: string | null;
  operatorColumns: DatasetColumnResponse[];
  partColumnId: string | null;
  partColumns: DatasetColumnResponse[];
  preflight: GageRrPreflightResponse | null;
  replicateColumnId: string | null;
  replicateColumns: DatasetColumnResponse[];
  result: GageRrResult | null;
  version: DatasetVersionResponse | null;
  onMeasurementColumnChange: (columnId: string) => void;
  onOperatorColumnChange: (columnId: string) => void;
  onPartColumnChange: (columnId: string) => void;
  onReplicateColumnChange: (columnId: string) => void;
  onRunAnalysis: () => void;
  onRunPreflight: () => void;
}

export function GageRrPreflightPanel({
  analysisResult,
  error,
  filterValidationError,
  isRunning,
  measurementColumnId,
  measurementColumns,
  methodId,
  operatorColumnId,
  operatorColumns,
  partColumnId,
  partColumns,
  preflight,
  replicateColumnId,
  replicateColumns,
  result,
  version,
  onMeasurementColumnChange,
  onOperatorColumnChange,
  onPartColumnChange,
  onReplicateColumnChange,
  onRunAnalysis,
  onRunPreflight,
}: GageRrPreflightPanelProps) {
  const distinctColumns = new Set(
    [measurementColumnId, partColumnId, operatorColumnId, replicateColumnId].filter(
      (columnId): columnId is string => columnId !== null,
    ),
  );
  const allColumnsSelected =
    measurementColumnId !== null &&
    partColumnId !== null &&
    operatorColumnId !== null &&
    replicateColumnId !== null;
  const hasDuplicateRoleColumn = allColumnsSelected && distinctColumns.size < 4;
  const canRunPreflight = version !== null && allColumnsSelected && !hasDuplicateRoleColumn;
  const canRunAnalysis =
    canRunPreflight &&
    filterValidationError === null &&
    preflight !== null &&
    preflight.design.ready_for_anova;
  const errorCount = preflight?.issues.filter((issue) => issue.severity === "error").length ?? 0;
  const warningCount =
    preflight?.issues.filter((issue) => issue.severity === "warning").length ?? 0;

  return (
    <section className="analysis-run-panel" aria-labelledby="gage-rr-preflight-title">
      <div className="panel-heading">
        <div>
          <h3 id="gage-rr-preflight-title">Gage R&R 실행</h3>
          <p>{methodId}</p>
        </div>
        <span className="status-pill status-ready">사용 가능</span>
      </div>
      {version === null ? (
        <div className="notice-box">데이터셋 버전 생성 후 사전점검할 수 있습니다.</div>
      ) : (
        <>
          <div className="option-grid">
            <ColumnSelect
              columns={measurementColumns}
              label="측정값"
              value={measurementColumnId}
              onChange={onMeasurementColumnChange}
            />
            <ColumnSelect
              columns={partColumns}
              label="부품"
              value={partColumnId}
              onChange={onPartColumnChange}
            />
            <ColumnSelect
              columns={operatorColumns}
              label="측정자"
              value={operatorColumnId}
              onChange={onOperatorColumnChange}
            />
            <ColumnSelect
              columns={replicateColumns}
              label="반복"
              value={replicateColumnId}
              onChange={onReplicateColumnChange}
            />
            <div className="option-note">
              <strong>Scope</strong>
              <span>balanced crossed ANOVA</span>
            </div>
            <div className="option-note">
              <strong>Data</strong>
              <span>canonical dataset version 전체</span>
            </div>
          </div>
          {hasDuplicateRoleColumn ? (
            <div className="notice-box notice-warning">
              측정값, 부품, 측정자, 반복 컬럼은 서로 달라야 합니다.
            </div>
          ) : null}
          <button
            className="primary-button"
            disabled={isRunning || !canRunPreflight}
            onClick={() => {
              onRunPreflight();
            }}
            type="button"
          >
            {isRunning ? "점검 중" : "설계 사전점검"}
          </button>
          <button
            className="secondary-button"
            disabled={isRunning || !canRunAnalysis}
            onClick={() => {
              onRunAnalysis();
            }}
            type="button"
          >
            {isRunning ? "실행 중" : "Gage R&R 계산"}
          </button>
          {preflight !== null && !preflight.design.ready_for_anova ? (
            <div className="notice-box notice-warning">
              사전점검 오류를 먼저 수정해야 Gage R&R 계산을 실행할 수 있습니다.
            </div>
          ) : null}
          {error !== null ? <div className="error-box">오류 코드: {error}</div> : null}
          {analysisResult?.warnings.length ? (
            <ul className="warning-list" aria-label="분석 경고">
              {analysisResult.warnings.map((warning, index) => (
                <li key={`${warning.code}-${index}`}>{warning.message}</li>
              ))}
            </ul>
          ) : null}
          {preflight !== null ? (
            <>
              <div className="metadata-grid" aria-label="Gage R&R 사전점검 요약">
                <span>상태</span>
                <strong>{preflight.design.ready_for_anova ? "준비됨" : "수정 필요"}</strong>
                <span>사용 N</span>
                <strong>
                  {preflight.sample.n_used.toLocaleString()} /{" "}
                  {preflight.sample.n_total.toLocaleString()}
                </strong>
                <span>부품</span>
                <strong>{preflight.design.part_count.toLocaleString()}</strong>
                <span>측정자</span>
                <strong>{preflight.design.operator_count.toLocaleString()}</strong>
                <span>반복 level</span>
                <strong>{preflight.design.replicate_level_count.toLocaleString()}</strong>
                <span>Cell</span>
                <strong>
                  {preflight.design.observed_cell_count.toLocaleString()} /{" "}
                  {preflight.design.expected_cell_count.toLocaleString()}
                </strong>
                <span>Cell별 반복</span>
                <strong>
                  {preflight.design.min_replicates_per_cell.toLocaleString()}-
                  {preflight.design.max_replicates_per_cell.toLocaleString()}
                </strong>
                <span>오류/경고</span>
                <strong>
                  {errorCount.toLocaleString()} / {warningCount.toLocaleString()}
                </strong>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>Replicates per cell</th>
                      <th>Cell count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preflight.design.cell_replicate_count_distribution.map((entry) => (
                      <tr key={entry.replicate_count}>
                        <td>{entry.replicate_count.toLocaleString()}</td>
                        <td>{entry.cell_count.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <ul className="warning-list" aria-label="Gage R&R 사전점검 이슈">
                {preflight.issues.map((issue) => (
                  <li key={issue.code}>
                    <strong>{issue.severity}</strong> {issue.message}
                    {issue.count === null ? null : ` (${issue.count.toLocaleString()})`}
                  </li>
                ))}
              </ul>
            </>
          ) : null}
          {result !== null ? (
            <>
              <div className="metadata-grid" aria-label="Gage R&R 결과 요약">
                <span>사용 N</span>
                <strong>
                  {result.sample.n_used.toLocaleString()} /{" "}
                  {result.sample.n_total.toLocaleString()}
                </strong>
                <span>부품</span>
                <strong>{result.design.part_count.toLocaleString()}</strong>
                <span>측정자</span>
                <strong>{result.design.operator_count.toLocaleString()}</strong>
                <span>반복</span>
                <strong>{result.design.replicate_count.toLocaleString()}</strong>
                <span>Total Gage R&R</span>
                <strong>
                  {formatPercent(
                    result.variance_components.total_gage_rr.percent_study_variation,
                  )}
                </strong>
                <span>Part-to-Part</span>
                <strong>
                  {formatPercent(
                    result.variance_components.part_to_part.percent_study_variation,
                  )}
                </strong>
                <span>NDC</span>
                <strong>{result.variance_components.ndc ?? "계산 불가"}</strong>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>Source</th>
                      <th>DF</th>
                      <th>SS</th>
                      <th>MS</th>
                      <th>F</th>
                      <th>p</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.anova_table.map((row) => (
                      <tr key={row.source}>
                        <td>{sourceLabel(row.source)}</td>
                        <td>{row.degrees_of_freedom.toLocaleString()}</td>
                        <td>{formatNumber(row.sum_of_squares)}</td>
                        <td>{formatOptionalNumber(row.mean_square)}</td>
                        <td>{formatOptionalNumber(row.f_statistic)}</td>
                        <td>{formatOptionalNumber(row.p_value)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>Component</th>
                      <th>Raw Var</th>
                      <th>Final Var</th>
                      <th>SD</th>
                      <th>Study Var</th>
                      <th>%Contribution</th>
                      <th>%Study</th>
                    </tr>
                  </thead>
                  <tbody>
                    {varianceComponentRows(result).map((component) => (
                      <tr key={component.component}>
                        <td>{componentLabel(component.component)}</td>
                        <td>{formatNumber(component.raw_variance)}</td>
                        <td>{formatNumber(component.final_variance)}</td>
                        <td>{formatNumber(component.standard_deviation)}</td>
                        <td>{formatNumber(component.study_variation)}</td>
                        <td>{formatPercent(component.percent_contribution)}</td>
                        <td>{formatPercent(component.percent_study_variation)}</td>
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

function ColumnSelect({
  columns,
  label,
  value,
  onChange,
}: {
  columns: DatasetColumnResponse[];
  label: string;
  value: string | null;
  onChange: (columnId: string) => void;
}) {
  return (
    <label>
      <span>{label}</span>
      <select
        value={value ?? ""}
        onChange={(event) => {
          onChange(event.currentTarget.value);
        }}
      >
        <option value="">선택</option>
        {columns.map((column) => (
          <option key={column.column_id} value={column.column_id}>
            {column.display_name}
          </option>
        ))}
      </select>
    </label>
  );
}

function varianceComponentRows(result: GageRrResult) {
  return [
    result.variance_components.repeatability,
    result.variance_components.operator,
    result.variance_components.part_operator,
    result.variance_components.reproducibility,
    result.variance_components.total_gage_rr,
    result.variance_components.part_to_part,
    result.variance_components.total_variation,
  ];
}

function sourceLabel(source: string): string {
  const labels: Record<string, string> = {
    part: "Part",
    operator: "Operator",
    part_operator: "Part x Operator",
    repeatability: "Repeatability",
    total: "Total",
  };
  return labels[source] ?? source;
}

function componentLabel(component: string): string {
  const labels: Record<string, string> = {
    repeatability: "Repeatability",
    operator: "Operator",
    part_operator: "Part x Operator",
    reproducibility: "Reproducibility",
    total_gage_rr: "Total Gage R&R",
    part_to_part: "Part-to-Part",
    total_variation: "Total Variation",
  };
  return labels[component] ?? component;
}

function formatNumber(value: number): string {
  return value.toLocaleString(undefined, { maximumFractionDigits: 6 });
}

function formatOptionalNumber(value: number | null): string {
  return value === null ? "NA" : formatNumber(value);
}

function formatPercent(value: number | null): string {
  if (value === null) {
    return "NA";
  }
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}%`;
}
