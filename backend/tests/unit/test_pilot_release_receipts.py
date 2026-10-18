"""Fail-closed receipt plumbing; this is not native archive/browser evidence."""

from __future__ import annotations

import copy
import importlib
from pathlib import Path

import pytest


@pytest.fixture
def modules(monkeypatch):
    root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    monkeypatch.syspath_prepend(str(root / "tests/e2e"))
    return importlib.import_module("verify_linux_release"), importlib.import_module(
        "linux_release_journey"
    )


@pytest.fixture
def receipt_set(modules):
    _, journey = modules

    def entry(index, method, result=None):
        return {
            "envelope": {
                "analysis_id": str(index),
                "method_id": method,
                "result": result or {"value": index},
            }
        }

    def report(index):
        return {
            "path": f"{index}.html",
            "descriptor": {"export_id": str(index), "sha256": f"{index:064x}"},
        }

    groups = [
        entry(i, method)
        for i, method in enumerate(
            ("eda.equal_variances", "hypothesis.kruskal_wallis", "hypothesis.two_sample_t")
        )
    ]
    variances = [
        entry(3 + i, "quality.two_variances", {"method": method})
        for i, method in enumerate(("brown_forsythe", "normal_f"))
    ]
    for item in variances:
        item["execution_evidence"] = "visible built/source UI form with preflight"
    prediction = entry(5, "regression.gaussian_process")
    prediction.update(
        status="succeeded",
        generic_report=report(8),
        prediction={"rows": [{"value": 0.000001}]},
        saved={"reports": [report(9), report(10)]},
    )
    receipt = {
        "schema_version": 1,
        "status": "succeeded",
        "phase": "initial",
        "ingestion": {"status": "succeeded"},
        "groups": {
            "status": "succeeded",
            "analyses": groups,
            "reports": [report(i) for i in range(6)],
        },
        "two_variances": {
            "status": "succeeded",
            "analyses": variances,
            "reports": [report(6), report(7)],
            "preflight": {"eligible": True},
        },
        "prediction": prediction,
        "legacy": {
            "status": "succeeded",
            "analysis_post_count": 0,
            "seed": {
                "status": "seeded_new_workspace",
                "existing_records_modified": False,
                "analysis_calculations_executed": 0,
                "source_commit": "0849aaa279e34a612c5c65d350cfccf220fe581e",
            },
            "analyses": [entry(i, "legacy") for i in range(6, 9)],
            "reports": [report(i) for i in range(11, 17)],
        },
    }
    cases = []
    for index, item in enumerate(receipt["legacy"]["analyses"]):
        envelope = item["envelope"]
        envelope["method_id"] = groups[index]["envelope"]["method_id"]
        envelope["method_version"] = "0.2.0" if index == 0 else "0.1.0"
        envelope["result"]["schema_version"] = 2 if index == 0 else 1
        cases.append(
            {
                "analysis_id": envelope["analysis_id"],
                "method_id": envelope["method_id"],
                "result_payload_sha256": journey.payload_digest(envelope["result"]),
                "artifact_file_sha256": f"{index + 21:064x}",
            }
        )
    receipt["legacy"]["seed"]["cases"] = cases
    for index, item in enumerate(receipt["legacy"]["reports"]):
        case = cases[index // 2]
        item["descriptor"].update(
            analysis_id=case["analysis_id"], source_result_sha256=case["artifact_file_sha256"]
        )
    resumed = {
        "schema_version": 1,
        "status": "succeeded",
        "phase": "resume",
        "analyses": [
            {
                "analysis_id": item["envelope"]["analysis_id"],
                "result_payload_sha256": journey.payload_digest(item["envelope"]["result"]),
            }
            for item in journey.pilot_analyses(receipt)
        ],
        "reports": [item["descriptor"] for item in journey.pilot_reports(receipt)],
        "prediction": {
            "same_saved_model_prediction": True,
            "rows": prediction["prediction"]["rows"],
        },
    }
    offline = {
        "schema_version": 1,
        "status": "succeeded",
        "phase": "offline",
        "reports": resumed["reports"],
    }
    return (
        {"pilot_receipt": receipt},
        [{"pilot_receipt": copy.deepcopy(resumed)} for _ in range(2)],
        {"pilot_receipt": copy.deepcopy(offline)},
    )


def test_pilot_receipts_add_exact_evidence_without_replacing_core(modules, receipt_set):
    verifier, journey = modules
    smoke, restarts, offline = receipt_set
    assert verifier.require_pilot_receipts(smoke, restarts, offline) == {
        "schema_version": 1,
        "status": "passed",
        "analysis_count": 9,
        "report_count": 17,
        "restart_count": 2,
        "offline_report_count": 17,
        "legacy_analysis_count": 3,
    }
    assert len(journey.pilot_analyses(smoke["pilot_receipt"])) == 9
    assert len(journey.pilot_reports(smoke["pilot_receipt"])) == 17


@pytest.mark.parametrize(
    "missing", ["ingestion", "groups", "prediction", "two_variances", "legacy"]
)
def test_each_actual_ui_journey_is_required(modules, receipt_set, missing):
    verifier, _ = modules
    smoke, restarts, offline = receipt_set
    del smoke["pilot_receipt"][missing]
    with pytest.raises(ValueError, match="Incomplete pilot UI"):
        verifier.require_pilot_receipts(smoke, restarts, offline)


@pytest.mark.parametrize("phase", [0, 1, 2])
def test_report_omission_or_byte_change_fails_each_resume_and_offline(modules, receipt_set, phase):
    verifier, _ = modules
    smoke, restarts, offline = receipt_set
    stage = [*restarts, offline][phase]["pilot_receipt"]
    stage["reports"][0]["sha256"] = "f" * 64
    with pytest.raises(ValueError, match="report bytes"):
        verifier.require_pilot_receipts(smoke, restarts, offline)


def test_api_only_variance_cannot_replace_visible_form_evidence(modules, receipt_set):
    verifier, _ = modules
    smoke, restarts, offline = receipt_set
    smoke["pilot_receipt"]["two_variances"]["analyses"][0]["execution_evidence"] = "API smoke"
    with pytest.raises(ValueError, match="API-only"):
        verifier.require_pilot_receipts(smoke, restarts, offline)


def test_changed_prediction_or_source_cannot_pass_resume(modules, receipt_set):
    verifier, _ = modules
    smoke, restarts, offline = receipt_set
    restarts[1]["pilot_receipt"]["prediction"]["rows"] = [{"value": 0}]
    with pytest.raises(ValueError, match="GP prediction differs"):
        verifier.require_pilot_receipts(smoke, restarts, offline)
    restarts[1]["pilot_receipt"]["prediction"]["rows"] = smoke["pilot_receipt"]["prediction"][
        "prediction"
    ]["rows"]
    restarts[0]["pilot_receipt"]["analyses"][0]["result_payload_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="analysis payload"):
        verifier.require_pilot_receipts(smoke, restarts, offline)


@pytest.mark.parametrize(
    "field,value",
    [
        ("existing_records_modified", True),
        ("analysis_calculations_executed", 1),
        ("source_commit", "f" * 40),
    ],
)
def test_legacy_rewrites_or_new_calculation_cannot_be_claimed_as_old_result(
    modules, receipt_set, field, value
):
    verifier, _ = modules
    smoke, restarts, offline = receipt_set
    smoke["pilot_receipt"]["legacy"]["seed"][field] = value
    with pytest.raises(ValueError, match="Legacy"):
        verifier.require_pilot_receipts(smoke, restarts, offline)
