import { RunResultChart } from "./charts/QualityResultCharts";
import type {
  AnalysisResultEnvelope,
  DatasetColumnResponse,
  DatasetVersionResponse,
  RunChartResult,
} from "./api";

interface RunChartPanelProps {
  analysisResult: AnalysisResultEnvelope | null;
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  methodId: string;
  orderColumnId: string | null;
  orderColumns: DatasetColumnResponse[];
  result: RunChartResult | null;
  valueColumnId: string | null;
  valueColumns: DatasetColumnResponse[];
  version: DatasetVersionResponse | null;
  onOrderColumnChange: (columnId: string) => void;
  onRun: () => void;
  onValueColumnChange: (columnId: string) => void;
}

export function RunChartPanel({
  analysisResult,
  filterValidationError,
  isRunningAnalysis,
  methodId,
  orderColumnId,
  orderColumns,
  result,
  valueColumnId,
  valueColumns,
  version,
  onOrderColumnChange,
  onRun,
  onValueColumnChange,
}: RunChartPanelProps) {
  const canRun = version !== null && valueColumnId !== null && filterValidationError === null;

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
              <span>순서</span>
              <select
                value={orderColumnId ?? ""}
                onChange={(event) => {
                  onOrderColumnChange(event.currentTarget.value);
                }}
              >
                <option value="">canonical row order</option>
                {orderColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
            <div className="option-note">
              <strong>중심선</strong>
              <span>median</span>
            </div>
            <div className="option-note">
              <strong>Trend</strong>
              <span>strict 6-point rule</span>
            </div>
            <div className="option-note">
              <strong>Oscillation</strong>
              <span>strict 14-point rule</span>
            </div>
            <div className="option-note">
              <strong>Clustering/Mixture</strong>
              <span>exact runs test α=0.05</span>
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
            {isRunningAnalysis ? "실행 중" : "런 차트 실행"}
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
              <div className="metadata-grid" aria-label="런 차트 요약">
                <span>측정값</span>
                <strong>{result.value.display_name}</strong>
                <span>사용 N</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>중심선</span>
                <strong>{formatRunChartNumber(result.center_line)}</strong>
                <span>순서</span>
                <strong>{formatRunChartOrder(result)}</strong>
                <span>Run count</span>
                <strong>{result.runs.run_count.toLocaleString()}</strong>
                <span>Runs test</span>
                <strong>{formatRunChartRunsTest(result)}</strong>
                <span>Trend 신호</span>
                <strong>
                  {countRunChartSignals(result, "run_chart_trend").toLocaleString()}개
                </strong>
                <span>Oscillation 신호</span>
                <strong>
                  {countRunChartSignals(result, "run_chart_oscillation").toLocaleString()}개
                </strong>
                <span>Clustering/Mixture</span>
                <strong>
                  {countRunChartSignals(result, "run_chart_clustering").toLocaleString()} /{" "}
                  {countRunChartSignals(result, "run_chart_mixture").toLocaleString()}개
                </strong>
                <span>관리한계</span>
                <strong>계산 안 함</strong>
              </div>
              <ApproximateRandomnessTests result={result} />
              <div className="result-section" aria-label="런 차트 결과">
                <div className="panel-heading">
                  <div>
                    <h4>런 차트</h4>
                    <p>
                      {result.chart.points.length.toLocaleString()} /{" "}
                      {result.chart.point_count.toLocaleString()} points
                      {result.chart.points_truncated ? " · capped" : ""}
                    </p>
                  </div>
                </div>
                <div className="chart-grid chart-grid-single analysis-result-grid">
                  <div className="chart-panel">
                    <div className="chart-panel-title">{result.value.display_name}</div>
                    <RunResultChart result={result} />
                  </div>
                </div>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>Above</th>
                      <th>Below</th>
                      <th>Tie</th>
                      <th>최장 run</th>
                      <th>결측 제외</th>
                      <th>비숫자 제외</th>
                      <th>순서 결측 제외</th>
                      <th>순서 비숫자 제외</th>
                      <th>순서 tie</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{result.runs.n_above.toLocaleString()}</td>
                      <td>{result.runs.n_below.toLocaleString()}</td>
                      <td>{result.runs.n_ties.toLocaleString()}</td>
                      <td>{result.runs.longest_run_length.toLocaleString()}</td>
                      <td>{result.n_excluded_missing_value.toLocaleString()}</td>
                      <td>{result.n_excluded_non_numeric_value.toLocaleString()}</td>
                      <td>{(result.n_excluded_missing_order ?? 0).toLocaleString()}</td>
                      <td>{(result.n_excluded_non_numeric_order ?? 0).toLocaleString()}</td>
                      <td>{(result.order_duplicate_count ?? 0).toLocaleString()}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              {result.signals.length > 0 ? (
                <div className="table-wrap">
                  <table className="result-table">
                    <thead>
                      <tr>
                        <th>신호</th>
                        <th>방향</th>
                        <th>길이</th>
                        <th>구간</th>
                        <th>정의</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.signals.map((signal) => (
                        <tr key={signal.signal_id}>
                          <td>{signal.code}</td>
                          <td>{signal.direction}</td>
                          <td>{signal.length.toLocaleString()}</td>
                          <td>
                            {signal.start_position.toLocaleString()} -{" "}
                            {signal.end_position.toLocaleString()}
                          </td>
                          <td>{signal.definition}</td>
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

function ApproximateRandomnessTests({ result }: { result: RunChartResult }) {
  const tests = result.approximate_randomness_tests;
  if (tests === undefined) {
    return (
      <div className="notice-box">
        이전 버전 결과에는 네 가지 근사 p-value가 없습니다. 기존 exact runs test와
        연속 패턴 결과는 그대로 확인할 수 있습니다.
      </div>
    );
  }
  const about = tests.about_median;
  const upDown = tests.up_down;
  const cards = [
    {
      key: "clustering",
      label: "군집",
      pValue: about.p_value_clustering,
      available: about.available,
      skippedReason: about.skipped_reason,
      observed: about.observed_runs,
      expected: about.expected_runs,
      policy: "중앙값과 같은 값은 아래쪽에 포함",
    },
    {
      key: "mixture",
      label: "혼합",
      pValue: about.p_value_mixture,
      available: about.available,
      skippedReason: about.skipped_reason,
      observed: about.observed_runs,
      expected: about.expected_runs,
      policy: "중앙값과 같은 값은 아래쪽에 포함",
    },
    {
      key: "trend",
      label: "추세",
      pValue: upDown.p_value_trend,
      available: upDown.available,
      skippedReason: upDown.skipped_reason,
      observed: upDown.observed_runs,
      expected: upDown.expected_runs,
      policy: "같은 값은 하강 방향에 포함",
    },
    {
      key: "oscillation",
      label: "진동",
      pValue: upDown.p_value_oscillation,
      available: upDown.available,
      skippedReason: upDown.skipped_reason,
      observed: upDown.observed_runs,
      expected: upDown.expected_runs,
      policy: "같은 값은 하강 방향에 포함",
    },
  ];
  return (
    <section className="result-section" aria-labelledby="run-chart-randomness-title">
      <div className="panel-heading">
        <div>
          <h4 id="run-chart-randomness-title">근사 랜덤성 검정</h4>
          <p>
            군집/혼합과 추세/진동은 각 쌍이 합계 1인 complementary one-sided
            p-value입니다. 연속 6점/14점 패턴 규칙 및 기존 exact runs test와 별도입니다.
          </p>
        </div>
      </div>
      <div className="run-chart-randomness-grid">
        {cards.map((card) => {
          const significant =
            card.available && card.pValue !== null && card.pValue <= tests.alpha;
          return (
            <article className="metric-card" key={card.key}>
              <span>{card.label}</span>
              <strong>
                {card.available
                  ? `p=${formatRunChartNumber(card.pValue)}`
                  : "계산할 수 없음"}
              </strong>
              <span>α={formatRunChartNumber(tests.alpha)}</span>
              <p>
                {card.available
                  ? significant
                    ? "비랜덤 패턴의 통계적 증거가 있어 원인 검토가 필요합니다."
                    : "이 패턴에 대한 유의한 증거가 부족합니다."
                  : `계산 조건 부족: ${card.skippedReason ?? "unknown"}`}
              </p>
              <details>
                <summary>상세정보</summary>
                <dl className="compact-definition-list">
                  <div>
                    <dt>관측 run</dt>
                    <dd>{card.observed.toLocaleString()}</dd>
                  </div>
                  <div>
                    <dt>기대 run</dt>
                    <dd>{formatRunChartNumber(card.expected)}</dd>
                  </div>
                  <div>
                    <dt>tie/flat 정책</dt>
                    <dd>{card.policy}</dd>
                  </div>
                </dl>
              </details>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function countRunChartSignals(result: RunChartResult, code: string): number {
  return result.signals.filter((signal) => signal.code === code).length;
}

function formatRunChartOrder(result: RunChartResult): string {
  if (result.order == null) {
    return "canonical row order";
  }
  if (result.order.data_type === "datetime") {
    const timezone = result.order_timezone === "timezone_aware_utc" ? " · UTC" : "";
    return `${result.order.display_name} datetime asc${timezone}`;
  }
  return `${result.order.display_name} numeric asc`;
}

function formatRunChartRunsTest(result: RunChartResult): string {
  if (!result.runs_test.available) {
    return result.runs_test.skipped_reason === null
      ? "계산 안 함"
      : `계산 안 함 · ${result.runs_test.skipped_reason}`;
  }
  return `low p=${formatRunChartNumber(result.runs_test.p_value_low)} · high p=${formatRunChartNumber(
    result.runs_test.p_value_high,
  )}`;
}

function formatRunChartNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "NA";
  }
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 6,
  }).format(value);
}
