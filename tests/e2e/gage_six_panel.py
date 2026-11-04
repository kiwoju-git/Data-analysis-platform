"""Synthetic saved Gage six-panel values through real ingestion and analysis forms.

The hand fixture is independent of the production plotting helper. Legacy UI
projection is explicitly transport-injected; real legacy file/hash compatibility
is separately exercised by the API tests. Offline report checks do not claim that
the application server process has stopped.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Browser, Locator, Page, Playwright, expect

from app_readiness import (
    SyntheticPageDiagnostics,
    diagnosed_page,
    wait_for_app_ready,
    wait_for_layout_settled,
)
from gage_followup import _restore_result
from pilot_edge_cases import (
    INITIAL_LOCALE,
    _api,
    _filter,
    _locale,
    _open,
    _report,
    digest,
    ingest,
)
from viewport_evidence import capture_viewport_evidence

ROUTE = "/analysis/quality/quality.gage_rr"
MEASUREMENT = "측정값 한국어 유지"
KINDS = (
    "components",
    "response_by_part",
    "dispersion",
    "response_by_operator",
    "xbar",
    "interaction",
)
REPORT_SECTIONS = (
    "gage_components_plot",
    "gage_response_by_part",
    "gage_dispersion",
    "gage_response_by_operator",
    "gage_xbar",
    "gage_interaction",
)


def _fixture(parts: int = 10, operators: int = 3) -> str:
    return f"part,operator,{MEASUREMENT}\n" + "".join(
        f"{i + 1},O{operator:02},{50 + 2*i + .2*(operator-1) + error:.10g}\n"
        for i in range(parts)
        for operator in range(operators)
        for error in (-0.1, 0.1)
    )


def _configure(page: Page, base: str, version: dict, policy: str) -> Locator:
    _open(page, base, ROUTE, version)
    columns = {
        column["display_name"]: column["column_id"] for column in version["columns"]
    }
    panel = page.locator('[data-analysis-execution="quality.gage_rr"]')
    selectors = panel.locator(".option-grid").first.locator("select")
    for index, name in enumerate((MEASUREMENT, "part", "operator")):
        selectors.nth(index).select_option(columns[name])
    expect(panel.locator('[data-gage-control="replicate-mode"]')).to_have_value(
        "infer_from_rows"
    )
    panel.locator('[data-gage-control="interaction-policy"]').select_option(policy)
    return panel


def _run(page: Page, panel: Locator) -> dict:
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and urlsplit(response.url).path == "/api/v1/analysis-runs"
    ) as submitted:
        panel.get_by_role("button", name="Gage R&R 계산", exact=True).click()
    response = submitted.value
    assert response.status == 201, response.text()
    envelope = response.json()
    assert envelope["result"]["schema_version"] == 4
    expect(panel.locator("[data-gage-six-panel]")).to_be_visible()
    return envelope


def _assert_close(actual: float, expected: float) -> None:
    assert math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10), (
        actual,
        expected,
    )


def _points(slot: Locator) -> list[dict]:
    return slot.locator("svg.chart-frame-svg [data-point-id]").evaluate_all(
        """nodes => nodes.map(node => ({id: node.dataset.pointId,
            x: Number(node.dataset.x), y: Number(node.dataset.y)}))"""
    )


def _graph_coordinates(charts: Locator) -> list[dict]:
    return charts.locator("svg.chart-frame-svg").evaluate_all("""nodes => nodes.map(svg => ({
        chart: svg.closest('[data-chart-id]').dataset.chartId,
        points: [...svg.querySelectorAll('[data-point-id]')].map(node => ({
            id: node.dataset.pointId, x: node.dataset.x, y: node.dataset.y})),
        bars: [...svg.querySelectorAll('[data-category][data-series][data-value]')].map(
            node => ({category: node.dataset.category, series: node.dataset.series,
                value: node.dataset.value})),
        boxes: [...svg.querySelectorAll('[data-box-id]')].map(node => ({
            id: node.dataset.boxId, q1: node.dataset.q1, median: node.dataset.median,
            q3: node.dataset.q3, mean: node.dataset.mean,
            low: node.dataset.lowerWhisker, high: node.dataset.upperWhisker}))
    }))""")


def _assert_six_values(charts: Locator, result: dict) -> dict:
    bundle = result["plot_bundle"]
    expected_ids = [str(index) for index in range(1, 11)]
    assert bundle["schema_version"] == 2
    assert [part["part_id"] for part in bundle["parts"]] == expected_ids
    for index, part in enumerate(bundle["parts"]):
        _assert_close(part["mean"], 50 + 2 * index)
    identities = charts.locator('[data-gage-part-identities="original"]')
    expect(identities).to_have_count(1)
    if identities.get_attribute("open") is None:
        identities.locator("summary").click()
    table = charts.locator("[data-gage-part-id-table]")
    expect(table).to_be_visible()
    expect(table.locator("td[data-gage-part-id]")).to_have_text(expected_ids)
    expect(table.locator('[data-gage-part-index="9"]')).to_contain_text("68")
    for kind in ("response_by_part", "interaction"):
        ticks = charts.locator(
            f'[data-gage-chart-kind="{kind}"] .chart-axes .chart-tick-label[text-anchor="middle"]'
        )
        expect(ticks).to_have_text(expected_ids)
    for kind in KINDS:
        slot = charts.locator(f'[data-gage-chart-kind="{kind}"]')
        expect(slot).to_have_count(1)
        expect(slot.locator("svg.chart-frame-svg")).to_have_count(1)
    bars = charts.locator(
        '[data-gage-chart-kind="components"] [data-category][data-series][data-value]'
    )
    expect(bars).to_have_count(8)
    visible_values = sorted(
        float(value)
        for value in bars.evaluate_all("nodes => nodes.map(n => n.dataset.value)")
    )
    stored_values = sorted(
        item[metric]
        for item in bundle["components"]["items"]
        for metric in ("percent_contribution", "percent_study_variation")
    )
    for actual, expected in zip(visible_values, stored_values, strict=True):
        _assert_close(actual, expected)
    for bar in bars.evaluate_all("nodes => nodes.map(n => n.dataset)"):
        component = bundle["components"]["items"][int(bar["category"])]
        metric = (
            "percent_contribution"
            if int(bar["series"]) == 0
            else "percent_study_variation"
        )
        _assert_close(float(bar["value"]), component[metric])
    bar_geometry = bars.evaluate_all("""nodes => nodes.map(node => ({
        value: Number(node.dataset.value), height: Number(node.querySelector('rect').getAttribute('height')),
        width: Number(node.querySelector('rect').getAttribute('width'))
    }))""")
    assert all(
        item["width"] > 0 and (item["height"] > 0) == (item["value"] > 0)
        for item in bar_geometry
    )
    for kind, field in (
        ("dispersion", "value"),
        ("xbar", "value"),
        ("interaction", "mean"),
    ):
        slot = charts.locator(f'[data-gage-chart-kind="{kind}"]')
        points = _points(slot)
        assert len(points) == 30, (kind, points)
        expected = sorted(point[field] for point in bundle[kind]["points"])
        for actual, value in zip(
            sorted(point["y"] for point in points), expected, strict=True
        ):
            _assert_close(actual, value)
        paths = slot.locator("svg.chart-frame-svg path[data-series-id]")
        expect(paths).to_have_count(3)
        series = paths.evaluate_all(
            "nodes => nodes.map(node => ({id: node.dataset.seriesId, d: node.getAttribute('d')}))"
        )
        assert {item["id"] for item in series} == {
            "operator:0",
            "operator:1",
            "operator:2",
        }
        assert all(
            item["d"].count("M") == 1 and item["d"].count("L") == 9 for item in series
        ), series
        markers = slot.locator("svg.chart-frame-svg [data-point-id]").evaluate_all("""nodes => nodes.map(node => ({
            id: node.dataset.pointId, x: node.getBBox().x + node.getBBox().width / 2,
            y: node.getBBox().y + node.getBBox().height / 2
        }))""")
        marker_positions = {item["id"]: item for item in markers}
        for item in series:
            operator = int(item["id"].split(":")[1])
            vertices = re.findall(r"[ML]\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)", item["d"])
            assert len(vertices) == 10
            for part, (x, y) in enumerate(vertices):
                marker = marker_positions[f"{kind}:{operator}:{part}"]
                assert math.isclose(float(x), marker["x"], abs_tol=1e-4)
                assert math.isclose(float(y), marker["y"], abs_tol=1e-4)
        if kind != "interaction":
            references = slot.locator("svg.chart-frame-svg line[data-reference-label]")
            expect(references).to_have_count(3)
            lines = references.evaluate_all("""nodes => nodes.map(node => ({
                label: node.dataset.referenceLabel, value: Number(node.dataset.y1),
                end: Number(node.dataset.y2), pixel: Number(node.getAttribute('y1'))
            }))""")
            for line, key in zip(
                lines, ("lower_limit", "center", "upper_limit"), strict=True
            ):
                _assert_close(line["value"], bundle[kind][key])
                _assert_close(line["end"], line["value"])
                expect(slot.locator(".chart-series-legend")).to_contain_text(
                    line["label"]
                )
            lower, _, upper = lines
            assert upper["pixel"] < lower["pixel"], "SVG Y orientation must be inverted"
            scale = (upper["pixel"] - lower["pixel"]) / (
                upper["value"] - lower["value"]
            )
            plotted = slot.locator("svg.chart-frame-svg [data-point-id]").evaluate_all("""nodes => nodes.map(node => ({
                value: Number(node.dataset.y), pixel: node.getBBox().y + node.getBBox().height / 2
            }))""")
            for item in plotted:
                expected_pixel = (
                    lower["pixel"] + (item["value"] - lower["value"]) * scale
                )
                assert math.isclose(item["pixel"], expected_pixel, abs_tol=1e-4)
    raw = _points(charts.locator('[data-gage-chart-kind="response_by_part"]'))
    assert len(raw) == 70
    raw_by_id = {point["id"]: point for point in raw}
    assert len(raw_by_id) == len(raw)
    # This plot also contains part means. Every original source row stays identifiable.
    for point in bundle["response_by_part"]["points"]:
        _assert_close(
            raw_by_id[f"raw:{point['source_row_number']}"]["y"], point["value"]
        )
    for part in bundle["parts"]:
        _assert_close(raw_by_id[f"part-mean:{part['part_index']}"]["y"], part["mean"])
    boxes = charts.locator(
        '[data-gage-chart-kind="response_by_operator"] [data-box-id]'
    )
    expect(boxes).to_have_count(3)
    actual_boxes = boxes.evaluate_all("nodes => nodes.map(n => n.dataset)")
    for actual, expected in zip(
        actual_boxes, bundle["response_by_operator"]["boxes"], strict=True
    ):
        for attr, key in (
            ("q1", "q1"),
            ("median", "median"),
            ("q3", "q3"),
            ("mean", "mean"),
            ("lowerWhisker", "lower_whisker"),
            ("upperWhisker", "upper_whisker"),
        ):
            _assert_close(float(actual[attr]), expected[key])
        assert expected["n"] == 20
        operator = expected["operator_index"]
        for attr, value in (
            ("q1", 53.85),
            ("median", 58.8),
            ("q3", 63.75),
            ("mean", 58.8),
            ("lowerWhisker", 49.7),
            ("upperWhisker", 67.9),
        ):
            _assert_close(float(actual[attr]), value + 0.2 * operator)
    box_geometry = boxes.evaluate_all("""nodes => nodes.map(node => ({
        height: Number(node.querySelector('rect:not(.chart-summary-hit)').getAttribute('height')),
        width: Number(node.querySelector('rect:not(.chart-summary-hit)').getAttribute('width')),
        median: Number(node.querySelector('.chart-box-median').getAttribute('y1')),
        top: Number(node.querySelector('rect:not(.chart-summary-hit)').getAttribute('y'))
    }))""")
    assert all(
        item["height"] > 0
        and item["width"] > 0
        and item["top"] < item["median"] < item["top"] + item["height"]
        for item in box_geometry
    )
    _assert_close(bundle["dispersion"]["center"], 0.2)
    _assert_close(bundle["dispersion"]["upper_limit"], 0.6534)
    _assert_close(bundle["xbar"]["center"], 59)
    half_width = (
        3 * math.sqrt(0.0125 / 2) if result["interaction_selection"]["pooled"] else 0.3
    )
    _assert_close(bundle["xbar"]["lower_limit"], 59 - half_width)
    _assert_close(bundle["xbar"]["upper_limit"], 59 + half_width)
    return {
        "raw_points": len(raw),
        "raw_measurement_points": 60,
        "component_bars": 8,
        "operator_paths_per_chart": 3,
        "numeric_svg_checked": True,
        "box_n": 20,
        "dispersion_center": 0.2,
        "dispersion_ucl": 0.6534,
        "xbar_center": 59,
        "xbar_half_width": half_width,
        "part_ids": expected_ids,
        "part_means": [50 + 2 * index for index in range(10)],
        "part_axis_labels_checked": True,
    }


def _interaction(page: Page, charts: Locator) -> None:
    chart = charts.locator('[data-gage-chart-kind="response_by_part"]')
    items = chart.locator("svg.chart-frame-svg [data-point-id]")
    assert (
        items.evaluate_all("nodes => nodes.filter(n => n.tabIndex === 0).length") == 1
    )
    first = chart.locator('[data-point-id="raw:1"]')
    second = chart.locator('[data-point-id="raw:2"]')
    first.hover()
    expect(page.get_by_role("tooltip")).to_be_visible()
    expect(page.get_by_role("tooltip")).to_contain_text("1")
    first.click()
    expect(first).to_have_attribute("data-selected", "true")
    second.hover()
    expect(first).to_have_attribute("data-selected", "true")
    expect(second).to_have_attribute("data-selected", "false")
    first.focus()
    first.press("Escape")
    expect(first).to_have_attribute("data-selected", "false")
    expect(first).to_be_focused()
    page.mouse.move(0, 0)
    expect(page.get_by_role("tooltip")).to_have_count(0)
    first.press("ArrowRight")
    assert (
        items.evaluate_all("nodes => nodes.filter(n => n.tabIndex === 0).length") == 1
    )
    page.keyboard.press("Home")
    mean = chart.locator('[data-point-id="part-mean:0"]')
    expect(mean).to_be_focused()
    page.keyboard.press("Enter")
    expect(mean).to_have_attribute("data-selected", "true")
    expect(page.get_by_role("tooltip")).to_be_visible()
    page.keyboard.press("Escape")
    expected_ids = set(items.evaluate_all("nodes => nodes.map(n => n.dataset.pointId)"))
    visited = set()
    for _ in range(len(expected_ids)):
        visited.add(page.evaluate("document.activeElement.dataset.pointId"))
        page.keyboard.press("ArrowRight")
    assert visited == expected_ids, "Keyboard must reach every raw and mean marker"
    page.keyboard.press("Tab")
    assert not chart.locator("svg.chart-frame-svg [data-point-id]:focus").count()
    last_part = chart.locator('[data-point-id="part-mean:9"]')
    last_part.focus()
    last_part.press("Enter")
    expect(page.get_by_role("tooltip")).to_contain_text("10")
    expect(page.get_by_role("tooltip")).to_contain_text("68")
    last_part.press("Escape")


def _layout(page: Page, charts: Locator) -> dict:
    wait_for_layout_settled(page)
    geometry = charts.evaluate("""root => {
        const rect = element => { const r = element.getBoundingClientRect();
            return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height}; };
        const cards = [...root.querySelectorAll('[data-gage-chart-kind]')].map(card => ({
            kind:card.dataset.gageChartKind, box:rect(card),
            svg:[...card.querySelectorAll('svg.chart-frame-svg')].map(rect)
        }));
        return {viewport:innerWidth, scrollWidth:document.documentElement.scrollWidth,
            container:rect(root), cards};
    }""")
    assert geometry["scrollWidth"] <= geometry["viewport"] + 1, geometry
    assert len(geometry["cards"]) == 6
    for card in geometry["cards"]:
        for svg in card["svg"]:
            assert svg["width"] > 0 and svg["height"] > 0
            assert svg["left"] >= card["box"]["left"] - 1
            assert svg["right"] <= card["box"]["right"] + 1
    for index, card in enumerate(geometry["cards"]):
        for other in geometry["cards"][index + 1 :]:
            a, b = card["box"], other["box"]
            overlap_x = min(a["right"], b["right"]) - max(a["left"], b["left"])
            overlap_y = min(a["bottom"], b["bottom"]) - max(a["top"], b["top"])
            assert overlap_x <= 1 or overlap_y <= 1, (card, other)
    row = geometry["cards"][0]["box"]["top"]
    geometry["columns"] = sum(
        abs(card["box"]["top"] - row) < 2 for card in geometry["cards"]
    )
    assert geometry["columns"] == (
        2 if geometry["container"]["width"] >= 840 else 1
    ), geometry
    return geometry


def _offline_reports(browser: Browser, artifacts: list[dict], output: Path) -> None:
    context = browser.new_context(offline=True)
    try:
        page = context.new_page()
        for artifact in artifacts:
            verify_gage_report_html(page, artifact, output)
    finally:
        context.close()


def verify_gage_report_html(page: Page, artifact: dict, output: Path) -> dict:
    """Reusable after actual release-server shutdown, using only downloaded bytes."""
    output.mkdir(parents=True, exist_ok=True)
    path = Path(artifact["path"])
    descriptor = artifact["descriptor"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == descriptor["sha256"]
    page.goto(path.resolve().as_uri(), wait_until="domcontentloaded")
    expect(page.locator('[data-report-level="full"]')).to_be_visible()
    sections = []
    for section in REPORT_SECTIONS:
        panel = page.locator(f'[data-report-section="{section}"]')
        expect(panel).to_be_visible()
        assert panel.locator("svg").count() >= 1
        sections.append({"section": section, "svg_count": panel.locator("svg").count()})
    part_ids = [str(index) for index in range(1, 11)]
    for section in ("gage_response_by_part", "gage_interaction"):
        panel = page.locator(f'[data-report-section="{section}"]')
        ticks = panel.locator("text[data-gage-part-id]")
        assert ticks.evaluate_all("nodes => nodes.map(n => n.dataset.gagePartId)") == part_ids
        assert ticks.evaluate_all(
            "nodes => nodes.map(n => [...n.querySelectorAll('tspan')].map(c => c.textContent).join(''))"
        ) == part_ids
    summary = page.locator('[data-gage-part-summary="true"] tbody tr')
    expect(summary).to_have_count(10)
    expect(summary.locator("td:first-child")).to_have_text(part_ids)
    for index in range(10):
        _assert_close(float(summary.nth(index).locator("td").nth(2).inner_text()), 50 + 2 * index)
    tenth = page.locator(
        '[data-report-section="gage_response_by_part"] [data-role="part_mean"][data-gage-part-id="10"]'
    )
    expect(tenth).to_have_count(1)
    _assert_close(float(tenth.get_attribute("data-y")), 68)
    raw = page.locator(
        '[data-report-section="gage_response_by_part"] [data-role="measurement"]'
    )
    expect(raw).to_have_count(60)
    for value in raw.evaluate_all("nodes => nodes.map(n => Number(n.dataset.y))"):
        assert math.isfinite(value)
    ucl = page.locator(
        '[data-report-section="gage_dispersion"] [data-reference="upper_limit"]'
    )
    assert ucl.count() > 0
    for value in ucl.evaluate_all("nodes => nodes.map(n => Number(n.dataset.value))"):
        _assert_close(value, 0.6534)
    expect(page.locator("body")).to_contain_text(MEASUREMENT)
    assert page.locator("script, link[href], img[src]").count() == 0
    page.screenshot(
        path=str(
            output / f"offline-{artifact['locale']}-{descriptor['export_id']}.png"
        ),
        full_page=True,
    )
    return {
        "export_id": descriptor["export_id"],
        "locale": artifact["locale"],
        "sha256": descriptor["sha256"],
        "sections": sections,
        "raw_point_count": 60,
        "part_ids": part_ids,
        "part_axis_labels_checked": True,
        "dispersion_ucl": 0.6534,
    }


def verify_gage_six_panel_resume(
    page: Page, base: str, output: Path, original: dict
) -> dict:
    """Exact saved source and original report bytes from a restarted installation."""
    output.mkdir(parents=True, exist_ok=True)
    receipt: dict = {
        "status": "running",
        "phase": "resume",
        "analyses": [],
        "reports": [],
    }
    writes: list[str] = []

    def observe(request):
        path = urlsplit(request.url).path
        if request.method == "POST" and (
            path == "/api/v1/analysis-runs" or path.endswith("/exports/html")
        ):
            writes.append(path)

    page.on("request", observe)
    try:
        for entry in original["analyses"]:
            analysis_id = entry["analysis_id"]
            restored = _api(page, base, f"/api/v1/analysis-runs/{analysis_id}/result")
            assert digest(restored) == entry["envelope_sha256"]
            capability = _api(
                page,
                base,
                f"/api/v1/analysis-runs/{analysis_id}/report-capability?locale=ko",
            )
            assert capability["source_result_sha256"] == entry["source_result_sha256"]
            _locale(page, "ko")
            _open(page, base, ROUTE, original["version"])
            _restore_result(page, base, original["version"], restored)
            charts = page.locator("[data-gage-six-panel]")
            expect(charts).to_be_visible()
            values = _assert_six_values(charts, restored["result"])
            charts.screenshot(path=str(output / f"restored-{entry['policy']}.png"))
            receipt["analyses"].append(
                {
                    "analysis_id": analysis_id,
                    "envelope_sha256": digest(restored),
                    "source_result_sha256": capability["source_result_sha256"],
                    **values,
                }
            )
        for artifact in original["reports"]:
            descriptor = artifact["descriptor"]
            locale = artifact["locale"]
            _locale(page, locale)
            page.goto(
                base + "/reports?analysis_id=" + descriptor["analysis_id"],
                wait_until="domcontentloaded",
            )
            wait_for_app_ready(page, locale, "/reports")
            row = page.locator(
                ".report-selected-result .analysis-export-panel .export-list-item"
            ).filter(has_text=descriptor["sha256"][:12])
            expect(row).to_have_count(1)
            with page.expect_download() as download:
                row.get_by_role(
                    "button",
                    name="다운로드" if locale == "ko" else "download",
                    exact=True,
                ).click()
            path = output / f"restored-{descriptor['export_id']}.html"
            download.value.save_as(path)
            assert path.read_bytes() == Path(artifact["path"]).read_bytes()
            assert hashlib.sha256(path.read_bytes()).hexdigest() == descriptor["sha256"]
            receipt["reports"].append(
                {
                    "export_id": descriptor["export_id"],
                    "sha256": descriptor["sha256"],
                    "bytes_identical": True,
                }
            )
        assert not writes, writes
        _locale(page, "ko")
        receipt.update(
            status="succeeded", analysis_post_count=0, report_creation_post_count=0
        )
        return receipt
    finally:
        page.remove_listener("request", observe)


def verify_gage_six_panel(browser: Browser, base: str, output: Path) -> dict:
    target = output / "gage-six-panel"
    target.mkdir(parents=True, exist_ok=True)
    receipt: dict = {
        "schema_version": 1,
        "status": "running",
        "fixture": "synthetic_hand60_not_user_data",
        "analyses": [],
        "layout": [],
        "reports": [],
        "legacy_ui": "synthetic_read_only_schema2_transport_projection",
        "offline_html": "network_disabled_context_not_server_process_shutdown",
    }
    with diagnosed_page(
        browser, output, "gage-six-panel", init_script=INITIAL_LOCALE
    ) as page:
        page.set_viewport_size({"width": 1440, "height": 1000})
        version = ingest(page, base, _fixture(), "csv")
        receipt["version"] = version
        analysis_posts: list[str] = []
        page.on(
            "request",
            lambda request: analysis_posts.append(request.url)
            if request.method == "POST"
            and urlsplit(request.url).path == "/api/v1/analysis-runs"
            else None,
        )
        for policy in ("retain", "auto_pool"):
            panel = _configure(page, base, version, policy)
            envelope = _run(page, panel)
            charts = panel.locator("[data-gage-six-panel]")
            values = _assert_six_values(charts, envelope["result"])
            original = digest(envelope)
            coordinates = _graph_coordinates(charts)
            post_count = len(analysis_posts)
            pinned = charts.locator(
                '[data-gage-chart-kind="response_by_part"] [data-point-id="raw:1"]'
            )
            pinned.click()
            for locale in ("ko", "en", "ko"):
                _locale(page, locale)
                expect(charts.get_by_role("heading", level=3)).to_have_text(
                    "Gage R&R graph summary"
                    if locale == "en"
                    else "Gage R&R 그래프 요약"
                )
                expect(charts).to_contain_text(MEASUREMENT)
                expect(pinned).to_have_attribute("data-selected", "true")
                assert _graph_coordinates(charts) == coordinates
                for width in (1440, 1024, 768, 1440):
                    page.set_viewport_size({"width": width, "height": 1000})
                    receipt["layout"].append(
                        {"policy": policy, "locale": locale, **_layout(page, charts)}
                    )
                charts.screenshot(
                    path=str(target / f"{policy}-{locale}-six-panels.png")
                )
            _interaction(page, charts)
            assert (
                len(analysis_posts) == post_count
            ), "View controls/locale/resize must not submit analysis"
            assert (
                digest(
                    _api(
                        page,
                        base,
                        f"/api/v1/analysis-runs/{envelope['analysis_id']}/result",
                    )
                )
                == original
            )
            receipt["analyses"].append(
                {
                    "analysis_id": envelope["analysis_id"],
                    "policy": policy,
                    "envelope_sha256": original,
                    **values,
                }
            )
            receipt["reports"].append(
                _report(
                    page,
                    base,
                    envelope,
                    target / "html",
                    "en" if policy == "retain" else "ko",
                )
            )
            receipt["analyses"][-1]["source_result_sha256"] = receipt["reports"][-1][
                "descriptor"
            ]["source_result_sha256"]
            _configure(page, base, version, policy)
            _restore_result(page, base, version, envelope)
            expect(page.locator("[data-gage-six-panel]")).to_be_visible()
            _assert_six_values(
                page.locator("[data-gage-six-panel]"), envelope["result"]
            )
        receipt["zoom_analysis_id"] = envelope["analysis_id"]
        # UI-only legacy reader projection; never rewrite a stored result or its hash.
        legacy = deepcopy(envelope)
        legacy["result"]["schema_version"] = 2
        del legacy["result"]["plot_bundle"]
        legacy_path = f"/api/v1/analysis-runs/{envelope['analysis_id']}/result"
        page.route(
            "**" + legacy_path,
            lambda route: route.fulfill(
                status=200, content_type="application/json", body=json.dumps(legacy)
            ),
        )
        post_count = len(analysis_posts)
        _open(page, base, ROUTE, version)
        _restore_result(page, base, version, legacy)
        legacy_charts = page.locator("[data-gage-six-panel]")
        expect(legacy_charts).to_be_visible()
        expect(legacy_charts.locator("svg.chart-frame-svg")).to_have_count(1)
        for kind in KINDS[1:]:
            slot = legacy_charts.locator(f'[data-gage-chart-kind="{kind}"]')
            expect(slot).to_be_visible()
            expect(slot).to_have_attribute("data-gage-chart-state", "unavailable")
            expect(slot.locator("svg")).to_have_count(0)
            assert slot.inner_text().strip()
        page.unroute("**" + legacy_path)
        assert _api(page, base, legacy_path) == envelope
        assert len(analysis_posts) == post_count
        # A complete-cell filter changes all plotted Ns, not merely the visible raw points.
        panel = _configure(page, base, version, "retain")
        measurement_id = next(
            column["column_id"]
            for column in version["columns"]
            if column["display_name"] == MEASUREMENT
        )
        _filter(page, measurement_id, "lt", "67")
        filtered = _run(page, panel)
        counts = filtered["result"]["plot_bundle"]["counts"]
        assert counts["n_used"] == 54 and counts["part_count"] == 9
        assert len(filtered["result"]["plot_bundle"]["cells"]) == 27
        receipt["filter"] = {
            "n_used": 54,
            "cells": 27,
            "source_digest": digest(filtered),
        }
        # Extra dimensions exercise both explicit pagers without changing the hand fixture.
        paged_version = ingest(page, base, _fixture(11, 4), "csv")
        paged = _run(page, _configure(page, base, paged_version, "retain"))
        assert paged["result"]["plot_bundle"]["counts"]["n_used"] == 88
        _locale(page, "en")
        charts = page.locator("[data-gage-six-panel]")
        post_count = len(analysis_posts)
        for name in ("Part page", "Operator page"):
            control = charts.get_by_role("group", name=name, exact=True)
            buttons = control.get_by_role("button")
            expect(buttons.first).to_be_disabled()
            expect(buttons.last).to_be_enabled()
            buttons.last.click()
            expect(buttons.last).to_be_disabled()
            expect(buttons.first).to_be_enabled()
        assert len(_points(charts.locator('[data-gage-chart-kind="dispersion"]'))) == 1
        assert len(_points(charts.locator('[data-gage-chart-kind="interaction"]'))) == 1
        expect(
            charts.locator(
                '[data-gage-chart-kind="response_by_operator"] [data-box-id]'
            )
        ).to_have_count(1)
        assert len(analysis_posts) == post_count
        assert (
            _api(page, base, f"/api/v1/analysis-runs/{paged['analysis_id']}/result")
            == paged
        )
        receipt["pagination"] = {
            "parts": 11,
            "operators": 4,
            "selected_cells": 1,
            "source_digest": digest(paged),
        }
    _offline_reports(browser, receipt["reports"], target)
    receipt["view_only_analysis_post_count"] = 0
    receipt["interaction_checks"] = [
        "hover",
        "pin_preserved_while_hovering",
        "escape_keeps_focus",
        "single_roving_item",
        "tab_exit",
        "locale_preserves_pin",
    ]
    receipt["status"] = "succeeded"
    (target / "receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return receipt


def verify_gage_six_panel_zoom(
    playwright: Playwright, base: str, output: Path, receipt: dict
) -> dict:
    """Real Chromium tab zoom using the existing extension mechanism, not CSS/DSF."""
    target = output / "gage-six-panel-zoom"
    target.mkdir(parents=True, exist_ok=True)
    result: dict = {
        "schema_version": 1,
        "status": "running",
        "fixture": "synthetic_saved_hand60",
        "mechanism": "chrome.tabs.setZoom/getZoom",
        "deviceScaleFactor_override": False,
        "steps": [],
    }
    errors: list[str] = []
    assets: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="datalab-gage-zoom-") as temporary:
        root = Path(temporary)
        extension = root / "extension"
        extension.mkdir()
        (extension / "manifest.json").write_text(
            json.dumps(
                {
                    "manifest_version": 3,
                    "name": "Synthetic Gage zoom verification",
                    "version": "1.0",
                    "permissions": ["tabs"],
                    "background": {"service_worker": "worker.js"},
                }
            ),
            encoding="utf-8",
        )
        (extension / "worker.js").write_text(
            "chrome.runtime.onInstalled.addListener(() => {});", encoding="utf-8"
        )
        context = playwright.chromium.launch_persistent_context(
            str(root / "profile"),
            channel="chromium",
            headless=True,
            viewport={"width": 1440, "height": 1000},
            args=[
                f"--disable-extensions-except={extension}",
                f"--load-extension={extension}",
            ],
        )
        context.add_init_script(INITIAL_LOCALE)
        page = context.new_page()
        diagnostics = SyntheticPageDiagnostics(page, output, "gage-six-panel-zoom")
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "requestfailed",
            lambda request: assets.append(
                {"path": urlsplit(request.url).path, "failure": request.failure}
            )
            if request.resource_type in ("script", "stylesheet")
            else None,
        )
        posts: list[str] = []
        page.on(
            "request",
            lambda request: posts.append(request.url)
            if request.method == "POST"
            and urlsplit(request.url).path == "/api/v1/analysis-runs"
            else None,
        )
        failed = False
        try:
            diagnostics.start()
            worker = (
                context.service_workers[0]
                if context.service_workers
                else context.wait_for_event("serviceworker")
            )
            analysis_id = receipt["zoom_analysis_id"]
            source_path = f"/api/v1/analysis-runs/{analysis_id}/result"
            original = _api(page, base, source_path)
            assert original["analysis_id"] == analysis_id
            assert original["dataset_version_id"] == receipt["version"]["version_id"]
            saved = next(
                entry for entry in receipt["analyses"] if entry["analysis_id"] == analysis_id
            )
            assert digest(original) == saved["envelope_sha256"]
            _open(page, base, ROUTE, receipt["version"])
            _restore_result(page, base, receipt["version"], original)
            charts = page.locator("[data-gage-six-panel]")
            expect(charts).to_be_visible()
            _assert_six_values(charts, original["result"])
            coordinates = _graph_coordinates(charts)
            for locale in ("ko", "en", "ko"):
                _locale(page, locale)
                for factor in (1, 1.25, 1.5, 1):
                    actual = worker.evaluate(
                        """async ({url, factor}) => {
                        const tab = (await chrome.tabs.query({})).find(tab => tab.url === url);
                        if (!tab) throw new Error('Gage saved result tab missing');
                        await chrome.tabs.setZoomSettings(tab.id, {mode:'automatic', scope:'per-tab'});
                        await chrome.tabs.setZoom(tab.id, factor);
                        return chrome.tabs.getZoom(tab.id);
                    }""",
                        {"url": page.url, "factor": factor},
                    )
                    _assert_close(actual, factor)
                    page.wait_for_function(
                        "width => Math.abs(innerWidth-width) <= 2", arg=1440 / factor
                    )
                    result["steps"].append(
                        {
                            "locale": locale,
                            "browser_zoom": actual,
                            **_layout(page, charts),
                        }
                    )
                    assert _graph_coordinates(charts) == coordinates
                    expect(charts).to_contain_text(MEASUREMENT)
                    result["steps"][-1]["viewport_evidence"] = [
                        {
                            "chart_kind": kind,
                            **capture_viewport_evidence(
                                page,
                                charts.locator(
                                    f'[data-gage-chart-kind="{kind}"] svg.chart-frame-svg'
                                ),
                                target
                                / (
                                    f"{len(result['steps']):02d}-{locale}-"
                                    f"{round(factor*100)}-{kind}.png"
                                ),
                            ),
                        }
                        for kind in ("components", "interaction")
                    ]
                    assert not posts and not errors and not assets
            assert _api(page, base, source_path) == original
            result["source_digest"] = digest(original)
            result["status"] = "succeeded"
            (target / "receipt.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except BaseException as error:
            failed = True
            diagnostics.capture_failure(error)
            raise
        finally:
            try:
                diagnostics.finish(failed=failed)
            except Exception as error:
                failed = True
                diagnostics.capture_failure(error)
                raise
            finally:
                try:
                    context.close()
                except Exception as error:
                    if not failed:
                        raise
                    print(
                        f"[Gage zoom cleanup] {type(error).__name__}", file=sys.stderr
                    )
    return result
