import { useState } from "react";

import type {
  AnalysisResultEnvelope,
  AttributeControlChartPoint,
  AttributeControlChartResult,
  AttributeControlChartType,
  DatasetColumnResponse,
  DatasetVersionResponse,
} from "./api";
import type {
  AttributeControlPhase,
  AttributeControlPhase2State,
} from "./useAttributeControlPhase2State";

interface AttributeControlChartPanelProps {
  analysisResult: AnalysisResultEnvelope | null;
  chartType: AttributeControlChartType;
  constantOpportunityConfirmed: boolean;
  countColumnId: string | null;
  countColumns: DatasetColumnResponse[];
  denominatorColumnId: string | null;
  denominatorColumns: DatasetColumnResponse[];
  filterValidationError: string | null;
  isRunningAnalysis: boolean;
  methodId: string;
  phase: AttributeControlPhase;
  phase2State?: AttributeControlPhase2State;
  result: AttributeControlChartResult | null;
  version: DatasetVersionResponse | null;
  onChartTypeChange: (chartType: AttributeControlChartType) => void;
  onConstantOpportunityConfirmedChange: (confirmed: boolean) => void;
  onCountColumnChange: (columnId: string) => void;
  onDenominatorColumnChange: (columnId: string) => void;
  onLimitSetChange: (limitSetId: string) => void;
  onPhaseChange: (phase: AttributeControlPhase) => void;
  onRun: () => void;
}

const chartOptions: Array<{
  type: AttributeControlChartType;
  label: string;
  purpose: string;
}> = [
  { type: "p", label: "P", purpose: "가변 표본 크기 불량률" },
  { type: "np", label: "NP", purpose: "고정 표본 크기 불량품 수" },
  { type: "c", label: "C", purpose: "동일 검사 기회의 결점 수" },
  { type: "u", label: "U", purpose: "가변 검사 기회의 단위당 결점" },
];

const chartWidth = 760;
const chartHeight = 300;
const plot = { left: 58, right: 22, top: 24, bottom: 44 };
const plotWidth = chartWidth - plot.left - plot.right;
const plotHeight = chartHeight - plot.top - plot.bottom;

