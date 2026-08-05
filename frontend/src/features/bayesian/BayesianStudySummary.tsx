import type { BayesianStudyResponse } from "../../api";
import { apiRoutes } from "../../api/routes";
import { formatDoeFactorValue } from "../../doe/factorDomain";
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
        <span>최적화 목표</span>
        <strong>
          {study.objective.goal_type === "match_target"
            ? `${study.objective.name} 목표 ${study.objective.target_value}${
                study.objective.target_tolerance === null
                  ? ""
                  : ` ± ${study.objective.target_tolerance}`
              }`
            : `${study.objective.name} ${
                study.objective.goal_type === "maximize" ? "최대화" : "최소화"
              }`}
        </strong>
        <span>초기 설계</span>
        <strong>
          {study.initial_design.policy === "latin_hypercube_random_cd_v1"
            ? "LHS 공간충전"
            : "제약 대응 균등 설계"}
        </strong>
        <span>완료 / 전체</span><strong>{study.completed_trial_count} / {study.trial_count}</strong>
        {study.predecessor_study_id !== null ? (
          <><span>Predecessor study</span><strong>{study.predecessor_study_id}</strong></>
        ) : null}
      </div>
      <h5>요인 정의</h5>
      <div className="table-wrap">
        <table className="result-table bayesian-factor-definition-table">
          <thead><tr><th>순서</th><th>Factor ID</th><th>표시 이름</th><th>설정 방식</th><th>하한</th><th>상한</th><th>실행 간격</th><th>허용 수준</th><th>단위</th></tr></thead>
          <tbody>{study.factors.map((factor) => (
            <tr key={factor.factor_id}><td>{factor.order}</td><td>{factor.factor_id}</td><td>{factor.name}</td><td>{factor.domain_kind === "discrete_numeric" ? "일정 간격 숫자" : "연속형"}</td><td>{formatDoeFactorValue(factor.low, factor.display_decimals)}</td><td>{formatDoeFactorValue(factor.high, factor.display_decimals)}</td><td>{factor.step == null ? "-" : formatDoeFactorValue(factor.step, factor.display_decimals)}</td><td>{factor.level_count ?? "-"}</td><td>{factor.unit ?? "-"}</td></tr>
          ))}</tbody>
        </table>
      </div>
      <h5>목적 반응</h5>
      <div className="metadata-grid" aria-label="Bayesian 목적 반응 정의">
        <span>반응 이름</span><strong>{study.objective.name}</strong>
        <span>단위</span><strong>{study.objective.unit ?? "-"}</strong>
        <span>목표</span><strong>{study.objective.goal_type === "maximize" ? "최대화" : study.objective.goal_type === "minimize" ? "최소화" : "목표값 맞추기"}</strong>
        <span>목표값 / 허용 오차</span><strong>{study.objective.target_value ?? "-"} / {study.objective.target_tolerance ?? "-"}</strong>
        <span>관측 정책</span><strong>실제 관측값 직접 입력</strong>
      </div>
      <h5>초기설계 설정</h5>
      <div className="metadata-grid" aria-label="Bayesian 초기설계 설정">
        <span>초기 실험 수</span><strong>{study.initial_design.generated_size}</strong>
        <span>Policy</span><strong>{study.initial_design.policy === "latin_hypercube_random_cd_v1" ? "LHS random-cd" : "제약 대응 균등 설계"}</strong>
        <span>Seed</span><strong>{study.initial_design.seed}</strong>
        <span>Centered discrepancy</span><strong>{study.initial_design.centered_discrepancy ?? "-"}</strong>
        <span>최소 거리</span><strong>{study.initial_design.minimum_pairwise_distance ?? "-"}</strong>
        <span>층화 상태</span><strong>{study.initial_design.strata_valid === null || study.initial_design.strata_valid === undefined ? "해당 없음" : study.initial_design.strata_valid ? "유효" : "확인 필요"}</strong>
      </div>
      <div className="panel-heading bayesian-initial-design-heading">
        <div><h5>초기 실험 설계</h5><p>Study definition에 저장된 실제 단위 조건입니다.</p></div>
        <a className="secondary-button" download href={apiRoutes.bayesianInitialDesignCsv(study.study_id)}>CSV 다운로드</a>
      </div>
      <div className="table-wrap">
        <table className="result-table">
          <thead><tr><th>Trial</th>{study.factors.map((factor) => <th key={factor.factor_id}>{factor.name}{factor.unit ? ` [${factor.unit}]` : ""}</th>)}<th>상태</th><th>실제 관측값</th></tr></thead>
          <tbody>{initialTrials.map((trial) => <tr key={trial.trial_id}><td>{trial.trial_number}</td>{study.factors.map((factor) => <td key={factor.factor_id}>{formatDoeFactorValue(trial.actual_coordinates[factor.factor_id], factor.display_decimals)}</td>)}<td>{trial.state}</td><td>{trial.objective_value ?? "-"}</td></tr>)}</tbody>
        </table>
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
      <details className="technical-details">
        <summary>기술 정보</summary>
        <div className="metadata-grid">
          <span>Method version</span><strong>{study.method_version}</strong>
          <span>Study schema</span><strong>{study.study_schema_version}</strong>
          <span>Definition SHA</span><strong>{study.definition_sha256}</strong>
          <span>History revision</span><strong>{study.observation_history.history_revision_id}</strong>
          <span>App version</span><strong>{study.app_version}</strong>
        </div>
      </details>
    </section>
  );
}
