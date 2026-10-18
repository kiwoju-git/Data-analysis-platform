"""PCA report projections preserve stored score/loading values and component count."""

from html import escape
from typing import Any

from app.i18n.report_text import ReportLocale, report_text
from app.services.report_contract import (
    ReportBody,
    ReportSection,
    ReportSectionDefinition,
    ReportVariantDefinition,
)
from app.services.stored_report_primitives import (
    report_horizontal_bars,
    report_number,
    report_plot,
    report_table,
)

PCA_REPORT_VARIANTS = (
    ReportVariantDefinition(
        "default",
        (
            ReportSectionDefinition("pca_summary", core=True),
            ReportSectionDefinition("eigenanalysis", core=True),
            ReportSectionDefinition("loadings", core=True),
            *tuple(
                ReportSectionDefinition(key)
                for key in ("scree_plot", "score_plot", "loading_plot", "biplot", "outlier_plot")
            ),
        ),
    ),
)


def principal_components_report_body(
    payload: dict[str, Any], locale: ReportLocale = "en"
) -> ReportBody:
    def text(en: str, ko: str) -> str:
        return report_text(locale, en=en, ko=ko)

    eigen, loadings = payload.get("eigenanalysis"), payload.get("loadings")
    if not isinstance(eigen, list) or not eigen or not isinstance(loadings, list) or not loadings:
        return ReportBody("default", (), "pca_core_not_stored")
    if not isinstance(payload.get("sample"), dict) or not isinstance(
        payload.get("component_selection"), dict
    ):
        return ReportBody("default", (), "pca_core_not_stored")
    sample, selection = payload["sample"], payload["component_selection"]
    sections: list[ReportSection] = []

    def rendered(section_id: str, en: str, ko: str, markup: str) -> None:
        sections.append(ReportSection(section_id, text(en, ko), "rendered", markup))

    rendered(
        "pca_summary",
        "PCA Summary",
        "PCA 요약",
        report_table(
            [text("Setting", "설정"), text("Value", "값")],
            [
                [key, value]
                for key, value in {
                    **sample,
                    **payload.get("preprocessing", {}),
                    **selection,
                }.items()
            ],
        ),
    )
    rendered(
        "eigenanalysis",
        "Eigenanalysis",
        "고유값 분석",
        report_table(
            [
                text("Component", "성분"),
                text("Eigenvalue", "고유값"),
                text("Proportion", "설명 비율"),
                text("Cumulative proportion", "누적 설명 비율"),
                text("Selected", "선택"),
            ],
            [
                [
                    row["component"],
                    row["eigenvalue"],
                    row["proportion"],
                    row["cumulative_proportion"],
                    row.get("selected"),
                ]
                for row in eigen
            ],
        ),
    )
    dimensions = min(len(row["values"]) for row in loadings)
    if dimensions < 1:
        return ReportBody("default", (), "pca_loadings_not_stored")
    rendered(
        "loadings",
        "Stored Loadings",
        "저장된 적재값",
        report_table(
            [
                text("Variable", "변수"),
                *[f"PC{i+1}" for i in range(max(len(row["values"]) for row in loadings))],
            ],
            [[row["display_name"], *row["values"]] for row in loadings],
        ),
    )
    rendered(
        "scree_plot",
        "Scree Plot",
        "스크리 그림",
        report_plot(
            text("Scree Plot", "스크리 그림"),
            text("Principal component", "주성분"),
            text("Eigenvalue", "고유값"),
            [
                (
                    text("Eigenvalue", "고유값"),
                    [
                        (
                            report_number(row["component"]),
                            report_number(row["eigenvalue"]),
                            f"PC{row['component']}; proportion={row['proportion']}; "
                            f"cumulative={row['cumulative_proportion']}; "
                            f"selected={row.get('selected')}",
                        )
                        for row in eigen
                    ],
                )
            ],
            lines=True,
            x_ticks=[(row["component"], str(row["component"])) for row in eigen],
            selected_x=selection.get("selected_components"),
        ),
    )
    plot = payload.get("plot") or {}
    points = plot.get("points")
    if not isinstance(points, list) or not points:
        loading_chart = (
            report_plot(
                text("Loading Plot", "적재 그림"),
                "PC1 loading",
                "PC2 loading",
                [
                    (
                        text("Variables", "변수"),
                        [
                            (
                                report_number(row["values"][0]),
                                report_number(row["values"][1]),
                                row["display_name"],
                            )
                            for row in loadings
                        ],
                    )
                ],
                square=True,
            )
            if dimensions >= 2
            else report_horizontal_bars(
                text("Loading Plot", "적재 그림"),
                "PC1 loading",
                text("Variable", "변수"),
                [(row["display_name"], report_number(row["values"][0])) for row in loadings],
            )
        )
        rendered("loading_plot", "Loading Plot", "적재 그림", loading_chart)
        sections.extend(
            ReportSection(key, text(en, ko), "missing", reason="pca_points_not_stored")
            for key, en, ko in (
                ("score_plot", "Score Plot", "점수 그림"),
                ("biplot", "Biplot", "이중 그림"),
                ("outlier_plot", "Outlier Plot", "이상치 그림"),
            )
        )
        return ReportBody("default", tuple(sections))
    dimensions = min(dimensions, *(len(row["scores"]) for row in points))
    if dimensions < 1:
        return ReportBody("default", (), "pca_score_dimensions_invalid")
    pair = dimensions >= 2

    def score_label(component: int) -> str:
        return (
            f"PC{component} "
            + text("score", "점수")
            + f" ({eigen[component-1]['proportion']*100:.1f}%)"
        )

    score_points = [
        (
            report_number(row["scores"][0]) if pair else report_number(row["source_row_number"]),
            report_number(row["scores"][1 if pair else 0]),
            f"{text('Source row', '원본 행')} {row['source_row_number']}; "
            f"D²={row.get('mahalanobis_distance_squared')}; outlier={row.get('outlier')}",
        )
        for row in points
    ]
    note = (
        "<p>"
        + escape(text("Stored / used points", "저장 / 사용 점 수"))
        + f": {len(points)} / {sample.get('n_used')}; "
        + escape(text("Sampled", "표시 표본화"))
        + f": {plot.get('sampled')}</p>"
    )
    rendered(
        "score_plot",
        "Score Plot",
        "점수 그림",
        report_plot(
            text("Score Plot", "점수 그림"),
            score_label(1) if pair else text("Source row number", "원본 행 번호"),
            score_label(2 if pair else 1),
            [(text("Scores", "점수"), score_points)],
            square=pair,
            marker_shapes=[["square" if row.get("outlier") else "circle" for row in points]],
        )
        + note,
    )
    if pair:
        loading_points = [
            (report_number(row["values"][0]), report_number(row["values"][1]), row["display_name"])
            for row in loadings
        ]
        rendered(
            "loading_plot",
            "Loading Plot",
            "적재 그림",
            report_plot(
                text("Loading Plot", "적재 그림"),
                "PC1 loading",
                "PC2 loading",
                [(text("Variables", "변수"), loading_points)],
                square=True,
            ),
        )
        # This is the existing frontend display scale, not a new SVD biplot estimator.
        display_scale = (
            max(1e-12, *(abs(value) for x, y, _ in score_points for value in (x, y))) * 1.08
        )
        rendered(
            "biplot",
            "Biplot",
            "이중 그림",
            report_plot(
                text("Biplot", "이중 그림"),
                score_label(1),
                score_label(2),
                [(text("Scores", "점수"), score_points)],
                square=True,
                vectors=[
                    (x * display_scale, y * display_scale, label, x, y)
                    for x, y, label in loading_points
                ],
            )
            + "<p>"
            + escape(
                text(
                    "Loading vector display scale (raw loadings are in titles/table)",
                    "적재 벡터 화면 배율 (원래 적재값은 제목과 표에 보존)",
                )
            )
            + f': <span data-loading-display-scale="{display_scale!r}">'
            + f"{display_scale:.10g}</span></p>",
        )
    else:
        rendered(
            "loading_plot",
            "Loading Plot",
            "적재 그림",
            report_horizontal_bars(
                text("Loading Plot", "적재 그림"),
                "PC1 loading",
                text("Variable", "변수"),
                [(row["display_name"], report_number(row["values"][0])) for row in loadings],
            ),
        )
        sections.append(
            ReportSection(
                "biplot",
                text("Biplot", "이중 그림"),
                "not_applicable",
                reason="two_stored_components_required",
            )
        )
    outliers = payload.get("outliers") or {}
    if "reference_value" not in outliers or any(
        row.get("mahalanobis_distance_squared") is None for row in points
    ):
        sections.append(
            ReportSection(
                "outlier_plot",
                text("Outlier Plot", "이상치 그림"),
                "missing",
                reason="outlier_values_not_stored",
            )
        )
    else:
        references = (
            []
            if outliers["reference_value"] is None
            else [
                (
                    "y",
                    report_number(outliers["reference_value"]),
                    text("Stored reference", "저장된 기준값"),
                )
            ]
        )
        rendered(
            "outlier_plot",
            "Outlier Plot",
            "이상치 그림",
            report_plot(
                text("PCA Mahalanobis Distance", "PCA Mahalanobis 거리"),
                text("Source row number", "원본 행 번호"),
                "Mahalanobis distance squared (D²)",
                [
                    (
                        "D²",
                        [
                            (
                                report_number(row["source_row_number"]),
                                report_number(row["mahalanobis_distance_squared"]),
                                str(row["source_row_number"]),
                            )
                            for row in points
                        ],
                    )
                ],
                reference_lines=references,
                marker_shapes=[["square" if row.get("outlier") else "circle" for row in points]],
            )
            + report_table(
                [text("Method", "방법"), "Alpha", text("Degrees of freedom", "자유도")],
                [
                    [
                        outliers.get("method"),
                        outliers.get("alpha"),
                        outliers.get("degrees_of_freedom"),
                    ]
                ],
            ),
        )
    return ReportBody("default", tuple(sections))
