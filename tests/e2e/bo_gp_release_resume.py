"""Read-only V2 BO and mixed/lag GP checks after exact-archive restart."""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Page, expect

from app_readiness import wait_for_app_ready
from bo_gp_release_contract import digest, extension_identity, report_identity
from gp_prediction_context import _restore
from managed_reports_live import verify_prediction_html

_UUID_PATH = (
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_READ_ONLY_REPORT_POSTS = frozenset(
    {
        "/api/v1/reports/capability",
        "/api/v1/reports/source-snapshot",
        "/api/v1/reports/artifacts/query",
    }
)


def _managed(original: dict):
    yield "bo", original["bo_noise_receipt"]["managed_report"]
    yield "mixed", original["gp_extension_receipt"]["managed"]
    yield "surface", original["gp_extension_receipt"]["surface_managed"]


def _get(page: Page, base: str, path: str) -> dict:
    response = page.request.get(base + path)
    assert response.status == 200, response.text()
    return response.json()


def _forbidden(request) -> bool:
    path = urlsplit(request.url).path
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return False
    if request.method != "POST":
        return True
    if path in _READ_ONLY_REPORT_POSTS:
        return False
    if re.fullmatch(rf"/api/v1/reports/{_UUID_PATH}/download", path):
        return False
    if re.fullmatch(
        rf"/api/v1/regression-models/{_UUID_PATH}/gaussian-process-predictions", path
    ):
        body = request.post_data_json
        return not isinstance(body, dict) or body.get("save_result", False) is not False
    return True


def verify_extension_resume(
    page: Page, base: str, output: Path, original: dict
) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    expected = extension_identity(original)
    forbidden = []

    def observe(request):
        if _forbidden(request):
            forbidden.append(
                {"method": request.method, "path": urlsplit(request.url).path}
            )

    page.on("request", observe)
    try:
        bo = original["bo_noise_receipt"]
        study = _get(page, base, f"/api/v1/bayesian-studies/{bo['study_id']}")
        batch = _get(
            page,
            base,
            f"/api/v1/bayesian-studies/{bo['study_id']}/recommendation-batches/{bo['batch_id']}",
        )
        assert digest(study) == bo["study_payload_sha256"]
        assert digest(batch) == bo["stored_batch_sha256"]
        history = study["observation_history"]
        assert history["history_revision_id"] == bo["current_history_revision_id"]
        assert history["observation_history_sha256"] == bo["current_history_sha256"]
        by_trial = {row["trial_id"]: row for row in study["trials"]}
        for trial_id in bo["replicate_trial_ids"]:
            assert by_trial[trial_id]["origin"] == "replicate"
            assert (
                by_trial[trial_id]["replicate_of_trial_id"]
                == bo["replicate_parent_trial_id"]
            )
            assert by_trial[trial_id]["state"] == "completed"
        locale = page.locator("html").get_attribute("lang")
        assert locale in {"ko", "en"}
        page.goto(
            base + f"/analysis/doe/doe.bayesian_optimization?study_id={bo['study_id']}",
            wait_until="domcontentloaded",
        )
        wait_for_app_ready(page, locale, "/analysis/doe/doe.bayesian_optimization")
        expect(page.locator("#bayesian-batch-result-title")).to_be_visible()
        expect(page.locator("#bo-observation-policy")).to_have_value("exact_replicates")
        page.screenshot(path=str(output / "bo-restored.png"), full_page=True)

        gp = original["gp_extension_receipt"]
        route = "/analysis/regression/regression.gaussian_process"
        page.goto(
            base + route + f"?dataset_version_id={gp['version_id']}",
            wait_until="domcontentloaded",
        )
        wait_for_app_ready(page, locale, route)
        for envelope, owner in zip(
            gp["analyses"], expected["gp"]["analyses"], strict=True
        ):
            restored = _get(
                page, base, f"/api/v1/analysis-runs/{owner['analysis_id']}/result"
            )
            assert digest(restored["result"]) == owner["result_payload_sha256"]
            model = _get(page, base, f"/api/v1/regression-models/{owner['model_id']}")
            assert model["manifest_sha256"] == owner["manifest_sha256"]
            _restore(page, base, {"version_id": gp["version_id"]}, envelope)
            page.screenshot(
                path=str(output / f"gp-{owner['analysis_id']}-restored.png"),
                full_page=True,
            )
        for kind, response_key, request_key in (
            ("mixed", "prediction", "prediction_request"),
            ("lag", "lag_prediction", "lag_prediction_request"),
            ("surface", "surface_prediction", "surface_request"),
        ):
            stored, sent = gp[response_key], dict(gp[request_key])
            sent["save_result"] = False
            predicted = page.request.post(
                base
                + f"/api/v1/regression-models/{stored['model_id']}/gaussian-process-predictions",
                headers={"Origin": base},
                data=sent,
            )
            assert predicted.status == 200, predicted.text()
            actual = predicted.json()
            assert actual.get("saved_prediction") is None
            assert actual["model_id"] == stored["model_id"]
            assert actual["rows"] == stored["rows"], kind

        reports = []
        for kind, saved in _managed(original):
            for artifact in saved["reports"]:
                descriptor = artifact["descriptor"]
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
                assert snapshot.value.status == 200
                assert snapshot.value.json()["payload"] == saved["snapshot"]["payload"]
                with page.expect_download() as download:
                    row.get_by_role(
                        "button",
                        name="Download" if locale == "en" else "다운로드",
                        exact=True,
                    ).click()
                path = output / f"{kind}-{descriptor['export_id']}.html"
                download.value.save_as(path)
                assert path.read_bytes() == Path(artifact["path"]).read_bytes()
                assert (
                    hashlib.sha256(path.read_bytes()).hexdigest()
                    == descriptor["sha256"]
                )
            reports.extend(report_identity(kind, saved))
        assert not forbidden, forbidden
        identity = {**expected, "reports": reports}
        return {
            "schema_version": 1,
            "phase": "resume",
            "status": "succeeded",
            "identity": identity,
            "identity_sha256": digest(identity),
            "forbidden_mutation_requests": forbidden,
            "models_predicted_without_save": True,
            "exact_sources_visible": True,
        }
    finally:
        page.remove_listener("request", observe)


def verify_surface_html(page: Page, payload: dict) -> None:
    view = payload["request"]["surface_view"]
    section = page.locator('[data-report-section="surface_view"]')
    expect(section).to_be_visible()
    expect(section.locator("svg")).to_be_visible()
    columns = {column["column_id"]: column for column in payload["predictors"]}
    visible = section.inner_text()
    for column_id in (view["x_column_id"], view["y_column_id"]):
        assert columns[column_id]["display_name"] in visible
    for value in view["hold_values"].values():
        assert str(value) in visible
    assert (
        "Latent Response SD"
        if page.locator("html").get_attribute("lang") == "en"
        else "잠재 반응 표준편차"
    ) in visible
    cells = section.locator("rect[data-x][data-y][data-value]")
    assert cells.count() == view["grid_size"] ** 2
    actual = cells.evaluate_all(
        "cells => cells.map(c => ({x:+c.dataset.x,y:+c.dataset.y,value:+c.dataset.value,width:c.getBoundingClientRect().width,height:c.getBoundingClientRect().height}))"
    )
    by_id = {row["client_row_id"]: row for row in payload["result"]["rows"]}
    expected = {
        (row["values"][view["x_column_id"]], row["values"][view["y_column_id"]]): by_id[
            row["client_row_id"]
        ]["latent_standard_deviation"]
        for row in payload["request"]["rows"]
    }
    assert len(expected) == len(actual)
    for cell in actual:
        assert cell["width"] > 0 and cell["height"] > 0
        assert math.isclose(
            cell["value"], expected[(cell["x"], cell["y"])], rel_tol=1e-12, abs_tol=0
        )


def verify_extension_offline(page: Page, output: Path, original: dict) -> dict:
    reports = []
    for kind, saved in _managed(original):
        for artifact in saved["reports"]:
            path, descriptor = Path(artifact["path"]), artifact["descriptor"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == descriptor["sha256"]
            if kind == "bo":
                from bo_noise_extension import verify_bo_report_html

                verify_bo_report_html(page, path, saved["snapshot"]["payload"])
                assert page.locator("script, link[href], img[src]").count() == 0
                assert saved["source"]["study_id"] in page.locator("body").inner_text()
                plot = page.locator('[data-report-section="history_plot"] svg')
                expect(plot).to_be_visible()
                points = plot.locator("[data-x][data-y]").evaluate_all(
                    "items => items.map(p => [+p.dataset.x,+p.dataset.y])"
                )
                observations = saved["snapshot"]["payload"]["observations"]
                assert sorted(points) == sorted(
                    [
                        [row["trial_number"], row["objective_value"]]
                        for row in observations
                    ]
                )
                expect(
                    page.locator('[data-report-section="noise_summary"]')
                ).to_be_visible()
            else:
                verify_prediction_html(
                    page, path, saved["snapshot"]["payload"], descriptor["locale"]
                )
                if kind == "surface":
                    verify_surface_html(page, saved["snapshot"]["payload"])
            page.screenshot(
                path=str(output / f"extension-offline-{descriptor['export_id']}.png"),
                full_page=True,
            )
        reports.extend(report_identity(kind, saved))
    identity = {"reports": reports}
    return {
        "schema_version": 1,
        "phase": "offline",
        "status": "succeeded",
        "identity": identity,
        "identity_sha256": digest(identity),
        "forbidden_mutation_requests": [],
        "stored_surface_geometry_visible": True,
    }
