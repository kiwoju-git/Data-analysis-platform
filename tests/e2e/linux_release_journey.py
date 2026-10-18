"""Visible archive UI journeys; the driver never imports installed app modules."""

from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from playwright.sync_api import Page, expect, sync_playwright

from app_readiness import wait_for_app_ready
from managed_reports_live import (
    prediction_values,
    verify_prediction_html,
    verify_saved_prediction_report,
)

RequestJson = Callable[..., dict]
METHODS = (
    (
        "eda.principal_components",
        "exploration",
        ".pca-panel",
        ".pca-results",
        "분석 실행",
    ),
    (
        "regression.partial_least_squares",
        "regression",
        ".pls-regression-panel",
        ".pls-results",
        "PLS 회귀 실행",
    ),
    (
        "regression.gaussian_process",
        "regression",
        ".gp-regression-panel",
        ".gp-results",
        "Gaussian Process 회귀 실행",
    ),
)


def payload_digest(value: dict) -> str:
    """Canonical inner JSON digest, explicitly not an artifact file checksum."""
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()


class JourneyEvidence:
    def __init__(self, output: Path, runtime: dict, phase: str):
        self.root = output
        self.html_root = output / "html"
        self.html_root.mkdir(parents=True, exist_ok=True)
        self.data = {
            "schema_version": 2,
            "phase": phase,
            "runtime": runtime,
            "driver_environment": {
                "platform": platform.platform(),
                "python": sys.version,
            },
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "events": [],
            "analyses": [],
            "predictions": [],
        }
        self.save()

    def save(self) -> None:
        if self.data["status"] != "running":
            self.data.setdefault("finished_at", datetime.now(timezone.utc).isoformat())
        (self.root / "journey-evidence.json").write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    def record(self, message: str) -> None:
        self.data["events"].append(message)
        self.save()

    def capture_page(self, page: Page, name: str) -> None:
        page.screenshot(path=str(self.root / name), full_page=True)


def _open(page: Page, base: str, route: str, version_id: str | None = None) -> None:
    suffix = "?dataset_version_id=" + version_id if version_id else ""
    page.goto(base + route + suffix, wait_until="domcontentloaded")
    wait_for_app_ready(page, "ko", route)
    if version_id:
        expect(page.locator("#active-dataset-version")).to_have_value(version_id)


def _paste_version(page: Page, base: str) -> dict:
    _open(page, base, "/datasets")
    content = (
        "yield_pct\ttemperature_c\tpressure_bar\tgroup\n"
        + "\n".join(
            f"{math.sin(i/3)+.35*((i*7)%11)/4:.12f}\t{i/3:.12f}\t{((i*7)%11)/4:.12f}\t{'A' if i <= 8 else 'B'}"
            for i in range(1, 17)
        )
        + "\n"
    )
    surface = page.get_by_role("textbox", name="복사한 표 붙여넣기")
    surface.focus()
    surface.evaluate(
        """(element, value) => {
      const clipboard = new DataTransfer(); clipboard.setData('text/plain', value);
      element.dispatchEvent(new ClipboardEvent('paste', {bubbles:true, cancelable:true, clipboardData:clipboard}));
    }""",
        content,
    )
    with page.expect_response(
        lambda r: r.request.method == "POST"
        and r.url.endswith("/api/v1/datasets/paste")
    ) as uploaded:
        page.get_by_role("button", name="붙여넣기 데이터 등록", exact=True).click()
    assert uploaded.value.status == 201, uploaded.value.text()
    assert uploaded.value.request.header_value("origin") == base
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
    assert version["row_count"] == 16 and version["column_count"] == 4
    return version


