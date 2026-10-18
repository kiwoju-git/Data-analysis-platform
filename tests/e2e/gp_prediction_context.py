"""Synthetic saved-model prediction identity and delayed-response browser checks."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Browser, Page, Route, expect

from app_readiness import diagnosed_page, wait_for_app_ready


def _fixtures(page: Page, base_url: str) -> tuple[dict, list[dict]]:
    lines = ["response,x1,x2"]
    for index in range(1, 17):
        x1, x2 = index / 3, ((index * 7) % 11) / 4
        lines.append(f"{math.sin(x1) + 0.35 * x2:.12f},{x1:.12f},{x2:.12f}")
    uploaded = page.request.post(
        base_url + "/api/v1/datasets",
        headers={"Origin": base_url},
        multipart={
            "file": {
                "name": "synthetic-gp-context.csv",
                "mimeType": "text/csv",
                "buffer": ("\n".join(lines) + "\n").encode(),
            }
        },
    )
    assert uploaded.status == 201, uploaded.text()
    confirmed = page.request.post(
        base_url + f"/api/v1/datasets/{uploaded.json()['dataset_id']}/confirm-parsing",
        headers={"Origin": base_url},
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
    assert confirmed.status == 201, confirmed.text()
    version = confirmed.json()
    response_id = version["columns"][0]["column_id"]
    predictors = [column["column_id"] for column in version["columns"][1:]]
    catalog = page.request.get(base_url + "/api/v1/analysis-methods").json()
    method = next(
        item
        for item in catalog["methods"]
        if item["method_id"] == "regression.gaussian_process"
    )
    analyses = []
    for preset in ("matern_5_2_ard", "rbf_ard"):
        created = page.request.post(
            base_url + "/api/v1/analysis-runs",
            headers={"Origin": base_url},
            timeout=120_000,
            data={
                "method_id": method["method_id"],
                "method_version": method["method_version"],
                "dataset_version_id": version["version_id"],
                "filter_snapshot": {"expression_version": 1, "conditions": []},
                "roles": {"response": response_id, "predictors": ",".join(predictors)},
                "options": {
                    "response_column_id": response_id,
                    "predictor_column_ids": predictors,
                    "missing_policy": "complete_case",
                    "kernel_preset": preset,
                    "noise_mode": "estimate",
                    "standardize_predictors": True,
                    "normalize_response": True,
                    "jitter": 1e-8,
                    "optimizer_restarts": 0,
                    "cv_optimizer_restarts": 0,
                    "cv": {"method": "k_fold", "folds": 3, "shuffle": True, "seed": 29},
                    "plot_point_limit": 100,
                    "profile_points": 10,
                    "surface_grid_size": 10,
                    "time_budget_seconds": 120,
                },
            },
        )
        assert created.status == 201, created.text()
        analyses.append(created.json())
    return version, analyses


def _restore(page: Page, base_url: str, version: dict, analysis: dict) -> None:
    history = page.locator(".compact-analysis-history")
    toggle = history.locator("button[aria-expanded]")
    if toggle.get_attribute("aria-expanded") != "true":
        toggle.click()
    response = page.request.get(
        base_url + "/api/v1/analysis-runs",
        params={
            "dataset_version_id": version["version_id"],
            "method_id": analysis["method_id"],
            "limit": 3,
            "offset": 0,
        },
    )
    assert response.status == 200
    runs = response.json()["runs"]
    index = next(
        index
        for index, run in enumerate(runs)
        if run["analysis_id"] == analysis["analysis_id"]
    )
    items = history.locator(".compact-history-list article")
    expect(items).to_have_count(len(runs))
    with page.expect_response(
        lambda response: urlsplit(response.url).path
        == f"/api/v1/analysis-runs/{analysis['analysis_id']}/result"
    ) as restored:
        items.nth(index).locator("button").click()
    assert restored.value.status == 200
    expect(page.locator(".gp-point-prediction")).to_have_attribute(
        "data-prediction-state", "empty"
    )


class PredictionResponse:
    def __init__(
        self,
        page: Page,
        model_id: str,
        *,
        hold: bool = False,
        mutation: str | None = None,
    ):
        self.page = page
        self.path = f"/api/v1/regression-models/{model_id}/gaussian-process-predictions"
        self.hold, self.mutation = hold, mutation
        self.route: Route | None = None
        self.payload: dict | None = None
        self.original: dict | None = None
        self.request: dict | None = None

    def handle(self, route: Route) -> None:
        if self.route is not None or route.request.method != "POST":
            route.continue_()
            return
        self.route = route
        self.request = route.request.post_data_json
        response = route.fetch()
        assert response.status == 200, response.text()
        self.original = response.json()
        self.payload = copy.deepcopy(self.original)
        if self.mutation == "reverse":
            self.payload["rows"].reverse()
        elif self.mutation == "duplicate":
            self.payload["rows"][1]["client_row_id"] = self.payload["rows"][0][
                "client_row_id"
            ]
        elif self.mutation == "missing":
            self.payload["rows"].pop()
        elif self.mutation == "foreign":
            self.payload["rows"][0]["client_row_id"] = "not-requested"
        elif self.mutation == "model":
            self.payload["model_id"] = "00000000-0000-4000-8000-000000000000"
        if self.hold:
            self.page.evaluate("window.__predictionHeld = true")
        else:
            self.fulfill()

    def wait(self) -> None:
        self.page.wait_for_function("window.__predictionHeld === true")
        assert self.request is not None and self.payload is not None

    def fulfill(self) -> None:
        assert self.route is not None and self.payload is not None
        self.route.fulfill(
            status=200, content_type="application/json", body=json.dumps(self.payload)
        )

    def release(self) -> None:
        with self.page.expect_response(
            lambda response: urlsplit(response.url).path == self.path
            and response.request.method == "POST"
        ) as received:
            self.fulfill()
        assert received.value.json() == self.payload
        self.page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )


def _inputs(page: Page, *, rows: int = 1) -> None:
    panel = page.locator(".gp-point-prediction")
    for index in range(rows):
        if index:
            panel.locator(".button-row > button.secondary-button").click()
        inputs = panel.locator("tbody tr").nth(index).locator("input")
        inputs.nth(0).fill(str(2.5 + index))
        inputs.nth(1).fill(str(1.0 + index / 4))


def _no_values(page: Page, state: str) -> None:
    panel = page.locator(".gp-point-prediction")
    expect(panel).to_have_attribute("data-prediction-state", state)
    for row in panel.locator("tbody tr").all():
        for column in range(3, 8):
            expect(row.locator("td").nth(column)).to_have_text("-")
    expect(panel.locator('[data-action="download-prediction-snapshot"]')).to_have_count(
        0
    )


def _snapshot(page: Page, path: Path) -> dict:
    panel = page.locator(".gp-point-prediction")
    expect(panel).to_have_attribute("data-prediction-state", "ready")
    with page.expect_download() as downloaded:
        panel.locator('[data-action="download-prediction-snapshot"]').click()
    downloaded.value.save_as(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _scenario(
    page: Page,
    base_url: str,
    version: dict,
    analyses: list[dict],
    kind: str,
    output: Path,
) -> dict:
    analysis = analyses[0]
    model = analysis["result"]["model_manifest"]
    hold = kind in ("edit", "delete", "replacement", "model-change")
    mutation = (
        kind
        if kind in ("reverse", "duplicate", "missing", "foreign", "model")
        else None
    )
    intercepted = PredictionResponse(
        page, model["model_id"], hold=hold, mutation=mutation
    )
    page.route("**" + intercepted.path, intercepted.handle)
    _inputs(
        page,
        rows=2
        if kind in ("delete", "reverse", "duplicate", "missing", "foreign")
        else 1,
    )
    panel = page.locator(".gp-point-prediction")
    panel.locator("button.primary-button").click()
    if hold:
        intercepted.wait()
        expect(panel).to_have_attribute("data-prediction-state", "running")
        if kind == "model-change":
            _restore(page, base_url, version, analyses[1])
            intercepted.release()
            _no_values(page, "empty")
        else:
            if kind == "delete":
                panel.locator("tbody tr").last.locator("button").click()
                expect(panel.locator("tbody tr")).to_have_count(1)
            else:
                panel.locator("tbody input").first.fill("4.1")
            _no_values(page, "stale")
            if kind == "replacement":
                panel.locator("button.primary-button").click()
                before = _snapshot(page, output / "newer-before.json")
                intercepted.release()
                after = _snapshot(page, output / "newer-after.json")
                assert after == before
                predictor = analysis["result"]["predictors"][0]["column_id"]
                assert after["request"]["rows"][0]["values"][predictor] == 4.1
            else:
                intercepted.release()
                _no_values(page, "stale")
    elif kind in ("duplicate", "missing", "foreign", "model"):
        _no_values(page, "error")
        expect(panel.locator('[role="alert"]')).to_contain_text(
            "gp_prediction_response_invalid"
        )
    else:
        snapshot = _snapshot(page, output / "prediction.json")
        assert snapshot["source_analysis_id"] == analysis["analysis_id"]
        assert snapshot["request"] == intercepted.request
        assert snapshot["response"] == intercepted.payload
        assert snapshot["prediction_recalculated_on_export"] is False
        assert snapshot["response"]["model_manifest_sha256"] == model["manifest_sha256"]
        for returned in snapshot["response"]["rows"]:
            assert (
                returned["predictive_standard_deviation"]
                >= returned["latent_standard_deviation"]
            )
        requested_ids = [row["client_row_id"] for row in snapshot["request"]["rows"]]
        if kind == "reverse":
            assert [
                row["client_row_id"] for row in snapshot["response"]["rows"]
            ] == list(reversed(requested_ids))
        rows_by_id = {row["client_row_id"]: row for row in snapshot["response"]["rows"]}
        for index, row_id in enumerate(requested_ids):
            displayed = (
                panel.locator("tbody tr")
                .nth(index)
                .locator("td")
                .nth(3)
                .inner_text()
                .replace(",", "")
            )
            # Intl's existing default is three fractional digits; this tolerance
            # applies only to the rounded cell. The JSON comparison above is exact.
            assert math.isclose(
                float(displayed),
                rows_by_id[row_id]["predicted_mean"],
                rel_tol=0,
                abs_tol=0.0005 + 1e-12,
            )
        count = []
        page.on(
            "request",
            lambda request: count.append(request.url)
            if request.method == "POST"
            else None,
        )
        next_locale = (
            "en" if page.locator("html").get_attribute("lang") == "ko" else "ko"
        )
        page.locator(".language-switcher button").filter(
            has_text="ENG" if next_locale == "en" else "KOR"
        ).click()
        expect(page.locator("html")).to_have_attribute("lang", next_locale)
        page.set_viewport_size({"width": 1024, "height": 768})
        assert _snapshot(page, output / "after-locale-resize.json") == snapshot
        assert count == []
    return {
        "scenario": kind,
        "request": intercepted.request,
        "original_response": intercepted.original,
        "delivered_response": intercepted.payload,
        "result_state": panel.get_attribute("data-prediction-state"),
    }


def verify_gp_prediction_context(
    browser: Browser, base_url: str, root: Path, *, isolated_workspace: bool
) -> None:
    if not isolated_workspace:
        raise ValueError("Prediction fixtures require an owned synthetic workspace")
    root.mkdir(parents=True, exist_ok=True)
    with diagnosed_page(browser, root, "fixtures", locale="ko") as setup:
        version, analyses = _fixtures(setup, base_url)
    for locale in ("ko", "en"):
        for kind in (
            "edit",
            "delete",
            "replacement",
            "model-change",
            "reverse",
            "duplicate",
            "missing",
            "foreign",
            "model",
        ):
            name = f"{kind}-{locale}"
            with diagnosed_page(browser, root, name, locale=locale) as page:
                page.goto(
                    base_url
                    + f"/analysis/regression/regression.gaussian_process?dataset_version_id={version['version_id']}",
                    wait_until="domcontentloaded",
                )
                wait_for_app_ready(
                    page, locale, "/analysis/regression/regression.gaussian_process"
                )
                _restore(page, base_url, version, analyses[0])
                evidence = _scenario(
                    page, base_url, version, analyses, kind, root / name
                )
                for analysis in analyses:
                    stored = page.request.get(
                        base_url
                        + f"/api/v1/analysis-runs/{analysis['analysis_id']}/result"
                    )
                    assert stored.status == 200
                    assert stored.json() == analysis
                evidence.update(
                    {
                        "fixture": "synthetic",
                        "locale": locale,
                        "source_model_sha256": analyses[0]["result"]["model_manifest"][
                            "manifest_sha256"
                        ],
                        "source_payload_sha256": hashlib.sha256(
                            json.dumps(analyses[0], sort_keys=True).encode()
                        ).hexdigest(),
                    }
                )
                (root / name / "evidence.json").write_text(
                    json.dumps(evidence, indent=2), encoding="utf-8"
                )
                page.screenshot(path=str(root / name / "completed.png"), full_page=True)
