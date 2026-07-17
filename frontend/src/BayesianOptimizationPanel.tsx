import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";

import {
  abandonBayesianTrial,
  closeBayesianStudy,
  createBayesianRecommendation,
  createBayesianStudy,
  deleteBayesianStudy,
  fetchLatestBayesianRecommendation,
  fetchBayesianStudies,
  fetchBayesianStudy,
  fetchBayesianStudyDeletionPreflight,
  recordBayesianObservation,
  type BayesianRecommendationResponse,
  type BayesianStudyCloseReason,
  type BayesianStudyDeletionPreflightResponse,
  type BayesianStudyResponse,
  type BayesianStudySummaryResponse,
  type BayesianTrialResponse,
} from "./api";
import {
  buildBayesianStudyRequest,
  bayesianRecommendationBudgetBlocker,
  bayesianRecommendationStatus,
  bayesianStudyCloseBlocker,
  minimumBayesianInitialDesignSize,
  type ConstraintDraft,
  type FactorDraft,
} from "./bayesianStudyDraft";
import { getAnalysisRunErrorDetails } from "./analysisRunErrors";

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

type PendingTrialTransition = {
  trialId: string;
  action: "complete" | "abandon";
};

type StudyCloseTarget = "completed" | "abandoned";

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
  const [totalTrialBudget, setTotalTrialBudget] = useState(
    String(defaultSearch.total_trial_budget),
  );
  const [observations, setObservations] = useState<Record<string, string>>({});
  const [pendingTransition, setPendingTransition] =
    useState<PendingTrialTransition | null>(null);
  const [closeTarget, setCloseTarget] = useState<StudyCloseTarget>("completed");
  const [closeReason, setCloseReason] =
    useState<BayesianStudyCloseReason>("confirmation_complete");
  const [closeNote, setCloseNote] = useState("");
  const [pendingStudyClose, setPendingStudyClose] = useState(false);
  const [deletionPreflight, setDeletionPreflight] =
    useState<BayesianStudyDeletionPreflightResponse | null>(null);
  const [pendingStudyDeletion, setPendingStudyDeletion] = useState(false);
  const [predecessorStudyId, setPredecessorStudyId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isSavingTrial, setIsSavingTrial] = useState(false);
  const [isRecommending, setIsRecommending] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const [isCheckingDeletion, setIsCheckingDeletion] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestRevision = useRef(0);
  const nextFactorKey = useRef(2);
  const nextConstraintKey = useRef(1);

  useEffect(() => {
    const minimum = minimumBayesianInitialDesignSize(factors.length);
    setInitialDesignSize((current) => {
      const parsed = Number(current);
      return Number.isInteger(parsed) && parsed < minimum ? String(minimum) : current;
    });
  }, [factors.length]);

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
    setIsCheckingDeletion(false);
    setError(null);
    setDeletionPreflight(null);
    setPendingStudyDeletion(false);
    try {
      const [restored, latest] = await Promise.all([
        fetchBayesianStudy(studyId),
        fetchLatestBayesianRecommendation(studyId),
      ]);
      if (requestRevision.current !== revision) return;
      setStudy(restored);
      setRecommendation(latest.item);
      if (latest.item?.requested_total_trial_budget !== null && latest.item?.requested_total_trial_budget !== undefined) {
        setTotalTrialBudget(String(latest.item.requested_total_trial_budget));
      }
      setObservations({});
      setPendingTransition(null);
      setPendingStudyClose(false);
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
      const created = await createBayesianStudy({
        ...request,
        predecessor_study_id: predecessorStudyId,
      });
      const catalog = await fetchBayesianStudies(0, 50);
      if (requestRevision.current !== revision) return;
      setStudy(created);
      setStudies(catalog.items);
      setRecommendation(null);
      setObservations({});
      setPendingTransition(null);
      setDeletionPreflight(null);
      setPendingStudyDeletion(false);
      setTotalTrialBudget(String(defaultSearch.total_trial_budget));
      setPredecessorStudyId(null);
    } catch (caught) {
      if (requestRevision.current === revision) setError(errorCode(caught));
    } finally {
      if (requestRevision.current === revision) setIsCreating(false);
    }
  };

  const requestTrialTransition = (
    trialId: string,
    action: "complete" | "abandon",
  ) => {
    if (action === "complete" && !Number.isFinite(Number(observations[trialId]))) {
      setError("bayesian_observation_invalid");
      return;
    }
    setError(null);
    setPendingTransition({ trialId, action });
  };

  const transitionTrial = async () => {
    if (pendingTransition === null) return;
    const { trialId, action } = pendingTransition;
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
        await abandonBayesianTrial(
          study.study_id,
          trialId,
          closeTarget === "abandoned"
            ? {
                expected_history_revision_id:
                  study.observation_history.history_revision_id,
                intent: "close_study",
              }
            : undefined,
        );
      }
      const [restored, latest] = await Promise.all([
        fetchBayesianStudy(study.study_id),
        fetchLatestBayesianRecommendation(study.study_id),
      ]);
      if (requestRevision.current !== revision) return;
      setStudy(restored);
      setRecommendation(latest.item);
      setObservations((current) => ({ ...current, [trialId]: "" }));
      setPendingTransition(null);
    } catch (caught) {
      if (requestRevision.current === revision) setError(errorCode(caught));
    } finally {
      if (requestRevision.current === revision) setIsSavingTrial(false);
    }
  };

  const recommend = async () => {
    if (study === null) return;
    const parsedTotalTrialBudget = Number(totalTrialBudget);
    if (
      !Number.isInteger(parsedTotalTrialBudget) ||
      parsedTotalTrialBudget < 2 ||
      parsedTotalTrialBudget > study.recommendation_hard_trial_limit
    ) {
      setError("bayesian_optimization_trial_budget_invalid");
      return;
    }
    const revision = ++requestRevision.current;
    setIsRecommending(true);
    setError(null);
    try {
      const created = await createBayesianRecommendation(study.study_id, {
        expected_history_revision_id: study.observation_history.history_revision_id,
        search: { ...defaultSearch, total_trial_budget: parsedTotalTrialBudget },
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

  const closeStudy = async () => {
    if (study === null || study.status !== "active") return;
    const revision = ++requestRevision.current;
    setIsClosing(true);
    setError(null);
    try {
      const response = await closeBayesianStudy(study.study_id, {
        target_status: closeTarget,
        reason_code: closeReason,
        note: closeNote.trim() || null,
        request_id: crypto.randomUUID(),
        expected_study_version_id: study.study_version_id,
        expected_history_revision_id: study.observation_history.history_revision_id,
        expected_observation_history_sha256:
          study.observation_history.observation_history_sha256,
      });
      const catalog = await fetchBayesianStudies(0, 50);
      if (requestRevision.current !== revision) return;
      setStudy(response.study);
      setStudies(catalog.items);
      setPendingStudyClose(false);
      setPendingTransition(null);
      setDeletionPreflight(null);
      setPendingStudyDeletion(false);
    } catch (caught) {
      if (requestRevision.current === revision) setError(errorCode(caught));
    } finally {
      if (requestRevision.current === revision) setIsClosing(false);
    }
  };

  const prepareSuccessor = () => {
    if (study === null || study.status === "active") return;
    const nextFactors = study.factors.map((factor, index) => ({
      key: index + 1,
      factorId: factor.factor_id,
      name: factor.name,
      low: String(factor.low),
      high: String(factor.high),
      unit: factor.unit ?? "",
    }));
    const factorKeyById = new Map(
      nextFactors.map((factor) => [factor.factorId, factor.key]),
    );
    setStudyName(`${study.name} successor`);
    setFactors(nextFactors);
    setObjectiveName(study.objective.name);
    setObjectiveUnit(study.objective.unit ?? "");
    setDirection(study.objective.direction);
    setInitialDesignSize(String(study.initial_design.requested_size));
    setInitialDesignSeed(String(study.initial_design.seed));
    setConstraints(
      study.constraints.map((constraint, index) => ({
        key: index + 1,
        constraintId: constraint.constraint_id,
        name: constraint.name,
        coefficients: Object.fromEntries(
          constraint.terms.flatMap((term) => {
            const key = factorKeyById.get(term.factor_id);
            return key === undefined ? [] : [[key, String(term.coefficient)]];
          }),
        ),
        relation: constraint.relation,
        bound: String(constraint.bound),
      })),
    );
    nextFactorKey.current = nextFactors.length + 1;
    nextConstraintKey.current = study.constraints.length + 1;
    setPredecessorStudyId(study.study_id);
    setDeletionPreflight(null);
    setPendingStudyDeletion(false);
    setError(null);
  };

  const checkDeletionImpact = async () => {
    if (study === null || study.status === "active") return;
    const studyId = study.study_id;
    const revision = ++requestRevision.current;
    setIsCheckingDeletion(true);
    setPendingStudyDeletion(false);
    setError(null);
    try {
      const preflight = await fetchBayesianStudyDeletionPreflight(studyId);
      if (requestRevision.current !== revision || preflight.study_id !== studyId) return;
      setDeletionPreflight(preflight);
    } catch (caught) {
      if (requestRevision.current === revision) setError(errorCode(caught));
    } finally {
      if (requestRevision.current === revision) setIsCheckingDeletion(false);
    }
  };

  const deleteStudy = async () => {
    if (
      study === null ||
      deletionPreflight === null ||
      !deletionPreflight.eligible ||
      deletionPreflight.study_id !== study.study_id
    ) {
      return;
    }
    const studyId = study.study_id;
    const revision = ++requestRevision.current;
    setIsDeleting(true);
    setError(null);
    try {
      await deleteBayesianStudy(studyId, {
        confirmation_study_id: studyId,
        expected_deletion_manifest_sha256:
          deletionPreflight.deletion_manifest_sha256,
      });
      if (requestRevision.current !== revision) return;
      setStudy(null);
      setRecommendation(null);
      setObservations({});
      setPendingTransition(null);
      setPendingStudyClose(false);
      setDeletionPreflight(null);
      setPendingStudyDeletion(false);
      setPredecessorStudyId(null);
      try {
        const catalog = await fetchBayesianStudies(0, 50);
        if (requestRevision.current === revision) setStudies(catalog.items);
      } catch (caught) {
        if (requestRevision.current === revision) setError(errorCode(caught));
      }
    } catch (caught) {
      if (requestRevision.current === revision) setError(errorCode(caught));
    } finally {
      if (requestRevision.current === revision) setIsDeleting(false);
    }
  };

  const minimumInitialDesignSize = minimumBayesianInitialDesignSize(factors.length);
  const parsedTotalTrialBudget = Number(totalTrialBudget);
  const trialBudgetBlocker = bayesianRecommendationBudgetBlocker(
    study?.trial_count ?? 0,
    parsedTotalTrialBudget,
    study?.recommendation_hard_trial_limit ?? 200,
  );
  const trialBudgetIsValid =
    trialBudgetBlocker !== "bayesian_optimization_trial_budget_invalid";
  const trialBudgetReached = trialBudgetBlocker === "bayesian_optimization_budget_exhausted";
  const recommendationDisabled =
    study === null ||
    study.status !== "active" ||
    !study.recommendation_available ||
    !trialBudgetIsValid ||
    trialBudgetReached ||
    isRecommending ||
    isSavingTrial ||
    isClosing ||
    isDeleting ||
    pendingTransition !== null ||
    pendingStudyClose;
  const studyIsActive = study?.status === "active";
  const closeRequirementsMet =
    study !== null &&
    bayesianStudyCloseBlocker(study, closeTarget, recommendation !== null) === null;
  const studyActionDisabled =
    !studyIsActive ||
    isSavingTrial ||
    isRecommending ||
    isClosing ||
    isDeleting ||
    pendingTransition !== null ||
    pendingStudyClose;

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
          <span className="cell-subtext">
            현재 요인 {factors.length}개에는 최소 {minimumInitialDesignSize}개가 필요합니다.
          </span>
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
          disabled={
            isCreating ||
            isSavingTrial ||
            isRecommending ||
            isClosing ||
            isCheckingDeletion ||
            isDeleting
          }
          onClick={() => void createStudy()}
        >
          {isCreating
            ? "생성 중"
            : predecessorStudyId === null
              ? "Study 생성"
              : "Successor study 생성"}
        </button>
        {predecessorStudyId !== null ? (
          <>
            <button
              type="button"
              className="secondary-button"
              disabled={isCreating}
              onClick={() => setPredecessorStudyId(null)}
            >
              Successor 생성 취소
            </button>
            <span className="cell-subtext">
              Factor, objective, constraint, seed만 새 정의 초안으로 복사합니다. 기존 관측,
              history, recommendation은 복사하지 않습니다.
            </span>
          </>
        ) : null}
      </div>

      <label>
        <span>저장된 study</span>
        <select
          aria-label="저장된 Bayesian study"
          value={study?.study_id ?? ""}
          disabled={isLoading || isSavingTrial || isRecommending || isClosing || isDeleting}
          onChange={(event) => {
            if (event.currentTarget.value.length > 0) void restoreStudy(event.currentTarget.value);
          }}
        >
          <option value="">선택</option>
          {studies.map((item) => (
            <option key={item.study_id} value={item.study_id}>
              {item.name} · {item.status} · 완료 {item.completed_trial_count}
            </option>
          ))}
        </select>
      </label>

      {error !== null ? (
        <div className="error-box" role="alert">
          <strong>{getAnalysisRunErrorDetails(error).title}</strong>
          <p>{getAnalysisRunErrorDetails(error).message}</p>
          <p>{getAnalysisRunErrorDetails(error).action}</p>
          <span>오류 코드: {error}</span>
        </div>
      ) : null}

      {study !== null ? (
        <>
          <div className="metadata-grid" aria-label="Bayesian study 상태">
            <span>Study 상태</span>
            <strong>{study.status}</strong>
            <span>Method version</span>
            <strong>{study.method_version}</strong>
            <span>관측 history</span>
            <strong>revision {study.observation_history.revision_number}</strong>
            <span>완료 / 전체</span>
            <strong>
              {study.completed_trial_count} / {study.trial_count}
            </strong>
            {study.predecessor_study_id !== null ? (
              <>
                <span>Predecessor study</span>
                <strong>{study.predecessor_study_id}</strong>
              </>
            ) : null}
          </div>
          {!studyIsActive && study.lifecycle_event !== null ? (
            <div className="info-box" aria-label="Bayesian study 종료 기록">
              <strong>
                {study.lifecycle_event.resulting_status} · {study.lifecycle_event.reason_code}
              </strong>
              <p>
                {study.lifecycle_event.closed_at}에 종료되었으며, 관측·trial·추천은 읽기
                전용입니다.
              </p>
              {study.lifecycle_event.note !== null ? <p>{study.lifecycle_event.note}</p> : null}
              <button
                type="button"
                className="secondary-button"
                disabled={isCreating || isCheckingDeletion || isDeleting}
                onClick={prepareSuccessor}
              >
                이 정의로 successor study 준비
              </button>
              <button
                type="button"
                className="secondary-button"
                disabled={isCheckingDeletion || isDeleting}
                onClick={() => void checkDeletionImpact()}
              >
                {isCheckingDeletion ? "삭제 영향 확인 중" : "삭제 영향 확인"}
              </button>
            </div>
          ) : null}
          {!studyIsActive &&
          deletionPreflight !== null &&
          deletionPreflight.study_id === study.study_id ? (
            <div className="info-box" aria-label="Bayesian study 삭제 영향">
              <strong>
                삭제 대상 metadata {deletionPreflight.counts.metadata_record_count}건 · 파일{" "}
                {deletionPreflight.counts.file_count}개
              </strong>
              <p>
                Trial {deletionPreflight.counts.trial_count}건, history revision{" "}
                {deletionPreflight.counts.history_revision_count}건, recommendation{" "}
                {deletionPreflight.counts.recommendation_count}건을 함께 삭제합니다.
              </p>
              {deletionPreflight.successor_study_count > 0 ? (
                <p>
                  Successor study {deletionPreflight.successor_study_count}개가 참조하여 삭제할
                  수 없습니다.
                </p>
              ) : null}
              {deletionPreflight.blockers.length > 0 ? (
                <p>삭제 차단 사유: {deletionPreflight.blockers.join(", ")}</p>
              ) : (
                <button
                  type="button"
                  className="secondary-button"
                  disabled={isDeleting}
                  onClick={() => setPendingStudyDeletion(true)}
                >
                  불가역 삭제 확인
                </button>
              )}
            </div>
          ) : null}
          {pendingStudyDeletion &&
          deletionPreflight !== null &&
          deletionPreflight.study_id === study.study_id ? (
            <BayesianStudyDeletionConfirmation
              study={study}
              preflight={deletionPreflight}
              isDeleting={isDeleting}
              onConfirm={() => void deleteStudy()}
              onCancel={() => setPendingStudyDeletion(false)}
            />
          ) : null}
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
                          disabled={!studyIsActive || isSavingTrial || isClosing}
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
                          disabled={
                            trial.state !== "pending" || studyActionDisabled
                          }
                          onClick={() =>
                            requestTrialTransition(trial.trial_id, "complete")
                          }
                        >
                          관측 저장
                        </button>
                        <button
                          type="button"
                          className="secondary-button"
                          disabled={
                            trial.state !== "pending" || studyActionDisabled
                          }
                          onClick={() =>
                            requestTrialTransition(trial.trial_id, "abandon")
                          }
                        >
                          Abandon
                        </button>
                      </div>
                      {pendingTransition?.trialId === trial.trial_id ? (
                        <BayesianTrialTransitionConfirmation
                          trial={trial}
                          action={pendingTransition.action}
                          objectiveValue={observations[trial.trial_id] ?? ""}
                          isSaving={isSavingTrial}
                          onConfirm={() => void transitionTrial()}
                          onCancel={() => setPendingTransition(null)}
                        />
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="option-grid">
            <label>
              <span>전체 trial 예산</span>
              <input
                aria-label="Bayesian 전체 trial 예산"
                inputMode="numeric"
                value={totalTrialBudget}
                disabled={!studyIsActive || isRecommending || isSavingTrial || isClosing}
                onChange={(event) => setTotalTrialBudget(event.currentTarget.value)}
              />
              <span className="cell-subtext">
                현재 {study.trial_count}개 / 요청 예산 {totalTrialBudget || "-"}개, hard limit{" "}
                {study.recommendation_hard_trial_limit}개
              </span>
            </label>
          </div>
          <div className="button-row">
            <button
              type="button"
              className="primary-button"
              disabled={recommendationDisabled}
              onClick={() => void recommend()}
            >
              {isRecommending ? "GP/EI 계산 중" : "다음 실험 추천"}
            </button>
          </div>
          {!trialBudgetIsValid ? (
            <p className="cell-subtext">
              전체 trial 예산은 2~{study.recommendation_hard_trial_limit} 사이의 정수여야 합니다.
            </p>
          ) : trialBudgetReached ? (
            <p className="cell-subtext">
              전체 trial 예산 {parsedTotalTrialBudget}개에 도달하여 새 추천을 만들 수 없습니다.
            </p>
          ) : !study.recommendation_available ? (
            <p className="cell-subtext">
              추천 차단 사유: {study.recommendation_blockers.join(", ")}. 최소 완료 관측은{" "}
              {study.recommendation_minimum_completed_observations}개입니다.
            </p>
          ) : null}
          {studyIsActive ? (
            <section aria-labelledby="bayesian-study-close-title">
              <div className="panel-heading">
                <div>
                  <h4 id="bayesian-study-close-title">Study 종료</h4>
                  <p>종료 후에는 관측, trial 중단, 추천을 추가하거나 다시 열 수 없습니다.</p>
                </div>
              </div>
              <div className="option-grid">
                <label>
                  <span>종료 상태</span>
                  <select
                    aria-label="Bayesian study 종료 상태"
                    value={closeTarget}
                    disabled={studyActionDisabled}
                    onChange={(event) => {
                      const target = event.currentTarget.value as StudyCloseTarget;
                      setCloseTarget(target);
                      setCloseReason(
                        target === "completed"
                          ? "confirmation_complete"
                          : "study_cancelled",
                      );
                      setPendingStudyClose(false);
                    }}
                  >
                    <option value="completed">완료</option>
                    <option value="abandoned">중단</option>
                  </select>
                </label>
                <label>
                  <span>종료 사유</span>
                  <select
                    aria-label="Bayesian study 종료 사유"
                    value={closeReason}
                    disabled={studyActionDisabled}
                    onChange={(event) =>
                      setCloseReason(event.currentTarget.value as BayesianStudyCloseReason)
                    }
                  >
                    {closeTarget === "completed" ? (
                      <>
                        <option value="confirmation_complete">확인 실험 완료</option>
                        <option value="objective_satisfied">목표 충족</option>
                        <option value="budget_reached">예산 도달</option>
                      </>
                    ) : (
                      <>
                        <option value="study_cancelled">Study 취소</option>
                        <option value="unsafe_or_infeasible">안전·실행 가능성 문제</option>
                        <option value="resources_unavailable">자원 부족</option>
                      </>
                    )}
                  </select>
                </label>
                <label>
                  <span>종료 메모</span>
                  <input
                    aria-label="Bayesian study 종료 메모"
                    value={closeNote}
                    maxLength={500}
                    disabled={studyActionDisabled}
                    onChange={(event) => setCloseNote(event.currentTarget.value)}
                  />
                </label>
              </div>
              {study.pending_trial_count > 0 ? (
                <p className="cell-subtext">
                  종료하려면 pending trial {study.pending_trial_count}개를 먼저 완료하거나
                  중단하세요.
                  {closeTarget === "abandoned"
                    ? " 중단 종료를 선택한 상태에서는 초기 trial도 종료 의도로 중단할 수 있습니다."
                    : ""}
                </p>
              ) : closeTarget === "completed" && recommendation === null ? (
                <p className="cell-subtext">
                  완료 종료에는 최소 관측 수와 저장된 recommendation이 필요합니다.
                </p>
              ) : null}
              <div className="button-row">
                <button
                  type="button"
                  className={
                    closeTarget === "completed" ? "primary-button" : "secondary-button"
                  }
                  disabled={!closeRequirementsMet || studyActionDisabled}
                  onClick={() => setPendingStudyClose(true)}
                >
                  {closeTarget === "completed" ? "Study 완료" : "Study 중단"}
                </button>
              </div>
              {pendingStudyClose ? (
                <BayesianStudyCloseConfirmation
                  study={study}
                  target={closeTarget}
                  reason={closeReason}
                  note={closeNote}
                  isClosing={isClosing}
                  onConfirm={() => void closeStudy()}
                  onCancel={() => setPendingStudyClose(false)}
                />
              ) : null}
            </section>
          ) : null}
        </>
      ) : null}

      {recommendation !== null ? (
        <section aria-labelledby="bayesian-recommendation-result-title">
          <div className="panel-heading">
            <div>
              <h4 id="bayesian-recommendation-result-title">추천 결과</h4>
              <p>{bayesianRecommendationStatus(recommendation).description}</p>
            </div>
            <span
              className={`status-pill ${bayesianRecommendationStatus(recommendation).className}`}
            >
              {bayesianRecommendationStatus(recommendation).label}
            </span>
          </div>
          <div className="metadata-grid">
            <span>추천 snapshot 상태</span>
            <strong>{recommendation.trial.state}</strong>
            <span>현재 trial 상태</span>
            <strong>{recommendation.current_trial?.state ?? recommendation.trial.state}</strong>
            <span>추천 조건</span>
            <strong>{coordinateText(recommendation.result.recommended_actual_coordinates)}</strong>
            <span>예측 평균</span>
            <strong>{formatNumber(recommendation.result.predicted_objective_mean)}</strong>
            <span>Posterior 표준편차</span>
            <strong>{formatNumber(recommendation.result.posterior_standard_deviation)}</strong>
            <span>Expected Improvement</span>
            <strong>{formatNumber(recommendation.result.expected_improvement)}</strong>
            {recommendation.current_trial?.state === "completed" &&
            recommendation.current_trial.objective_value !== null ? (
              <>
                <span>실제 관측값</span>
                <strong>{formatNumber(recommendation.current_trial.objective_value)}</strong>
              </>
            ) : null}
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
          <p className="cell-subtext">추천 생성 당시의 immutable warning snapshot</p>
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

export function BayesianStudyCloseConfirmation({
  study,
  target,
  reason,
  note,
  isClosing,
  onConfirm,
  onCancel,
}: {
  study: Pick<
    BayesianStudyResponse,
    "study_id" | "name" | "completed_trial_count" | "abandoned_trial_count"
  >;
  target: StudyCloseTarget;
  reason: BayesianStudyCloseReason;
  note: string;
  isClosing: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="info-box" aria-label="Bayesian study terminal action 확인">
      <strong>
        {study.name} · {study.study_id} · {target === "completed" ? "완료" : "중단"} ·{" "}
        {reason}
      </strong>
      <p>
        최종 관측 {study.completed_trial_count}개, 중단 trial {study.abandoned_trial_count}개를
        현재 history checksum에 고정합니다. 종료 후에는 수정하거나 다시 열 수 없습니다.
      </p>
      {note.trim().length > 0 ? <p>메모: {note.trim()}</p> : null}
      {target === "completed" ? (
        <p>이 상태는 전역 최적해 달성이나 목적함수의 자동 실행을 의미하지 않습니다.</p>
      ) : null}
      <div className="button-row">
        <button
          type="button"
          className={target === "completed" ? "primary-button" : "secondary-button"}
          disabled={isClosing}
          onClick={onConfirm}
        >
          {isClosing ? "종료 처리 중" : "종료 확인"}
        </button>
        <button
          type="button"
          className="secondary-button"
          disabled={isClosing}
          onClick={onCancel}
        >
          취소
        </button>
      </div>
    </div>
  );
}

export function BayesianStudyDeletionConfirmation({
  study,
  preflight,
  isDeleting,
  onConfirm,
  onCancel,
}: {
  study: Pick<BayesianStudyResponse, "study_id" | "name">;
  preflight: BayesianStudyDeletionPreflightResponse;
  isDeleting: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const confirmationIsCurrent =
    preflight.eligible && preflight.study_id === study.study_id;
  return (
    <div className="error-box" aria-label="Bayesian study irreversible deletion 확인">
      <strong>
        {study.name} · {study.study_id}
      </strong>
      <p>
        {`metadata ${preflight.counts.metadata_record_count}건을 영구 삭제합니다. 삭제 후 복원할 수 없으며 cascade 또는 successor 삭제는 수행하지 않습니다.`}
      </p>
      <p>
        {`파일 ${preflight.counts.file_count}개 · ${preflight.counts.file_bytes} bytes. 현재 Bayesian study graph는 workspace 파일을 소유하지 않습니다.`}
      </p>
      <div className="button-row">
        <button
          type="button"
          className="secondary-button"
          disabled={isDeleting || !confirmationIsCurrent}
          onClick={onConfirm}
        >
          {isDeleting ? "영구 삭제 중" : "영구 삭제 확인"}
        </button>
        <button
          type="button"
          className="secondary-button"
          disabled={isDeleting}
          onClick={onCancel}
        >
          취소
        </button>
      </div>
    </div>
  );
}

export function BayesianTrialTransitionConfirmation({
  trial,
  action,
  objectiveValue,
  isSaving,
  onConfirm,
  onCancel,
}: {
  trial: BayesianTrialResponse;
  action: "complete" | "abandon";
  objectiveValue: string;
  isSaving: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const isCompletion = action === "complete";
  return (
    <div className="info-box" aria-label={`Trial ${trial.trial_number} terminal action 확인`}>
      <strong>Trial {trial.trial_number} · {coordinateText(trial.actual_coordinates)}</strong>
      <p>
        {isCompletion
          ? `objective ${objectiveValue}을 저장하면 이후 수정할 수 없습니다.`
          : "중단하면 이 조건과 duplicate tolerance 이내 조건은 향후 추천에서 제외됩니다."}
      </p>
      {action === "abandon" && trial.origin === "initial_design" ? (
        <p>초기 trial 중단은 추천에 필요한 최소 완료 관측 수를 남기는 경우에만 허용됩니다.</p>
      ) : null}
      <div className="button-row">
        <button
          type="button"
          className={isCompletion ? "primary-button" : "secondary-button"}
          disabled={isSaving}
          onClick={onConfirm}
        >
          {isSaving ? "처리 중" : isCompletion ? "관측 저장 확인" : "Abandon 확인"}
        </button>
        <button
          type="button"
          className="secondary-button"
          disabled={isSaving}
          onClick={onCancel}
        >
          취소
        </button>
      </div>
    </div>
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
