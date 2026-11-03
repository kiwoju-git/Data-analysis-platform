"""Metric DOM geometry under live resize and actual Chromium tab zoom."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Page, Playwright, expect

from app_readiness import SyntheticPageDiagnostics
from english_system_text import (
    _source_digest,
    create_quality_fixture,
    run_chart_fixture,
)
from pilot_edge_cases import _locale


def metric_geometry(page: Page) -> dict:
    evidence = page.locator(".run-chart-randomness-container").evaluate("""root => {
        const rect = el => {
            const r = el.getBoundingClientRect();
            return {left:r.left, right:r.right, top:r.top, bottom:r.bottom, width:r.width, height:r.height};
        };
        const grid = root.querySelector('.run-chart-randomness-grid');
        const cards = [...grid.querySelectorAll('[data-result-metric]')].map(card => ({
            id:card.dataset.resultMetric, card:rect(card),
            label:rect(card.querySelector('.result-metric-card-label')),
            value:rect(card.querySelector('.result-metric-card-value')),
            client:card.clientWidth, scroll:card.scrollWidth,
            pairs:[...card.querySelectorAll('dl > div')].map(pair => ({
                dt:rect(pair.querySelector('dt')), dd:rect(pair.querySelector('dd')),
                client:pair.clientWidth, scroll:pair.scrollWidth
            }))
        }));
        return {container:rect(root), columns:getComputedStyle(grid).gridTemplateColumns.split(' ').length,
            viewport:{width:innerWidth,height:innerHeight}, pageScroll:document.documentElement.scrollWidth, cards};
    }""")
    width = evidence["container"]["width"]
    expected_columns = 4 if width >= 1028 else 2 if width >= 508 else 1
    assert evidence["columns"] == expected_columns, evidence
    assert len(evidence["cards"]) == 4, evidence
    assert evidence["pageScroll"] <= evidence["viewport"]["width"] + 1, evidence
    for card in evidence["cards"]:
        assert card["value"]["top"] - card["label"]["bottom"] >= 7, card
        assert card["scroll"] <= card["client"] + 1, card
        assert card["value"]["right"] <= card["card"]["right"] + 1, card
        assert card["value"]["left"] >= card["card"]["left"] - 1, card
        assert len(card["pairs"]) == 3, card
        for pair in card["pairs"]:
            assert pair["dd"]["top"] - pair["dt"]["bottom"] >= 5, pair
            assert pair["scroll"] <= pair["client"] + 1, pair
    return evidence


def verify_result_metric_layout(
    playwright: Playwright, base: str, output: Path
) -> dict:
    report: dict = {
        "schema_version": 1,
        "status": "running",
        "fixture": "synthetic 60-row Run Chart",
        "mechanism": "chrome.tabs.setZoom/getZoom",
        "deviceScaleFactor_override": False,
        "steps": [],
    }
    with tempfile.TemporaryDirectory(prefix="datalab-metric-zoom-") as temporary:
        directory = Path(temporary)
        extension = directory / "extension"
        extension.mkdir()
        (extension / "manifest.json").write_text(
            json.dumps(
                {
                    "manifest_version": 3,
                    "name": "Synthetic metric zoom verification",
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
            str(directory / "profile"),
            channel="chromium",
            headless=True,
            viewport={"width": 1440, "height": 1000},
            args=[
                f"--disable-extensions-except={extension}",
                f"--load-extension={extension}",
            ],
        )
        page = context.new_page()
        diagnostics = SyntheticPageDiagnostics(page, output, "result-metric-layout")
        failure = False
        try:
            diagnostics.start()
            context.add_init_script(
                "localStorage.setItem('statistical-twin.locale', 'ko')"
            )
            worker = (
                context.service_workers[0]
                if context.service_workers
                else context.wait_for_event("serviceworker")
            )
            version = create_quality_fixture(page, base, "측정값 사용자 이름")
            panel, envelope = run_chart_fixture(page, base, version, "ko")
            before_hash = _source_digest(page, base, envelope["analysis_id"])
            for summary in panel.locator(".result-metric-card summary").all():
                summary.click()
            source_values = panel.locator("select").evaluate_all(
                "els => els.map(el => el.value)"
            )
            cards = panel.locator("[data-result-metric]").element_handles()
            posts: list[str] = []
            errors: list[str] = []
            page.on(
                "request",
                lambda request: posts.append(request.url)
                if request.method == "POST"
                and urlsplit(request.url).path == "/api/v1/analysis-runs"
                else None,
            )
            page.on("pageerror", lambda error: errors.append(str(error)))
            for locale in ("ko", "en", "ko"):
                _locale(page, locale)
                for width in (1440, 1280, 1024, 390, 1440):
                    page.set_viewport_size({"width": width, "height": 1000})
                    for factor in (1.0,) if width == 390 else (1.0, 1.25, 1.5, 1.0):
                        zoom = worker.evaluate(
                            """async ({url,factor}) => {
                            const tab = (await chrome.tabs.query({})).find(item => item.url === url);
                            if (!tab) throw new Error('Metric tab missing');
                            await chrome.tabs.setZoomSettings(tab.id, {mode:'automatic',scope:'per-tab'});
                            await chrome.tabs.setZoom(tab.id, factor);
                            return chrome.tabs.getZoom(tab.id);
                        }""",
                            {"url": page.url, "factor": factor},
                        )
                        assert abs(zoom - factor) < 1e-9, zoom
                        page.wait_for_function(
                            "expected => Math.abs(innerWidth-expected) <= 2",
                            arg=width / factor,
                        )
                        opener = page.locator(".mobile-menu-toggle")
                        if width == 1024 and factor == 1.0 and opener.is_visible():
                            opener.click()
                            expect(opener).to_have_attribute("aria-expanded", "true")
                            page.keyboard.press("Escape")
                            expect(opener).to_have_attribute("aria-expanded", "false")
                        page.evaluate(
                            "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
                        )
                        assert all(
                            card.evaluate("el => el.isConnected") for card in cards
                        )
                        assert (
                            panel.locator("select").evaluate_all(
                                "els => els.map(el => el.value)"
                            )
                            == source_values
                        )
                        expect(page.locator("#active-dataset-version")).to_have_value(
                            version["version_id"]
                        )
                        state = metric_geometry(page)
                        state.update(
                            locale=locale, browserZoom=zoom, physicalViewportWidth=width
                        )
                        report["steps"].append(state)
                        assert not posts, posts
                        assert not errors, errors
                        if width in (1024, 1440) and factor in (1.0, 1.5):
                            page.locator(".run-chart-randomness-container").screenshot(
                                path=str(
                                    diagnostics.target
                                    / f"{locale}-{width}-{round(factor*100)}.png"
                                )
                            )
            assert {step["columns"] for step in report["steps"]} == {1, 2, 4}, report
            assert _source_digest(page, base, envelope["analysis_id"]) == before_hash
            report.update(
                analysis_id=envelope["analysis_id"],
                source_sha256=before_hash,
                status="succeeded",
                source_hash_preserved=True,
                analysis_posts_during_resize=0,
                pageerror_count=0,
            )
            (diagnostics.target / "receipt.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except BaseException as error:
            failure = True
            diagnostics.capture_failure(error)
            raise
        finally:
            try:
                diagnostics.finish(failed=failure)
            finally:
                context.close()
    return report
