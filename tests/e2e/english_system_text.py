"""Built-UI semantic text boundaries; all rows and labels are synthetic."""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Browser, Locator, Page, expect

from app_readiness import diagnosed_page, wait_for_app_ready
from pilot_edge_cases import _locale


def create_quality_fixture(page: Page, base: str, label: str = "Measurement") -> dict:
    content = label + "\n" + "\n".join(str(value) for value in range(1, 61)) + "\n"
    uploaded = page.request.post(
        base + "/api/v1/datasets",
        headers={"Origin": base},
        multipart={
            "file": {
                "name": "synthetic-metric.csv",
                "mimeType": "text/csv",
                "buffer": content.encode(),
            }
        },
    )
    assert uploaded.status == 201, uploaded.text()
    response = page.request.post(
        base + f"/api/v1/datasets/{uploaded.json()['dataset_id']}/confirm-parsing",
        headers={"Origin": base},
        data={
            "parsing": {
                "kind": "delimited_text",
                "encoding": "utf-8",
                "delimiter": ",",
                "quote_char": '"',
                "decimal": ".",
                "thousands": None,
                "has_header": True,
                "header_row": 1,
                "data_start_row": 2,
                "missing_tokens": ["", "NA"],
            },
            "columns": [],
        },
    )
    assert response.status == 201, response.text()
    return response.json()


def open_quality_method(
    page: Page, base: str, version: dict, method: str, locale: str
) -> Locator:
    route = "/analysis/quality/" + method
    page.goto(
        base + route + "?dataset_version_id=" + version["version_id"],
        wait_until="domcontentloaded",
    )
    wait_for_app_ready(page, locale, route)
    expect(page.locator("#active-dataset-version")).to_have_value(version["version_id"])
    panel = page.locator(f'[data-analysis-execution="{method}"]')
    panel.locator(".option-grid select").first.select_option(
        version["columns"][0]["column_id"]
    )
    return panel


def run_chart_fixture(
    page: Page, base: str, version: dict, locale: str
) -> tuple[Locator, dict]:
    panel = open_quality_method(page, base, version, "quality.run_chart", locale)
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and urlsplit(response.url).path == "/api/v1/analysis-runs"
    ) as response:
        panel.locator("button.primary-button").click()
    assert response.value.status == 201, response.value.text()
    envelope = response.value.json()
    expect(panel.locator("[data-result-metric]")).to_have_count(4)
    assert (
        0
        < envelope["result"]["approximate_randomness_tests"]["about_median"][
            "p_value_clustering"
        ]
        < 1e-6
    )
    return panel, envelope


def assert_english_system_text(
    scope: Locator, user_labels: tuple[str, ...] = ()
) -> dict:
    """Only exact fixture-owned labels may contain Korean; no element-wide exemption."""
    inspected = scope.evaluate(
        """(root, owned) => {
        const hangul = /[\\uAC00-\\uD7A3]/u;
        const visible = el => el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden';
        const records = [];
        const check = (text, kind) => {
            if (!text?.trim()) return;
            let system = text;
            for (const label of owned) system = system.split(label).join('');
            records.push({kind, text, invalid: hangul.test(system)});
        };
        const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        while (walk.nextNode()) {
            const parent = walk.currentNode.parentElement;
            if (parent && !['SCRIPT','STYLE'].includes(parent.tagName) && visible(parent)) check(walk.currentNode.textContent, 'text');
        }
        for (const element of [root, ...root.querySelectorAll('*')]) {
            if (!visible(element)) continue;
            for (const attribute of ['aria-label', 'aria-description', 'title', 'placeholder']) check(element.getAttribute(attribute), attribute);
        }
        return {checked: records.length, failures: records.filter(record => record.invalid)};
    }""",
        list(user_labels),
    )
    assert inspected["checked"] > 0, inspected
    assert not inspected["failures"], inspected
    return inspected


def _source_digest(page: Page, base: str, analysis_id: str) -> str:
    response = page.request.get(base + f"/api/v1/analysis-runs/{analysis_id}/result")
    assert response.status == 200, response.text()
    return hashlib.sha256(response.body()).hexdigest()


