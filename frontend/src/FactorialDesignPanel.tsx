import { useEffect, useMemo, useState, type Dispatch, type SetStateAction } from "react";

import type {
  DoeDesignResponsesResponse,
  DoeDesignResponsesUpsertRequest,
  DoeFactorialAnalysisCreateRequest,
  DoeFactorialAnalysisResponse,
  FactorialDesignCreateRequest,
  FactorialDesignResponse,
} from "./api";

interface FactorDraft {
  id: string;
  name: string;
  low: string;
  high: string;
  unit: string;
}

interface FactorialDesignPanelProps {
  analysis: DoeFactorialAnalysisResponse | null;
  analysisError: string | null;
  design: FactorialDesignResponse | null;
  error: string | null;
  isCreating: boolean;
  isRunningAnalysis: boolean;
  isSavingResponses: boolean;
  methodId: string;
  onCreateDesign: (request: FactorialDesignCreateRequest) => void;
  onRunAnalysis: (designId: string, request: DoeFactorialAnalysisCreateRequest) => void;
  onSaveResponses: (designId: string, request: DoeDesignResponsesUpsertRequest) => void;
  responseError: string | null;
  responses: DoeDesignResponsesResponse | null;
}

interface ValidationResult {
  kind: "ready" | "error";
  message: string | null;
  request: FactorialDesignCreateRequest | null;
  runCount: number;
}

interface ResponseValidationResult {
  kind: "ready" | "error";
  message: string | null;
  request: DoeDesignResponsesUpsertRequest | null;
}

const maxFactorCount = 6;
const maxRunCount = 256;

