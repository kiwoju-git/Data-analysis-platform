import hashlib
import math

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

URL = "/api/v1/bayesian-studies/target-curve-preview"


def test_curve_tail_underflow_is_explicit():
    from app.api.v1.schemas.bo_curve_preview import CurvePreviewRequest
    from app.services.bo_curve_preview import preview_target_curve

    body = request()
    body.update(plot_lower=-10.0, plot_upper=10.0, assumed_distribution=None)
    body["controls"].update(lower_desirability=1e-300, upper_desirability=1e-300)
    result = preview_target_curve(CurvePreviewRequest.model_validate(body))
    assert result.gaussian_underflow_count > 0
    assert result.gaussian_underflow_count == sum(p.gaussian == 0 for p in result.points)


def test_large_finite_plot_grid_has_no_intermediate_overflow(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body = request()
        body.update(plot_lower=0.0, plot_upper=1e308, assumed_distribution=None)
        body["controls"].update(lower=1e307, target=5e307, upper=9e307)
        response = client.post(URL, json=body)
        assert response.status_code == 200, response.text
        values = [p["response_value"] for p in response.json()["points"]]
        assert all(math.isfinite(x) for x in values)
        assert values == sorted(set(values)) and values[0] == 0 and values[-1] == 1e308


def request():
    return {
        "controls": {
            "lower": -1.0,
            "target": 0.0,
            "upper": 1.0,
            "lower_desirability": math.exp(-1),
            "upper_desirability": math.exp(-1),
        },
        "plot_lower": -2.0,
        "plot_upper": 2.0,
        "assumed_distribution": {"mean": 0.0, "standard_deviation": 1.0, "incumbent": 0.5},
    }


def test_real_api_is_bounded_read_only_and_does_not_fit(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("curve preview must not fit")

    monkeypatch.setattr("sklearn.gaussian_process.GaussianProcessRegressor.fit", forbidden)

    def hashes():
        return {
            str(p.relative_to(tmp_path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in tmp_path.rglob("*")
            if p.is_file() and p.name != ".workspace.lock"
        }

    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        before = hashes()
        response = client.post(URL, json=request())
        assert response.status_code == 200, response.text
        data = response.json()
        assert (
            data["preview_only"]
            and not data["persisted"]
            and not data["applied_to_recommendations"]
        )
        assert data["request_snapshot"]["controls"]["peak"] == 1
        assert 161 <= len(data["points"]) <= 164
        assert data["metrics"][0]["mean"] == pytest.approx(1 / math.sqrt(3))
        assert data["metrics"][0]["variance"] == pytest.approx(1 / math.sqrt(5) - 1 / 3)
        assert data["metrics"][0]["beta_ei"] > 0
        assert hashes() == before
        assert client.post(URL, json=request()).json() == data
        body = request()
        body.pop("assumed_distribution")
        assert client.post(URL, json=body).json()["metrics"] == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("lower", 0),
        ("upper", "2"),
        ("lower_desirability", 0),
        ("upper_desirability", 1),
        ("peak", 0.9),
        ("target", True),
    ],
)
def test_invalid_controls_are_not_coerced(tmp_path, field, value):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body = request()
        body["controls"][field] = value
        assert client.post(URL, json=body).status_code == 422


def test_precision_failure_preserves_curve_and_reports_unavailable(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body = request()
        body["assumed_distribution"].update(mean=0.5, standard_deviation=1e-200)
        data = client.post(URL, json=body).json()
        assert data["points"]
        assert data["metrics"][0]["variance"] is None
        assert (
            data["metrics"][0]["unavailable_code"] == "bayesian_target_curve_precision_unsupported"
        )


def test_peak_support_and_existing_curve_contract_are_separate(tmp_path):
    from app.api.v1.schemas.bayesian_desirability import BayesianDesirabilityObjective

    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body = request()
        body["assumed_distribution"].update(incumbent=1.0, xi=0.5)
        data = client.post(URL, json=body).json()
        assert all(row["beta_ei"] == 0 for row in data["metrics"])
        body["controls"]["unexpected"] = "private"
        assert client.post(URL, json=body).status_code == 422
    assert (
        BayesianDesirabilityObjective.model_json_schema()["properties"]["curve_policy"]["const"]
        == "derringer_suich_linear_v1"
    )
