"""Closure-preserving saved diagnostics use the frozen model, never refit."""

import math
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.workspace_backup import backup_workspace, restore_workspace
from tests.unit.test_bo_mixed_planning_api import fit_options, source
from tests.unit.test_bo_mixture_lifecycle_api import observations, request


@pytest.mark.parametrize("mixed", [False, True])
def test_mixture_matrix_and_loo_save_restart_and_stored_report(tmp_path, mixed, monkeypatch):
    settings = Settings(workspace_root=tmp_path / "mixture diagnostic workspace")
    with TestClient(create_app(settings)) as client:
        created = client.post("/api/v1/bayesian-studies/mixture", json=request(mixed))
        assert created.status_code == 201, created.text
        study = created.json()
        base = "/api/v1/bayesian-studies/" + study["study_id"]
        completed = client.put(base + "/observations/batch", json=observations(study))
        assert completed.status_code == 200, completed.text
        study = completed.json()["study"]
        fitted = client.post(
            base + "/mixture-planning-models",
            json={
                **source(study),
                "request_id": str(uuid4()),
                "fit": fit_options(),
            },
        )
        assert fitted.status_code == 201, fitted.text
        model = fitted.json()
        holds = study["trials"][0]["actual_coordinates"]
        views = []
        for kind in ("profiler_matrix", "conditional_loo"):
            body = {
                "kind": kind,
                "expected_model_sha256": model["snapshot_sha256"],
                "expected_history_sha256": model["history_sha256"],
            }
            if kind == "profiler_matrix":
                body.update(holds=holds, points_per_axis=3)
            evaluated = client.post(
                base + "/planning-models/" + model["model_id"] + "/view-evaluations", json=body
            )
            assert evaluated.status_code == 200, evaluated.text
            receipt = evaluated.json()
            payload = receipt["payload"]
            if kind == "profiler_matrix":
                assert payload["schema_version"] == 2
                assert payload["mixture_domain"] == model["design_domain"]
                axes = {axis["factor_id"]: axis for axis in payload["axes"]}
                assert set(axes) == set(holds)
                assert axes["fixed"]["points"] == []
                assert axes["fixed"]["path"]["unavailable_reason"]
                for axis in axes.values():
                    for point in axis["points"]:
                        actual = point["actual_coordinates"]
                        assert math.isclose(
                            actual["a"] + actual["b"] + actual["fixed"], 1, abs_tol=4e-15
                        )
                        assert actual["fixed"] == 0.1
                        assert point["prediction_source"] == "completed_observations_base_posterior"
                axis_points = axes["a"]["points"]
                assert (
                    axis_points[0]["actual_coordinates"]["b"]
                    != axis_points[-1]["actual_coordinates"]["b"]
                )
                check = client.post(
                    base + "/mixture-planning-models/" + model["model_id"] + "/evaluate",
                    json={
                        "expected_model_sha256": model["snapshot_sha256"],
                        "points": [point["actual_coordinates"] for point in axis_points],
                    },
                )
                assert check.status_code == 200, check.text
                for left, right in zip(axis_points, check.json()["items"], strict=True):
                    assert left["response_predictions"] == right["response_predictions"]
            else:
                assert payload["calculation"]["model_refit"] is False
                assert payload["calculation"]["responses"][0]["n_scored"] == 8
            saved = client.post(
                base + "/views",
                json={
                    "request_id": str(uuid4()),
                    "receipt_id": receipt["receipt_id"],
                    "expected_model_sha256": model["snapshot_sha256"],
                    "expected_request_sha256": receipt["request_sha256"],
                    "expected_view_sha256": receipt["view_sha256"],
                },
            )
            assert saved.status_code == 201, saved.text
            views.append(saved.json())

    def forbidden(*args, **kwargs):
        raise AssertionError("Saved diagnostic reads and reports must not fit/evaluate")

    monkeypatch.setattr("app.services.bo_planning._run", forbidden)
    archive, restored_root = tmp_path / "mixture views.zip", tmp_path / "restored mixture views"
    backup_workspace(settings.workspace_root, archive)
    restore_workspace(archive, restored_root)
    with TestClient(create_app(Settings(workspace_root=restored_root))) as client:
        from app.services.bo_view_report import render_view_body

        for view in views:
            restored = client.get(base + "/views/" + view["view_id"])
            assert restored.status_code == 200, restored.text
            assert restored.json() == view
            # The report function accepts exactly the immutable, validated saved payload.
            document = render_view_body({"saved_view": view}, locale="en")
            assert document
            descriptor_response = client.get(base + "/views/" + view["view_id"] + "/report-source")
            assert descriptor_response.status_code == 200, descriptor_response.text
            descriptor = descriptor_response.json()
            exported = client.post(
                "/api/v1/reports",
                json={
                    "source": descriptor["source"],
                    "expected_source_ref_sha256": descriptor["source_ref_sha256"],
                    "locale": "en",
                },
            )
            assert exported.status_code == 201, exported.text
            artifact = exported.json()
            download = client.post(
                "/api/v1/reports/" + artifact["export_id"] + "/download",
                json={
                    "source": descriptor["source"],
                    "expected_sha256": artifact["sha256"],
                },
            )
            assert download.status_code == 200, download.text
            assert "<svg" in download.text and view["view_sha256"] in download.text
            assert "default-src 'none'" in download.headers["Content-Security-Policy"]
            if view["kind"] == "profiler_matrix":
                assert "co-vary" in download.text
                assert "fixed_component" in download.text


