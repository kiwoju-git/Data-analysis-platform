"""Synthetic, visible BO V2 journeys shared by native CI and the exact archive."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Browser, Page, Route, expect

from app_readiness import diagnosed_page, wait_for_app_ready, wait_for_layout_settled

ROUTE = "/analysis/doe/doe.bayesian_optimization"
_INITIAL_LOCALE = """if (localStorage.getItem('statistical-twin.locale') === null) {
    localStorage.setItem('statistical-twin.locale', 'ko');
}"""

_RECEIPT_CHECKS = (
    "q1_target_ui",
    "joint_batch_ui",
    "replicate_ui",
    "individual_observations_ui",
    "exact_aggregation_ui",
    "legacy_observations_unchanged",
    "restore_ui",
    "locale_resize_restore_do_not_post",
    "committed_post_replayed_only_by_explicit_action",
    "same_request_id_payload",
    "no_duplicate_trials",
    "history_unchanged",
)


def _record_receipt(output: Path, receipt: dict) -> dict:
    """Persist allowlisted test evidence without changing the archive receipt contract."""
    assert receipt["schema_version"] == 1 and receipt["synthetic"] is True
    assert receipt["status"] == "succeeded"
    checks = {}
    for key in _RECEIPT_CHECKS:
        if key in receipt:
            assert receipt[key] is True
            checks[key] = True
    assert checks
    counts = {}
    for key in ("raw_n", "effective_n"):
        if key in receipt:
            value = receipt[key]
            assert type(value) is int and 0 <= value <= 200
            counts[key] = value
    viewports = []
    for view in receipt.get("locales_viewports", []):
        assert view["locale"] in {"ko", "en"}
        assert type(view["width"]) is int and view["width"] in {1024, 1440}
        viewports.append({"locale": view["locale"], "width": view["width"]})
    safe = {
        "schema_version": 1,
        "synthetic": True,
        "status": "succeeded",
        "checks": checks,
        "counts": counts,
        "locales_viewports": viewports,
    }
    if "layout_geometry" in receipt:
        geometry = []
        for item in receipt["layout_geometry"]:
            assert item["locale"] in {"ko", "en"}
            assert item["width"] in {1024, 1440}
            assert type(item["sidebar_hidden"]) is bool
            record = {
                "locale": item["locale"],
                "width": item["width"],
                "sidebar_hidden": item["sidebar_hidden"],
            }
            for key in (
                "main_left",
                "main_right",
                "sidebar_right",
                "title_left",
                "title_right",
                "control_left",
                "control_right",
            ):
                assert type(item[key]) in (int, float) and math.isfinite(item[key])
                record[key] = item[key]
            geometry.append(record)
        safe["layout_geometry"] = geometry
    output.mkdir(parents=True, exist_ok=True)
    (output / "bo-validation-receipt.json").write_text(
        json.dumps(safe, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return receipt


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def _settled_layout(page: Page) -> dict:
    wait_for_layout_settled(page)
    geometry = page.evaluate("""() => {
        const rect = selector => document.querySelector(selector).getBoundingClientRect();
        const main = rect('main.main'), sidebar = rect('#application-sidebar');
        const title = rect('#bayesian-batch-result-title'), control = rect('#bo-noise-mode');
        return {width: document.documentElement.clientWidth,
            main_left: main.left, main_right: main.right,
            sidebar_right: sidebar.right,
            sidebar_hidden: document.querySelector('#application-sidebar').getAttribute('aria-hidden') === 'true',
            title_left: title.left, title_right: title.right,
            control_left: control.left, control_right: control.right};
    }""")
    width = geometry["width"]
    assert geometry["main_left"] >= -1 and geometry["main_right"] <= width + 1, geometry
    for name in ("title", "control"):
        assert geometry[f"{name}_left"] >= max(0, geometry["main_left"]) - 1, geometry
        assert (
            geometry[f"{name}_right"] <= min(width, geometry["main_right"]) + 1
        ), geometry
    if width < 1100:
        assert geometry["sidebar_hidden"] and geometry["sidebar_right"] <= 1, geometry
    else:
        assert not geometry["sidebar_hidden"], geometry
        assert geometry["sidebar_right"] <= geometry["main_left"] + 1, geometry
    return geometry


def _seed(page: Page, base: str) -> dict:
    created = page.request.post(
        base + "/api/v1/bayesian-studies",
        headers={"Origin": base},
        data={
            "name": "Synthetic noise-aware target study",
            "factors": [
                {
                    "factor_id": "x",
                    "name": "Synthetic input",
                    "low": 0,
                    "high": 1,
                    "unit": None,
                }
            ],
            "objective": {
                "name": "Synthetic response",
                "unit": "mg",
                "goal_type": "match_target",
                "target_value": 1.5,
                "target_tolerance": 0.05,
                "observation_policy": "manual_single_observation",
            },
            "constraints": [],
            "initial_design_seed": 17,
            "initial_design_size": 4,
        },
    )
    assert created.status == 201, created.text()
    study = created.json()
    revision = study["observation_history"]["history_revision_id"]
    for index, trial in enumerate(study["trials"]):
        saved = page.request.put(
            base
            + f"/api/v1/bayesian-studies/{study['study_id']}/trials/{trial['trial_id']}/observation",
            headers={"Origin": base},
            data={
                "objective_value": 1
                + 2 * trial["actual_coordinates"]["x"]
                + 0.01 * (index % 2),
                "expected_history_revision_id": revision,
            },
        )
        assert saved.status == 200, saved.text()
        revision = saved.json()["observation_history"]["history_revision_id"]
    return _study(page, base, study["study_id"])


def _study(page: Page, base: str, study_id: str) -> dict:
    response = page.request.get(base + f"/api/v1/bayesian-studies/{study_id}")
    assert response.status == 200
    return response.json()


def _open(page: Page, base: str, study_id: str) -> None:
    page.goto(base + ROUTE + f"?study_id={study_id}", wait_until="domcontentloaded")
    wait_for_app_ready(page, "ko", ROUTE)
    expect(page.locator("#bo-noise-mode")).to_be_enabled(timeout=20_000)


def _recommend(page: Page) -> dict:
    button = page.get_by_role("button", name="추천 batch 생성", exact=True)
    expect(button).to_be_enabled(timeout=20_000)
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and urlsplit(response.url).path.endswith("/recommendation-batches"),
        timeout=90_000,
    ) as response:
        button.click()
    assert response.value.status == 201, response.value.text()
    payload = response.value.request.post_data_json
    result = response.value.json()
    assert (
        payload["schema_version"] == 2 and len(payload["expected_history_sha256"]) == 64
    )
    assert result["result_schema_version"] == 2
    assert result["batch_policy"] == "greedy_mc_joint_latent_improvement_v2"
    assert result["acquisition"]["kind"] == "expected_target_improvement"
    expect(page.locator("#bayesian-batch-result-title")).to_be_visible()
    for item in result["items"]:
        assert (
            item["trial"]["state"] == "pending"
            and item["trial"]["objective_value"] is None
        )
        assert math.isfinite(item["latent_standard_deviation"])
        assert (
            item["predictive_standard_deviation"] >= item["latent_standard_deviation"]
        )
        noise = result["shared_model"]["observation_noise_sd_raw"]
        assert math.isclose(
            item["predictive_standard_deviation"] ** 2
            - item["latent_standard_deviation"] ** 2,
            noise**2,
            abs_tol=1e-10,
            rel_tol=1e-8,
        )
        assert (
            item["planning"]["representative_prediction_source"]
            == "completed_observations_base_posterior"
        )
    return result


def _observe_visible(page: Page, trials: list[dict]) -> None:
    for index, trial in enumerate(trials):
        field = page.get_by_label(f"Trial {trial['trial_number']} 관측값", exact=True)
        expect(field).to_be_visible(timeout=20_000)
        field.fill(str(1 + 2 * trial["actual_coordinates"]["x"] + 0.02 * index))
    count = len(trials)
    page.get_by_role("button", name=f"입력한 관측 {count}건 저장", exact=True).click()
    with page.expect_response(
        lambda response: response.request.method == "PUT"
        and response.url.endswith("/observations/batch")
    ) as saved:
        page.get_by_role("alertdialog").get_by_role(
            "button", name=f"{count}건 저장", exact=True
        ).click()
    assert saved.value.status == 200
    for trial in trials:
        expect(
            page.get_by_label(f"Trial {trial['trial_number']} 관측값", exact=True)
        ).to_have_count(0)


def verify_bo_report_html(page: Page, path: Path, payload: dict) -> None:
    page.goto(path.resolve().as_uri(), wait_until="domcontentloaded")
    expect(page.locator("html")).to_have_attribute("lang", "en")
    section = page.locator('[data-report-section="noise_summary"]')
    expect(section).to_have_attribute("data-report-section-status", "rendered")
    expect(section).to_contain_text("New-observation predictive SD (mg)")
    expect(section).to_contain_text("Numerical jitter (not measurement noise)")
    expect(section).to_contain_text("9 / 7 / 7")
    attachment = payload["attachment"]
    factors = payload["definition"]["factors"]
    table = section.locator("table").nth(1)
    expect(table.locator("tbody tr")).to_have_count(len(attachment["items"]))
    for row_index, item in enumerate(attachment["items"]):
        values = (
            [item["rank"]]
            + [item["actual_coordinates"][factor["factor_id"]] for factor in factors]
            + [
                item["predicted_objective_mean"],
                item["latent_standard_deviation"],
                item["predictive_standard_deviation"],
                item["acquisition_value_standardized"],
                item["acquisition_value_raw"],
            ]
        )
        cells = table.locator("tbody tr").nth(row_index).locator("td")
        for column, value in enumerate(values):
            displayed = float(cells.nth(column).inner_text())
            assert math.isclose(displayed, value, rel_tol=1e-9, abs_tol=1e-15)
            if value != 0:
                assert displayed != 0


def _managed_report(page: Page, base: str, output: Path, batch: dict) -> dict:
    previous_url = page.url
    catalog = page.request.get(
        base + "/api/v1/reports/sources?source_kind=bayesian_history_revision&limit=100"
    )
    assert catalog.status == 200, catalog.text()
    source = next(
        item
        for item in catalog.json()["items"]
        if item["source"].get("attachment", {}).get("batch_id") == batch["batch_id"]
    )
    reference = source["source_ref_sha256"]
    page.goto(
        base + "/reports?source_kind=bayesian_history_revision",
        wait_until="domcontentloaded",
    )
    wait_for_app_ready(page, "ko", "/reports")
    page.locator(".language-switcher button").filter(has_text="ENG").click()
    page.reload(wait_until="domcontentloaded")
    wait_for_app_ready(page, "en", "/reports")
    page.locator(f'[data-report-source="{reference}"]').click()
    selected = page.locator(f'[data-managed-report-selection="{reference}"]')
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and response.url.endswith("/reports/source-snapshot")
    ) as saved_snapshot:
        selected.locator("[data-view-stored-source]").click()
    assert saved_snapshot.value.status == 200, saved_snapshot.value.text()
    snapshot = saved_snapshot.value.json()
    assert snapshot["source"] == source["source"] and snapshot["locale"] == "en"
    assert snapshot["payload"]["attachment"]["batch_id"] == batch["batch_id"]
    assert (
        snapshot["payload"]["attachment"]["observation_view"]
        == batch["observation_view"]
    )
    assert snapshot["payload"]["attachment"]["result_sha256"] == batch["result_sha256"]
    shown = selected.locator(".managed-report-snapshot-json")
    expect(shown).to_be_visible()
    assert json.loads(shown.inner_text()) == snapshot["payload"]
    with page.expect_response(
        lambda response: response.request.method == "POST"
        and urlsplit(response.url).path == "/api/v1/reports"
    ) as created:
        selected.locator("[data-create-managed-report]").click()
    assert created.value.status == 201, created.value.text()
    report = created.value.json()
    assert report["source"] == source["source"] and report["locale"] == "en"
    row = selected.locator(f'[data-managed-report="{report["export_id"]}"]')
    with page.expect_download() as download:
        row.get_by_role("button", name="Download", exact=True).click()
    path = output / "bo-noise-managed-en.html"
    download.value.save_as(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == report["sha256"]
    page.goto(
        base + f'/reports?report_id={report["export_id"]}',
        wait_until="domcontentloaded",
    )
    wait_for_app_ready(page, "en", "/reports")
    expect(
        page.locator(f'[data-managed-report-selection="{reference}"]')
    ).to_be_visible()
    expect(
        page.locator(f'[data-managed-report="{report["export_id"]}"]')
    ).to_be_visible()
    page.locator(".language-switcher button").filter(has_text="KOR").click()
    page.goto(previous_url, wait_until="domcontentloaded")
    wait_for_app_ready(page, "ko", ROUTE)
    return {
        "source_ref_sha256": reference,
        "source": source["source"],
        "snapshot": snapshot,
        "reports": [{"descriptor": report, "path": str(path.resolve())}],
    }


def verify_bo_noise_extension(browser: Browser, base: str, output: Path) -> dict:
    with diagnosed_page(browser, output, "bo-noise-workflow", init_script=_INITIAL_LOCALE) as page:
        ui_posts: list[str] = []
        page.on(
            "request",
            lambda request: ui_posts.append(urlsplit(request.url).path)
            if request.method == "POST"
            else None,
        )
        study = _seed(page, base)
        original = _digest(study["trials"])
        _open(page, base, study["study_id"])
        expect(page.locator("#bo-noise-mode")).to_have_value("estimate")
        first = _recommend(page)
        assert (
            first["batch_size"] == 1
            and first["items"][0]["planning"]["effective_sample_count"] == 0
        )
        _observe_visible(page, [item["trial"] for item in first["items"]])
        page.locator(
            'input[name="bayesian-execution-mode"][value="parallel_batch"]'
        ).check()
        page.locator("#bayesian-recommendation-batch-size").fill("2")
        batch = _recommend(page)
        assert batch["batch_size"] == 2
        assert batch["items"][1]["planning"]["effective_sample_count"] == 64
        assert batch["items"][1]["planning"]["conditioned_on_selected_ranks"] == [1]
        _observe_visible(page, [item["trial"] for item in batch["items"]])
        page.locator("#bo-replicate-parent").select_option(
            study["trials"][0]["trial_id"]
        )
        page.locator("#bo-replicate-count").fill("2")
        page.get_by_label(
            "같은 조건의 독립적인 추가 실험을 의도했음을 확인합니다."
        ).check()
        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/replicates")
        ) as replicated:
            page.get_by_role("button", name="반복 실험 등록", exact=True).click()
        assert replicated.value.status == 201
        replicates = replicated.value.json()["trials"]
        assert len(replicates) == 2 and all(
            row["origin"] == "replicate" for row in replicates
        )
        _observe_visible(page, replicates)
        page.locator("#bo-observation-policy").select_option("exact_replicates")
        page.locator(
            'input[name="bayesian-execution-mode"][value="sequential_single"]'
        ).check()
        compressed = _recommend(page)
        view = compressed["observation_view"]
        assert view["mode"] == "exact_replicates" and view["raw_observation_count"] == 9
        assert (
            view["effective_training_count"] == 7
            and view["unique_condition_count"] == 7
        )
        assert any(
            group["n"] == 3
            and study["trials"][0]["trial_id"] in group["member_trial_ids"]
            for group in view["groups"]
        )
        restored = _study(page, base, study["study_id"])
        assert _digest(restored["trials"][:4]) == original
        assert (
            restored["completed_trial_count"] == 9
            and restored["pending_trial_count"] == 1
        )
        snapshots = []
        layout_geometry = []
        posts_before_display_changes = len(ui_posts)
        for locale, label in (("en", "ENG"), ("ko", "KOR")):
            page.locator(".language-switcher button").filter(has_text=label).click()
            expect(page.locator("html")).to_have_attribute("lang", locale)
            for width in (1024, 1440):
                page.set_viewport_size({"width": width, "height": 1000})
                expect(page.locator("#bayesian-batch-result-title")).to_be_visible()
                layout_geometry.append({"locale": locale, **_settled_layout(page)})
                assert (
                    page.evaluate(
                        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
                    )
                    <= 1
                )
                path = output / f"bo-noise-{locale}-{width}.png"
                page.screenshot(path=str(path), full_page=True)
                snapshots.append({"locale": locale, "width": width})
        page.reload(wait_until="domcontentloaded")
        wait_for_app_ready(page, "ko", ROUTE)
        expect(page.locator("#bo-observation-policy")).to_have_value("exact_replicates")
        expect(page.locator("#bayesian-batch-result-title")).to_be_visible()
        assert len(ui_posts) == posts_before_display_changes
        saved = page.request.get(
            base
            + f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches/{compressed['batch_id']}"
        )
        assert saved.status == 200 and saved.json()["observation_view"] == view
        managed_report = _managed_report(page, base, output, saved.json())
        assert _digest(_study(page, base, study["study_id"])) == _digest(restored)
        return _record_receipt(
            output,
            {
                "schema_version": 1,
                "synthetic": True,
                "status": "succeeded",
                "study_id": study["study_id"],
                "q1_target_ui": True,
                "joint_batch_ui": True,
                "replicate_ui": True,
                "individual_observations_ui": True,
                "exact_aggregation_ui": True,
                "legacy_observations_unchanged": True,
                "restore_ui": True,
                "locale_resize_restore_do_not_post": True,
                "raw_n": 9,
                "effective_n": 7,
                "locales_viewports": snapshots,
                "layout_geometry": layout_geometry,
                "batch_id": compressed["batch_id"],
                "stored_batch_sha256": _digest(saved.json()),
                "study_payload_sha256": _digest(restored),
                "source_history_revision_id": compressed["source_history_revision_id"],
                "source_history_sha256": compressed[
                    "source_observation_history_sha256"
                ],
                "current_history_revision_id": restored["observation_history"][
                    "history_revision_id"
                ],
                "current_history_sha256": restored["observation_history"][
                    "observation_history_sha256"
                ],
                "replicate_parent_trial_id": study["trials"][0]["trial_id"],
                "replicate_trial_ids": [row["trial_id"] for row in replicates],
                "managed_report": managed_report,
            },
        )


def verify_bo_noise_context(browser: Browser, base: str, output: Path) -> dict:
    with diagnosed_page(browser, output, "bo-replicate-context", init_script=_INITIAL_LOCALE) as page:
        study = _seed(page, base)
        _open(page, base, study["study_id"])
        page.locator("#bo-replicate-parent").select_option(
            study["trials"][0]["trial_id"]
        )
        page.get_by_label(
            "같은 조건의 독립적인 추가 실험을 의도했음을 확인합니다."
        ).check()
        requests: list[dict] = []

        def committed_but_disconnected(route: Route) -> None:
            requests.append(route.request.post_data_json)
            result = route.fetch()
            assert result.status == 201
            route.fulfill(
                status=503,
                content_type="application/json",
                json={"error": {"code": "synthetic_connection_lost"}},
            )

        pattern = "**/api/v1/bayesian-studies/*/trials/*/replicates"
        page.route(pattern, committed_but_disconnected)
        page.get_by_role("button", name="반복 실험 등록", exact=True).click()
        retry = page.get_by_role("button", name="동일 요청 확인/재시도", exact=True)
        expect(retry).to_be_enabled()
        assert len(requests) == 1
        page.unroute(pattern)
        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/replicates")
        ) as retried:
            retry.click()
        assert retried.value.status == 201 and retried.value.json()["replayed"] is True
        assert retried.value.request.post_data_json == requests[0]
        restored = _study(page, base, study["study_id"])
        assert len(restored["trials"]) == 5 and restored["pending_trial_count"] == 1
        assert restored["observation_history"] == study["observation_history"]
        return _record_receipt(
            output,
            {
                "schema_version": 1,
                "synthetic": True,
                "status": "succeeded",
                "committed_post_replayed_only_by_explicit_action": True,
                "same_request_id_payload": True,
                "no_duplicate_trials": True,
                "history_unchanged": True,
                "study_id": study["study_id"],
                "request_id": retried.value.json()["request_id"],
                "current_history_revision_id": restored["observation_history"][
                    "history_revision_id"
                ],
                "current_history_sha256": restored["observation_history"][
                    "observation_history_sha256"
                ],
                "replicate_trial_ids": [
                    row["trial_id"] for row in retried.value.json()["trials"]
                ],
            },
        )
