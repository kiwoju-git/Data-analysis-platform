import type {
  BayesianStudyCloseReason,
  BayesianStudyDeletionPreflightResponse,
  BayesianStudyResponse,
  BayesianTrialResponse,
} from "../../api";
import { coordinateText, type StudyCloseTarget } from "./bayesianDisplay";

export function BayesianStudyCloseConfirmation({
  study,
  target,
  reason,
  note,
  isClosing,
  onConfirm,
  onCancel,
}: {
  study: Pick<BayesianStudyResponse, "study_id" | "name" | "completed_trial_count" | "abandoned_trial_count">;
  target: StudyCloseTarget;
  reason: BayesianStudyCloseReason;
  note: string;
  isClosing: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="info-box" aria-label="Bayesian study terminal action 확인">
      <strong>{study.name} · {study.study_id} · {target === "completed" ? "완료" : "중단"} · {reason}</strong>
      <p>
        최종 관측 {study.completed_trial_count}개, 중단 trial {study.abandoned_trial_count}개를
        현재 history checksum에 고정합니다. 종료 후에는 수정하거나 다시 열 수 없습니다.
      </p>
      {note.trim().length > 0 ? <p>메모: {note.trim()}</p> : null}
      {target === "completed" ? <p>이 상태는 전역 최적해 달성이나 목적함수의 자동 실행을 의미하지 않습니다.</p> : null}
      <div className="button-row">
        <button type="button" className={target === "completed" ? "primary-button" : "secondary-button"} disabled={isClosing} onClick={onConfirm}>
          {isClosing ? "종료 처리 중" : "종료 확인"}
        </button>
        <button type="button" className="secondary-button" disabled={isClosing} onClick={onCancel}>취소</button>
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
  const confirmationIsCurrent = preflight.eligible && preflight.study_id === study.study_id;
  return (
    <div className="error-box" aria-label="Bayesian study irreversible deletion 확인">
      <strong>{study.name} · {study.study_id}</strong>
      <p>{`metadata ${preflight.counts.metadata_record_count}건을 영구 삭제합니다. 삭제 후 복원할 수 없으며 cascade 또는 successor 삭제는 수행하지 않습니다.`}</p>
      <p>{`파일 ${preflight.counts.file_count}개 · ${preflight.counts.file_bytes} bytes. 현재 Bayesian study graph는 workspace 파일을 소유하지 않습니다.`}</p>
      <div className="button-row">
        <button type="button" className="secondary-button" disabled={isDeleting || !confirmationIsCurrent} onClick={onConfirm}>
          {isDeleting ? "영구 삭제 중" : "영구 삭제 확인"}
        </button>
        <button type="button" className="secondary-button" disabled={isDeleting} onClick={onCancel}>취소</button>
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
      {action === "abandon" && trial.origin === "initial_design" ? <p>초기 trial 중단은 추천에 필요한 최소 완료 관측 수를 남기는 경우에만 허용됩니다.</p> : null}
      <div className="button-row">
        <button type="button" className={isCompletion ? "primary-button" : "secondary-button"} disabled={isSaving} onClick={onConfirm}>
          {isSaving ? "처리 중" : isCompletion ? "관측 저장 확인" : "Abandon 확인"}
        </button>
        <button type="button" className="secondary-button" disabled={isSaving} onClick={onCancel}>취소</button>
      </div>
    </div>
  );
}
