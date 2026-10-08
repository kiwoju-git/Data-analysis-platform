"""Static report projection of saved Two Variances values, without fitting or I/O."""

from html import escape
from typing import Any

from app.i18n.report_text import ReportLocale, report_text
from app.services.stored_report_primitives import report_plot, report_table, report_value


def ratio_interval_svg(payload: dict[str, Any], locale: ReportLocale, scale: str) -> str:
    interval = payload["ratio_interval"]
    estimate = payload["ratio_estimate"]["value"]
    null_ratio = payload["hypothesis"]["ratio"]
    lower = interval["lower"]["value"]
    upper = interval["upper"]["value"]
    finite = [estimate, null_ratio, lower] + ([] if upper is None else [upper])
    low, high = min(finite), max(finite)
    pad = (high - low or 1) * 0.1
    low, high = max(0, low - pad), high + pad

    def x(value: float) -> float:
        return 75 + (value - low) / (high - low) * 500

    title = report_text(locale, en="Ratio confidence interval", ko="비율 신뢰구간")
    comparison = report_text(locale, en="Comparison", ko="비교")
    unbounded = report_text(locale, en="Unbounded upper limit", ko="상한 없음")
    null_label = report_text(locale, en="Hypothesized ratio", ko="귀무가설 비율")
    end = x(high if upper is None else upper)
    parts = [
        f'<svg viewBox="0 0 640 210" role="img" aria-label="{escape(title)}">',
        f'<title>{escape(title)}</title><desc>{escape(scale)}; '
        f'{interval["confidence_level"]*100:g}%</desc>',
        '<path d="M75 30V150H575" fill="none" stroke="#637083"/>',
        f'<text x="10" y="90" font-size="10">{escape(comparison)}</text>',
        f'<line x1="{x(null_ratio):.3f}" x2="{x(null_ratio):.3f}" y1="30" y2="150" '
        'stroke="#777" stroke-dasharray="4 3"/>',
        f'<text x="{x(null_ratio):.3f}" y="22" text-anchor="middle" font-size="10">'
        f"{escape(null_label)} {null_ratio:.6g}</text>",
        f'<line x1="{x(lower):.3f}" x2="{end:.3f}" y1="85" y2="85" '
        'stroke="#225aa7" stroke-width="2"/>',
        f'<circle cx="{x(estimate):.3f}" cy="85" r="4" fill="#225aa7" '
        f'data-value="{estimate!r}"><title>{estimate:.10g}</title></circle>',
    ]
    if upper is None:
        parts.append(
            f'<path d="M{end-7:.3f} 79L{end:.3f} 85L{end-7:.3f} 91" '
            'fill="none" stroke="#225aa7"/><text x="575" y="112" '
            f'text-anchor="end" font-size="11">{escape(unbounded)}</text>'
        )
    for index in range(5):
        value = low + (high - low) * index / 4
        parts.append(
            f'<text x="{x(value):.3f}" y="170" text-anchor="middle" '
            f'font-size="10">{value:.4g}</text>'
        )
    parts.append(
        f'<text x="325" y="193" text-anchor="middle" font-size="12">{escape(scale)}</text></svg>'
    )
    return "".join(parts)


def two_variances_warning(code: str, locale: ReportLocale = "en") -> str:
    messages = {
        "two_variances_independence_required": (
            "Independent groups and observations are required.",
            "그룹과 관측값의 독립성이 필요합니다.",
        ),
        "two_variances_nonrejection_not_equivalence": (
            "Non-rejection does not prove equal variances.",
            "비기각은 분산이 같음을 증명하지 않습니다.",
        ),
        "two_variances_f_normality_sensitive": (
            "Normal-theory F inference is sensitive to non-normality.",
            "정규이론 F 검정은 비정규성에 민감합니다.",
        ),
        "two_variances_ratio_ci_unavailable": (
            "The selected Brown-Forsythe method does not provide a ratio confidence interval.",
            "Brown–Forsythe 검정에서는 비율 신뢰구간을 제공하지 않습니다.",
        ),
        "two_variances_complete_case_exclusions": (
            "Missing group/response and nonnumeric response rows were excluded.",
            "그룹·반응 결측 또는 비수치 반응 행을 제외했습니다.",
        ),
        "two_variances_display_points_limited": (
            "Charts contain at most 500 saved points per group; calculations use all usable rows.",
            "그래프는 그룹별 최대 500점을 표시하며 계산에는 유효한 모든 행을 사용합니다.",
        ),
    }
    en, ko = messages.get(
        code, ("Review the saved warning code.", "저장된 경고 코드를 확인하세요.")
    )
    return report_text(locale, en=en, ko=ko)


