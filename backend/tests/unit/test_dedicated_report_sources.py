import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_bayesian_batches_api import _batch_request, _completed_study
from test_bayesian_recommendations_api import (
    _complete_initial_trials,
    _create_study,
    _recommendation_request,
)
from test_factorial_prediction import _analyze
from test_lhs_design_api import _request as lhs_request
from test_regression_workflow_extensions_api import _fit_model
from test_response_optimizer_api import _create_source_analysis, _optimizer_request

from app.api.v1.schemas.reports import CompletedPredictionRef, RegressionPredictionReportSource
from app.core.config import Settings
from app.core.errors import ApiError
from app.main import create_app
from app.services.dedicated_report_renderers import render_doe_analysis_body
from app.services.dedicated_report_sources import (
    doe_prediction_source_descriptor,
    list_dedicated_report_sources,
    prepare_dedicated_report_source,
    report_source_is_stale,
)
from app.services.report_contract import assess_report_body
from app.storage.metadata import metadata_db_path


def forbidden(*args, **kwargs):
    raise AssertionError("report reran a calculation or read raw data")


def no_recompute(monkeypatch):
    for module, name in (
        ("app.services.lhs_designs", "calculate_latin_hypercube_quality"),
        ("app.services.lhs_designs", "generate_latin_hypercube_design"),
        ("app.services.bayesian_studies", "_generate_initial_design"),
        ("app.services.bayesian_studies", "_load_validated_study"),
        ("app.services.bayesian_recommendations", "_run_worker"),
        ("app.services.bayesian_recommendation_batches", "_run_worker"),
        ("app.services.doe_factorial_analysis", "calculate_factorial_analysis"),
        ("app.services.general_factorial_designs", "calculate_general_factorial_analysis"),
        ("app.services.doe_response_surface_analysis", "calculate_response_surface_analysis"),
        ("app.services.response_optimizer", "calculate_response_optimizer"),
        ("app.services.dataset_rows", "_iter_canonical_rows_jsonl"),
    ):
        monkeypatch.setattr(module + "." + name, forbidden)


def snapshot(root):
    with sqlite3.connect(metadata_db_path(root)) as connection:
        return "\n".join(connection.iterdump())


@pytest.mark.parametrize("general", [False, True])
@pytest.mark.parametrize("locale", ["en", "ko"])
def test_factorial_sources_preserve_saved_tables_svg_and_hashes(
    tmp_path, monkeypatch, general, locale
):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        design, analysis, _ = _analyze(client, general=general)
        page = list_dedicated_report_sources(settings, "doe_analysis")
        assert len(page.items) == 1
        source = page.items[0].source
        assert str(source.design_id) in page.items[0].open_target
        assert str(source.analysis_id) in page.items[0].open_target
        assert ("design_kind=general" in page.items[0].open_target) is general
        assert not report_source_is_stale(settings, source)
        before = snapshot(tmp_path)
        no_recompute(monkeypatch)
        verified = prepare_dedicated_report_source(settings, source, locale)
        assert verified.payload["result"] == analysis["result"]
        html = verified.body.render()
        assert 'data-report-section="anova"' in html
        assert 'data-report-section="residual_plots"' in html
        assert "<svg" in html and "<table" in html
        assert verified.definition is not None
        assert assess_report_body(verified.definition, verified.body) == "full"
        assert snapshot(tmp_path) == before
        wrong = source.model_copy(update={"expected_source_sha256": "0" * 64})
        with pytest.raises(ApiError) as caught:
            prepare_dedicated_report_source(settings, wrong, locale)
        assert caught.value.code == "report_source_changed"
        wrong_owner = source.model_copy(update={"design_id": uuid4()})
        with pytest.raises(ApiError):
            prepare_dedicated_report_source(settings, wrong_owner, locale)
        incomplete = {**verified.payload, "result": {**verified.payload["result"], "fit": {}}}
        assert (
            render_doe_analysis_body(incomplete, source.family, locale).unsupported_reason
            == "required_result_section_missing"
        )
        legacy = {
            **verified.payload,
            "result": {
                key: value
                for key, value in verified.payload["result"].items()
                if key not in {"final_model", "model_selection"}
            },
        }
        assert (
            assess_report_body(
                verified.definition, render_doe_analysis_body(legacy, source.family, locale)
            )
            == "summary"
        )
        superseding = client.post(
            f"/api/v1/doe-designs/{design['design_id']}/response-revisions",
            json={
                "response_name": "Yield",
                "unit": None,
                "supersedes_response_revision_id": analysis["response_revision_id"],
                "values": [
                    {"run_order": item["run_order"], "value": float(item["run_order"])}
                    for item in design["runs"]
                ],
            },
        )
        assert superseding.status_code == 201, superseding.text
        assert report_source_is_stale(settings, source)
        historical = prepare_dedicated_report_source(settings, source, locale)
        assert historical.stale and historical.payload["result"] == verified.payload["result"]
        assert list_dedicated_report_sources(settings, "doe_analysis").items[0].stale


