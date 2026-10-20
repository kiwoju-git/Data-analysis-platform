"""Actual Chromium tab zoom against an immutable, saved synthetic RSM analysis."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import traceback
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from playwright.sync_api import BrowserContext, Page, Playwright, expect

from app_readiness import (
    socket_failure_diagnostics,
    source_identity,
    wait_for_app_ready,
)


def _controls(page: Page) -> list[dict]:
    return page.locator(
        ".analysis-run-panel input, .analysis-run-panel select, .analysis-run-panel textarea"
    ).evaluate_all("""elements => elements.map(element => ({
        tag: element.tagName, type: element.type, value: element.value,
        checked: element instanceof HTMLInputElement ? element.checked : null
    }))""")


def _plot_coordinates(page: Page) -> list[dict]:
    return page.locator(".rsm-plot-options svg.chart-frame-svg").evaluate_all(
        """elements => elements.map(svg => ({
            viewBox: svg.getAttribute('viewBox'),
            shapes: [...svg.querySelectorAll('path, circle, line, rect, polygon, polyline')]
                .map(shape => Object.fromEntries(
                    ['d', 'cx', 'cy', 'r', 'x', 'y', 'x1', 'x2', 'y1', 'y2',
                     'width', 'height', 'points'].map(key => [key, shape.getAttribute(key)])
                ))
        }))"""
    )


def _geometry(page: Page) -> dict:
    geometry = page.evaluate("""() => {
        const rect = element => {
            const value = element.getBoundingClientRect();
            return {left: value.left, right: value.right, top: value.top,
                bottom: value.bottom, width: value.width, height: value.height};
        };
        const result = document.querySelector('[aria-labelledby="rsm-result-title"]');
        const summary = [...result.querySelectorAll('dl > div')].flatMap(pair => {
            const label = pair.querySelector(':scope > dt');
            const value = pair.querySelector(':scope > dd');
            return label && value ? [{
                label: label.textContent, dt: rect(label), dd: rect(value),
                dtClient: label.clientWidth, dtScroll: label.scrollWidth,
                ddClient: value.clientWidth, ddScroll: value.scrollWidth
            }] : [];
        });
        const charts = [...result.querySelectorAll('.chart-frame-svg')].map(svg => ({
            svg: rect(svg), frame: rect(svg.closest('.chart-frame')),
            card: svg.closest('.doe-compact-plot')
                ? rect(svg.closest('.doe-compact-plot')) : null
        }));
        return {
            viewport: {width: innerWidth, height: innerHeight},
            scrollWidth: document.documentElement.scrollWidth,
            devicePixelRatio, summary, charts,
            compactCount: result.querySelectorAll('.doe-compact-plot').length,
            columns: [...result.querySelectorAll('.doe-compact-grid')].map(
                grid => getComputedStyle(grid).gridTemplateColumns.split(' ').length
            )
        };
    }""")
    assert geometry["scrollWidth"] <= geometry["viewport"]["width"] + 1, geometry
    assert geometry["summary"], "Saved model summaries were not rendered"
    for pair in geometry["summary"]:
        label, value = pair["dt"], pair["dd"]
        overlap_x = min(label["right"], value["right"]) - max(
            label["left"], value["left"]
        )
        overlap_y = min(label["bottom"], value["bottom"]) - max(
            label["top"], value["top"]
        )
        assert overlap_x <= 1 or overlap_y <= 1, pair
        assert pair["dtScroll"] <= pair["dtClient"] + 1, pair
        assert pair["ddScroll"] <= pair["ddClient"] + 1, pair
    assert geometry["charts"] and geometry["compactCount"] > 0, geometry
    for chart in geometry["charts"]:
        svg, frame, card = chart["svg"], chart["frame"], chart["card"]
        assert svg["width"] > 0 and svg["height"] > 0, chart
        assert (
            svg["left"] >= frame["left"] - 1 and svg["right"] <= frame["right"] + 1
        ), chart
        assert (
            svg["top"] >= frame["top"] - 1 and svg["bottom"] <= frame["bottom"] + 1
        ), chart
        if card is not None:
            assert frame["left"] >= card["left"] - 1, chart
            assert frame["right"] <= card["right"] + 1, chart
    return geometry


def _failure_evidence(
    page: Page | None,
    output: Path,
    failure: BaseException,
    errors: list[str],
    failed_assets: list[dict],
    report: dict,
) -> None:
    failure.e2e_child_diagnostics = str(output)
    evidence: dict = {
        "fixture": "synthetic",
        "stage": "doe-browser-zoom",
        "pageerrors": errors,
        "failed_assets": failed_assets,
        "failure_type": type(failure).__name__,
        "traceback": traceback.format_exception(
            type(failure), failure, failure.__traceback__
        ),
        "socket_snapshot": socket_failure_diagnostics(),
        "partial_receipt": report,
        **source_identity(),
    }
    if page is not None:
        for name, capture in {
            "url": lambda: page.url,
            "dom": lambda: (output / "failure.html").write_text(
                page.content(), encoding="utf-8"
            ),
            "screenshot": lambda: page.screenshot(
                path=str(output / "failure.png"), full_page=True
            )
            and None,
        }.items():
            try:
                evidence[name] = capture()
            except Exception as diagnostic_error:
                evidence[name + "_capture_error"] = type(diagnostic_error).__name__
    try:
        (output / "failure.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except Exception as diagnostic_error:
        print(f"[zoom diagnostics] {type(diagnostic_error).__name__}", file=sys.stderr)


def verify_doe_browser_zoom(
    playwright: Playwright,
    base: str,
    output: Path,
    rsm_design_id: str,
    rsm_analysis_id: str,
) -> dict:
    """A separate extension-enabled context; no CSS scale or DSF emulation."""
    target = output / "doe-browser-zoom"
    target.mkdir(parents=True, exist_ok=True)
    path = "/analysis/doe/doe.response_surface"
    route = (
        path
        + "?"
        + urlencode(
            {
                "design_id": rsm_design_id,
                "analysis_id": rsm_analysis_id,
            }
        )
    )
    analysis_path = f"/api/v1/doe-designs/response-surface/{rsm_design_id}/analyses/{rsm_analysis_id}"
    report: dict = {
        "schema_version": 1,
        "fixture": "synthetic saved RSM analysis",
        "mechanism": "chrome.tabs.setZoom/getZoom",
        "deviceScaleFactor_override": False,
        "design_id": rsm_design_id,
        "analysis_id": rsm_analysis_id,
        "steps": [],
        "fractional_zoom": "not_exercised_by_this_fixture",
    }
    errors: list[str] = []
    failed_assets: list[dict] = []
    analysis_posts: list[str] = []
    context: BrowserContext | None = None
    page: Page | None = None
    original_failure: BaseException | None = None
    trace_started = False
    with tempfile.TemporaryDirectory(prefix="datalab-doe-zoom-") as temporary:
        root = Path(temporary)
        extension = root / "extension"
        extension.mkdir()
        (extension / "manifest.json").write_text(
            json.dumps(
                {
                    "manifest_version": 3,
                    "name": "Synthetic DOE zoom verification",
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
        try:
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
            context.add_init_script(
                "localStorage.setItem('statistical-twin.locale', 'ko')"
            )
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            trace_started = True
            worker = (
                context.service_workers[0]
                if context.service_workers
                else (context.wait_for_event("serviceworker"))
            )
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on(
                "requestfailed",
                lambda request: failed_assets.append(
                    {
                        "path": urlsplit(request.url).path,
                        "failure": request.failure,
                    }
                )
                if request.resource_type in ("script", "stylesheet")
                else None,
            )
            page.on(
                "request",
                lambda request: analysis_posts.append(urlsplit(request.url).path)
                if request.method == "POST"
                and urlsplit(request.url).path.endswith("/analyses")
                else None,
            )
            page.goto(base + route, wait_until="domcontentloaded")
            wait_for_app_ready(page, "ko", route)
            result = page.locator('[aria-labelledby="rsm-result-title"]')
            plots = result.locator(".rsm-plot-options")
            expect(plots).to_be_visible()
            expect(
                plots.get_by_role("button", name="그래프 설정 적용", exact=True)
            ).to_be_enabled()
            source = page.request.get(base + analysis_path)
            assert source.status == 200, source.text()
            stored_bytes = source.body()
            stored = source.json()
            assert stored["analysis_id"] == rsm_analysis_id
            assert stored["design_id"] == rsm_design_id
            assert stored["result"]["plot_bundle"]
            factor_count = len(stored["result"]["factor_names"])
            expected_cards = factor_count + factor_count * (factor_count - 1) // 2
            plots.get_by_label("소형 전체 보기", exact=True).check()
            expect(plots.locator(".doe-compact-plot")).to_have_count(expected_cards)
            name = page.locator("#rsm-design-name")
            draft = "Synthetic zoom draft 유지"
            name.fill(draft)
            controls = _controls(page)
            coordinates = _plot_coordinates(page)
            assert coordinates
            result_element = result.element_handle()
            assert result_element is not None
            dataset = page.locator("#active-dataset-version")
            dataset_value = dataset.input_value() if dataset.count() else None
            for locale in ("ko", "en"):
                if locale == "en":
                    page.locator(".language-switcher button").filter(
                        has_text="ENG"
                    ).click()
                wait_for_app_ready(page, locale, route)
                overview = plots.get_by_label(
                    "소형 전체 보기" if locale == "ko" else "Compact overview",
                    exact=True,
                )
                for index, factor in enumerate((1.0, 1.25, 1.5, 1.0)):
                    actual = worker.evaluate(
                        """async ({url, factor}) => {
                        const tabs = await chrome.tabs.query({});
                        const tab = tabs.find(tab => tab.url === url);
                        if (!tab) throw new Error('Saved RSM tab missing');
                        await chrome.tabs.setZoomSettings(tab.id, {
                            mode: 'automatic', scope: 'per-tab'
                        });
                        await chrome.tabs.setZoom(tab.id, factor);
                        return chrome.tabs.getZoom(tab.id);
                    }""",
                        {"url": page.url, "factor": factor},
                    )
                    assert abs(actual - factor) < 1e-9
                    page.wait_for_function(
                        "expected => Math.abs(innerWidth - expected) <= 2",
                        arg=1440 / factor,
                    )
                    expect(name).to_have_value(draft)
                    expect(overview).to_be_checked()
                    expect(plots.locator(".doe-compact-plot")).to_have_count(
                        expected_cards
                    )
                    assert result_element.evaluate("element => element.isConnected")
                    assert _controls(page) == controls
                    assert _plot_coordinates(page) == coordinates
                    if dataset_value is not None:
                        expect(dataset).to_have_value(dataset_value)
                    assert parse_qs(urlsplit(page.url).query) == {
                        "design_id": [rsm_design_id],
                        "analysis_id": [rsm_analysis_id],
                    }
                    geometry = _geometry(page)
                    geometry.update(locale=locale, browserZoom=actual)
                    report["steps"].append(geometry)
                    assert not analysis_posts, analysis_posts
                    assert not errors, errors
                    page.mouse.move(0, 0)
                    page.evaluate("window.scrollTo(0, 0)")
                    page.screenshot(
                        path=str(
                            target / f"{locale}-{index}-{round(factor * 100)}.png"
                        ),
                        full_page=True,
                    )
            restored = page.request.get(base + analysis_path)
            assert restored.status == 200 and restored.body() == stored_bytes
            assert not failed_assets, failed_assets
            report.update(
                {
                    "status": "passed",
                    "analysis_sha256": hashlib.sha256(stored_bytes).hexdigest(),
                    "source_unchanged": True,
                    "analysis_post_count": len(analysis_posts),
                    "draft_preserved": True,
                    "plot_coordinates_unchanged": True,
                    "committed_result_dom_preserved": True,
                }
            )
            (target / "zoom-receipt.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return report
        except BaseException as failure:
            original_failure = failure
            _failure_evidence(page, target, failure, errors, failed_assets, report)
            raise
        finally:
            cleanup_errors: list[Exception] = []
            if context is not None:
                if trace_started:
                    try:
                        context.tracing.stop(path=str(target / "trace.zip"))
                    except Exception as cleanup_error:
                        cleanup_errors.append(cleanup_error)
                try:
                    context.close()
                except Exception as cleanup_error:
                    cleanup_errors.append(cleanup_error)
            for cleanup_error in cleanup_errors:
                print(f"[zoom cleanup] {type(cleanup_error).__name__}", file=sys.stderr)
            if cleanup_errors and original_failure is None:
                raise cleanup_errors[0]