def verify_english_system_text(browser: Browser, base: str, output: Path) -> dict:
    evidence: dict = {
        "schema_version": 1,
        "status": "running",
        "fixture": "synthetic",
        "run_chart": [],
        "capability_errors": [],
        "coverage": "active Run Chart and Capability only",
    }
    with diagnosed_page(browser, output, "english-system-text", locale="en") as page:
        for label in ("Measurement", "측정값 사용자 이름"):
            version = create_quality_fixture(page, base, label)
            panel, envelope = run_chart_fixture(page, base, version, "en")
            source_hash = _source_digest(page, base, envelope["analysis_id"])
            for summary in panel.locator(".result-metric-card summary").all():
                summary.click()
            cards = panel.locator("[data-result-metric]").element_handles()
            before = panel.locator("select").evaluate_all(
                "els => els.map(el => el.value)"
            )
            posts: list[str] = []

            def track(request):
                if (
                    request.method == "POST"
                    and urlsplit(request.url).path == "/api/v1/analysis-runs"
                ):
                    posts.append(request.url)

            page.on("request", track)
            for locale in ("ko", "en", "ko", "en"):
                _locale(page, locale)
                assert (
                    panel.locator("select").evaluate_all(
                        "els => els.map(el => el.value)"
                    )
                    == before
                )
                assert all(card.evaluate("el => el.isConnected") for card in cards)
                expect(panel.locator(".metadata-grid")).to_contain_text(label)
                value = panel.locator(
                    '[data-result-metric="clustering"] .result-metric-card-value'
                )
                expect(value).not_to_have_text("p=0")
                if locale == "en":
                    evidence["run_chart"].append(
                        assert_english_system_text(
                            panel, () if label == "Measurement" else (label,)
                        )
                    )
                    history = page.locator(".compact-analysis-history")
                    expect(history.locator(".status-pill")).to_have_text("Not loaded")
                    evidence["run_chart"].append(assert_english_system_text(history))
            point = panel.locator('svg [tabindex="0"]').first
            expect(point).to_be_visible()
            point.focus()
            tooltip = page.locator('.chart-tooltip-portal[role="tooltip"]')
            expect(tooltip).to_be_visible()
            evidence["run_chart"].append(
                assert_english_system_text(
                    tooltip, () if label == "Measurement" else (label,)
                )
            )
            point.press("Escape")
            assert not posts, posts
            page.remove_listener("request", track)
            assert _source_digest(page, base, envelope["analysis_id"]) == source_hash
            evidence["run_chart"].append(
                {
                    "analysis_id": envelope["analysis_id"],
                    "source_sha256": source_hash,
                    "user_label_preserved": label != "Measurement",
                }
            )

        # Each invalid message is generated by actual input handlers, not a synthetic DOM injection.
        panel = open_quality_method(page, base, version, "quality.capability", "en")
        capability_posts: list[str] = []

        def track_capability(request):
            if (
                request.method == "POST"
                and urlsplit(request.url).path == "/api/v1/analysis-runs"
            ):
                capability_posts.append(request.url)

        page.on("request", track_capability)
        for lsl, usl, target, code, text in (
            (
                "NaN",
                "20",
                "",
                "invalid_number",
                "Specification limits and target must be finite numbers.",
            ),
            ("20", "10", "", "invalid_limit_order", "LSL must be less than USL."),
            (
                "10",
                "20",
                "9",
                "target_outside_limits",
                "Target must be within the specified limits.",
            ),
            (
                "10",
                "20",
                "21",
                "target_outside_limits",
                "Target must be within the specified limits.",
            ),
        ):
            fields = panel.locator(".option-grid input")
            for index, value in enumerate((lsl, usl, target)):
                fields.nth(index).fill(value)
            inputs = fields.evaluate_all("els => els.map(el => el.value)")
            url = page.url
            for locale in ("ko", "en", "ko", "en"):
                _locale(page, locale)
                notice = panel.locator(f'[data-validation-code="{code}"]')
                expect(notice).to_be_visible()
                expect(panel.locator("button.primary-button")).to_be_disabled()
                assert fields.evaluate_all("els => els.map(el => el.value)") == inputs
                assert page.url == url
                if locale == "en":
                    expect(notice).to_have_text(text)
                    evidence["capability_errors"].append(
                        assert_english_system_text(panel, ("측정값 사용자 이름",))
                    )
        page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )
        assert not capability_posts, capability_posts
        page.remove_listener("request", track_capability)
        evidence["capability_errors"].append({"cases": 4, "drafts_preserved": True})
    evidence.update(
        status="succeeded",
        analysis_posts_during_locale_changes=0,
        source_hashes_preserved=True,
    )
    return evidence
