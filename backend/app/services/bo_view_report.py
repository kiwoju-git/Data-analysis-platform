"""Owner-locked saved diagnostic reports; no raw data or model execution."""

from html import escape
from typing import Any
from uuid import UUID

from app.api.v1.schemas.reports import BayesianHistoryReportSource, ReportSourceDescriptor
from app.core.config import Settings
from app.i18n.report_text import ReportLocale, report_text
from app.services.bo_views import read_view
from app.services.dedicated_report_readers import invalid
from app.services.report_contract import ReportBody, ReportSection
from app.services.stored_report_primitives import report_plot, report_table

_MODEL_WARNING_MEANINGS = {
    "bayesian_optimization_model_convergence_warning": (
        "Model optimization reported a convergence warning; fitted parameters may be unreliable.",
        "모형 최적화 수렴 경고가 있습니다. 적합 파라미터가 불안정할 수 있습니다.",
    ),
    "bayesian_surrogate_noise_bound": (
        "The fitted noise parameter reached a configured bound.",
        "적합 노이즈 파라미터가 설정 경계에 도달했습니다.",
    ),
    "bayesian_surrogate_signal_bound": (
        "A fitted signal parameter reached a configured bound.",
        "적합 신호 파라미터가 설정 경계에 도달했습니다.",
    ),
    "bayesian_category_unobserved_level_prior_dependent": (
        "Predictions for unobserved category levels are prior-dependent, not measured evidence.",
        "미관측 범주 수준의 예측은 사전 가정에 의존하며 측정 근거가 아닙니다.",
    ),
    "bayesian_category_correlation_unidentified": (
        "Category correlation is not identified by the available observations.",
        "가용 관측으로 범주 상관을 식별할 수 없습니다.",
    ),
    "bayesian_optimization_constant_objective": (
        "The observed objective is constant; predictive interpretation requires caution.",
        "관측 목적값이 일정합니다. 예측 해석에 주의가 필요합니다.",
    ),
}


def resolve_view_report_source(
    settings: Settings, study_id: UUID, view_id: UUID
) -> ReportSourceDescriptor:
    from app.services.dedicated_report_sources import _descriptor, report_source_is_stale

    saved = read_view(settings, study_id, view_id)
    owner = saved.source
    source = BayesianHistoryReportSource.model_validate(
        {
            "study_id": owner.study_id,
            "study_version_id": owner.study_version_id,
            "definition_sha256": owner.definition_sha256,
            "history_revision_id": owner.history_revision_id,
            "expected_source_sha256": owner.history_sha256,
            "attachment": {
                "kind": "view",
                "view_id": saved.view_id,
                "model_id": owner.model_id,
                "model_sha256": owner.model_sha256,
                "model_config_sha256": owner.model_config_sha256,
                "request_sha256": saved.request_sha256,
                "view_sha256": saved.view_sha256,
            },
        }
    )
    return _descriptor(
        source,
        "Saved BO " + saved.kind,
        saved.created_at,
        "/analysis/doe/doe.bayesian_optimization",
        report_source_is_stale(settings, source),
    )


def read_view_report(
    settings: Settings, source: BayesianHistoryReportSource
) -> tuple[dict[str, Any], str, str]:
    attachment = source.attachment
    if attachment.kind != "view":
        raise invalid("report_source_kind_mismatch")
    saved = read_view(settings, source.study_id, attachment.view_id)
    owner = saved.source
    if (
        owner.study_version_id != source.study_version_id
        or owner.definition_sha256 != source.definition_sha256
        or owner.history_revision_id != source.history_revision_id
        or owner.history_sha256 != source.expected_source_sha256
        or owner.model_id != attachment.model_id
        or owner.model_sha256 != attachment.model_sha256
        or owner.model_config_sha256 != attachment.model_config_sha256
        or saved.request_sha256 != attachment.request_sha256
        or saved.view_sha256 != attachment.view_sha256
    ):
        raise invalid("report_source_changed")
    return (
        {
            "saved_view": saved.model_dump(mode="json"),
            "owner": {
                "study_id": str(owner.study_id),
                "study_version_id": str(owner.study_version_id),
            },
        },
        "Saved BO " + saved.kind,
        saved.created_at,
    )


