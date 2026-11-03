"""Synthetic 60-row Gage journey through real UI forms and exact saved reports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Browser, Page, expect

from app_readiness import diagnosed_page, wait_for_app_ready
from pilot_edge_cases import (
    INITIAL_LOCALE,
    _api,
    _filter,
    _locale,
    _open,
    _report,
    ingest,
)


def verify_gage_followup(browser: Browser, base: str, output: Path) -> dict:
    evidence: dict = {
        "fixture": "synthetic_10_parts_3_operators_2_repeats_not_user_data",
        "analyses": [],
        "reports": [],
        "layout": [],
    }
    content = "part,operator,measurement\n" + "".join(
        f"P{part},O{operator},{100+2*part+operator+0.01*(part-4.5)*(operator-1)+error}\n"
        for part in range(10)
        for operator in range(3)
        for error in (-0.2, 0.2)
    )
    with diagnosed_page(
        browser, output, "gage-followup", init_script=INITIAL_LOCALE
    ) as page:
        version = ingest(page, base, content, "csv")
        columns = {
            item["display_name"]: item["column_id"] for item in version["columns"]
        }
        for policy in ("auto_pool", "retain"):
            _open(page, base, "/analysis/quality/quality.gage_rr", version)
            panel = page.locator('[data-analysis-execution="quality.gage_rr"]')
            selects = panel.locator(".option-grid").first.locator("select")
            selects.nth(0).select_option(columns["measurement"])
            selects.nth(1).select_option(columns["part"])
            selects.nth(2).select_option(columns["operator"])
            expect(panel.locator('[data-gage-control="replicate-mode"]')).to_have_value(
                "infer_from_rows"
            )
            panel.locator('[data-gage-control="interaction-policy"]').select_option(
                policy
            )
            alpha = "0.1" if policy == "auto_pool" else "0.05"
            panel.locator("details").first.locator("summary").click()
            panel.locator('[data-gage-control="interaction-alpha"]').fill(alpha)
            run = panel.get_by_role("button", name="Gage R&R 계산", exact=True)
            expect(run).to_be_enabled()
            with page.expect_response(
                lambda response: response.request.method == "POST"
                and urlsplit(response.url).path == "/api/v1/analysis-runs"
            ) as response:
                run.click()
            assert response.value.status == 201, response.value.text()
            envelope = response.value.json()
            result = envelope["result"]
            sent = response.value.request.post_data_json
            assert sent["options"]["replicate_column_id"] is None
            assert sent["options"]["interaction_policy"] == policy
            assert result["sample"]["n_used"] == 60
            assert result["design"]["replicate_count"] == 2
            assert result["interaction_selection"]["pooled"] is (policy == "auto_pool")
            assert result["interaction_selection"][
                "alpha_to_remove_interaction"
            ] == float(alpha)
            expect(panel.locator("[data-gage-policy]")).to_contain_text(policy)
            expect(
                panel.locator(".result-table").filter(has=page.locator("caption")).first
            ).to_be_visible()
            for locale in ("ko", "en"):
                _locale(page, locale)
                warnings = panel.locator(".warning-list")
                expect(warnings.first).to_contain_text(
                    "풀링했습니다"
                    if locale == "ko" and policy == "auto_pool"
                    else "별도 분산성분으로 유지했습니다"
                    if locale == "ko"
                    else "pooling interaction into repeatability error"
                    if policy == "auto_pool"
                    else "retained as a separate variance component"
                )
                expect(warnings.last).to_contain_text(
                    "사전점검은 설계 조건만 확인"
                    if locale == "ko"
                    else "This preflight checks the study design only"
                )
                for warning in envelope["warnings"]:
                    expect(warnings.first).to_contain_text(warning["code"])
                for width in (1024, 1280, 1440):
                    page.set_viewport_size({"width": width, "height": 900})
                    geometry = _settled_shell(page)
                    evidence["layout"].append(
                        {"policy": policy, "locale": locale, **geometry}
                    )
                    notes = panel.locator(".option-note").evaluate_all("""elements =>
                        elements.map(element => ({
                            labelBottom: element.querySelector('strong').getBoundingClientRect().bottom,
                            valueTop: element.querySelector('span').getBoundingClientRect().top
                        }))""")
                    assert len(notes) == 2
                    assert all(
                        note["valueTop"] >= note["labelBottom"] + 3 for note in notes
                    ), notes
                    expect(panel.locator("[data-gage-policy]")).to_contain_text(policy)
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= innerWidth + 1"
                    )
                    page.screenshot(
                        path=str(
                            output / "gage-followup" / f"{policy}-{locale}-{width}.png"
                        ),
                        full_page=True,
                    )
            evidence["analyses"].append(envelope)
            evidence["reports"].append(
                _report(page, base, envelope, output / "gage-html", "ko")
            )
            page.reload(wait_until="domcontentloaded")
            wait_for_app_ready(page, "ko", "/reports")
            expect(page.locator(".report-selected-result")).to_be_visible()
            assert (
                _api(
                    page,
                    base,
                    f"/api/v1/analysis-runs/{envelope['analysis_id']}/result",
                )
                == envelope
            )
            _open(page, base, "/analysis/quality/quality.gage_rr", version)
            _restore_result(page, base, version, envelope)
            panel = page.locator('[data-analysis-execution="quality.gage_rr"]')
            expect(
                panel.locator('[data-gage-control="interaction-policy"]')
            ).to_have_value(policy)
            expect(
                panel.locator('[data-gage-control="interaction-alpha"]')
            ).to_have_value(alpha)
            expect(panel.locator("[data-gage-policy]")).to_contain_text(policy)
        _open(page, base, "/analysis/quality/quality.gage_rr", version)
        panel = page.locator('[data-analysis-execution="quality.gage_rr"]')
        selects = panel.locator(".option-grid").first.locator("select")
        for index, name in enumerate(("measurement", "part", "operator")):
            selects.nth(index).select_option(columns[name])
        _filter(page, columns["measurement"], "gt", "100")
        requests = []
        page.on(
            "request",
            lambda request: requests.append(request.url)
            if request.method == "POST"
            and urlsplit(request.url).path == "/api/v1/analysis-runs"
            else None,
        )
        with page.expect_response(
            lambda response: response.url.endswith("/quality/gage-rr/preflight")
        ) as preflight:
            panel.get_by_role("button", name="Gage R&R 계산", exact=True).click()
        assert preflight.value.ok
        assert not preflight.value.json()["design"]["ready_for_anova"]
        expect(
            panel.locator(".notice-warning").filter(has_text="사전점검 오류").first
        ).to_be_visible()
        assert not requests, "Unbalanced filtered preflight must not launch an analysis"
    context = browser.new_context(offline=True)
    try:
        offline = context.new_page()
        for artifact in evidence["reports"]:
            path = Path(artifact["path"])
            assert (
                hashlib.sha256(path.read_bytes()).hexdigest()
                == artifact["descriptor"]["sha256"]
            )
            offline.goto(path.as_uri())
            expect(
                offline.locator('[data-report-section="gage_policy"]')
            ).to_contain_text("infer_from_rows")
            expect(
                offline.locator('[data-report-section="gage_full_anova"] table')
            ).to_be_visible()
            expect(
                offline.locator('[data-report-section="gage_anova"] table')
            ).to_be_visible()
            assert offline.locator("script, link[href]").count() == 0
    finally:
        context.close()
    evidence["status"] = "succeeded"
    (output / "gage-followup.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )
    return evidence


def _settled_shell(page: Page) -> dict:
    # Observe the actual drawer transition; an immediate screenshot can catch it mid-slide.
    page.wait_for_function("""() => {
        const sidebar = document.querySelector('#application-sidebar');
        const main = document.querySelector('.main');
        if (!sidebar || !main || sidebar.getAnimations().some(
            animation => animation.playState === 'running' || animation.pending)) return false;
        const side = sidebar.getBoundingClientRect();
        const content = main.getBoundingClientRect();
        return innerWidth < 1100
            ? sidebar.getAttribute('aria-hidden') === 'true' && side.right <= 1
                && content.left <= 1
            : sidebar.getAttribute('aria-hidden') === 'false' && side.left >= -1
                && content.left >= side.right - 1;
    }""")
    geometry = page.evaluate("""() => {
        const sidebar = document.querySelector('#application-sidebar');
        const side = sidebar.getBoundingClientRect();
        const main = document.querySelector('.main').getBoundingClientRect();
        return {viewport: innerWidth, sidebarHidden: sidebar.getAttribute('aria-hidden'),
            sidebarLeft: side.left, sidebarRight: side.right,
            mainLeft: main.left, mainRight: main.right};
    }""")
    if geometry["viewport"] < 1100:
        assert geometry["sidebarHidden"] == "true", geometry
        assert geometry["sidebarRight"] <= 1 and geometry["mainLeft"] <= 1, geometry
        expect(page.locator(".mobile-menu-toggle")).to_have_attribute(
            "aria-expanded", "false"
        )
    else:
        assert geometry["sidebarHidden"] == "false", geometry
        assert geometry["mainLeft"] >= geometry["sidebarRight"] - 1, geometry
    assert geometry["mainRight"] <= geometry["viewport"] + 1, geometry
    return geometry


def _restore_result(page: Page, base: str, version: dict, envelope: dict) -> None:
    history = page.locator(".compact-analysis-history")
    toggle = history.locator("button[aria-expanded]")
    if toggle.get_attribute("aria-expanded") != "true":
        toggle.click()
    listed = page.request.get(
        base + "/api/v1/analysis-runs",
        params={
            "dataset_version_id": version["version_id"],
            "method_id": "quality.gage_rr",
            "limit": 3,
            "offset": 0,
        },
    )
    assert listed.status == 200
    runs = listed.json()["runs"]
    index = next(
        index
        for index, run in enumerate(runs)
        if run["analysis_id"] == envelope["analysis_id"]
    )
    items = history.locator(".compact-history-list article")
    expect(items).to_have_count(len(runs))
    with page.expect_response(
        lambda response: urlsplit(response.url).path
        == f"/api/v1/analysis-runs/{envelope['analysis_id']}/result"
    ) as restored:
        items.nth(index).locator("button").click()
    assert restored.value.status == 200
    assert restored.value.json() == envelope
