"""Static mixture batch presentation, using already validated stored values only."""

from html import escape
from typing import Any

from app.i18n.report_text import ReportLocale, report_text
from app.services.report_contract import ReportSection
from app.services.stored_report_primitives import report_table


def mixture_batch_report_section(
    attachment: dict[str, Any], definition: dict[str, Any], locale: ReportLocale
) -> ReportSection:
    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    config, result = attachment["config"], attachment["result"]
    goals = {goal["response_id"]: goal for goal in definition["objective"]["responses"]}
    fields = [
        ("Policy", "정책", result["selection_policy"]),
        ("Distance policy", "거리 정책", result["distance_policy"]),
        ("Model ID", "모형 ID", config["model_id"]),
        ("Model SHA-256", "모형 SHA-256", config["expected_model_sha256"]),
        ("History SHA-256", "이력 SHA-256", config["expected_history_sha256"]),
        ("Candidate revision", "후보 revision", config["candidate_revision_id"]),
        ("Candidate SHA-256", "후보 SHA-256", config["expected_rows_sha256"]),
        ("Selection SHA-256", "선택 SHA-256", attachment["result_sha256"]),
    ]
    markup = report_table(
        [text("Planning source", "계획 출처"), text("Stored value", "저장값")],
        [[text(en, ko), value] for en, ko, value in fields],
    )
    for response in attachment["response_models"]:
        model, goal = response["model"], goals[response["response_id"]]
        markup += "<h4>" + escape(goal["name"]) + "</h4>"
        markup += report_table(
            [text("Fit setting", "적합 설정"), text("Stored value", "저장값")],
            [
                [text("Measurement noise", "측정 노이즈"), model["noise"]["mode"]],
                [text("Measurement noise SD", "측정 노이즈 SD"), model["observation_noise_sd_raw"]],
                [text("Unit", "단위"), goal.get("unit")],
                ["LML", model["log_marginal_likelihood"]],
                [text("Fit evaluations", "적합 평가 횟수"), model["optimizer"]["evaluations"]],
            ],
        )
    for item in attachment["items"]:
        row = item["result"]
        markup += "<h4>" + escape(text("Selection rank", "선택 순서")) + f" {item['rank']}</h4>"
        markup += report_table(
            [text("Factor", "요인"), text("Actual setting", "실제 조건"), text("Unit", "단위")],
            [
                [factor["name"], row["actual_coordinates"][factor["factor_id"]], factor.get("unit")]
                for factor in definition["factors"]
            ],
        )
        markup += report_table(
            [
                text("Response", "반응"),
                text("Base posterior mean", "실제 관측 기반 예측 평균"),
                "Latent SD",
                text("Predictive SD", "새 관측 predictive SD"),
            ],
            [
                [
                    goals[p["response_id"]]["name"],
                    p["mean_raw"],
                    p["latent_standard_deviation_raw"],
                    p["predictive_standard_deviation_raw"],
                ]
                for p in row["response_predictions"]
            ],
        )
        markup += report_table(
            [text("Criterion", "기준"), text("Stored value", "저장값")],
            [
                [text("Expected desirability", "기대 만족도"), row["desirability_moments"]["mean"]],
                [
                    text("Individual Beta EI", "개별 Beta EI"),
                    None if row["acquisition"] is None else row["acquisition"]["value"],
                ],
                [
                    text("Nearest existing distance", "가장 가까운 기존점 거리"),
                    row["nearest_existing_distance"],
                ],
                [
                    text("Nearest selected distance", "가장 가까운 선택점 거리"),
                    row["nearest_selected_distance"],
                ],
            ],
        )
    markup += report_table(
        [text("Stored warning code", "저장된 경고 코드")],
        [[code] for code in attachment["warnings"]],
    )
    markup += (
        "<p>"
        + escape(
            text(
                "Actual component amounts satisfy the declared total. "
                "The model uses stored pseudocomponents; "
                "spacing uses declared actual-domain bounds. "
                "Manual or maximin selection is not joint EI or JMP MaxPro. "
                "All predictions use completed real observations, without refitting during export.",
                "실제 성분량은 선언한 합계를 따릅니다. 모형은 저장된 의사성분 좌표를, "
                "거리는 실제 선언 범위를 사용합니다. "
                "수동 또는 maximin 선택은 결합 EI나 JMP MaxPro가 아닙니다. "
                "표시 예측은 완료된 실제 관측에 기반하며 내보내기 중 다시 적합하지 않습니다.",
            )
        )
        + "</p>"
    )
    return ReportSection(
        "noise_summary", text("Mixture planning evidence", "혼합물 계획 근거"), "rendered", markup
    )
