import type { MixtureStudy } from "../../api/boMixture";
import { InteractiveScatterChart } from "../../charts/InteractiveScatterChart";
import { paddedNumericRange } from "../../charts/chartScale";
import { useI18n } from "../../i18n/LocaleProvider";
import { formatExactNumericValue as exact } from "../../statisticalNumberFormat";

export function BayesianMixtureProgress({ study }: { study: MixtureStudy }) {
  const { locale } = useI18n(), ko = locale === "ko";
  return <section className="bo-planning" aria-label={ko ? "혼합물 관측 추이" : "Mixture observation progress"}>
    <h4>{ko ? "관측 추이" : "Observation progress"}</h4>
    {study.objective.responses.map(response => {
      const completed = study.trials.filter(trial => trial.state === "completed");
      const rows = completed.flatMap(trial => { const value = trial.response_values?.[response.response_id]; return typeof value === "number" && Number.isFinite(value) ? [{ id: trial.trial_id, x: trial.trial_number, y: value, title: String(trial.trial_number), ariaLabel: `${response.name}: ${exact(value)}`, className: "bo-planning-profile-mean", details: [{ label: response.name, value: `${exact(value)}${response.unit ? ` ${response.unit}` : ""}` }] }] : []; });
      const description = ko ? "실제 측정 반응입니다. 예측이나 인과 효과가 아닙니다." : "Measured responses, not predictions or causal effects.";
      return <section key={response.response_id}><h5>{response.name}</h5><p>N={rows.length}; {ko ? "제외" : "excluded"}={completed.length - rows.length}</p>{rows.length ? <InteractiveScatterChart annotations={[description]} chartId={`mixture-progress-${response.response_id}`} sourceKey={`${study.study_version_id}:${study.observation_history.observation_history_sha256}`} title={response.name} description={description} emptyLabel={ko ? "완료 관측 없음" : "No completed observations"} points={rows} xLabel={ko ? "실험 번호" : "Trial number"} yLabel={response.name} yUnit={response.unit} xRange={paddedNumericRange(rows.map(row => row.x))} yRange={paddedNumericRange(rows.map(row => row.y))} collapsibleDetails /> : <p>{ko ? "완료 관측 없음" : "No completed observations"}</p>}</section>;
    })}
  </section>;
}