def test_rsm_and_exact_optimizer_dependencies_no_rerun(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        design, analysis = _create_source_analysis(client)
        saved = client.post(
            f"/api/v1/doe-designs/response-surface/{design['design_id']}/optimizations",
            json=_optimizer_request(analysis["analysis_id"]),
        )
        assert saved.status_code == 201, saved.text
        analyses = list_dedicated_report_sources(settings, "doe_analysis")
        optimizers = list_dedicated_report_sources(settings, "doe_optimizer_result")
        assert len(analyses.items) == len(optimizers.items) == 1
        before = snapshot(tmp_path)
        no_recompute(monkeypatch)
        for item in [*analyses.items, *optimizers.items]:
            verified = prepare_dedicated_report_source(settings, item.source, "en")
            assert "<table" in verified.body.render()
            if item.source.kind == "doe_analysis":
                assert "<svg" in verified.body.render()
            else:
                assert verified.payload["result"] == saved.json()["result"]
        assert snapshot(tmp_path) == before
        source = optimizers.items[0].source
        dependency = source.optimizer.source_dependencies[0]
        wrong_dependency = dependency.model_copy(update={"analysis_sha256": "0" * 64})
        wrong = source.model_copy(
            update={
                "optimizer": source.optimizer.model_copy(
                    update={"source_dependencies": [wrong_dependency]}
                )
            }
        )
        with pytest.raises(ApiError):
            prepare_dedicated_report_source(settings, wrong, "en")


@pytest.mark.parametrize("mixed", [False, True])
def test_lhs_stored_quality_exact_old_abandoned_revision_and_escape(tmp_path, monkeypatch, mixed):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        request = lhs_request()
        request["name"] = '<script>"한글\ue000"</script>'
        if mixed:
            request["factors"][0].update(low=1, high=10, domain_kind="discrete_numeric", step=1)
        created = client.post("/api/v1/doe-designs/latin-hypercube", json=request)
        assert created.status_code == 201, created.text
        design = created.json()
        base = f"/api/v1/doe-designs/latin-hypercube/{design['design_id']}/responses"
        for multiplier in (1.0, 10.0):
            saved = client.put(
                base,
                json={
                    "response_name": '<img src=x onerror="bad">',
                    "unit": "%",
                    "values": [
                        {"run_order": row["run_order"], "value": multiplier * row["run_order"]}
                        for row in design["runs"]
                    ],
                },
            )
            assert saved.status_code == 200, saved.text
        sources = list_dedicated_report_sources(settings, "lhs_design_revision", 100, 0)
        assert len(sources.items) == 3
        old = sources.items[-2].source
        # Select by stored revision identity, not list position or a latest pointer.
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            first = connection.execute(
                "SELECT response_revision_id FROM experiment_response_revisions "
                "ORDER BY revision_number LIMIT 1"
            ).fetchone()[0]
            connection.execute(
                "UPDATE experiment_response_revisions SET state='abandoned' "
                "WHERE response_revision_id=?",
                (first,),
            )
        old = next(
            item.source
            for item in sources.items
            if item.source.response_revisions
            and str(item.source.response_revisions[0].response_revision_id) == first
        )
        before = snapshot(tmp_path)
        no_recompute(monkeypatch)
        verified = prepare_dedicated_report_source(settings, old, "en")
        assert verified.stale and report_source_is_stale(settings, old)
        assert "historical_abandoned_response_revision" in verified.body.render()
        assert "&lt;img" in verified.body.render() and "<img" not in verified.body.render()
        assert verified.payload["responses"][0]["values"][0]["response_value"] == 1
        assert (
            verified.payload["design"]["quality"]["centered_discrepancy"]
            == design["quality"]["centered_discrepancy"]
        )
        assert snapshot(tmp_path) == before
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE experiment_design_versions SET options_json="
                "replace(options_json,'centered_discrepancy','tampered_discrepancy') "
                "WHERE design_version_id=?",
                (design["design_version_id"],),
            )
        with pytest.raises(ApiError):
            prepare_dedicated_report_source(settings, old, "en")
        assert list_dedicated_report_sources(settings, "lhs_design_revision", 1, 0).has_more
        assert (
            list_dedicated_report_sources(settings, "lhs_design_revision", 1, 1)
            .items[0]
            .source_ref_sha256
            != list_dedicated_report_sources(settings, "lhs_design_revision", 1, 0)
            .items[0]
            .source_ref_sha256
        )


