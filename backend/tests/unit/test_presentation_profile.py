from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_presentation_catalog_and_routes_are_scoped(tmp_path) -> None:
    settings = Settings(
        product_profile="presentation",
        workspace_root=tmp_path / "presentation-workspace",
        cors_allowed_origins=["http://127.0.0.1:8701"],
    )

    with TestClient(create_app(settings)) as client:
        catalog_response = client.get("/api/v1/analysis-methods")
        openapi_response = client.get("/api/openapi.json")

    assert catalog_response.status_code == 200
    catalog = catalog_response.json()
    assert [module["module_id"] for module in catalog["modules"]] == [
        "exploration",
        "hypothesis",
    ]
    assert {method["module_id"] for method in catalog["methods"]} == {
        "exploration",
        "hypothesis",
    }
    paths = openapi_response.json()["paths"]
    assert "/api/v1/assets" not in paths
    assert "/api/v1/bayesian-studies" not in paths
    assert "/api/v1/doe-designs/factorial" not in paths
    assert "/api/v1/regression-models" not in paths
    assert "/api/v1/quality/attribute-control-limit-sets" not in paths


def test_presentation_rejects_hidden_analysis_execution(tmp_path) -> None:
    settings = Settings(
        product_profile="presentation",
        workspace_root=tmp_path / "presentation-workspace",
    )

    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "quality.run_chart",
                "method_version": "0.2.0",
                "roles": {},
                "options": {},
            },
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "presentation_profile_method_unavailable"


def test_presentation_regression_catalog_and_routes_are_scoped(tmp_path) -> None:
    settings = Settings(
        product_profile="presentation-regression",
        workspace_root=tmp_path / "presentation-regression-workspace",
        cors_allowed_origins=["http://127.0.0.1:8702"],
    )

    with TestClient(create_app(settings)) as client:
        catalog_response = client.get("/api/v1/analysis-methods")
        openapi_response = client.get("/api/openapi.json")
        hidden_method_response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "quality.run_chart",
                "method_version": "0.2.0",
                "roles": {},
                "options": {},
            },
        )

    assert catalog_response.status_code == 200
    catalog = catalog_response.json()
    assert [module["module_id"] for module in catalog["modules"]] == [
        "exploration",
        "hypothesis",
        "regression",
    ]
    assert {method["module_id"] for method in catalog["methods"]} == {
        "exploration",
        "hypothesis",
        "regression",
    }
    paths = openapi_response.json()["paths"]
    assert "/api/v1/regression-models" in paths
    assert "/api/v1/assets" not in paths
    assert "/api/v1/bayesian-studies" not in paths
    assert "/api/v1/doe-designs/factorial" not in paths
    assert "/api/v1/quality/attribute-control-limit-sets" not in paths
    assert hidden_method_response.status_code == 403
    assert (
        hidden_method_response.json()["error"]["code"] == "presentation_profile_method_unavailable"
    )


def test_four_domain_profile_marks_later_domains_planned_and_blocks_execution(tmp_path) -> None:
    settings = Settings(
        product_profile="presentation-four-domains",
        workspace_root=tmp_path / "presentation-four-domain-workspace",
        cors_allowed_origins=["http://127.0.0.1:8602"],
    )

    with TestClient(create_app(settings)) as client:
        catalog_response = client.get("/api/v1/analysis-methods")
        openapi_response = client.get("/api/openapi.json")
        blocked_equal_variances = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "eda.equal_variances",
                "method_version": "0.2.0",
                "roles": {},
                "options": {},
            },
        )
        blocked_doe = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "doe.factorial_design",
                "method_version": "0.6.0",
                "roles": {},
                "options": {},
            },
        )

    assert catalog_response.status_code == 200
    catalog = catalog_response.json()
    assert len(catalog["modules"]) == 6
    methods = {method["method_id"]: method for method in catalog["methods"]}
    assert methods["eda.descriptive"]["availability"] == "available"
    assert methods["hypothesis.mann_whitney"]["availability"] == "available"
    assert methods["categorical.chi_square_association"]["availability"] == "available"
    assert methods["regression.partial_least_squares"]["availability"] == "available"
    assert methods["eda.equal_variances"]["availability"] == "planned"
    assert methods["doe.factorial_design"]["availability"] == "planned"
    assert methods["quality.run_chart"]["availability"] == "planned"
    for response in (blocked_equal_variances, blocked_doe):
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "presentation_profile_method_unavailable"
    paths = openapi_response.json()["paths"]
    assert "/api/v1/regression-models" in paths
    assert "/api/v1/doe-designs/factorial" not in paths
    assert "/api/v1/quality/attribute-control-limit-sets" not in paths


def test_full_profile_keeps_complete_catalog_and_routes(tmp_path) -> None:
    settings = Settings(product_profile="full", workspace_root=tmp_path / "full-workspace")

    with TestClient(create_app(settings)) as client:
        catalog = client.get("/api/v1/analysis-methods").json()
        paths = client.get("/api/openapi.json").json()["paths"]

    assert len(catalog["modules"]) == 6
    assert "/api/v1/assets" in paths
    assert "/api/v1/bayesian-studies" in paths
    assert "/api/v1/doe-designs/factorial" in paths
    assert "/api/v1/regression-models" in paths
