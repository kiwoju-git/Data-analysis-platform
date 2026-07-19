import type {
  BayesianRecommendationResponse,
  BayesianStudyResponse,
} from "../../api";
import {
  bayesianRecommendationBudgetBlocker,
  bayesianRecommendationStatus,
} from "../../bayesianStudyDraft";
import { coordinateText, formatNumber } from "./bayesianDisplay";

export function BayesianRecommendationPanel({
  study,
  recommendation,
  totalTrialBudget,
  isRecommending,
  actionsDisabled,
  onBudgetChange,
  onRecommend,
}: {
  study: BayesianStudyResponse;
  recommendation: BayesianRecommendationResponse | null;
  totalTrialBudget: string;
  isRecommending: boolean;
  actionsDisabled: boolean;
  onBudgetChange: (value: string) => void;
  onRecommend: () => void;
}) {
  const parsedBudget = Number(totalTrialBudget);
  const budgetBlocker = bayesianRecommendationBudgetBlocker(
    study.trial_count,
    parsedBudget,
    study.recommendation_hard_trial_limit,
  );
  const budgetIsValid = budgetBlocker !== "bayesian_optimization_trial_budget_invalid";
  const budgetReached = budgetBlocker === "bayesian_optimization_budget_exhausted";
  const disabled =
    actionsDisabled ||
    study.status !== "active" ||
    !study.recommendation_available ||
    budgetBlocker !== null ||
    isRecommending;

  return (
    <section aria-labelledby="bayesian-recommendation-title">
      <div className="panel-heading"><div><h4 id="bayesian-recommendation-title">다음 조건 추천</h4><p>완료 관측으로 GP/EI를 계산하고 하나의 확인 실험 trial을 저장합니다.</p></div></div>
      <div className="option-grid">
        <label>
          <span>전체 trial 예산</span>
          <input
            aria-label="Bayesian 전체 trial 예산"
            inputMode="numeric"
            value={totalTrialBudget}
            disabled={study.status !== "active" || actionsDisabled}
            onChange={(event) => onBudgetChange(event.currentTarget.value)}
          />
          <span className="cell-subtext">현재 {study.trial_count}개 / 요청 예산 {totalTrialBudget || "-"}개, hard limit {study.recommendation_hard_trial_limit}개</span>
        </label>
      </div>
      <div className="button-row">
        <button type="button" className="primary-button" disabled={disabled} onClick={onRecommend}>
          {isRecommending ? "GP/EI 계산 중" : "다음 실험 추천"}
        </button>
      </div>
      {!budgetIsValid ? (
        <p className="cell-subtext">전체 trial 예산은 2~{study.recommendation_hard_trial_limit} 사이의 정수여야 합니다.</p>
      ) : budgetReached ? (
        <p className="cell-subtext">전체 trial 예산 {parsedBudget}개에 도달하여 새 추천을 만들 수 없습니다.</p>
      ) : !study.recommendation_available ? (
        <p className="cell-subtext">추천 차단 사유: {study.recommendation_blockers.join(", ")}. 최소 완료 관측은 {study.recommendation_minimum_completed_observations}개입니다.</p>
      ) : null}
      {recommendation !== null ? <BayesianRecommendationResult recommendation={recommendation} /> : null}
    </section>
  );
}

function BayesianRecommendationResult({ recommendation }: { recommendation: BayesianRecommendationResponse }) {
  const status = bayesianRecommendationStatus(recommendation);
  return (
    <section aria-labelledby="bayesian-recommendation-result-title">
      <div className="panel-heading">
        <div><h4 id="bayesian-recommendation-result-title">추천 결과</h4><p>{status.description}</p></div>
        <span className={`status-pill ${status.className}`}>{status.label}</span>
      </div>
      <div className="metadata-grid">
        <span>추천 snapshot 상태</span><strong>{recommendation.trial.state}</strong>
        <span>현재 trial 상태</span><strong>{recommendation.current_trial?.state ?? recommendation.trial.state}</strong>
        <span>추천 조건</span><strong>{coordinateText(recommendation.result.recommended_actual_coordinates)}</strong>
        <span>예측 평균</span><strong>{formatNumber(recommendation.result.predicted_objective_mean)}</strong>
        <span>Posterior 표준편차</span><strong>{formatNumber(recommendation.result.posterior_standard_deviation)}</strong>
        <span>Expected Improvement</span><strong>{formatNumber(recommendation.result.expected_improvement)}</strong>
        {recommendation.current_trial?.state === "completed" && recommendation.current_trial.objective_value !== null ? (
          <><span>실제 관측값</span><strong>{formatNumber(recommendation.current_trial.objective_value)}</strong></>
        ) : null}
      </div>
      {recommendation.result.constraint_evaluations.length > 0 ? (
        <div className="table-wrap" aria-label="Bayesian recommendation constraints">
          <table className="result-table">
            <thead><tr><th>제약</th><th>좌변</th><th>관계</th><th>우변</th><th>Slack</th><th>상태</th></tr></thead>
            <tbody>
              {recommendation.result.constraint_evaluations.map((evaluation) => (
                <tr key={evaluation.constraint_id}>
                  <td>{evaluation.constraint_id}</td><td>{formatNumber(evaluation.lhs)}</td>
                  <td>{evaluation.relation === "less_than_or_equal" ? "≤" : "≥"}</td>
                  <td>{formatNumber(evaluation.bound)}</td><td>{formatNumber(evaluation.slack)}</td>
                  <td>{evaluation.satisfied ? "충족" : "위반"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      <p className="cell-subtext">추천 생성 당시의 immutable warning snapshot</p>
      <ul className="warning-list">{recommendation.result.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
      <p className="cell-subtext">획득함수 탐색과 추천은 전역 최적을 보장하지 않습니다. 실제 확인 실험 결과를 저장한 뒤 다음 추천을 생성하세요.</p>
    </section>
  );
}