def _fit(page: Page, base: str, version: dict, spec: tuple) -> tuple[dict, dict]:
    method_id, module, panel_selector, result_selector, run_label = spec
    _open(page, base, f"/analysis/{module}/{method_id}", version["version_id"])
    panel = page.locator(panel_selector)
    if module == "exploration":
        for name in ("yield_pct", "temperature_c", "pressure_bar"):
            panel.locator(".numeric-column-picker").get_by_role(
                "checkbox", name=name, exact=True
            ).check()
    else:
        panel.locator("label").filter(
            has=page.get_by_text("반응 변수", exact=True)
        ).locator("select").select_option(label="yield_pct")
        for name in ("temperature_c", "pressure_bar"):
            panel.get_by_role("group", name="예측변수", exact=True).get_by_role(
                "checkbox", name=name, exact=True
            ).check()
        panel.get_by_label("Fold 수", exact=True).fill("3")
        if method_id == "regression.partial_least_squares":
            settings = panel.locator(".pls-settings-table")
            expect(settings.locator("thead th").nth(1)).to_have_text(
                "최대 평가 성분 수"
            )
            settings.locator("tbody tr").first.locator("td").nth(1).locator(
                "input"
            ).fill("2")
        else:
            panel.get_by_text("고급 설정", exact=True).click()
            for label, value in (
                ("최종 모형 restart 수", "0"),
                ("CV restart 수", "0"),
                ("Profile 점 수", "10"),
                ("Surface grid 크기", "10"),
            ):
                panel.get_by_label(label, exact=True).fill(value)
    with page.expect_response(
        lambda r: r.request.method == "POST"
        and r.url.endswith("/api/v1/analysis-runs"),
        timeout=120_000,
    ) as fitted:
        panel.get_by_role("button", name=run_label, exact=True).click()
    assert fitted.value.status == 201, fitted.value.text()
    result = fitted.value.json()
    request = fitted.value.request.post_data_json
    assert request["method_id"] == result["method_id"] == method_id
    assert (
        request["dataset_version_id"]
        == result["dataset_version_id"]
        == version["version_id"]
    )
    expect(panel.locator(result_selector)).to_be_visible(timeout=120_000)
    return result, request


def _predict(
    page: Page, result: dict, family: str, *, save: bool, rows: list | None = None
) -> tuple[dict, dict]:
    selector, endpoint = (
        (".pls-point-prediction", "/pls-point-predictions")
        if family == "pls"
        else (".gp-point-prediction", "/gaussian-process-predictions")
    )
    panel = page.locator(selector)
    expect(panel).to_be_visible()
    predictors = result["predictors"]
    count = 2 if rows is None else len(rows)
    for _ in range(count - 1):
        panel.get_by_role("button", name="행 추가", exact=True).click()
    for index in range(count):
        for predictor in predictors:
            value = (
                (
                    2.0 + index * 0.5
                    if predictor["display_name"] == "temperature_c"
                    else 1.0 + index * 0.25
                )
                if rows is None
                else rows[index]["values"][predictor["column_id"]]
            )
            panel.get_by_label(
                f"{predictor['display_name']} {index+1}", exact=True
            ).fill(str(value))
    checkbox = panel.locator("[data-save-completed-prediction]")
    expect(checkbox).not_to_be_checked()
    if save:
        checkbox.check()
    with page.expect_response(
        lambda r: r.request.method == "POST" and r.url.endswith(endpoint)
    ) as completed:
        panel.get_by_role(
            "button", name="점예측 실행" if family == "pls" else "예측 실행", exact=True
        ).click()
    assert completed.value.status == 200, completed.value.text()
    prediction, request = completed.value.json(), completed.value.request.post_data_json
    assert request.get("save_result", False) == save
    if rows is not None:
        assert request["rows"] == rows
    assert prediction["model_id"] == result["model_manifest"]["model_id"]
    assert (
        request["expected_model_manifest_sha256"]
        == result["model_manifest"]["manifest_sha256"]
    )
    assert len({row["client_row_id"] for row in prediction["rows"]}) == count
    assert {row["client_row_id"] for row in prediction["rows"]} == {
        row["client_row_id"] for row in request["rows"]
    }
    for row in prediction["rows"]:
        assert all(math.isfinite(value) for value in prediction_values(row, family))
    expect(panel).to_have_attribute("data-prediction-state", "ready")
    return prediction, request


def _capture_failure(page: Page, evidence: JourneyEvidence) -> None:
    evidence.data["status"] = "failed"
    evidence.save()
    evidence.capture_page(page, "failure.png")
    (evidence.root / "failure.html").write_text(page.content(), encoding="utf-8")


