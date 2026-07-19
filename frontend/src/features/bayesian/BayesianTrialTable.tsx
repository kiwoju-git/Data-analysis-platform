import type { BayesianStudyResponse } from "../../api";
import { coordinateText, type PendingTrialTransition } from "./bayesianDisplay";
import { BayesianTrialTransitionConfirmation } from "./BayesianTransitionConfirmations";

export function BayesianTrialTable({
  study,
  observations,
  pendingTransition,
  isSaving,
  actionsDisabled,
  onObservationChange,
  onRequestTransition,
  onConfirmTransition,
  onCancelTransition,
}: {
  study: BayesianStudyResponse;
  observations: Record<string, string>;
  pendingTransition: PendingTrialTransition | null;
  isSaving: boolean;
  actionsDisabled: boolean;
  onObservationChange: (trialId: string, value: string) => void;
  onRequestTransition: (trialId: string, action: "complete" | "abandon") => void;
  onConfirmTransition: () => void;
  onCancelTransition: () => void;
}) {
  return (
    <section aria-labelledby="bayesian-trials-title">
      <div className="panel-heading"><div><h4 id="bayesian-trials-title">Trial과 실제 관측</h4><p>관측 저장과 abandon은 되돌릴 수 없는 terminal transition입니다.</p></div></div>
      <div className="table-wrap">
        <table className="result-table">
          <thead><tr><th>Trial</th><th>종류</th><th>실제 조건</th><th>상태</th><th>관측값</th><th>처리</th></tr></thead>
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
                      disabled={study.status !== "active" || isSaving}
                      onChange={(event) => onObservationChange(trial.trial_id, event.currentTarget.value)}
                    />
                  ) : trial.objective_value}
                </td>
                <td>
                  <div className="button-row">
                    <button type="button" className="primary-button" disabled={trial.state !== "pending" || actionsDisabled} onClick={() => onRequestTransition(trial.trial_id, "complete")}>관측 저장</button>
                    <button type="button" className="secondary-button" disabled={trial.state !== "pending" || actionsDisabled} onClick={() => onRequestTransition(trial.trial_id, "abandon")}>Abandon</button>
                  </div>
                  {pendingTransition?.trialId === trial.trial_id ? (
                    <BayesianTrialTransitionConfirmation
                      trial={trial}
                      action={pendingTransition.action}
                      objectiveValue={observations[trial.trial_id] ?? ""}
                      isSaving={isSaving}
                      onConfirm={onConfirmTransition}
                      onCancel={onCancelTransition}
                    />
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
