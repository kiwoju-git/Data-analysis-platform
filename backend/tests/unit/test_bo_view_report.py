"""Saved BO report contracts, owner locking, and stored-only rendering."""

import json
import sqlite3
from copy import deepcopy
from uuid import UUID, uuid4

import pytest

from app.core.errors import ApiError
from app.services import bo_view_report
from app.services.dedicated_report_sources import (
    list_dedicated_report_sources,
    prepare_dedicated_report_source,
)
from app.services.report_contract import assess_report_body
from tests.unit.test_bayesian_multiresponse_lifecycle import url
from tests.unit.test_bo_views import _evaluate, _save_body, source  # noqa: F401


@pytest.mark.parametrize(
    "locale,coverage",
    [("en", "2 of 2: all available levels"), ("ko", "2 of 2: 사용 가능한 전체 수준")],
)
def test_trimmed_stored_axis_coverage_names_available_not_declared_levels(
    locale, coverage, monkeypatch
):
    def forbidden(*args, **kwargs):
        raise AssertionError("Stored coverage rendering must not run a worker")

    monkeypatch.setattr("app.services.bo_planning._run", forbidden)
    points = [
        {
            "actual_coordinates": {"p": value},
            "constraints_satisfied": True,
            "response_predictions": [
                {
                    "mean_raw": 1.0,
                    "latent_standard_deviation_raw": 0.1,
                    "predictive_standard_deviation_raw": 0.2,
                }
            ],
            "desirability_moments": {"mean": 0.5},
        }
        for value in (101.0, 102.0)
    ]
    saved = {
        "source": {},
        "view_id": "stored",
        "view_sha256": "a" * 64,
        "request_sha256": "b" * 64,
        "created_at": "2026-11-14",
        "evaluation_request": {},
        "payload": {
            "kind": "profiler_matrix",
            "policy": "source_locked_mixture_profiler_matrix_v1",
            "mixture_domain": {"declared_process_interval": [0, 10000]},
            "point_count": 2,
            "constraints": [],
            "holds": {"p": 101.0},
            "warnings": [],
            "responses": [{"response_id": "y", "name": "Yield", "unit": None}],
            "axes": [
                {
                    "factor_id": "p",
                    "name": "Process",
                    "unit": None,
                    "kind": "discrete_numeric",
                    "available_level_count": 2,
                    "points": points,
                    "path": {
                        "policy": "held_mixture_process_axis_v1",
                        "feasible_interval": [101, 102],
                        "unavailable_reason": None,
                    },
                }
            ],
        },
    }
    html = bo_view_report.render_view_body({"saved_view": saved}, locale).render()
    assert coverage in html
    assert "all declared levels" not in html


@pytest.fixture
def warning_discrete_setup(monkeypatch):
    from app.services import bo_planning
    from tests.unit import test_bayesian_multiresponse_lifecycle as lifecycle

    original_request = lifecycle.study_request
    original_run = bo_planning._run

    def discrete_request():
        body = original_request()
        body["factors"][0].update(domain_kind="discrete_numeric", step=0.001, display_decimals=3)
        return body

    def warned_run(operation, *args, **kwargs):
        result = original_run(operation, *args, **kwargs)
        if operation == "fit":
            # Persist a deterministic warning-bearing synthetic fitted source.
            result["warnings"] = ["bayesian_category_unobserved_level_prior_dependent"]
        return result

    monkeypatch.setattr(lifecycle, "study_request", discrete_request)
    monkeypatch.setattr(bo_planning, "_run", warned_run)


@pytest.fixture
def warning_discrete_source(warning_discrete_setup, source):  # noqa: F811
    return source


@pytest.mark.parametrize("check", ["warnings", "coverage"])
def test_warning_and_discrete_coverage_survive_save_backup_report(
    warning_discrete_source,
    tmp_path,
    monkeypatch,
    check,
):
    from app.api.v1.schemas.reports import CreateManagedReportRequest, ManagedReportActionRequest
    from app.core.config import Settings
    from app.services.report_exports import create_report, download_report
    from app.storage.metadata import metadata_db_path
    from app.storage.workspace_backup import backup_workspace, restore_workspace

    context = warning_discrete_source
    context.body["points_per_axis"] = 21
    receipt = _evaluate(context)
    with sqlite3.connect(metadata_db_path(context.settings.workspace_root)) as db:
        snapshot = json.loads(
            db.execute("SELECT snapshot_json FROM bayesian_planning_models").fetchone()[0]
        )
    warnings = snapshot["warnings"]
    assert warnings == ["bayesian_category_unobserved_level_prior_dependent"]
    if check == "warnings":
        assert receipt["payload"].get("warnings") == warnings
    saved_response = context.client.post(url(context.study) + "/views", json=_save_body(receipt))
    assert saved_response.status_code == 201, saved_response.text
    saved = saved_response.json()
    if check == "warnings":
        assert saved["payload"]["warnings"] == warnings
    context.close()
    archive, restored = tmp_path / "warnings.tar.gz", tmp_path / "restored warnings"
    backup_workspace(context.settings.workspace_root, archive)
    restore_workspace(archive, restored)

    def forbidden(*args, **kwargs):
        pytest.fail("stored warning/coverage report cannot evaluate or read raw data")

    monkeypatch.setattr("app.services.bo_planning._run", forbidden)
    monkeypatch.setattr("app.services.bo_planning._read_model", forbidden)
    monkeypatch.setattr("app.services.bo_planning.get_bayesian_study", forbidden)
    settings = Settings(workspace_root=restored)
    restored_view = bo_view_report.read_view(
        settings, UUID(context.study["study_id"]), UUID(saved["view_id"])
    )
    assert restored_view.model_dump(mode="json") == saved
    descriptor = bo_view_report.resolve_view_report_source(
        settings, UUID(context.study["study_id"]), UUID(saved["view_id"])
    )
    prepared = prepare_dedicated_report_source(settings, descriptor.source, "en")
    html = prepared.body.render()
    artifact = create_report(
        settings,
        CreateManagedReportRequest(
            source=descriptor.source,
            expected_source_ref_sha256=descriptor.source_ref_sha256,
            locale="en",
        ),
    )
    exported = download_report(
        settings,
        artifact.export_id,
        ManagedReportActionRequest(
            source=descriptor.source,
            expected_sha256=artifact.sha256,
        ),
    ).decode("utf-8")
    if check == "warnings":
        assert warnings[0] in html
        assert "prior-dependent" in html
        assert "independent response" in html.lower()
        assert warnings[0] in exported and "prior-dependent" in exported
    assert "Displayed levels" in html and "Available levels" in html
    assert "21 of 10001" in html and "sampled subset" in html
    assert "21 of 10001" in exported and "sampled subset" in exported