export function AttributeControlChartPanel({
  analysisResult,
  chartType,
  constantOpportunityConfirmed,
  countColumnId,
  countColumns,
  denominatorColumnId,
  denominatorColumns,
  filterValidationError,
  isRunningAnalysis,
  methodId,
  phase,
  phase2State,
  result,
  version,
  onChartTypeChange,
  onConstantOpportunityConfirmedChange,
  onCountColumnChange,
  onDenominatorColumnChange,
  onLimitSetChange,
  onPhaseChange,
  onRun,
}: AttributeControlChartPanelProps) {
  const [limitSetDeletionConfirmed, setLimitSetDeletionConfirmed] = useState(false);
  const needsDenominator = chartType !== "c";
  const phase2Ready =
    phase === "phase_1" ||
    (phase2State?.selectedLimitSet !== null &&
      phase2State?.selectedLimitSet !== undefined &&
      phase2State.preflight?.ready === true &&
      !phase2State.isLoading);
  const canRun =
    version !== null &&
    countColumnId !== null &&
    (!needsDenominator || denominatorColumnId !== null) &&
    (chartType !== "c" || constantOpportunityConfirmed) &&
    phase2Ready &&
    filterValidationError === null;
  const countLabel = chartType === "p" || chartType === "np" ? "불량품 수" : "결점 수";
  const denominatorLabel = chartType === "u" ? "검사 기회" : "표본 크기";

  return (
    <section className="analysis-run-panel" aria-labelledby="attribute-chart-title">
      <div className="panel-heading">
        <div>
          <h3 id="attribute-chart-title">계수형 관리도 실행</h3>
          <p>{methodId}</p>
        </div>
        <span className="status-pill status-ready">사용 가능</span>
      </div>
      <div className="notice-box">
        {phase === "phase_1"
          ? "Phase I은 현재 데이터에서 기준선을 추정합니다. 안정성을 확인한 결과만 immutable limit set으로 닫으세요."
          : "Phase II는 선택한 immutable limit set의 중심선과 3-sigma 한계를 현재 데이터에 그대로 적용합니다."}
      </div>
      {version === null ? (
        <div className="notice-box">데이터셋 버전 생성 후 실행할 수 있습니다.</div>
      ) : (
        <>
          <div className="chart-mode-control" role="radiogroup" aria-label="관리 단계">
            <button
              aria-checked={phase === "phase_1"}
              className={phase === "phase_1" ? "is-active" : undefined}
              onClick={() => {
                onPhaseChange("phase_1");
              }}
              role="radio"
              type="button"
            >
              Phase I 기준선 추정
            </button>
            <button
              aria-checked={phase === "phase_2"}
              className={phase === "phase_2" ? "is-active" : undefined}
              onClick={() => {
                onPhaseChange("phase_2");
              }}
              role="radio"
              type="button"
            >
              Phase II 고정 한계 모니터링
            </button>
          </div>
          <div
            className="chart-mode-control"
            role="radiogroup"
            aria-label="계수형 관리도 유형"
          >
            {chartOptions.map((option) => (
              <button
                aria-checked={chartType === option.type}
                className={chartType === option.type ? "is-active" : undefined}
                key={option.type}
                onClick={() => {
                  onChartTypeChange(option.type);
                }}
                role="radio"
                title={option.purpose}
                type="button"
              >
                {option.label}
              </button>
            ))}
          </div>
          {phase === "phase_2" ? (
            <div className="option-grid" aria-label="Phase II limit set 선택">
              <label>
                <span>검증된 limit set</span>
                <select
                  aria-label="검증된 limit set"
                  disabled={phase2State?.isLoading === true && !phase2State.limitSets.length}
                  value={phase2State?.selectedLimitSetId ?? ""}
                  onChange={(event) => {
                    onLimitSetChange(event.currentTarget.value);
                  }}
                >
                  <option value="">직접 선택</option>
                  {(phase2State?.limitSets ?? []).map((limitSet) => (
                    <option key={limitSet.limit_set_id} value={limitSet.limit_set_id}>
                      {`${limitSet.chart_type.toUpperCase()} · 기준 ${formatDate(limitSet.closed_at)} · N=${limitSet.baseline_point_count}`}
                    </option>
                  ))}
                </select>
              </label>
              {phase2State?.selectedLimitSet ? (
                <div className="option-note">
                  <strong>
                    {phase2State.selectedLimitSet.chart_type.toUpperCase()} frozen center {formatNumber(phase2State.selectedLimitSet.frozen_center_line)}
                  </strong>
                  <span>
                    기준선 종료 {formatDate(phase2State.selectedLimitSet.closed_at)} · source analysis {shortId(phase2State.selectedLimitSet.source_analysis_id)}
                  </span>
                </div>
              ) : null}
              {phase2State?.selectedLimitSet ? (
                <div className="option-note">
                  <div className="button-row">
                    <button
                      className="secondary-button"
                      disabled={
                        phase2State.isDeleting ||
                        phase2State.isLoadingDeletionPreflight
                      }
                      onClick={() => {
                        setLimitSetDeletionConfirmed(false);
                        phase2State.onLoadDeletionPreflight();
                      }}
                      type="button"
                    >
                      {phase2State.isLoadingDeletionPreflight
                        ? "삭제 영향 확인 중"
                        : "limit set 삭제 영향 확인"}
                    </button>
                  </div>
                  {phase2State.deletionPreflight ? (
                    <div className="notice-box">
                      <strong>
                        Phase II 참조 {phase2State.deletionPreflight.counts.dependent_phase_2_analysis_count.toLocaleString()}건
                      </strong>
                      {phase2State.deletionPreflight.deletion_ready ? (
                        <label className="checkbox-field">
                          <input
                            checked={limitSetDeletionConfirmed}
                            type="checkbox"
                            onChange={(event) => {
                              setLimitSetDeletionConfirmed(event.currentTarget.checked);
                            }}
                          />
                          <span>
                            이 고정 관리한계 세트를 새 Phase II 분석에 사용할 수 없게 됨을
                            확인했습니다.
                          </span>
                        </label>
                      ) : (
                        <span>
                          이 limit set을 참조하는 Phase II 분석을 먼저 삭제해야 합니다.
                        </span>
                      )}
                      <div className="button-row">
                        <button
                          className="secondary-button"
                          disabled={
                            !phase2State.deletionPreflight.deletion_ready ||
                            !limitSetDeletionConfirmed ||
                            phase2State.isDeleting
                          }
                          onClick={() => {
                            phase2State.onDeleteLimitSet(
                              phase2State.deletionPreflight!,
                            );
                          }}
                          type="button"
                        >
                          {phase2State.isDeleting ? "삭제 중" : "limit set 삭제"}
                        </button>
                        <button
                          className="secondary-button"
                          disabled={phase2State.isDeleting}
                          onClick={() => {
                            setLimitSetDeletionConfirmed(false);
                            phase2State.onClearDeletion();
                          }}
                          type="button"
                        >
                          취소
                        </button>
                      </div>
                    </div>
                  ) : null}
                </div>
              ) : null}
              {phase2State?.deletion ? (
                <div className="notice-box" role="status">
                  limit set을 삭제했습니다. source Phase I 분석은 기록에 유지됩니다.
                </div>
              ) : null}
              {phase2State?.deletionError ? (
                <div className="error-banner" role="alert">
                  오류 코드: {phase2State.deletionError}
                </div>
              ) : null}
              {phase2State?.isLoading ? <div className="notice-box">호환성 확인 중...</div> : null}
              {phase2State?.error ? (
                <div className="error-banner">오류 코드: {phase2State.error}</div>
              ) : null}
              {phase2State?.preflight?.issues.map((issue) => (
                <div className="error-banner" key={issue.code}>
                  {issue.message} ({issue.code})
                </div>
              ))}
              {!phase2State?.isLoading && (phase2State?.limitSets.length ?? 0) === 0 ? (
                <div className="notice-box">
                  이 관리도 유형에 사용할 수 있는 닫힌 limit set이 없습니다.
                </div>
              ) : null}
            </div>
          ) : null}
          <div className="option-grid">
            <label>
              <span>{countLabel}</span>
              <select
                value={countColumnId ?? ""}
                onChange={(event) => {
                  onCountColumnChange(event.currentTarget.value);
                }}
              >
                <option value="">선택</option>
                {countColumns.map((column) => (
                  <option key={column.column_id} value={column.column_id}>
                    {column.display_name}
                  </option>
                ))}
              </select>
            </label>
            {needsDenominator ? (
              <label>
                <span>{denominatorLabel}</span>
                <select
                  value={denominatorColumnId ?? ""}
                  onChange={(event) => {
                    onDenominatorColumnChange(event.currentTarget.value);
                  }}
                >
                  <option value="">선택</option>
                  {denominatorColumns.map((column) => (
                    <option key={column.column_id} value={column.column_id}>
                      {column.display_name}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <label className="checkbox-field">
                <input
                  checked={constantOpportunityConfirmed}
                  onChange={(event) => {
                    onConstantOpportunityConfirmedChange(event.currentTarget.checked);
                  }}
                  type="checkbox"
                />
                <span>
                  {phase === "phase_2"
                    ? "현재 관측의 검사 기회가 기준선과 동일함을 확인"
                    : "모든 관측의 검사 기회가 동일함을 확인"}
                </span>
              </label>
            )}
            <div className="option-note">
              <strong>{chartType.toUpperCase()} chart</strong>
              <span>{chartOptions.find((option) => option.type === chartType)?.purpose}</span>
            </div>
          </div>
          <button
            className="primary-button"
            disabled={isRunningAnalysis || phase2State?.isLoading === true || !canRun}
            onClick={onRun}
            type="button"
          >
            {isRunningAnalysis ? "실행 중" : `${chartType.toUpperCase()} 관리도 실행`}
          </button>
          {analysisResult?.warnings.length ? (
            <ul className="warning-list" aria-label="분석 경고">
              {analysisResult.warnings.map((warning, index) => (
                <li key={`${warning.code}-${index}`}>{warning.message}</li>
              ))}
            </ul>
          ) : null}
          {result === null ? null : (
            <>
              <div className="metadata-grid" aria-label="계수형 관리도 요약">
                <span>Chart</span>
                <strong>{result.chart_type.toUpperCase()}</strong>
                <span>단계</span>
                <strong>{result.phase === "phase_2" ? "Phase II" : "Phase I"}</strong>
                <span>한계 출처</span>
                <strong>
                  {result.phase === "phase_2"
                    ? "검증된 immutable limit set"
                    : "필터 후 유효 관측에서 추정"}
                </strong>
                {result.limit_set_dependency ? (
                  <>
                    <span>Limit set</span>
                    <strong>{shortId(result.limit_set_dependency.limit_set_id)}</strong>
                    <span>기준선 종료</span>
                    <strong>{formatDate(result.limit_set_dependency.baseline_closed_at)}</strong>
                  </>
                ) : null}
                <span>계수 정의</span>
                <strong>{result.count_definition === "defectives" ? "불량품" : "결점"}</strong>
                <span>사용 관측</span>
                <strong>
                  {result.n_used.toLocaleString()} / {result.n_total.toLocaleString()}
                </strong>
                <span>중심선</span>
                <strong>{formatNumber(result.center_line)}</strong>
                <span>Dispersion ratio</span>
                <strong>{formatNumber(result.dispersion.ratio)}</strong>
                <span>관측별 한계</span>
                <strong>{result.limits_vary ? "가변" : "고정"}</strong>
                <span>신호</span>
                <strong>{result.signals.length.toLocaleString()}개</strong>
              </div>
              <div className="result-section" aria-label="계수형 관리도 결과">
                <div className="chart-panel">
                  <div className="chart-panel-title">
                    {result.chart_type.toUpperCase()} chart · {result.count.display_name}
                  </div>
                  {renderAttributeChart(result)}
                </div>
              </div>
              <div className="table-wrap">
                <table className="result-table">
                  <thead>
                    <tr>
                      <th>점</th>
                      <th>계수</th>
                      <th>{result.denominator_role === "sample_size" ? "표본 크기" : "검사 기회"}</th>
                      <th>값</th>
                      <th>LCL</th>
                      <th>UCL</th>
                      <th>신호</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.chart.points.slice(0, 25).map((point) => (
                      <tr key={point.position}>
                        <td>{point.position.toLocaleString()}</td>
                        <td>{point.count.toLocaleString()}</td>
                        <td>{point.denominator === null ? "동일 기회" : formatNumber(point.denominator)}</td>
                        <td>{formatNumber(point.value)}</td>
                        <td>{formatNumber(point.lcl)}</td>
                        <td>{formatNumber(point.ucl)}</td>
                        <td>{point.signal_codes.length ? "관리한계 밖" : "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}
    </section>
  );
}

function renderAttributeChart(result: AttributeControlChartResult) {
  const points = result.chart.points.filter((point) =>
    [point.position, point.value, point.lcl, point.ucl].every(Number.isFinite),
  );
  if (points.length === 0) {
    return null;
  }
  const xRange = paddedRange(points.map((point) => point.position));
  const yRange = paddedRange(
    points.flatMap((point) => [point.value, point.lcl, point.ucl, result.center_line]),
  );
  const path = (selector: (point: AttributeControlChartPoint) => number) =>
    points
      .map((point) => `${scaleX(point.position, xRange)},${scaleY(selector(point), yRange)}`)
      .join(" ");

  return (
    <svg className="mini-chart" role="img" viewBox={`0 0 ${chartWidth} ${chartHeight}`}>
      <title>
        {`${result.chart_type.toUpperCase()} 관리도. 중심선 ${formatNumber(result.center_line)}, 신호 ${result.signals.length}개`}
      </title>
      <rect
        fill="#ffffff"
        height={plotHeight}
        stroke="#d4dde8"
        width={plotWidth}
        x={plot.left}
        y={plot.top}
      />
      <polyline fill="none" points={path((point) => point.ucl)} stroke="#b45309" strokeWidth="1.4" />
      <line
        stroke="#6b7280"
        strokeDasharray="5 4"
        x1={plot.left}
        x2={plot.left + plotWidth}
        y1={scaleY(result.center_line, yRange)}
        y2={scaleY(result.center_line, yRange)}
      />
      <polyline fill="none" points={path((point) => point.lcl)} stroke="#b45309" strokeWidth="1.4" />
      <polyline fill="none" points={path((point) => point.value)} stroke="#1f4e79" strokeWidth="2" />
      {points.map((point) => (
        <circle
          cx={scaleX(point.position, xRange)}
          cy={scaleY(point.value, yRange)}
          fill={point.signal_codes.length ? "#b45309" : "#2563eb"}
          key={point.position}
          r={point.signal_codes.length ? 5 : 4}
          stroke="#172033"
        >
          <title>
            {`점 ${point.position}: ${formatNumber(point.value)} · LCL ${formatNumber(point.lcl)} · UCL ${formatNumber(point.ucl)}`}
          </title>
        </circle>
      ))}
      <text className="chart-axis-label" x={plot.left + 6} y={scaleY(result.center_line, yRange) - 5}>
        CL {formatNumber(result.center_line)}
      </text>
      <text className="chart-axis-label" x={plot.left} y={chartHeight - 12}>
        canonical position
      </text>
    </svg>
  );
}

function paddedRange(values: number[]): { min: number; max: number } {
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) {
    return { min: Math.max(0, min - 1), max: max + 1 };
  }
  const pad = (max - min) * 0.08;
  return { min: Math.max(0, min - pad), max: max + pad };
}

function scaleX(value: number, range: { min: number; max: number }) {
  return plot.left + ((value - range.min) / (range.max - range.min)) * plotWidth;
}

function scaleY(value: number, range: { min: number; max: number }) {
  return plot.top + plotHeight - ((value - range.min) / (range.max - range.min)) * plotHeight;
}

function formatNumber(value: number): string {
  if (!Number.isFinite(value)) {
    return "NA";
  }
  return new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 6 }).format(value);
}

function formatDate(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("ko-KR");
}

function shortId(value: string): string {
  return value.length <= 12 ? value : `${value.slice(0, 8)}...`;
}