def test_empty_and_old_bayesian_history_do_not_regenerate_or_overlay(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _create_study(client)
        empty = list_dedicated_report_sources(settings, "bayesian_history_revision").items[0].source
        _complete_initial_trials(client, study)
        no_recompute(monkeypatch)
        before = snapshot(tmp_path)
        verified = prepare_dedicated_report_source(settings, empty, "en")
        assert verified.stale and report_source_is_stale(settings, empty)
        assert verified.payload["observations"] == []
        assert "no completed observations" in verified.body.render()
        assert verified.definition is not None
        assert assess_report_body(verified.definition, verified.body) == "full"
        assert snapshot(tmp_path) == before
        wrong = empty.model_copy(update={"study_id": uuid4()})
        with pytest.raises(ApiError):
            prepare_dedicated_report_source(settings, wrong, "ko")


def test_report_does_not_apply_frontend_100_row_limit(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        _, analysis, _ = _analyze(client, replicates=16)
        source = list_dedicated_report_sources(settings, "doe_analysis").items[0].source
        no_recompute(monkeypatch)
        verified = prepare_dedicated_report_source(settings, source, "en")
        assert len(analysis["result"]["diagnostics"]["points"]) == 128
        assert "points[128].run_order" in verified.body.render()


@pytest.mark.parametrize("batch", [False, True])
def test_bayesian_exact_attachment_restores_saved_snapshot_not_current_trial(
    tmp_path, monkeypatch, batch
):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = (
            _completed_study(client)
            if batch
            else _complete_initial_trials(client, _create_study(client))
        )
        history_id = study["observation_history"]["history_revision_id"]
        route = "recommendation-batches" if batch else "recommendations"
        request = (
            _batch_request(history_id, batch_size=2, kind="expected_improvement")
            if batch
            else _recommendation_request(history_id)
        )
        saved = client.post(f"/api/v1/bayesian-studies/{study['study_id']}/{route}", json=request)
        assert saved.status_code == 201, saved.text
        source = next(
            item.source
            for item in list_dedicated_report_sources(settings, "bayesian_history_revision").items
            if item.source.attachment.kind != "none"
        )
        assert not report_source_is_stale(settings, source)
        table, key = (
            ("bayesian_recommendation_batches", "batch_id")
            if batch
            else ("bayesian_recommendations", "recommendation_id")
        )
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.row_factory = sqlite3.Row
            child = connection.execute(
                f"SELECT * FROM {table} WHERE {key}=?", (saved.json()[key],)
            ).fetchone()
            connection.execute(
                f"UPDATE {table} SET result_sha256=? WHERE {key}=?",
                ("0" * 64, saved.json()[key]),
            )
        assert report_source_is_stale(settings, source)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(f"DELETE FROM {table} WHERE {key}=?", (saved.json()[key],))
        assert report_source_is_stale(settings, source)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            columns = ",".join(child.keys())
            placeholders = ",".join("?" for _ in child)
            connection.execute(
                f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(child)
            )
        assert not report_source_is_stale(settings, source)
        trial = saved.json()["items"][0]["trial"] if batch else saved.json()["trial"]
        completed = client.put(
            f"/api/v1/bayesian-studies/{study['study_id']}/trials/{trial['trial_id']}/observation",
            json={"objective_value": 999.0, "expected_history_revision_id": history_id},
        )
        assert completed.status_code == 200, completed.text
        no_recompute(monkeypatch)
        before = snapshot(tmp_path)
        verified = prepare_dedicated_report_source(settings, source, "en")
        assert verified.stale and report_source_is_stale(settings, source)
        assert str(source.study_id) in verified.open_target
        assert ("batch_id=" if batch else "recommendation_id=") in verified.open_target
        assert all(item["objective_value"] != 999 for item in verified.payload["observations"])
        attachment = verified.payload["attachment"]
        item = attachment["items"][0] if batch else attachment
        assert item["trial"]["state"] == "pending" and "current_trial" not in item
        assert "<svg" in verified.body.render()
        assert snapshot(tmp_path) == before


def test_saved_doe_prediction_validates_asset_without_prediction_execution(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        _, _, base = _analyze(client)
        rows = {"rows": [{"row_id": "test", "factor_settings": {"A": 0.2, "B": -0.4, "C": 0.7}}]}
        preflight = client.post(base + "/prediction-preflight", json=rows).json()
        saved = client.post(
            base + "/predictions",
            json={**rows, "expected_preflight_sha256": preflight["preflight_sha256"]},
        )
        assert saved.status_code == 201, saved.text
        item = doe_prediction_source_descriptor(settings, saved.json()["prediction_id"])
        no_recompute(monkeypatch)
        monkeypatch.setattr(
            "app.services.factorial_prediction.load_factorial_model_source", forbidden
        )
        verified = prepare_dedicated_report_source(settings, item.source, "ko")
        assert verified.payload["prediction"] == saved.json()
        assert "individual_prediction_interval" in verified.body.render()
        assert not report_source_is_stale(settings, item.source)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE experiment_design_analysis_assets SET sha256=? WHERE asset_id=?",
                ("0" * 64, saved.json()["prediction_id"]),
            )
        assert report_source_is_stale(settings, item.source)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "DELETE FROM experiment_design_analysis_assets WHERE asset_id=?",
                (saved.json()["prediction_id"],),
            )
        assert report_source_is_stale(settings, item.source)


@pytest.mark.parametrize("family", ["pls", "gaussian_process"])
def test_completed_prediction_staleness_checks_exact_child_without_opening_files(tmp_path, family):
    settings = Settings(workspace_root=tmp_path)
    source = RegressionPredictionReportSource(
        prediction=CompletedPredictionRef(
            family=family,
            source_analysis_id=uuid4(),
            source_result_sha256="1" * 64,
            model_id=uuid4(),
            model_manifest_sha256="2" * 64,
            prediction_artifact_id=uuid4(),
            expected_source_sha256="3" * 64,
        )
    )
    database = metadata_db_path(tmp_path)
    database.parent.mkdir(parents=True, exist_ok=True)
    ref = source.prediction
    kind = "gp_completed_prediction" if family == "gaussian_process" else "pls_completed_prediction"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE analysis_artifacts(artifact_id,analysis_id,kind,sha256)")
        connection.execute("CREATE TABLE analysis_runs(analysis_id,stale,result_sha256)")
        connection.execute(
            "INSERT INTO analysis_runs VALUES(?,?,?)",
            (str(ref.source_analysis_id), 0, ref.source_result_sha256),
        )
        connection.execute(
            "INSERT INTO analysis_artifacts VALUES(?,?,?,?)",
            (
                str(ref.prediction_artifact_id),
                str(ref.source_analysis_id),
                kind,
                ref.expected_source_sha256,
            ),
        )
    assert not report_source_is_stale(settings, source)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE analysis_artifacts SET sha256=?", ("4" * 64,))
    assert report_source_is_stale(settings, source)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE analysis_artifacts SET sha256=?", (ref.expected_source_sha256,))
        connection.execute("UPDATE analysis_runs SET result_sha256=?", ("4" * 64,))
    assert report_source_is_stale(settings, source)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE analysis_runs SET result_sha256=?", (ref.source_result_sha256,))
        connection.execute("DELETE FROM analysis_artifacts")
    assert report_source_is_stale(settings, source)


def test_regression_optimizer_uses_exact_saved_result_and_manifest_without_model_loader(
    tmp_path, monkeypatch
):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        _, model_id, manifest_sha = _fit_model(client)
        saved = client.post(
            f"/api/v1/regression-models/{model_id}/response-optimizations",
            json={
                "expected_model_manifest_sha256": manifest_sha,
                "goal": {"kind": "maximize", "lower": 8.0, "target": 30.0, "upper": None},
                "factor_bounds": [],
                "fixed_categorical_levels": [],
                "linear_constraints": [],
                "search": {
                    "random_seed": 11,
                    "random_candidate_count": 64,
                    "multi_start_count": 4,
                    "max_iterations": 100,
                    "max_evaluations": 2000,
                    "profile_point_count": 21,
                },
            },
        )
        assert saved.status_code == 201, saved.text
        source = list_dedicated_report_sources(settings, "doe_optimizer_result").items[0].source
        no_recompute(monkeypatch)
        monkeypatch.setattr(
            "app.services.regression_response_optimizer.get_regression_model_manifest", forbidden
        )
        monkeypatch.setattr(
            "app.services.regression_response_optimizer.calculate_regression_response_optimizer",
            forbidden,
        )
        before = snapshot(tmp_path)
        verified = prepare_dedicated_report_source(settings, source, "en")
        assert verified.payload["result"] == saved.json()["result"]
        assert verified.storage_kind == "analysis"
        assert 'data-report-section="profiles"' in verified.body.render()
        assert snapshot(tmp_path) == before
