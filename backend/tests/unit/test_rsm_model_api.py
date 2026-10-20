from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.v1.schemas.doe import (
    DoeResponseSurfaceAnalysisResponse,
    ResponseOptimizerCreateRequest,
)
from app.core.config import Settings
from app.main import create_app
from app.services.dedicated_report_renderers import render_doe_analysis_body
from app.services.response_optimizer import (
    _load_source_objectives,
    _source_model_eligibility_issues,
)
from app.statistics.response_optimizer import _predict


def test_rsm_presets_backward_restore_and_optimizer_use_final_terms(tmp_path):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/doe-designs/response-surface",
            json={
                "name": "Synthetic final-model workflow",
                "factors": [{"name": name, "low": 10, "high": 20} for name in "ABCD"],
                "ccd_type": "circumscribed",
                "axial_points_confirmed": True,
                "center_point_mode": "recommended",
                "randomize": False,
                "randomization_seed": 7,
            },
        )
        assert response.status_code == 201, response.text
        design = response.json()
        base = f"/api/v1/doe-designs/response-surface/{design['design_id']}"
        errors = iter([-0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3])
        values = []
        for run in design["runs"]:
            a, b = run["coded_levels"]["A"], run["coded_levels"]["B"]
            value = 20 + 3 * a - 2 * b + 4 * a * b + 5 * a * a
            if run["center_point"]:
                value += next(errors)
            values.append({"run_order": run["run_order"], "value": value})
        saved = client.put(
            base + "/responses", json={"response_name": "Y", "unit": "g", "values": values}
        )
        assert saved.status_code == 200, saved.text
        for preset, count in [
            ("linear", 5),
            ("linear_squares", 9),
            ("linear_interactions", 11),
            ("full_quadratic", 15),
        ]:
            catalog = client.get(base + "/term-catalog", params={"term_preset": preset})
            assert catalog.status_code == 200, catalog.text
            assert len(catalog.json()["terms"]) == count
            fitted = client.post(
                base + "/analyses", json={"response_name": "Y", "term_preset": preset}
            )
            assert fitted.status_code == 201, fitted.text
            analysis = fitted.json()
            assert analysis["result"]["sample"]["parameter_count"] == count
            assert analysis["result"]["model_selection"]["method"] == "none"
            assert analysis["result"]["model_selection"]["removed_term_ids"] == []
            assert client.get(base + f"/analyses/{analysis['analysis_id']}").json() == analysis
            if preset == "linear":
                assert not analysis["result"]["stationary_point"]["available"]
        fitted = client.post(
            base + "/analyses",
            json={
                "response_name": "Y",
                "model_selection": {"method": "backward_elimination"},
            },
        )
        assert fitted.status_code == 201, fitted.text
        analysis = fitted.json()
        assert analysis["result"]["sample"]["parameter_count"] == 5
        assert analysis["result"]["final_basis"]["term_ids"] == [
            "intercept",
            "factor_1",
            "factor_2",
            "factor_1:factor_2",
            "factor_1^2",
        ]
        assert client.get(base + f"/analyses/{analysis['analysis_id']}").json() == analysis
        # This center-only-noise fixture is intentionally non-normal. Acknowledge
        # its actual advisories; the guard itself has separate rejection tests.
        required = [
            issue.code
            for issue in _source_model_eligibility_issues(
                DoeResponseSurfaceAnalysisResponse.model_validate(analysis),
                0.95,
            )
            if issue.severity == "acknowledgment_required"
        ]
        assert "response_optimizer_source_residual_normality_severe" in required
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
                    "acknowledged_source_warning_codes": required,
                }
            ),
        )
        for point in analysis["result"]["contour"]["points"][::41]:
            a, b = point["x_coded"], point["y_coded"]
            expected = 20 + 3 * a - 2 * b + 4 * a * b + 5 * a * a
            actual = {"A": point["x_actual"], "B": point["y_actual"], "C": 16, "D": 13}
            assert point["predicted"] == pytest.approx(expected, abs=1e-11)
            assert _predict(objectives[0].model, actual) == pytest.approx(expected, abs=1e-11)
        body = render_doe_analysis_body(analysis, "response_surface", "en")
        assert any(section.section_id == "selection" for section in body.sections)
        rejected = client.post(
            base + "/analyses",
            json={
                "response_name": "Y",
                "term_preset": "linear_squares",
                "model_selection": {
                    "method": "backward_elimination",
                    "term_policies": [
                        {"term_id": "factor_1", "disposition": "excluded"},
                        {"term_id": "factor_1^2", "disposition": "forced"},
                    ],
                },
            },
        )
        assert rejected.status_code == 409
        assert rejected.json()["error"]["code"] == "doe_factorial_selection_hierarchy_invalid"
