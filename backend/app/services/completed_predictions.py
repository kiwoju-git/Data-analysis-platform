"""Persist only server-completed predictions, never client-computed snapshots."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ValidationError

from app.api.v1.schemas.reports import (
    CompletedPredictionRef,
    RegressionPredictionReportSource,
    SavedPredictionDescriptor,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_report_source import load_analysis_report_source
from app.services.analysis_run_execution import canonical_json_bytes
from app.storage.metadata import (
    AnalysisArtifactRecord,
    get_analysis_artifact_record,
    get_analysis_run_record,
)
from app.storage.source_bound_artifacts import (
    SourceBoundArtifactError,
    insert_source_bound_artifact,
    read_source_bound_artifact,
)


def completed_prediction_path(analysis_id: str, artifact_id: str) -> str:
    return (
        Path("workspaces")
        / "analyses"
        / analysis_id
        / "exports"
        / f"{artifact_id}.completed-prediction.json"
    ).as_posix()


def save_completed_prediction(
    settings: Settings,
    *,
    family: Literal["pls", "gaussian_process"],
    source_analysis_id: UUID,
    source_result_sha256: str,
    model_id: UUID,
    model_manifest_sha256: str,
    manifest: dict[str, Any],
    request: BaseModel,
    response: BaseModel,
) -> SavedPredictionDescriptor:
    created_at = datetime.now(timezone.utc).isoformat()
    artifact_id = uuid4()
    request_payload = request.model_dump(mode="json")
    response_payload = response.model_dump(mode="json", exclude={"saved_prediction"})
    payload = {
        "schema_version": 1,
        "family": family,
        "source_analysis_id": str(source_analysis_id),
        "source_result_sha256": source_result_sha256,
        "model_id": str(model_id),
        "model_manifest_sha256": model_manifest_sha256,
        "created_at": created_at,
        "predictors": manifest["predictors"],
        "response": manifest["response"],
        "method_version": manifest.get("method_version"),
        "package_versions": manifest.get("package_versions", {}),
        "request": request_payload,
        "request_sha256": hashlib.sha256(canonical_json_bytes(request_payload)).hexdigest(),
        "result": response_payload,
        "result_sha256": hashlib.sha256(canonical_json_bytes(response_payload)).hexdigest(),
    }
    content = canonical_json_bytes(payload)
    sha256 = hashlib.sha256(content).hexdigest()
    record = AnalysisArtifactRecord(
        artifact_id=str(artifact_id),
        analysis_id=str(source_analysis_id),
        kind="gp_completed_prediction"
        if family == "gaussian_process"
        else "pls_completed_prediction",
        path=completed_prediction_path(str(source_analysis_id), str(artifact_id)),
        sha256=sha256,
        media_type="application/json",
        created_at=created_at,
    )
    try:
        insert_source_bound_artifact(
            settings.workspace_root,
            record,
            content,
            expected_source_sha256=source_result_sha256,
            model_id=str(model_id),
            model_manifest_sha256=model_manifest_sha256,
        )
    except SourceBoundArtifactError as exc:
        raise _error(exc.code) from exc
    return SavedPredictionDescriptor(
        source=RegressionPredictionReportSource(
            prediction=CompletedPredictionRef(
                family=family,
                source_analysis_id=source_analysis_id,
                source_result_sha256=source_result_sha256,
                model_id=model_id,
                model_manifest_sha256=model_manifest_sha256,
                prediction_artifact_id=artifact_id,
                expected_source_sha256=sha256,
            )
        ),
        created_at=created_at,
    )


def load_completed_prediction(
    settings: Settings, source: CompletedPredictionRef
) -> tuple[dict[str, Any], AnalysisArtifactRecord]:
    record = get_analysis_artifact_record(
        settings.workspace_root, str(source.source_analysis_id), str(source.prediction_artifact_id)
    )
    expected_kind = (
        "gp_completed_prediction"
        if source.family == "gaussian_process"
        else "pls_completed_prediction"
    )
    if record is None:
        raise _error("completed_prediction_not_found", 404)
    if (
        record.sha256 != source.expected_source_sha256
        or record.kind != expected_kind
        or record.media_type != "application/json"
        or record.path != completed_prediction_path(record.analysis_id, record.artifact_id)
    ):
        raise _error("completed_prediction_source_changed")
    owner = get_analysis_run_record(settings.workspace_root, record.analysis_id)
    expected_method = (
        "regression.gaussian_process"
        if source.family == "gaussian_process"
        else "regression.partial_least_squares"
    )
    if (
        owner is None
        or owner.result_sha256 != source.source_result_sha256
        or owner.method_id != expected_method
    ):
        raise _error("completed_prediction_source_changed")
    stored_source = load_analysis_report_source(settings, source.source_analysis_id)
    if stored_source.record.result_sha256 != source.source_result_sha256:
        raise _error("completed_prediction_source_changed")
    try:
        content = read_source_bound_artifact(settings.workspace_root, record)
        payload = json.loads(content)
        _validate_completed_payload(payload, source, record)
    except (ValueError, TypeError, KeyError, SourceBoundArtifactError) as exc:
        raise _error("completed_prediction_corrupt") from exc
    return payload, record


def _finite_tree(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("nonfinite prediction")
    if isinstance(value, dict):
        for child in value.values():
            _finite_tree(child)
    elif isinstance(value, list):
        for child in value:
            _finite_tree(child)


def _validate_completed_payload(
    payload: Any, source: CompletedPredictionRef, record: AnalysisArtifactRecord
) -> None:
    from app.api.v1.schemas.analyses import (
        GaussianProcessPointPredictionRequest,
        GaussianProcessPointPredictionResponse,
        PlsPointPredictionRequest,
        PlsPointPredictionResponse,
    )

    if (
        not isinstance(payload, dict)
        or type(payload.get("schema_version")) is not int
        or payload.get("schema_version") != 1
    ):
        raise ValueError("prediction schema")
    for key, expected in {
        "family": source.family,
        "source_analysis_id": str(source.source_analysis_id),
        "source_result_sha256": source.source_result_sha256,
        "model_id": str(source.model_id),
        "model_manifest_sha256": source.model_manifest_sha256,
        "created_at": record.created_at,
    }.items():
        if payload.get(key) != expected:
            raise ValueError("prediction identity")
    _finite_tree(payload)
    for field in ("request", "result"):
        if (
            hashlib.sha256(canonical_json_bytes(payload[field])).hexdigest()
            != payload[field + "_sha256"]
        ):
            raise ValueError("prediction payload hash")
    request: GaussianProcessPointPredictionRequest | PlsPointPredictionRequest
    result: GaussianProcessPointPredictionResponse | PlsPointPredictionResponse
    try:
        if source.family == "gaussian_process":
            request = GaussianProcessPointPredictionRequest.model_validate(payload["request"])
            result = GaussianProcessPointPredictionResponse.model_validate(payload["result"])
        else:
            request = PlsPointPredictionRequest.model_validate(payload["request"])
            result = PlsPointPredictionResponse.model_validate(payload["result"])
    except ValidationError as exc:
        raise ValueError("prediction contract") from exc
    request_ids = [row.client_row_id for row in request.rows]
    result_ids = [row.client_row_id for row in result.rows]
    predictors = payload["predictors"]
    predictor_ids = [item["column_id"] for item in predictors]
    if (
        not predictor_ids
        or len(predictor_ids) != len(set(predictor_ids))
        or len(request_ids) != len(set(request_ids))
        or len(result_ids) != len(set(result_ids))
        or set(request_ids) != set(result_ids)
        or result.row_count != len(result_ids)
        or not request.save_result
        or result.saved_prediction is not None
        or request.expected_model_manifest_sha256 != source.model_manifest_sha256
        or result.model_manifest_sha256 != source.model_manifest_sha256
        or result.model_id != source.model_id
        or result.response_column_id != payload["response"]["column_id"]
        or any(set(row.values) != set(predictor_ids) for row in request.rows)
    ):
        raise ValueError("prediction rows or model mismatch")
    if isinstance(result, GaussianProcessPointPredictionResponse):
        for row in result.rows:
            if (
                row.predictive_standard_deviation < row.latent_standard_deviation
                or not row.latent_interval_95.lower
                <= row.predicted_mean
                <= row.latent_interval_95.upper
                or not row.predictive_interval_95.lower
                <= row.predicted_mean
                <= row.predictive_interval_95.upper
            ):
                raise ValueError("prediction interval ordering")


def _error(code: str, status_code: int = 409) -> ApiError:
    return ApiError(
        code=code,
        message="The stored prediction source could not be verified.",
        status_code=status_code,
    )
