"""Synthetic fractional-design UI journey, shared by source and built releases."""

from __future__ import annotations

import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from playwright.sync_api import Browser, Locator, Page, Response, expect

from app_readiness import diagnosed_page, wait_for_app_ready

ROUTE = "/analysis/doe/doe.factorial_design"
LABELS = {
    "ko": {
        "partial": "2수준 부분요인",
        "add": "요인 추가",
        "generate": "DOE 설계 생성",
        "paste": "반응값 붙여넣기",
        "preview": "미리보기",
        "apply": "반응값 입력표에 적용",
        "save": "반응값 저장",
        "order": "최대 상호작용 차수",
        "run": "효과 및 ANOVA 분석",
        "all_alias": "고차 항으로만 이루어진 Alias 그룹도 표시",
        "estimability": "요청 모형의 추정 가능성",
        "report": "HTML 분석 보고서 생성",
        "download": "다운로드",
        "retained": "모형 유지",
        "pooled": "초기 풀링",
        "alias": "Alias로 독립 추정 불가",
        "expand": "그래프 크게 보기",
    },
    "en": {
        "partial": "2-level partial factor",
        "add": "Add factors",
        "generate": "DOE design creation",
        "paste": "Paste responses",
        "preview": "Preview",
        "apply": "Apply to response draft",
        "save": "Save response value",
        "order": "Maximum interaction order",
        "run": "Effects and ANOVA analysis",
        "all_alias": "Include classes containing only higher-order terms",
        "estimability": "Requested model estimability",
        "report": "Create HTML analysis report",
        "download": "Download",
        "retained": "Retained",
        "pooled": "Initially pooled",
        "alias": "Alias / not independently estimable",
        "expand": "Enlarge plot",
    },
}


