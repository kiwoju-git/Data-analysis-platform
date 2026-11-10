"""Static mixed-selection report from saved values; no model or history evaluation."""

from html import escape
from typing import Any

from app.i18n.report_text import ReportLocale, report_text
from app.services.report_contract import ReportSection
from app.services.stored_report_primitives import report_table


def mixed_batch_report_section(
    attachment: dict[str, Any], definition: dict[str, Any], locale: ReportLocale
) -> ReportSection:
    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    source, calculation = attachment["source"], attachment["calculation"]
    manual = calculation["schema_version"] == 2
    rows = calculation["items"] if manual else calculation["selected_rows"]
    augmentation = None if manual else calculation["augmentation"]
    policy = calculation["selection_policy"] if manual else calculation["augmentation"]["policy"]
    goals = {goal["response_id"]: goal for goal in attachment["objective"]["responses"]}
    markup = report_table(
        [text("Planning source", "계획 출처"), text("Stored value", "저장값")],
        [
            [text("Policy", "정책"), policy],
            [text("Model ID", "모형 ID"), source["model_id"]],
            [text("Model SHA-256", "모형 SHA-256"), source["model_sha256"]],
            [text("Candidate revision", "후보 revision"), source["candidate_revision_id"]],
            [text("Candidate rows SHA-256", "후보 행 SHA-256"), source["rows_sha256"]],
            [text("Selection SHA-256", "선택 SHA-256"), source["selection_result_sha256"]],
            [
                text("History SHA-256", "관측 이력 SHA-256"),
                attachment["source_observation_history_sha256"],
            ],
            [text("Coordinate encoding", "좌표 인코딩"), "numeric_normalized_category_index_v1"],
            [text("Distance policy", "거리 정책"), rows[0]["distance_policy"]],
        ],
    )
    if attachment["response_models"] is None:
        markup += (
            "<p>"
            + escape(
                text(
                    "This model-free selection has no predicted response, desirability, "
                    "or acquisition value.",
                    "이 모형 없는 선택에는 예측 반응, 만족도 또는 acquisition 값이 없습니다.",
                )
            )
            + "</p>"
        )
    else:
        view, incumbent = attachment["observation_view"], attachment["incumbent"]
        markup += report_table(
            [text("Model evidence", "모형 근거"), text("Stored value", "저장값")],
            [
                [text("Raw observations", "실제 관측 수"), view["raw_observation_count"]],
                [text("Unique conditions", "고유 조건 수"), view["unique_condition_count"]],
                [text("Training rows", "학습 행 수"), view["effective_training_count"]],
                [
                    text("Observed best desirability", "관측 최선 만족도"),
                    incumbent["best_observed_desirability"],
                ],
                [text("Latent incumbent", "잠재 기준값"), incumbent["latent_incumbent_value"]],
            ],
        )
        for response in attachment["response_models"]:
            model, goal = response["model"], goals[response["response_id"]]
            signal = model["signal_kernel"]
            markup += "<h4>" + escape(goal["name"]) + "</h4>"
            markup += report_table(
                [text("Fit setting", "적합 설정"), text("Stored value", "저장값")],
                [
                    [text("Numeric kernel", "숫자 커널"), signal["numeric_signal"]["kind"]],
                    [text("Noise policy", "노이즈 정책"), model["noise"]["mode"]],
                    [
                        text("Measurement noise SD", "측정 노이즈 SD"),
                        model["observation_noise_sd_raw"],
                    ],
                    [text("Unit", "단위"), goal.get("unit")],
                    [
                        text("Curve", "곡선"),
                        goal.get("curve", {}).get("policy", "derringer_suich_linear_v1"),
                    ],
                    ["LML", model["log_marginal_likelihood"]],
                    [text("Fit evaluations", "적합 평가 횟수"), model["optimizer"]["evaluations"]],
                ],
            )
            markup += report_table(
                [
                    text("Factor index", "요인 인덱스"),
                    text("Kind", "유형"),
                    text("Correlation policy", "상관 정책"),
                ],
                [[item["index"], item["kind"], item["policy"]] for item in signal["categories"]],
            )
            markup += report_table(
                [
                    text("Start", "시작점"),
                    text("Final iterate LML", "종료점 LML"),
                    text("Converged", "수렴"),
                    text("Evaluations", "평가 횟수"),
                ],
                [
                    [
                        index + 1,
                        -item["negative_log_likelihood"],
                        item["success"],
                        item["evaluations"],
                    ]
                    for index, item in enumerate(model["optimizer"]["starts"])
                ],
            )
    codes = list(attachment["warnings"])
    if augmentation is not None:
        codes.extend(augmentation.get("warnings", []))
    markup += report_table(
        [text("Stored warning code", "저장된 경고 코드")], [[code] for code in dict.fromkeys(codes)]
    )
    for rank, (row, item) in enumerate(zip(rows, attachment["items"], strict=True), 1):
        markup += (
            f'<section data-batch-rank="{rank}"><h4>'
            f'{escape(text("Selection rank", "선택 순서"))} {rank}</h4>'
        )
        fields = [
            [text("Candidate identity", "후보 식별자"), row["row_id"]],
            [text("Trial ID", "실험 ID"), item["trial"]["trial_id"]],
            [
                text("Nearest existing distance", "가장 가까운 기존점 거리"),
                row["nearest_existing_distance"],
            ],
        ]
        if "desirability_moments" in row:
            fields.extend(
                [
                    [
                        text("Expected desirability", "기대 만족도"),
                        row["desirability_moments"]["mean"],
                    ],
                    [
                        text("Desirability variance", "만족도 분산"),
                        row["desirability_moments"]["variance"],
                    ],
                    [
                        text("Individual Beta EI", "개별 Beta EI"),
                        None if row["acquisition"] is None else row["acquisition"]["value"],
                    ],
                ]
            )
        if manual:
            fields.extend(
                [
                    [text("Marginal planning score", "한계 계획 점수"), row["planning"]["score"]],
                    [
                        text("MC standard error", "MC 표준오차"),
                        row["planning"]["mc_standard_error"],
                    ],
                    [
                        text("Samples", "표본 수"),
                        row["planning"]["sampler"]["effective_sample_count"],
                    ],
                ]
            )
        else:
            step = augmentation["steps"][rank - 1]
            fields.extend(
                [
                    [text("Criterion", "기준"), step["criterion"]],
                    [text("Selection score", "선택 점수"), step["score"]],
                ]
            )
        markup += report_table([text("Field", "항목"), text("Stored value", "저장값")], fields)
        markup += report_table(
            [
                text("Factor", "요인"),
                text("Actual setting", "실제 조건"),
                text("Kind", "유형"),
                text("Unit", "단위"),
            ],
            [
                [
                    factor["name"],
                    row["actual_coordinates"][factor["factor_id"]],
                    factor["domain_kind"],
                    factor.get("unit"),
                ]
                for factor in definition["factors"]
            ],
        )
        if "response_predictions" in row:
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
                        goals[value["response_id"]]["name"],
                        value["mean_raw"],
                        value["latent_standard_deviation_raw"],
                        value["predictive_standard_deviation_raw"],
                        goals[value["response_id"]].get("unit"),
                    ]
                    for value in row["response_predictions"]
                ],
            )
        markup += "</section>"
    markup += (
        "<p>"
        + escape(
            text(
                "Category codes identify levels; they are not numeric distances. "
                "Saved base predictions use completed observations only. "
                "Conditional planning is not measured information. Manual ordering "
                "and augmentation policies do not guarantee a global optimum or JMP "
                "numerical parity. This export neither refits a model nor reads original "
                "data. Actual observations remain separate from predictions.",
                "범주 코드는 수준 식별자이며 숫자 거리가 아닙니다. "
                "저장된 기본 예측은 완료된 관측만 사용합니다. "
                "조건부 계획은 측정된 정보가 아닙니다. 수동 순서와 실험 추가 정책은 "
                "전역 최적점이나 JMP 수치 일치를 보장하지 않습니다. "
                "이 내보내기는 모형을 재학습하거나 원자료를 읽지 않습니다. "
                "실제 관측과 예측은 별도로 유지됩니다.",
            )
        )
        + "</p>"
    )
    return ReportSection(
        "noise_summary",
        text("Saved Mixed Candidate Selection", "저장된 혼합 후보 선택"),
        "rendered",
        markup,
    )
