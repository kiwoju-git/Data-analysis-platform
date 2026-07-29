import type { BayesianStudyResponse } from "../../api";
import { constraintText } from "./bayesianDisplay";

export function BayesianStudySummary({ study }: { study: BayesianStudyResponse }) {
  const initialTrials = study.trials.filter((trial) => trial.origin === "initial_design");
  const completedInitialTrials = initialTrials.filter(
    (trial) => trial.state === "completed",
  ).length;
  const pendingInitialTrials = initialTrials.filter((trial) => trial.state === "pending").length;
  const phase =
    pendingInitialTrials > 0
      ? "초기 실험 수행 및 반응 입력"
      : study.recommendation_available
        ? "다음 실험 조건 추천 가능"
        : "추천 조건의 실제 반응 입력";
  return (
    <section aria-labelledby="bayesian-study-summary-title">
      <div className="panel-heading">
        <div>
          <h4 id="bayesian-study-summary-title">Study 정의와 상태</h4>
          <p>선택한 immutable definition과 현재 lifecycle 상태입니다.</p>
        </div>
      </div>
      <div className="info-box">
        <strong>현재 단계: {phase}</strong>
        <p>
          초기 실험 {completedInitialTrials} / {initialTrials.length} 완료
          {pendingInitialTrials > 0
            ? " · 모든 필수 초기 실험이 종료된 뒤 GP 추천을 생성할 수 있습니다."
            : ` · 완료 관측 ${study.completed_trial_count}개`}
        </p>
        <p>
          Gaussian Process는 반응함수를 근사하고 예측 불확실성을 계산하는
          surrogate model입니다. 원자료가 일반 정규성 검정을 통과해야만 사용할 수
          있다는 뜻은 아닙니다. Expected Improvement 추천값은 관측값이 아니며 실제
          실험을 대신하지 않습니다.
        </p>
      </div>
      <div className="metadata-grid" aria-label="Bayesian study 상태">
        <span>Study 상태</span><strong>{study.status}</strong>
        <span>Method version</span><strong>{study.method_version}</strong>
        <span>초기 설계</span>
        <strong>
          {study.initial_design.policy === "latin_hypercube_random_cd_v1"
            ? "LHS 공간충전"
            : "제약 대응 균등 설계"}
        </strong>
        <span>관측 history</span><strong>revision {study.observation_history.revision_number}</strong>
        <span>완료 / 전체</span><strong>{study.completed_trial_count} / {study.trial_count}</strong>
        {study.predecessor_study_id !== null ? (
          <><span>Predecessor study</span><strong>{study.predecessor_study_id}</strong></>
        ) : null}
      </div>
      {study.constraints.length > 0 ? (
        <div className="table-wrap" aria-label="Bayesian stored constraints">
          <table className="result-table">
            <thead><tr><th>제약</th><th>실제 단위 식</th></tr></thead>
            <tbody>
              {study.constraints.map((constraint) => (
                <tr key={constraint.constraint_id}>
                  <td><strong>{constraint.constraint_id}</strong><span className="cell-subtext">{constraint.name}</span></td>
                  <td>{constraintText(constraint)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