export function FactorialDesignPanel({
  analysis,
  analysisError,
  design,
  error,
  isCreating,
  isRunningAnalysis,
  isSavingResponses,
  methodId,
  onCreateDesign,
  onRunAnalysis,
  onSaveResponses,
  responseError,
  responses,
}: FactorialDesignPanelProps) {
  const [name, setName] = useState("2-level screening design");
  const [factors, setFactors] = useState<FactorDraft[]>([
    { id: "factor-1", name: "Temperature", low: "60", high: "80", unit: "C" },
    { id: "factor-2", name: "Pressure", low: "5", high: "15", unit: "bar" },
  ]);
  const [replicates, setReplicates] = useState("1");
  const [centerPoints, setCenterPoints] = useState("1");
  const [randomize, setRandomize] = useState(true);
  const [randomizationSeed, setRandomizationSeed] = useState("20260702");
  const [blockCount, setBlockCount] = useState("1");
  const validation = useMemo(
    () =>
      validateFactorialDesignDraft({
        name,
        factors,
        replicates,
        centerPoints,
        randomize,
        randomizationSeed,
        blockCount,
      }),
    [blockCount, centerPoints, factors, name, randomizationSeed, randomize, replicates],
  );

  return (
    <section className="analysis-run-panel" aria-labelledby="factorial-design-title">
      <div className="panel-heading">
        <div>
          <h3 id="factorial-design-title">2-level full factorial 설계 생성</h3>
          <p>{methodId}</p>
        </div>
        <span className="status-pill status-ready">사용 가능</span>
      </div>
      <div className="option-grid">
        <label>
          <span>설계 이름</span>
          <input
            value={name}
            onChange={(event) => {
              setName(event.currentTarget.value);
            }}
          />
        </label>
        <label>
          <span>반복</span>
          <input
            inputMode="numeric"
            value={replicates}
            onChange={(event) => {
              setReplicates(event.currentTarget.value);
            }}
          />
        </label>
        <label>
          <span>센터점</span>
          <input
            inputMode="numeric"
            value={centerPoints}
            onChange={(event) => {
              setCenterPoints(event.currentTarget.value);
            }}
          />
        </label>
        <label>
          <span>Seed</span>
          <input
            inputMode="numeric"
            value={randomizationSeed}
            onChange={(event) => {
              setRandomizationSeed(event.currentTarget.value);
            }}
          />
        </label>
        <label>
          <span>Block</span>
          <input
            inputMode="numeric"
            value={blockCount}
            onChange={(event) => {
              setBlockCount(event.currentTarget.value);
            }}
          />
        </label>
        <label className="inline-option">
          <input
            checked={randomize}
            type="checkbox"
            onChange={(event) => {
              setRandomize(event.currentTarget.checked);
            }}
          />
          <span>랜덤화</span>
        </label>
      </div>
      <div className="table-wrap">
        <table className="result-table">
          <thead>
            <tr>
              <th>요인</th>
              <th>Low</th>
              <th>High</th>
              <th>Unit</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {factors.map((factor, index) => (
              <tr key={factor.id}>
                <td>
                  <input
                    aria-label={`factor ${index + 1} name`}
                    value={factor.name}
                    onChange={(event) => {
                      updateFactor(factor.id, "name", event.currentTarget.value, setFactors);
                    }}
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name || `factor ${index + 1}`} low`}
                    inputMode="decimal"
                    value={factor.low}
                    onChange={(event) => {
                      updateFactor(factor.id, "low", event.currentTarget.value, setFactors);
                    }}
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name || `factor ${index + 1}`} high`}
                    inputMode="decimal"
                    value={factor.high}
                    onChange={(event) => {
                      updateFactor(factor.id, "high", event.currentTarget.value, setFactors);
                    }}
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name || `factor ${index + 1}`} unit`}
                    value={factor.unit}
                    onChange={(event) => {
                      updateFactor(factor.id, "unit", event.currentTarget.value, setFactors);
                    }}
                  />
                </td>
                <td>
                  <button
                    disabled={factors.length <= 2}
                    onClick={() => {
                      setFactors((current) => current.filter((item) => item.id !== factor.id));
                    }}
                    type="button"
                  >
                    삭제
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="button-row">
        <button
          disabled={factors.length >= maxFactorCount}
          onClick={() => {
            setFactors((current) => [
              ...current,
              {
                id: `factor-${Date.now()}`,
                name: `Factor ${current.length + 1}`,
                low: "0",
                high: "1",
                unit: "",
              },
            ]);
          }}
          type="button"
        >
          요인 추가
        </button>
        <button
          className="primary-button"
          disabled={isCreating || validation.kind === "error"}
          onClick={() => {
            if (validation.request !== null) {
              onCreateDesign(validation.request);
            }
          }}
          type="button"
        >
          {isCreating ? "생성 중" : "DOE 설계 생성"}
        </button>
      </div>
      <div className="metadata-grid" aria-label="DOE 설계 입력 요약">
        <span>예상 run</span>
        <strong>{validation.runCount.toLocaleString()}</strong>
        <span>Family</span>
        <strong>two_level_full_factorial</strong>
        <span>Response</span>
        <strong>run별 저장 지원</strong>
        <span>Analysis</span>
        <strong>효과·OLS/ANOVA 지원</strong>
      </div>
      {validation.message !== null ? (
        <div className="notice-box notice-warning">{validation.message}</div>
      ) : null}
      {error !== null ? <div className="error-box">오류 코드: {error}</div> : null}
      {design !== null ? (
        <FactorialDesignPreview
          analysis={analysis}
          analysisError={analysisError}
          design={design}
          isRunningAnalysis={isRunningAnalysis}
          isSavingResponses={isSavingResponses}
          onSaveResponses={onSaveResponses}
          onRunAnalysis={onRunAnalysis}
          responseError={responseError}
          responses={responses}
        />
      ) : null}
    </section>
  );
}

function FactorialDesignPreview({
  analysis,
  analysisError,
  design,
  isRunningAnalysis,
  isSavingResponses,
  onSaveResponses,
  onRunAnalysis,
  responseError,
  responses,
}: {
  analysis: DoeFactorialAnalysisResponse | null;
  analysisError: string | null;
  design: FactorialDesignResponse;
  isRunningAnalysis: boolean;
  isSavingResponses: boolean;
  onSaveResponses: (designId: string, request: DoeDesignResponsesUpsertRequest) => void;
  onRunAnalysis: (designId: string, request: DoeFactorialAnalysisCreateRequest) => void;
  responseError: string | null;
  responses: DoeDesignResponsesResponse | null;
}) {
  const visibleRuns = design.runs.slice(0, 64);
  const matchingResponses = responses?.design_id === design.design_id ? responses : null;
  const firstResponse = matchingResponses?.responses[0] ?? null;
  const [responseName, setResponseName] = useState("Yield");
  const [responseUnit, setResponseUnit] = useState("");
  const [responseValues, setResponseValues] = useState<Record<number, string>>({});
  const [maxInteractionOrder, setMaxInteractionOrder] = useState(
    Math.min(2, design.factors.length),
  );
  useEffect(() => {
    const nextValues: Record<number, string> = {};
    if (firstResponse !== null) {
      for (const value of firstResponse.values) {
        nextValues[value.run_order] = String(value.value);
      }
      setResponseName(firstResponse.response_name);
      setResponseUnit(firstResponse.unit ?? "");
    } else {
      for (const run of design.runs) {
        nextValues[run.run_order] = "";
      }
      setResponseName("Yield");
      setResponseUnit("");
    }
    setResponseValues(nextValues);
  }, [design.design_id, design.runs, firstResponse]);
  const responseValidation = useMemo(
    () => validateResponseDraft(design.runs, responseName, responseUnit, responseValues),
    [design.runs, responseName, responseUnit, responseValues],
  );
  const matchingAnalysis = analysis?.design_id === design.design_id ? analysis : null;

  return (
    <>
      <div className="metadata-grid" aria-label="DOE 설계 결과 요약">
        <span>Design</span>
        <strong>{design.name}</strong>
        <span>Version</span>
        <strong>v{design.version_number}</strong>
        <span>Status</span>
        <strong>{matchingResponses?.status ?? design.status}</strong>
        <span>Run count</span>
        <strong>{design.run_count.toLocaleString()}</strong>
        <span>SHA-256</span>
        <strong>{design.design_sha256.slice(0, 12)}</strong>
      </div>
      <div className="table-wrap">
        <table className="result-table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Standard</th>
              <th>Rep</th>
              <th>Block</th>
              <th>Center</th>
              {design.factors.map((factor) => (
                <th key={factor.name}>{factor.name}</th>
              ))}
              <th>Coded</th>
            </tr>
          </thead>
          <tbody>
            {visibleRuns.map((run) => (
              <tr key={run.run_order}>
                <td>{run.run_order}</td>
                <td>{run.standard_order}</td>
                <td>{run.replicate_index}</td>
                <td>{run.block_index ?? "-"}</td>
                <td>{run.center_point ? "yes" : "no"}</td>
                {design.factors.map((factor) => (
                  <td key={factor.name}>{formatFactorLevel(run.factor_levels[factor.name])}</td>
                ))}
                <td>{formatCodedLevels(run.coded_levels)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {design.runs.length > visibleRuns.length ? (
        <div className="notice-box">
          {visibleRuns.length.toLocaleString()} / {design.runs.length.toLocaleString()} runs 표시
        </div>
      ) : null}
      <div className="panel-heading compact-heading">
        <div>
          <h4>반응값 입력</h4>
          <p>현재 설계의 run_order 전체와 정확히 맞는 numeric response만 저장합니다.</p>
        </div>
        <span className="status-pill status-ready">
          {matchingResponses?.responses.length ? "저장됨" : "입력 대기"}
        </span>
      </div>
      <div className="option-grid">
        <label>
          <span>반응 이름</span>
          <input
            value={responseName}
            onChange={(event) => {
              setResponseName(event.currentTarget.value);
            }}
          />
        </label>
        <label>
          <span>단위</span>
          <input
            value={responseUnit}
            onChange={(event) => {
              setResponseUnit(event.currentTarget.value);
            }}
          />
        </label>
      </div>
      <div className="table-wrap">
        <table className="result-table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Standard</th>
              {design.factors.map((factor) => (
                <th key={factor.name}>{factor.name}</th>
              ))}
              <th>Response</th>
            </tr>
          </thead>
          <tbody>
            {design.runs.map((run) => (
              <tr key={run.run_order}>
                <td>{run.run_order}</td>
                <td>{run.standard_order}</td>
                {design.factors.map((factor) => (
                  <td key={factor.name}>{formatFactorLevel(run.factor_levels[factor.name])}</td>
                ))}
                <td>
                  <input
                    aria-label={`run ${run.run_order} response`}
                    inputMode="decimal"
                    value={responseValues[run.run_order] ?? ""}
                    onChange={(event) => {
                      const value = event.currentTarget.value;
                      setResponseValues((current) => ({
                        ...current,
                        [run.run_order]: value,
                      }));
                    }}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {responseValidation.message !== null ? (
        <div className="notice-box notice-warning">{responseValidation.message}</div>
      ) : null}
      {responseError !== null ? <div className="error-box">오류 코드: {responseError}</div> : null}
      <div className="button-row">
        <button
          className="primary-button"
          disabled={
            isSavingResponses ||
            responseValidation.kind === "error" ||
            design.status === "analyzed"
          }
          onClick={() => {
            if (responseValidation.request !== null) {
              onSaveResponses(design.design_id, responseValidation.request);
            }
          }}
          type="button"
        >
          {design.status === "analyzed"
            ? "분석 후 반응 잠금"
            : isSavingResponses
              ? "저장 중"
              : "반응값 저장"}
        </button>
      </div>
      {matchingResponses?.responses.map((response) => (
        <div className="metadata-grid" key={response.response_name} aria-label="저장된 DOE 반응 요약">
          <span>Response</span>
          <strong>{response.response_name}</strong>
          <span>Count</span>
          <strong>{response.response_count.toLocaleString()}</strong>
          <span>Unit</span>
          <strong>{response.unit ?? "-"}</strong>
          <span>Analysis</span>
          <strong>{matchingAnalysis === null ? "실행 대기" : `v${matchingAnalysis.method_version}`}</strong>
        </div>
      ))}
      {firstResponse !== null ? (
        <>
          <div className="panel-heading compact-heading">
            <div>
              <h4>Factorial 분석</h4>
              <p>-1/+1 coding, hierarchy 고정, OLS/ANOVA와 pure error/lack-of-fit</p>
            </div>
            <span className="status-pill status-ready">
              {matchingAnalysis === null ? "분석 대기" : "분석 완료"}
            </span>
          </div>
          <div className="option-grid">
            <label>
              <span>최대 상호작용 차수</span>
              <select
                aria-label="최대 상호작용 차수"
                value={maxInteractionOrder}
                onChange={(event) => {
                  setMaxInteractionOrder(Number(event.currentTarget.value));
                }}
              >
                {Array.from({ length: Math.min(3, design.factors.length) }, (_, index) => index + 1).map(
                  (order) => (
                    <option key={order} value={order}>
                      {order}차
                    </option>
                  ),
                )}
              </select>
            </label>
            <div className="metadata-grid compact-metadata" aria-label="DOE 분석 정책">
              <span>Confidence</span>
              <strong>95%</strong>
              <span>Selection</span>
              <strong>자동 선택 없음</strong>
            </div>
          </div>
          {analysisError !== null ? (
            <div className="error-box">오류 코드: {analysisError}</div>
          ) : null}
          <div className="button-row">
            <button
              className="primary-button"
              disabled={isRunningAnalysis}
              onClick={() => {
                onRunAnalysis(design.design_id, {
                  response_name: firstResponse.response_name,
                  max_interaction_order: maxInteractionOrder,
                  confidence_level: 0.95,
                  point_limit: 256,
                });
              }}
              type="button"
            >
              {isRunningAnalysis ? "분석 중" : "효과 및 ANOVA 분석"}
            </button>
          </div>
          {matchingAnalysis !== null ? (
            <FactorialAnalysisResultView analysis={matchingAnalysis} />
          ) : null}
        </>
      ) : null}
    </>
  );
}

function FactorialAnalysisResultView({
  analysis,
}: {
  analysis: DoeFactorialAnalysisResponse;
}) {
  const { result } = analysis;
  const terms = result.terms.filter((term) => term.kind !== "intercept");
  const lackOfFit = result.anova.lack_of_fit;
  return (
    <section className="analysis-result-section" aria-labelledby="factorial-analysis-result-title">
      <div className="panel-heading compact-heading">
        <div>
          <h4 id="factorial-analysis-result-title">Factorial 분석 결과</h4>
          <p>
            {analysis.response_name} · {analysis.method_id} v{analysis.method_version}
          </p>
        </div>
        <span className="status-pill status-ready">검증 저장됨</span>
      </div>
      <div className="metadata-grid" aria-label="DOE 분석 적합 요약">
        <span>N / residual df</span>
        <strong>
          {result.sample.n_observations} / {result.sample.df_residual}
        </strong>
        <span>R² / adjusted R²</span>
        <strong>
          {formatMetric(result.fit.r_squared)} / {formatMetric(result.fit.adjusted_r_squared)}
        </strong>
        <span>Residual SE</span>
        <strong>{formatMetric(result.fit.residual_standard_error)}</strong>
        <span>Model F / p</span>
        <strong>
          {formatMetric(result.fit.f_statistic)} / {formatPValue(result.fit.f_p_value)}
        </strong>
        <span>Coding</span>
        <strong>-1 / +1, center 0</strong>
        <span>Response SHA</span>
        <strong>{analysis.response_sha256.slice(0, 12)}</strong>
        <span>Analysis ID</span>
        <strong>{analysis.analysis_id}</strong>
      </div>
      <div className="chart-grid">
        <div className="chart-panel">
          <span className="chart-panel-title">절대 효과 순위</span>
          <FactorialEffectChart analysis={analysis} />
        </div>
        <div className="chart-panel">
          <span className="chart-panel-title">주효과 평균</span>
          <FactorialMainEffectsChart analysis={analysis} />
        </div>
      </div>
      <div className="table-wrap">
        <table className="result-table">
          <thead>
            <tr>
              <th>Term</th>
              <th>Kind</th>
              <th>Coefficient</th>
              <th>Effect</th>
              <th>SE</th>
              <th>p-value</th>
              <th>Effect 95% CI</th>
            </tr>
          </thead>
          <tbody>
            {terms.map((term) => (
              <tr key={term.term_id}>
                <td>{term.label}</td>
                <td>{term.kind}</td>
                <td>{formatMetric(term.coefficient)}</td>
                <td>{formatMetric(term.effect)}</td>
                <td>{formatMetric(term.standard_error)}</td>
                <td>{formatPValue(term.p_value)}</td>
                <td>{formatInterval(term.effect_confidence_interval)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-wrap">
        <table className="result-table">
          <thead>
            <tr>
              <th>ANOVA source</th>
              <th>DF</th>
              <th>SS</th>
              <th>MS</th>
              <th>F</th>
              <th>p-value</th>
            </tr>
          </thead>
          <tbody>
            {([
              ["Model", result.anova.model],
              ["Residual", result.anova.residual],
              ["Pure error", lackOfFit.pure_error],
              ["Lack of fit", lackOfFit.lack_of_fit],
              ["Total", result.anova.total],
            ] as const).map(([label, row]) => (
              <tr key={label}>
                <td>{label}</td>
                <td>{row.df}</td>
                <td>{formatMetric(row.sum_squares)}</td>
                <td>{formatMetric(row.mean_square)}</td>
                <td>{formatMetric(row.f_statistic)}</td>
                <td>{formatPValue(row.p_value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="metadata-grid" aria-label="DOE 잔차 진단 요약">
        <span>Lack-of-fit available</span>
        <strong>{lackOfFit.available ? "yes" : "no"}</strong>
        <span>Durbin-Watson</span>
        <strong>{formatMetric(result.diagnostics.durbin_watson)}</strong>
        <span>Shapiro-Wilk p</span>
        <strong>{formatPValue(result.diagnostics.shapiro_wilk.p_value)}</strong>
        <span>|standardized residual| &gt; 3</span>
        <strong>{result.diagnostics.high_standardized_residual_count}</strong>
        <span>High leverage / Cook</span>
        <strong>
          {result.diagnostics.high_leverage_count} / {result.diagnostics.high_cooks_distance_count}
        </strong>
        <span>Points</span>
        <strong>
          {result.diagnostics.points.length}
          {result.diagnostics.points_truncated ? " (truncated)" : ""}
        </strong>
      </div>
      {result.warnings.map((warning) => (
        <div className="notice-box notice-warning" key={warning}>
          {factorialWarningMessage(warning)}
        </div>
      ))}
    </section>
  );
}

function FactorialEffectChart({ analysis }: { analysis: DoeFactorialAnalysisResponse }) {
  const effects = analysis.result.ranked_effects.slice(0, 12);
  if (effects.length === 0) {
    return <div className="notice-box">표시할 factorial 효과가 없습니다.</div>;
  }
  const width = 720;
  const left = 170;
  const right = 40;
  const rowHeight = 28;
  const height = Math.max(180, 32 + effects.length * rowHeight);
  const maxEffect = Math.max(...effects.map((effect) => effect.absolute_effect), 1e-12);
  const barWidth = width - left - right;
  return (
    <svg
      aria-label="절대 효과 순위 차트"
      className="chart-svg"
      role="img"
      viewBox={`0 0 ${width} ${height}`}
    >
      <title>절대 효과 순위</title>
      {effects.map((effect, index) => {
        const y = 18 + index * rowHeight;
        const valueWidth = (effect.absolute_effect / maxEffect) * barWidth;
        return (
          <g key={effect.term_id}>
            <text className="chart-axis-label chart-axis-label-end" x={left - 10} y={y + 13}>
              {effect.label}
            </text>
            <rect className="doe-effect-bar" height={18} width={valueWidth} x={left} y={y} />
            <text className="chart-axis-label" x={left + valueWidth + 6} y={y + 13}>
              {formatMetric(effect.effect)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function FactorialMainEffectsChart({ analysis }: { analysis: DoeFactorialAnalysisResponse }) {
  const effects = analysis.result.plots.main_effects;
  if (effects.length === 0) {
    return <div className="notice-box">표시할 주효과 평균이 없습니다.</div>;
  }
  const width = 720;
  const leftX = 270;
  const rightX = 620;
  const rowHeight = 42;
  const height = Math.max(180, 35 + effects.length * rowHeight);
  const values = effects.flatMap((effect) => [effect.low_mean, effect.high_mean]);
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const range = Math.max(maximum - minimum, 1e-12);
  return (
    <svg
      aria-label="주효과 평균 차트"
      className="chart-svg"
      role="img"
      viewBox={`0 0 ${width} ${height}`}
    >
      <title>요인별 low와 high 반응 평균</title>
      {effects.map((effect, index) => {
        const centerY = 24 + index * rowHeight + rowHeight / 2;
        const lowY = centerY + ((maximum - effect.low_mean) / range - 0.5) * 24;
        const highY = centerY + ((maximum - effect.high_mean) / range - 0.5) * 24;
        return (
          <g key={effect.factor}>
            <text className="chart-axis-label chart-axis-label-end" x={150} y={centerY + 4}>
              {effect.factor}
            </text>
            <line className="doe-main-effect-line" x1={leftX} x2={rightX} y1={lowY} y2={highY} />
            <circle className="doe-main-effect-point" cx={leftX} cy={lowY} r={5} />
            <circle className="doe-main-effect-point" cx={rightX} cy={highY} r={5} />
            <text className="chart-axis-label" x={leftX - 80} y={lowY + 4}>
              -1: {formatMetric(effect.low_mean)}
            </text>
            <text className="chart-axis-label" x={rightX + 10} y={highY + 4}>
              +1: {formatMetric(effect.high_mean)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function formatMetric(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "-";
  }
  return Number(value.toPrecision(6)).toLocaleString();
}

function formatPValue(value: number | null): string {
  if (value === null || !Number.isFinite(value)) {
    return "-";
  }
  return value < 0.0001 ? "< 0.0001" : value.toFixed(4);
}

function formatInterval(
  interval: { lower: number; upper: number } | null,
): string {
  return interval === null
    ? "-"
    : `[${formatMetric(interval.lower)}, ${formatMetric(interval.upper)}]`;
}

function factorialWarningMessage(code: string): string {
  const messages: Record<string, string> = {
    doe_factorial_randomization_and_independence_not_proven:
      "랜덤화와 관측 독립성은 결과만으로 증명되지 않으므로 실험 실행 기록을 확인해야 합니다.",
    doe_factorial_effects_are_associations_within_experiment:
      "효과는 현재 실험 설계영역의 연관이며 설계영역 밖 인과효과를 자동으로 증명하지 않습니다.",
    doe_factorial_model_saturated_no_inference:
      "포화 모형이므로 효과는 계산되지만 오차 기반 p-value와 신뢰구간은 제공되지 않습니다.",
    doe_factorial_residual_df_small:
      "잔차 자유도가 작아 추론과 잔차 진단을 신중히 해석해야 합니다.",
    doe_factorial_higher_order_interactions_excluded_by_policy:
      "선택한 최대 차수보다 높은 상호작용은 모형에서 제외됐습니다.",
    doe_factorial_residual_variance_zero:
      "적합 후 잔차 분산이 사실상 0이므로 오차 기반 추론을 신중히 해석해야 합니다.",
    doe_factorial_pure_error_unavailable_without_replication:
      "동일 설계점 반복이 없어 pure error와 lack-of-fit을 분리할 수 없습니다.",
    doe_factorial_lack_of_fit_df_unavailable:
      "현재 설계와 자유도로 lack-of-fit 검정을 계산할 수 없습니다.",
    doe_factorial_block_fixed_effects_included: "Block을 고정효과로 포함했습니다.",
    doe_factorial_large_standardized_residual:
      "절대 표준화 잔차가 3을 넘는 run이 있어 입력과 실행조건을 확인해야 합니다.",
    doe_factorial_influential_run_detected:
      "Cook's distance가 큰 run이 있어 잔차 진단을 확인해야 합니다.",
  };
  return messages[code] ?? code;
}

function updateFactor(
  factorId: string,
  field: keyof Omit<FactorDraft, "id">,
  value: string,
  setFactors: Dispatch<SetStateAction<FactorDraft[]>>,
) {
  setFactors((current) =>
    current.map((factor) => (factor.id === factorId ? { ...factor, [field]: value } : factor)),
  );
}

function validateFactorialDesignDraft({
  name,
  factors,
  replicates,
  centerPoints,
  randomize,
  randomizationSeed,
  blockCount,
}: {
  name: string;
  factors: FactorDraft[];
  replicates: string;
  centerPoints: string;
  randomize: boolean;
  randomizationSeed: string;
  blockCount: string;
}): ValidationResult {
  const trimmedName = name.trim();
  if (trimmedName.length === 0) {
    return validationError("설계 이름을 입력하세요.", 0);
  }
  if (factors.length < 2 || factors.length > maxFactorCount) {
    return validationError("요인은 2개 이상 6개 이하입니다.", 0);
  }

  const parsedFactors: FactorialDesignCreateRequest["factors"] = [];
  const names = new Set<string>();
  for (const factor of factors) {
    const factorName = factor.name.trim();
    const low = Number(factor.low);
    const high = Number(factor.high);
    if (factorName.length === 0) {
      return validationError("비어 있는 요인 이름이 있습니다.", 0);
    }
    const normalizedName = factorName.toLocaleLowerCase("ko-KR");
    if (names.has(normalizedName)) {
      return validationError("요인 이름은 중복될 수 없습니다.", 0);
    }
    names.add(normalizedName);
    if (!Number.isFinite(low) || !Number.isFinite(high) || low >= high) {
      return validationError(`${factorName}의 low/high를 확인하세요.`, 0);
    }
    parsedFactors.push({
      name: factorName,
      low,
      high,
      unit: factor.unit.trim().length > 0 ? factor.unit.trim() : null,
    });
  }

  const parsedReplicates = integerField(replicates);
  const parsedCenterPoints = integerField(centerPoints);
  const parsedSeed = integerField(randomizationSeed);
  const parsedBlockCount = integerField(blockCount);
  if (parsedReplicates === null || parsedReplicates < 1 || parsedReplicates > 16) {
    return validationError("반복 수는 1 이상 16 이하입니다.", 0);
  }
  if (parsedCenterPoints === null || parsedCenterPoints < 0 || parsedCenterPoints > 32) {
    return validationError("센터점 수는 0 이상 32 이하입니다.", 0);
  }
  if (parsedSeed === null || parsedSeed < 0) {
    return validationError("Seed는 0 이상의 정수입니다.", 0);
  }
  if (parsedBlockCount === null || parsedBlockCount < 1 || parsedBlockCount > 64) {
    return validationError("Block 수는 1 이상 64 이하입니다.", 0);
  }

  const runCount = 2 ** parsedFactors.length * parsedReplicates + parsedCenterPoints;
  if (runCount > maxRunCount) {
    return validationError(`현재 설계 제한은 ${maxRunCount.toLocaleString()} runs입니다.`, runCount);
  }
  if (parsedBlockCount > runCount) {
    return validationError("Block 수는 전체 run 수보다 클 수 없습니다.", runCount);
  }
  return {
    kind: "ready",
    message: null,
    request: {
      name: trimmedName,
      factors: parsedFactors,
      replicates: parsedReplicates,
      center_points: parsedCenterPoints,
      randomize,
      randomization_seed: parsedSeed,
      block_count: parsedBlockCount,
    },
    runCount,
  };
}

function validationError(message: string, runCount: number): ValidationResult {
  return {
    kind: "error",
    message,
    request: null,
    runCount,
  };
}

function validateResponseDraft(
  runs: FactorialDesignResponse["runs"],
  responseName: string,
  responseUnit: string,
  responseValues: Record<number, string>,
): ResponseValidationResult {
  const trimmedName = responseName.trim();
  if (trimmedName.length === 0) {
    return responseValidationError("반응 이름을 입력하세요.");
  }
  const values = [];
  for (const run of runs) {
    const rawValue = responseValues[run.run_order] ?? "";
    if (rawValue.trim().length === 0) {
      return responseValidationError(`Run ${run.run_order}의 반응값을 입력하세요.`);
    }
    const parsed = Number(rawValue);
    if (!Number.isFinite(parsed)) {
      return responseValidationError(`Run ${run.run_order}의 반응값은 숫자여야 합니다.`);
    }
    values.push({ run_order: run.run_order, value: parsed });
  }
  return {
    kind: "ready",
    message: null,
    request: {
      response_name: trimmedName,
      unit: responseUnit.trim().length > 0 ? responseUnit.trim() : null,
      values,
    },
  };
}

function responseValidationError(message: string): ResponseValidationResult {
  return {
    kind: "error",
    message,
    request: null,
  };
}

function integerField(value: string): number | null {
  const parsed = Number(value);
  return Number.isInteger(parsed) ? parsed : null;
}

function formatFactorLevel(value: number | undefined): string {
  return typeof value === "number" ? Number(value.toPrecision(12)).toLocaleString() : "-";
}

function formatCodedLevels(levels: Record<string, number>): string {
  return Object.entries(levels)
    .map(([name, level]) => `${name}:${level}`)
    .join(", ");
}