def render_view_body(payload: dict[str, Any], locale: ReportLocale) -> ReportBody:
    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    saved = payload["saved_view"]
    view = saved["payload"]
    metadata = {
        **saved["source"],
        "view_id": saved["view_id"],
        "view_sha256": saved["view_sha256"],
        "request_sha256": saved["request_sha256"],
        "created_at": saved["created_at"],
        "model_refit": False,
    }
    source = report_table(
        [text("Source", "출처"), text("Stored value", "저장값")],
        [[key, value] for key, value in metadata.items()],
    )
    request_markup = report_table(
        [text("Evaluation setting", "평가 설정"), text("Stored value", "저장값")],
        [[key, value] for key, value in saved["evaluation_request"].items()],
    )
    markup = ""
    model_warning_markup = ""
    if view["kind"] == "profiler_matrix":
        mixture = view["policy"] == "source_locked_mixture_profiler_matrix_v1"
        if mixture:
            markup += report_table(
                [text("Stored mixture domain", "저장 혼합물 정의"), text("Value", "값")],
                [[key, value] for key, value in view["mixture_domain"].items()],
            )
        markup += report_table(
            [text("Policy", "정책"), text("Point count", "평가점 수")],
            [[view["policy"], view["point_count"]]],
        )
        markup += report_table(
            [
                text("Fixed constraint", "고정 제약"),
                text("Terms", "항"),
                text("Relation", "관계"),
                text("Bound", "경계"),
            ],
            [
                [
                    constraint["name"],
                    "; ".join(
                        str(term["coefficient"]) + " * " + term["factor_id"]
                        for term in constraint["terms"]
                    ),
                    constraint["relation"],
                    constraint["bound"],
                ]
                for constraint in view["constraints"]
            ]
            or [[text("Constraints", "제약"), text("None", "없음"), "-", "-"]],
        )
        markup += report_table(
            [
                text("Factor", "요인"),
                text("Unit", "단위"),
                text("Fixed hold", "고정 조건"),
                text("Axis meaning", "축 의미"),
                text("Displayed levels", "표시 수준 수"),
                text("Available levels", "가용 수준 수"),
                text("Coverage", "표시 범위"),
            ],
            [
                [
                    axis["name"],
                    axis["unit"],
                    view["holds"][axis["factor_id"]],
                    axis["kind"],
                    len(axis["points"]),
                    axis["available_level_count"],
                    (
                        str(len(axis["points"]))
                        + " of "
                        + str(axis["available_level_count"])
                        + ": "
                        + (
                            text("sampled subset", "표본 부분집합")
                            if len(axis["points"]) < axis["available_level_count"]
                            else text("all available levels", "사용 가능한 전체 수준")
                        )
                    )
                    if axis["available_level_count"] is not None
                    else text(
                        "Continuous axis sample; not all possible values",
                        "연속 축 표본: 전체 값이 아님",
                    ),
                ]
                for axis in view["axes"]
            ],
        )
        for axis in view["axes"]:
            factor = axis["factor_id"]
            if axis.get("path"):
                markup += report_table(
                    [
                        text("Axis", "축"),
                        text(
                            "Co-varying path / conditional process axis",
                            "동반 변화 경로 / 조건부 공정 축",
                        ),
                        text("Feasible interval", "가능 구간"),
                        text("Unavailable reason", "표시 불가 이유"),
                    ],
                    [
                        [
                            axis["name"],
                            axis["path"]["policy"],
                            axis["path"]["feasible_interval"],
                            axis["path"]["unavailable_reason"],
                        ]
                    ],
                )
            if not axis["points"]:
                continue
            numeric = axis["kind"] in {"continuous", "discrete_numeric", "mixture_component"}
            ticks = (
                [
                    (float(i), str(p["actual_coordinates"][factor]))
                    for i, p in enumerate(axis["points"])
                ]
                if not numeric
                else None
            )
            for response_index, response in enumerate(view["responses"]):
                label = response["name"] + (f" ({response['unit']})" if response["unit"] else "")
                metrics = [
                    ("mean_raw", text("Mean", "평균")),
                    ("latent_standard_deviation_raw", "Latent SD"),
                    ("predictive_standard_deviation_raw", "Predictive SD"),
                ]
                for metric, metric_label in metrics:
                    markup += report_plot(
                        label + ": " + metric_label,
                        axis["name"] + (f" ({axis['unit']})" if axis["unit"] else ""),
                        metric_label,
                        [
                            (
                                metric_label,
                                [
                                    (
                                        float(p["actual_coordinates"][factor])
                                        if numeric
                                        else float(i),
                                        p["response_predictions"][response_index][metric],
                                        str(p["actual_coordinates"][factor]),
                                    )
                                    for i, p in enumerate(axis["points"])
                                ],
                            )
                        ],
                        x_ticks=ticks,
                        lines=numeric,
                    )
            markup += report_plot(
                text("Composite desirability", "종합 만족도"),
                axis["name"],
                text("Expected desirability", "기대 만족도"),
                [
                    (
                        "D",
                        [
                            (
                                float(p["actual_coordinates"][factor]) if numeric else float(i),
                                p["desirability_moments"]["mean"],
                                str(p["actual_coordinates"][factor]),
                            )
                            for i, p in enumerate(axis["points"])
                        ],
                    )
                ],
                x_ticks=ticks,
                lines=numeric,
            )
            markup += report_table(
                [
                    text("Axis", "축"),
                    text("Setting", "조건"),
                    text("All actual coordinates", "전체 실제 좌표"),
                    text("Constraints satisfied", "제약 충족"),
                    text("Response", "반응"),
                    "Mean",
                    "Latent SD",
                    "Predictive SD",
                    "Composite desirability",
                ],
                [
                    [
                        axis["name"],
                        p["actual_coordinates"][factor],
                        p["actual_coordinates"],
                        p["constraints_satisfied"],
                        response["name"],
                        p["response_predictions"][j]["mean_raw"],
                        p["response_predictions"][j]["latent_standard_deviation_raw"],
                        p["response_predictions"][j]["predictive_standard_deviation_raw"],
                        p["desirability_moments"]["mean"],
                    ]
                    for p in axis["points"]
                    for j, response in enumerate(view["responses"])
                ],
            )
        warning = (
            text(
                "Mixture component profiles co-vary the other components "
                "to preserve the declared total. The stored path preserves excess-above-lower "
                "or deficit-below-upper ratios; it is not an independent component effect. "
                "Process-factor profiles hold the composition fixed. Predictions are not "
                "measurements. Composite desirability assumes independent response GPs.",
                "혼합물 성분 프로파일은 선언한 총량을 유지하도록 다른 성분도 함께 변합니다. "
                "저장 경로는 하한 초과량 또는 상한 부족량의 비율을 유지하며 "
                "독립 성분 효과가 아닙니다. 공정 요인 프로파일은 조성을 고정합니다. "
                "예측은 측정값이 아니며 종합 만족도는 독립 반응 GP를 가정합니다.",
            )
            if mixture
            else text(
                "Conditional profiles hold all other factors fixed. Categories are labels, "
                "not numeric distances. Constraint validity is stored per point; "
                "predictions are not measurements. Composite desirability assumes independent "
                "response GPs; correlations between responses are not modeled.",
                "조건부 프로파일은 다른 모든 요인을 고정합니다. "
                "범주는 수치 거리가 아닌 레이블입니다. "
                "제약 충족 여부는 각 점에 저장되며 예측은 측정값이 아닙니다. "
                "종합 만족도는 독립 반응 GP를 가정하며 반응 간 상관을 모형화하지 않습니다.",
            )
        )
        model_warning_markup = (
            report_table(
                [text("Stored model warning code", "저장 모형 경고 코드"), text("Meaning", "의미")],
                [
                    [
                        code,
                        text(*_MODEL_WARNING_MEANINGS[code])
                        if code in _MODEL_WARNING_MEANINGS
                        else text(
                            "Stored source-model qualification; "
                            "retain this code when interpreting results.",
                            "저장 원본 모형의 제한 사항입니다. "
                            "결과 해석 시 이 코드를 유지하십시오.",
                        ),
                    ]
                    for code in view["warnings"]
                ],
            )
            if view["warnings"]
            else ""
        )
    else:
        calculation = view["calculation"]
        names = {r["response_id"]: r for r in view["responses"]}
        markup += report_table(
            [text("Policy", "정책"), text("Stored value", "저장값")],
            [
                [key, value]
                for key, value in calculation.items()
                if key not in {"responses", "warnings"}
            ],
        )
        for diagnostic in calculation["responses"]:
            response = names[diagnostic["response_id"]]
            label = response["name"] + (f" ({response['unit']})" if response["unit"] else "")
            markup += "<h4>" + escape(label) + "</h4>"
            markup += report_table(
                ["N raw", "N effective", "N scored", "RMSE", "R squared", "Reason"],
                [
                    [
                        diagnostic[k]
                        for k in (
                            "raw_observation_count",
                            "effective_training_count",
                            "n_scored",
                            "rmse",
                            "r_squared",
                            "r_squared_reason",
                        )
                    ]
                ],
            )
            markup += report_plot(
                label,
                text("Observed", "관측"),
                text("Conditional LOO prediction", "조건부 LOO 예측"),
                [
                    (
                        label,
                        [
                            (p["observed"], p["predicted"], p["trial_id"])
                            for p in diagnostic["points"]
                        ],
                    )
                ],
            )
            markup += report_table(
                ["Trial ID", "Index", "Observed", "Predicted", "Residual"],
                [
                    [
                        p[k]
                        for k in (
                            "trial_id",
                            "observation_index",
                            "observed",
                            "predicted",
                            "residual",
                        )
                    ]
                    for p in diagnostic["points"]
                ],
            )
        warning = text(
            "Conditional row LOO is not external validation. Full-fit parameters include "
            "held-out observations; repeats do not validate new conditions.",
            "조건부 행 LOO는 외부 검증이 아닙니다. 전체 적합 파라미터에는 제외 관측의 정보가 "
            "포함되며 반복은 새 조건을 검증하지 않습니다.",
        )
        warning += " " + "; ".join(calculation["warnings"])
    return ReportBody(
        "bayesian",
        (
            ReportSection("source", text("Source", "출처"), "rendered", source),
            ReportSection("definition", text("Saved diagnostic", "저장 진단"), "rendered", markup),
            ReportSection(
                "history",
                text("Saved evaluation request", "저장 평가 요청"),
                "rendered",
                request_markup,
            ),
            ReportSection(
                "warnings",
                text("Limitations", "제한 사항"),
                "rendered",
                "<p>" + escape(warning) + "</p>" + model_warning_markup,
            ),
        ),
    )