def _download_local_snapshot(
    page: Page,
    output: Path,
    family: str,
    analysis_id: str,
    request: dict,
    response: dict,
) -> dict:
    """The browser snapshot is not the server-persisted completed-prediction artifact."""
    endpoint_calls = []

    def capture(sent):
        if sent.method == "POST":
            endpoint_calls.append(sent.url)

    page.on("request", capture)
    try:
        with page.expect_download() as downloaded:
            page.locator('[data-action="download-prediction-snapshot"]').click()
        path = output / f"local-{family}-prediction-snapshot.json"
        downloaded.value.save_as(path)
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        assert snapshot["source_analysis_id"] == analysis_id
        assert snapshot["artifact_kind"] == (
            "pls_point_prediction_snapshot"
            if family == "pls"
            else "gaussian_process_point_prediction_snapshot"
        )
        assert snapshot["prediction_recalculated_on_export"] is False
        assert snapshot["request"] == request
        assert snapshot["response"]["rows"] == response["rows"]
        assert snapshot["response"]["model_id"] == response["model_id"]
        assert (
            snapshot["response"]["model_manifest_sha256"]
            == response["model_manifest_sha256"]
        )
        assert snapshot["response"].get("saved_prediction") == response.get(
            "saved_prediction"
        )
        assert not endpoint_calls, endpoint_calls
        return {
            "path": str(path.resolve()),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "snapshot": snapshot,
            "post_count": 0,
        }
    finally:
        page.remove_listener("request", capture)


def run_initial(base: str, output: Path, request: RequestJson) -> dict:
    runtime = request(base, "/api/v1/runtime-info")
    evidence = JourneyEvidence(output, runtime, "initial")
    evidence.data["access_origin"] = base
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        evidence.data["driver_environment"]["chromium"] = browser.version
        context = browser.new_context(
            viewport={"width": 1440, "height": 900}, accept_downloads=True
        )
        context.add_init_script(
            "if (!localStorage.getItem('statistical-twin.locale')) localStorage.setItem('statistical-twin.locale','ko')"
        )
        context.tracing.start(screenshots=True, snapshots=True, sources=False)
        page = context.new_page()
        fit_calls = []
        page.on(
            "request",
            lambda r: fit_calls.append(r.post_data_json)
            if r.method == "POST" and urlsplit(r.url).path == "/api/v1/analysis-runs"
            else None,
        )
        try:
            _open(page, base, "/home")
            expect(
                page.get_by_role("heading", name="Statistical Twin", exact=True)
            ).to_be_visible()
            evidence.capture_page(page, "release-home.png")
            browser_runtime = page.evaluate(
                "async () => (await fetch('/api/v1/runtime-info')).json()"
            )
            assert browser_runtime["build_commit"] == runtime["build_commit"]
            version = _paste_version(page, base)
            evidence.data["dataset_version_id"] = version["version_id"]
            evidence.data["version"] = version
            evidence.data["browser_same_origin_mutation"] = True
            evidence.record(
                "Visible paste and parsing confirmation created the synthetic dataset version."
            )
            for spec in METHODS:
                result, fit_request = _fit(page, base, version, spec)
                analysis = {
                    "method_id": spec[0],
                    "analysis_id": result["analysis_id"],
                    "request": fit_request,
                    "envelope": result,
                    "result_payload_sha256": payload_digest(result["result"]),
                }
                assert (
                    request(
                        base, f"/api/v1/analysis-runs/{result['analysis_id']}/result"
                    )["result"]
                    == result["result"]
                )
                evidence.data["analyses"].append(analysis)
                evidence.capture_page(page, spec[0] + ".png")
                evidence.record("Visible analysis completed: " + spec[0])
                if spec[0].startswith("regression."):
                    family = (
                        "pls"
                        if spec[0].endswith("partial_least_squares")
                        else "gaussian_process"
                    )
                    pointer = result["result"]["model_manifest"]
                    manifest = request(
                        base, f"/api/v1/regression-models/{pointer['model_id']}"
                    )
                    assert manifest["manifest_sha256"] == pointer["manifest_sha256"]
                    analysis["model_manifest"] = manifest
                    prediction, prediction_request = _predict(
                        page, result["result"], family, save=True
                    )
                    local_snapshot = _download_local_snapshot(
                        page,
                        output,
                        family,
                        result["analysis_id"],
                        prediction_request,
                        prediction,
                    )
                    saved = verify_saved_prediction_report(
                        page,
                        evidence,
                        prediction,
                        prediction_request,
                        family=family,
                        open_offline=False,
                    )
                    saved["analysis_id"] = result["analysis_id"]
                    saved["local_json_snapshot"] = local_snapshot
                    evidence.data["predictions"].append(saved)
                    evidence.save()
            route = "/analysis/quality/quality.two_variances"
            _open(page, base, route, version["version_id"])
            page.reload(wait_until="domcontentloaded")
            wait_for_app_ready(page, "ko", route)
            expect(
                page.locator('[data-analysis-execution="quality.two_variances"]')
            ).to_be_visible()
            expect(page.locator(".error-box[role=alert]")).to_have_count(0)
            evidence.record(
                "Two Variances direct route and refresh render the actual panel; execution is separately API-tested."
            )
            assert len(fit_calls) == 3
            evidence.data["ui_analysis_post_count"] = len(fit_calls)
            evidence.data["status"] = "succeeded"
            evidence.record(
                "Three visible analysis submissions completed; managed report export did not submit another analysis."
            )
            return evidence.data
        except Exception:
            _capture_failure(page, evidence)
            raise
        finally:
            context.tracing.stop(path=str(output / "journey-trace.zip"))
            context.close()
            browser.close()


