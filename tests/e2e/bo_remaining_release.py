"""Exact-archive BO completion, immutable restart and server-stopped HTML evidence.

The pure contract imports no application or browser modules. Browser imports are
local so negative receipt tests cannot accidentally start a process or fit.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROUTE = "/analysis/doe/doe.bayesian_optimization"


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _require(condition: object) -> None:
    if not condition:
        raise ValueError(
            "Exact-archive BO completion evidence is incomplete or changed"
        )


def _saved_identity(evidence: dict, kind: str) -> dict:
    _require(evidence.get("synthetic") is True)
    saved, report = evidence["saved"], evidence["report"]["descriptor"]
    payload, source = saved["payload"], saved["source"]
    _require(payload["source"] == source and payload["kind"] == "profiler_matrix")
    _require(payload["schema_version"] == (2 if kind == "mixture" else 1))
    _require(bool(payload["axes"]) and any(axis["points"] for axis in payload["axes"]))
    _require(digest(payload) == saved["view_sha256"])
    result = {
        "study_id": source["study_id"],
        "model_id": source["model_id"],
        "model_sha256": source["model_sha256"],
        "history_sha256": source["history_sha256"],
        "view_id": saved["view_id"],
        "view_sha256": saved["view_sha256"],
        "report_id": report["export_id"],
        "report_sha256": report["sha256"],
    }
    for key, value in result.items():
        _require(isinstance(value, str) and bool(value))
        if key.endswith("sha256"):
            _require(re.fullmatch(r"[0-9a-f]{64}", value))
    _require(isinstance(evidence["report"]["path"], str))
    return result


def initial_identity(receipt: object) -> dict:
    try:
        _require(isinstance(receipt, dict))
        _require(
            receipt.get("schema_version") == 1 and receipt.get("phase") == "initial"
        )
        _require(
            receipt.get("status") == "succeeded" and receipt.get("synthetic") is True
        )
        numeric, mixture = receipt["numeric"], receipt["mixture"]
        _require(numeric["fit_posts"] == 1 and numeric["pageerrors"] == [])
        identities = {
            kind: _saved_identity(part["saved_matrix"], kind)
            for kind, part in (("numeric", numeric), ("mixture", mixture))
        }
        legacy = numeric["legacy_renewal"]
        _require(legacy["synthetic"] is True and legacy["old_bytes_unchanged"] is True)
        _require(legacy["fit_posts"] == 0 and legacy["pageerrors"] == [])
        old, renewed = legacy["original_selection"], legacy["renewal"]["selection"]
        lineage = legacy["renewal"]["lineage"]
        _require(old["selection_id"] != renewed["selection_id"])
        _require(lineage["numerical_policy"] == "positive_beta_integral_v2")
        for key in ("selection_id", "config_sha256", "result_sha256"):
            _require(lineage["original_" + key] == old[key])
        identities["legacy"] = {
            "original_selection_id": old["selection_id"],
            "original_config_sha256": old["config_sha256"],
            "original_result_sha256": old["result_sha256"],
            "renewed_selection_id": renewed["selection_id"],
            "renewed_result_sha256": renewed["result_sha256"],
            "batch_id": legacy["batch"]["batch_id"],
            "batch_sha256": digest(legacy["batch"]),
        }
        _require(mixture["synthetic"] is True and mixture["import_schema"] == 2)
        _require(mixture["completed_before"] == 8 and mixture["completed_after"] == 10)
        _require(mixture["candidate_count"] == 32)
        _require(
            mixture["source_model_sha256"] == identities["mixture"]["model_sha256"]
        )
        _require(mixture["next_model_sha256"] != mixture["source_model_sha256"])
        _require(mixture["saved_view_sha256"] == identities["mixture"]["view_sha256"])
        return identities
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("Required BO archive journey evidence is missing") from error


def require_roundtrip(initial: object, resumes: list, offline: object) -> dict:
    expected = initial_identity(initial)
    _require(len(resumes) == 2)
    for phase, receipt in [("resume", item) for item in resumes] + [
        ("offline", offline)
    ]:
        _require(isinstance(receipt, dict))
        _require(receipt.get("schema_version") == 1 and receipt.get("phase") == phase)
        _require(receipt.get("status") == "succeeded")
        _require(receipt.get("identity") == expected)
        _require(receipt.get("identity_sha256") == digest(expected))
        _require(
            receipt.get("forbidden_mutation_requests") == []
            and receipt.get("pageerrors") == []
        )
        if phase == "resume":
            _require(receipt.get("exact_sources_visible") is True)
        else:
            _require(receipt.get("original_server_unreachable") is True)
            _require(receipt.get("http_request_count") == 0)
            _require(receipt.get("visible_report_count") == 2)
    return {
        "schema_version": 1,
        "status": "succeeded",
        "identity_sha256": digest(expected),
        "same_install_restart": True,
        "second_install_shared_workspace": True,
        "server_stopped_reports": True,
    }


def run_initial(browser, base: str, output: Path, workspace: Path) -> dict:
    from bo_mixture_completion import verify_mixture_completion
    from bo_persistent_planning import verify_profile_constraints

    numeric = verify_profile_constraints(
        browser, base, output / "numeric", synthetic_workspace=workspace
    )
    mixture = verify_mixture_completion(browser, base, output / "mixture")
    receipt = {
        "schema_version": 1,
        "phase": "initial",
        "status": "succeeded",
        "synthetic": True,
        "numeric": numeric,
        "mixture": mixture,
    }
    initial_identity(receipt)
    return receipt


def _get(page, base: str, path: str) -> dict:
    response = page.request.get(base + path)
    assert response.status == 200, response.text()
    return response.json()


def run_resume(base: str, output: Path, original: dict) -> dict:
    from app_readiness import diagnosed_page, wait_for_bayesian_ready
    from bo_gp_release_resume import _forbidden
    from playwright.sync_api import expect, sync_playwright

    expected = initial_identity(original["bo_remaining_receipt"])
    forbidden, errors = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            with diagnosed_page(
                browser,
                output,
                "bo-remaining-resume",
                init_script="localStorage.setItem('statistical-twin.locale', 'en');",
            ) as page:
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on(
                    "request",
                    lambda request: forbidden.append(request.url)
                    if _forbidden(request)
                    else None,
                )
                for kind in ("numeric", "mixture"):
                    evidence = original["bo_remaining_receipt"][kind]["saved_matrix"]
                    saved, identity = evidence["saved"], expected[kind]
                    api = f"/api/v1/bayesian-studies/{identity['study_id']}"
                    before = _get(page, base, api)
                    restored = _get(page, base, api + "/views/" + identity["view_id"])
                    assert restored == saved
                    model_path = (
                        "/mixture-planning-models/"
                        if kind == "mixture"
                        else "/planning-models/"
                    )
                    model = _get(page, base, api + model_path + identity["model_id"])
                    assert model["snapshot_sha256"] == identity["model_sha256"]
                    page.goto(
                        base
                        + ROUTE
                        + f"?study_id={identity['study_id']}&view_id={identity['view_id']}",
                        wait_until="domcontentloaded",
                    )
                    wait_for_bayesian_ready(page, "en", ROUTE)
                    panel = page.get_by_role(
                        "region", name="Saved diagnostic views", exact=True
                    )
                    expect(panel).to_contain_text(identity["view_sha256"])
                    expect(panel).to_contain_text(identity["model_sha256"])
                    expect(panel.locator(".chart-frame-svg").first).to_be_visible()
                    descriptor = evidence["report"]["descriptor"]
                    download = page.request.post(
                        base + f"/api/v1/reports/{descriptor['export_id']}/download",
                        headers={"Origin": base},
                        data={
                            "source": descriptor["source"],
                            "expected_sha256": descriptor["sha256"],
                        },
                    )
                    assert download.status == 200, download.text()
                    assert (
                        hashlib.sha256(download.body()).hexdigest()
                        == identity["report_sha256"]
                    )
                    assert (
                        download.body() == Path(evidence["report"]["path"]).read_bytes()
                    )
                    assert _get(page, base, api) == before
                    page.screenshot(
                        path=output / f"{kind}-saved-view.png", full_page=True
                    )
                legacy = original["bo_remaining_receipt"]["numeric"]["legacy_renewal"]
                api = f"/api/v1/bayesian-studies/{expected['numeric']['study_id']}"
                old = _get(
                    page,
                    base,
                    api
                    + "/augmentations/"
                    + expected["legacy"]["original_selection_id"],
                )
                assert (
                    old["config_sha256"] == expected["legacy"]["original_config_sha256"]
                )
                assert (
                    old["result_sha256"] == expected["legacy"]["original_result_sha256"]
                )
                assert {
                    key: value
                    for key, value in old.items()
                    if key != "source_is_current"
                } == {
                    key: value
                    for key, value in legacy["original_selection"].items()
                    if key != "source_is_current"
                }
                lineage = _get(
                    page,
                    base,
                    api
                    + "/augmentations/"
                    + expected["legacy"]["renewed_selection_id"]
                    + "/renewal",
                )
                assert lineage == legacy["renewal"]["lineage"]
                batch = _get(
                    page,
                    base,
                    api + "/augmentation-batches/" + expected["legacy"]["batch_id"],
                )
                assert batch == legacy["batch"]
                assert not forbidden and not errors, (forbidden, errors)
        finally:
            browser.close()
    return {
        "schema_version": 1,
        "phase": "resume",
        "status": "succeeded",
        "identity": expected,
        "identity_sha256": digest(expected),
        "forbidden_mutation_requests": forbidden,
        "pageerrors": errors,
        "exact_sources_visible": True,
    }


def capture_report_charts(page, output: Path, kind: str) -> int:
    """Bound each bitmap without omitting graphs or changing report layout."""
    viewport = page.viewport_size
    assert viewport is not None
    page.evaluate("window.scrollTo(0, 0)")
    page.screenshot(path=output / f"{kind}-server-stopped.png", full_page=False)
    charts = page.locator("svg").all()
    assert charts
    for index, chart in enumerate(charts, start=1):
        chart.scroll_into_view_if_needed()
        box = chart.bounding_box()
        assert box is not None and all(math.isfinite(value) for value in box.values())
        assert 0 < box["width"] <= viewport["width"]
        assert 0 < box["height"] <= viewport["height"]
        assert -1 <= box["x"] and box["x"] + box["width"] <= viewport["width"] + 1
        assert -1 <= box["y"] and box["y"] + box["height"] <= viewport["height"] + 1
        chart.screenshot(path=output / f"{kind}-server-stopped-chart-{index}.png")
    return len(charts)


def run_offline(output: Path, original: dict) -> dict:
    from app_readiness import diagnosed_page
    from linux_release import require_server_stopped
    from playwright.sync_api import expect, sync_playwright

    require_server_stopped(original["access_origin"])
    expected = initial_identity(original["bo_remaining_receipt"])
    requests, errors = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            with diagnosed_page(browser, output, "bo-remaining-offline") as page:
                page.context.set_offline(True)
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on(
                    "request",
                    lambda request: requests.append(request.url)
                    if urlsplit(request.url).scheme in {"http", "https"}
                    else None,
                )
                for kind in ("numeric", "mixture"):
                    evidence = original["bo_remaining_receipt"][kind]["saved_matrix"]
                    path, saved = Path(evidence["report"]["path"]), evidence["saved"]
                    assert (
                        hashlib.sha256(path.read_bytes()).hexdigest()
                        == expected[kind]["report_sha256"]
                    )
                    page.goto(path.resolve().as_uri(), wait_until="domcontentloaded")
                    body = page.locator("body")
                    expect(body).to_contain_text(saved["view_sha256"])
                    expect(body).to_contain_text(saved["source"]["model_sha256"])
                    assert page.locator("script, link[href], img[src]").count() == 0
                    points = Counter(
                        tuple(point)
                        for point in page.locator("svg [data-x][data-y]").evaluate_all(
                            "nodes => nodes.map(node => [Number(node.dataset.x), Number(node.dataset.y)])"
                        )
                    )
                    wanted = Counter()
                    axes = saved["payload"]["axes"]
                    for axis in axes:
                        expect(body).to_contain_text(axis["name"])
                        numeric = axis["kind"] in {
                            "continuous",
                            "discrete_numeric",
                            "mixture_component",
                        }
                        for i, point in enumerate(axis["points"]):
                            x = (
                                float(point["actual_coordinates"][axis["factor_id"]])
                                if numeric
                                else float(i)
                            )
                            for prediction in point["response_predictions"]:
                                for metric in (
                                    "mean_raw",
                                    "latent_standard_deviation_raw",
                                    "predictive_standard_deviation_raw",
                                ):
                                    wanted[(x, prediction[metric])] += 1
                            wanted[(x, point["desirability_moments"]["mean"])] += 1
                    assert points == wanted and bool(wanted)
                    for svg in page.locator("svg").all():
                        expect(svg).to_be_visible()
                    if kind == "mixture":
                        expect(body).to_contain_text("co-vary")
                    assert capture_report_charts(page, output, kind) == sum(
                        3 * len(axis["points"][0]["response_predictions"]) + 1
                        for axis in axes
                        if axis["points"]
                    )
                assert not requests and not errors, (requests, errors)
        finally:
            browser.close()
    return {
        "schema_version": 1,
        "phase": "offline",
        "status": "succeeded",
        "identity": expected,
        "identity_sha256": digest(expected),
        "forbidden_mutation_requests": [],
        "pageerrors": errors,
        "original_server_unreachable": True,
        "http_request_count": len(requests),
        "visible_report_count": 2,
    }
