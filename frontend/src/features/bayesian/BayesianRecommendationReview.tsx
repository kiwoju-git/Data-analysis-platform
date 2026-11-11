import { Check, X } from "lucide-react";
import type { BayesianRecommendationReviewResponse, BayesianStudyResponse } from "../../api";
import { useI18n } from "../../i18n/LocaleProvider";
import { formatMeasurement } from "../../statisticalNumberFormat";
import { boText } from "./boNoisePolicy";
import { BayesianSurrogateSummary } from "./BayesianSurrogateSummary";
import { BayesianCandidatePurpose } from "./BayesianCandidatePurpose";

export function BayesianRecommendationReview({
  review, study, disabled, isConfirming, onConfirm, onDiscard,
}: {
  review: BayesianRecommendationReviewResponse;
  study: BayesianStudyResponse;
  disabled: boolean;
  isConfirming: boolean;
  onConfirm: () => void;
  onDiscard: () => void;
}) {
  const { locale } = useI18n();
  const text = (ko: string, en: string) => boText(locale, ko, en);
  const number = (value: number | null) => formatMeasurement(value, locale);
  const unit = study.objective.unit;
  const calculation = review.calculation;
  return (
    <section aria-labelledby="bayesian-review-title">
      <div className="panel-heading">
        <h4 id="bayesian-review-title">{text("실험 후보 검토", "Review experiment candidates")}</h4>
        <span className="status-pill">{text("미확정", "Not committed")}</span>
      </div>
      <p className="notice-box" role="status">
        {text("아직 실험 이력에 등록되지 않았습니다. 확정하면 이 순서의 후보 전체가 대기 실험으로 저장됩니다.",
          "No trials have been created. Confirming saves this entire ordered batch as pending experiments.")}
      </p>
      <p className="cell-subtext">
        {text("임시 후보는 최대 20분 동안 유지됩니다. 서버 재시작 또는 검토 보관 한도 초과 시 더 일찍 만료될 수 있습니다.",
          "Unconfirmed candidates last up to 20 minutes and may expire earlier on restart or when the review cache is full.")}
        {unit ? ` ${text("반응 단위", "Response unit")}: ${unit}` : null}
      </p>
      <BayesianSurrogateSummary model={calculation.shared_model} factors={study.factors} />
      <div className="table-wrap">
        <table className="result-table bayesian-review-table">
          <thead><tr>
            <th>{text("순위", "Rank")}</th>
            <th>{text("실제 조건", "Actual settings")}</th>
            <th>{text("예측 평균", "Predicted mean")}</th>
            <th>Latent SD</th>
            <th>{text("새 관측 predictive SD", "New-observation predictive SD")}</th>
            <th>{text("배치 한계 EI/ETI", "Marginal batch EI/ETI")}</th>
            <th>{text("제약", "Constraints")}</th>
            <th>{text("목표 / 선정 기준", "Goal / selection")}</th>
          </tr></thead>
          <tbody>{calculation.items.map(item => (
            <tr key={`${review.review_id}:${item.rank}`}>
              <td>{item.rank}</td>
              <td>{study.factors.map(factor => (
                <div key={factor.factor_id}>{factor.name}: {number(item.actual_coordinates[factor.factor_id])}{factor.unit ? ` ${factor.unit}` : ""}</div>
              ))}</td>
              <td>{number(item.predicted_objective_mean)}</td>
              <td>{number(item.latent_standard_deviation)}</td>
              <td>{number(item.predictive_standard_deviation)}</td>
              <td>{number(item.acquisition_value_raw)}</td>
              <td>{item.constraint_evaluations.every(constraint => constraint.satisfied)
                ? text("충족", "Satisfied") : text("위반", "Violated")}</td>
              <td><BayesianCandidatePurpose goal={calculation.shared_model.objective_goal_type} acquisition={item.acquisition_kind}
                xi={calculation.incumbent.xi_standardized} conditionedOn={item.planning.conditioned_on_selected_ranks} /></td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <p className="cell-subtext">
        {text("평균과 SD는 완료 관측의 예측이며 실제 측정값이 아닙니다. 후순위 후보의 점수는 선행 후보에 조건화한 계획 값입니다.",
          "Means and SDs are predictions from completed observations, not measurements. Later scores are planning values conditioned on earlier candidates.")}
      </p>
      {calculation.search_budget.searches.some(search => search.all_acquisitions_zero) ? (
        <p className="warning-box" role="status">
          {text("일부 선택 단계에서 평가한 모든 후보의 acquisition이 수치적으로 0이었습니다. 높은 개선 가능성의 증거로 해석하지 마세요.",
            "All evaluated acquisitions were numerically zero at one or more selection steps. This is not evidence of high improvement potential.")}
        </p>
      ) : null}
      {calculation.warnings.length > 0 ? <details>
        <summary>{text("계산 경고", "Calculation warnings")}</summary>
        <ul>{calculation.warnings.map(code => <li key={code}>{code}</li>)}</ul>
      </details> : null}
      <div className="button-row">
        <button type="button" className="primary-button" disabled={disabled || isConfirming} onClick={onConfirm}>
          <Check size={16} aria-hidden="true" />
          {isConfirming ? text("실험 확정 중", "Committing experiments") : text("이 후보로 실험 확정", "Confirm these experiments")}
        </button>
        <button type="button" className="secondary-button" disabled={disabled || isConfirming} onClick={onDiscard}>
          <X size={16} aria-hidden="true" />{text("후보 닫기", "Dismiss candidates")}
        </button>
      </div>
    </section>
  );
}
