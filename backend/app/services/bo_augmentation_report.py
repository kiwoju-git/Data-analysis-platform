"""Display only immutable augmentation evidence; no fitting, search or source rows."""

from html import escape
from typing import Any

from app.i18n.report_text import ReportLocale, report_text
from app.services.bo_auto_evidence_report import auto_evidence_markup
from app.services.report_contract import ReportSection
from app.services.stored_report_primitives import report_table


def augmentation_report_section(
    attachment: dict[str, Any], definition: dict[str, Any], locale: ReportLocale
) -> ReportSection:
    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    selection = attachment["calculation"]
    evidence = selection.get("auto_evidence")
    trace, source = selection["augmentation"], attachment["source"]
    goals = {row["response_id"]: row for row in attachment["objective"]["responses"]}
    markup = report_table(
        [text("Selection source", "선택 출처"), text("Stored value", "저장값")],
        [
            [text("Augmentation policy", "추가 실험 선택 정책"), trace["policy"]],
            [text("Model-free", "모형 미사용"), source["model_id"] is None],
            [text("Model ID", "모형 ID"), source["model_id"]],
            [text("Model SHA-256", "모형 SHA-256"), source["model_sha256"]],
            [text("Candidate revision", "후보 revision"), source["candidate_revision_id"]],
            [text("Candidate SHA-256", "후보 SHA-256"), source["rows_sha256"]],
            [text("Selection SHA-256", "선택 SHA-256"), source["selection_result_sha256"]],
            [text("Distance policy", "거리 정책"), trace["distance_policy"]],
            [text("Evaluations", "평가 횟수"), trace["evaluations"]],
            [text("Evaluation budget", "평가 예산"), trace["max_evaluations"]],
        ],
    )
    if evidence is not None:
        markup += auto_evidence_markup(evidence, goals, locale)
    uncertainty = trace.get("response_uncertainty")
    if uncertainty:
        markup += report_table(
            [
                text("Response", "반응"),
                text("Saved Y scale", "저장된 Y 척도"),
                text("Normalized importance", "정규화 중요도"),
            ],
            [
                [
                    goals[row["response_id"]]["name"],
                    row["normalization_scale"],
                    row["normalized_importance"],
                ]
                for row in uncertainty["context"]
            ],
        )
        markup += "<p>" + escape(uncertainty["policy"]) + "</p>"
    for step, row, item in zip(
        trace["steps"], selection["selected_rows"], attachment["items"], strict=True
    ):
        markup += (
            f'<section data-batch-rank="{step["rank"]}"><h4>'
            f'{escape(text("Selection rank", "선택 순서"))} {step["rank"]}</h4>'
        )
        markup += report_table(
            [text("Criterion", "기준"), text("Stored value", "저장값")],
            [
                [text("Candidate row", "후보 행"), row["source_row_number"]],
                [text("Trial ID", "실험 ID"), item["trial"]["trial_id"]],
                [text("Selection criterion", "선택 기준"), step["criterion"]],
                [text("Criterion score", "기준 점수"), step["score"]],
                [text("Score scale", "점수 척도"), step["score_scale"]],
                [text("Direction", "방향"), step["optimization_direction"]],
                [
                    text("Nearest existing distance", "가장 가까운 기존점 거리"),
                    step["nearest_existing_distance"],
                ],
                [
                    text("Nearest selected distance", "가장 가까운 선택점 거리"),
                    step["nearest_selected_distance"],
                ],
            ],
        )
        markup += report_table(
            [text("Factor", "요인"), text("Actual setting", "실제 조건"), text("Unit", "단위")],
            [
                [factor["name"], row["actual_coordinates"][factor["factor_id"]], factor.get("unit")]
                for factor in definition["factors"]
            ],
        )
        if "response_predictions" in row:
            markup += report_table(
                [
                    text("Response", "반응"),
                    text("Mean", "평균"),
                    text("Latent SD", "잠재 SD"),
                    text("New-measurement predictive SD", "새 측정 예측 SD"),
                    text("Unit", "단위"),
                ],
                [
                    [
                        goals[p["response_id"]]["name"],
                        p["mean_raw"],
                        p["latent_standard_deviation_raw"],
                        p["predictive_standard_deviation_raw"],
                        goals[p["response_id"]].get("unit"),
                    ]
                    for p in row["response_predictions"]
                ],
            )
        markup += "</section>"
    markup += report_table(
        [text("Stored warning code", "저장된 경고 코드")], [[code] for code in trace["warnings"]]
    )
    markup += (
        "<p>"
        + escape(
            text(
                "This is the saved fixed-candidate augmentation order, not measured outcomes "
                "or a global optimum guarantee. Model-free policies contain no GP predictions. "
                "Model-based uncertainty uses the completed-observation posterior, not acquired "
                "information from selected runs. RMS and alternating Refine rules are explicit "
                "product policies, not verified JMP formulas. Export neither refits nor reruns "
                "the selection.",
                "저장된 고정 후보의 추가 실험 선택 순서이며 "
                "측정 결과나 전역 최적점 보장이 아닙니다. "
                "모형 미사용 정책에는 GP 예측이 없습니다. 모형 기반 불확실성은 완료된 관측만 "
                "사용하며 선택한 실험을 이미 관측한 것으로 취급하지 않습니다. RMS와 교대 Refine "
                "규칙은 명시적인 제품 정책으로 JMP 수식과의 일치를 검증하지 않았습니다. "
                "내보내기에서 재학습하거나 선택을 다시 실행하지 않습니다.",
            )
        )
        + "</p>"
    )
    return ReportSection(
        "noise_summary", text("Saved Augmentation", "저장된 추가 실험 선택"), "rendered", markup
    )
