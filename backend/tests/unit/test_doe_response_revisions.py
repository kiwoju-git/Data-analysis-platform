import sqlite3

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import metadata_db_path


def _create_factorial_design(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/doe-designs/factorial",
        json={
            "name": "revision design",
            "factors": [
                {"name": "Temperature", "low": 60, "high": 80, "unit": "C"},
                {"name": "Pressure", "low": 5, "high": 15, "unit": "bar"},
            ],
            "replicates": 2,
            "center_points": 1,
            "randomize": False,
            "randomization_seed": 20260715,
            "block_count": 1,
        },
    )
    assert response.status_code == 201
    return response.json()


def _values(design: dict[str, object], delta: float = 0.0) -> list[dict[str, float | int]]:
    runs = design["runs"]
    assert isinstance(runs, list)
    return [
        {"run_order": run["run_order"], "value": 50.0 + run["run_order"] + delta} for run in runs
    ]


def test_response_revision_correction_keeps_old_analysis_pinned_and_pages_history(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        design = _create_factorial_design(client)
        design_id = design["design_id"]
        first_save = client.put(
            f"/api/v1/doe-designs/{design_id}/responses",
            json={"response_name": "Yield", "unit": "kg", "values": _values(design)},
        )
        assert first_save.status_code == 200
        first = first_save.json()["responses"][0]
        first_analysis = client.post(
            f"/api/v1/doe-designs/{design_id}/analyses",
            json={
                "response_name": "Yield",
                "response_revision_id": first["response_revision_id"],
                "max_interaction_order": 2,
                "confidence_level": 0.95,
                "point_limit": 256,
            },
        )
        assert first_analysis.status_code == 201
        first_analysis_payload = first_analysis.json()

        correction = client.post(
            f"/api/v1/doe-designs/{design_id}/response-revisions",
            json={
                "response_name": "Yield",
                "unit": "kg",
                "values": _values(design, 1.0),
                "supersedes_response_revision_id": first["response_revision_id"],
            },
        )
        history = client.get(
            f"/api/v1/doe-designs/{design_id}/response-revisions",
            params={"response_name": "Yield", "offset": 0, "limit": 1},
        )
        old_restore = client.get(
            f"/api/v1/doe-designs/{design_id}/analyses/" f"{first_analysis_payload['analysis_id']}"
        )
        consumed_abandon = client.post(
            f"/api/v1/doe-designs/{design_id}/response-revisions/"
            f"{first['response_revision_id']}/abandon"
        )

    assert correction.status_code == 201
    corrected = correction.json()
    assert corrected["revision_number"] == 2
    assert corrected["is_current"] is True
    assert corrected["supersedes_response_revision_id"] == first["response_revision_id"]
    assert corrected["response_revision_sha256"] != first["response_revision_sha256"]
    assert history.status_code == 200
    assert history.json()["total"] == 2
    assert [item["revision_number"] for item in history.json()["items"]] == [2]
    assert old_restore.status_code == 200
    assert old_restore.json()["response_revision_id"] == first["response_revision_id"]
    assert old_restore.json()["response_revision_number"] == 1
    assert consumed_abandon.status_code == 409
    assert consumed_abandon.json()["error"]["code"] == "doe_response_revision_state_invalid"


def test_response_revision_streams_are_independent_and_unused_history_can_be_abandoned(
    tmp_path,
) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        design = _create_factorial_design(client)
        design_id = design["design_id"]
        yield_save = client.put(
            f"/api/v1/doe-designs/{design_id}/responses",
            json={"response_name": "Yield", "unit": "kg", "values": _values(design)},
        ).json()["responses"][0]
        purity_save = client.put(
            f"/api/v1/doe-designs/{design_id}/responses",
            json={"response_name": "Purity", "unit": "%", "values": _values(design, 5)},
        ).json()["responses"]
        purity = next(item for item in purity_save if item["response_name"] == "Purity")
        second_yield = client.post(
            f"/api/v1/doe-designs/{design_id}/response-revisions",
            json={
                "response_name": "Yield",
                "unit": "kg",
                "values": _values(design, 2),
                "supersedes_response_revision_id": yield_save["response_revision_id"],
            },
        )
        abandoned = client.post(
            f"/api/v1/doe-designs/{design_id}/response-revisions/"
            f"{yield_save['response_revision_id']}/abandon"
        )
        purity_history = client.get(
            f"/api/v1/doe-designs/{design_id}/response-revisions",
            params={"response_name": "Purity"},
        )

    assert second_yield.status_code == 201
    assert abandoned.status_code == 200
    assert abandoned.json()["state"] == "abandoned"
    assert abandoned.json()["is_current"] is False
    assert purity_history.status_code == 200
    assert purity_history.json()["total"] == 1
    assert (
        purity_history.json()["items"][0]["response_revision_id"] == purity["response_revision_id"]
    )


def test_response_revision_value_tamper_is_rejected_without_internal_path(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        design = _create_factorial_design(client)
        design_id = design["design_id"]
        saved = client.put(
            f"/api/v1/doe-designs/{design_id}/responses",
            json={"response_name": "Yield", "unit": "kg", "values": _values(design)},
        ).json()["responses"][0]
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as connection:
            connection.execute(
                """
                UPDATE experiment_response_revision_values
                SET response_value = response_value + 100
                WHERE response_revision_id = ? AND run_order = 1
                """,
                (saved["response_revision_id"],),
            )
        response = client.get(
            f"/api/v1/doe-designs/{design_id}/response-revisions/"
            f"{saved['response_revision_id']}"
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "doe_response_revision_checksum_mismatch"
    assert str(tmp_path) not in response.text
    assert "150" not in response.text


def test_analysis_response_revision_relation_tamper_is_rejected(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        design = _create_factorial_design(client)
        design_id = design["design_id"]
        first = client.put(
            f"/api/v1/doe-designs/{design_id}/responses",
            json={"response_name": "Yield", "unit": "kg", "values": _values(design)},
        ).json()["responses"][0]
        analysis = client.post(
            f"/api/v1/doe-designs/{design_id}/analyses",
            json={
                "response_name": "Yield",
                "response_revision_id": first["response_revision_id"],
                "max_interaction_order": 2,
            },
        ).json()
        second = client.post(
            f"/api/v1/doe-designs/{design_id}/response-revisions",
            json={
                "response_name": "Yield",
                "unit": "kg",
                "values": _values(design, 3),
                "supersedes_response_revision_id": first["response_revision_id"],
            },
        ).json()
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as connection:
            connection.execute(
                """
                UPDATE experiment_design_analysis_response_revisions
                SET response_revision_id = ?, response_revision_sha256 = ?
                WHERE analysis_id = ?
                """,
                (
                    second["response_revision_id"],
                    second["response_revision_sha256"],
                    analysis["analysis_id"],
                ),
            )
        restored = client.get(f"/api/v1/doe-designs/{design_id}/analyses/{analysis['analysis_id']}")

    assert restored.status_code == 409
    assert restored.json()["error"]["code"] == "doe_factorial_analysis_dependency_mismatch"
    assert str(tmp_path) not in restored.text
