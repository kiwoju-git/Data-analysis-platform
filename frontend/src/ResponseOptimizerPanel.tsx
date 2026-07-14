import { useEffect, useMemo, useRef, useState } from "react";

import {
  createResponseOptimizer,
  type DoeResponseSurfaceAnalysisResponse,
  type ResponseOptimizerCreateRequest,
  type ResponseOptimizerGoal,
  type ResponseOptimizerResponse,
  type ResponseSurfaceDesignResponse,
} from "./api";

interface BoundDraft {
  lower: string;
  upper: string;
}

interface ThresholdDraft {
  lower: string;
  target: string;
  upper: string;
}

interface ResponseOptimizerPanelProps {
  design: ResponseSurfaceDesignResponse;
  analysis: DoeResponseSurfaceAnalysisResponse;
}

export function ResponseOptimizerPanel({ design, analysis }: ResponseOptimizerPanelProps) {
  const responseRange = useMemo(() => {
    const values = analysis.result.contour.points.map((point) => point.predicted);
    return { minimum: Math.min(...values), maximum: Math.max(...values) };
  }, [analysis]);
  const [goal, setGoal] = useState<ResponseOptimizerGoal>("maximize");
  const [thresholds, setThresholds] = useState<ThresholdDraft>(() =>
    defaultThresholds("maximize", responseRange.minimum, responseRange.maximum),
  );
  const [lowerWeight, setLowerWeight] = useState("1");
  const [upperWeight, setUpperWeight] = useState("1");
  const [importance, setImportance] = useState("1");
  const [bounds, setBounds] = useState<Record<string, BoundDraft>>(() =>
    factorBounds(design),
  );
  const [linearEnabled, setLinearEnabled] = useState(false);
  const [linearRelation, setLinearRelation] = useState<
    "less_than_or_equal" | "greater_than_or_equal"
  >("less_than_or_equal");
  const [linearBound, setLinearBound] = useState("0");
  const [linearCoefficients, setLinearCoefficients] = useState<Record<string, string>>(() =>
    Object.fromEntries(design.factors.map((factor) => [factor.name, "0"])),
  );
  const [randomSeed, setRandomSeed] = useState("20260714");
  const [randomCandidates, setRandomCandidates] = useState("256");
  const [multiStarts, setMultiStarts] = useState("8");
  const [maxIterations, setMaxIterations] = useState("120");
  const [maxEvaluations, setMaxEvaluations] = useState("5000");
  const [timeBudgetMs, setTimeBudgetMs] = useState("5000");
  const [optimization, setOptimization] = useState<ResponseOptimizerResponse | null>(null);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestRevision = useRef(0);

  useEffect(() => {
    requestRevision.current += 1;
    setGoal("maximize");
    setThresholds(defaultThresholds("maximize", responseRange.minimum, responseRange.maximum));
    setBounds(factorBounds(design));
    setLinearEnabled(false);
    setLinearCoefficients(
      Object.fromEntries(design.factors.map((factor) => [factor.name, "0"])),
    );
    setOptimization(null);
    setIsOptimizing(false);
    setError(null);
    return () => {
      requestRevision.current += 1;
    };
  }, [analysis.analysis_id, design, responseRange.maximum, responseRange.minimum]);

  const changeGoal = (nextGoal: ResponseOptimizerGoal) => {
    setGoal(nextGoal);
    setThresholds(defaultThresholds(nextGoal, responseRange.minimum, responseRange.maximum));
    setOptimization(null);
  };

  const optimize = async () => {
    const request = optimizerRequest({
      analysis,
      design,
      goal,
      thresholds,
      lowerWeight,
      upperWeight,
      importance,
      bounds,
      linearEnabled,
      linearRelation,
      linearBound,
      linearCoefficients,
      randomSeed,
      randomCandidates,
      multiStarts,
      maxIterations,
      maxEvaluations,
      timeBudgetMs,
    });
    if (typeof request === "string") {
      setError(request);
      return;
    }
    const revision = ++requestRevision.current;
    setIsOptimizing(true);
    setOptimization(null);
    setError(null);
    try {
      const created = await createResponseOptimizer(design.design_id, request);
      if (requestRevision.current !== revision) return;
      setOptimization(created);
    } catch (caught) {
      if (requestRevision.current === revision) setError(errorCode(caught));
    } finally {
      if (requestRevision.current === revision) setIsOptimizing(false);
    }
  };

  return (
    <section className="analysis-result-section" aria-labelledby="response-optimizer-title">
      <div className="panel-heading compact-heading">
        <div>
          <h4 id="response-optimizer-title">Response Optimizer</h4>
          <p>regression.response_optimizer · source {analysis.response_name}</p>
        </div>
        <span className="status-pill status-ready">설계영역 제한</span>
      </div>
      <div className="option-grid">
        <label>
          <span>목표 유형</span>
          <select value={goal} onChange={(event) => changeGoal(event.currentTarget.value as ResponseOptimizerGoal)}>
            <option value="maximize">최대화</option>
            <option value="minimize">최소화</option>
            <option value="target">목표값</option>
            <option value="range">허용 범위</option>
          </select>
        </label>
        {goal !== "minimize" ? (
          <label>
            <span>{goal === "range" ? "허용 하한" : "완전 비선호 하한"}</span>
            <input
              aria-label="Optimizer lower"
              inputMode="decimal"
              value={thresholds.lower}
              onChange={(event) => setThresholds((current) => ({ ...current, lower: event.currentTarget.value }))}
            />
          </label>
        ) : null}
        {goal !== "range" ? (
          <label>
            <span>{goal === "target" ? "목표값" : "완전 선호 기준"}</span>
            <input
              aria-label="Optimizer target"
              inputMode="decimal"
              value={thresholds.target}
              onChange={(event) => setThresholds((current) => ({ ...current, target: event.currentTarget.value }))}
            />
          </label>
        ) : null}
        {goal !== "maximize" ? (
          <label>
            <span>{goal === "range" ? "허용 상한" : "완전 비선호 상한"}</span>
            <input
              aria-label="Optimizer upper"
              inputMode="decimal"
              value={thresholds.upper}
              onChange={(event) => setThresholds((current) => ({ ...current, upper: event.currentTarget.value }))}
            />
          </label>
        ) : null}
        <label>
          <span>하한 방향 shape</span>
          <input inputMode="decimal" value={lowerWeight} onChange={(event) => setLowerWeight(event.currentTarget.value)} />
        </label>
        <label>
          <span>상한 방향 shape</span>
          <input inputMode="decimal" value={upperWeight} onChange={(event) => setUpperWeight(event.currentTarget.value)} />
        </label>
        <label>
          <span>목표 importance</span>
          <input inputMode="decimal" value={importance} onChange={(event) => setImportance(event.currentTarget.value)} />
        </label>
      </div>

      <div className="table-wrap">
        <table className="result-table">
          <thead>
            <tr>
              <th>요인</th>
              <th>탐색 하한</th>
              <th>탐색 상한</th>
              {linearEnabled ? <th>선형 계수</th> : null}
            </tr>
          </thead>
          <tbody>
            {design.factors.map((factor) => (
              <tr key={factor.name}>
                <td>{factor.name}{factor.unit ? ` (${factor.unit})` : ""}</td>
                <td>
                  <input
                    aria-label={`${factor.name} optimizer lower bound`}
                    inputMode="decimal"
                    value={bounds[factor.name]?.lower ?? ""}
                    onChange={(event) => updateBound(setBounds, factor.name, "lower", event.currentTarget.value)}
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name} optimizer upper bound`}
                    inputMode="decimal"
                    value={bounds[factor.name]?.upper ?? ""}
                    onChange={(event) => updateBound(setBounds, factor.name, "upper", event.currentTarget.value)}
                  />
                </td>
                {linearEnabled ? (
                  <td>
                    <input
                      aria-label={`${factor.name} linear constraint coefficient`}
                      inputMode="decimal"
                      value={linearCoefficients[factor.name] ?? "0"}
                      onChange={(event) =>
                        setLinearCoefficients((current) => ({
                          ...current,
                          [factor.name]: event.currentTarget.value,
                        }))
                      }
                    />
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="option-grid">
        <label className="inline-option">
          <span>선형 제약 사용</span>
          <input type="checkbox" checked={linearEnabled} onChange={(event) => setLinearEnabled(event.currentTarget.checked)} />
        </label>
        {linearEnabled ? (
          <>
            <label>
              <span>제약 관계</span>
              <select
                value={linearRelation}
                onChange={(event) =>
                  setLinearRelation(
                    event.currentTarget.value as "less_than_or_equal" | "greater_than_or_equal",
                  )
                }
              >
                <option value="less_than_or_equal">합계 ≤ 경계</option>
                <option value="greater_than_or_equal">합계 ≥ 경계</option>
              </select>
            </label>
            <label>
              <span>제약 경계</span>
              <input inputMode="decimal" value={linearBound} onChange={(event) => setLinearBound(event.currentTarget.value)} />
            </label>
          </>
        ) : null}
        <label>
          <span>탐색 seed</span>
          <input inputMode="numeric" value={randomSeed} onChange={(event) => setRandomSeed(event.currentTarget.value)} />
        </label>
        <label>
          <span>초기 후보 수</span>
          <input inputMode="numeric" value={randomCandidates} onChange={(event) => setRandomCandidates(event.currentTarget.value)} />
        </label>
        <label>
          <span>Multi-start 수</span>
          <input inputMode="numeric" value={multiStarts} onChange={(event) => setMultiStarts(event.currentTarget.value)} />
        </label>
        <label>
          <span>시작점당 iteration</span>
          <input inputMode="numeric" value={maxIterations} onChange={(event) => setMaxIterations(event.currentTarget.value)} />
        </label>
        <label>
          <span>최대 평가 수</span>
          <input inputMode="numeric" value={maxEvaluations} onChange={(event) => setMaxEvaluations(event.currentTarget.value)} />
        </label>
        <label>
          <span>시간 budget (ms)</span>
          <input inputMode="numeric" value={timeBudgetMs} onChange={(event) => setTimeBudgetMs(event.currentTarget.value)} />
        </label>
      </div>
      <div className="button-row">
        <button type="button" className="primary-button" disabled={isOptimizing} onClick={() => void optimize()}>
          {isOptimizing ? "최적화 중" : "Response Optimizer 실행"}
        </button>
      </div>
      {error !== null ? <div className="error-box">오류 코드: {error}</div> : null}
      {optimization !== null ? <ResponseOptimizerResultView optimization={optimization} /> : null}
    </section>
  );
}

function ResponseOptimizerResultView({ optimization }: { optimization: ResponseOptimizerResponse }) {
  const { result } = optimization;
  return (
    <section className="analysis-result-section" aria-labelledby="response-optimizer-result-title">
      <div className="panel-heading compact-heading">
        <div>
          <h5 id="response-optimizer-result-title">권장 운전 조건</h5>
          <p>{optimization.method_id} v{optimization.method_version}</p>
        </div>
        <span className="status-pill status-ready">검증 저장됨</span>
      </div>
      <div className="metadata-grid" aria-label="Response Optimizer 결과 요약">
        <span>Composite desirability</span>
        <strong>{formatNumber(result.recommendation.composite_desirability)}</strong>
        <span>종료 이유</span>
        <strong>{result.search.termination_reason}</strong>
        <span>평가 / local starts</span>
        <strong>{result.search.evaluation_count} / {result.search.local_starts_attempted}</strong>
        <span>제약 충족</span>
        <strong>{result.recommendation.all_constraints_satisfied ? "예" : "아니오"}</strong>
        <span>전역 최적 보장</span>
        <strong>아니오</strong>
      </div>
      <div className="table-wrap">
        <table className="result-table">
          <thead><tr><th>요인</th><th>권장 실제값</th><th>Coded</th></tr></thead>
          <tbody>
            {Object.entries(result.recommendation.actual_coordinates).map(([factor, value]) => (
              <tr key={factor}>
                <td>{factor}</td>
                <td>{formatNumber(value)}</td>
                <td>{formatNumber(result.recommendation.coded_coordinates[factor])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-wrap">
        <table className="result-table">
          <thead><tr><th>반응</th><th>목표</th><th>예측</th><th>개별 desirability</th><th>Importance</th></tr></thead>
          <tbody>
            {result.recommendation.objectives.map((objective) => (
              <tr key={objective.source_analysis_id}>
                <td>{objective.response_name}</td>
                <td>{objective.goal}</td>
                <td>{formatNumber(objective.predicted_response)}</td>
                <td>{formatNumber(objective.individual_desirability)}</td>
                <td>{formatNumber(objective.importance)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {result.recommendation.constraints.length > 0 ? (
        <div className="table-wrap">
          <table className="result-table">
            <thead><tr><th>제약</th><th>좌변</th><th>경계</th><th>Slack</th><th>충족</th></tr></thead>
            <tbody>
              {result.recommendation.constraints.map((constraint) => (
                <tr key={constraint.name}>
                  <td>{constraint.name}</td>
                  <td>{formatNumber(constraint.lhs)}</td>
                  <td>{formatNumber(constraint.bound)}</td>
                  <td>{formatNumber(constraint.slack)}</td>
                  <td>{constraint.satisfied ? "예" : "아니오"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {result.warnings.map((warning) => (
        <div className="notice-box notice-warning" key={warning}>{warning}</div>
      ))}
    </section>
  );
}

function optimizerRequest(input: {
  analysis: DoeResponseSurfaceAnalysisResponse;
  design: ResponseSurfaceDesignResponse;
  goal: ResponseOptimizerGoal;
  thresholds: ThresholdDraft;
  lowerWeight: string;
  upperWeight: string;
  importance: string;
  bounds: Record<string, BoundDraft>;
  linearEnabled: boolean;
  linearRelation: "less_than_or_equal" | "greater_than_or_equal";
  linearBound: string;
  linearCoefficients: Record<string, string>;
  randomSeed: string;
  randomCandidates: string;
  multiStarts: string;
  maxIterations: string;
  maxEvaluations: string;
  timeBudgetMs: string;
}): ResponseOptimizerCreateRequest | string {
  const lower = input.goal === "minimize" ? null : Number(input.thresholds.lower);
  const target = input.goal === "range" ? null : Number(input.thresholds.target);
  const upper = input.goal === "maximize" ? null : Number(input.thresholds.upper);
  const lowerWeight = Number(input.lowerWeight);
  const upperWeight = Number(input.upperWeight);
  const importance = Number(input.importance);
  if (
    (lower !== null && !Number.isFinite(lower)) ||
    (target !== null && !Number.isFinite(target)) ||
    (upper !== null && !Number.isFinite(upper)) ||
    ![lowerWeight, upperWeight, importance].every((value) => Number.isFinite(value) && value > 0)
  ) {
    return "response_optimizer_objective_invalid";
  }
  const factorBounds = input.design.factors.map((factor) => ({
    factor_name: factor.name,
    lower: Number(input.bounds[factor.name]?.lower),
    upper: Number(input.bounds[factor.name]?.upper),
  }));
  if (
    factorBounds.some((bound, index) => {
      const factor = input.design.factors[index];
      return !Number.isFinite(bound.lower) || !Number.isFinite(bound.upper) || bound.lower < factor.low || bound.upper > factor.high || bound.lower >= bound.upper;
    })
  ) {
    return "response_optimizer_factor_bound_invalid";
  }
  const linearConstraints = [];
  if (input.linearEnabled) {
    const coefficients = Object.fromEntries(
      input.design.factors.map((factor) => [factor.name, Number(input.linearCoefficients[factor.name])]),
    );
    const bound = Number(input.linearBound);
    if (!Number.isFinite(bound) || Object.values(coefficients).some((value) => !Number.isFinite(value)) || Object.values(coefficients).every((value) => value === 0)) {
      return "response_optimizer_linear_constraint_invalid";
    }
    linearConstraints.push({
      name: "UI linear constraint",
      coefficients,
      relation: input.linearRelation,
      bound,
    });
  }
  const searchValues = [
    input.randomSeed,
    input.randomCandidates,
    input.multiStarts,
    input.maxIterations,
    input.maxEvaluations,
    input.timeBudgetMs,
  ].map((value) => Number.parseInt(value, 10));
  if (searchValues.some((value) => !Number.isInteger(value))) {
    return "response_optimizer_search_budget_invalid";
  }
  return {
    objectives: [{
      source_analysis_id: input.analysis.analysis_id,
      goal: input.goal,
      lower,
      target,
      upper,
      lower_weight: lowerWeight,
      upper_weight: upperWeight,
      importance,
    }],
    factor_bounds: factorBounds,
    linear_constraints: linearConstraints,
    search: {
      random_seed: searchValues[0],
      random_candidate_count: searchValues[1],
      multi_start_count: searchValues[2],
      max_iterations: searchValues[3],
      max_evaluations: searchValues[4],
      time_budget_ms: searchValues[5],
    },
  };
}

function defaultThresholds(goal: ResponseOptimizerGoal, minimum: number, maximum: number): ThresholdDraft {
  const spread = Math.max(maximum - minimum, Math.max(Math.abs(minimum), Math.abs(maximum), 1) * 0.1);
  if (goal === "maximize") return { lower: String(minimum), target: String(maximum), upper: "" };
  if (goal === "minimize") return { lower: "", target: String(minimum), upper: String(maximum) };
  if (goal === "target") return { lower: String(minimum), target: String((minimum + maximum) / 2), upper: String(maximum) };
  return { lower: String(minimum - spread * 0.1), target: "", upper: String(maximum + spread * 0.1) };
}

function factorBounds(design: ResponseSurfaceDesignResponse): Record<string, BoundDraft> {
  return Object.fromEntries(
    design.factors.map((factor) => [factor.name, { lower: String(factor.low), upper: String(factor.high) }]),
  );
}

function updateBound(
  setter: React.Dispatch<React.SetStateAction<Record<string, BoundDraft>>>,
  factorName: string,
  key: keyof BoundDraft,
  value: string,
) {
  setter((current) => ({
    ...current,
    [factorName]: { ...(current[factorName] ?? { lower: "", upper: "" }), [key]: value },
  }));
}

function errorCode(error: unknown): string {
  return error instanceof Error ? error.message : "response_optimizer_unknown_error";
}

function formatNumber(value: number): string {
  return Number.isFinite(value) ? value.toPrecision(6).replace(/\.?0+$/, "") : "-";
}
