"""Immutable, source-owned BO model and candidate revisions in workspace metadata."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from app.storage.bayesian_studies import BayesianStorageConflict
from app.storage.metadata import metadata_db_path

MAX_OWNER_MODELS = 32
MAX_OWNER_CANDIDATE_SETS = 32
MAX_DOCUMENT_BYTES = 16 * 1024 * 1024
MAX_OWNER_SELECTIONS = 32
MAX_OWNER_BYTES = 128 * 1024 * 1024
MAX_WORKSPACE_BYTES = 256 * 1024 * 1024
MAX_DATABASE_BYTES_FOR_PLANNING_WRITE = 1536 * 1024 * 1024


def planning_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def planning_sha(value: Any) -> str:
    return hashlib.sha256(planning_json(value).encode("utf-8")).hexdigest()


@contextmanager
def _write(root: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(metadata_db_path(root), isolation_level=None)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def require_current_source(
    connection: sqlite3.Connection,
    *,
    study_version_id: str,
    history_revision_id: str,
    history_sha256: str,
    definition_sha256: str,
    source_trial_count: int | None = None,
) -> None:
    row = connection.execute(
        "SELECT s.status,v.definition_sha256,h.history_revision_id,r.observation_history_sha256 "
        "FROM bayesian_study_versions v JOIN bayesian_studies s ON s.study_id=v.study_id "
        "JOIN bayesian_observation_history_heads h ON h.study_version_id=v.study_version_id "
        "JOIN bayesian_observation_history_revisions r "
        "ON r.history_revision_id=h.history_revision_id "
        "WHERE v.study_version_id=?",
        (study_version_id,),
    ).fetchone()
    if row is None or tuple(row[1:]) != (definition_sha256, history_revision_id, history_sha256):
        raise BayesianStorageConflict("bayesian_optimization_history_stale")
    if row[0] != "active":
        raise BayesianStorageConflict("bayesian_study_closed")
    if source_trial_count is not None:
        count = connection.execute(
            "SELECT COUNT(*) FROM bayesian_trials WHERE study_version_id=?", (study_version_id,)
        ).fetchone()[0]
        if count != source_trial_count:
            raise BayesianStorageConflict("bayesian_candidate_source_changed")


def _documents(record: dict[str, Any], pairs: tuple[tuple[str, str], ...]) -> None:
    for field, digest in pairs:
        value = record[field]
        if (
            not isinstance(value, str)
            or len(value.encode("utf-8")) > MAX_DOCUMENT_BYTES
            or hashlib.sha256(value.encode("utf-8")).hexdigest() != record[digest]
        ):
            raise BayesianStorageConflict("bayesian_planning_artifact_invalid")


def _capacity(connection: sqlite3.Connection, owner: str, added_bytes: int) -> None:
    owner_bytes = 0
    workspace_bytes = 0
    for table, payload in (
        ("bayesian_planning_models", "snapshot_json"),
        ("bayesian_candidate_revisions", "rows_json"),
        ("bayesian_planning_selections", "result_json"),
    ):
        expression = f"length(CAST(config_json AS BLOB))+length(CAST({payload} AS BLOB))"
        row = connection.execute(
            f"SELECT COALESCE(SUM({expression}),0),"
            f"COALESCE(SUM(CASE WHEN study_version_id=? THEN {expression} ELSE 0 END),0) "
            f"FROM {table}",
            (owner,),
        ).fetchone()
        workspace_bytes += int(row[0])
        owner_bytes += int(row[1])
    database_bytes = (
        connection.execute("PRAGMA page_count").fetchone()[0]
        * connection.execute("PRAGMA page_size").fetchone()[0]
    )
    if (
        owner_bytes + added_bytes > MAX_OWNER_BYTES
        or workspace_bytes + added_bytes > MAX_WORKSPACE_BYTES
        or database_bytes + added_bytes > MAX_DATABASE_BYTES_FOR_PLANNING_WRITE
    ):
        raise BayesianStorageConflict("bayesian_planning_capacity_exceeded")


def insert_planning_model(root: Path, record: dict[str, Any]) -> str:
    _documents(record, (("config_json", "config_sha256"), ("snapshot_json", "snapshot_sha256")))
    with _write(root) as connection:
        old = connection.execute(
            "SELECT model_id,config_sha256 FROM bayesian_planning_models "
            "WHERE study_version_id=? AND request_id=?",
            (record["study_version_id"], record["request_id"]),
        ).fetchone()
        if old is not None:
            if old[1] != record["config_sha256"]:
                raise BayesianStorageConflict("bayesian_planning_request_conflict")
            return str(old[0])
        require_current_source(
            connection,
            study_version_id=record["study_version_id"],
            history_revision_id=record["source_history_revision_id"],
            history_sha256=record["history_sha256"],
            definition_sha256=record["definition_sha256"],
        )
        count = connection.execute(
            "SELECT COUNT(*) FROM bayesian_planning_models WHERE study_version_id=?",
            (record["study_version_id"],),
        ).fetchone()[0]
        if count >= MAX_OWNER_MODELS:
            raise BayesianStorageConflict("bayesian_planning_capacity_exceeded")
        _capacity(
            connection,
            record["study_version_id"],
            len(record["config_json"].encode()) + len(record["snapshot_json"].encode()),
        )
        fields = (
            "model_id",
            "study_version_id",
            "source_history_revision_id",
            "definition_sha256",
            "history_sha256",
            "schema_version",
            "request_id",
            "config_json",
            "config_sha256",
            "snapshot_json",
            "snapshot_sha256",
            "created_at",
        )
        connection.execute(
            f"INSERT INTO bayesian_planning_models ({','.join(fields)}) "
            f"VALUES ({','.join('?' for _ in fields)})",
            tuple(record[key] for key in fields),
        )
        return str(record["model_id"])


def get_planning_model(root: Path, model_id: str, study_version_id: str) -> dict[str, Any] | None:
    with sqlite3.connect(metadata_db_path(root)) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT * FROM bayesian_planning_models WHERE model_id=? AND study_version_id=?",
            (model_id, study_version_id),
        ).fetchone()
    if row is None:
        return None
    result = dict(row)
    _documents(result, (("config_json", "config_sha256"), ("snapshot_json", "snapshot_sha256")))
    return result


def list_planning_models(root: Path, study_version_id: str) -> list[dict[str, Any]]:
    with sqlite3.connect(metadata_db_path(root)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT model_id,study_version_id,source_history_revision_id,"
            "history_sha256,definition_sha256,"
            "snapshot_sha256,config_sha256,created_at FROM bayesian_planning_models "
            "WHERE study_version_id=? ORDER BY created_at DESC,model_id LIMIT ?",
            (study_version_id, MAX_OWNER_MODELS),
        ).fetchall()
    return [dict(row) for row in rows]


def insert_candidate_revision(
    root: Path, record: dict[str, Any], *, name: str, expected_head: str | None
) -> str:
    _documents(record, (("config_json", "config_sha256"), ("rows_json", "rows_sha256")))
    with _write(root) as connection:
        owner = connection.execute(
            "SELECT study_version_id FROM bayesian_candidate_sets WHERE candidate_set_id=?",
            (record["candidate_set_id"],),
        ).fetchone()
        if owner is not None and owner[0] != record["study_version_id"]:
            raise BayesianStorageConflict("bayesian_planning_request_conflict")
        old = connection.execute(
            "SELECT revision_id,config_sha256,study_version_id FROM bayesian_candidate_revisions "
            "WHERE study_version_id=? AND request_id=?",
            (record["study_version_id"], record["request_id"]),
        ).fetchone()
        if old is not None:
            if old[1] != record["config_sha256"] or old[2] != record["study_version_id"]:
                raise BayesianStorageConflict("bayesian_planning_request_conflict")
            return str(old[0])
        model = None
        if record["model_id"] is not None:
            model = connection.execute(
                "SELECT * FROM bayesian_planning_models WHERE model_id=? AND study_version_id=?",
                (record["model_id"], record["study_version_id"]),
            ).fetchone()
            if model is None:
                raise BayesianStorageConflict("bayesian_planning_artifact_invalid")
        if record["schema_version"] == 1:
            if model is None:
                raise BayesianStorageConflict("bayesian_planning_artifact_invalid")
            source = dict(model)
        elif record["schema_version"] in {2, 3}:
            source = record
            if model is not None and any(
                model[key] != record[key]
                for key in ("source_history_revision_id", "history_sha256", "definition_sha256")
            ):
                raise BayesianStorageConflict("bayesian_candidate_source_changed")
        else:
            raise BayesianStorageConflict("bayesian_planning_artifact_invalid")
        require_current_source(
            connection,
            study_version_id=record["study_version_id"],
            history_revision_id=source["source_history_revision_id"],
            history_sha256=source["history_sha256"],
            definition_sha256=source["definition_sha256"],
            source_trial_count=record["source_trial_count"],
        )
        head = connection.execute(
            "SELECT h.revision_id,r.revision_number FROM bayesian_candidate_heads h "
            "JOIN bayesian_candidate_revisions r ON r.revision_id=h.revision_id "
            "WHERE h.candidate_set_id=?",
            (record["candidate_set_id"],),
        ).fetchone()
        if (None if head is None else head[0]) != expected_head or record[
            "parent_revision_id"
        ] != expected_head:
            raise BayesianStorageConflict("bayesian_candidate_revision_conflict")
        number = 1 if head is None else int(head[1]) + 1
        if record["revision_number"] != number or number > 64:
            raise BayesianStorageConflict("bayesian_candidate_revision_conflict")
        _capacity(
            connection,
            record["study_version_id"],
            len(record["config_json"].encode()) + len(record["rows_json"].encode()),
        )
        if head is None:
            count = connection.execute(
                "SELECT COUNT(*) FROM bayesian_candidate_sets WHERE study_version_id=?",
                (record["study_version_id"],),
            ).fetchone()[0]
            if count >= MAX_OWNER_CANDIDATE_SETS:
                raise BayesianStorageConflict("bayesian_planning_capacity_exceeded")
            connection.execute(
                "INSERT INTO bayesian_candidate_sets"
                "(candidate_set_id,study_version_id,name,created_at) VALUES (?,?,?,?)",
                (
                    record["candidate_set_id"],
                    record["study_version_id"],
                    name,
                    record["created_at"],
                ),
            )
        fields: tuple[str, ...] = (
            "revision_id",
            "candidate_set_id",
            "study_version_id",
            "model_id",
            "revision_number",
            "schema_version",
            "request_id",
            "parent_revision_id",
            "source_trial_count",
            "excluded_coordinates_sha256",
            "config_json",
            "config_sha256",
            "rows_json",
            "rows_sha256",
            "row_count",
            "created_at",
        )
        if record["schema_version"] in {2, 3}:
            fields += ("source_history_revision_id", "history_sha256", "definition_sha256")
        connection.execute(
            f"INSERT INTO bayesian_candidate_revisions({','.join(fields)}) "
            f"VALUES ({','.join('?' for _ in fields)})",
            tuple(record[key] for key in fields),
        )
        if head is None:
            connection.execute(
                "INSERT INTO bayesian_candidate_heads(candidate_set_id,revision_id) VALUES (?,?)",
                (record["candidate_set_id"], record["revision_id"]),
            )
        else:
            updated = connection.execute(
                "UPDATE bayesian_candidate_heads SET revision_id=? "
                "WHERE candidate_set_id=? AND revision_id=?",
                (record["revision_id"], record["candidate_set_id"], expected_head),
            ).rowcount
            if updated != 1:
                raise BayesianStorageConflict("bayesian_candidate_revision_conflict")
        return str(record["revision_id"])


def get_candidate_revision(
    root: Path, revision_id: str, study_version_id: str
) -> dict[str, Any] | None:
    with sqlite3.connect(metadata_db_path(root)) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT * FROM bayesian_candidate_revisions "
            "WHERE revision_id=? AND study_version_id=?",
            (revision_id, study_version_id),
        ).fetchone()
    if row is None:
        return None
    result = dict(row)
    _documents(result, (("config_json", "config_sha256"), ("rows_json", "rows_sha256")))
    if result["schema_version"] == 1:
        for key in ("source_history_revision_id", "history_sha256", "definition_sha256"):
            if result.pop(key, None) is not None:
                raise BayesianStorageConflict("bayesian_planning_artifact_invalid")
    return result


def list_candidate_sets(root: Path, study_version_id: str) -> list[dict[str, Any]]:
    with sqlite3.connect(metadata_db_path(root)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT s.candidate_set_id,json_extract(r.config_json,'$.request.name') AS name,"
            "r.schema_version,r.study_version_id,r.revision_id,r.revision_number,r.parent_revision_id,r.model_id,"
            "r.rows_sha256,r.config_sha256,r.excluded_coordinates_sha256,r.source_trial_count,"
            "r.row_count,r.created_at,m.snapshot_sha256 AS model_sha256,"
            "COALESCE(r.definition_sha256,m.definition_sha256) AS definition_sha256,"
            "COALESCE(r.source_history_revision_id,m.source_history_revision_id) "
            "AS source_history_revision_id,"
            "COALESCE(r.history_sha256,m.history_sha256) AS history_sha256,"
            "json_extract(r.config_json,'$.request.duplicate_tolerance') AS duplicate_tolerance,"
            "json_extract(r.config_json,'$.request.ordinal_rank_distance') "
            "AS ordinal_rank_distance,"
            "(SELECT COUNT(*) FROM json_each(r.rows_json) "
            "WHERE json_extract(value,'$.eligible')=1) AS eligible_count "
            "FROM bayesian_candidate_sets s "
            "JOIN bayesian_candidate_heads h ON h.candidate_set_id=s.candidate_set_id "
            "JOIN bayesian_candidate_revisions r ON r.revision_id=h.revision_id "
            "LEFT JOIN bayesian_planning_models m ON m.model_id=r.model_id "
            "WHERE s.study_version_id=? ORDER BY r.created_at DESC,s.candidate_set_id LIMIT ?",
            (study_version_id, MAX_OWNER_CANDIDATE_SETS),
        ).fetchall()
    return [dict(row) for row in rows]


def find_planning_request(
    root: Path, study_version_id: str, request_id: str, *, kind: str
) -> dict[str, Any] | None:
    tables = {
        "model": "bayesian_planning_models",
        "selection": "bayesian_planning_selections",
        "candidate": "bayesian_candidate_revisions",
    }
    if kind not in tables:
        raise ValueError("invalid internal planning record kind")
    with sqlite3.connect(metadata_db_path(root)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f"SELECT * FROM {tables[kind]} WHERE study_version_id=? AND request_id=? LIMIT 2",
            (study_version_id, request_id),
        ).fetchall()
    if len(rows) > 1:
        raise BayesianStorageConflict("bayesian_planning_request_conflict")
    return None if not rows else dict(rows[0])


def insert_planning_selection(root: Path, record: dict[str, Any]) -> str:
    _documents(record, (("config_json", "config_sha256"), ("result_json", "result_sha256")))
    with _write(root) as connection:
        old = connection.execute(
            "SELECT selection_id,config_sha256 FROM bayesian_planning_selections "
            "WHERE study_version_id=? AND request_id=?",
            (record["study_version_id"], record["request_id"]),
        ).fetchone()
        if old is not None:
            if old[1] != record["config_sha256"]:
                raise BayesianStorageConflict("bayesian_planning_request_conflict")
            return str(old[0])
        _require_selection_source(connection, record)
        count = connection.execute(
            "SELECT COUNT(*) FROM bayesian_planning_selections WHERE study_version_id=?",
            (record["study_version_id"],),
        ).fetchone()[0]
        if count >= MAX_OWNER_SELECTIONS:
            raise BayesianStorageConflict("bayesian_planning_capacity_exceeded")
        _capacity(
            connection,
            record["study_version_id"],
            len(record["config_json"].encode()) + len(record["result_json"].encode()),
        )
        fields = (
            "selection_id",
            "study_version_id",
            "model_id",
            "candidate_revision_id",
            "request_id",
            "schema_version",
            "config_json",
            "config_sha256",
            "result_json",
            "result_sha256",
            "created_at",
        )
        connection.execute(
            f"INSERT INTO bayesian_planning_selections({','.join(fields)}) "
            f"VALUES ({','.join('?' for _ in fields)})",
            tuple(record[key] for key in fields),
        )
        return str(record["selection_id"])


def _require_selection_source(connection: sqlite3.Connection, record: dict[str, Any]) -> None:
    if record["schema_version"] in {2, 3}:
        _require_augmentation_source(connection, record)
        return
    candidate = connection.execute(
        "SELECT * FROM bayesian_candidate_revisions WHERE revision_id=? AND study_version_id=?",
        (record["candidate_revision_id"], record["study_version_id"]),
    ).fetchone()
    model = connection.execute(
        "SELECT * FROM bayesian_planning_models WHERE model_id=? AND study_version_id=?",
        (record["model_id"], record["study_version_id"]),
    ).fetchone()
    if candidate is None or model is None or candidate["model_id"] != model["model_id"]:
        raise BayesianStorageConflict("bayesian_planning_artifact_invalid")
    _documents(dict(candidate), (("config_json", "config_sha256"), ("rows_json", "rows_sha256")))
    _documents(
        dict(model), (("config_json", "config_sha256"), ("snapshot_json", "snapshot_sha256"))
    )
    config = json.loads(record["config_json"])
    if (
        config["expected_model_sha256"] != model["snapshot_sha256"]
        or config["expected_rows_sha256"] != candidate["rows_sha256"]
        or config["expected_history_revision_id"] != model["source_history_revision_id"]
        or config["expected_history_sha256"] != model["history_sha256"]
        or config["expected_trial_count"] != candidate["source_trial_count"]
    ):
        raise BayesianStorageConflict("bayesian_candidate_source_changed")
    require_current_source(
        connection,
        study_version_id=record["study_version_id"],
        history_revision_id=model["source_history_revision_id"],
        history_sha256=model["history_sha256"],
        definition_sha256=model["definition_sha256"],
        source_trial_count=candidate["source_trial_count"],
    )
    pending = connection.execute(
        "SELECT 1 FROM bayesian_trials WHERE study_version_id=? AND state='pending' LIMIT 1",
        (record["study_version_id"],),
    ).fetchone()
    if pending is not None:
        raise BayesianStorageConflict("bayesian_optimization_pending_recommendation_exists")


def _require_augmentation_source(connection: sqlite3.Connection, record: dict[str, Any]) -> None:
    candidate = connection.execute(
        "SELECT * FROM bayesian_candidate_revisions WHERE revision_id=? AND study_version_id=?",
        (record["candidate_revision_id"], record["study_version_id"]),
    ).fetchone()
    if candidate is None:
        raise BayesianStorageConflict("bayesian_planning_artifact_invalid")
    if record["schema_version"] == 3 and candidate["schema_version"] != 3:
        raise BayesianStorageConflict("bayesian_planning_artifact_invalid")
    _documents(dict(candidate), (("config_json", "config_sha256"), ("rows_json", "rows_sha256")))
    if candidate["schema_version"] in {2, 3}:
        source = dict(candidate)
    else:
        source_row = connection.execute(
            "SELECT * FROM bayesian_planning_models WHERE model_id=? AND study_version_id=?",
            (candidate["model_id"], record["study_version_id"]),
        ).fetchone()
        if source_row is None:
            raise BayesianStorageConflict("bayesian_planning_artifact_invalid")
        source = dict(source_row)
    config = json.loads(record["config_json"])
    if (
        config["expected_study_version_id"] != record["study_version_id"]
        or config["expected_definition_sha256"] != source["definition_sha256"]
        or config["expected_history_revision_id"] != source["source_history_revision_id"]
        or config["expected_history_sha256"] != source["history_sha256"]
        or config["expected_rows_sha256"] != candidate["rows_sha256"]
        or config["expected_trial_count"] != candidate["source_trial_count"]
        or config["model_id"] != record["model_id"]
    ):
        raise BayesianStorageConflict("bayesian_candidate_source_changed")
    if record["model_id"] is not None:
        model = connection.execute(
            "SELECT * FROM bayesian_planning_models WHERE model_id=? AND study_version_id=?",
            (record["model_id"], record["study_version_id"]),
        ).fetchone()
        if (
            model is None
            or record["schema_version"] == 3
            and model["schema_version"] != 2
            or config["expected_model_sha256"] != model["snapshot_sha256"]
            or any(
                model[key] != source[key]
                for key in ("definition_sha256", "source_history_revision_id", "history_sha256")
            )
        ):
            raise BayesianStorageConflict("bayesian_planning_model_mismatch")
        _documents(
            dict(model), (("config_json", "config_sha256"), ("snapshot_json", "snapshot_sha256"))
        )
    elif config["expected_model_sha256"] is not None:
        raise BayesianStorageConflict("bayesian_planning_model_mismatch")
    require_current_source(
        connection,
        study_version_id=record["study_version_id"],
        history_revision_id=source["source_history_revision_id"],
        history_sha256=source["history_sha256"],
        definition_sha256=source["definition_sha256"],
        source_trial_count=candidate["source_trial_count"],
    )
    if (
        connection.execute(
            "SELECT 1 FROM bayesian_trials WHERE study_version_id=? AND state='pending' LIMIT 1",
            (record["study_version_id"],),
        ).fetchone()
        is not None
    ):
        raise BayesianStorageConflict("bayesian_optimization_pending_recommendation_exists")


def get_planning_selection(
    root: Path, selection_id: str, study_version_id: str
) -> dict[str, Any] | None:
    with sqlite3.connect(metadata_db_path(root)) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT s.*,c.batch_id AS confirmed_batch_id FROM bayesian_planning_selections s "
            "LEFT JOIN bayesian_planning_confirmations c ON c.selection_id=s.selection_id "
            "WHERE s.selection_id=? AND s.study_version_id=?",
            (selection_id, study_version_id),
        ).fetchone()
    if row is None:
        return None
    record = dict(row)
    _documents(record, (("config_json", "config_sha256"), ("result_json", "result_sha256")))
    return record


def list_mixed_selection_summaries(root: Path, study_version_id: str) -> list[dict[str, Any]]:
    with sqlite3.connect(metadata_db_path(root)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT s.selection_id,s.study_version_id,s.model_id,s.candidate_revision_id,"
            "s.config_sha256,s.result_sha256,s.created_at,"
            "json_extract(s.config_json,'$.kind') AS kind,"
            "json_extract(s.config_json,'$.policy') AS policy,"
            "json_extract(s.config_json,'$.batch_size') AS selected_count,"
            "r.source_history_revision_id,r.history_sha256,r.definition_sha256,r.source_trial_count,"
            "c.batch_id AS confirmed_batch_id FROM bayesian_planning_selections s "
            "JOIN bayesian_candidate_revisions r ON r.revision_id=s.candidate_revision_id "
            "LEFT JOIN bayesian_planning_confirmations c ON c.selection_id=s.selection_id "
            "WHERE s.study_version_id=? AND s.schema_version=3 "
            "ORDER BY s.created_at DESC,s.selection_id",
            (study_version_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_planning_selection_summaries(root: Path, study_version_id: str) -> list[dict[str, Any]]:
    with sqlite3.connect(metadata_db_path(root)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT s.selection_id,s.study_version_id,s.model_id,s.candidate_revision_id,"
            "s.config_sha256,s.result_sha256,s.created_at,"
            "json_array_length(s.config_json,'$.row_ids') AS selected_count,"
            "m.definition_sha256,m.source_history_revision_id,m.history_sha256,"
            "r.source_trial_count,c.batch_id AS confirmed_batch_id "
            "FROM bayesian_planning_selections s "
            "JOIN bayesian_planning_models m ON m.model_id=s.model_id "
            "JOIN bayesian_candidate_revisions r ON r.revision_id=s.candidate_revision_id "
            "LEFT JOIN bayesian_planning_confirmations c ON c.selection_id=s.selection_id "
            "WHERE s.study_version_id=? AND s.schema_version=1 "
            "ORDER BY s.created_at DESC,s.selection_id LIMIT ?",
            (study_version_id, MAX_OWNER_SELECTIONS),
        ).fetchall()
    return [dict(row) for row in rows]


def planning_owner_manifest(connection: sqlite3.Connection, study_id: str) -> dict[str, Any]:
    """Bounded identity manifest for the existing deletion CAS, without reading GP arrays."""
    owned = "SELECT study_version_id FROM bayesian_study_versions WHERE study_id=?"
    specifications = (
        ("planning_model", "bayesian_planning_models", "model_id,config_sha256,snapshot_sha256"),
        ("candidate_set", "bayesian_candidate_sets", "candidate_set_id,name"),
        (
            "candidate_revision",
            "bayesian_candidate_revisions",
            "revision_id,config_sha256,rows_sha256",
        ),
        (
            "planning_selection",
            "bayesian_planning_selections",
            "selection_id,config_sha256,result_sha256",
        ),
    )
    manifest = {}
    counts = {}
    for label, table, columns in specifications:
        rows = connection.execute(
            f"SELECT {columns} FROM {table} WHERE study_version_id IN ({owned}) ORDER BY 1",
            (study_id,),
        ).fetchall()
        manifest[label] = [tuple(row) for row in rows]
        counts[label + "_count"] = len(rows)
    manifest["heads"] = [
        tuple(row)
        for row in connection.execute(
            "SELECT h.candidate_set_id,h.revision_id FROM bayesian_candidate_heads h "
            "JOIN bayesian_candidate_sets s ON s.candidate_set_id=h.candidate_set_id "
            f"WHERE s.study_version_id IN ({owned}) ORDER BY 1",
            (study_id,),
        )
    ]
    manifest["confirmations"] = [
        tuple(row)
        for row in connection.execute(
            "SELECT c.selection_id,c.batch_id FROM bayesian_planning_confirmations c "
            "JOIN bayesian_planning_selections s ON s.selection_id=c.selection_id "
            f"WHERE s.study_version_id IN ({owned}) ORDER BY 1",
            (study_id,),
        )
    ]
    counts["planning_confirmation_count"] = len(manifest["confirmations"])
    return {**counts, "planning_manifest_sha256": planning_sha(manifest)}


def validate_planning_confirmation(
    connection: sqlite3.Connection,
    selection_id: str,
    *,
    study_version_id: str,
    expected_config_sha256: str,
    expected_result_sha256: str,
) -> dict[str, Any]:
    """Called inside the existing atomic batch transaction, before inserting trials."""
    previous_factory = connection.row_factory
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            "SELECT * FROM bayesian_planning_selections "
            "WHERE selection_id=? AND study_version_id=?",
            (selection_id, study_version_id),
        ).fetchone()
        if (
            row is None
            or row["config_sha256"] != expected_config_sha256
            or row["result_sha256"] != expected_result_sha256
        ):
            raise BayesianStorageConflict("bayesian_planning_selection_mismatch")
        record = dict(row)
        _documents(record, (("config_json", "config_sha256"), ("result_json", "result_sha256")))
        _require_selection_source(connection, record)
        return record
    finally:
        connection.row_factory = previous_factory


def delete_planning_owner(connection: sqlite3.Connection, study_version_id: str) -> None:
    """Use only within the existing explicit owner deletion transaction."""
    connection.execute(
        "DELETE FROM bayesian_planning_confirmations WHERE selection_id IN "
        "(SELECT selection_id FROM bayesian_planning_selections WHERE study_version_id=?)",
        (study_version_id,),
    )
    connection.execute(
        "DELETE FROM bayesian_planning_selections WHERE study_version_id=?", (study_version_id,)
    )
    connection.execute(
        "DELETE FROM bayesian_candidate_heads WHERE candidate_set_id IN "
        "(SELECT candidate_set_id FROM bayesian_candidate_sets WHERE study_version_id=?)",
        (study_version_id,),
    )
    rows = connection.execute(
        "SELECT revision_id FROM bayesian_candidate_revisions WHERE study_version_id=? "
        "ORDER BY revision_number DESC",
        (study_version_id,),
    ).fetchall()
    for row in rows:
        connection.execute(
            "DELETE FROM bayesian_candidate_revisions WHERE revision_id=?", (row[0],)
        )
    connection.execute(
        "DELETE FROM bayesian_candidate_sets WHERE study_version_id=?", (study_version_id,)
    )
    connection.execute(
        "DELETE FROM bayesian_planning_models WHERE study_version_id=?", (study_version_id,)
    )
