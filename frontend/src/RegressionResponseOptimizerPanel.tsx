import { useEffect, useMemo, useState } from "react";

import type {
  LinearModelResult,
  RegressionResponseOptimizationProfile,
  RegressionResponseOptimizationRequest,
  RegressionResponseOptimizationResponse,
} from "./api";
import {
  createRegressionResponseOptimization,
  fetchRegressionResponseOptimizations,
} from "./api/regression";
import {
  InteractiveScatterChart,
  type InteractiveScatterPoint,
} from "./charts/InteractiveScatterChart";
import { paddedNumericRange } from "./charts/chartScale";

interface RegressionResponseOptimizerPanelProps {
  modelAvailable: boolean;
  result: LinearModelResult;
}

type GoalKind = "maximize" | "minimize" | "target" | "range";

export function RegressionResponseOptimizerPanel({
  modelAvailable,
  result,
}: RegressionResponseOptimizerPanelProps) {
  const model = result.model_manifest;
  const domains = useMemo(
    () => result.training_domain?.predictors ?? [],
    [result.training_domain],
  );
  const [goal, setGoal] = useState<GoalKind>("maximize");
  const [lower, setLower] = useState("0");
  const [target, setTarget] = useState("1");
  const [upper, setUpper] = useState("");
  const [bounds, setBounds] = useState<Record<string, { lower: string; upper: string }>>({});
  const [fixedLevels, setFixedLevels] = useState<Record<string, string>>({});
  const [response, setResponse] = useState<RegressionResponseOptimizationResponse | null>(null);
  const [historyCount, setHistoryCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    setBounds(
      Object.fromEntries(
        domains
          .filter((domain) => domain.kind === "numeric")
          .map((domain) => [
            domain.column_id,
            { lower: String(domain.minimum ?? ""), upper: String(domain.maximum ?? "") },
          ]),
      ),
    );
    setFixedLevels({});
    setResponse(null);
  }, [domains, model?.model_id]);

  useEffect(() => {
    if (!modelAvailable || !model) {
      setHistoryCount(0);
      return;
    }
    let active = true;
    void fetchRegressionResponseOptimizations(model.model_id)
      .then((payload) => {
        if (!active) return;
        setHistoryCount(payload.total);
        setResponse(payload.optimizations[0] ?? null);
      })
      .catch(() => {
        if (active) setHistoryCount(0);
      });
    return () => {
      active = false;
    };
  }, [model, modelAvailable]);

  const goalValues = useMemo(
    () => resolveGoalValues(goal, lower, target, upper),
    [goal, lower, target, upper],
  );
  const request = useMemo<RegressionResponseOptimizationRequest | null>(() => {
    if (!model || !goalValues) return null;
    const factorBounds = domains
      .filter((domain) => domain.kind === "numeric")
      .map((domain) => ({
        column_id: domain.column_id,
        lower: Number(bounds[domain.column_id]?.lower),
        upper: Number(bounds[domain.column_id]?.upper),
      }));
    if (factorBounds.some((bound) => !Number.isFinite(bound.lower) || !Number.isFinite(bound.upper) || bound.lower >= bound.upper)) {
      return null;
    }
    return {
      expected_model_manifest_sha256: model.manifest_sha256,
      goal: { kind: goal, ...goalValues },
      factor_bounds: factorBounds,
      fixed_categorical_levels: Object.entries(fixedLevels)
        .filter(([, level]) => level !== "")
        .map(([column_id, level]) => ({ column_id, level })),
      linear_constraints: [],
      search: {
        random_seed: 20260804,
        random_candidate_count: 512,
        multi_start_count: 8,
        max_iterations: 300,
        max_evaluations: 10_000,
        profile_point_count: 41,
      },
    };
  }, [bounds, domains, fixedLevels, goal, goalValues, model]);

  return (
    <section className="result-section" aria-labelledby="regression-response-optimizer-title">
      <div className="panel-heading">
        <div>
          <h4 id="regression-response-optimizer-title">회귀모형 기반 반응 최적화</h4>
          <p>최종 선택 모형과 회귀 학습 범위 안에서 목표에 맞는 predictor 설정을 탐색합니다.</p>
        </div>
        <span className="status-pill">저장 결과 {historyCount.toLocaleString()}건</span>
      </div>
      {!modelAvailable || !model || domains.length === 0 ? (
        <div className="notice-box">
          schema 5 manifest가 사용 가능한 저장 모델에서 최적화를 실행할 수 있습니다.
        </div>
      ) : (
        <>
          <div className="option-grid option-grid-wide">
            <label>
              <span>목표 유형</span>
              <select value={goal} onChange={(event) => setGoal(event.currentTarget.value as GoalKind)}>
                <option value="maximize">최대화</option>
                <option value="minimize">최소화</option>
                <option value="target">목표값</option>
                <option value="range">허용 범위</option>
              </select>
            </label>
            {goal !== "minimize" ? (
              <label>
                <span>{goal === "range" ? "허용 하한" : "하한"}</span>
                <input inputMode="decimal" type="number" value={lower} onChange={(event) => setLower(event.currentTarget.value)} />
              </label>
            ) : null}
            {goal !== "range" ? (
              <label>
                <span>{goal === "target" ? "목표값" : goal === "maximize" ? "충분히 높은 목표" : "충분히 낮은 목표"}</span>
                <input inputMode="decimal" type="number" value={target} onChange={(event) => setTarget(event.currentTarget.value)} />
              </label>
            ) : null}
            {goal !== "maximize" ? (
              <label>
                <span>{goal === "range" ? "허용 상한" : "상한"}</span>
                <input inputMode="decimal" type="number" value={upper} onChange={(event) => setUpper(event.currentTarget.value)} />
              </label>
            ) : null}
          </div>
          <div className="table-wrap">
            <table className="result-table">
              <thead>
                <tr>
                  <th>Predictor</th>
                  <th>종류</th>
                  <th>학습 범위/수준</th>
                  <th>검색 설정</th>
                </tr>
              </thead>
              <tbody>
                {domains.map((domain) => {
                  const predictor = result.predictors.find((item) => item.column_id === domain.column_id);
                  return (
                    <tr key={domain.column_id}>
                      <td>{predictor?.display_name ?? domain.column_id}</td>
                      <td>{domain.kind === "numeric" ? (domain.integer_only ? "정수형" : "연속형") : "범주형"}</td>
                      <td>
                        {domain.kind === "numeric"
                          ? `${formatNumber(domain.minimum)} - ${formatNumber(domain.maximum)}`
                          : domain.levels?.join(", ")}
                      </td>
                      <td>
                        {domain.kind === "numeric" ? (
                          <div className="inline-field-row">
                            <input
                              aria-label={`${predictor?.display_name ?? domain.column_id} 검색 하한`}
                              inputMode="decimal"
                              type="number"
                              value={bounds[domain.column_id]?.lower ?? ""}
                              onChange={(event) => setBounds((current) => ({ ...current, [domain.column_id]: { lower: event.currentTarget.value, upper: current[domain.column_id]?.upper ?? "" } }))}
                            />
                            <span>~</span>
                            <input
                              aria-label={`${predictor?.display_name ?? domain.column_id} 검색 상한`}
                              inputMode="decimal"
                              type="number"
                              value={bounds[domain.column_id]?.upper ?? ""}
                              onChange={(event) => setBounds((current) => ({ ...current, [domain.column_id]: { lower: current[domain.column_id]?.lower ?? "", upper: event.currentTarget.value } }))}
                            />
                          </div>
                        ) : (
                          <select
                            aria-label={`${predictor?.display_name ?? domain.column_id} 수준 제한`}
                            value={fixedLevels[domain.column_id] ?? ""}
                            onChange={(event) => setFixedLevels((current) => ({ ...current, [domain.column_id]: event.currentTarget.value }))}
                          >
                            <option value="">모든 학습 수준 탐색</option>
                            {domain.levels?.map((level) => <option key={level} value={level}>{level}</option>)}
                          </select>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="button-row">
            <button
              className="primary-button"
              disabled={isRunning || request === null}
              onClick={() => {
                if (!request || !model) return;
                setIsRunning(true);
                setError(null);
                void createRegressionResponseOptimization(model.model_id, request)
                  .then((payload) => {
                    setResponse(payload);
                    setHistoryCount((count) => count + 1);
                  })
                  .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "regression_response_optimizer_failed"))
                  .finally(() => setIsRunning(false));
              }}
              type="button"
            >
              {isRunning ? "최적화 중" : "반응 최적화 실행"}
            </button>
          </div>
          {request === null ? <div className="warning-box">목표 한계와 검색 범위를 확인하세요.</div> : null}
          {error ? <div className="error-box" role="alert">오류 코드: {error}</div> : null}
          {response ? <OptimizationResult response={response} result={result} /> : null}
        </>
      )}
    </section>
  );
}

function OptimizationResult({ response, result }: { response: RegressionResponseOptimizationResponse; result: LinearModelResult }) {
  const optimization = response.result;
  return (
    <div className="regression-optimizer-result">
      <div className="metadata-grid" aria-label="회귀 반응 최적화 결과">
        <span>예측 반응</span>
        <strong>{formatNumber(optimization.recommendation.predicted_response)}</strong>
        <span>Desirability</span>
        <strong>{formatNumber(optimization.recommendation.overall_desirability)}</strong>
        <span>학습 범위</span>
        <strong>{optimization.recommendation.within_training_domain ? "범위 안" : "범위 밖"}</strong>
        <span>탐색 종료</span>
        <strong>{optimization.search.termination_reason}</strong>
      </div>
      <div className="table-wrap">
        <table className="result-table">
          <thead><tr><th>Predictor</th><th>최적 설정</th></tr></thead>
          <tbody>
            {Object.entries(optimization.recommendation.predictor_settings).map(([columnId, value]) => (
              <tr key={columnId}>
                <td>{result.predictors.find((item) => item.column_id === columnId)?.display_name ?? columnId}</td>
                <td>{typeof value === "number" ? formatNumber(value) : value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="regression-optimizer-profile-grid">
        {optimization.profiles.map((profile) => <PredictorProfile key={profile.column_id} profile={profile} />)}
      </div>
      <div className="warning-box">
        이 최적값은 저장된 회귀모형과 지정 범위에 기반한 모델 예측입니다. 인과관계나
        전역 최적을 보장하지 않으며 확인 실험이 필요합니다.
      </div>
    </div>
  );
}

function PredictorProfile({ profile }: { profile: RegressionResponseOptimizationProfile }) {
  if (profile.kind === "categorical") {
    return (
      <div className="chart-panel regression-optimizer-profile-card regression-optimizer-categorical-profile">
        <div className="chart-panel-title">{profile.display_name} 조건부 프로파일</div>
        <div className="table-wrap regression-categorical-profile-table-wrap">
          <table className="result-table regression-categorical-profile-table">
            <thead><tr><th>수준</th><th>예측 반응</th><th>Desirability</th></tr></thead>
            <tbody>{profile.points.map((point) => (
              <tr key={String(point.predictor_value)}><td>{String(point.predictor_value)}</td><td>{formatNumber(point.predicted_response)}</td><td>{formatNumber(point.desirability)}</td></tr>
            ))}</tbody>
          </table>
        </div>
      </div>
    );
  }
  const numericPoints = profile.points.filter((point): point is typeof point & { predictor_value: number } => typeof point.predictor_value === "number");
  const points: InteractiveScatterPoint[] = numericPoints.map((point, index) => ({
    ariaLabel: `${profile.display_name} ${formatNumber(point.predictor_value)}, 예측 반응 ${formatNumber(point.predicted_response)}`,
    className: "profile-point",
    details: [
      { label: "Predictor", value: formatNumber(point.predictor_value) },
      { label: "예측 반응", value: formatNumber(point.predicted_response) },
      { label: "Desirability", value: formatNumber(point.desirability) },
    ],
    id: `regression-profile-${profile.column_id}-${index}`,
    title: `${profile.display_name} ${formatNumber(point.predictor_value)}`,
    x: point.predictor_value,
    y: point.predicted_response,
  }));
  return (
    <div className="chart-panel regression-optimizer-profile-card regression-optimizer-numeric-profile">
      <div className="chart-panel-title">{profile.display_name} 조건부 프로파일</div>
      <InteractiveScatterChart
        annotations={["다른 predictor는 최적 설정에 고정"]}
        chartId={`regression-profile-${profile.column_id}`}
        compact
        connectPoints="line"
        description={`${profile.display_name}만 변화시키고 다른 predictor를 최적 설정에 고정한 조건부 예측 단면입니다.`}
        emptyLabel="프로파일 point 없음"
        formatValue={formatNumber}
        points={points}
        title={`${profile.display_name} Predictor Profile`}
        xLabel={profile.display_name}
        xRange={paddedNumericRange(points.map((point) => point.x))}
        yLabel="Predicted response"
        yRange={paddedNumericRange(points.map((point) => point.y))}
      />
    </div>
  );
}

function resolveGoalValues(goal: GoalKind, lower: string, target: string, upper: string) {
  const values = { lower: numberOrNull(lower), target: numberOrNull(target), upper: numberOrNull(upper) };
  if (goal === "maximize") return values.lower !== null && values.target !== null && values.lower < values.target ? { lower: values.lower, target: values.target, upper: null } : null;
  if (goal === "minimize") return values.target !== null && values.upper !== null && values.target < values.upper ? { lower: null, target: values.target, upper: values.upper } : null;
  if (goal === "target") return values.lower !== null && values.target !== null && values.upper !== null && values.lower < values.target && values.target < values.upper ? values : null;
  return values.lower !== null && values.upper !== null && values.lower < values.upper ? { lower: values.lower, target: null, upper: values.upper } : null;
}

function numberOrNull(value: string): number | null {
  const parsed = Number(value);
  return value.trim() !== "" && Number.isFinite(parsed) ? parsed : null;
}

function formatNumber(value: number | undefined): string {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toLocaleString("ko-KR", { maximumFractionDigits: 6 })
    : "-";
}