@pytest.mark.parametrize("collapsed", [True, False])
def test_process_profile_boundaries_budget_save_and_report(tmp_path, collapsed, monkeypatch):
    settings = Settings(workspace_root=tmp_path / "process profile workspace")
    definition = request()
    definition["mixture"]["components"] = [
        {"factor_id": key, "name": key.upper(), "low": 0.0, "high": 1.0, "unit": "g"}
        for key in ("a", "b")
    ]
    definition["process_factors"] = [
        {
            "factor_id": "p",
            "name": "Process",
            "unit": "C",
            "low": 0.0,
            "high": 1.0 if collapsed else 10000.0,
            "domain_kind": "continuous" if collapsed else "discrete_numeric",
            "step": None if collapsed else 1.0,
            "display_decimals": None if collapsed else 0,
        }
    ]
    definition["constraints"] = (
        [
            {
                "constraint_id": "cap",
                "name": "Conditional process cap",
                "terms": [
                    {"factor_id": "p", "coefficient": 1.0},
                    {"factor_id": "a", "coefficient": -1.0},
                ],
                "relation": "less_than_or_equal",
                "bound": 0.0,
            }
        ]
        if collapsed
        else [
            {
                "constraint_id": "lo",
                "name": "Process lower limit",
                "terms": [{"factor_id": "p", "coefficient": 1.0}],
                "relation": "greater_than_or_equal",
                "bound": 100.2,
            },
            {
                "constraint_id": "hi",
                "name": "Process upper limit",
                "terms": [{"factor_id": "p", "coefficient": 1.0}],
                "relation": "less_than_or_equal",
                "bound": 9900.8,
            },
        ]
    )
    with TestClient(create_app(settings)) as client:
        created = client.post("/api/v1/bayesian-studies/mixture", json=definition)
        assert created.status_code == 201, created.text
        study = created.json()
        base = "/api/v1/bayesian-studies/" + study["study_id"]
        completed = client.put(base + "/observations/batch", json=observations(study))
        assert completed.status_code == 200, completed.text
        study = completed.json()["study"]
        fitted = client.post(
            base + "/mixture-planning-models",
            json={**source(study), "request_id": str(uuid4()), "fit": fit_options()},
        )
        assert fitted.status_code == 201, fitted.text
        model = fitted.json()
        holds = {"a": 0.0, "b": 1.0, "p": 0.0} if collapsed else {"a": 0.4, "b": 0.6, "p": 5000.0}
        evaluated = client.post(
            base + "/planning-models/" + model["model_id"] + "/view-evaluations",
            json={
                "kind": "profiler_matrix",
                "expected_model_sha256": model["snapshot_sha256"],
                "expected_history_sha256": model["history_sha256"],
                "holds": holds,
                "points_per_axis": 2 if collapsed else 21,
            },
        )
        assert evaluated.status_code == 200, evaluated.text
        receipt = evaluated.json()
        payload = receipt["payload"]
        axes = {axis["factor_id"]: axis for axis in payload["axes"]}
        assert set(axes) == {"a", "b", "p"}
        process = axes["p"]
        assert process["path"]["unavailable_reason"] is None
        values = [point["actual_coordinates"]["p"] for point in process["points"]]
        assert len(values) == len(set(values))
        if collapsed:
            assert values == [0.0]
            assert process["path"]["feasible_interval"] == [0.0, 0.0]
            assert len(axes["a"]["points"]) == 2
        else:
            assert len(values) == 21
            assert process["available_level_count"] == 9800
            assert (values[0], values[-1]) == (101, 9900)
            assert all(value.is_integer() for value in values)
        assert payload["point_count"] == sum(len(axis["points"]) for axis in axes.values())
        saved = client.post(
            base + "/views",
            json={
                "request_id": str(uuid4()),
                "receipt_id": receipt["receipt_id"],
                "expected_model_sha256": model["snapshot_sha256"],
                "expected_request_sha256": receipt["request_sha256"],
                "expected_view_sha256": receipt["view_sha256"],
            },
        )
        assert saved.status_code == 201, saved.text
        view = saved.json()

        def forbidden(*args, **kwargs):
            raise AssertionError("Saved process paths must not refit or evaluate")

        monkeypatch.setattr("app.services.bo_planning._run", forbidden)
        assert client.get(base + "/views/" + view["view_id"]).json() == view
        descriptor = client.get(base + "/views/" + view["view_id"] + "/report-source").json()
        exported = client.post(
            "/api/v1/reports",
            json={
                "source": descriptor["source"],
                "expected_source_ref_sha256": descriptor["source_ref_sha256"],
                "locale": "en",
            },
        )
        assert exported.status_code == 201, exported.text
        artifact = exported.json()
        downloaded = client.post(
            "/api/v1/reports/" + artifact["export_id"] + "/download",
            json={"source": descriptor["source"], "expected_sha256": artifact["sha256"]},
        )
        assert downloaded.status_code == 200, downloaded.text
        if not collapsed:
            assert "21 of 9800: sampled subset" in downloaded.text
