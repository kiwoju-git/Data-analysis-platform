"""Static presentation of a saved manual candidate batch, with no model evaluation."""

from html import escape
from typing import Any

from app.i18n.report_text import ReportLocale, report_text
from app.services.bo_fit_quality_report import fit_quality_markup
from app.services.report_contract import ReportSection
from app.services.stored_report_primitives import report_table


def planning_report_section(
    attachment: dict[str, Any],
    definition: dict[str, Any],
    locale: ReportLocale,
) -> ReportSection:
    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    source = attachment["source"]
    selection = attachment["calculation"]
    goals = {goal["response_id"]: goal for goal in attachment["objective"]["responses"]}
    markup = report_table(
        [text("Planning source", "계획 출처"), text("Stored value", "저장값")],
        [
            [text("Policy", "정책"), selection["selection_policy"]],
            [text("Fitted model", "적합모형"), source["model_id"]],
            [text("Model SHA-256", "모형 SHA-256"), source["model_sha256"]],
            [text("Candidate revision", "후보 revision"), source["candidate_revision_id"]],
            [text("Candidate rows SHA-256", "후보 행 SHA-256"), source["rows_sha256"]],
            [text("Selection", "선택"), source["selection_id"]],
            [text("Selection SHA-256", "선택 SHA-256"), source["selection_result_sha256"]],
            [
                text("Raw observation count", "실제 관측 수"),
                attachment["observation_view"]["raw_observation_count"],
            ],
            [
                text("Unique conditions", "고유 조건 수"),
                attachment["observation_view"]["unique_condition_count"],
            ],
            [
                text("Observed best desirability", "관측 최선 만족도"),
                attachment["incumbent"]["best_observed_desirability"],
            ],
            [
                text("Latent incumbent", "잠재 기준값"),
                attachment["incumbent"]["latent_incumbent_value"],
            ],
        ],
    )
    markup += report_table(
        [
            text("Response", "반응"),
            text("Kernel", "커널"),
            text("Noise policy", "노이즈 정책"),
            text("Noise SD", "노이즈 SD"),
            text("Unit", "단위"),
            text("Curve", "곡선"),
            text("All optimizer starts converged", "모든 최적화 시작점 수렴"),
            text("Fit evaluations", "적합 평가 횟수"),
        ],
        [
            [
                goals[row["response_id"]]["name"],
                row["model"]["signal_kernel"]["family"],
                row["model"]["noise"]["mode"],
                row["model"]["observation_noise_sd_raw"],
                goals[row["response_id"]].get("unit"),
                goals[row["response_id"]]
                .get("curve", {})
                .get("policy", "derringer_suich_linear_v1"),
                all(start["success"] for start in row["model"]["optimizer"]["starts"])
                if row["model"]["optimizer"]["starts"]
                else None,
                row["model"]["optimizer"]["evaluations"],
            ]
            for row in attachment["response_models"]
        ],
    )
    markup += report_table(
        [text("Stored warning code", "저장된 경고 코드")],
        [[code] for code in attachment["warnings"]],
    )
    markup += fit_quality_markup(
        {
            "objective": attachment["objective"],
            "shared_model": {"response_models": attachment["response_models"]},
        },
        locale,
    )
    for item, stored_trial in zip(selection["items"], attachment["items"], strict=True):
        markup += (
            f'<section data-batch-rank="{item["rank"]}"><h4>'
            f'{escape(text("Selection rank", "선택 순서"))} {item["rank"]}</h4>'
        )
        markup += report_table(
            [text("Field", "항목"), text("Stored value", "저장값")],
            [
                [text("Candidate row", "후보 행"), item["source_row_number"]],
                [text("Candidate identity", "후보 식별자"), item["row_id"]],
                [text("Trial ID", "실험 ID"), stored_trial["trial"]["trial_id"]],
                [
                    text("Expected desirability", "기대 만족도"),
                    item["desirability_moments"]["mean"],
                ],
                [
                    text("Desirability variance", "만족도 분산"),
                    item["desirability_moments"]["variance"],
                ],
                [text("Individual Beta EI", "개별 Beta EI"), item["acquisition"]["value"]],
                [text("Marginal batch score", "배치 한계 점수"), item["planning"]["score"]],
                [text("MC standard error", "MC 표준오차"), item["planning"]["mc_standard_error"]],
                [
                    text("Nearest existing distance", "가장 가까운 기존점 거리"),
                    item["nearest_existing_distance"],
                ],
                [
                    text("Nearest selected distance", "가장 가까운 선택점 거리"),
                    item["nearest_selected_distance"],
                ],
            ],
        )
        markup += report_table(
            [text("Factor", "요인"), text("Actual setting", "실제 조건"), text("Unit", "단위")],
            [
                [
                    factor["name"],
                    item["actual_coordinates"][factor["factor_id"]],
                    factor.get("unit"),
                ]
                for factor in definition["factors"]
            ],
        )
        markup += report_table(
            [
                text("Response", "반응"),
                text("Mean", "평균"),
                text("Latent SD", "잠재 SD"),
                text("New-observation predictive SD", "새 관측 예측 SD"),
                text("Unit", "단위"),
            ],
            [
                [
                    goals[row["response_id"]]["name"],
                    row["mean_raw"],
                    row["latent_standard_deviation_raw"],
                    row["predictive_standard_deviation_raw"],
                    goals[row["response_id"]].get("unit"),
                ]
                for row in item["response_predictions"]
            ],
        )
        sampler = item["planning"]["sampler"]
        markup += report_table(
            [text("Planning assumption", "계획 가정"), text("Stored value", "저장값")],
            [
                [text("Root seed", "기본 시드"), sampler["root_seed"]],
                [text("Samples", "표본 수"), sampler["effective_sample_count"]],
                [
                    text("Conditioned selection ranks", "조건부 선택 순서"),
                    ", ".join(map(str, sampler["conditioned_on_selected_ranks"])),
                ],
            ],
        )
        markup += "</section>"
    markup += (
        "<p>"
        + escape(
            text(
                "These are manually ordered candidates, not automatic search optima. "
                "The saved model was not refitted. Predictions use completed observations only; "
                "conditional planning uncertainty is not measured information. Beta/MC scores "
                "do not establish exact noisy EI or JMP numerical parity. "
                "No fitting or source-row read occurs during export.",
                "사용자가 순서대로 고른 후보이며 자동 탐색 최적점이 아닙니다. "
                "저장된 모형을 재학습하지 않았습니다. 예측은 완료된 관측만 사용하며 "
                "조건부 계획 불확실성은 실제 측정 정보가 아닙니다. "
                "Beta/MC 점수는 정확한 noisy EI 또는 JMP 수치 일치를 뜻하지 않습니다. "
                "내보내기 중 학습하거나 원자료를 읽지 않습니다.",
            )
        )
        + "</p>"
    )
    return ReportSection(
        "noise_summary", text("Saved Candidate Selection", "저장된 후보 선택"), "rendered", markup
    )
