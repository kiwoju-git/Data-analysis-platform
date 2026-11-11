"""Synthetic saved-history graphs; no model fit is needed to inspect real observations."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from playwright.sync_api import Browser, expect, sync_playwright

from app_readiness import (
    diagnosed_page,
    wait_for_bayesian_ready,
    wait_for_layout_settled,
)

ROUTE = "/analysis/doe/doe.bayesian_optimization"


def _seed(page, base: str, vector: bool, mixed: bool = False) -> dict:
    objective = {
        "name": "Synthetic response",
        "unit": "mg",
        "goal_type": "match_target",
        "target_value": 5,
        "observation_policy": "manual_single_observation",
    }
    if vector:
        objective = {
            "name": "Synthetic joint goals",
            "goal_type": "desirability",
            "observation_policy": "complete_response_vector",
            "curve_policy": "derringer_suich_linear_v1",
            "responses": [
                {
                    "response_id": "a",
                    "name": "수율 <raw>",
                    "unit": "mg",
                    "goal": "maximize",
                    "lower": 0,
                    "target": 10,
                    "upper": None,
                    "importance": 1,
                },
                {
                    "response_id": "b",
                    "name": "Cost",
                    "unit": "USD",
                    "goal": "minimize",
                    "lower": None,
                    "target": 0,
                    "upper": 10,
                    "importance": 1,
                },
            ],
        }
    created = page.request.post(
        base + "/api/v1/bayesian-studies" + ("/mixed" if mixed else ""),
        headers={"Origin": base},
        data={
            **({"schema_version": 7} if mixed else {}),
            "name": "Synthetic progress vector"
            if vector
            else "Synthetic progress target",
            "factors": [
                {
                    "factor_id": "x",
                    "name": "온도 <raw>",
                    "unit": "C",
                    "domain_kind": "continuous",
                    "low": 0,
                    "high": 10,
                },
                (
                    {
                        "factor_id": "z",
                        "name": "Pressure",
                        "domain_kind": "nominal",
                        "levels": [
                            f"범주 {index} " + "긴이름" * 30 for index in range(32)
                        ],
                        "correlation_policy": "equal_positive_correlation_v1",
                    }
                    if mixed
                    else {
                        "factor_id": "z",
                        "name": "Pressure",
                        "unit": "kPa",
                        "low": 0,
                        "high": 10,
                    }
                ),
            ],
            "objective": objective,
            "initial_design_seed": 17,
            "initial_design_size": 4,
        },
    )
    assert created.status == 201, created.text()
    study = created.json()
    url = base + "/api/v1/bayesian-studies/" + study["study_id"]
    if vector:
        response = page.request.put(
            url + "/observations/batch",
            headers={"Origin": base},
            data={
                "request_id": str(uuid4()),
                "expected_study_version_id": study["study_version_id"],
                "expected_history_revision_id": study["observation_history"][
                    "history_revision_id"
                ],
                "expected_observation_history_sha256": study["observation_history"][
                    "observation_history_sha256"
                ],
                "observations": [
                    {
                        "trial_id": trial["trial_id"],
                        "response_values": {"a": value, "b": 10 - value},
                    }
                    for trial, value in zip(study["trials"][:3], (2, 8, 4))
                ],
            },
        )
        assert response.status == 200, response.text()
    else:
        for trial, value in zip(study["trials"][:3], (1e-8, 6, 4)):
            response = page.request.put(
                url + f"/trials/{trial['trial_id']}/observation",
                headers={"Origin": base},
                data={
                    "objective_value": value,
                    "expected_history_revision_id": study["observation_history"][
                        "history_revision_id"
                    ],
                },
            )
            assert response.status == 200, response.text()
            study = response.json()
    return page.request.get(url).json()


def verify_bo_progress(browser: Browser, base: str, output: Path) -> dict:
    with diagnosed_page(
        browser,
        output,
        "bo-progress",
        init_script="localStorage.setItem('statistical-twin.locale','en');",
    ) as page:
        scalar, vector = _seed(page, base, False), _seed(page, base, True)
        mixed = _seed(page, base, True, True)
        errors, writes, layouts = [], [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "request",
            lambda request: writes.append(request.method)
            if "/api/" in request.url and request.method in {"POST", "PUT", "DELETE"}
            else None,
        )
        for study, is_vector in ((scalar, False), (vector, True), (mixed, True)):
            is_mixed = study["study_id"] == mixed["study_id"]
            url = base + "/api/v1/bayesian-studies/" + study["study_id"]
            before = hashlib.sha256(
                json.dumps(study, sort_keys=True).encode()
            ).hexdigest()
            page.goto(
                base + ROUTE + "?study_id=" + study["study_id"],
                wait_until="domcontentloaded",
            )
            wait_for_bayesian_ready(page, "en", ROUTE)
            panel = page.locator(".bo-progress")
            observed = panel.locator('[data-chart-id="bo-progress-observed"]')
            space = panel.locator('[data-chart-id="bo-progress-space"]')
            expect(observed.locator('[data-point-id$=":measured"]')).to_have_count(3)
            expect(space.locator("[data-point-id]")).to_have_count(4)
            expect(space.locator(".bo-progress-pending[data-point-id]")).to_have_count(
                1
            )
            if is_mixed:
                panel.locator(".bo-progress-levels > summary").click()
                expect(panel.locator(".bo-progress-levels dd")).to_have_count(32)
                expect(panel.locator(".bo-progress-levels dd").first).to_have_text(
                    study["factors"][1]["levels"][0]
                )
                panel.locator(".bo-progress-levels > summary").click()
            if is_vector:
                score = panel.locator('[data-chart-id="bo-progress-desirability"]')
                assert [
                    float(value)
                    for value in score.locator(
                        '[data-point-id$=":measured"]'
                    ).evaluate_all("els=>els.map(e=>e.dataset.y)")
                ] == [0.2, 0.8, 0.4]
                assert score.locator('[data-point-id$=":best"]').evaluate_all(
                    "els=>els.map(e=>Number(e.dataset.y))"
                ) == [0.2, 0.8, 0.8]
                panel.get_by_label("Response", exact=True).select_option("b")
                assert observed.locator('[data-point-id$=":measured"]').evaluate_all(
                    "els=>els.map(e=>Number(e.dataset.y))"
                ) == [8, 2, 6]
                panel.get_by_label("Response", exact=True).select_option("a")
            else:
                expect(panel).to_contain_text("No desirability limits")
                assert (
                    float(
                        observed.locator(
                            '[data-point-id$=":measured"]'
                        ).first.get_attribute("data-y")
                    )
                    == 1e-8
                )
                panel.get_by_label("Response view", exact=True).select_option(
                    "distance"
                )
                assert observed.locator('[data-point-id$=":best"]').evaluate_all(
                    "els=>els.map(e=>Number(e.dataset.y))"
                ) == [4.99999999, 1, 1]
                disclosure = page.locator(
                    "section[aria-labelledby='bo-replicates-title'] > details"
                )
                expect(disclosure).not_to_have_attribute("open", "")
                disclosure.locator("summary").click()
                expect(disclosure).to_have_attribute("open", "")
            point = observed.locator('[data-point-id$=":measured"]').first
            point.focus()
            point.press("Enter")
            expect(point).to_have_attribute("data-selected", "true")
            for locale, label in (("ko", "KOR"), ("en", "ENG")):
                page.locator(".language-switcher button").filter(has_text=label).click()
                for width in (1024, 1440):
                    page.set_viewport_size({"width": width, "height": 1000})
                    wait_for_layout_settled(page)
                    expect(point).to_have_attribute("data-selected", "true")
                    boxes = panel.locator(".chart-frame").evaluate_all(
                        "els=>els.map(e=>{const r=e.getBoundingClientRect();return {left:r.left,right:r.right,width:r.width}})"
                    )
                    assert boxes and all(
                        box["left"] >= 0
                        and box["right"] <= width + 1
                        and box["width"] >= 240
                        for box in boxes
                    ), boxes
                    expect(panel).to_contain_text("온도 <raw>")
                    if is_vector:
                        expect(panel).to_contain_text("수율 <raw>")
                    layouts.append(
                        {
                            "locale": locale,
                            "width": width,
                            "vector": is_vector,
                            "boxes": boxes,
                        }
                    )
                    panel.screenshot(
                        path=str(
                            output
                            / f"progress-{is_vector}-{is_mixed}-{locale}-{width}.png"
                        )
                    )
            point.press("Escape")
            expect(point).to_have_attribute("data-selected", "false")
            point.focus()
            point.press("ArrowRight")
            assert observed.locator("[data-point-id]").evaluate_all(
                "els=>els.some(e=>e===document.activeElement)"
            )
            panel.get_by_label("X factor", exact=True).select_option("z")
            expect(space.locator('[data-selected="true"]')).to_have_count(0)
            page.reload(wait_until="domcontentloaded")
            wait_for_bayesian_ready(page, "en", ROUTE)
            expect(
                page.locator(
                    '[data-chart-id="bo-progress-observed"] [data-point-id$=":measured"]'
                )
            ).to_have_count(3)
            after = page.request.get(url).json()
            assert (
                hashlib.sha256(json.dumps(after, sort_keys=True).encode()).hexdigest()
                == before
            )
            if not is_vector:
                space = page.locator('[data-chart-id="bo-progress-space"]')
                selected = space.locator("[data-point-id]").first
                selected.focus()
                selected.press("Enter")
                expect(selected).to_have_attribute("data-selected", "true")
                pending = study["trials"][3]
                abandoned = page.request.post(
                    url + f"/trials/{pending['trial_id']}/abandon",
                    headers={"Origin": base},
                    data={
                        "expected_history_revision_id": study["observation_history"][
                            "history_revision_id"
                        ]
                    },
                )
                assert abandoned.status == 200, abandoned.text()
                updated = page.request.get(url).json()
                assert (
                    updated["observation_history"]["observation_history_sha256"]
                    == study["observation_history"]["observation_history_sha256"]
                )
                page.locator("#bo-replicates-title").click()
                page.get_by_role("button", name="Refresh trials", exact=True).click()
                expect(
                    space.locator(".bo-progress-abandoned[data-point-id]")
                ).to_have_count(1)
                expect(space.locator('[data-selected="true"]')).to_have_count(0)
        assert not writes, writes
        assert not errors, errors
        receipt = {
            "synthetic": True,
            "status": "succeeded",
            "browser": browser.version,
            "layouts": layouts,
            "api_writes_during_views": len(writes),
            "pageerrors": errors,
            "source_unchanged": True,
            "target_distance": True,
            "vector_desirability": True,
            "pending_not_measured": True,
            "keyboard_pin_escape": True,
            "locale_resize_preserve_pin": True,
            "restore": True,
            "mixed_full_labels_preserved": True,
            "pending_state_change_clears_pin": True,
        }
        (output / "progress-receipt.json").write_text(
            json.dumps(receipt, indent=2), encoding="utf-8"
        )
        return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            print(
                json.dumps(
                    verify_bo_progress(browser, args.base_url, args.output), indent=2
                )
            )
        finally:
            browser.close()