def _restore_analysis(page: Page, base: str, version_id: str, analysis: dict) -> None:
    spec = next(item for item in METHODS if item[0] == analysis["method_id"])
    route = f"/analysis/{spec[1]}/{spec[0]}"
    _open(page, base, route, version_id)
    page.reload(wait_until="domcontentloaded")
    wait_for_app_ready(page, "ko", route)
    expect(page.locator("#active-dataset-version")).to_have_value(version_id)
    history = page.locator(".compact-analysis-history")
    history.get_by_role("button", name="최근 이력 열기", exact=True).click()
    row = history.locator(".compact-history-list article").filter(
        has_text=analysis["method_id"]
    )
    expect(row).to_have_count(1)
    with page.expect_response(
        lambda r: r.request.method == "GET"
        and r.url.endswith(f"/analysis-runs/{analysis['analysis_id']}/result")
    ) as restored:
        row.get_by_role("button", name="결과 불러오기", exact=True).click()
    assert restored.value.status == 200
    assert restored.value.json()["result"] == analysis["envelope"]["result"]
    expect(page.locator(spec[2]).locator(spec[3])).to_be_visible()


def run_pilot_initial(base: str, output: Path, legacy_seed: dict) -> dict:
    """Additional built-UI evidence stays separate from the original release gate."""
    from pilot_edge_cases import (
        verify_pilot_groups,
        verify_pilot_ingestion,
        verify_pilot_prediction,
        verify_pilot_two_variances,
    )

    output.mkdir(parents=True, exist_ok=True)
    receipt = {"schema_version": 1, "status": "running", "phase": "initial"}
    path = output / "pilot-receipt.json"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            for name, verify in (
                ("ingestion", verify_pilot_ingestion),
                ("groups", verify_pilot_groups),
                ("prediction", verify_pilot_prediction),
                ("two_variances", verify_pilot_two_variances),
            ):
                receipt[name] = verify(browser, base, output / name)
                assert receipt[name]["status"] == "succeeded"
                path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            receipt["legacy"] = verify_pilot_legacy(
                browser, base, output / "legacy", legacy_seed
            )
            receipt["status"] = "succeeded"
            return receipt
        except Exception:
            receipt["status"] = "failed"
            raise
        finally:
            path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            browser.close()


def pilot_analyses(receipt: dict) -> list[dict]:
    assert receipt["schema_version"] == 1 and receipt["status"] == "succeeded"
    return [
        *receipt["groups"]["analyses"],
        *receipt["two_variances"]["analyses"],
        {"envelope": receipt["prediction"]["envelope"]},
        *receipt["legacy"]["analyses"],
    ]


def pilot_reports(receipt: dict) -> list[dict]:
    return [
        *receipt["groups"]["reports"],
        *receipt["two_variances"]["reports"],
        receipt["prediction"]["generic_report"],
        *receipt["prediction"]["saved"]["reports"],
        *receipt["legacy"]["reports"],
    ]


