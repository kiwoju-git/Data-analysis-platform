import type { AnalysisRunComparisonResponse } from "./api";
import {
  comparisonCellValue,
  comparisonNumberCell,
  shortHash,
} from "./analysisWorkbenchUtils";

type SettingComparison = {
  setting: string;
  left: string | number | boolean | null;
  right: string | number | boolean | null;
  same: boolean;
};

type MetricComparison = {
  metric: string;
  left: number | null;
  right: number | null;
  delta: number | null;
};

export function AnalysisComparisonPanel({
  comparison,
}: {
  comparison: AnalysisRunComparisonResponse;
}) {
  return (
    <div className="analysis-comparison-result" role="status">
      <div className="panel-heading">
        <div>
          <h4>비교 결과</h4>
          <p>{comparison.comparable ? "compatible" : "incompatible"}</p>
        </div>
        <span className={comparison.comparable ? "status-pill status-ready" : "status-pill"}>
          {comparison.comparable ? "비교 가능" : "조건 다름"}
        </span>
      </div>
      <ComparisonExplanation comparison={comparison} />
      <div className="comparison-side-grid">
        <ComparisonSide label="left" side={comparison.left} />
        <ComparisonSide label="right" side={comparison.right} />
      </div>
      <div className="comparison-compatibility">
        <CompatibilityBadge label="method" same={comparison.compatibility.same_method_id} />
        <CompatibilityBadge label="version" same={comparison.compatibility.same_method_version} />
        <CompatibilityBadge
          label="dataset"
          same={comparison.compatibility.same_dataset_version_id}
        />
        <CompatibilityBadge label="summary" same={comparison.compatibility.same_summary_type} />
      </div>
      {comparison.method_specific?.descriptive_statistics !== null &&
      comparison.method_specific?.descriptive_statistics !== undefined ? (
        <DescriptiveComparisonTable comparison={comparison.method_specific.descriptive_statistics} />
      ) : null}
      {comparison.method_specific?.one_sample_t_test !== null &&
      comparison.method_specific?.one_sample_t_test !== undefined ? (
        <SettingsMetricsComparisonTable
          comparison={comparison.method_specific.one_sample_t_test}
          compatibility={[`response ${comparison.method_specific.one_sample_t_test.same_response_column ? "same" : "diff"}`]}
          subtitle={comparison.method_specific.one_sample_t_test.response_display_name ?? "response column"}
          title="1-표본 t-검정 비교"
        />
      ) : null}
      {comparison.method_specific?.two_sample_t_test !== null &&
      comparison.method_specific?.two_sample_t_test !== undefined ? (
        <SettingsMetricsComparisonTable
          comparison={comparison.method_specific.two_sample_t_test}
          compatibility={[
            `response ${comparison.method_specific.two_sample_t_test.same_response_column ? "same" : "diff"}`,
            `group column ${comparison.method_specific.two_sample_t_test.same_group_column ? "same" : "diff"}`,
            `group set ${comparison.method_specific.two_sample_t_test.same_group_label_set ? "same" : "diff"}`,
            `group order ${comparison.method_specific.two_sample_t_test.same_group_label_order ? "same" : "diff"}`,
          ]}
          subtitle={`${comparison.method_specific.two_sample_t_test.response_display_name ?? "response column"} / ${
            comparison.method_specific.two_sample_t_test.group_display_name ?? "group column"
          }`}
          title="2-표본 t-검정 비교"
        />
      ) : null}
      {comparison.method_specific?.paired_t_test !== null &&
      comparison.method_specific?.paired_t_test !== undefined ? (
        <SettingsMetricsComparisonTable
          comparison={comparison.method_specific.paired_t_test}
          compatibility={[
            `before ${comparison.method_specific.paired_t_test.same_before_column ? "same" : "diff"}`,
            `after ${comparison.method_specific.paired_t_test.same_after_column ? "same" : "diff"}`,
          ]}
          subtitle={`${comparison.method_specific.paired_t_test.before_display_name ?? "before column"} -> ${
            comparison.method_specific.paired_t_test.after_display_name ?? "after column"
          }`}
          title="대응표본 t-검정 비교"
        />
      ) : null}
      {comparison.method_specific?.equivalence_tost !== null &&
      comparison.method_specific?.equivalence_tost !== undefined ? (
        <SettingsMetricsComparisonTable
          comparison={comparison.method_specific.equivalence_tost}
          compatibility={[
            `response ${comparison.method_specific.equivalence_tost.same_response_column ? "same" : "diff"}`,
          ]}
          subtitle={comparison.method_specific.equivalence_tost.response_display_name ?? "response column"}
          title="동등성 TOST 비교"
        />
      ) : null}
      {comparison.method_specific?.one_way_anova !== null &&
      comparison.method_specific?.one_way_anova !== undefined ? (
        <SettingsMetricsComparisonTable
          comparison={comparison.method_specific.one_way_anova}
          compatibility={[
            `response ${comparison.method_specific.one_way_anova.same_response_column ? "same" : "diff"}`,
            `group column ${comparison.method_specific.one_way_anova.same_group_column ? "same" : "diff"}`,
            `group set ${comparison.method_specific.one_way_anova.same_group_label_set ? "same" : "diff"}`,
            `group order ${comparison.method_specific.one_way_anova.same_group_label_order ? "same" : "diff"}`,
          ]}
          subtitle={`${comparison.method_specific.one_way_anova.response_display_name ?? "response column"} / ${
            comparison.method_specific.one_way_anova.group_display_name ?? "group column"
          }`}
          title="일원분산분석 비교"
        />
      ) : null}
      {comparison.method_specific?.kruskal_wallis !== null &&
      comparison.method_specific?.kruskal_wallis !== undefined ? (
        <SettingsMetricsComparisonTable
          comparison={comparison.method_specific.kruskal_wallis}
          compatibility={[
            `response ${comparison.method_specific.kruskal_wallis.same_response_column ? "same" : "diff"}`,
            `group column ${comparison.method_specific.kruskal_wallis.same_group_column ? "same" : "diff"}`,
            `group set ${comparison.method_specific.kruskal_wallis.same_group_label_set ? "same" : "diff"}`,
            `group order ${comparison.method_specific.kruskal_wallis.same_group_label_order ? "same" : "diff"}`,
          ]}
          subtitle={`${comparison.method_specific.kruskal_wallis.response_display_name ?? "response column"} / ${
            comparison.method_specific.kruskal_wallis.group_display_name ?? "group column"
          }`}
          title="Kruskal-Wallis 비교"
        />
      ) : null}
      {comparison.differences.length > 0 ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>field</th>
                <th>left</th>
                <th>right</th>
              </tr>
            </thead>
            <tbody>
              {comparison.differences.map((difference) => (
                <tr key={difference.field}>
                  <td>{difference.field}</td>
                  <td>{comparisonCellValue(difference.left)}</td>
                  <td>{comparisonCellValue(difference.right)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="notice-box">metadata 차이가 없습니다.</div>
      )}
    </div>
  );
}

function ComparisonExplanation({ comparison }: { comparison: AnalysisRunComparisonResponse }) {
  return (
    <div className="comparison-explanation-box">
      <p>같은 method/version일 때만 자세한 비교가 가능합니다.</p>
      {!comparison.comparable ? (
        <p>incompatible comparison: method, version, dataset, summary type 중 다른 항목을 먼저 확인하세요.</p>
      ) : null}
      {!comparison.compatibility.same_method_version ? (
        <p>method version mismatch: 계산식이나 result schema가 달라졌을 수 있어 delta를 직접 비교하면 안 됩니다.</p>
      ) : null}
      {!comparison.compatibility.same_dataset_version_id ? (
        <p>dataset version mismatch: 입력 데이터가 다르므로 결과 차이는 데이터 차이일 수 있습니다.</p>
      ) : null}
      <p>delta는 right - left입니다. p-value delta는 효과가 커졌다는 뜻이 아니며, estimate와 confidence interval을 함께 봐야 합니다.</p>
    </div>
  );
}

function CompatibilityBadge({ label, same }: { label: string; same: boolean }) {
  return (
    <span className={same ? "status-pill status-ready compact-status-pill" : "status-pill compact-status-pill"}>
      {label} {same ? "same" : "different"}
    </span>
  );
}

function DescriptiveComparisonTable({
  comparison,
}: {
  comparison: NonNullable<
    AnalysisRunComparisonResponse["method_specific"]
  >["descriptive_statistics"];
}) {
  if (comparison === null) {
    return null;
  }
  return (
    <section className="comparison-method-section" aria-label="기술통계 비교">
      <h4>기술통계 비교</h4>
      {comparison.columns.length > 0 ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>column</th>
                <th>metric</th>
                <th>left</th>
                <th>right</th>
                <th>delta</th>
              </tr>
            </thead>
            <tbody>
              {comparison.columns.flatMap((column) =>
                column.metrics.map((metric) => (
                  <tr key={`${column.column_id}-${metric.metric}`}>
                    <td>{column.display_name}</td>
                    <td>{metric.metric}</td>
                    <td>{comparisonNumberCell(metric.left)}</td>
                    <td>{comparisonNumberCell(metric.right)}</td>
                    <td>{comparisonNumberCell(metric.delta)}</td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="notice-box">공통 column_id가 없습니다.</div>
      )}
      {comparison.left_only_column_ids.length > 0 ||
      comparison.right_only_column_ids.length > 0 ? (
        <div className="comparison-compatibility">
          <span>left-only {comparison.left_only_column_ids.length.toLocaleString()}</span>
          <span>right-only {comparison.right_only_column_ids.length.toLocaleString()}</span>
        </div>
      ) : null}
    </section>
  );
}

function SettingsMetricsComparisonTable({
  comparison,
  compatibility,
  subtitle,
  title,
}: {
  comparison: { settings: SettingComparison[]; metrics: MetricComparison[] };
  compatibility: readonly string[];
  subtitle: string;
  title: string;
}) {
  return (
    <section className="comparison-method-section" aria-label={title}>
      <div className="panel-heading compact-heading">
        <div>
          <h4>{title}</h4>
          <p>{subtitle}</p>
        </div>
      </div>
      <div className="comparison-compatibility">
        {compatibility.map((item) => (
          <span key={item}>{item}</span>
        ))}
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>setting</th>
              <th>left</th>
              <th>right</th>
              <th>same</th>
            </tr>
          </thead>
          <tbody>
            {comparison.settings.map((setting) => (
              <tr key={setting.setting}>
                <td>{setting.setting}</td>
                <td>{comparisonCellValue(setting.left)}</td>
                <td>{comparisonCellValue(setting.right)}</td>
                <td>{setting.same ? "same" : "diff"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>metric</th>
              <th>left</th>
              <th>right</th>
              <th>delta</th>
            </tr>
          </thead>
          <tbody>
            {comparison.metrics.map((metric) => (
              <tr key={metric.metric}>
                <td>{metric.metric}</td>
                <td>{comparisonNumberCell(metric.left)}</td>
                <td>{comparisonNumberCell(metric.right)}</td>
                <td>{comparisonNumberCell(metric.delta)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ComparisonSide({
  label,
  side,
}: {
  label: string;
  side: AnalysisRunComparisonResponse["left"];
}) {
  return (
    <div className="comparison-side-card">
      <strong>{label}</strong>
      <span>{side.method_id}</span>
      <span>v{side.method_version}</span>
      <span>{side.summary_type ?? "summary 없음"}</span>
      <span>
        rows {side.row_count_included?.toLocaleString() ?? "-"} /{" "}
        {side.row_count_total?.toLocaleString() ?? "-"}
      </span>
      <span>warnings {side.warning_count.toLocaleString()}</span>
      {side.stale ? <span className="stale-badge">stale · 재검토 필요</span> : null}
      <code>{shortHash(side.result_sha256)}</code>
    </div>
  );
}
