"""Exact applied-axis graph checks, with no fit or evaluation side effects."""

from pathlib import Path

from playwright.sync_api import expect

from app_readiness import wait_for_layout_settled


def verify_profile_grid(
    page,
    profiler,
    rows: list[dict],
    responses: list[dict],
    factor: dict,
    output: Path,
    *,
    suffix: str,
) -> dict:
    grid = profiler.locator(".bo-profile-grid")
    expect(grid).to_have_count(1)
    expect(grid.locator(".bo-profile-grid-item")).to_have_count(len(responses) + 1)
    categorical = factor.get("domain_kind") in {"nominal", "ordinal"}
    xs = [
        index if categorical else row["actual_coordinates"][factor["factor_id"]]
        for index, row in enumerate(rows)
    ]
    for definition in responses:
        # The response identity belongs to the item itself, not a translated label.
        chart = grid.locator(
            f'.bo-profile-grid-item[data-response-id="{definition["response_id"]}"]'
        )
        expect(chart).to_have_count(1)
        expect(chart).to_contain_text(definition["name"])
        if definition.get("unit"):
            expect(chart.locator("svg.chart-frame-svg")).to_contain_text(
                definition["unit"]
            )
        expected = [
            [
                x,
                next(
                    p
                    for p in row["response_predictions"]
                    if p["response_id"] == definition["response_id"]
                )["mean_raw"],
            ]
            for x, row in zip(xs, rows, strict=True)
        ]
        assert (
            chart.locator("[data-point-id]").evaluate_all(
                "els => els.map(e => [Number(e.dataset.x), Number(e.dataset.y)])"
            )
            == expected
        )
        if categorical:
            expect(chart.locator("path.interactive-data-line")).to_have_count(0)
        for row in rows:
            marker = chart.locator(f'[data-point-id="{row["row_id"]}"]')
            assert marker.evaluate("element => element.tagName") == (
                "circle" if row["constraints_satisfied"] else "polygon"
            )
        first = chart.locator("[data-point-id]").first
        first.focus()
        first.press("Enter")
        expect(first).to_have_attribute("data-selected", "true")
        first.press("Escape")
        expect(first).to_have_attribute("data-selected", "false")
        if len(rows) > 1:
            first.press("ArrowRight")
            expect(chart.locator("[data-point-id]").nth(1)).to_be_focused()
    composite = grid.locator('[data-profile-kind="composite"]')
    assert composite.locator("[data-point-id]").evaluate_all(
        "els => els.map(e => [Number(e.dataset.x), Number(e.dataset.y)])"
    ) == [
        [x, row["desirability_moments"]["mean"]]
        for x, row in zip(xs, rows, strict=True)
    ]
    writes = []

    def record(request):
        if "/api/" in request.url and request.method in {
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        }:
            writes.append(request.url)

    page.on("request", record)
    layouts = []
    try:
        for locale, language in (("ko", "KOR"), ("en", "ENG")):
            page.locator(".language-switcher button").filter(has_text=language).click()
            expect(page.locator("html")).to_have_attribute("lang", locale)
            # Use a locale-independent locator after switching language.
            current = page.locator(".bo-profile-grid")
            for row in rows:
                status = (
                    "Within the stored constraints." if row["constraints_satisfied"] else "Outside the stored constraints."
                ) if locale == "en" else (
                    "저장된 제약 조건 안입니다." if row["constraints_satisfied"] else "저장된 제약 조건을 벗어납니다."
                )
                markers = current.locator(f'[data-point-id="{row["row_id"]}"]')
                assert markers.count() == len(responses) + 1
                assert all(status in item for item in markers.evaluate_all("els => els.map(e => e.getAttribute('aria-label'))"))
            for width in (1024, 1440):
                page.set_viewport_size({"width": width, "height": 1000})
                wait_for_layout_settled(page)
                boxes = current.locator(".bo-profile-grid-item").evaluate_all("""els => els.map(e => {
                    const r = e.getBoundingClientRect();
                    return {x:r.x, y:r.y, width:r.width, height:r.height,
                        overflow:e.scrollWidth-e.clientWidth};
                })""")
                assert boxes and all(
                    b["overflow"] <= 1 and b["width"] > 200 for b in boxes
                ), boxes
                for index, a in enumerate(boxes):
                    for b in boxes[index + 1 :]:
                        assert (
                            a["x"] + a["width"] <= b["x"] + 1
                            or b["x"] + b["width"] <= a["x"] + 1
                            or a["y"] + a["height"] <= b["y"] + 1
                            or b["y"] + b["height"] <= a["y"] + 1
                        ), boxes
                ticks = current.locator("svg.chart-frame-svg").evaluate_all("""svgs => svgs.map(svg => {
                    const frame = svg.getBoundingClientRect();
                    return [...svg.querySelectorAll('text.chart-tick-label[text-anchor="middle"]')]
                        .map(e => { const r=e.getBoundingClientRect();
                            return {text:e.textContent, left:r.left, right:r.right,
                                inside:r.left>=frame.left-1 && r.right<=frame.right+1}; });
                })""")
                for labels in ticks:
                    assert all(label["inside"] for label in labels), labels
                    assert all(
                        a["right"] + 1 <= b["left"] for a, b in zip(labels, labels[1:])
                    ), labels
                current.screenshot(
                    path=output / f"profile-grid-{suffix}-{locale}-{width}.png"
                )
                layouts.append(
                    {
                        "locale": locale,
                        "viewport": width,
                        "items": boxes,
                        "x_ticks": ticks,
                    }
                )
        assert not writes, writes
    finally:
        page.remove_listener("request", record)
    return {
        "axis": factor["factor_id"],
        "response_count": len(responses),
        "rows_per_chart": len(rows),
        "constraint_violations_per_chart": sum(not row["constraints_satisfied"] for row in rows),
        "constraint_marker_and_accessibility_verified": True,
        "exact_coordinates": True,
        "display_only_api_writes": writes,
        "layouts": layouts,
    }
