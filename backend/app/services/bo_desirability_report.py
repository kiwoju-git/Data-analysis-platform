"""Read-only report presentation of a saved response-vector recommendation."""

from html import escape
from typing import Any

from app.i18n.report_text import ReportLocale, report_text
from app.services.bo_fit_quality_report import fit_quality_markup
from app.services.report_contract import ReportSection
from app.services.stored_report_primitives import report_table


def desirability_report_section(
    attachment: dict[str, Any], definition: dict[str, Any], locale: ReportLocale
) -> ReportSection:
    result = attachment["calculation"]
    if result["schema_version"] == 4:
        return _candidate_section(attachment, definition, locale, result["items"][0])
    markup = fit_quality_markup(result, locale)
    if result["schema_version"] == 7:
        markup += report_table(
            [
                report_text(locale, en="Response", ko="반응"),
                report_text(locale, en="Curve policy", ko="곡선 정책"),
                "L",
                "T",
                "H",
                "d(L)",
                "d(T)",
                "d(H)",
            ],
            [
                [
                    r["name"],
                    r.get("curve", {}).get("policy", "derringer_suich_linear_v1"),
                    r["lower"],
                    r["target"],
                    r["upper"],
                    r.get("curve", {}).get(
                        "lower_desirability", 0 if r["lower"] is not None else None
                    ),
                    1,
                    r.get("curve", {}).get(
                        "upper_desirability", 0 if r["upper"] is not None else None
                    ),
                ]
                for r in result["objective"]["responses"]
            ],
        )
    for item, candidate in zip(attachment["items"], result["items"], strict=True):
        label = report_text(locale, en="Batch selection rank", ko="배치 선택 순서")
        section = _candidate_section(attachment, definition, locale, candidate)
        markup += (
            f'<section data-batch-rank="{candidate["rank"]}">'
            f'<h4>{escape(label)} {candidate["rank"]}</h4>'
        )
        markup += report_table(
            [report_text(locale, en="Trial ID", ko="실험 ID")],
            [[str(item["trial"]["trial_id"])]],
        )
        markup += (section.markup or "") + "</section>"
    markup += (
        "<p>"
        + escape(
            report_text(
                locale,
                en=(
                    "The ordered batch uses conditional MC/Beta marginal improvement, "
                    "not JMP augmentation or exact joint EI. Base predictions use completed "
                    "observations only. Conditional planning variance is not information "
                    "already measured. MC standard error excludes approximation and "
                    "hyperparameter uncertainty. Rank is selection order, not a "
                    "success-probability ranking."
                ),
                ko=(
                    "순서 있는 배치는 조건부 MC/Beta 한계 개선을 사용하며 JMP 증강 또는 "
                    "정확한 joint EI가 아닙니다. 기본 예측은 완료된 관측만 사용합니다. "
                    "조건부 계획 분산은 실제로 측정한 정보가 아닙니다. MC 표준오차는 "
                    "근사 및 하이퍼파라미터 불확실성을 포함하지 않습니다. "
                    "순위는 선택 순서이며 성공 확률 순위가 아닙니다."
                ),
            )
        )
        + "</p>"
    )
    return ReportSection(
        "noise_summary",
        report_text(locale, en="Desirability Batch Recommendation", ko="만족도 배치 추천"),
        "rendered",
        markup,
    )