def _restore_group_analysis(page: Page, base: str, envelope: dict) -> None:
    method = envelope["method_id"]
    module = "exploration" if method.startswith("eda.") else "hypothesis"
    route = f"/analysis/{module}/{method}"
    _open(page, base, route, envelope["dataset_version_id"])
    history = page.locator(".compact-analysis-history")
    history.get_by_role("button", name="최근 이력 열기", exact=True).click()
    row = history.locator(".compact-history-list article").filter(has_text=method)
    expect(row).to_have_count(1)
    with page.expect_response(
        lambda r: r.request.method == "GET"
        and r.url.endswith(f"/analysis-runs/{envelope['analysis_id']}/result")
    ) as restored:
        row.get_by_role("button", name="결과 불러오기", exact=True).click()
    assert restored.value.json() == envelope
    expect(
        page.locator(
            f'[data-analysis-execution="{method}"] [data-group-identity-legacy]'
        )
    ).to_be_visible()


def verify_pilot_legacy(browser, base: str, output: Path, seed: dict) -> dict:
    from pilot_edge_cases import _api, _locale, _report

    assert seed["status"] == "seeded_new_workspace"
    assert (
        seed["existing_records_modified"] is False
        and seed["analysis_calculations_executed"] == 0
    )
    output.mkdir(parents=True, exist_ok=True)
    receipt = {"status": "running", "seed": seed, "analyses": [], "reports": []}
    context = browser.new_context(
        accept_downloads=True, viewport={"width": 1440, "height": 900}
    )
    context.add_init_script(
        "if (!localStorage.getItem('statistical-twin.locale')) localStorage.setItem('statistical-twin.locale','ko')"
    )
    context.tracing.start(screenshots=True, snapshots=True, sources=False)
    page = context.new_page()
    fit_calls = []
    page.on(
        "request",
        lambda r: fit_calls.append(r.url)
        if r.method == "POST" and urlsplit(r.url).path == "/api/v1/analysis-runs"
        else None,
    )
    try:
        for case in seed["cases"]:
            envelope = _api(
                page, base, f"/api/v1/analysis-runs/{case['analysis_id']}/result"
            )
            assert (
                envelope["method_id"] == case["method_id"]
                and envelope["method_version"] == case["method_version"]
            )
            assert payload_digest(envelope["result"]) == case["result_payload_sha256"]
            assert envelope["result"]["schema_version"] == case["result_schema_version"]
            _restore_group_analysis(page, base, envelope)
            receipt["analyses"].append({"envelope": envelope, "seed": case})
            for locale in ("ko", "en"):
                _locale(page, locale)
                expect(page.locator("[data-group-identity-legacy]")).to_be_visible()
                page.screenshot(
                    path=str(output / f"{case['method_id']}-{locale}.png"),
                    full_page=True,
                )
            _locale(page, "ko")
            for locale in ("ko", "en"):
                artifact = _report(page, base, envelope, output, locale)
                assert (
                    artifact["descriptor"]["source_result_sha256"]
                    == case["artifact_file_sha256"]
                )
                receipt["reports"].append(artifact)
        assert not fit_calls
        receipt.update(status="succeeded", analysis_post_count=0)
        return receipt
    finally:
        context.tracing.stop(path=str(output / "legacy-trace.zip"))
        context.close()


