"""Saved fit diagnostics only; never refit or reopen training rows."""

from html import escape
from typing import Any

from app.i18n.report_text import ReportLocale, report_text
from app.services.stored_report_primitives import report_plot, report_table


def fit_quality_markup(result: dict[str, Any], locale: ReportLocale) -> str:
    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    goals = {r["response_id"]: r for r in result["objective"]["responses"]}
    sections = []
    for response in result["shared_model"]["response_models"]:
        model = response["model"]
        evidence = model.get("fit_diagnostics")
        if evidence is None:
            continue
        title = text("Surrogate fit diagnostics", "대리모형 적합 진단")
        starts = model["optimizer"]["starts"]
        initial = evidence["start_initial_negative_log_likelihoods"]
        best = evidence["start_best_evaluations"]
        rows = [
            [
                i + 1,
                -initial[i],
                -best[i]["negative_log_likelihood"],
                -s["negative_log_likelihood"],
                s["evaluations"],
                s["success"],
            ]
            for i, s in enumerate(starts)
        ]
        headers = [
            text("Start", "시작점"),
            text("Initial LML", "시작 LML"),
            text("Best visited LML", "최선 평가 LML"),
            text("Final iterate LML", "종료점 LML"),
            text("Evaluations", "평가 횟수"),
            text("Converged", "수렴"),
        ]
        markup = (
            f'<section data-fit-policy="{escape(evidence["policy"], quote=True)}">'
            f'<h4>{escape(title)}: {escape(goals[response["response_id"]]["name"])}</h4>'
        )
        markup += report_table(
            [text("Setting", "설정"), text("Stored value", "저장값")],
            [
                [text("Policy", "정책"), evidence["policy"]],
                [text("Screened points", "선별 평가점"), len(evidence["screening"])],
                [
                    text("Deterministic starts", "결정적 시작점"),
                    evidence["deterministic_start_count"],
                ],
                [text("Random restarts", "무작위 재시작"), model["optimizer"]["restarts"]],
                [text("Selected LML", "선택 LML"), model["log_marginal_likelihood"]],
                [
                    text("Total fit evaluations", "총 적합 평가 횟수"),
                    model["optimizer"]["evaluations"],
                ],
                [text("Selected origin", "선택 출처"), evidence["selected"]["stage"]],
            ],
        )
        markup += report_plot(
            title,
            headers[0],
            "LML",
            [
                (headers[1], [(float(i + 1), -v, str(i + 1)) for i, v in enumerate(initial)]),
                (
                    headers[2],
                    [
                        (float(i + 1), -v["negative_log_likelihood"], str(i + 1))
                        for i, v in enumerate(best)
                    ],
                ),
                (
                    headers[3],
                    [
                        (float(i + 1), -s["negative_log_likelihood"], str(i + 1))
                        for i, s in enumerate(starts)
                    ],
                ),
            ],
            x_ticks=[(float(i + 1), str(i + 1)) for i in range(len(starts))],
            reference_lines=[
                ("y", model["log_marginal_likelihood"], text("Selected LML", "선택 LML"))
            ],
        )
        markup += report_table(headers, rows)
        markup += report_table(
            [
                text("Parameter", "파라미터"),
                text("Factor index (zero-based)", "요인 인덱스 (0부터)"),
                text("Boundary", "경계"),
                text("Value", "값"),
            ],
            [
                [h["parameter"], h["factor_index"], h["side"], h["value"]]
                for h in evidence["bound_hits"]
            ],
        )
        markup += (
            "<p>"
            + escape(
                text(
                    "Higher LML is better only within this response and normalization. "
                    "Starts are not optimizer iterations. All screening and local evaluations "
                    "share the fit budget. No global optimum or JMP numerical equivalence "
                    "is guaranteed.",
                    "LML은 같은 반응과 정규화 안에서만 클수록 좋습니다. "
                    "시작점은 반복 이력이 아닙니다. 선별과 국소 평가 모두 적합 예산을 사용합니다. "
                    "전역 최적점이나 JMP 수치 일치를 보장하지 않습니다.",
                )
            )
            + "</p></section>"
        )
        sections.append(markup)
    return "".join(sections)