def _candidate_section(
    attachment: dict[str, Any],
    definition: dict[str, Any],
    locale: ReportLocale,
    candidate: dict[str, Any],
) -> ReportSection:
    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    result = attachment["calculation"]
    goals = {r["response_id"]: r for r in definition["objective"]["responses"]}
    models = {r["response_id"]: r["model"] for r in result["shared_model"]["response_models"]}
    markup = report_table(
        [
            text("Response", "반응"),
            text("Unit", "단위"),
            text("Predicted mean", "예측 평균"),
            text("Latent SD", "잠재 SD"),
            text("New-observation predictive SD", "새 관측 예측 SD"),
            text("Kernel", "커널"),
            text("Noise mode", "노이즈 모드"),
            text("Observation noise SD", "관측 노이즈 SD"),
        ],
        [
            [
                goals[p["response_id"]]["name"],
                goals[p["response_id"]].get("unit"),
                p["mean_raw"],
                p["latent_standard_deviation_raw"],
                p["predictive_standard_deviation_raw"],
                models[p["response_id"]]["signal_kernel"]["family"],
                models[p["response_id"]]["noise"]["mode"],
                models[p["response_id"]]["observation_noise_sd_raw"],
            ]
            for p in candidate["response_predictions"]
        ],
    )
    view, incumbent = result["observation_view"], result["incumbent"]
    markup += report_table(
        [text("Setting", "설정"), text("Stored value", "저장값")],
        [
            [text("Raw observation count", "실제 관측 수"), view["raw_observation_count"]],
            [text("Unique conditions", "고유 조건 수"), view["unique_condition_count"]],
            [text("Effective training count", "유효 학습 수"), view["effective_training_count"]],
            [
                text("Observed best desirability", "관측 최선 만족도"),
                incumbent["best_observed_desirability"],
            ],
            [
                text("Posterior-mean incumbent", "사후평균 기준값"),
                incumbent["latent_incumbent_value"],
            ],
            [
                text("Expected joint desirability", "기대 종합 만족도"),
                candidate["desirability_moments"]["mean"],
            ],
            [
                text("Desirability variance", "만족도 분산"),
                candidate["desirability_moments"]["variance"],
            ],
            [
                text("Beta moment-matched EI", "Beta 모멘트 근사 EI"),
                candidate["acquisition"]["value"],
            ],
            [
                text("Xi (desirability units)", "Xi (만족도 단위)"),
                candidate["acquisition"]["xi_desirability"],
            ],
            [text("Policy", "정책"), result["policy"]],
        ],
    )
    if "planning" in candidate:
        planning = candidate["planning"]
        sampler = planning["sampler"]
        markup += report_table(
            [text("Planning setting", "계획 설정"), text("Stored value", "저장값")],
            [
                [text("Marginal batch improvement", "배치 한계 개선"), planning["score"]],
                [text("MC standard error", "MC 표준오차"), planning["mc_standard_error"]],
                [text("Posterior samples", "사후 표본 수"), sampler["effective_sample_count"]],
                [text("Requested samples", "요청 표본 수"), sampler["requested_sample_count"]],
                [text("Root seed", "기본 시드"), sampler["root_seed"]],
                [text("Search seed", "탐색 시드"), planning["search_seed"]],
                [
                    text("Conditioned ranks", "조건부 선택 순서"),
                    ", ".join(map(str, sampler["conditioned_on_selected_ranks"])),
                ],
                [
                    text("Nearest selected distance", "가장 가까운 선택점 거리"),
                    candidate["nearest_selected_distance"],
                ],
                [
                    text("Nearest existing distance", "가장 가까운 기존점 거리"),
                    candidate["nearest_existing_distance"],
                ],
            ],
        )
        markup += report_table(
            [
                text("Response", "반응"),
                text("Conditional planning variance", "조건부 계획 분산"),
                text("Sample seed", "표본 시드"),
            ],
            [
                [goals[key]["name"], value, sampler["response_sample_seeds"][key]]
                for key, value in planning["conditional_variance_raw"].items()
            ],
        )
    markup += report_table(
        [text("Factor", "요인"), text("Actual setting", "실제 조건"), text("Unit", "단위")],
        [
            [f["name"], candidate["actual_coordinates"][f["factor_id"]], f.get("unit")]
            for f in definition["factors"]
        ],
    )
    markup += (
        "<p>"
        + escape(
            text(
                "Independent response GPs and the stored per-response curves "
                "and Beta moment-matched EI. "
                "Predictions are not measured responses. Jitter is not future measurement noise. "
                "This is not exact noisy EI or verified JMP numerical parity. "
                "No fitting occurs during export.",
                "독립 반응 GP, 반응별 저장 곡선과 Beta 모멘트 근사 EI를 사용합니다. "
                "예측은 실제 측정값이 아니며 jitter는 미래 측정 노이즈가 아닙니다. "
                "정확한 noisy EI 또는 JMP 수치 일치를 뜻하지 않습니다. "
                "내보내기 중 학습하지 않습니다.",
            )
        )
        + "</p>"
    )
    return ReportSection(
        "noise_summary", text("Desirability Recommendation", "만족도 기반 추천"), "rendered", markup
    )