def restore_pilot(
    page: Page, base: str, output: Path, original: dict, request: RequestJson
) -> dict:
    """Read saved pilot sources and download the original report, never export again."""
    output.mkdir(parents=True, exist_ok=True)
    receipt = {"schema_version": 1, "phase": "resume", "analyses": [], "reports": []}
    for entry in pilot_analyses(original):
        envelope = entry["envelope"]
        analysis_id = envelope["analysis_id"]
        restored = request(base, f"/api/v1/analysis-runs/{analysis_id}/result")
        assert restored == envelope
        if "seed" in entry:
            _restore_group_analysis(page, base, envelope)
            capability = request(
                base, f"/api/v1/analysis-runs/{analysis_id}/report-capability?locale=en"
            )
            assert (
                capability["source_result_sha256"]
                == entry["seed"]["artifact_file_sha256"]
            )
        receipt["analyses"].append(
            {
                "analysis_id": analysis_id,
                "result_payload_sha256": payload_digest(restored["result"]),
            }
        )
    prediction = original["prediction"]
    envelope = prediction["envelope"]
    _restore_analysis(
        page,
        base,
        prediction["version"]["version_id"],
        {
            "method_id": envelope["method_id"],
            "analysis_id": envelope["analysis_id"],
            "envelope": envelope,
        },
    )
    saved = prediction["saved"]
    pointer = envelope["result"]["model_manifest"]
    manifest = request(base, f"/api/v1/regression-models/{pointer['model_id']}")
    assert manifest["manifest_sha256"] == pointer["manifest_sha256"]
    completed, sent = _predict(
        page,
        envelope["result"],
        "gaussian_process",
        save=False,
        rows=saved["request"]["rows"],
    )
    assert completed.get("saved_prediction") is None
    assert sent["rows"] == saved["request"]["rows"]
    assert completed["rows"] == saved["prediction"]["rows"]
    receipt["prediction"] = {
        "manifest_sha256": manifest["manifest_sha256"],
        "rows": completed["rows"],
        "same_saved_model_prediction": True,
    }
    for artifact in pilot_reports(original):
        descriptor = artifact["descriptor"]
        locale = artifact.get("locale", descriptor.get("locale", "en"))
        page.locator(".language-switcher button").filter(
            has_text="ENG" if locale == "en" else "KOR"
        ).click()
        managed = artifact in saved["reports"]
        route = (
            f"/reports?report_id={descriptor['export_id']}"
            if managed
            else f"/reports?analysis_id={descriptor['analysis_id']}"
        )
        page.goto(base + route, wait_until="domcontentloaded")
        wait_for_app_ready(page, locale, "/reports")
        if managed:
            selected = page.locator(
                f'[data-managed-report-selection="{saved["source_ref_sha256"]}"]'
            )
            row = selected.locator(f'[data-managed-report="{descriptor["export_id"]}"]')
            with page.expect_response(
                lambda r: r.request.method == "POST"
                and r.url.endswith("/reports/source-snapshot")
            ) as snapshot:
                selected.locator("[data-view-stored-source]").click()
            assert snapshot.value.json()["payload"] == saved["snapshot"]["payload"]
        else:
            selected = page.locator(".report-center-selected .analysis-export-panel")
            row = selected.locator(".export-list-item").filter(
                has_text=descriptor["sha256"][:12]
            )
        expect(row).to_have_count(1)
        with page.expect_download() as download:
            row.get_by_role(
                "button", name="Download" if locale == "en" else "다운로드", exact=True
            ).click()
        path = output / f"{descriptor['export_id']}.html"
        download.value.save_as(path)
        assert path.read_bytes() == Path(artifact["path"]).read_bytes()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == descriptor["sha256"]
        receipt["reports"].append(
            {"export_id": descriptor["export_id"], "sha256": descriptor["sha256"]}
        )
    page.locator(".language-switcher button").filter(has_text="KOR").click()
    receipt["status"] = "succeeded"
    return receipt


def verify_pilot_offline(page: Page, output: Path, receipt: dict) -> dict:
    """Called in the existing server-stopped/offline context, including pilot HTML."""
    from pilot_edge_cases import GROUPS

    checks = []
    saved = receipt["prediction"]["saved"]
    for artifact in pilot_reports(receipt):
        descriptor = artifact["descriptor"]
        path = Path(artifact["path"])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == descriptor["sha256"]
        if artifact in saved["reports"]:
            verify_prediction_html(
                page, path, saved["snapshot"]["payload"], descriptor["locale"]
            )
        else:
            page.goto(path.resolve().as_uri())
            expect(page.locator("table").first).to_be_visible()
            if (
                artifact in receipt["two_variances"]["reports"]
                or artifact == receipt["prediction"]["generic_report"]
            ):
                expect(page.locator("svg").first).to_be_visible()
            if artifact in receipt["groups"]["reports"]:
                for group in GROUPS[:2]:
                    expect(
                        page.locator("table").get_by_text(group, exact=True).first
                    ).to_be_visible()
            if artifact in receipt["legacy"]["reports"]:
                notice = (
                    "Stored labels" if artifact["locale"] == "en" else "저장된 라벨"
                )
                expect(
                    page.locator("[data-report-section]").filter(has_text=notice).first
                ).to_be_visible()
            assert page.locator("script, link[href], img[src]").count() == 0
        page.screenshot(
            path=str(output / f"pilot-offline-{descriptor['export_id']}.png"),
            full_page=True,
        )
        checks.append(
            {"export_id": descriptor["export_id"], "sha256": descriptor["sha256"]}
        )
    return {
        "schema_version": 1,
        "phase": "offline",
        "status": "succeeded",
        "reports": checks,
    }


