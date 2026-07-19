import type { BayesianStudyResponse } from "../../api";
import { constraintText } from "./bayesianDisplay";

export function BayesianStudySummary({ study }: { study: BayesianStudyResponse }) {
  return (
    <section aria-labelledby="bayesian-study-summary-title">
      <div className="panel-heading">
        <div>
          <h4 id="bayesian-study-summary-title">Study 정의와 상태</h4>
          <p>선택한 immutable definition과 현재 lifecycle 상태입니다.</p>
        </div>
      </div>
      <div className="metadata-grid" aria-label="Bayesian study 상태">
        <span>Study 상태</span><strong>{study.status}</strong>
        <span>Method version</span><strong>{study.method_version}</strong>
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
