"""Pilot boundary journeys through real forms and immutable saved results.

Only synthetic data is created. This driver works against Vite or the installed
release and never imports calculation or installed application modules.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

from playwright.sync_api import Browser, Page, expect, sync_playwright

from app_readiness import diagnosed_page, wait_for_app_ready

PREFIX = "X" * 121
INITIAL_LOCALE = "if (localStorage.getItem('statistical-twin.locale') === null) localStorage.setItem('statistical-twin.locale', 'ko');"
GROUPS = (PREFIX + "-A", PREFIX + "-B", "C", "D")
GROUP_CSV = (
    "group,value,include\n"
    + "".join(
        f"{group},{10 * index + value},1\n"
        for index, group in enumerate(GROUPS)
        for value in range(1, 6)
    )
    + "excluded,999,0\n"
)
METHODS = (
    ("eda.equal_variances", "exploration", 3),
    ("hypothesis.kruskal_wallis", "hypothesis", 2),
    ("hypothesis.two_sample_t", "hypothesis", 2),
)


def digest(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode()
    ).hexdigest()


def _api(page: Page, base: str, path: str, body: dict | None = None) -> dict:
    response = (
        page.request.get(base + path)
        if body is None
        else page.request.post(base + path, data=body, headers={"Origin": base})
    )
    assert response.ok, (path, response.status, response.text())
    return response.json()


def _locale(page: Page, locale: str) -> None:
    page.locator(".language-switcher button").filter(
        has_text="KOR" if locale == "ko" else "ENG"
    ).click()
    expect(page.locator("html")).to_have_attribute("lang", locale)


def _open(page: Page, base: str, route: str, version: dict | None = None) -> None:
    query = "?dataset_version_id=" + version["version_id"] if version else ""
    page.goto(base + route + query, wait_until="domcontentloaded")
    wait_for_app_ready(page, "ko", route)
    if version:
        expect(page.locator("#active-dataset-version")).to_have_value(
            version["version_id"]
        )


def ingest(page: Page, base: str, content: str, kind: str = "paste") -> dict:
    _open(page, base, "/datasets")
    if kind == "paste":
        target = page.get_by_role("textbox", name="복사한 표 붙여넣기")
        target.focus()
        target.evaluate(
            """(element, text) => {
              const data = new DataTransfer(); data.setData('text/plain', text);
              element.dispatchEvent(new ClipboardEvent('paste', {
                bubbles: true, cancelable: true, clipboardData: data
              }));
            }""",
            content,
        )
        button = page.get_by_role("button", name="붙여넣기 데이터 등록", exact=True)
        endpoint = "/api/v1/datasets/paste"
    else:
        page.get_by_label("원본 데이터 파일").set_input_files(
            {
                "name": "synthetic-pilot.csv",
                "mimeType": "text/csv",
                "buffer": content.encode(),
            }
        )
        button = page.get_by_role("button", name="업로드", exact=True)
        endpoint = "/api/v1/datasets"
    with page.expect_response(
        lambda r: r.request.method == "POST" and urlsplit(r.url).path == endpoint
    ) as uploaded:
        button.click()
    assert uploaded.value.status == 201, uploaded.value.text()
    dataset_id = uploaded.value.json()["dataset_id"]
    expect(page.get_by_role("heading", name="파싱 옵션", exact=True)).to_be_visible()
    with page.expect_response(
        lambda r: r.request.method == "POST"
        and r.url.endswith(f"/datasets/{dataset_id}/confirm-parsing")
    ) as confirmed:
        page.get_by_role("button", name="파싱 확정 및 버전 생성", exact=True).click()
    assert confirmed.value.status == 201, confirmed.value.text()
    version = confirmed.value.json()
    expect(page.locator("#active-dataset-version")).to_have_value(version["version_id"])
    return version


def _filter(page: Page, column: str, operator: str, value: str) -> None:
    controls = page.locator(".filter-panel")
    controls.get_by_role("button", name="조건 추가", exact=True).click()
    row = controls.locator(".filter-row").last
    row.locator("select").nth(0).select_option(column)
    row.locator("select").nth(1).select_option(operator)
    row.locator("input").fill(value)


def _run(page: Page, panel, expected_status: int = 201) -> tuple[dict, dict]:
    with page.expect_response(
        lambda r: r.request.method == "POST"
        and urlsplit(r.url).path == "/api/v1/analysis-runs",
        timeout=120_000,
    ) as run:
        panel.locator("button.primary-button").first.click()
    assert run.value.status == expected_status, run.value.text()
    return run.value.json(), run.value.request.post_data_json


def _report(page: Page, base: str, envelope: dict, output: Path, locale: str) -> dict:
    analysis_id = envelope["analysis_id"]
    _locale(page, "ko")
    page.goto(
        base + "/reports?analysis_id=" + analysis_id, wait_until="domcontentloaded"
    )
    wait_for_app_ready(page, "ko", "/reports")
    _locale(page, locale)
    panel = page.locator(".report-selected-result .analysis-export-panel")
    expect(panel).to_be_visible()
    with page.expect_response(
        lambda r: r.request.method == "POST"
        and r.url.endswith(f"/analysis-runs/{analysis_id}/exports/html")
    ) as exported:
        panel.get_by_role("button", name=re.compile(r"^HTML ")).first.click()
    assert exported.value.ok, exported.value.text()
    descriptor = exported.value.json()
    with page.expect_download() as download:
        panel.get_by_role("button", name=re.compile(r"^HTML ")).last.click()
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"{envelope['method_id']}-{locale}-{analysis_id}.html"
    download.value.save_as(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == descriptor["sha256"]
    restored = _api(page, base, f"/api/v1/analysis-runs/{analysis_id}/result")
    assert restored == envelope, "Export must preserve the original result envelope"
    _locale(page, "ko")
    return {"path": str(path.resolve()), "descriptor": descriptor, "locale": locale}


def verify_pilot_groups(browser: Browser, base: str, output: Path) -> dict:
    evidence: dict = {"fixture": "synthetic", "analyses": [], "reports": []}
    with diagnosed_page(
        browser, output, "long-groups", init_script=INITIAL_LOCALE
    ) as page:
        page.set_viewport_size({"width": 1440, "height": 900})
        version = ingest(page, base, GROUP_CSV)
        columns = {
            item["display_name"]: item["column_id"] for item in version["columns"]
        }
        assert version["row_count"] == 21
        evidence["version"] = version
        for method, module, schema in METHODS:
            _open(page, base, f"/analysis/{module}/{method}", version)
            panel = page.locator(f'[data-analysis-execution="{method}"]')
            panel.locator(".option-grid select").nth(0).select_option(columns["value"])
            panel.locator(".option-grid select").nth(1).select_option(columns["group"])
            _filter(page, columns["include"], "eq", "1")
            if method.endswith("two_sample_t"):
                _filter(page, columns["value"], "lt", "30")
                failure, _ = _run(page, panel, 400)
                assert (
                    failure["error"]["code"]
                    == "two_sample_t_requires_exactly_two_groups"
                )
                expect(panel.locator(".result-table")).to_have_count(0)
                page.locator(".filter-row").last.locator("input").fill("20")
            envelope, sent = _run(page, panel)
            result = envelope["result"]
            expected = 2 if method.endswith("two_sample_t") else 4
            assert result["schema_version"] == schema
            assert len(result["groups"]) == expected
            assert [g["group_value"] for g in result["groups"]] == list(
                GROUPS[:expected]
            )
            assert [g["group_index"] for g in result["groups"]] == list(range(expected))
            assert [g["n"] for g in result["groups"]] == [5] * expected
            assert sent["filter_snapshot"]["conditions"]
            expect(panel.locator(".result-table").first).to_be_visible()
            identities = panel.locator("details[data-group-identities]")
            identities.locator(":scope > summary").click()
            for group in GROUPS[:expected]:
                expect(panel.get_by_text(group, exact=True).first).to_be_visible()
            for locale in ("en", "ko"):
                _locale(page, locale)
                for width, height in ((1440, 900), (1024, 768)):
                    page.set_viewport_size({"width": width, "height": height})
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= innerWidth + 1"
                    )
                    page.screenshot(
                        path=str(
                            output / "long-groups" / f"{method}-{locale}-{width}.png"
                        ),
                        full_page=True,
                    )
            evidence["analyses"].append(
                {"envelope": envelope, "request": sent, "sha256": digest(result)}
            )
            for locale in ("ko", "en"):
                evidence["reports"].append(
                    _report(page, base, envelope, output / "html", locale)
                )
        # Reopen exact stored results, not whichever history row happens to sort first.
        for entry in evidence["analyses"]:
            envelope = entry["envelope"]
            _open(page, base, "/reports?analysis_id=" + envelope["analysis_id"])
            expect(page.locator(".report-selected-result")).to_be_visible()
            assert (
                digest(
                    _api(
                        page,
                        base,
                        f"/api/v1/analysis-runs/{envelope['analysis_id']}/result",
                    )["result"]
                )
                == entry["sha256"]
            )
        evidence["status"] = "succeeded"
    verify_pilot_html(browser, evidence["reports"], output / "offline")
    (output / "pilot-groups.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )
    return evidence


def verify_pilot_ingestion(browser: Browser, base: str, output: Path) -> dict:
    with diagnosed_page(
        browser, output, "long-csv", init_script=INITIAL_LOCALE
    ) as page:
        version = ingest(page, base, GROUP_CSV, "csv")
        assert version["row_count"] == 21
        preview = _api(
            page,
            base,
            f"/api/v1/dataset-versions/{version['version_id']}/rows?limit=30&offset=0",
        )
        serialized = json.dumps(preview, ensure_ascii=False)
        assert GROUPS[0] in serialized and GROUPS[1] in serialized
        result = {
            "status": "succeeded",
            "fixture": "synthetic",
            "version": version,
            "full_group_names_preserved": True,
        }
        (output / "pilot-ingestion.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        return result


def verify_pilot_html(browser: Browser, reports: list[dict], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    context = browser.new_context(offline=True)
    page = context.new_page()
    network = []
    page.on(
        "request",
        lambda r: network.append(r.url)
        if urlsplit(r.url).scheme in {"http", "https"}
        else None,
    )
    try:
        for artifact in reports:
            path = Path(artifact["path"])
            assert (
                hashlib.sha256(path.read_bytes()).hexdigest()
                == artifact["descriptor"]["sha256"]
            )
            page.goto(path.as_uri(), wait_until="load")
            expect(page.locator("table").first).to_be_visible()
            for group in GROUPS[:2]:
                expect(
                    page.locator("table").get_by_text(group, exact=True).first
                ).to_be_visible()
            assert page.locator("script, link[href]").count() == 0
            page.screenshot(path=str(output / (path.stem + ".png")), full_page=True)
        assert not network
    finally:
        context.close()


def _visible_numbers(text: str) -> list[float]:
    return [
        float(value)
        for value in re.findall(
            r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?",
            text.replace(",", "").replace("\u2212", "-"),
        )
    ]


def verify_pilot_prediction(browser: Browser, base: str, output: Path) -> dict:
    from linux_release_journey import METHODS as REGRESSION_METHODS, _fit, _predict
    from managed_reports_live import verify_saved_prediction_report

    content = "yield_pct,temperature_c,pressure_bar\n" + "".join(
        f"{(2 + math.sin(i / 3) + i * .03) * 1e-6:.17g},{1e12 + i:.17g},{1000 + i * .0005:.17g}\n"
        for i in range(1, 17)
    )
    evidence: dict = {"fixture": "synthetic", "events": []}
    with diagnosed_page(
        browser, output, "small-gp", init_script=INITIAL_LOCALE
    ) as page:
        version = ingest(page, base, content)
        spec = next(
            item
            for item in REGRESSION_METHODS
            if item[0] == "regression.gaussian_process"
        )
        envelope, fit_request = _fit(page, base, version, spec)
        result = envelope["result"]
        predictor_ids = {
            item["display_name"]: item["column_id"] for item in result["predictors"]
        }
        rows = [
            {
                "client_row_id": f"gp-row-{i + 1}",
                "values": {
                    predictor_ids["temperature_c"]: 1e12 + 4 + i,
                    predictor_ids["pressure_bar"]: 1000 + (4 + i) * 0.0005,
                },
            }
            for i in range(2)
        ]
        prediction, sent = _predict(
            page, result, "gaussian_process", save=True, rows=rows
        )
        before = digest(result)
        points_before = page.locator(".gp-profile-chart circle").evaluate_all(
            "nodes => nodes.map(n => [n.getAttribute('cx'), n.getAttribute('cy')])"
        )
        assert points_before and all(
            all(value is not None and math.isfinite(float(value)) for value in point)
            for point in points_before
        )
        panel = page.locator(".gp-point-prediction")
        for locale in ("en", "ko"):
            _locale(page, locale)
            for width, height in ((1440, 900), (1024, 768)):
                page.set_viewport_size({"width": width, "height": height})
                expect(panel).to_have_attribute("data-prediction-state", "ready")
                for index, expected in enumerate(prediction["rows"]):
                    cells = panel.locator("tbody tr").nth(index).locator("td")
                    first_output = 1 + len(result["predictors"])
                    for cell_offset, name in (
                        (0, "predicted_mean"),
                        (1, "latent_standard_deviation"),
                        (3, "predictive_standard_deviation"),
                    ):
                        numbers = _visible_numbers(
                            cells.nth(first_output + cell_offset).inner_text()
                        )
                        assert len(numbers) == 1, numbers
                        stored = expected[name]
                        assert math.isfinite(stored) and 0 < abs(stored) < 0.001
                        assert numbers[0] != 0
                        # Seven significant display digits, not an inference tolerance.
                        assert math.isclose(numbers[0], stored, rel_tol=1e-6, abs_tol=0)
                    for cell_offset, name in (
                        (2, "latent_interval_95"),
                        (4, "predictive_interval_95"),
                    ):
                        numbers = _visible_numbers(
                            cells.nth(first_output + cell_offset).inner_text()
                        )
                        assert len(numbers) == 2 and numbers[0] < numbers[1], numbers
                        for shown, bound in zip(
                            numbers, ("lower", "upper"), strict=True
                        ):
                            assert math.isclose(
                                shown, expected[name][bound], rel_tol=1e-6, abs_tol=0
                            )
                headers = panel.locator("thead").inner_text()
                assert (
                    ("Latent" in headers and "Predictive" in headers)
                    if locale == "en"
                    else ("잠재" in headers and "관측" in headers)
                )
                for chart in page.locator(".gp-profile-chart .chart-frame").all():
                    labels = chart.locator(
                        ".chart-axes > g > text[text-anchor=middle]"
                    ).all_text_contents()
                    assert len(labels) >= 2 and len(set(labels)) == len(labels), labels
                    assert (
                        "NaN" not in chart.inner_html()
                        and "Infinity" not in chart.inner_html()
                    )
                assert points_before == page.locator(
                    ".gp-profile-chart circle"
                ).evaluate_all(
                    "nodes => nodes.map(n => [n.getAttribute('cx'), n.getAttribute('cy')])"
                )
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth + 1"
                ), page.evaluate("""() => ({width: innerWidth, scroll: document.documentElement.scrollWidth,
                  elements: [...document.querySelectorAll('.main *')].filter(e => {
                    const r=e.getBoundingClientRect(); return r.right > innerWidth + 1 && r.width > 0;
                  }).slice(0, 25).map(e => ({tag: e.tagName, cls: e.className,
                    right:e.getBoundingClientRect().right, width:e.getBoundingClientRect().width,
                    overflow:getComputedStyle(e).overflowX, whitespace:getComputedStyle(e).whiteSpace}))})""")
                page.screenshot(
                    path=str(output / "small-gp" / f"prediction-{locale}-{width}.png"),
                    full_page=True,
                )
        _locale(page, "ko")
        html_root = output / "html"
        html_root.mkdir(parents=True, exist_ok=True)
        diagnostics = SimpleNamespace(
            root=output,
            html_root=html_root,
            capture_page=lambda p, name: p.screenshot(
                path=str(output / name), full_page=True
            ),
            record=lambda message: evidence["events"].append(message),
        )
        saved = verify_saved_prediction_report(
            page, diagnostics, prediction, sent, family="gaussian_process"
        )
        assert (
            digest(
                _api(
                    page,
                    base,
                    f"/api/v1/analysis-runs/{envelope['analysis_id']}/result",
                )["result"]
            )
            == before
        )
        evidence.update(
            status="succeeded",
            version=version,
            envelope=envelope,
            fit_request=fit_request,
            prediction=prediction,
            request=sent,
            saved=saved,
            source_result_sha256=before,
        )
        evidence["generic_report"] = _report(page, base, envelope, html_root, "en")
    (output / "pilot-prediction.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )
    return evidence


def verify_pilot_two_variances(browser: Browser, base: str, output: Path) -> dict:
    """Both methods are submitted from the built UI, including actual preflight."""
    evidence: dict = {"fixture": "synthetic", "analyses": [], "reports": []}
    content = (
        "group,value\n"
        + "".join(f"A,{i}\n" for i in range(1, 6))
        + "".join(f"B,{i}\n" for i in (1, 3, 5, 7, 9))
    )
    with diagnosed_page(
        browser, output, "two-variances", init_script=INITIAL_LOCALE
    ) as page:
        version = ingest(page, base, content)
        columns = {
            item["display_name"]: item["column_id"] for item in version["columns"]
        }
        _open(page, base, "/analysis/quality/quality.two_variances", version)
        panel = page.locator('[data-analysis-execution="quality.two_variances"]')
        panel.locator(".option-grid").first.locator("select").nth(0).select_option(
            columns["value"]
        )
        panel.locator(".option-grid").first.locator("select").nth(1).select_option(
            columns["group"]
        )
        _locale(page, "en")
        with page.expect_response(
            lambda r: r.request.method == "POST"
            and r.url.endswith("/quality.two_variances/preflight")
        ) as checked:
            panel.get_by_role("button", name="Check groups", exact=True).click()
        preflight = checked.value.json()
        assert checked.value.ok and preflight["eligible"]
        panel.get_by_role(
            "combobox", name=re.compile(r"^Numerator group")
        ).select_option("A")
        for method, p in (("brown_forsythe", 0.189403661093321), ("normal_f", 0.208)):
            panel.locator(".option-grid").last.locator("select").first.select_option(
                method
            )
            envelope, sent = _run(page, panel)
            result = envelope["result"]
            assert sent["options"]["preflight_fingerprint"] == preflight["fingerprint"]
            assert math.isclose(
                result["test"]["p_value"], p, abs_tol=1e-12, rel_tol=1e-12
            )
            assert result["ratio_estimate"]["variance"] == 0.25
            assert result["ratio_interval"]["available"] == (method == "normal_f")
            expect(panel.locator(".result-section")).to_be_visible()
            page.screenshot(
                path=str(output / "two-variances" / (method + ".png")), full_page=True
            )
            evidence["analyses"].append(
                {
                    "envelope": envelope,
                    "request": sent,
                    "execution_evidence": "visible built/source UI form with preflight",
                }
            )
        for entry in evidence["analyses"]:
            evidence["reports"].append(
                _report(page, base, entry["envelope"], output / "html", "en")
            )
        evidence.update(status="succeeded", version=version, preflight=preflight)
    (output / "pilot-two-variances.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--kind",
        choices=("groups", "ingestion", "prediction", "two-variances"),
        default="groups",
    )
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            fn = {
                "groups": verify_pilot_groups,
                "ingestion": verify_pilot_ingestion,
                "prediction": verify_pilot_prediction,
                "two-variances": verify_pilot_two_variances,
            }[args.kind]
            fn(browser, args.base_url.rstrip("/"), args.output)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
