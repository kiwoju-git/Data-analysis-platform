import type { BayesianRecommendationResponse, BayesianStudyCloseReason, BayesianStudyResponse } from "../../api";
import { bayesianStudyCloseBlocker } from "../../bayesianStudyDraft";
import type { StudyCloseTarget } from "./bayesianDisplay";
import { BayesianStudyCloseConfirmation } from "./BayesianTransitionConfirmations";

export function BayesianStudyClosePanel({
  study,
  recommendation,
  target,
  reason,
  note,
  pending,
  isClosing,
  actionsDisabled,
  onTargetChange,
  onReasonChange,
  onNoteChange,
  onRequestClose,
  onConfirmClose,
  onCancelClose,
  onPrepareSuccessor,
}: {
  study: BayesianStudyResponse;
  recommendation: BayesianRecommendationResponse | null;
  target: StudyCloseTarget;
  reason: BayesianStudyCloseReason;
  note: string;
  pending: boolean;
  isClosing: boolean;
  actionsDisabled: boolean;
  onTargetChange: (target: StudyCloseTarget) => void;
  onReasonChange: (reason: BayesianStudyCloseReason) => void;
  onNoteChange: (note: string) => void;
  onRequestClose: () => void;
  onConfirmClose: () => void;
  onCancelClose: () => void;
  onPrepareSuccessor: () => void;
}) {
  if (study.status !== "active") {
    return study.lifecycle_event === null ? null : (
      <section aria-labelledby="bayesian-study-close-title">
        <div className="panel-heading"><div><h4 id="bayesian-study-close-title">Study 종료/Successor</h4><p>종료된 Study는 읽기 전용이며 다시 열 수 없습니다.</p></div></div>
        <div className="info-box" aria-label="Bayesian study 종료 기록">
          <strong>{study.lifecycle_event.resulting_status} · {study.lifecycle_event.reason_code}</strong>
          <p>{study.lifecycle_event.closed_at}에 종료되었으며, 관측·trial·추천은 읽기 전용입니다.</p>
          {study.lifecycle_event.note !== null ? <p>{study.lifecycle_event.note}</p> : null}
          <button type="button" className="secondary-button" onClick={onPrepareSuccessor}>이 정의로 successor study 준비</button>
        </div>
      </section>
    );
  }

  const blocker = bayesianStudyCloseBlocker(study, target, recommendation !== null);
  return (
    <section aria-labelledby="bayesian-study-close-title">
      <div className="panel-heading"><div><h4 id="bayesian-study-close-title">Study 종료/Successor</h4><p>종료 후에는 관측, trial 중단, 추천을 추가하거나 다시 열 수 없습니다.</p></div></div>
      <div className="option-grid">
        <label><span>종료 상태</span><select aria-label="Bayesian study 종료 상태" value={target} disabled={actionsDisabled} onChange={(event) => onTargetChange(event.currentTarget.value as StudyCloseTarget)}><option value="completed">완료</option><option value="abandoned">중단</option></select></label>
        <label><span>종료 사유</span><select aria-label="Bayesian study 종료 사유" value={reason} disabled={actionsDisabled} onChange={(event) => onReasonChange(event.currentTarget.value as BayesianStudyCloseReason)}>{target === "completed" ? <><option value="confirmation_complete">확인 실험 완료</option><option value="objective_satisfied">목표 충족</option><option value="budget_reached">예산 도달</option></> : <><option value="study_cancelled">Study 취소</option><option value="unsafe_or_infeasible">안전·실행 가능성 문제</option><option value="resources_unavailable">자원 부족</option></>}</select></label>
        <label><span>종료 메모</span><input aria-label="Bayesian study 종료 메모" value={note} maxLength={500} disabled={actionsDisabled} onChange={(event) => onNoteChange(event.currentTarget.value)} /></label>
      </div>
      {study.pending_trial_count > 0 ? <p className="cell-subtext">종료하려면 pending trial {study.pending_trial_count}개를 먼저 완료하거나 중단하세요.{target === "abandoned" ? " 중단 종료를 선택한 상태에서는 초기 trial도 종료 의도로 중단할 수 있습니다." : ""}</p> : target === "completed" && recommendation === null ? <p className="cell-subtext">완료 종료에는 최소 관측 수와 저장된 recommendation이 필요합니다.</p> : null}
      <div className="button-row"><button type="button" className={target === "completed" ? "primary-button" : "secondary-button"} disabled={blocker !== null || actionsDisabled} onClick={onRequestClose}>{target === "completed" ? "Study 완료" : "Study 중단"}</button></div>
      {pending ? <BayesianStudyCloseConfirmation study={study} target={target} reason={reason} note={note} isClosing={isClosing} onConfirm={onConfirmClose} onCancel={onCancelClose} /> : null}
    </section>
  );
}
