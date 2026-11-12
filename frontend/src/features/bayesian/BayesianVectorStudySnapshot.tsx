import type { BayesianStudyResponse } from "../../api";
import { apiRoutes } from "../../api/routes";
import { useI18n } from "../../i18n/LocaleProvider";
import { desirabilityMessages } from "../../i18n/boDesirability";
import { formatExactNumericValue } from "../../statisticalNumberFormat";
import { boText } from "./boNoisePolicy";
import { BayesianCurveSummary } from "./BayesianCurvePolicy";
import { BayesianDatasetSourceSummary } from "./BayesianDatasetSourceSummary";

export function BayesianVectorStudySnapshot({ study }: { study: BayesianStudyResponse }) {
  const { locale } = useI18n();
  if (study.objective.goal_type !== "desirability") return null;
  const objective = study.objective;
  const stateLabel = (state: string) => state === "completed"
    ? boText(locale, "완료", "Completed") : state === "pending" || state === "active"
      ? boText(locale, "대기", "Pending") : boText(locale, "중단", "Abandoned");
  return <section aria-label={boText(locale, "다중 반응 저장 이력", "Stored multiresponse history")}>
    <div className="panel-heading"><h4>{study.name}</h4>
      <a className="secondary-button" download href={apiRoutes.bayesianInitialDesignCsv(study.study_id)}>
        {boText(locale, "초기 실험 CSV", "Initial experiment CSV")}
      </a>
    </div>
    <div className="notice-box" role="status">
      {desirabilityMessages(locale).savedNotice}
    </div>
    <p>{objective.name} · {boText(locale, "완료 / 전체", "Completed / total")}: {study.completed_trial_count} / {study.trial_count}</p>
    {study.initial_design?.policy === "dataset_observations_v1" && <BayesianDatasetSourceSummary receipt={study.initial_design} />}
    <div className="table-wrap"><table className="result-table">
      <caption>{boText(locale, "저장된 반응 목표", "Stored response goals")}</caption>
      <thead><tr>{[boText(locale, "반응", "Response"), boText(locale, "목표", "Goal"),
        boText(locale, "단위", "Unit"), boText(locale, "하한", "Lower"),
        boText(locale, "목표값", "Target"), boText(locale, "상한", "Upper"),
        boText(locale, "중요도", "Importance")].map(label => <th key={label} scope="col">{label}</th>)}</tr></thead>
      <tbody>{objective.responses.map(response => <tr key={response.response_id}>
        <th scope="row">{response.name}</th>
        <td>{response.goal === "maximize" ? boText(locale, "최대화", "Maximize")
          : response.goal === "minimize" ? boText(locale, "최소화", "Minimize")
            : boText(locale, "목표값 맞추기", "Match target")}</td>
        <td>{response.unit ?? "-"}</td>
        {[response.lower, response.target, response.upper, response.importance].map((value, index) =>
          <td key={index}>{formatExactNumericValue(value)}</td>)}</tr>)}</tbody>
    </table></div>
    <div className="table-wrap"><table className="result-table">
      <caption>{boText(locale, "실제 측정값", "Measured responses")}</caption>
      <thead><tr><th scope="col">Trial</th><th scope="col">{boText(locale, "상태", "State")}</th>
        {study.factors.map(factor => <th key={factor.factor_id} scope="col">{factor.name}{factor.unit ? ` [${factor.unit}]` : ""}</th>)}
        {objective.responses.map(response => <th key={response.response_id} scope="col">{response.name}{response.unit ? ` [${response.unit}]` : ""}</th>)}
      </tr></thead>
      <tbody>{study.trials.map(trial => <tr key={trial.trial_id}>
        <th scope="row">{trial.trial_number}</th><td>{stateLabel(trial.state)}</td>
        {study.factors.map(factor => <td key={factor.factor_id}>{formatExactNumericValue(trial.actual_coordinates[factor.factor_id])}</td>)}
        {objective.responses.map(response => <td key={response.response_id}>{formatExactNumericValue(trial.response_values?.[response.response_id])}</td>)}
      </tr>)}</tbody>
    </table></div>
    <BayesianCurveSummary responses={objective.responses} />
    <details className="technical-details"><summary>{boText(locale, "출처", "Source")}</summary>
      <p>Study: {study.study_id}</p><p>Definition SHA-256: {study.definition_sha256}</p>
      <p>History: {study.observation_history.history_revision_id}</p>
      <p>History SHA-256: {study.observation_history.observation_history_sha256}</p>
      <p>Curve policy: {objective.curve_policy}</p>
    </details>
  </section>;
}