def render_two_variances_report(payload: dict[str, Any], locale: ReportLocale) -> str:
    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    if payload.get("schema_version") != 1 or payload.get("summary_type") != "two_variances_test":
        raise ValueError("analysis_report_schema_unsupported")
    try:
        groups, test, interval = payload["groups"], payload["test"], payload["ratio_interval"]
        if len(groups) != 2 or not payload["plot"]["groups"]:
            raise ValueError("analysis_report_payload_invalid")
        method = (
            "Brown-Forsythe (median Levene)"
            if payload["method"] == "brown_forsythe"
            else text("Normal-theory F", "정규이론 F")
        )
        response = payload["response"]["display_name"]
        unit = payload["response"].get("unit")
        response_label = response + (f" ({unit})" if unit else "")
        ratio = payload["ratio_estimate"]
        hypothesis = payload["hypothesis"]
        scale = (
            text("Variance ratio", "분산 비율")
            if ratio["scale"] == "variance"
            else text("Standard deviation ratio", "표준편차 비율")
        )
        alternative = {
            "two_sided": text("Not equal", "같지 않음"),
            "less": text("Less", "작음"),
            "greater": text("Greater", "큼"),
        }[hypothesis["alternative"]]
        parts = [
            '<section data-two-variances-report="1"><h3>'
            + escape(text("Two Variances", "두 분산 비교"))
            + "</h3>"
        ]
        parts.append(
            report_table(
                [text("Setting", "설정"), text("Value", "값")],
                [
                    [text("Method", "방법"), method],
                    [text("Response", "반응"), response_label],
                    [text("Group column", "그룹 변수"), payload["group_column"]["display_name"]],
                    [
                        text("Numerator / denominator", "분자 / 분모"),
                        groups[0]["label"] + " / " + groups[1]["label"],
                    ],
                    [
                        text("Used / excluded rows", "사용 / 제외 행"),
                        f'{payload["sample"]["n_used"]} / {payload["sample"]["n_excluded"]}',
                    ],
                    [
                        text("Complete-case handling", "완전 사례 처리"),
                        payload["sample"]["missing_policy"],
                    ],
                    [scale, ratio["value"]],
                    [text("Hypothesized ratio", "귀무가설 비율"), hypothesis["ratio"]],
                    [text("Alternative", "대립가설"), alternative],
                    [text("Confidence level", "신뢰수준"), hypothesis["confidence_level"]],
                ],
            )
        )
        parts.append(
            report_table(
                [
                    text("Group", "그룹"),
                    "N",
                    text("Mean", "평균"),
                    text("Variance", "분산"),
                    text("Standard deviation", "표준편차"),
                ],
                [
                    [
                        group["label"],
                        group["n"],
                        group["mean"],
                        group["variance"],
                        group["standard_deviation"],
                    ]
                    for group in groups
                ],
            )
        )
        parts.append(
            report_table(
                [text("Statistic", "검정통계량"), "DF1", "DF2", "p", "alpha"],
                [[test[key] for key in ("statistic", "df1", "df2", "p_value", "alpha")]],
            )
        )
        conclusion = (
            text(
                "Evidence against the specified ratio hypothesis "
                "in favor of the selected alternative.",
                "지정한 비율 귀무가설에 반대하며 선택한 대립가설을 지지하는 근거가 있습니다.",
            )
            if test["reject"]
            else text(
                "Insufficient evidence against the specified ratio hypothesis; "
                "non-rejection does not establish equivalence.",
                "지정한 비율 귀무가설을 기각할 근거가 부족합니다. "
                "비기각은 동등함을 증명하지 않습니다.",
            )
        )
        parts.append(f"<p>{escape(conclusion)}</p>")
        if interval["available"]:

            def bound(item: dict[str, Any]) -> str:
                return (
                    text("Unbounded", "상한 없음")
                    if item["kind"] == "unbounded"
                    else report_value(item["value"])
                )

            parts.append(
                report_table(
                    [
                        text("Ratio confidence interval", "비율 신뢰구간"),
                        text("Lower", "하한"),
                        text("Upper", "상한"),
                    ],
                    [
                        [
                            interval["confidence_level"],
                            bound(interval["lower"]),
                            bound(interval["upper"]),
                        ]
                    ],
                )
            )
            parts.append(ratio_interval_svg(payload, locale, scale))
        else:
            parts.append(
                "<p>"
                + escape(two_variances_warning("two_variances_ratio_ci_unavailable", locale))
                + "</p>"
            )
        series = [
            (
                group["key"],
                [
                    (float(index + 1), float(point["value"]), str(point["row_number"]))
                    for point in group["points"]
                ],
            )
            for index, group in enumerate(payload["plot"]["groups"])
        ]
        parts.append(
            report_plot(
                text("Group response values", "그룹별 반응값"),
                text("Group (1 numerator, 2 denominator)", "그룹 (1 분자, 2 분모)"),
                response_label,
                series,
                x_ticks=[(float(index + 1), group["label"]) for index, group in enumerate(groups)],
            )
        )
        displayed = sum(group["n_displayed"] for group in payload["plot"]["groups"])
        parts.append(
            "<p>"
            + escape(
                text(
                    f'Displayed {displayed} / used {payload["sample"]["n_used"]}; '
                    'row labels are filtered analysis row numbers.',
                    f'표시 {displayed} / 사용 {payload["sample"]["n_used"]}; '
                    '행 번호는 필터 적용 후 분석 행 번호입니다.',
                )
            )
            + "</p>"
        )
        parts.append(
            "<ul>"
            + "".join(
                "<li>" + escape(two_variances_warning(code, locale)) + "</li>"
                for code in payload["warnings"]
            )
            + "</ul></section>"
        )
        return "".join(parts)
    except (KeyError, TypeError, IndexError) as exc:
        raise ValueError("analysis_report_payload_invalid") from exc
