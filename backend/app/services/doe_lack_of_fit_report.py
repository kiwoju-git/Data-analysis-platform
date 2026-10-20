"""Readable, escaped explanations from stored DOE decomposition metadata only."""

from html import escape
from typing import Any

from app.i18n.report_text import ReportLocale

_REASONS = {
    "no_replicated_design_points": (
        "동일한 실제 설계 조건과 블록 내 반복이 없습니다.",
        "No replicated physical design settings within blocks.",
    ),
    "no_lack_of_fit_df": (
        "최종 모형에 적합성 결여 자유도가 없습니다.",
        "The final model leaves no lack-of-fit degrees of freedom.",
    ),
    "pure_error_variance_zero": (
        "순수오차 분산이 0이므로 F/p를 계산할 수 없습니다.",
        "Pure-error variance is zero; F/p cannot be computed.",
    ),
    "numerical_decomposition_failure": (
        "제곱합 분해 또는 F 계산의 수치적 정합성을 검증할 수 없습니다.",
        "The numerical SS decomposition or F calculation could not be validated.",
    ),
}


def lack_of_fit_report_notice(lack: dict[str, Any], locale: ReportLocale) -> str:
    messages = []
    if not lack.get("available"):
        messages.append(
            _REASONS.get(
                str(lack.get("reason")),
                (
                    "저장 결과에서 적합성 결여 검정을 제공하지 않습니다.",
                    "Lack-of-fit inference is unavailable in this stored result.",
                ),
            )
        )
    if lack.get("non_curvature_reason") in _REASONS:
        reason = _REASONS[lack["non_curvature_reason"]]
        messages.append(("나머지 적합성 결여: " + reason[0], "Other lack of fit: " + reason[1]))
    if lack.get("replication_grouping_policy"):
        messages.append(
            (
                "모형에서 제외된 요인도 포함한 모든 실제 설계 조건과 블록을 "
                "기준으로 반복을 묶습니다. "
                "다른 설계점에 반복이 있으면 중심점이 없어도 검정할 수 있습니다.",
                "Replication uses all physical design factor settings and blocks, "
                "including omitted "
                "factors. Center points are not required when other settings are replicated.",
            )
        )
    return "".join("<p>" + escape(item[0 if locale == "ko" else 1]) + "</p>" for item in messages)
