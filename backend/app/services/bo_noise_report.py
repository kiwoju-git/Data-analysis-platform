"""Read-only presentation of the versioned noisy-BO recommendation contract."""

from html import escape
from typing import Any

from app.i18n.report_text import ReportLocale, report_text
from app.services.report_contract import ReportSection
from app.services.stored_report_primitives import report_table


def bo_noise_report_section(
    attachment: Any, definition: dict[str, Any], locale: ReportLocale
) -> ReportSection:
    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    title = text("Noise-aware Recommendation", "관측 노이즈 기반 추천")
    if not isinstance(attachment, dict) or attachment.get("result_schema_version") != 2:
        return ReportSection(
            "noise_summary", title, "not_applicable", reason="legacy_or_no_attachment"
        )
    model = attachment["shared_model"]
    incumbent = attachment["incumbent"]
    view = attachment["observation_view"]
    factors = definition["factors"]
    unit = definition["objective"].get("unit")

    def raw_label(en: str, ko: str) -> str:
        return text(en, ko) + (f" ({unit})" if unit else "")

    markup = report_table(
        [text("Setting", "설정"), text("Stored value", "저장값")],
        [
            [text("Noise mode", "노이즈 모드"), model["noise"]["mode"]],
            [
                text("Fitted scaled noise variance", "적합 표준화 노이즈 분산"),
                model["noise"]["fitted_variance_scaled"],
            ],
            [
                raw_label("Observation noise SD", "관측 노이즈 표준편차"),
                model["observation_noise_sd_raw"],
            ],
            [
                text("Numerical jitter (not measurement noise)", "수치 jitter (측정 노이즈 아님)"),
                model["jitter"],
            ],
            [
                text(
                    "Raw observations / unique conditions / training rows",
                    "실제 관측 / 고유 조건 / 학습 행",
                ),
                f'{view["raw_observation_count"]} / {view["unique_condition_count"]} / '
                f'{view["effective_training_count"]}',
            ],
            [text("Observation view policy", "관측 학습 뷰 정책"), view["mode"]],
            [
                raw_label("Best observed response", "관측 최선 반응"),
                incumbent["best_observed_objective"],
            ],
            [
                raw_label("Latent incumbent response", "잠재 기준 반응"),
                incumbent["latent_incumbent_value_raw"],
            ],
            [
                raw_label("Latent incumbent target distance", "잠재 기준 목표 거리"),
                incumbent["latent_incumbent_distance_raw"],
            ],
            [
                text("Xi (standardized response)", "Xi (표준화 반응 단위)"),
                incumbent["xi_standardized"],
            ],
            [raw_label("Xi", "Xi"), incumbent["xi_raw"]],
            [text("Batch policy", "배치 정책"), attachment["batch_policy"]],
        ],
    )
    headers = [text("Batch rank", "배치 순서")]
    headers += [
        str(factor["name"]) + (f" ({factor['unit']})" if factor.get("unit") else "")
        for factor in factors
    ]
    headers += [
        raw_label("Base posterior mean", "실제 관측 기반 예측 평균"),
        raw_label("Latent SD", "잠재 표준편차"),
        raw_label("New-observation predictive SD", "새 관측 예측 표준편차"),
        text("Marginal EI/ETI (standardized)", "한계 EI/ETI (표준화)"),
        raw_label("Marginal EI/ETI", "한계 EI/ETI"),
        text("MC draws", "MC 표본 수"),
        text("Sample seed", "표본 seed"),
        text("Conditioned ranks (planning only)", "조건부 순서 (계획 전용)"),
        text("Conditional latent SD (scaled; planning only)", "조건부 잠재 SD (표준화; 계획 전용)"),
    ]
    markup += report_table(
        headers,
        [
            [item["rank"]]
            + [item["actual_coordinates"][factor["factor_id"]] for factor in factors]
            + [
                item["predicted_objective_mean"],
                item["latent_standard_deviation"],
                item["predictive_standard_deviation"],
                item["acquisition_value_standardized"],
                item["acquisition_value_raw"],
                item["planning"]["effective_sample_count"],
                item["planning"]["sample_seed"],
                item["planning"]["conditioned_on_selected_ranks"],
                item["planning"]["conditional_latent_sd_scaled"],
            ]
            for item in attachment["items"]
        ],
    )
    markup += report_table(
        [
            text("Member trial IDs", "구성 실험 ID"),
            text("N", "N"),
            raw_label("Mean", "평균"),
            text("Within-group SS", "그룹 내 제곱합"),
            text("Sample variance", "표본 분산"),
        ],
        [
            [
                group["member_trial_ids"],
                group["n"],
                group["mean"],
                group["within_ss"],
                group["sample_variance"],
            ]
            for group in view["groups"]
        ],
    )
    notice = text(
        "Posterior-mean plug-in EI/ETI and greedy joint-latent Monte Carlo improvement "
        "are not exact qNEI. Planning samples are not observations. "
        "Displayed predictions use only completed real observations. "
        "Jitter is excluded from future measurement noise. "
        "Batch rank is not a success-probability ranking. "
        "Nearby diagnostics do not merge training data. "
        "Independent homoscedastic errors are an assumption.",
        "사후 평균 기준 EI/ETI와 탐욕적 결합 잠재 MC 개선은 exact qNEI가 아닙니다. "
        "계획 표본은 실제 관측이 아니며 표시 예측은 완료된 실제 관측만 사용합니다. "
        "Jitter는 미래 측정 노이즈에서 제외됩니다. 배치 순서는 성공 확률 순위가 아닙니다. "
        "근접 진단은 학습 자료를 병합하지 않습니다. 독립적인 동일 분산 오차는 모형 가정입니다.",
    )
    return ReportSection("noise_summary", title, "rendered", markup + f"<p>{escape(notice)}</p>")
