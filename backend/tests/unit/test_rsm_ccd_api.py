import hashlib
import json
import sqlite3
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.v1.schemas.doe import ResponseOptimizerCreateRequest
from app.core.config import Settings
from app.main import create_app
from app.services.response_optimizer import _load_source_objectives
from app.statistics.response_optimizer import _predict
from app.statistics.response_surface import (
    ResponseSurfaceDesignOptions,
    ResponseSurfaceFactor,
    canonical_response_surface_design_payload,
    generate_central_composite_design,
)
from app.storage.metadata import metadata_db_path


def test_legacy_canonical_payload_omits_new_defaults_and_keeps_hash():
    design = generate_central_composite_design(
        [ResponseSurfaceFactor(name, 10, 20) for name in "ABCD"],
        ResponseSurfaceDesignOptions("rotatable", 1, 1, 5, False, 7),
    )
    assert design.schema_version == 2 and len(design.runs) == 29
    payload = canonical_response_surface_design_payload(
        schema_version=2,
        family=design.family,
        alpha=design.alpha,
        factors=design.factors,
        options=design.options,
        runs=design.runs,
    )
    assert "coding" not in payload and "ccd_type" not in payload["options"]
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    assert hashlib.sha256(encoded).hexdigest() == design.design_sha256


@pytest.mark.parametrize(
    "kind,cube,axial",
    [
        ("circumscribed", (10, 20), (5, 25)),
        ("inscribed", (12.5, 17.5), (10, 20)),
        ("face_centered", (10, 20), (10, 20)),
    ],
)
def test_ccd_create_analysis_contour_optimizer_coding_and_restore(tmp_path, kind, cube, axial):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        request = {
            "name": "Synthetic CCD",
            "factors": [{"name": name, "low": 10, "high": 20} for name in "ABCD"],
            "ccd_type": kind,
            "axial_points_confirmed": True,
            "center_points": 7,
            "randomize": False,
            "randomization_seed": 7,
        }
        created = client.post("/api/v1/doe-designs/response-surface", json=request)
        assert created.status_code == 201, created.text
        design = created.json()
        assert design["design_schema_version"] == 3 and design["run_count"] == 31
        coding = design["coding"]["A"]
        assert (coding["factorial_low"], coding["factorial_high"]) == cube
        assert (coding["axial_low"], coding["axial_high"]) == axial
        base = f"/api/v1/doe-designs/response-surface/{design['design_id']}"
        assert client.get(base).json() == design
        values = []
        center_errors = iter([-0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3])
        for run in design["runs"]:
            a, b = (run["coded_levels"][name] for name in "AB")
            value = 20 + 3 * a - 2 * b + 4 * a * b + 5 * a * a
            if run["point_type"] == "center":
                value += next(center_errors)
            values.append({"run_order": run["run_order"], "value": value})
        assert (
            client.put(
                base + "/responses", json={"response_name": "Y", "values": values}
            ).status_code
            == 200
        )
        response = client.post(base + "/analyses", json={"response_name": "Y"})
        assert response.status_code == 201, response.text
        analysis = response.json()
        assert analysis["result"]["coding"]["factors"] == design["coding"]
        assert analysis["result"]["sample"]["parameter_count"] == 15
        catalog = client.get("/api/v1/doe-designs/response-surface-analyses").json()
        assert catalog["analyses"][0]["eligibility_status"] not in {
            "integrity_error",
            "incompatible_method_version",
        }
        # Read the service's actual optimizer source, not a separately reconstructed test model.
        objectives, _, _ = _load_source_objectives(
            settings,
            design_id=UUID(design["design_id"]),
            body=ResponseOptimizerCreateRequest.model_validate(
                {
                    "objectives": [
                        {
                            "source_analysis_id": analysis["analysis_id"],
                            "goal": "maximize",
                            "lower": -50,
                            "target": 100,
                        }
                    ],
                    # This fixture deliberately puts noise only at centers, not normal residuals.
                    "acknowledged_source_warning_codes": [
                        "response_optimizer_source_residual_normality_severe"
                    ],
                }
            ),
        )
        for point in analysis["result"]["contour"]["points"][::19]:
            actual = {name: 15.0 for name in "ABCD"}
            actual.update(A=point["x_actual"], B=point["y_actual"])
            a, b = point["x_coded"], point["y_coded"]
            expected = 20 + 3 * a - 2 * b + 4 * a * b + 5 * a * a
            assert point["predicted"] == pytest.approx(expected, abs=1e-10)
            assert _predict(objectives[0].model, actual) == pytest.approx(
                point["predicted"], abs=1e-11
            )
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            before = connection.execute(
                "SELECT result_json, result_sha256 FROM experiment_design_analyses"
            ).fetchall()
        assert client.get(base + f"/analyses/{analysis['analysis_id']}").json() == analysis
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            assert (
                connection.execute(
                    "SELECT result_json, result_sha256 FROM experiment_design_analyses"
                ).fetchall()
                == before
            )


def test_ccc_requires_confirmation_and_rejects_mode_conflict(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body = {
            "factors": [{"name": name, "low": 10, "high": 20} for name in "AB"],
            "ccd_type": "circumscribed",
            "randomization_seed": 7,
        }
        assert client.post("/api/v1/doe-designs/response-surface", json=body).status_code == 422
        body.update(axial_points_confirmed=True, alpha_mode="face_centered")
        assert client.post("/api/v1/doe-designs/response-surface", json=body).status_code == 422