def run_resume(base: str, output: Path, original: dict, request: RequestJson) -> dict:
    runtime = request(base, "/api/v1/runtime-info")
    for field in (
        "service",
        "build_commit",
        "api_contract_version",
        "metadata_schema_version",
        "capabilities",
    ):
        assert runtime[field] == original["runtime"][field]
    evidence = JourneyEvidence(output, runtime, "resume")
    evidence.data["access_origin"] = base
    evidence.data["initial_access_origin"] = original["access_origin"]
    evidence.data["dataset_version_id"] = original["dataset_version_id"]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        evidence.data["driver_environment"]["chromium"] = browser.version
        context = browser.new_context(
            viewport={"width": 1440, "height": 900}, accept_downloads=True
        )
        context.add_init_script(
            "if (!localStorage.getItem('statistical-twin.locale')) localStorage.setItem('statistical-twin.locale','ko')"
        )
        context.tracing.start(screenshots=True, snapshots=True, sources=False)
        page = context.new_page()
        fit_calls = []
        page.on(
            "request",
            lambda r: fit_calls.append(r.url)
            if r.method == "POST" and urlsplit(r.url).path == "/api/v1/analysis-runs"
            else None,
        )
        try:
            for analysis in original["analyses"]:
                restored = request(
                    base, f"/api/v1/analysis-runs/{analysis['analysis_id']}/result"
                )
                assert (
                    payload_digest(restored["result"])
                    == analysis["result_payload_sha256"]
                )
                capability = request(
                    base,
                    f"/api/v1/analysis-runs/{analysis['analysis_id']}/report-capability?locale=en",
                )
                if "source_result_artifact_sha256" in analysis:
                    assert (
                        capability["source_result_sha256"]
                        == analysis["source_result_artifact_sha256"]
                    )
                evidence.data["analyses"].append(
                    {
                        "analysis_id": analysis["analysis_id"],
                        "method_id": analysis["method_id"],
                        "result_payload_sha256": payload_digest(restored["result"]),
                        "source_result_artifact_sha256": capability[
                            "source_result_sha256"
                        ],
                    }
                )
                if analysis["method_id"] not in {spec[0] for spec in METHODS}:
                    continue
                _restore_analysis(page, base, original["dataset_version_id"], analysis)
                evidence.capture_page(page, analysis["method_id"] + "-restored.png")
                if analysis.get("model_manifest") is None:
                    continue
                saved = next(
                    item
                    for item in original["predictions"]
                    if item["analysis_id"] == analysis["analysis_id"]
                )
                manifest = analysis["model_manifest"]
                current = request(
                    base, f"/api/v1/regression-models/{manifest['model_id']}"
                )
                assert current["manifest_sha256"] == manifest["manifest_sha256"]
                assert current["manifest"] == manifest["manifest"]
                response, sent = _predict(
                    page,
                    analysis["envelope"]["result"],
                    saved["family"],
                    save=False,
                    rows=saved["request"]["rows"],
                )
                assert response.get("saved_prediction") is None
                assert sent["rows"] == saved["request"]["rows"]
                local_snapshot = _download_local_snapshot(
                    page,
                    output,
                    saved["family"],
                    analysis["analysis_id"],
                    sent,
                    response,
                )
                original_by_id = {
                    row["client_row_id"]: row for row in saved["prediction"]["rows"]
                }
                for row in response["rows"]:
                    # Same installed model and request: compare complete stored values exactly.
                    assert prediction_values(row, saved["family"]) == prediction_values(
                        original_by_id[row["client_row_id"]], saved["family"]
                    )
                    assert row.get("warnings") == original_by_id[
                        row["client_row_id"]
                    ].get("warnings")
                evidence.data["predictions"].append(
                    {
                        "family": saved["family"],
                        "request": sent,
                        "prediction": response,
                        "manifest_sha256": current["manifest_sha256"],
                        "local_json_snapshot": local_snapshot,
                    }
                )
                for artifact in saved["reports"]:
                    descriptor = artifact["descriptor"]
                    locale = descriptor["locale"]
                    page.locator(".language-switcher button").filter(
                        has_text="ENG" if locale == "en" else "KOR"
                    ).click()
                    page.goto(
                        base + f"/reports?report_id={descriptor['export_id']}",
                        wait_until="domcontentloaded",
                    )
                    wait_for_app_ready(page, locale, "/reports")
                    selected = page.locator(
                        f'[data-managed-report-selection="{saved["source_ref_sha256"]}"]'
                    )
                    row = selected.locator(
                        f'[data-managed-report="{descriptor["export_id"]}"]'
                    )
                    expect(row).to_be_visible()
                    with page.expect_response(
                        lambda r: r.request.method == "POST"
                        and r.url.endswith("/reports/source-snapshot")
                    ) as snapshot:
                        selected.locator("[data-view-stored-source]").click()
                    assert (
                        snapshot.value.json()["payload"] == saved["snapshot"]["payload"]
                    )
                    with page.expect_download() as download:
                        row.get_by_role(
                            "button",
                            name="Download" if locale == "en" else "다운로드",
                            exact=True,
                        ).click()
                    path = (
                        evidence.html_root / f"restored-{saved['family']}-{locale}.html"
                    )
                    download.value.save_as(path)
                    assert path.read_bytes() == Path(artifact["path"]).read_bytes()
                    assert (
                        hashlib.sha256(path.read_bytes()).hexdigest()
                        == descriptor["sha256"]
                    )
                page.locator(".language-switcher button").filter(has_text="KOR").click()
                evidence.record(
                    "Restored model, exact point inputs/outputs and report bytes: "
                    + saved["family"]
                )
            evidence.data["pilot_receipt"] = restore_pilot(
                page, base, output / "pilot", original["pilot_receipt"], request
            )
            assert not fit_calls, fit_calls
            evidence.data["analysis_post_count"] = 0
            evidence.data["status"] = "succeeded"
            evidence.save()
            return evidence.data
        except Exception:
            _capture_failure(page, evidence)
            raise
        finally:
            context.tracing.stop(path=str(output / "journey-trace.zip"))
            context.close()
            browser.close()


