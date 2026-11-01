import { ApiNoticeText } from "./i18n/ApiNoticeText";
import { useI18n } from "./i18n/LocaleProvider";
import { gageRrNoticeKeys } from "./i18n/gageRrMessages";
import { formatMeasurement, formatProbability } from "./statisticalNumberFormat";

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
  replicateMode?: "infer_from_rows" | "explicit_column";
  interactionPolicy?: "retain" | "auto_pool";
  interactionAlpha?: string;
  onReplicateModeChange?: (mode: "infer_from_rows" | "explicit_column") => void;
  onInteractionPolicyChange?: (policy: "retain" | "auto_pool") => void;
  onInteractionAlphaChange?: (value: string) => void;
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
  replicateMode = "infer_from_rows",
  interactionPolicy = "auto_pool",
  interactionAlpha = "0.05",
  onReplicateModeChange = () => undefined,
  onInteractionPolicyChange = () => undefined,
  onInteractionAlphaChange = () => undefined,
  result,
  version,
  onMeasurementColumnChange,
  onOperatorColumnChange,
  onPartColumnChange,
  onReplicateColumnChange,
  onRunAnalysis,
  onRunPreflight,
}: GageRrPreflightPanelProps) {
  const { t } = useI18n();
  const distinctColumns = new Set(
    [measurementColumnId, partColumnId, operatorColumnId, ...(replicateMode === "explicit_column" ? [replicateColumnId] : [])].filter(
      (columnId): columnId is string => columnId !== null,
    ),
  );
  const allColumnsSelected =
    measurementColumnId !== null &&
    partColumnId !== null &&
    operatorColumnId !== null &&
    (replicateMode === "infer_from_rows" || replicateColumnId !== null);
  const hasDuplicateRoleColumn = allColumnsSelected && distinctColumns.size < (replicateMode === "explicit_column" ? 4 : 3);
  const canRunPreflight = version !== null && allColumnsSelected && !hasDuplicateRoleColumn && filterValidationError === null;
  const canRunAnalysis = canRunPreflight;
  const errorCount = preflight?.issues.filter((issue) => issue.severity === "error").length ?? 0;
  const warningCount =
    preflight?.issues.filter((issue) => issue.severity === "warning").length ?? 0;

  return (
    <section className="analysis-run-panel gage-rr-panel" data-analysis-execution={methodId}>
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
            <div className="option-note">
              <strong>{t("gage.followup.scope")}</strong>
              <span>balanced crossed ANOVA</span>
            </div>
            <div className="option-note">
              <strong>{t("gage.followup.data")}</strong>
              <span>{t("gage.followup.currentData")}</span>
            </div>
          </div>
          <p>{t("gage.followup.repeatedMeasurements")}</p>
          <div className="option-grid">
            <label><span>{t("gage.followup.replicateMode")}</span>
              <select aria-label="Gage replicate mode" value={replicateMode} onChange={(event) => onReplicateModeChange(event.currentTarget.value as "infer_from_rows" | "explicit_column")}>
                <option value="infer_from_rows">{t("gage.followup.inferReplicates")}</option>
                <option value="explicit_column">{t("gage.followup.explicitReplicates")}</option>
              </select>
            </label>
            <label><span>{t("gage.followup.interactionPolicy")}</span>
              <select aria-label="Gage interaction policy" value={interactionPolicy} onChange={(event) => onInteractionPolicyChange(event.currentTarget.value as "retain" | "auto_pool")}>
                <option value="auto_pool">{t("gage.followup.autoPool")}</option>
                <option value="retain">{t("gage.followup.retain")}</option>
              </select>
            </label>
          </div>
          <details open={replicateMode === "explicit_column"}>
            <summary>{t("gage.followup.advanced")}</summary>
            {replicateMode === "explicit_column" ? <ColumnSelect columns={replicateColumns} label={t("gage.followup.replicateId")} value={replicateColumnId} onChange={onReplicateColumnChange} /> : null}
            <label><span>{t("gage.followup.interactionAlpha")}</span>
              <input aria-label="Gage interaction alpha" inputMode="decimal" value={interactionAlpha} onChange={(event) => onInteractionAlphaChange(event.currentTarget.value)} />
            </label>
          </details>
          {hasDuplicateRoleColumn ? (
            <div className="notice-box notice-warning">
              측정값, 부품, 측정자, 반복 컬럼은 서로 달라야 합니다.
            </div>
          ) : null}
          <button
            className="secondary-button"
            disabled={isRunning || !canRunPreflight}
            onClick={() => {
              onRunPreflight();
            }}
            type="button"
          >
            {isRunning ? "점검 중" : "설계 사전점검"}
          </button>
          <button
            className="primary-button"
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
                <li key={`${warning.code}-${index}`}><ApiNoticeText notice={warning} messageKeys={gageRrNoticeKeys} showCode /></li>
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
                    <strong>{issue.severity}</strong> <ApiNoticeText notice={issue} messageKeys={gageRrNoticeKeys} showCode />
                    {issue.count === null ? null : ` (${issue.count.toLocaleString()})`}
                  </li>
                ))}
              </ul>
            </>
          ) : null}
          {result !== null ? (
            <>
              <div className="notice-box" data-gage-policy>
                {t("gage.followup.storedPolicy")}: {result.replicate_mode ?? "explicit_column"} / {result.interaction_selection?.requested_policy ?? "retain"}
                {result.interaction_selection ? <> · alpha {formatMeasurement(result.interaction_selection.alpha_to_remove_interaction)} · p {formatProbability(result.interaction_selection.interaction_p_value)} · {result.interaction_selection.reason}</> : null}
              </div>
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
                  <caption>{t("gage.followup.finalAnova")}</caption>
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
              {result.full_anova_table ? <details><summary>{t("gage.followup.fullAnova")}</summary>
                <div className="table-wrap"><table className="result-table"><thead><tr><th>Source</th><th>DF</th><th>SS</th><th>MS</th><th>F</th><th>p</th></tr></thead>
                  <tbody>{result.full_anova_table.map((row) => <tr key={row.source}><td>{sourceLabel(row.source)}</td><td>{row.degrees_of_freedom}</td><td>{formatMeasurement(row.sum_of_squares)}</td><td>{formatMeasurement(row.mean_square)}</td><td>{formatMeasurement(row.f_statistic)}</td><td>{formatProbability(row.p_value)}</td></tr>)}</tbody>
                </table></div>
              </details> : null}
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
  return formatMeasurement(value);
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
