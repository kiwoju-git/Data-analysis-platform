import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";

import {
  abandonBayesianTrial,
  createBayesianRecommendation,
  createBayesianStudy,
  fetchBayesianRecommendations,
  fetchBayesianStudies,
  fetchBayesianStudy,
  recordBayesianObservation,
  type BayesianRecommendationResponse,
  type BayesianStudyResponse,
  type BayesianStudySummaryResponse,
} from "./api";
import {
  buildBayesianStudyRequest,
  type ConstraintDraft,
  type FactorDraft,
} from "./bayesianStudyDraft";

const defaultSearch = {
  random_seed: 20260715,
  xi: 0.01,
  candidate_count: 256,
  local_start_count: 4,
  max_iterations: 100,
  max_evaluations: 4096,
  model_max_iterations: 50,
  model_max_evaluations: 200,
  hyperparameter_restart_count: 0,
  time_budget_ms: 15_000,
  jitter: 1e-8,
  duplicate_tolerance: 1e-6,
  total_trial_budget: 50,
};

export function BayesianOptimizationPanel() {
  const [studyName, setStudyName] = useState("Sequential process study");
  const [factors, setFactors] = useState<FactorDraft[]>([
    { key: 1, factorId: "x", name: "Input", low: "-1", high: "1", unit: "" },
  ]);
  const [objectiveName, setObjectiveName] = useState("Response");
  const [objectiveUnit, setObjectiveUnit] = useState("");
  const [direction, setDirection] = useState<"minimize" | "maximize">("maximize");
  const [initialDesignSize, setInitialDesignSize] = useState("2");
  const [initialDesignSeed, setInitialDesignSeed] = useState("20260715");
  const [constraints, setConstraints] = useState<ConstraintDraft[]>([]);
  const [studies, setStudies] = useState<BayesianStudySummaryResponse[]>([]);
  const [study, setStudy] = useState<BayesianStudyResponse | null>(null);
  const [recommendation, setRecommendation] =
    useState<BayesianRecommendationResponse | null>(null);
  const [observations, setObservations] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isSavingTrial, setIsSavingTrial] = useState(false);
  const [isRecommending, setIsRecommending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestRevision = useRef(0);
  const nextFactorKey = useRef(2);
  const nextConstraintKey = useRef(1);

  useEffect(() => {
    const revision = ++requestRevision.current;
    setIsLoading(true);
    void fetchBayesianStudies(0, 50)
      .then((response) => {
        if (requestRevision.current === revision) setStudies(response.items);
      })
      .catch((caught: unknown) => {
        if (requestRevision.current === revision) setError(errorCode(caught));
      })
      .finally(() => {
        if (requestRevision.current === revision) setIsLoading(false);
      });
    return () => {
      requestRevision.current += 1;
    };
  }, []);

  const restoreStudy = async (studyId: string) => {
    const revision = ++requestRevision.current;
    setIsLoading(true);
    setError(null);
    try {
      const [restored, recommendations] = await Promise.all([
        fetchBayesianStudy(studyId),
        fetchBayesianRecommendations(studyId, 0, 20),
      ]);
      if (requestRevision.current !== revision) return;
      setStudy(restored);
      setRecommendation(
        recommendations.items[recommendations.items.length - 1] ?? null,
      );
      setObservations({});
    } catch (caught) {
      if (requestRevision.current === revision) setError(errorCode(caught));
    } finally {
      if (requestRevision.current === revision) setIsLoading(false);
    }
  };

  const createStudy = async () => {
    const request = buildBayesianStudyRequest({
      studyName,
      factors,
      constraints,
      objectiveName,
      objectiveUnit,
      direction,
      initialDesignSize,
      initialDesignSeed,
    });
    if (typeof request === "string") {
      setError(request);
      return;
    }
    const revision = ++requestRevision.current;
    setIsCreating(true);
    setError(null);
    try {
      const created = await createBayesianStudy(request);
      const catalog = await fetchBayesianStudies(0, 50);
      if (requestRevision.current !== revision) return;
      setStudy(created);
      setStudies(catalog.items);
      setRecommendation(null);
      setObservations({});
    } catch (caught) {
      if (requestRevision.current === revision) setError(errorCode(caught));
    } finally {
      if (requestRevision.current === revision) setIsCreating(false);
    }
  };

  const transitionTrial = async (
    trialId: string,
    action: "complete" | "abandon",
  ) => {
    if (study === null) return;
    const objectiveValue = Number(observations[trialId]);
    if (action === "complete" && !Number.isFinite(objectiveValue)) {
      setError("bayesian_observation_invalid");
      return;
    }
    const revision = ++requestRevision.current;
    setIsSavingTrial(true);
    setError(null);
    try {
      if (action === "complete") {
        await recordBayesianObservation(study.study_id, trialId, {
          objective_value: objectiveValue,
          expected_history_revision_id: study.observation_history.history_revision_id,
        });
      } else {
        await abandonBayesianTrial(study.study_id, trialId);
      }
      const restored = await fetchBayesianStudy(study.study_id);
      if (requestRevision.current !== revision) return;
      setStudy(restored);
      setObservations((current) => ({ ...current, [trialId]: "" }));
    } catch (caught) {
      if (requestRevision.current === revision) setError(errorCode(caught));
    } finally {
      if (requestRevision.current === revision) setIsSavingTrial(false);
    }
  };

  const recommend = async () => {
    if (study === null) return;
    const revision = ++requestRevision.current;
    setIsRecommending(true);
    setError(null);
    try {
      const created = await createBayesianRecommendation(study.study_id, {
        expected_history_revision_id: study.observation_history.history_revision_id,
        search: defaultSearch,
      });
      const restored = await fetchBayesianStudy(study.study_id);
      if (requestRevision.current !== revision) return;
      setRecommendation(created);
      setStudy(restored);
    } catch (caught) {
      if (requestRevision.current === revision) setError(errorCode(caught));
    } finally {
      if (requestRevision.current === revision) setIsRecommending(false);
    }
  };

  return (
    <section className="analysis-run-panel" aria-labelledby="bayesian-optimization-title">
      <div className="panel-heading">
        <div>
          <h3 id="bayesian-optimization-title">Bayesian 최적화</h3>
          <p>doe.bayesian_optimization</p>
        </div>
        <span className="status-pill status-ready">전용 API</span>
      </div>

      <div className="info-box">
        앱은 목적함수를 실행하지 않습니다. 실제 실험 관측값만 입력하며, 추천 trial은 관측 전까지
        pending 상태입니다.
      </div>

      <div className="option-grid">
        <label>
          <span>Study 이름</span>
          <input value={studyName} onChange={(event) => setStudyName(event.currentTarget.value)} />
        </label>
        <label>
          <span>목적 반응</span>
          <input
            value={objectiveName}
            onChange={(event) => setObjectiveName(event.currentTarget.value)}
          />
        </label>
        <label>
          <span>반응 단위</span>
          <input
            value={objectiveUnit}
            onChange={(event) => setObjectiveUnit(event.currentTarget.value)}
          />
        </label>
        <label>
          <span>방향</span>
          <select
            value={direction}
            onChange={(event) =>
              setDirection(event.currentTarget.value as "minimize" | "maximize")
            }
          >
            <option value="maximize">최대화</option>
            <option value="minimize">최소화</option>
          </select>
        </label>
        <label>
          <span>초기 trial 수</span>
          <input
            inputMode="numeric"
            value={initialDesignSize}
            onChange={(event) => setInitialDesignSize(event.currentTarget.value)}
          />
        </label>
        <label>
          <span>초기 설계 seed</span>
          <input
            inputMode="numeric"
            value={initialDesignSeed}
            onChange={(event) => setInitialDesignSeed(event.currentTarget.value)}
          />
        </label>
      </div>

      <div className="table-wrap">
        <table className="result-table">
          <thead>
            <tr>
              <th>Factor ID</th>
              <th>표시 이름</th>
              <th>하한</th>
              <th>상한</th>
              <th>단위</th>
              <th>제거</th>
            </tr>
          </thead>
          <tbody>
            {factors.map((factor, index) => (
              <tr key={factor.key}>
                <td>
                  <input
                    aria-label={`요인 ${index + 1} ID`}
                    value={factor.factorId}
                    onChange={(event) =>
                      updateFactor(setFactors, factor.key, "factorId", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <input
                    aria-label={`요인 ${index + 1} 이름`}
                    value={factor.name}
                    onChange={(event) =>
                      updateFactor(setFactors, factor.key, "name", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name} 하한`}
                    inputMode="decimal"
                    value={factor.low}
                    onChange={(event) =>
                      updateFactor(setFactors, factor.key, "low", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name} 상한`}
                    inputMode="decimal"
                    value={factor.high}
                    onChange={(event) =>
                      updateFactor(setFactors, factor.key, "high", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <input
                    aria-label={`${factor.name} 단위`}
                    value={factor.unit}
                    onChange={(event) =>
                      updateFactor(setFactors, factor.key, "unit", event.currentTarget.value)
                    }
                  />
                </td>
                <td>
                  <button
                    type="button"
                    className="secondary-button"
                    disabled={factors.length === 1}
                    onClick={() =>
                      setFactors((current) => current.filter((item) => item.key !== factor.key))
                    }
                  >
                    제거
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="button-row">
        <button
          type="button"
          className="secondary-button"
          disabled={factors.length >= 6}
          onClick={() => {
            const key = nextFactorKey.current++;
            setFactors((current) => [
              ...current,
              {
                key,
                factorId: `x${key}`,
                name: `Input ${key}`,
                low: "-1",
                high: "1",
                unit: "",
              },
            ]);
          }}
        >
          요인 추가
        </button>
      </div>

      <div className="panel-heading">
        <div>
          <h4>실제 단위 선형 제약</h4>
          <p>각 제약은 입력한 factor 단위에서 계산되며 0이 아닌 계수가 필요합니다.</p>
        </div>
        <button
          type="button"
          className="secondary-button"
          disabled={constraints.length >= 16}
          onClick={() => {
            const key = nextConstraintKey.current++;
            setConstraints((current) => [
              ...current,
              {
                key,
                constraintId: `constraint_${key}`,
                name: `Constraint ${key}`,
                coefficients: {},
                relation: "less_than_or_equal",
                bound: "0",
              },
            ]);
          }}
        >
          제약 추가
        </button>
      </div>
      {constraints.length === 0 ? (
        <p className="cell-subtext">선형 제약이 없으면 선언한 factor bounds만 적용됩니다.</p>
      ) : (
        <div className="table-wrap">
          <table className="result-table">
            <thead>
              <tr>
                <th>제약 ID</th>
                <th>이름</th>
                {factors.map((factor) => (
                  <th key={factor.key}>{factor.factorId || `factor_${factor.key}`} 계수</th>
                ))}
                <th>관계</th>
                <th>우변</th>
                <th>제거</th>
              </tr>
            </thead>
            <tbody>
              {constraints.map((constraint, index) => (
                <tr key={constraint.key}>
                  <td>
                    <input
                      aria-label={`제약 ${index + 1} ID`}
                      value={constraint.constraintId}
                      onChange={(event) =>
                        updateConstraint(
                          setConstraints,
                          constraint.key,
                          "constraintId",
                          event.currentTarget.value,
                        )
                      }
                    />
                  </td>
                  <td>
                    <input
                      aria-label={`제약 ${index + 1} 이름`}
                      value={constraint.name}
                      onChange={(event) =>
                        updateConstraint(
                          setConstraints,
                          constraint.key,
                          "name",
                          event.currentTarget.value,
                        )
                      }
                    />
                  </td>
                  {factors.map((factor) => (
                    <td key={factor.key}>
                      <input
                        aria-label={`제약 ${index + 1} ${factor.factorId || `factor_${factor.key}`} 계수`}
                        inputMode="decimal"
                        value={constraint.coefficients[factor.key] ?? ""}
                        placeholder="0"
                        onChange={(event) =>
                          updateConstraintCoefficient(
                            setConstraints,
                            constraint.key,
                            factor.key,
                            event.currentTarget.value,
                          )
                        }
                      />
                    </td>
                  ))}
                  <td>
                    <select
                      aria-label={`제약 ${index + 1} 관계`}
                      value={constraint.relation}
                      onChange={(event) =>
                        updateConstraint(
                          setConstraints,
                          constraint.key,
                          "relation",
                          event.currentTarget.value as ConstraintDraft["relation"],
                        )
                      }
                    >
                      <option value="less_than_or_equal">≤</option>
                      <option value="greater_than_or_equal">≥</option>
                    </select>
                  </td>
                  <td>
                    <input
                      aria-label={`제약 ${index + 1} 우변`}
                      inputMode="decimal"
                      value={constraint.bound}
                      onChange={(event) =>
                        updateConstraint(
                          setConstraints,
                          constraint.key,
                          "bound",
                          event.currentTarget.value,
                        )
                      }
                    />
                  </td>
                  <td>
                    <button
                      type="button"
                      className="secondary-button"
                      aria-label={`제약 ${index + 1} 제거`}
                      onClick={() =>
                        setConstraints((current) =>
                          current.filter((item) => item.key !== constraint.key),
                        )
                      }
                    >
                      제거
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="button-row">
        <button
          type="button"
          className="primary-button"
          disabled={isCreating}
          onClick={() => void createStudy()}
        >
          {isCreating ? "생성 중" : "Study 생성"}
        </button>
      </div>

      <label>
        <span>저장된 study</span>
        <select
          aria-label="저장된 Bayesian study"
          value={study?.study_id ?? ""}
          disabled={isLoading}
          onChange={(event) => {
            if (event.currentTarget.value.length > 0) void restoreStudy(event.currentTarget.value);
          }}
        >
          <option value="">선택</option>
          {studies.map((item) => (
            <option key={item.study_id} value={item.study_id}>
              {item.name} · 완료 {item.completed_trial_count}
            </option>
          ))}
        </select>
      </label>

      {error !== null ? <div className="error-box">오류 코드: {error}</div> : null}

      {study !== null ? (
        <>
          <div className="metadata-grid" aria-label="Bayesian study 상태">
            <span>Method version</span>
            <strong>{study.method_version}</strong>
            <span>관측 history</span>
            <strong>revision {study.observation_history.revision_number}</strong>
            <span>완료 / 전체</span>
            <strong>
              {study.completed_trial_count} / {study.trial_count}
            </strong>
          </div>
          {study.constraints.length > 0 ? (
            <div className="table-wrap" aria-label="Bayesian stored constraints">
              <table className="result-table">
                <thead>
                  <tr>
                    <th>제약</th>
                    <th>실제 단위 식</th>
                  </tr>
                </thead>
                <tbody>
                  {study.constraints.map((constraint) => (
                    <tr key={constraint.constraint_id}>
                      <td>
                        <strong>{constraint.constraint_id}</strong>
                        <span className="cell-subtext">{constraint.name}</span>
                      </td>
                      <td>{constraintText(constraint)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
          <div className="table-wrap">
            <table className="result-table">
              <thead>
                <tr>
                  <th>Trial</th>
                  <th>종류</th>
                  <th>실제 조건</th>
                  <th>상태</th>
                  <th>관측값</th>
                  <th>처리</th>
                </tr>
              </thead>
              <tbody>
                {study.trials.map((trial) => (
                  <tr key={trial.trial_id}>
                    <td>{trial.trial_number}</td>
                    <td>{trial.origin === "recommendation" ? "추천" : "초기 설계"}</td>
                    <td>{coordinateText(trial.actual_coordinates)}</td>
                    <td>{trial.state}</td>
                    <td>
                      {trial.state === "pending" ? (
                        <input
                          aria-label={`Trial ${trial.trial_number} 관측값`}
                          inputMode="decimal"
                          value={observations[trial.trial_id] ?? ""}
                          onChange={(event) => {
                            const value = event.currentTarget.value;
                            setObservations((current) => ({
                              ...current,
                              [trial.trial_id]: value,
                            }));
                          }}
                        />
                      ) : (
                        trial.objective_value
                      )}
                    </td>
                    <td>
                      <div className="button-row">
                        <button
                          type="button"
                          className="primary-button"
                          disabled={trial.state !== "pending" || isSavingTrial}
                          onClick={() => void transitionTrial(trial.trial_id, "complete")}
                        >
                          관측 저장
                        </button>
                        <button
                          type="button"
                          className="secondary-button"
                          disabled={trial.state !== "pending" || isSavingTrial}
                          onClick={() => void transitionTrial(trial.trial_id, "abandon")}
                        >
                          Abandon
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="button-row">
            <button
              type="button"
              className="primary-button"
              disabled={!study.recommendation_available || isRecommending}
              onClick={() => void recommend()}
            >
              {isRecommending ? "GP/EI 계산 중" : "다음 실험 추천"}
            </button>
          </div>
          {!study.recommendation_available ? (
            <p className="cell-subtext">
              모든 초기 trial을 닫고 최소 관측 수를 충족해야 하며, pending 추천은 한 개만 허용됩니다.
            </p>
          ) : null}
        </>
      ) : null}

      {recommendation !== null ? (
        <section aria-labelledby="bayesian-recommendation-result-title">
          <div className="panel-heading">
            <div>
              <h4 id="bayesian-recommendation-result-title">추천 결과</h4>
              <p>관측값이 아닌 다음 확인 실험 후보입니다.</p>
            </div>
            <span className="status-pill status-warning">확인 실험 필요</span>
          </div>
          <div className="metadata-grid">
            <span>추천 조건</span>
            <strong>{coordinateText(recommendation.result.recommended_actual_coordinates)}</strong>
            <span>예측 평균</span>
            <strong>{formatNumber(recommendation.result.predicted_objective_mean)}</strong>
            <span>Posterior 표준편차</span>
            <strong>{formatNumber(recommendation.result.posterior_standard_deviation)}</strong>
            <span>Expected Improvement</span>
            <strong>{formatNumber(recommendation.result.expected_improvement)}</strong>
          </div>
          {recommendation.result.constraint_evaluations.length > 0 ? (
            <div className="table-wrap" aria-label="Bayesian recommendation constraints">
              <table className="result-table">
                <thead>
                  <tr>
                    <th>제약</th>
                    <th>좌변</th>
                    <th>관계</th>
                    <th>우변</th>
                    <th>Slack</th>
                    <th>상태</th>
                  </tr>
                </thead>
                <tbody>
                  {recommendation.result.constraint_evaluations.map((evaluation) => (
                    <tr key={evaluation.constraint_id}>
                      <td>{evaluation.constraint_id}</td>
                      <td>{formatNumber(evaluation.lhs)}</td>
                      <td>
                        {evaluation.relation === "less_than_or_equal" ? "≤" : "≥"}
                      </td>
                      <td>{formatNumber(evaluation.bound)}</td>
                      <td>{formatNumber(evaluation.slack)}</td>
                      <td>{evaluation.satisfied ? "충족" : "위반"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
          <ul className="warning-list">
            {recommendation.result.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
          <p className="cell-subtext">
            획득함수 탐색과 추천은 전역 최적을 보장하지 않습니다. 실제 확인 실험 결과를 저장한 뒤
            다음 추천을 생성하세요.
          </p>
        </section>
      ) : null}
    </section>
  );
}

function updateFactor(
  setter: Dispatch<SetStateAction<FactorDraft[]>>,
  key: number,
  field: keyof Omit<FactorDraft, "key">,
  value: string,
) {
  setter((current) =>
    current.map((factor) => (factor.key === key ? { ...factor, [field]: value } : factor)),
  );
}

function updateConstraint<Field extends "constraintId" | "name" | "relation" | "bound">(
  setter: Dispatch<SetStateAction<ConstraintDraft[]>>,
  key: number,
  field: Field,
  value: ConstraintDraft[Field],
) {
  setter((current) =>
    current.map((constraint) =>
      constraint.key === key ? { ...constraint, [field]: value } : constraint,
    ),
  );
}

function updateConstraintCoefficient(
  setter: Dispatch<SetStateAction<ConstraintDraft[]>>,
  key: number,
  factorKey: number,
  value: string,
) {
  setter((current) =>
    current.map((constraint) =>
      constraint.key === key
        ? {
            ...constraint,
            coefficients: { ...constraint.coefficients, [factorKey]: value },
          }
        : constraint,
    ),
  );
}

function constraintText(constraint: {
  terms: Array<{ factor_id: string; coefficient: number }>;
  relation: "less_than_or_equal" | "greater_than_or_equal";
  bound: number;
}) {
  const lhs = constraint.terms
    .map((term) => `${formatNumber(term.coefficient)}×${term.factor_id}`)
    .join(" + ");
  return `${lhs} ${constraint.relation === "less_than_or_equal" ? "≤" : "≥"} ${formatNumber(constraint.bound)}`;
}

function coordinateText(coordinates: Record<string, number>) {
  return Object.entries(coordinates)
    .map(([factorId, value]) => `${factorId}=${formatNumber(value)}`)
    .join(", ");
}

function formatNumber(value: number) {
  return Number.isFinite(value) ? value.toPrecision(6) : "-";
}

function errorCode(caught: unknown) {
  return caught instanceof Error ? caught.message : "bayesian_request_failed";
}