def run_offline(output: Path, original: dict) -> dict:
    checks = []
    started_at = datetime.now(timezone.utc).isoformat()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(
            offline=True, viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        network_requests = []
        page.on(
            "request",
            lambda r: network_requests.append(r.url)
            if urlsplit(r.url).scheme in ("http", "https")
            else None,
        )
        try:
            for saved in original["predictions"]:
                for artifact in saved["reports"]:
                    descriptor = artifact["descriptor"]
                    path = Path(artifact["path"])
                    assert (
                        hashlib.sha256(path.read_bytes()).hexdigest()
                        == descriptor["sha256"]
                    )
                    verify_prediction_html(
                        page, path, saved["snapshot"]["payload"], descriptor["locale"]
                    )
                    page.screenshot(
                        path=str(
                            output
                            / f"offline-{saved['family']}-{descriptor['locale']}.png"
                        ),
                        full_page=True,
                    )
                    checks.append(
                        {
                            "family": saved["family"],
                            "locale": descriptor["locale"],
                            "sha256": descriptor["sha256"],
                        }
                    )
            for analysis in original["analyses"]:
                artifact = analysis.get("generic_report")
                if artifact is None:
                    continue
                path = Path(artifact["path"])
                assert (
                    hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
                )
                page.goto(path.resolve().as_uri())
                expect(page.locator("svg").first).to_be_visible()
                assert page.locator("table").count() > 0
                assert page.locator("script, link[href], img[src]").count() == 0
            pilot_receipt = verify_pilot_offline(
                page, output, original["pilot_receipt"]
            )
            assert not network_requests, network_requests
            return {
                "schema_version": 2,
                "status": "succeeded",
                "phase": "offline",
                "started_at": started_at,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "driver_environment": {
                    "platform": platform.platform(),
                    "python": sys.version,
                    "chromium": browser.version,
                },
                "reports": checks,
                "pilot_receipt": pilot_receipt,
                "http_request_count": 0,
                "browser_network_offline": True,
            }
        finally:
            context.close()
            browser.close()
