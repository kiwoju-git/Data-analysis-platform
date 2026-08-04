import { useState } from "react";

import type {
  LinearModelResidualScatter,
  LinearModelResult,
} from "./api";
import { InteractiveHistogramChart } from "./charts/InteractiveHistogramChart";
import {
  InteractiveScatterChart,
  type InteractiveScatterPoint,
} from "./charts/InteractiveScatterChart";
import { paddedNumericRange } from "./charts/chartScale";
import { observedDiagnosticPoints } from "./linearModelDiagnosticPoints";

interface LinearModelFitResultsProps {
  result: LinearModelResult;
}

export function LinearModelFitResults({ result }: LinearModelFitResultsProps) {
  const [residualPlotsOpen, setResidualPlotsOpen] = useState(false);
  const [residualType, setResidualType] = useState<"raw" | "standardized">("raw");
  const topDiagnosticPoints = result.diagnostics.diagnostic_points.points
    .slice()
    .sort((left, right) => (right.cooks_distance ?? -1) - (left.cooks_distance ?? -1))
    .slice(0, 5);

  return (
    <>
      {result.model_selection?.method === "backward_elimination" ? (
        <section className="result-section" aria-labelledby="linear-model-selection-title">
          <div className="panel-heading">
            <div>
              <h4 id="linear-model-selection-title">후진 제거 결과</h4>
              <p>
                Alpha to remove {formatModelNumber(result.model_selection.alpha_to_remove)} · 강한
                계층 원칙 · {selectionStopLabel(result.model_selection.stop_reason)}
              </p>
            </div>
          </div>
          <div className="metadata-grid" aria-label="후진 제거 요약">
            <span>초기 항</span>
            <strong>{result.model_selection.initial_terms.length.toLocaleString()}개</strong>
            <span>제거 항</span>
            <strong>
              {(result.model_selection.initial_terms.length - result.model_selection.final_terms.length).toLocaleString()}개
            </strong>
            <span>최종 항</span>
            <strong>{result.model_selection.final_terms.length.toLocaleString()}개</strong>
            <span>종료 이유</span>
            <strong>{selectionStopLabel(result.model_selection.stop_reason)}</strong>
          </div>
          <div className="table-wrap">
            <table className="result-table">
              <thead>
                <tr>
                  <th>단계</th>
                  <th>제거된 항</th>
                  <th>제거 p-value</th>
                  <th>S</th>
                  <th>R²</th>
                  <th>Adjusted R²</th>
                  <th>Predicted R²</th>
                  <th>Mallows Cp</th>
                </tr>
              </thead>
              <tbody>
                {result.model_selection.steps.map((step) => (
                  <tr key={step.step}>
                    <td>{step.step.toLocaleString()}</td>
                    <td>
                      {step.removed_term ?? "초기 모형"}
                      <span className="cell-subtle">유지 항 {step.active_terms.length}개</span>
                    </td>
                    <td>{formatModelNumber(step.removal_p_value)}</td>
                    <td>{formatModelNumber(step.s)}</td>
                    <td>{formatPercent(step.r_squared)}</td>
                    <td>{formatPercent(step.adjusted_r_squared)}</td>
                    <td>{formatPercent(step.predicted_r_squared)}</td>
                    <td>{formatModelNumber(step.mallows_cp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="warning-box">
            Stepwise 선택 이후의 p-value와 신뢰구간은 같은 데이터를 사용해 모형을 선택한
            영향을 받으므로 탐색적으로 해석해야 합니다.
          </div>
        </section>
      ) : null}

      <section className="result-section" aria-labelledby="linear-model-equation-title">
        <div className="panel-heading">
          <div>
            <h4 id="linear-model-equation-title">회귀방정식</h4>
            <p>화면에서는 반올림해 표시하며 계산과 저장에는 전체 정밀도 계수를 사용합니다.</p>
          </div>
          {result.equation ? (
            <button
              className="secondary-button"
              onClick={() => void navigator.clipboard?.writeText(result.equation?.display_equation ?? "")}
              type="button"
            >
              방정식 복사
            </button>
          ) : null}
        </div>
        {result.equation ? (
          <pre className="linear-model-equation">{result.equation.display_equation}</pre>
        ) : (
          <div className="notice-box">이전 결과 schema에는 구조화된 회귀방정식이 없습니다.</div>
        )}
      </section>

      <section className="result-section" aria-labelledby="linear-model-summary-title">
        <h4 id="linear-model-summary-title">모델 요약</h4>
        <div className="metadata-grid" aria-label="회귀 모델 요약">
          <span>S</span>
          <strong>{formatModelNumber(result.fit.residual_standard_error)}</strong>
          <span>R²</span>
          <strong>{formatPercent(result.fit.r_squared)}</strong>
          <span>Adjusted R²</span>
          <strong>{formatPercent(result.fit.adjusted_r_squared)}</strong>
          <span>Predicted R²</span>
          <strong>{formatPercent(result.fit.predicted_r_squared)}</strong>
          <span>PRESS</span>
          <strong>{formatModelNumber(result.fit.press)}</strong>
          <span>사용 N</span>
          <strong>{result.sample.n_used.toLocaleString()}</strong>
          <span>잔차 자유도</span>
          <strong>{result.sample.df_residual.toLocaleString()}</strong>
          <span>최대 VIF</span>
          <strong>{formatModelNumber(result.diagnostics.max_vif)}</strong>
          <span>Condition number</span>
          <strong>{formatModelNumber(result.diagnostics.condition_number)}</strong>
        </div>
        {typeof result.fit.predicted_r_squared === "number" && result.fit.predicted_r_squared < 0 ? (
          <div className="notice-box">
            음수 Predicted R²는 leave-one-out 예측력이 단순 평균 기준보다 낮을 수 있음을
            의미합니다.
          </div>
        ) : null}
        <p className="cell-subtle">
          VIF는 각 계수의 다중공선성 민감도를 보여주는 보조 지표이며 높은 값만으로 변수를
          자동 제거하지 않습니다.
        </p>
      </section>

      <section className="result-section" aria-labelledby="linear-model-coefficients-title">
        <h4 id="linear-model-coefficients-title">계수</h4>
        <div className="table-wrap">
          <table className="result-table">
            <thead>
              <tr>
                <th>항</th>
                <th>계수</th>
                <th>계수 표준오차</th>
                <th>신뢰구간</th>
                <th>t</th>
                <th>p-value</th>
                <th>VIF</th>
              </tr>
            </thead>
            <tbody>
              {result.coefficients.map((coefficient) => (
                <tr key={coefficient.term}>
                  <td>
                    {coefficient.term_kind === "intercept" ? "상수" : coefficient.term}
                    <span className="cell-subtle">
                      {coefficient.reference_level === null
                        ? coefficient.term_kind
                        : `기준 ${coefficient.reference_level} · ${coefficient.coding}`}
                    </span>
                  </td>
                  <td>{formatModelNumber(coefficient.estimate)}</td>
                  <td>{formatModelNumber(coefficient.standard_error)}</td>
                  <td>
                    {formatPercent(coefficient.confidence_interval.level)} CI{" "}
                    {formatModelNumber(coefficient.confidence_interval.lower)} -{" "}
                    {formatModelNumber(coefficient.confidence_interval.upper)}
                  </td>
                  <td>{formatModelNumber(coefficient.statistic)}</td>
                  <td>{formatModelNumber(coefficient.p_value)}</td>
                  <td>{formatModelNumber(coefficient.vif)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="result-section" aria-labelledby="linear-model-anova-title">
        <h4 id="linear-model-anova-title">분산분석</h4>
        {result.anova ? (
          <>
            <div className="table-wrap">
              <table className="result-table">
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>DF</th>
                    <th>Adj SS</th>
                    <th>Adj MS</th>
                    <th>F</th>
                    <th>P</th>
                  </tr>
                </thead>
                <tbody>
                  {result.anova.rows.map((row) => (
                    <tr key={`${row.row_kind}-${row.source}`}>
                      <td>{anovaSourceLabel(row.source)}</td>
                      <td>{row.df.toLocaleString()}</td>
                      <td>{formatModelNumber(row.adjusted_ss)}</td>
                      <td>{formatModelNumber(row.adjusted_ms)}</td>
                      <td>{formatModelNumber(row.f_statistic)}</td>
                      <td>{formatModelNumber(row.p_value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!result.anova.lack_of_fit.available ? (
              <p className="cell-subtle">적합결여 계산 불가: {lackOfFitReason(result.anova.lack_of_fit.reason)}</p>
            ) : null}
            <p className="cell-subtle">
              상호작용이나 2차항이 포함된 경우 주효과 검정은 다른 고차항을 포함한 조건부
              검정입니다.
            </p>
          </>
        ) : (
          <div className="notice-box">이전 결과 schema에는 항별 분산분석 표가 없습니다.</div>
        )}
      </section>

      <section className="result-section" aria-labelledby="linear-model-residual-plots-title">
        <div className="panel-heading">
          <div>
            <h4 id="linear-model-residual-plots-title">4-in-1 잔차 그림</h4>
            <p>저장된 진단 payload를 사용하며 모형을 다시 적합하지 않습니다.</p>
          </div>
          <button
            aria-expanded={residualPlotsOpen}
            className="secondary-button"
            disabled={!result.residual_plots}
            onClick={() => setResidualPlotsOpen((open) => !open)}
            type="button"
          >
            {residualPlotsOpen ? "잔차 그림 닫기" : "4-in-1 잔차 그림 보기"}
          </button>
        </div>
        {residualPlotsOpen && result.residual_plots ? (
          <>
            <fieldset className="segmented-control compact-segmented-control">
              <legend>잔차 종류</legend>
              {(["raw", "standardized"] as const).map((kind) => (
                <label key={kind}>
                  <input
                    checked={residualType === kind}
                    name="linear-model-residual-kind"
                    onChange={() => setResidualType(kind)}
                    type="radio"
                  />
                  <span>{kind === "raw" ? "일반 잔차" : "표준화 잔차"}</span>
                </label>
              ))}
            </fieldset>
            <div className="linear-model-four-in-one">
              <ChartPanel title="잔차 정규확률도">
                {renderResidualQqChart(result, residualType)}
              </ChartPanel>
              <ChartPanel title="잔차 히스토그램">
                <InteractiveHistogramChart
                  bins={result.residual_plots.histograms[residualType].bins.map((bin, index, bins) => ({
                    ...bin,
                    include_lower: true,
                    include_upper: index === bins.length - 1,
                  }))}
                  chartId={`linear-model-residual-histogram-${residualType}`}
                  columnName={residualType === "raw" ? "일반 잔차" : "표준화 잔차"}
                  nBasis={result.residual_plots.histograms[residualType].n}
                />
              </ChartPanel>
              <ChartPanel title="잔차 대 적합값">
                {renderResidualPayloadChart(
                  result.residual_plots.residuals_vs_fits[residualType],
                  residualType,
                )}
              </ChartPanel>
              <ChartPanel title="잔차 대 관측순서">
                {renderResidualPayloadChart(
                  result.residual_plots.residuals_vs_order[residualType],
                  residualType,
                )}
              </ChartPanel>
            </div>
          </>
        ) : null}
      </section>

      <section className="result-section" aria-labelledby="linear-model-diagnostics-title">
        <div className="panel-heading">
          <div>
            <h4 id="linear-model-diagnostics-title">추가 진단</h4>
            <p>진단 기준 초과는 검토 후보이며 자동 제외 기준이 아닙니다.</p>
          </div>
        </div>
        <div className="metadata-grid" aria-label="회귀 진단 요약">
          <span>최대 표준화 잔차</span>
          <strong>{formatModelNumber(result.diagnostics.residual_summary.max_abs_standardized)}</strong>
          <span>큰 잔차 후보</span>
          <strong>{result.diagnostics.residual_summary.large_standardized_count.toLocaleString()}개</strong>
          <span>최대 leverage</span>
          <strong>{formatModelNumber(result.diagnostics.leverage.max)}</strong>
          <span>High leverage</span>
          <strong>{result.diagnostics.leverage.high_count.toLocaleString()}개</strong>
          <span>최대 Cook&apos;s D</span>
          <strong>{formatModelNumber(result.diagnostics.influence.cooks_distance_max)}</strong>
          <span>Influential 후보</span>
          <strong>{result.diagnostics.influence.high_cooks_distance_count.toLocaleString()}개</strong>
        </div>
        <div className="linear-model-diagnostic-layout">
          <ChartPanel title="Observed vs Fitted">{renderObservedFittedChart(result)}</ChartPanel>
          <ChartPanel title="Leverage vs Cook's D">{renderInfluenceChart(result)}</ChartPanel>
        </div>
      </section>

      <section className="result-section" aria-labelledby="linear-model-unusual-title">
        <h4 id="linear-model-unusual-title">이상 관측치 후보</h4>
        <div className="table-wrap">
          <table className="result-table">
            <thead>
              <tr>
                <th>행 index</th>
                <th>Fitted</th>
                <th>Residual</th>
                <th>Std residual</th>
                <th>Leverage</th>
                <th>Cook&apos;s D</th>
              </tr>
            </thead>
            <tbody>
              {topDiagnosticPoints.map((point) => (
                <tr key={point.row_index}>
                  <td>{point.row_index.toLocaleString()}</td>
                  <td>{formatModelNumber(point.fitted)}</td>
                  <td>{formatModelNumber(point.residual)}</td>
                  <td>{formatModelNumber(point.standardized_residual)}</td>
                  <td>{formatModelNumber(point.leverage)}</td>
                  <td>{formatModelNumber(point.cooks_distance)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

function ChartPanel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="chart-panel">
      <div className="chart-panel-title">{title}</div>
      {children}
    </div>
  );
}

function renderResidualQqChart(result: LinearModelResult, kind: "raw" | "standardized") {
  const payload = result.residual_plots?.qq_plots[kind];
  if (!payload) return null;
  const points = payload.points.map((point) => ({
    ariaLabel: `순위 ${point.rank}, 이론 분위수 ${formatModelNumber(point.theoretical_quantile)}, 잔차 ${formatModelNumber(point.residual)}`,
    className: "qq-point interactive-chart-point",
    details: [
      { label: "행 index", value: point.row_index.toLocaleString() },
      { label: "이론 분위수", value: formatModelNumber(point.theoretical_quantile) },
      { label: "잔차", value: formatModelNumber(point.residual) },
    ],
    id: `linear-residual-qq-${kind}-${point.rank}`,
    title: `순위 ${point.rank}`,
    x: point.theoretical_quantile,
    y: point.residual,
  }));
  const xRange = paddedNumericRange(points.map((point) => point.x));
  const yRange = paddedNumericRange(points.map((point) => point.y));
  const line = payload.reference_line;
  return (
    <InteractiveScatterChart
      annotations={[
        `표시 ${points.length.toLocaleString()} / 전체 ${payload.n.toLocaleString()}`,
        payload.truncated ? "결정적 분위수 축약 적용" : "전체 point 표시",
      ]}
      chartId={`linear-model-residual-qq-${kind}`}
      compact
      description="잔차가 정규분포 기준선에서 체계적으로 벗어나는지 확인하는 시각적 진단입니다."
      emptyLabel="잔차 Q-Q point 없음"
      formatValue={formatModelNumber}
      points={points}
      referenceLines={line ? [{
        label: "정규확률 기준선",
        x1: xRange.min,
        x2: xRange.max,
        y1: line.intercept + line.slope * xRange.min,
        y2: line.intercept + line.slope * xRange.max,
      }] : []}
      title="Residual Normal Probability Plot"
      xLabel="Theoretical quantile"
      xRange={xRange}
      yLabel="Residual"
      yRange={yRange}
    />
  );
}

function renderResidualPayloadChart(
  payload: LinearModelResidualScatter,
  kind: "raw" | "standardized",
) {
  const isOrder = payload.x_kind === "order";
  const points: InteractiveScatterPoint[] = payload.points.map((point) => ({
    ariaLabel: `행 ${point.row_index}, ${isOrder ? "관측순서" : "적합값"} ${formatModelNumber(isOrder ? point.order : point.fitted)}, 잔차 ${formatModelNumber(point.residual)}`,
    className: "diagnostic-point",
    details: [
      { label: "행 index", value: point.row_index.toLocaleString() },
      { label: isOrder ? "관측순서" : "적합값", value: formatModelNumber(isOrder ? point.order : point.fitted) },
      { label: kind === "raw" ? "일반 잔차" : "표준화 잔차", value: formatModelNumber(point.residual) },
    ],
    id: `linear-residual-${payload.x_kind}-${kind}-${point.row_index}`,
    title: `행 ${point.row_index}`,
    x: isOrder ? point.order : point.fitted,
    y: point.residual,
  }));
  const xRange = paddedNumericRange(points.map((point) => point.x));
  const yRange = paddedNumericRange([...points.map((point) => point.y), 0]);
  return (
    <InteractiveScatterChart
      annotations={[
        `표시 ${points.length.toLocaleString()} / 전체 ${payload.n.toLocaleString()}`,
        payload.truncated ? "결정적 point cap 적용" : "전체 point 표시",
      ]}
      chartId={`linear-model-residual-${payload.x_kind}-${kind}`}
      compact
      connectPoints={isOrder ? "line" : undefined}
      description={isOrder
        ? "회귀에 사용된 row snapshot 순서에 따른 잔차를 보여주며 시간 인과성을 뜻하지 않습니다."
        : "적합값에 따른 잔차 분포를 보여줍니다."}
      emptyLabel="잔차 point 없음"
      formatValue={formatModelNumber}
      points={points}
      referenceLines={[{ label: "잔차 0 기준선", x1: xRange.min, x2: xRange.max, y1: 0, y2: 0 }]}
      title={isOrder ? "Residuals versus Order" : "Residuals versus Fits"}
      xLabel={isOrder ? "Observation order" : "Fitted value"}
      xRange={xRange}
      yLabel="Residual"
      yRange={yRange}
    />
  );
}

function renderObservedFittedChart(result: LinearModelResult) {
  const sourcePoints = observedDiagnosticPoints(result);
  const range = paddedNumericRange(sourcePoints.flatMap((point) => [point.fitted, point.observed]));
  const points: InteractiveScatterPoint[] = sourcePoints.map((point) => ({
    ariaLabel: `행 ${point.rowIndex}, 실제값 ${formatModelNumber(point.observed)}, 예측값 ${formatModelNumber(point.fitted)}`,
    className: "diagnostic-point",
    details: [
      { label: "행 index", value: point.rowIndex.toLocaleString() },
      { label: "실제값", value: formatModelNumber(point.observed) },
      { label: "예측값", value: formatModelNumber(point.fitted) },
      { label: "잔차", value: formatModelNumber(point.residual) },
    ],
    id: `observed-${point.rowIndex}`,
    title: `행 ${point.rowIndex}`,
    x: point.fitted,
    y: point.observed,
  }));
  return (
    <InteractiveScatterChart
      annotations={[`표시 ${points.length.toLocaleString()} / 전체 ${result.sample.n_used.toLocaleString()}`]}
      chartId="linear-model-observed-fitted"
      description="실제 관측값과 회귀모형 예측값을 비교하며 점선은 y=x 기준선입니다."
      emptyLabel="진단 point 없음"
      formatValue={formatModelNumber}
      points={points}
      referenceLines={[{ label: "y=x 기준선", x1: range.min, x2: range.max, y1: range.min, y2: range.max }]}
      title="Observed vs Fitted"
      xLabel="Fitted"
      xRange={range}
      yLabel="Observed"
      yRange={range}
    />
  );
}

function renderInfluenceChart(result: LinearModelResult) {
  const source = result.diagnostics.diagnostic_points.points.filter(
    (point) => point.cooks_distance !== null && Number.isFinite(point.cooks_distance),
  );
  const xRange = paddedNumericRange([...source.map((point) => point.leverage), result.diagnostics.leverage.threshold]);
  const yRange = paddedNumericRange([...source.map((point) => point.cooks_distance ?? 0), result.diagnostics.influence.cooks_distance_threshold]);
  const points: InteractiveScatterPoint[] = source.map((point) => {
    const cooks = point.cooks_distance ?? 0;
    const warning = point.leverage > result.diagnostics.leverage.threshold || cooks > result.diagnostics.influence.cooks_distance_threshold;
    return {
      ariaLabel: `행 ${point.row_index}, leverage ${formatModelNumber(point.leverage)}, Cook's D ${formatModelNumber(cooks)}`,
      className: "influence-point",
      details: [
        { label: "행 index", value: point.row_index.toLocaleString() },
        { label: "Leverage", value: formatModelNumber(point.leverage) },
        { label: "Cook's D", value: formatModelNumber(cooks) },
      ],
      id: `influence-${point.row_index}`,
      title: `행 ${point.row_index}`,
      warning,
      x: point.leverage,
      y: cooks,
    };
  });
  return (
    <InteractiveScatterChart
      annotations={["기준 초과는 검토 후보이며 자동 제외 기준이 아닙니다."]}
      chartId="linear-model-leverage-cook"
      description="각 진단점의 leverage와 Cook's D를 보여줍니다."
      emptyLabel="영향점 point 없음"
      formatValue={formatModelNumber}
      points={points}
      referenceLines={[
        { label: "Leverage 기준", x1: result.diagnostics.leverage.threshold, x2: result.diagnostics.leverage.threshold, y1: yRange.min, y2: yRange.max },
        { label: "Cook's D 기준", x1: xRange.min, x2: xRange.max, y1: result.diagnostics.influence.cooks_distance_threshold, y2: result.diagnostics.influence.cooks_distance_threshold },
      ]}
      title="Leverage vs Cook's D"
      xLabel="Leverage"
      xRange={xRange}
      yLabel="Cook's D"
      yRange={yRange}
    />
  );
}

function anovaSourceLabel(source: string): string {
  return ({ Regression: "Regression", Error: "Error", Total: "Total", "Lack-of-Fit": "Lack-of-Fit", "Pure Error": "Pure Error" } as Record<string, string>)[source] ?? source;
}

function lackOfFitReason(reason: string | null): string {
  const labels: Record<string, string> = {
    no_replicated_predictor_settings: "반복된 predictor 조합이 없어 순수오차와 적합결여를 분리할 수 없습니다.",
    no_lack_of_fit_degrees_of_freedom: "적합결여 자유도가 없습니다.",
    pure_error_variance_zero: "반복점의 순수오차 분산이 0입니다.",
  };
  return reason === null ? "계산 조건을 충족하지 않습니다." : labels[reason] ?? reason;
}

function selectionStopLabel(reason: string): string {
  const labels: Record<string, string> = {
    all_removal_p_values_at_or_below_alpha: "제거 기준 충족 항 없음",
    no_eligible_terms: "계층 원칙상 제거 가능 항 없음",
    intercept_only: "상수항 모형 도달",
    method_none: "모형 선택 없음",
  };
  return labels[reason] ?? reason;
}

function formatPercent(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value)
    ? `${(value * 100).toLocaleString("ko-KR", { maximumFractionDigits: 2 })}%`
    : "NA";
}

function formatModelNumber(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toLocaleString("ko-KR", { maximumFractionDigits: 6 })
    : "NA";
}
