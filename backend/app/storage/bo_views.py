"""Owner-locked diagnostic artifacts, independent of the current experiment head."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.api.v1.schemas.bo_views import SavedView, SaveViewRequest
from app.storage.bayesian_studies import BayesianStorageConflict
from app.storage.bo_planning import _capacity, _documents, _write, planning_json, planning_sha
from app.storage.metadata import metadata_db_path

PAIRS = (
    ("save_json", "save_sha256"),
    ("config_json", "config_sha256"),
    ("result_json", "result_sha256"),
)


def model_source(root: Path, study_id: str, model_id: str) -> dict[str, Any]:
    with sqlite3.connect(metadata_db_path(root)) as db:
        db.row_factory = sqlite3.Row
        return _model_source(db, study_id, model_id)


def _model_source(db: sqlite3.Connection, study_id: str, model_id: str) -> dict[str, Any]:
    cursor = db.execute(
        "SELECT m.*,v.study_id,v.schema_version AS study_schema_version,"
        "v.definition_sha256 AS owner_definition,"
        "h.study_version_id AS history_owner,h.observation_history_sha256 AS source_history_hash "
        "FROM bayesian_planning_models m "
        "JOIN bayesian_study_versions v ON v.study_version_id=m.study_version_id "
        "JOIN bayesian_observation_history_revisions h "
        "ON h.history_revision_id=m.source_history_revision_id "
        "WHERE m.model_id=? AND v.study_id=?",
        (model_id, study_id),
    )
    row = cursor.fetchone()
    if row is None:
        raise BayesianStorageConflict("bayesian_view_source_not_found")
    model = dict(zip((column[0] for column in cursor.description), row, strict=True))
    _documents(model, (("config_json", "config_sha256"), ("snapshot_json", "snapshot_sha256")))
    if (
        model["history_owner"] != model["study_version_id"]
        or model["owner_definition"] != model["definition_sha256"]
        or model["source_history_hash"] != model["history_sha256"]
    ):
        raise BayesianStorageConflict("bayesian_view_artifact_invalid")
    return model


def validate_record(db: sqlite3.Connection, row: dict[str, Any], study_id: str) -> SavedView:
    try:
        _documents(row, PAIRS)
        saved = SavedView.model_validate(
            {
                "view_id": row["view_id"],
                "source": json.loads(row["result_json"])["source"],
                "kind": row["kind"],
                "request_sha256": row["config_sha256"],
                "view_sha256": row["result_sha256"],
                "created_at": row["created_at"],
                "evaluation_request": json.loads(row["config_json"]),
                "payload": json.loads(row["result_json"]),
            }
        )
        body = SaveViewRequest.model_validate_json(row["save_json"])
        model = _model_source(db, study_id, row["model_id"])
        source = saved.source
        if (
            saved.payload.kind == "profiler_matrix"
            and saved.payload.warnings != json.loads(model["snapshot_json"])["warnings"]
        ):
            raise ValueError
        if saved.payload.kind == "profiler_matrix":
            mixture = model["study_schema_version"] == 8
            if (saved.payload.schema_version == 2) != mixture:
                raise ValueError
            if mixture:
                from app.statistics.bo_mixture_design import BoMixtureDesign

                snapshot = json.loads(model["snapshot_json"])
                if saved.payload.mixture_domain != snapshot["design_domain"]:
                    raise ValueError
                domain = BoMixtureDesign.from_payload(snapshot["design_domain"])
                domain.canonical(saved.payload.holds)
                if [axis.factor_id for axis in saved.payload.axes] != list(domain.keys):
                    raise ValueError
                for axis in saved.payload.axes:
                    for point in axis.points:
                        domain.canonical(point.actual_coordinates)
        if (
            saved.payload.kind == "conditional_loo"
            and saved.payload.calculation_sha256
            != planning_sha(saved.payload.calculation.model_dump(mode="json"))
        ):
            raise ValueError
        if (
            row["schema_version"] != 1
            or source != saved.payload.source
            or str(source.study_id) != study_id
            or str(source.study_version_id) != row["study_version_id"]
            or str(source.study_version_id) != model["study_version_id"]
            or str(source.model_id) != row["model_id"]
            or source.model_sha256 != model["snapshot_sha256"]
            or source.model_config_sha256 != model["config_sha256"]
            or source.definition_sha256 != model["definition_sha256"]
            or str(source.history_revision_id) != model["source_history_revision_id"]
            or source.history_sha256 != model["history_sha256"]
            or str(body.request_id) != row["request_id"]
            or body.expected_model_sha256 != source.model_sha256
            or body.expected_request_sha256 != saved.request_sha256
            or body.expected_view_sha256 != saved.view_sha256
            or saved.evaluation_request.expected_model_sha256 != source.model_sha256
            or saved.evaluation_request.expected_history_sha256 != source.history_sha256
            or saved.kind != saved.evaluation_request.kind
            or saved.kind != saved.payload.kind
            or planning_json(saved.payload.model_dump(mode="json")) != row["result_json"]
            or planning_json(saved.evaluation_request.model_dump(mode="json")) != row["config_json"]
            or planning_json(body.model_dump(mode="json")) != row["save_json"]
        ):
            raise ValueError
        return saved
    except (ValueError, TypeError, KeyError):
        raise BayesianStorageConflict("bayesian_view_artifact_invalid") from None


def read_view(root: Path, study_id: str, view_id: str) -> SavedView:
    with sqlite3.connect(metadata_db_path(root)) as db:
        db.row_factory = sqlite3.Row
        row = db.execute(
            "SELECT w.* FROM bayesian_saved_views w JOIN bayesian_study_versions v "
            "ON v.study_version_id=w.study_version_id WHERE w.view_id=? AND v.study_id=?",
            (view_id, study_id),
        ).fetchone()
        if row is None:
            raise BayesianStorageConflict("bayesian_view_not_found")
        return validate_record(db, dict(row), study_id)


def list_views(root: Path, study_id: str) -> list[SavedView]:
    with sqlite3.connect(metadata_db_path(root)) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT w.* FROM bayesian_saved_views w JOIN bayesian_study_versions v "
            "ON v.study_version_id=w.study_version_id WHERE v.study_id=? "
            "ORDER BY w.created_at DESC,w.view_id LIMIT 33",
            (study_id,),
        ).fetchall()
        if len(rows) > 32:
            raise BayesianStorageConflict("bayesian_view_artifact_invalid")
        return [validate_record(db, dict(row), study_id) for row in rows]


def replay(root: Path, study_id: str, body: SaveViewRequest) -> SavedView | None:
    with sqlite3.connect(metadata_db_path(root)) as db:
        db.row_factory = sqlite3.Row
        return _replay(db, study_id, body)


def _replay(db: sqlite3.Connection, study_id: str, body: SaveViewRequest) -> SavedView | None:
    row = db.execute(
        "SELECT w.* FROM bayesian_saved_views w JOIN bayesian_study_versions v "
        "ON v.study_version_id=w.study_version_id WHERE v.study_id=? AND w.request_id=?",
        (study_id, str(body.request_id)),
    ).fetchone()
    if row is None:
        return None
    if row["save_json"] != planning_json(body.model_dump(mode="json")):
        raise BayesianStorageConflict("bayesian_view_request_conflict")
    return validate_record(db, dict(row), study_id)


def insert_view(root: Path, study_id: str, row: dict[str, Any]) -> SavedView:
    with _write(root) as db:
        previous = _replay(db, study_id, SaveViewRequest.model_validate_json(row["save_json"]))
        if previous is not None:
            return previous
        saved = validate_record(db, row, study_id)
        count = db.execute(
            "SELECT COUNT(*) FROM bayesian_saved_views WHERE study_version_id=?",
            (row["study_version_id"],),
        ).fetchone()[0]
        if count >= 32:
            raise BayesianStorageConflict("bayesian_view_capacity_exceeded")
        _capacity(
            db, row["study_version_id"], sum(len(row[field].encode("utf-8")) for field, _ in PAIRS)
        )
        fields = tuple(row)
        allowed = {
            "view_id",
            "study_version_id",
            "model_id",
            "schema_version",
            "request_id",
            "kind",
            "save_json",
            "save_sha256",
            "config_json",
            "config_sha256",
            "result_json",
            "result_sha256",
            "created_at",
        }
        if set(fields) != allowed:
            raise BayesianStorageConflict("bayesian_view_artifact_invalid")
        db.execute(
            f"INSERT INTO bayesian_saved_views ({','.join(fields)}) "
            f"VALUES ({','.join('?' for _ in fields)})",
            tuple(row[key] for key in fields),
        )
        return saved
