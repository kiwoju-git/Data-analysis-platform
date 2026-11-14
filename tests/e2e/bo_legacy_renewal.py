"""Synthetic absent-policy receipt -> explicit built-UI renewal, without refitting."""

import hashlib
import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from playwright.sync_api import expect


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def verify_legacy_renewal(page, api: str, model: dict, output: Path, workspace: Path):
    output.mkdir(parents=True, exist_ok=True)
    workspace = workspace.resolve(strict=True)
    assert workspace.name == "workspace"
    assert (workspace.parent / ".datalab-e2e-owned").read_text(encoding="utf-8") == str(workspace)
    database = workspace / "db" / "metadata.sqlite3"
    assert database.resolve(strict=True).is_relative_to(workspace)
    study = page.request.get(api).json()
    assert study["pending_trial_count"] == 0
    source = {"schema_version": 2, "expected_study_version_id": study["study_version_id"],
        "expected_definition_sha256": study["definition_sha256"],
        "expected_history_revision_id": study["observation_history"]["history_revision_id"],
        "expected_history_sha256": study["observation_history"]["observation_history_sha256"],
        "expected_trial_count": study["trial_count"], "model_id": model["model_id"],
        "expected_model_sha256": model["snapshot_sha256"],
        "duplicate_tolerance": model["fit"]["search"]["duplicate_tolerance"]}
    headers = {"Origin": api.split("/api/")[0]}
    candidate = page.request.post(api + "/candidate-revisions", headers=headers, data={
        **source, "request_id": str(uuid4()), "candidate_set_id": str(uuid4()),
        "name": "Synthetic legacy renewal", "expected_head_revision_id": None,
        "source": {"kind": "explicit_rows", "points": [{"x": x} for x in (0.25, 1.25, 2.25, 3.25, 4.25, 5.25)]}})
    assert candidate.status == 201, candidate.text()
    revision = candidate.json()["revision"]
    selected = page.request.post(api + "/augmentations", headers=headers, data={
        **source, "request_id": str(uuid4()), "candidate_revision_id": revision["revision_id"],
        "expected_rows_sha256": revision["rows_sha256"], "policy": "refine_ei_then_desirability_sd_v1",
        "batch_size": 2, "total_trial_budget": 20})
    assert selected.status == 201, selected.text()
    selected = selected.json()
    selection_id = selected["selection_id"]
    query = "SELECT config_json,config_sha256,result_json,result_sha256 FROM bayesian_planning_selections WHERE selection_id=? AND study_version_id=?"
    key = (selection_id, study["study_version_id"])
    with sqlite3.connect(database) as db:
        original = db.execute(query, key).fetchone()
        assert original is not None
        assert hashlib.sha256(original[0].encode("utf-8")).hexdigest() == original[1] == selected["config_sha256"]
        assert hashlib.sha256(original[2].encode("utf-8")).hexdigest() == original[3] == selected["result_sha256"]
        assert json.loads(original[0]) == selected["request"]
        # The typed API supplies this nullable schema default; it is absent in
        # stored v1 refine traces. Do not reserialize API output as stored bytes.
        comparable = json.loads(original[2])
        assert "response_uncertainty" not in comparable["augmentation"]
        comparable["augmentation"]["response_uncertainty"] = None
        assert comparable == selected["calculation"]
        historical = json.loads(original[2])
        removed = 0
        for row in historical["selected_rows"]:
            if row["acquisition"] is not None:
                assert row["acquisition"].pop("numerical_policy") == "positive_beta_integral_v2"
                removed += 1
        assert removed > 0
        payload = _encoded(historical)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        changed = db.execute("UPDATE bayesian_planning_selections SET result_json=?,result_sha256=? WHERE selection_id=? AND study_version_id=? AND config_json=? AND config_sha256=? AND result_json=? AND result_sha256=?", (payload, digest, *key, *original))
        assert changed.rowcount == 1
    with sqlite3.connect(database) as db:
        old_bytes = db.execute(query, key).fetchone()
    endpoint = api + "/augmentations/" + selection_id
    old = page.request.get(endpoint).json()
    assert old["result_sha256"] == digest
    writes, errors = [], []
    page.on("request", lambda request: writes.append(request.url) if request.method in {"POST", "PUT", "DELETE"} and "/api/" in request.url else None)
    page.on("pageerror", lambda error: errors.append(str(error)))
    panel = page.get_by_role("region", name="Experimental augmentation", exact=True)
    panel.locator("summary").filter(has_text="Open exact saved selection").click()
    panel.get_by_label("Saved automatic selection ID", exact=True).fill(selection_id)
    panel.get_by_role("button", name="Open exact saved selection", exact=True).click()
    expect(panel.get_by_role("status")).to_contain_text("earlier EI numerical policy")
    confirm = panel.get_by_role("button", name="Confirm entire pending batch", exact=True)
    expect(confirm).to_be_disabled()
    assert writes == []
    assert page.request.get(api).json() == study
    with page.expect_response(lambda response: response.url == endpoint + "/renew" and response.request.method == "POST", timeout=90000) as response:
        panel.get_by_role("button", name="Renew saved recommendation", exact=True).click()
    assert response.value.status == 201, response.value.text()
    renewal = response.value.json()
    renewed, lineage = renewal["selection"], renewal["lineage"]
    assert lineage["original_selection_id"] == selection_id
    assert lineage["original_config_sha256"] == old["config_sha256"]
    assert lineage["original_result_sha256"] == old["result_sha256"]
    assert lineage["numerical_policy"] == "positive_beta_integral_v2"
    assert renewed["selection_id"] != selection_id and renewed["confirmed_batch_id"] is None
    assert renewed["request"] == {**old["request"], "request_id": renewed["request"]["request_id"]}
    assert all(row["acquisition"] is None or row["acquisition"]["numerical_policy"] == "positive_beta_integral_v2" for row in renewed["calculation"]["selected_rows"])
    expect(panel.get_by_text("Renewed review; not yet confirmed", exact=True)).to_be_visible()
    assert writes == [endpoint + "/renew"]
    assert page.request.get(api).json() == study
    assert page.request.get(api + "/augmentations/" + renewed["selection_id"]).json() == renewed
    assert page.request.get(api + "/augmentations/" + renewed["selection_id"] + "/renewal").json() == lineage
    review = panel.get_by_role("region", name="Saved automatic selection", exact=True)
    expect(review).to_contain_text(renewed["result_sha256"])
    rows = review.get_by_role("table", name="Automatic selection trace", exact=True).locator("tbody tr")
    expect(rows).to_have_count(len(renewed["calculation"]["selected_rows"]))
    for index, row in enumerate(renewed["calculation"]["selected_rows"]):
        cells = rows.nth(index).locator("td")
        assert float(cells.nth(0).inner_text()) == row["actual_coordinates"]["x"] <= 6
        assert float(cells.nth(2).inner_text().splitlines()[0]) == renewed["calculation"]["augmentation"]["steps"][index]["score"]
    page.screenshot(path=output / "renewed-review.png", full_page=True)
    expect(confirm).to_be_enabled()
    confirm_url = api + "/augmentations/" + renewed["selection_id"] + "/confirm"
    with page.expect_response(lambda response: response.url == confirm_url and response.request.method == "POST", timeout=90000) as response:
        confirm.click()
    assert response.value.status == 201, response.value.text()
    batch = response.value.json()
    expect(page.get_by_text(batch["batch_id"], exact=True).first).to_be_visible()
    page.screenshot(path=output / "confirmed-batch.png", full_page=True)
    replay = page.request.post(confirm_url, headers=headers, data={"expected_config_sha256": renewed["config_sha256"], "expected_result_sha256": renewed["result_sha256"]})
    assert replay.status == 201 and replay.json() == batch
    assert page.request.get(api).json()["trial_count"] == study["trial_count"] + 2
    restored_old = page.request.get(endpoint).json()
    assert {key: value for key, value in restored_old.items() if key != "source_is_current"} == {key: value for key, value in old.items() if key != "source_is_current"}
    with sqlite3.connect(database) as db:
        assert db.execute(query, key).fetchone() == old_bytes
    assert writes == [endpoint + "/renew", confirm_url]
    assert not errors, errors
    receipt = {"synthetic": True, "fixture": "absent_numerical_policy", "source": source,
        "original_selection": old, "fixture_current_stored_bytes": original,
        "original_stored_bytes": old_bytes, "renewal": renewal,
        "batch": batch, "old_bytes_unchanged": True, "fit_posts": 0, "pageerrors": errors}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt
