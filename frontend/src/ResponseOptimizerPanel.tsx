import { useEffect, useMemo, useRef, useState } from "react";

import {
  createResponseOptimizer,
  type DoeResponseSurfaceAnalysisResponse,
  type ResponseOptimizerCreateRequest,
  type ResponseOptimizerEligibilityIssue,
  type ResponseOptimizerGoal,
  type ResponseOptimizerResponse,
  type ResponseSurfaceDesignResponse,
} from "./api";
import {
  DoeActionBar,
  DoeAdvancedSettings,
  DoeFactorEditor,
  DoeFormSection,
} from "./doe/DoeFormPrimitives";
import { DoeSettingsTable } from "./doe/DoeSettingsTable";

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
  initialOptimization?: ResponseOptimizerResponse | null;
  onOptimizationCreated?: (optimization: ResponseOptimizerResponse) => void;
}

export function ResponseOptimizerPanel({
  design,
  analysis,
  initialOptimization = null,
  onOptimizationCreated,
}: ResponseOptimizerPanelProps) {
  const responseRange = useMemo(() => {
    const values = analysis.result.contour.points.map((point) => point.predicted);
    return { minimum: Math.min(...values), maximum: Math.max(...values) };
  }, [analysis]);
  const sourceEligibility = useMemo(
    () => responseOptimizerSourceEligibility(analysis),
    [analysis],
  );
  const blockingIssues = sourceEligibility.filter((issue) => issue.severity === "blocking");
  const acknowledgmentIssues = sourceEligibility.filter(
    (issue) => issue.severity === "acknowledgment_required",
  );
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
  const [sourceWarningsAcknowledged, setSourceWarningsAcknowledged] = useState(false);
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
    setOptimization(
      initialOptimization !== null &&
        initialOptimization.design_id === design.design_id &&
        initialOptimization.source_analysis_ids.length === 1 &&
        initialOptimization.source_analysis_ids[0] === analysis.analysis_id
        ? initialOptimization
        : null,
    );
    setIsOptimizing(false);
    setError(null);
    setSourceWarningsAcknowledged(false);
    return () => {
      requestRevision.current += 1;
    };
  }, [
    analysis.analysis_id,
    design,
    initialOptimization,
    responseRange.maximum,
    responseRange.minimum,
  ]);

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
      acknowledgedSourceWarningCodes: sourceWarningsAcknowledged
        ? acknowledgmentIssues.map((issue) => issue.code)
        : [],
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
      onOptimizationCreated?.(created);
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
          <p>doe.response_optimizer · source {analysis.response_name}</p>
        </div>
        <span className="status-pill status-ready">설계영역 제한</span>
      </div>
      {blockingIssues.map((issue) => (
        <div className="notice-box notice-warning" key={issue.code} role="alert">
          차단: {issue.code}
        </div>
      ))}
      {acknowledgmentIssues.length > 0 ? (
        <label className="inline-option">
          <input
            type="checkbox"
            checked={sourceWarningsAcknowledged}
            onChange={(event) => setSourceWarningsAcknowledged(event.currentTarget.checked)}
          />
          <span>
            source 모형 진단 경고를 검토했습니다: {acknowledgmentIssues.map((issue) => issue.code).join(", ")}
          </span>
        </label>
      ) : null}
      <DoeFormSection
        title="목적 반응 설정"
        description={`${analysis.response_name}의 desirability 목표와 중요도를 정합니다.`}
      >
        <DoeSettingsTable
          ariaLabel="Response Optimizer 목적 반응 설정"
          fields={[
            {
              key: "goal",
              label: "목표 유형",
              controlId: "optimizer-goal",
              control: (
                <select
                  id="optimizer-goal"
                  value={goal}
                  onChange={(event) =>
                    changeGoal(event.currentTarget.value as ResponseOptimizerGoal)
                  }
                >
                  <option value="maximize">최대화</option>
                  <option value="minimize">최소화</option>
                  <option value="target">목표값</option>
                  <option value="range">허용 범위</option>
                </select>
              ),
            },
            ...(goal !== "minimize"
              ? [
                  {
                    key: "lower",
                    label: goal === "range" ? "허용 하한" : "완전 비선호 하한",
                    controlId: "optimizer-lower",
                    control: (
                      <input
                        id="optimizer-lower"
                        aria-label="Optimizer lower"
                        inputMode="decimal"
                        value={thresholds.lower}
                        onChange={(event) =>
                          setThresholds((current) => ({
                            ...current,
                            lower: event.currentTarget.value,
                          }))
                        }
                      />
                    ),
                  },
                ]
              : []),
            ...(goal !== "range"
              ? [
                  {
                    key: "target",
                    label: goal === "target" ? "목표값" : "완전 선호 기준",
                    controlId: "optimizer-target",
                    control: (
                      <input
                        id="optimizer-target"
                        aria-label="Optimizer target"
                        inputMode="decimal"
                        value={thresholds.target}
                        onChange={(event) =>
                          setThresholds((current) => ({
                            ...current,
                            target: event.currentTarget.value,
                          }))
                        }
                      />
                    ),
                  },
                ]
              : []),
            ...(goal !== "maximize"
              ? [
                  {
                    key: "upper",
                    label: goal === "range" ? "허용 상한" : "완전 비선호 상한",
                    controlId: "optimizer-upper",
                    control: (
                      <input
                        id="optimizer-upper"
                        aria-label="Optimizer upper"
                        inputMode="decimal"
                        value={thresholds.upper}
                        onChange={(event) =>
                          setThresholds((current) => ({
                            ...current,
                            upper: event.currentTarget.value,
                          }))
                        }
                      />
                    ),
                  },
                ]
              : []),
          ]}
        />
        <DoeSettingsTable
          ariaLabel="Response Optimizer desirability 설정"
          fields={[
            {
              key: "lower-weight",
              label: "하한 방향 shape",
              controlId: "optimizer-lower-weight",
              control: (
                <input
                  id="optimizer-lower-weight"
                  inputMode="decimal"
                  value={lowerWeight}
                  onChange={(event) => setLowerWeight(event.currentTarget.value)}
                />
              ),
            },
            {
              key: "upper-weight",
              label: "상한 방향 shape",
              controlId: "optimizer-upper-weight",
              control: (
                <input
                  id="optimizer-upper-weight"
                  inputMode="decimal"
                  value={upperWeight}
                  onChange={(event) => setUpperWeight(event.currentTarget.value)}
                />
              ),
            },
            {
              key: "importance",
              label: "목표 importance",
              controlId: "optimizer-importance",
              control: (
                <input
                  id="optimizer-importance"
                  inputMode="decimal"
                  value={importance}
                  onChange={(event) => setImportance(event.currentTarget.value)}
                />
              ),
            },
          ]}
        />
      </DoeFormSection>

      <DoeFactorEditor
        title="요인 검색 범위"
        description="RSM 설계 범위 안에서 최적화가 탐색할 하한과 상한을 정합니다."
      >
        <div className="table-wrap">
          <table className="result-table doe-factor-table response-optimizer-factor-table">
            <thead>
              <tr>
                <th>요인</th>
                <th>설계 범위</th>
                <th>탐색 하한</th>
                <th>탐색 상한</th>
                {linearEnabled ? <th>선형 계수</th> : null}
              </tr>
            </thead>
            <tbody>
              {design.factors.map((factor) => (
                <tr key={factor.name}>
                  <td>{factor.name}{factor.unit ? ` (${factor.unit})` : ""}</td>
                  <td>{formatNumber(factor.low)} – {formatNumber(factor.high)}</td>
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
      </DoeFactorEditor>

      <DoeFormSection
        title="제약조건"
        description="필요한 경우 실제 단위 선형 제약을 활성화합니다."
      >
        <DoeSettingsTable
          ariaLabel="Response Optimizer 제약조건 설정"
          fields={[
            {
              key: "enabled",
              label: "선형 제약 사용",
              controlId: "optimizer-linear-enabled",
              control: (
                <label className="doe-table-toggle" htmlFor="optimizer-linear-enabled">
                  <input
                    id="optimizer-linear-enabled"
                    type="checkbox"
                    checked={linearEnabled}
                    onChange={(event) => setLinearEnabled(event.currentTarget.checked)}
                  />
                  <span>사용</span>
                </label>
              ),
            },
            ...(linearEnabled
              ? [
                  {
                    key: "relation",
                    label: "제약 관계",
                    controlId: "optimizer-linear-relation",
                    control: (
                      <select
                        id="optimizer-linear-relation"
                        value={linearRelation}
                        onChange={(event) =>
                          setLinearRelation(
                            event.currentTarget.value as
                              | "less_than_or_equal"
                              | "greater_than_or_equal",
                          )
                        }
                      >
                        <option value="less_than_or_equal">합계 ≤ 경계</option>
                        <option value="greater_than_or_equal">합계 ≥ 경계</option>
                      </select>
                    ),
                  },
                  {
                    key: "bound",
                    label: "제약 경계",
                    controlId: "optimizer-linear-bound",
                    control: (
                      <input
                        id="optimizer-linear-bound"
                        inputMode="decimal"
                        value={linearBound}
                        onChange={(event) => setLinearBound(event.currentTarget.value)}
                      />
                    ),
                  },
                ]
              : []),
          ]}
        />
      </DoeFormSection>
      <DoeAdvancedSettings
        summaryText={`seed ${randomSeed} · 후보 ${randomCandidates}개`}
      >
        <DoeSettingsTable
          ariaLabel="Response Optimizer 고급 탐색 설정 1"
          fields={[
            {
              key: "seed",
              label: "탐색 seed",
              controlId: "optimizer-search-seed",
              control: (
                <input
                  id="optimizer-search-seed"
                  inputMode="numeric"
                  value={randomSeed}
                  onChange={(event) => setRandomSeed(event.currentTarget.value)}
                />
              ),
            },
            {
              key: "candidates",
              label: "초기 후보 수",
              controlId: "optimizer-random-candidates",
              control: (
                <input
                  id="optimizer-random-candidates"
                  inputMode="numeric"
                  value={randomCandidates}
                  onChange={(event) => setRandomCandidates(event.currentTarget.value)}
                />
              ),
            },
            {
              key: "starts",
              label: "Multi-start 수",
              controlId: "optimizer-multi-starts",
              control: (
                <input
                  id="optimizer-multi-starts"
                  inputMode="numeric"
                  value={multiStarts}
                  onChange={(event) => setMultiStarts(event.currentTarget.value)}
                />
              ),
            },
          ]}
        />
        <DoeSettingsTable
          ariaLabel="Response Optimizer 고급 탐색 설정 2"
          fields={[
            {
              key: "iterations",
              label: "시작점당 iteration",
              controlId: "optimizer-max-iterations",
              control: (
                <input
                  id="optimizer-max-iterations"
                  inputMode="numeric"
                  value={maxIterations}
                  onChange={(event) => setMaxIterations(event.currentTarget.value)}
                />
              ),
            },
            {
              key: "evaluations",
              label: "최대 평가 수",
              controlId: "optimizer-max-evaluations",
              control: (
                <input
                  id="optimizer-max-evaluations"
                  inputMode="numeric"
                  value={maxEvaluations}
                  onChange={(event) => setMaxEvaluations(event.currentTarget.value)}
                />
              ),
            },
            {
              key: "time",
              label: "시간 budget (ms)",
              controlId: "optimizer-time-budget",
              control: (
                <input
                  id="optimizer-time-budget"
                  inputMode="numeric"
                  value={timeBudgetMs}
                  onChange={(event) => setTimeBudgetMs(event.currentTarget.value)}
                />
              ),
            },
          ]}
        />
      </DoeAdvancedSettings>
      <DoeActionBar summary="설계영역과 제약을 검증한 뒤 최적화를 실행합니다.">
        <button
          type="button"
          className="primary-button"
          disabled={
            isOptimizing ||
            blockingIssues.length > 0 ||
            (acknowledgmentIssues.length > 0 && !sourceWarningsAcknowledged)
          }
          onClick={() => void optimize()}
        >
          {isOptimizing ? "최적화 중" : "Response Optimizer 실행"}
        </button>
      </DoeActionBar>
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
      {result.source_model_eligibility.issues.map((issue) => (
        <div className="notice-box" key={`${issue.source_analysis_id ?? "optimizer"}-${issue.code}`}>
          {issue.severity}: {issue.code}
        </div>
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
  acknowledgedSourceWarningCodes: string[];
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
    acknowledged_source_warning_codes: input.acknowledgedSourceWarningCodes,
  };
}

function responseOptimizerSourceEligibility(
  analysis: DoeResponseSurfaceAnalysisResponse,
): ResponseOptimizerEligibilityIssue[] {
  const { result } = analysis;
  const issues: ResponseOptimizerEligibilityIssue[] = [];
  const add = (
    code: string,
    severity: ResponseOptimizerEligibilityIssue["severity"],
    sourceWarningCode: string | null = null,
  ) => {
    issues.push({
      source_analysis_id: analysis.analysis_id,
      code,
      severity,
      source_warning_code: sourceWarningCode,
    });
  };
  const confidenceLevel =
    result.terms.find((term) => term.confidence_interval !== null)?.confidence_interval?.level ??
    0.95;

  if (result.sample.rank !== result.sample.parameter_count) {
    add("response_optimizer_source_model_rank_invalid", "blocking");
  }
  if (result.sample.df_residual <= 0) {
    add(
      "response_optimizer_source_model_saturated",
      "blocking",
      "doe_rsm_model_saturated_no_inference",
    );
  } else {
    const residualVariance = result.fit.residual_mean_square;
    const residualStandardError = result.fit.residual_standard_error;
    if (
      residualVariance === null ||
      !Number.isFinite(residualVariance) ||
      residualVariance <= 0 ||
      residualStandardError === null ||
      !Number.isFinite(residualStandardError) ||
      residualStandardError <= 0
    ) {
      add(
        "response_optimizer_source_residual_variance_unusable",
        "blocking",
        "doe_rsm_residual_variance_zero",
      );
    }
    if (result.sample.df_residual < 5) {
      add(
        "response_optimizer_source_residual_df_small",
        "acknowledgment_required",
        "doe_rsm_residual_df_small",
      );
    }
  }
  const lackOfFit = result.anova.lack_of_fit;
  const lackOfFitP = lackOfFit.lack_of_fit.p_value;
  if (
    lackOfFit.available &&
    lackOfFitP !== null &&
    Number.isFinite(lackOfFitP) &&
    lackOfFitP < 1 - confidenceLevel
  ) {
    add("response_optimizer_source_lack_of_fit_significant", "blocking");
  }
  if (result.diagnostics.high_cooks_distance_count > 0) {
    add(
      "response_optimizer_source_influential_run",
      "acknowledgment_required",
      "doe_rsm_influential_run_detected",
    );
  }
  if (result.diagnostics.high_leverage_count > 0) {
    add("response_optimizer_source_high_leverage", "acknowledgment_required");
  }
  if (result.diagnostics.high_standardized_residual_count > 0) {
    add(
      "response_optimizer_source_large_standardized_residual",
      "acknowledgment_required",
      "doe_rsm_large_standardized_residual",
    );
  }
  const normalityP = result.diagnostics.shapiro_wilk.p_value;
  if (normalityP !== null && Number.isFinite(normalityP) && normalityP < 0.01) {
    add("response_optimizer_source_residual_normality_severe", "acknowledgment_required");
  }
  add(
    "response_optimizer_source_model_associational",
    "informational",
    "doe_rsm_model_is_associational_not_causal",
  );
  if (result.factor_names.length > 2) {
    add(
      "response_optimizer_source_contour_slice_limited",
      "informational",
      "doe_rsm_contour_holds_other_factors_at_center",
    );
  }
  issues.push(
    {
      source_analysis_id: null,
      code: "response_optimizer_global_optimum_not_guaranteed",
      severity: "informational",
      source_warning_code: null,
    },
    {
      source_analysis_id: null,
      code: "response_optimizer_confirmation_run_required",
      severity: "informational",
      source_warning_code: null,
    },
  );
  return issues;
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
