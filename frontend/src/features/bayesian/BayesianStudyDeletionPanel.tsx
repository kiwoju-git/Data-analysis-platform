import type { BayesianStudyResponse } from "../../api";
import type { useBayesianRetentionState } from "./hooks/useBayesianRetentionState";
import { BayesianStudyDeletionConfirmation } from "./BayesianTransitionConfirmations";

type RetentionState = ReturnType<typeof useBayesianRetentionState>;

export function BayesianStudyDeletionPanel({ study, state, disabled, onDeleted }: { study: BayesianStudyResponse; state: RetentionState; disabled: boolean; onDeleted: () => void }) {
  if (study.status === "active") return null;
  const preflight = state.preflight?.study_id === study.study_id ? state.preflight : null;
  return (
    <section aria-labelledby="bayesian-study-deletion-title">
      <div className="panel-heading"><div><h4 id="bayesian-study-deletion-title">삭제/보존</h4><p>닫힌 Study의 전체 metadata graph와 successor 참조를 먼저 확인합니다.</p></div></div>
      <button type="button" className="secondary-button" disabled={disabled || state.isChecking || state.isDeleting} onClick={() => void state.onCheck()}>{state.isChecking ? "삭제 영향 확인 중" : "삭제 영향 확인"}</button>
      {state.error !== null ? <div className="error-box" role="alert">삭제 상태 확인 실패. 오류 코드: {state.error}</div> : null}
      {preflight !== null ? (
        <div className="info-box" aria-label="Bayesian study 삭제 영향">
          <strong>삭제 대상 metadata {preflight.counts.metadata_record_count}건 · 파일 {preflight.counts.file_count}개</strong>
          <p>Trial {preflight.counts.trial_count}건, history revision {preflight.counts.history_revision_count}건, recommendation {preflight.counts.recommendation_count}건을 함께 삭제합니다.</p>
          {preflight.successor_study_count > 0 ? <p>Successor study {preflight.successor_study_count}개가 참조하여 삭제할 수 없습니다.</p> : null}
          {preflight.blockers.length > 0 ? <p>삭제 차단 사유: {preflight.blockers.join(", ")}</p> : <button type="button" className="secondary-button" disabled={state.isDeleting} onClick={() => state.setPendingDeletion(true)}>불가역 삭제 확인</button>}
        </div>
      ) : null}
      {state.pendingDeletion && preflight !== null ? (
        <BayesianStudyDeletionConfirmation
          study={study}
          preflight={preflight}
          isDeleting={state.isDeleting}
          onConfirm={() => void state.onDelete().then((deleted) => { if (deleted) onDeleted(); })}
          onCancel={() => state.setPendingDeletion(false)}
        />
      ) : null}
    </section>
  );
}