@pytest.mark.parametrize("kind", ["profiler_matrix", "conditional_loo"])
def test_saved_view_report_stored_only(source, monkeypatch, kind):  # noqa: F811
    receipt = _evaluate(source, kind=kind)
    response = source.client.post(url(source.study) + "/views", json=_save_body(receipt))
    assert response.status_code == 201, response.text
    saved = response.json()
    descriptor = bo_view_report.resolve_view_report_source(
        source.settings, UUID(source.study["study_id"]), UUID(saved["view_id"])
    )
    assert descriptor.source.attachment.kind == "view"
    assert "view_id=" + saved["view_id"] in descriptor.open_target
    catalog = list_dedicated_report_sources(source.settings, "bayesian_history_revision")
    assert any(item.source == descriptor.source for item in catalog.items)
    resolved = source.client.get(
        url(source.study) + "/views/" + saved["view_id"] + "/report-source"
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["source_ref_sha256"] == descriptor.source_ref_sha256

    def forbidden(*args, **kwargs):
        raise AssertionError("saved report attempted model or raw-data execution")

    monkeypatch.setattr("app.services.dedicated_report_sources.read_bayesian", forbidden)
    monkeypatch.setattr("app.services.bo_views.evaluate_view", forbidden)
    prepared = prepare_dedicated_report_source(source.settings, descriptor.source, "en")
    assert assess_report_body(prepared.definition, prepared.body) == "full"
    html = prepared.body.render()
    assert "<svg" in html
    assert saved["view_sha256"] in html
    if kind == "profiler_matrix":
        assert "Latent SD" in html and "Predictive SD" in html
        assert "Composite desirability" in html
        assert "Constraints satisfied" in html
        assert "yield" in html.lower() and "cost" in html.lower()
        synthetic = deepcopy(prepared.payload)
        axis = synthetic["saved_view"]["payload"]["axes"][0]
        axis["name"] = "<script>factor</script>"
        axis["kind"] = "nominal"
        for i, point in enumerate(axis["points"]):
            point["actual_coordinates"][axis["factor_id"]] = "category<&" + str(i)
        escaped = bo_view_report.render_view_body(synthetic, "en").render()
        assert "<script>" not in escaped and "&lt;script&gt;" in escaped
        assert "category&lt;&amp;0" in escaped
        assert "<polyline" not in escaped
    else:
        assert "not external validation" in html
        assert "full_fit_parameters_include_held_out_observation" in html
    exported = source.client.post(
        "/api/v1/reports",
        json={
            "source": descriptor.source.model_dump(mode="json"),
            "locale": "en",
            "expected_source_ref_sha256": descriptor.source_ref_sha256,
        },
    )
    assert exported.status_code == 201, exported.text
    artifact = exported.json()
    download = source.client.post(
        "/api/v1/reports/" + artifact["export_id"] + "/download",
        json={
            "source": descriptor.source.model_dump(mode="json"),
            "expected_sha256": artifact["sha256"],
        },
    )
    assert download.status_code == 200, download.text
    assert "default-src 'none'" in download.headers["Content-Security-Policy"]
    assert saved["view_sha256"] in download.text
    for field in ("expected_source_sha256", "definition_sha256"):
        bad = descriptor.source.model_copy(update={field: "f" * 64})
        with pytest.raises(ApiError) as error:
            bo_view_report.read_view_report(source.settings, bad)
        assert error.value.code == "report_source_changed"
    for field, value in (
        ("model_id", uuid4()),
        ("model_sha256", "f" * 64),
        ("model_config_sha256", "f" * 64),
        ("request_sha256", "f" * 64),
        ("view_sha256", "f" * 64),
    ):
        bad = descriptor.source.model_copy(
            update={
                "attachment": descriptor.source.attachment.model_copy(update={field: value}),
            }
        )
        with pytest.raises(ApiError) as error:
            bo_view_report.read_view_report(source.settings, bad)
        assert error.value.code == "report_source_changed"
