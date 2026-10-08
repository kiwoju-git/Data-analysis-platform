import { SubgroupResultChart } from "./charts/QualityResultCharts";
import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  SubgroupChartResult,
  SubgroupChartSeries,
} from "./api";

type SubgroupChartType = "xbar_r" | "xbar_s";

interface SubgroupChartPanelProps {
  analysisResult: AnalysisResultEnvelope | null;
  chartType: SubgroupChartType;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  methodId: string;
  result: SubgroupChartResult | null;
  subgroupColumnId: string | null;
  subgroupColumns: DatasetColumnResponse[];
  valueColumnId: string | null;
  valueColumns: DatasetColumnResponse[];
  version: DatasetVersionResponse | null;
  onChartTypeChange: (chartType: SubgroupChartType) => void;
  onRun: () => void;
  onSubgroupColumnChange: (columnId: string) => void;
  onValueColumnChange: (columnId: string) => void;
}

export function SubgroupChartPanel({
  analysisResult,
  chartType,
  filterValidationError,
  isRunningAnalysis,
  methodId,
  result,
  subgroupColumnId,
  subgroupColumns,
  valueColumnId,
  valueColumns,
  version,
  onChartTypeChange,
  onRun,
  onSubgroupColumnChange,
  onValueColumnChange,
}: SubgroupChartPanelProps) {
  const canRun =
    version !== null &&
    valueColumnId !== null &&
    subgroupColumnId !== null &&
    filterValidationError === null;
  const secondaryChart = result === null ? null : subgroupChartDispersionSeries(result);
  const secondaryChartLabel = result?.chart_type === "xbar_s" ? "S" : "R";
  const secondaryCenterLabel = result?.chart_type === "xbar_s" ? "Sbar" : "Rbar";

  return (
    <section className="analysis-run-panel" data-analysis-execution={methodId}>
      {version === null ? (
        <div className="notice-box">데이터셋 버전 생성 후 실행할 수 있습니다.</div>
      ) : (
        <>
          <div className="option-grid">
            <label>
              <span>측정값</span>
              <select
                value={valueColumnId ?? ""}
                onChange={(event) => {
                  onValueColumnChange(event.currentTarget.value);
                }}
              >
                <option value="">선택</option>
                {valueColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>부분군</span>
              <select
                value={subgroupColumnId ?? ""}
                onChange={(event) => {
                  onSubgroupColumnChange(event.currentTarget.value);
                }}
              >
                <option value="">선택</option>
                {subgroupColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Chart</span>
              <select
                value={chartType}
                onChange={(event) => {
                  onChartTypeChange(event.currentTarget.value as SubgroupChartType);
                }}
              >
                <option value="xbar_r">Xbar-R</option>
                <option value="xbar_s">Xbar-S</option>
              </select>
            </label>
            <div className="option-note">
              <strong>Rule</strong>
              <span>fixed subgroup size · control limit signals</span>
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
            {isRunningAnalysis ? "실행 중" : "부분군 관리도 실행"}
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
              <div className="metadata-grid" aria-label="부분군 관리도 요약">
                <span>측정값</span>
                <strong>{result.value.display_name}</strong>
                <span>부분군</span>
                <strong>{result.subgroup.display_name}</strong>
                <span>부분군 수</span>
                <strong>{result.subgroup_count.toLocaleString()}</strong>
                <span>부분군 크기</span>
                <strong>{result.subgroup_size.toLocaleString()}</strong>
                <span>사용 N</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>Xbar center</span>
                <strong>{formatNumber(result.xbar_chart.center_line)}</strong>
                <span>{secondaryCenterLabel}</span>
                <strong>
                  {secondaryChart === null ? "n/a" : formatNumber(secondaryChart.center_line)}
                </strong>
                <span>신호</span>
                <strong>{result.signals.length.toLocaleString()}개</strong>
              </div>
              <div className="result-section" aria-label="부분군 관리도 결과">
                <div className="chart-grid analysis-result-grid">
                  <div className="chart-panel">
                    <div className="chart-panel-title">Xbar chart</div>
                    <SubgroupResultChart series={result.xbar_chart} label={`${result.value.display_name} Xbar`} kind="xbar" unit={result.value.unit} />
                  </div>
                  {secondaryChart === null ? null : (
                    <div className="chart-panel">
                      <div className="chart-panel-title">{secondaryChartLabel} chart</div>
                      <SubgroupResultChart series={secondaryChart} label={`${result.value.display_name} ${secondaryChartLabel}`} kind={secondaryChartLabel} unit={result.value.unit} />
                    </div>
                  )}
                </div>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>Chart</th>
                      <th>LCL</th>
                      <th>Center</th>
                      <th>UCL</th>
                      <th>Points</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Xbar</td>
                      <td>{formatNumber(result.xbar_chart.lcl)}</td>
                      <td>{formatNumber(result.xbar_chart.center_line)}</td>
                      <td>{formatNumber(result.xbar_chart.ucl)}</td>
                      <td>{result.xbar_chart.point_count.toLocaleString()}</td>
                    </tr>
                    {secondaryChart === null ? null : (
                      <tr>
                        <td>{secondaryChartLabel}</td>
                        <td>{formatNumber(secondaryChart.lcl)}</td>
                        <td>{formatNumber(secondaryChart.center_line)}</td>
                        <td>{formatNumber(secondaryChart.ucl)}</td>
                        <td>{secondaryChart.point_count.toLocaleString()}</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              {result.signals.length > 0 ? (
                <div className="table-wrap">
                  <table className="result-table">
                    <thead>
                      <tr>
                        <th>신호</th>
                        <th>Chart</th>
                        <th>부분군</th>
                        <th>값</th>
                        <th>한계</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.signals.map((signal) => (
                        <tr key={signal.signal_id}>
                          <td>{signal.code}</td>
                          <td>{signal.chart}</td>
                          <td>{signal.subgroup_label}</td>
                          <td>{formatNumber(signal.value)}</td>
                          <td>{signal.limit}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </>
          ) : null}
        </>
      )}
    </section>
  );
}

function subgroupChartDispersionSeries(result: SubgroupChartResult): SubgroupChartSeries | null {
  if (result.chart_type === "xbar_s") {
    return result.s_chart ?? null;
  }
  return result.r_chart ?? null;
}

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "NA";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 6,
  }).format(value);
}
