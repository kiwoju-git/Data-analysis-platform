import type { BayesianNoiseBatchResponse } from "../../api";
import { useI18n } from "../../i18n/LocaleProvider";
import { formatMeasurement } from "../../statisticalNumberFormat";
import { boText } from "./boNoisePolicy";

export function BayesianNoiseBatchResult({ batch, study }: { batch: BayesianNoiseBatchResponse; study?: { objective: { unit: string | null } } }) {
  const { locale } = useI18n();
  const text = (ko: string, en: string) => boText(locale, ko, en), number = (value: number | null) => formatMeasurement(value, locale);
  const unit = study?.objective.unit ?? text("반응 단위", "response units");
  const stateLabels = { pending: text("실험 대기", "Awaiting experiments"), partially_completed: text("일부 완료", "Partially completed"), completed: text("전체 완료", "All completed"), abandoned: text("전체 포기", "All abandoned"), closed_mixed: text("완료 및 포기", "Completed and abandoned") };
  return <section aria-labelledby="bayesian-batch-result-title" aria-label={text("노이즈 인지 추천 결과", "Noise-aware recommendation results")}>
    <div className="panel-heading"><h4 id="bayesian-batch-result-title">{text("추천 batch 결과", "Recommendation batch results")}</h4><span className="status-pill">{stateLabels[batch.batch_state]}</span></div>
    <div className="table-wrap"><table className="result-table"><tbody>
      <tr><th>{text("실제 관측 N / 고유 조건 / 학습 N", "Raw N / unique conditions / training N")}</th><td>{batch.observation_view.raw_observation_count} / {batch.observation_view.unique_condition_count} / {batch.observation_view.effective_training_count}</td></tr>
      <tr><th>{text("관측 최선값", "Best observed value")}</th><td>{number(batch.incumbent.best_observed_objective)} ({unit})</td></tr>
      <tr><th>{text("관측 위치의 latent 기준값", "Latent incumbent at observed locations")}</th><td>{number(batch.incumbent.latent_incumbent_value_raw)} ({unit})</td></tr>
      {batch.incumbent.latent_incumbent_distance_raw !== null ? <tr><th>{text("Latent 목표 거리", "Latent target distance")}</th><td>{number(batch.incumbent.latent_incumbent_distance_raw)} ({unit})</td></tr> : null}
      <tr><th>{text("추정/지정 측정 SD", "Estimated/fixed measurement SD")}</th><td>{number(batch.shared_model.observation_noise_sd_raw)} ({unit}) · {batch.shared_model.noise.mode}</td></tr>
      <tr><th>{text("최적화", "Optimizer")}</th><td>{batch.shared_model.optimizer.name} · {batch.shared_model.optimizer.evaluations} {text("평가", "evaluations")} · {batch.shared_model.optimizer.restarts} {text("재시작", "restarts")}</td></tr>
    </tbody></table></div>
    <p className="cell-subtext">{text("예측 평균과 SD의 단위", "Unit of predicted means and SDs")}: {unit}</p>
    <div className="table-wrap"><table className="result-table bayesian-batch-result-table"><thead><tr>
      {[text("순위", "Rank"), text("실제 조건", "Actual settings"), text("예측 평균", "Predicted mean"), "Latent SD", text("새 관측 predictive SD", "New-observation predictive SD"), text("배치 한계 EI/ETI", "Marginal batch EI/ETI"), text("상태 / 상세", "Status / details")].map(label => <th key={label}>{label}</th>)}
    </tr></thead><tbody>{batch.items.map((item, index) => <tr key={item.item_id}>
      <td>{item.rank}</td><td>{Object.entries(item.actual_coordinates).map(([id, value]) => <div key={id}>{id}: {number(value)}</div>)}</td>
      <td>{number(item.predicted_objective_mean)}</td><td>{number(item.latent_standard_deviation)}</td><td>{number(item.predictive_standard_deviation)}</td>
      <td>{number(item.acquisition_value_raw)} ({unit})<div className="cell-subtext">{text("표준화", "Standardized")}: {number(item.acquisition_value_standardized)}</div></td>
      <td>{item.current_trial.state}<details><summary>{text("계산 근거", "Calculation details")}</summary>
        <dl className="bayesian-reason-metrics">
          <div><dt>{text("기존 trial 거리", "Nearest existing trial")}</dt><dd>{number(item.nearest_existing_distance)}</dd></div>
          <div><dt>{text("선행 선택 거리", "Nearest selected candidate")}</dt><dd>{number(item.nearest_selected_distance)}</dd></div>
          <div><dt>{text("MC 표본 수", "MC samples")}</dt><dd>{item.planning.effective_sample_count} / {item.planning.requested_sample_count}</dd></div>
          <div><dt>{text("계획상 조건부 latent SD (표준화)", "Planning conditional latent SD (standardized)")}</dt><dd>{number(item.planning.conditional_latent_sd_scaled)}</dd></div>
          <div><dt>{text("조건화한 순위", "Conditioned-on ranks")}</dt><dd>{item.planning.conditioned_on_selected_ranks.join(", ") || "-"}</dd></div>
          <div><dt>{text("샘플 시드", "Sample seed")}</dt><dd>{item.planning.sample_seed}</dd></div>
          <div><dt>{text("제약", "Constraints")}</dt><dd>{item.constraint_evaluations.every(value => value.satisfied) ? text("충족", "Satisfied") : text("위반", "Violated")}</dd></div>
          <div><dt>{text("탐색 종료", "Search termination")}</dt><dd>{batch.search_budget.searches[index]?.termination_reason ?? "-"}</dd></div>
        </dl>
        {item.constraint_evaluations.length ? <ul>{item.constraint_evaluations.map(value => <li key={value.constraint_id}>{value.constraint_id}: {value.satisfied ? text("충족", "Satisfied") : text("위반", "Violated")}</li>)}</ul> : null}
        {batch.search_budget.searches[index]?.all_acquisitions_zero ? <p className="warning-box">{text("모든 평가 후보의 acquisition이 수치적으로 0입니다. 높은 개선 가능성의 증거로 해석하지 마세요.", "All evaluated acquisitions are numerically zero; this is not evidence of high improvement potential.")}</p> : null}
      </details></td>
    </tr>)}</tbody></table></div>
    <p className="cell-subtext">{text("표의 평균과 두 SD는 실제 완료 관측만 이용합니다. 조건부 계획 SD는 실제로 얻은 정보가 아닙니다. 순위는 성공확률 순서가 아니며 전역 최적을 보장하지 않습니다.", "Means and both SDs use completed observations only. Conditional planning SD is not acquired evidence. Ranks are not success probabilities; global optimality is not guaranteed.")}</p>
    {batch.warnings.length ? <div className="warning-box" role="status"><strong>{text("저장된 경고", "Stored warnings")}</strong><ul>{batch.warnings.map(code => <li key={code}>{code}</li>)}</ul></div> : null}
    <details><summary>{text("학습 관측과 재현 정보", "Training observations and provenance")}</summary>
      <p>{text("원 이력과 관측은 변경하지 않습니다.", "Raw history and observations are unchanged.")} {batch.source_history_revision_id}</p>
      <p>{text("수치 안정화 jitter", "Numerical jitter")}: {number(batch.shared_model.jitter)} · xi: {number(batch.incumbent.xi_standardized)} ({text("표준화 Y", "standardized Y")})</p>
      <p>{text("적합된 측정 분산 (표준화 Y)", "Fitted measurement variance (standardized Y)")}: {number(batch.shared_model.noise.fitted_variance_scaled)} · {text("설정 경계", "Configured bounds")}: {batch.shared_model.noise.bounds_scaled?.map(number).join(" / ") ?? "-"}</p>
      <ul>{batch.shared_model.optimizer.starts.map((start, index) => <li key={index}>{text("최적화 시작", "Optimizer start")} {index + 1}: {start.success ? text("수렴", "Converged") : text("수렴하지 않음", "Not converged")} ({start.termination_reason})</li>)}</ul>
      <div className="table-wrap"><table className="result-table"><thead><tr><th>{text("Trial 구성원", "Trial members")}</th><th>N</th><th>{text("평균", "Mean")}</th><th>{text("그룹 내 SS", "Within-group SS")}</th></tr></thead>
        <tbody>{batch.observation_view.groups.map(group => <tr key={group.member_trial_ids.join(":")}><td>{group.member_trial_ids.join(", ")}</td><td>{group.n}</td><td>{number(group.mean)}</td><td>{number(group.within_ss)}</td></tr>)}</tbody></table></div>
      {batch.observation_view.mode === "nearby_diagnostics" ? <>
        <p>{text("근접 진단 (학습 데이터 변경 없음)", "Nearby diagnostics (training data unchanged)")}: {batch.observation_view.nearby_diagnostics.units}</p>
        <div className="table-wrap"><table className="result-table"><thead><tr><th>{text("Trial 구성원", "Trial members")}</th><th>{text("최대 정규화 거리", "Maximum normalized distance")}</th><th>{text("요인별 최대 거리", "Maximum per-factor distances")}</th><th>{text("반응 최소 / 최대", "Response min / max")}</th><th>{text("반응 표본 분산", "Response sample variance")}</th></tr></thead>
          <tbody>{batch.observation_view.nearby_diagnostics.groups.map(group => <tr key={group.member_trial_ids.join(":")}><td>{group.member_trial_ids.join(", ")}</td><td>{number(group.maximum_normalized_distance)}</td><td>{Object.entries(group.maximum_axis_distances).map(([id, value]) => <div key={id}>{id}: {number(value)}</div>)}</td><td>{group.response_range.map(number).join(" / ")}</td><td>{number(group.response_sample_variance)}</td></tr>)}</tbody></table></div>
      </> : null}
      <ul>{batch.limitations.map((value, index) => <li key={index}>{value}</li>)}</ul>
    </details>
  </section>;
}