class _ReportBody(HTMLParser):
    """Exclude JSON/config appendices when asserting visible report evidence."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden_depth = 0
        self.text: list[str] = []
        self.svg_count = 0
        self.table_count = 0
        self.scripts = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"pre", "script", "style"}:
            self.hidden_depth += 1
        if tag == "script":
            self.scripts += 1
        if not self.hidden_depth:
            self.svg_count += tag == "svg"
            self.table_count += tag == "table"

    def handle_endtag(self, tag: str) -> None:
        if tag in {"pre", "script", "style"}:
            self.hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            self.text.append(data)


def _matches(response: Response, path: str, method: str) -> bool:
    return response.request.method == method and urlsplit(response.url).path == path


def _root(page: Page) -> Locator:
    root = page.locator(
        '.analysis-run-panel[data-analysis-execution="doe.factorial_design"]'
    )
    expect(root).to_be_visible()
    return root


def _open(
    page: Page,
    base: str,
    locale: str,
    design: dict | None = None,
    analysis_id: str | None = None,
) -> Locator:
    query = {}
    if design is not None:
        query = {"design_id": design["design_id"], "design_kind": "two_level"}
        if analysis_id is not None:
            query["analysis_id"] = analysis_id
    page.goto(
        base + ROUTE + ("?" + urlencode(query) if query else ""),
        wait_until="domcontentloaded",
    )
    wait_for_app_ready(page, locale, ROUTE)
    root = _root(page)
    if design is not None:
        expect(root.locator(".fractional-alias-summary")).to_be_visible()
    return root


def _five_factor_design(page: Page, root: Locator, locale: str) -> dict:
    labels = LABELS[locale]
    root.get_by_role("radio", name=labels["partial"], exact=True).check()
    root.locator("#factorial-design-name").fill(f"Synthetic fraction V {locale}")
    for _ in range(3):
        root.get_by_role("button", name=labels["add"], exact=True).click()
    for index, name in enumerate("ABCDE", 1):
        root.get_by_label(f"factor {index} name", exact=True).fill(name)
        root.get_by_label(f"{name} low", exact=True).fill("-1")
        root.get_by_label(f"{name} high", exact=True).fill("1")
        root.get_by_label(f"{name} unit", exact=True).fill("mm")
    root.locator("#factorial-replicates").fill("1")
    root.locator("#factorial-center-points").fill("0")
    advanced = root.locator("details").filter(has=page.locator("#factorial-randomize"))
    advanced.locator("summary").click()
    root.locator("#factorial-randomization-seed").fill("7")
    root.locator("#factorial-block-count").fill("1")
    root.locator("#factorial-randomize").uncheck()
    root.locator("#factorial-fraction-id").select_option("5-factor-half-r5")
    with page.expect_response(
        lambda response: _matches(response, "/api/v1/doe-designs/factorial", "POST")
    ) as pending:
        root.get_by_role("button", name=labels["generate"], exact=True).click()
    assert pending.value.status == 201, pending.value.text()
    design = pending.value.json()
    assert design["run_count"] == len(design["runs"]) == 16
    assert design["fractional"]["generators"] == ["E=ABCD"]
    assert [factor["name"] for factor in design["factors"]] == list("ABCDE")
    assert not any(run["center_point"] for run in design["runs"])
    return design


def _aliases(root: Locator, locale: str, design: dict) -> None:
    summary = root.locator(".fractional-alias-summary")
    metadata = design["fractional"]
    expect(summary.locator(".doe-alias-names tbody tr")).to_have_count(
        len(design["factors"])
    )
    expected = [
        " = ".join(
            ("-" if term["sign"] < 0 else "") + term["compact_label"] for term in terms
        )
        for terms in metadata["alias_classes"]
    ]
    compact = [
        label
        for label, terms in zip(expected, metadata["alias_classes"], strict=True)
        if any(term["order"] <= 2 for term in terms)
    ]
    expect(summary.locator("tbody td > code")).to_have_text(compact)
    toggle = summary.get_by_label(LABELS[locale]["all_alias"], exact=True)
    expect(toggle).not_to_be_checked()
    toggle.check()
    expect(toggle).to_be_checked()
    expect(summary.locator("tbody td > code")).to_have_text(expected)
    identity = "I = " + "".join(chr(65 + i) for i in range(len(design["factors"])))
    assert identity in expected
    full_names = summary.locator("tbody td details").first
    full_names.locator("summary").click()
    expected_full = " = ".join(
        ("-" if term["sign"] < 0 else "") + term["full_label"]
        for term in metadata["alias_classes"][0]
    )
    expect(full_names.locator("p")).to_have_text(expected_full)
    toggle.uncheck()
    expect(summary.locator("tbody td > code")).to_have_text(compact)


def _save_responses(
    page: Page, base: str, root: Locator, locale: str, design: dict
) -> list[dict]:
    labels = LABELS[locale]
    values = [
        {
            "run_order": run["run_order"],
            "value": 10
            + 2 * run["coded_levels"]["A"]
            - run["coded_levels"]["B"]
            + 0.4 * run["coded_levels"]["A"] * run["coded_levels"]["B"]
            + (run["run_order"] * 17 % 11) * 0.023,
        }
        for run in design["runs"]
    ]
    path = f"/api/v1/doe-designs/{design['design_id']}/responses"
    root.get_by_role("button", name=labels["paste"], exact=True).click()
    paste = root.locator(".doe-response-paste")
    paste.locator("textarea").fill("\n".join(str(row["value"]) for row in values))
    paste.get_by_role("button", name=labels["preview"], exact=True).click()
    expect(paste.locator("tbody tr")).to_have_count(len(values))
    paste.get_by_role("button", name=labels["apply"], exact=True).click()
    for row in values:
        expect(
            root.get_by_label(f"run {row['run_order']} response", exact=True)
        ).to_have_value(str(row["value"]))
    draft = page.request.get(base + path)
    assert draft.status == 200, draft.text()
    assert (
        draft.json()["responses"] == []
    ), "Paste preview must not persist response values"
    with page.expect_response(
        lambda response: _matches(response, path, "PUT")
    ) as pending:
        root.get_by_role("button", name=labels["save"], exact=True).click()
    assert pending.value.status == 200, pending.value.text()
    assert pending.value.request.post_data_json["values"] == values
    saved = page.request.get(base + path)
    assert saved.status == 200, saved.text()
    stored = saved.json()["responses"][0]["values"]
    assert {row["run_order"]: row["value"] for row in stored} == {
        row["run_order"]: row["value"] for row in values
    }
    return values


def _preflight(
    page: Page, root: Locator, locale: str, design: dict, method: str
) -> dict:
    path = f"/api/v1/doe-designs/{design['design_id']}/analysis-term-preflight"
    order = root.get_by_label(LABELS[locale]["order"], exact=True)
    selector = root.locator(".doe-model-selection select")
    # Force a real input transition, not an API-only preflight or a cached UI assertion.
    order.select_option("1")
    selector.select_option(method)
    with page.expect_response(
        lambda response: _matches(response, path, "POST")
        and response.request.post_data_json["max_interaction_order"] == 2
        and response.request.post_data_json["model_selection"]["method"] == method
    ) as pending:
        order.select_option("2")
    assert pending.value.status == 200, pending.value.text()
    plan = pending.value.json()["estimability"]
    metadata = root.locator(".doe-term-selection").get_by_label(
        LABELS[locale]["estimability"], exact=True
    )
    expect(metadata.locator("strong")).to_have_text(
        [
            str(plan["requested_parameter_count"]),
            str(plan["rank"]),
            str(plan["expected_residual_df"]),
            str(len(plan["exclusions"])),
        ]
    )
    expect(
        root.get_by_role("button", name=LABELS[locale]["run"], exact=True)
    ).to_be_enabled()
    return plan


def _analyze(
    page: Page, root: Locator, locale: str, design: dict, method: str, plan: dict
) -> dict:
    path = f"/api/v1/doe-designs/{design['design_id']}/analyses"
    with page.expect_response(
        lambda response: _matches(response, path, "POST")
    ) as pending:
        root.get_by_role("button", name=LABELS[locale]["run"], exact=True).click()
    assert pending.value.status == 201, pending.value.text()
    request = pending.value.request.post_data_json
    assert request["max_interaction_order"] == 2
    assert request["model_selection"]["method"] == method
    analysis = pending.value.json()
    assert analysis["design_id"] == design["design_id"]
    assert analysis["result"]["estimability"] == plan
    assert analysis["result"]["model_policy"]["effective_interaction_order"] == 2
    expect(root.locator(".factorial-coded-coefficients")).to_be_visible()
    expect(root.locator(".fractional-estimability")).to_be_visible()
    return analysis


def _saturated(root: Locator, analysis: dict, parameter_count: int) -> None:
    result = analysis["result"]
    assert (
        result["sample"]["parameter_count"]
        == result["sample"]["rank"]
        == parameter_count
    )
    assert result["sample"]["df_residual"] == 0
    assert not result["model_selection"]["removed_term_ids"]
    assert not result["model_selection"]["pooled_term_ids"]
    assert all(term["p_value"] is None for term in result["terms"])
    coefficients = result["final_model"]["coded_coefficients"]
    assert all(term["p_value"] is None for term in coefficients)
    rows = root.locator(".factorial-coded-coefficients tbody tr")
    expect(rows).to_have_count(len(coefficients))
    for row in rows.all():
        expect(row.locator("td").nth(5)).to_have_text("-")


def _backward(root: Locator, locale: str, analysis: dict) -> None:
    result = analysis["result"]
    selection = result["model_selection"]
    assert selection["initial_model_saturated"]
    assert selection["initial_residual_df"] == 0
    assert selection["target_pool_count"] == len(selection["pooled_term_ids"]) == 4
    pooling_steps = [
        step for step in selection["steps"] if step["phase"] == "initial_pooling"
    ]
    assert pooling_steps
    assert all(step["removal_p_value"] is None for step in pooling_steps)
    assert result["sample"]["df_residual"] > 0
    expect(root.locator(".doe-step-matrix")).to_be_visible()
    plots = root.locator(".factorial-plots")
    expect(plots.locator(".doe-compact-plot")).to_have_count(15)
    pooled = plots.locator('.doe-compact-plot[data-term-status="pooled"]')
    expect(pooled).to_have_count(4)
    for card in pooled.all():
        expect(card.locator(".doe-plot-status")).to_contain_text(
            LABELS[locale]["pooled"]
        )
    retained = plots.locator('.doe-compact-plot[data-term-status="retained"]')
    expect(retained).to_have_count(len(selection["final_term_ids"]))
    expect(retained.first.locator(".doe-plot-status")).to_contain_text(
        LABELS[locale]["retained"]
    )
    card = plots.locator(".doe-compact-plot").first
    button = card.get_by_role("button", name=LABELS[locale]["expand"], exact=True)
    button.click()
    expect(card).to_have_attribute("data-expanded", "true")
    expect(card.get_by_role("button")).to_have_attribute("aria-expanded", "true")
    card.get_by_role("button").click()
    expect(card).to_have_attribute("data-expanded", "false")


def _report_and_restore(
    page: Page,
    base: str,
    root: Locator,
    locale: str,
    design: dict,
    analysis: dict,
    output: Path,
) -> dict:
    path = (
        f"/api/v1/doe-designs/{design['design_id']}/analyses/{analysis['analysis_id']}"
    )
    original = page.request.get(base + path)
    assert original.status == 200, original.text()
    original_bytes = original.body()
    assert original.json() == analysis
    analyses_created: list[str] = []

    def watch(request) -> None:
        if request.method == "POST" and urlsplit(request.url).path.endswith(
            "/analyses"
        ):
            analyses_created.append(urlsplit(request.url).path)

    page.on("request", watch)
    try:
        assets = root.locator(".factorial-analysis-assets")
        with page.expect_response(
            lambda response: _matches(response, path + "/exports/html", "POST")
        ) as pending:
            assets.get_by_role(
                "button", name=LABELS[locale]["report"], exact=True
            ).click()
        assert pending.value.status == 201, pending.value.text()
        asset = pending.value.json()
        assert asset["kind"] == "html_report" and asset["locale"] == locale
        assert asset["analysis_id"] == analysis["analysis_id"]
        row = assets.locator("tbody tr").filter(has_text="HTML").first
        expect(row).to_be_visible()
        with page.expect_download() as pending_download:
            row.get_by_role(
                "button", name=LABELS[locale]["download"], exact=True
            ).click()
        report_path = output / f"fraction-{len(design['factors'])}-{locale}.html"
        pending_download.value.save_as(report_path)
        report_bytes = report_path.read_bytes()
        digest = hashlib.sha256(report_bytes).hexdigest()
        assert digest == asset["sha256"]
        assert len(report_bytes) == asset["size_bytes"]
        html = report_bytes.decode("utf-8")
        body = _ReportBody()
        body.feed(html)
        visible = " ".join(" ".join(body.text).split())
        assert body.svg_count > 0 and body.table_count > 0 and body.scripts == 0
        assert analysis["analysis_id"] in html
        assert design["name"] in visible and analysis["response_name"] in visible
        assert (
            "I = " + "".join(chr(65 + i) for i in range(len(design["factors"])))
            in visible
        )
        if locale == "en":
            assert "Independent representative basis" in visible
            if analysis["result"]["model_selection"]["pooled_term_ids"]:
                assert "Initial pooling" in visible
        offline = page.context.new_page()
        external_requests: list[str] = []

        def block_external(route) -> None:
            external_requests.append(route.request.resource_type)
            route.abort("blockedbyclient")

        try:
            offline.route("http://**/*", block_external)
            offline.route("https://**/*", block_external)
            offline.goto(report_path.resolve().as_uri(), wait_until="load")
            expect(
                offline.get_by_role("cell", name=design["name"], exact=True)
            ).to_be_visible()
            expect(offline.locator("svg").first).to_be_visible()
            assert (
                not external_requests
            ), "Standalone report requested external resources"
            offline.screenshot(
                path=str(output / f"report-{len(design['factors'])}.png")
            )
        finally:
            offline.close()
        restored_root = _open(page, base, locale, design, analysis["analysis_id"])
        expect(restored_root.locator(".factorial-coded-coefficients")).to_be_visible()
        expect(
            restored_root.locator(".factorial-analysis-assets tbody tr")
        ).to_contain_text("HTML")
        after = page.request.get(base + path)
        assert after.status == 200 and after.body() == original_bytes
        restored_design = page.request.get(
            base + f"/api/v1/doe-designs/{design['design_id']}"
        )
        assert restored_design.status == 200
        assert restored_design.json()["design_sha256"] == design["design_sha256"]
        assert (
            not analyses_created
        ), "Report/restore unexpectedly executed another analysis"
        restored_root.locator(".fractional-estimability").screenshot(
            path=str(output / f"restored-{len(design['factors'])}.png")
        )
        return {
            "analysis_id": analysis["analysis_id"],
            "analysis_sha256": hashlib.sha256(original_bytes).hexdigest(),
            "asset_id": asset["asset_id"],
            "report_sha256": digest,
            "report_svg_count": body.svg_count,
            "source_unchanged": True,
            "restore_without_analysis": True,
            "standalone_network_blocked": True,
        }
    finally:
        page.remove_listener("request", watch)


def verify_fractional_completion(browser: Browser, base: str, output: Path) -> dict:
    receipt: dict = {
        "schema_version": 1,
        "status": "succeeded",
        "fixture": "synthetic",
        "locales": {},
    }
    for locale in ("ko", "en"):
        directory = output / f"fractional-completion-{locale}"
        with diagnosed_page(browser, output, directory.name, locale=locale) as page:
            page.set_viewport_size({"width": 1440, "height": 1000})
            root = _open(page, base, locale)
            design = _five_factor_design(page, root, locale)
            _aliases(root, locale, design)
            root.locator(".fractional-alias-summary").screenshot(
                path=str(directory / "five-factor-alias.png")
            )
            _save_responses(page, base, root, locale, design)
            plan = _preflight(page, root, locale, design, "none")
            assert plan["requested_parameter_count"] == plan["rank"] == 16
            assert plan["expected_residual_df"] == 0 and not plan["exclusions"]
            full = _analyze(page, root, locale, design, "none", plan)
            _saturated(root, full, 16)
            expect(
                root.locator(
                    '.factorial-plots .doe-compact-plot[data-term-status="retained"]'
                )
            ).to_have_count(15)
            root.locator(".factorial-coded-coefficients").screenshot(
                path=str(directory / "five-factor-saturated.png")
            )
            backward_plan = _preflight(
                page, root, locale, design, "backward_elimination"
            )
            assert (
                backward_plan == plan
            ), "Selection must not alter the requested design rank"
            selected = _analyze(
                page, root, locale, design, "backward_elimination", plan
            )
            _backward(root, locale, selected)
            root.locator(".factorial-plots").screenshot(
                path=str(directory / "five-factor-status-plots.png")
            )
            report = _report_and_restore(
                page, base, root, locale, design, selected, directory
            )
            _backward(_root(page), locale, selected)

            created = page.request.post(
                base + "/api/v1/doe-designs/factorial",
                headers={"Origin": base},
                data={
                    "name": f"Synthetic fraction IV {locale}",
                    "design_type": "two_level_fractional",
                    "fraction_id": "4-factor-half-r4",
                    "factors": [
                        {"name": name, "low": -1, "high": 1, "unit": "mm"}
                        for name in "ABCD"
                    ],
                    "replicates": 1,
                    "center_points": 0,
                    "randomize": False,
                    "randomization_seed": 7,
                    "block_count": 1,
                },
            )
            assert created.status == 201, created.text()
            four = created.json()
            assert four["run_count"] == 8 and four["fractional"]["generators"] == [
                "D=ABC"
            ]
            root = _open(page, base, locale, four)
            _aliases(root, locale, four)
            codes = root.locator(".fractional-alias-summary tbody td > code")
            for pair in ("AB = CD", "AC = BD", "AD = BC"):
                expect(codes.filter(has_text=pair)).to_have_count(1)
            _save_responses(page, base, root, locale, four)
            four_plan = _preflight(page, root, locale, four, "none")
            assert four_plan["requested_parameter_count"] == 11
            assert four_plan["rank"] == four_plan["estimable_parameter_count"] == 8
            assert four_plan["expected_residual_df"] == 0
            exclusions = {item["term_id"]: item for item in four_plan["exclusions"]}
            assert {
                key: value["representative_term_id"]
                for key, value in exclusions.items()
            } == {
                "factor_3:factor_4": "factor_1:factor_2",
                "factor_2:factor_4": "factor_1:factor_3",
                "factor_2:factor_3": "factor_1:factor_4",
            }
            assert all(
                row["reason"] == "complete_alias" and row["sign"] == 1
                for row in exclusions.values()
            )
            four_analysis = _analyze(page, root, locale, four, "none", four_plan)
            _saturated(root, four_analysis, 8)
            alias_cards = root.locator(
                '.factorial-plots .doe-compact-plot[data-term-status="alias_nonestimable"]'
            )
            expect(alias_cards).to_have_count(3)
            for card in alias_cards.all():
                expect(card.locator(".doe-plot-status")).to_contain_text(
                    LABELS[locale]["alias"]
                )
            expect(
                root.locator(
                    '.factorial-plots .doe-compact-plot[data-term-status="backward_removed"]'
                )
            ).to_have_count(0)
            root.locator(".factorial-plots").screenshot(
                path=str(directory / "four-factor-alias-status.png")
            )
            four_report = _report_and_restore(
                page, base, root, locale, four, four_analysis, directory
            )
            receipt["locales"][locale] = {
                "five_factor_design_id": design["design_id"],
                "five_factor_design_sha256": design["design_sha256"],
                "saturated_analysis_id": full["analysis_id"],
                "preflight_rank": plan["rank"],
                "saturated_residual_df": full["result"]["sample"]["df_residual"],
                "pooled_term_ids": selected["result"]["model_selection"][
                    "pooled_term_ids"
                ],
                "backward": report,
                "four_factor_design_id": four["design_id"],
                "four_factor_design_sha256": four["design_sha256"],
                "alias_representatives": exclusions,
                "four_factor": four_report,
            }
            (directory / "fractional-receipt.json").write_text(
                json.dumps(receipt["locales"][locale], ensure_ascii=False, indent=2)
                + "\n",
                encoding="utf-8",
            )
    return receipt
