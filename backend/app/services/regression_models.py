import hashlib
import json
import os
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from math import isfinite, sqrt
from pathlib import Path
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from fastapi import status
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from scipy import stats  # type: ignore[import-untyped]

from app.analyses.registry import get_method_version
from app.api.v1.schemas.analyses import (
    AnalysisResultEnvelope,
    AnalysisRunState,
    AnalysisWarning,
    RegressionModelCatalogItem,
    RegressionModelCatalogResponse,
    RegressionModelCatalogResponseColumn,
    RegressionModelManifestResponse,
    RegressionModelMetadataResponse,
    RegressionModelMetadataUpdateRequest,
    RegressionPredictionCategoricalCheck,
    RegressionPredictionColumnMapping,
    RegressionPredictionInterval,
    RegressionPredictionNumericCheck,
    RegressionPredictionPreflightIssue,
    RegressionPredictionPreflightResponse,
    RegressionPredictionProvenance,
    RegressionPredictionRequest,
    RegressionPredictionResponse,
    RegressionPredictionRow,
    RegressionPredictionRowsPageResponse,
    RegressionPredictionWarning,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import runtime_build_provenance
from app.services.analysis_run_results import (
    StoredAnalysisRunResult,
    load_analysis_run_result_base,
)
from app.services.dataset_rows import (
    DatasetRowsContext,
    get_dataset_rows_context,
    iter_dataset_rows,
)
from app.storage.atomic import atomic_replace, atomic_write_bytes
from app.storage.metadata import (
    AnalysisArtifactRecord,
    AnalysisRunRecord,
    DatasetColumnRecord,
    WorkspaceAssetStorageConflict,
    count_regression_model_catalog_records,
    get_analysis_run_record,
    get_regression_model_record,
    get_regression_model_user_metadata,
    insert_analysis_run_record_with_artifacts,
    list_analysis_artifact_records,
    list_regression_model_catalog_records,
    upsert_regression_model_user_metadata,
)

APP_VERSION = "0.1.0"
REGRESSION_PREDICTION_METHOD_ID = "regression.predict"
REGRESSION_PREDICTION_METHOD_VERSION = get_method_version(REGRESSION_PREDICTION_METHOD_ID)
REGRESSION_PREDICTION_SCHEMA_VERSION = 2
REGRESSION_PREDICTION_CONFIG_SCHEMA_VERSION = 3
REGRESSION_PREDICTION_ROWS_SCHEMA_VERSION = 2
MAX_REGRESSION_PREDICTION_INLINE_ROWS = 1000
REGRESSION_PREDICTION_ROWS_ARTIFACT_KIND = "regression_prediction_rows"
REGRESSION_PREDICTION_ROWS_MEDIA_TYPE = "application/x-ndjson"


@dataclass
class _PredictionColumnCheck:
    source_column_id: str
    display_name: str
    predictor_kind: Literal["numeric", "categorical"]
    target_column: DatasetColumnRecord | None
    match_type: Literal["column_id", "display_name", "missing", "ambiguous"]
    status: Literal["ok", "warning", "error"]
    training_min: float | None = None
    training_max: float | None = None
    training_levels: set[str] | None = None
    n_valid: int = 0
    n_missing: int = 0
    n_non_numeric: int = 0
    n_below_training_range: int = 0
    n_above_training_range: int = 0
    n_unseen_level: int = 0


@dataclass
class _PredictionPreflightState:
    model_response: RegressionModelManifestResponse
    source_dataset_version_id: UUID
    target_context: DatasetRowsContext
    source_context: DatasetRowsContext | None
    source_analysis_stale: bool | None
    checks: list[_PredictionColumnCheck]
    issues: list[RegressionPredictionPreflightIssue]
    row_count_usable: int


@dataclass(frozen=True)
class _PredictionRowsContext:
    model_id: UUID
    expected_total: int
    path: Path
    sha256: str
    header: "_PredictionRowsHeader"


@dataclass(frozen=True)
class RegressionPredictionConsistencyContext:
    stored_result: StoredAnalysisRunResult
    config: "_PredictionStoredConfig"
    prediction: RegressionPredictionResponse
    model_response: RegressionModelManifestResponse | None
    rows: _PredictionRowsContext


class _PredictionStoredConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_schema_version: Literal[3]
    prediction_id: UUID
    analysis_id: UUID
    method_id: Literal["regression.predict"]
    method_version: str
    model_id: UUID
    source_analysis_id: UUID
    source_dataset_version_id: UUID
    source_schema_hash_at_fit: str
    source_schema_hash_current: str
    target_dataset_version_id: UUID
    target_schema_hash: str
    model_manifest_sha256: str
    prediction_schema_version: int = Field(ge=1)
    rows_artifact_schema_version: int = Field(ge=1)
    confidence_level: float = Field(gt=0.0, lt=1.0)
    missing_policy: Literal["complete_case"]
    include_intervals: bool
    row_limit: int = Field(ge=1)
    row_count_total: int = Field(ge=0)
    row_count_predicted: int = Field(ge=0)
    row_count_excluded: int = Field(ge=0)


class _PredictionRowsHeader(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_type: Literal["regression_prediction_rows_header"]
    artifact_schema_version: Literal[2]
    artifact_kind: Literal["regression_prediction_rows"]
    prediction_id: UUID
    analysis_id: UUID
    method_id: Literal["regression.predict"]
    method_version: str
    model_id: UUID
    source_analysis_id: UUID
    source_dataset_version_id: UUID
    target_dataset_version_id: UUID
    model_manifest_sha256: str
    target_schema_hash: str
    row_count_predicted: int = Field(ge=0)


def list_regression_models(
    settings: Settings,
    *,
    offset: int,
    limit: int,
    source_dataset_version_id: UUID | None = None,
    source_analysis_id: UUID | None = None,
) -> RegressionModelCatalogResponse:
    dataset_filter = None if source_dataset_version_id is None else str(source_dataset_version_id)
    analysis_filter = None if source_analysis_id is None else str(source_analysis_id)
    total = count_regression_model_catalog_records(
        settings.workspace_root,
        source_dataset_version_id=dataset_filter,
        source_analysis_id=analysis_filter,
    )
    records = list_regression_model_catalog_records(
        settings.workspace_root,
        offset=offset,
        limit=limit,
        source_dataset_version_id=dataset_filter,
        source_analysis_id=analysis_filter,
    )
    items: list[RegressionModelCatalogItem] = []
    for catalog_record in records:
        record = catalog_record.model
        availability: Literal["available", "source_stale", "integrity_error"] = "available"
        availability_code: str | None = None
        response_column: RegressionModelCatalogResponseColumn | None = None
        predictor_count: int | None = None
        if (
            record.method_id != "regression.linear_model"
            or catalog_record.source_analysis_status != AnalysisRunState.SUCCEEDED.value
        ):
            availability = "integrity_error"
            availability_code = "regression_model_source_analysis_invalid"
        else:
            try:
                manifest_response = get_regression_model_manifest(
                    settings,
                    UUID(record.model_id),
                )
                response_column, predictor_count = _regression_model_catalog_metadata(
                    manifest_response.manifest,
                )
            except (ApiError, ValueError):
                availability = "integrity_error"
                availability_code = "regression_model_integrity_error"
        if availability == "available" and catalog_record.source_analysis_stale:
            availability = "source_stale"
            availability_code = "regression_prediction_source_model_stale"
        items.append(
            RegressionModelCatalogItem(
                model_id=UUID(record.model_id),
                source_analysis_id=UUID(record.analysis_id),
                source_dataset_version_id=UUID(record.dataset_version_id),
                method_id="regression.linear_model",
                method_version=record.method_version,
                schema_hash=record.schema_hash,
                response=response_column,
                predictor_count=predictor_count,
                created_at=record.created_at,
                availability=availability,
                availability_code=availability_code,
                user_label=catalog_record.user_label,
                note=catalog_record.note,
                pinned=catalog_record.pinned,
                metadata_updated_at=catalog_record.metadata_updated_at,
            )
        )
    return RegressionModelCatalogResponse(
        models=items,
        total=total,
        returned=len(items),
        limit=limit,
        offset=offset,
        has_previous=offset > 0,
        has_next=offset + len(items) < total,
    )


def update_regression_model_metadata(
    settings: Settings,
    *,
    model_id: UUID,
    body: RegressionModelMetadataUpdateRequest,
) -> RegressionModelMetadataResponse:
    if get_regression_model_record(settings.workspace_root, str(model_id)) is None:
        raise ApiError(
            code="regression_model_not_found",
            message="요청한 회귀모델을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    updated_at = datetime.now(timezone.utc).isoformat()
    current = get_regression_model_user_metadata(settings.workspace_root, str(model_id))
    fields = body.model_fields_set
    user_label = (
        body.user_label if "user_label" in fields else current.user_label if current else None
    )
    note = body.note if "note" in fields else current.note if current else None
    pinned = body.pinned if "pinned" in fields else current.pinned if current else False
    try:
        metadata = upsert_regression_model_user_metadata(
            settings.workspace_root,
            model_id=str(model_id),
            user_label=user_label,
            note=note,
            pinned=bool(pinned),
            updated_at=updated_at,
            expected_updated_at=body.expected_metadata_updated_at,
        )
    except WorkspaceAssetStorageConflict as exc:
        raise ApiError(
            code=exc.code,
            message="자산 메타데이터가 다른 화면에서 변경되었습니다. 목록을 새로고침하세요.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc
    return RegressionModelMetadataResponse(
        model_id=model_id,
        user_label=metadata.user_label,
        note=metadata.note,
        pinned=metadata.pinned,
        metadata_updated_at=metadata.updated_at,
    )


def _regression_model_catalog_metadata(
    manifest: dict[str, Any],
) -> tuple[RegressionModelCatalogResponseColumn, int]:
    response = manifest.get("response")
    predictors = manifest.get("predictors")
    if not isinstance(response, dict) or not isinstance(predictors, list) or not predictors:
        raise ValueError("regression_model_catalog_metadata_invalid")
    try:
        response_column = RegressionModelCatalogResponseColumn(
            column_id=UUID(str(response["column_id"])),
            display_name=str(response["display_name"]),
            data_type=str(response["data_type"]),
            measurement_level=str(response["measurement_level"]),
            unit=None if response.get("unit") is None else str(response["unit"]),
        )
    except (KeyError, TypeError, ValidationError, ValueError) as exc:
        raise ValueError("regression_model_catalog_metadata_invalid") from exc
    return response_column, len(predictors)


def get_regression_model_manifest(
    settings: Settings,
    model_id: UUID,
) -> RegressionModelManifestResponse:
    record = get_regression_model_record(settings.workspace_root, str(model_id))
    if record is None:
        raise ApiError(
            code="regression_model_not_found",
            message="요청한 회귀모델을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    manifest_path = _safe_manifest_path(settings.workspace_root, record.manifest_path)
    if not manifest_path.exists():
        raise ApiError(
            code="regression_model_manifest_missing",
            message="저장된 회귀모델 manifest 파일을 찾을 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    manifest_bytes = manifest_path.read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != record.manifest_sha256:
        raise ApiError(
            code="regression_model_manifest_checksum_mismatch",
            message="저장된 회귀모델 manifest가 메타데이터와 일치하지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ApiError(
            code="regression_model_manifest_invalid",
            message="저장된 회귀모델 manifest 형식이 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc

    if not isinstance(manifest, dict):
        raise ApiError(
            code="regression_model_manifest_invalid",
            message="저장된 회귀모델 manifest 형식이 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    return RegressionModelManifestResponse(
        model_id=UUID(record.model_id),
        analysis_id=UUID(record.analysis_id),
        dataset_version_id=UUID(record.dataset_version_id),
        method_id=record.method_id,
        method_version=record.method_version,
        schema_hash=record.schema_hash,
        manifest_sha256=record.manifest_sha256,
        created_at=record.created_at,
        app_version=record.app_version,
        manifest=manifest,
    )


def get_regression_prediction_preflight(
    settings: Settings,
    model_id: UUID,
    dataset_version_id: UUID,
) -> RegressionPredictionPreflightResponse:
    return _prediction_preflight_response(
        _build_prediction_preflight_state(settings, model_id, dataset_version_id),
    )


def create_regression_predictions(
    settings: Settings,
    model_id: UUID,
    body: RegressionPredictionRequest,
) -> RegressionPredictionResponse:
    state = _build_prediction_preflight_state(settings, model_id, body.dataset_version_id)
    preflight = _prediction_preflight_response(state)
    if not preflight.prediction_ready:
        error_codes = sorted(
            {issue.code for issue in preflight.issues if issue.severity == "error"},
        )
        raise ApiError(
            code="regression_prediction_preflight_failed",
            message="예측 사전점검 오류가 있어 실행할 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
            developer_detail=",".join(error_codes) if error_codes else None,
        )

    manifest = state.model_response.manifest
    basis = _validated_prediction_basis(manifest)
    coefficient_estimates = _coefficient_estimates(manifest)
    _validate_prediction_dimensions(
        basis=basis,
        coefficient_count=len(coefficient_estimates),
    )
    prediction_id = uuid4()
    created_at = _utc_now()
    rows_relative_path = _prediction_rows_relative_path(str(prediction_id))
    rows_path = settings.workspace_root / rows_relative_path
    response_holder: list[RegressionPredictionResponse] = []
    rows_sha256_holder: list[str] = []

    def write_rows(temp_path: Path) -> None:
        hasher = hashlib.sha256()
        with temp_path.open("wb") as handle:
            header = _PredictionRowsHeader(
                record_type="regression_prediction_rows_header",
                artifact_schema_version=2,
                artifact_kind="regression_prediction_rows",
                prediction_id=prediction_id,
                analysis_id=prediction_id,
                method_id="regression.predict",
                method_version=REGRESSION_PREDICTION_METHOD_VERSION,
                model_id=preflight.model_id,
                source_analysis_id=preflight.analysis_id,
                source_dataset_version_id=preflight.source_dataset_version_id,
                target_dataset_version_id=preflight.target_dataset_version_id,
                model_manifest_sha256=preflight.model_manifest_sha256,
                target_schema_hash=preflight.target_schema_hash,
                row_count_predicted=preflight.row_count_usable,
            )
            header_line = _canonical_json_bytes(header.model_dump(mode="json")) + b"\n"
            handle.write(header_line)
            hasher.update(header_line)

            def store_row(row: RegressionPredictionRow) -> None:
                line = _canonical_json_bytes(row.model_dump(mode="json")) + b"\n"
                handle.write(line)
                hasher.update(line)

            response_holder.append(
                _calculate_prediction_response(
                    settings=settings,
                    prediction_id=prediction_id,
                    created_at=created_at,
                    request=body,
                    preflight=preflight,
                    state=state,
                    basis=basis,
                    coefficient_estimates=coefficient_estimates,
                    row_sink=store_row,
                ),
            )
            handle.flush()
            os.fsync(handle.fileno())
        rows_sha256_holder.append(hasher.hexdigest())

    atomic_replace(rows_path, write_rows)
    response = response_holder[0]
    _persist_prediction_response(
        settings,
        response,
        rows_relative_path=rows_relative_path,
        rows_sha256=rows_sha256_holder[0],
    )
    return response


def get_regression_prediction_rows(
    settings: Settings,
    prediction_id: UUID,
    *,
    limit: int,
    offset: int,
) -> RegressionPredictionRowsPageResponse:
    consistency = validate_regression_prediction_consistency(
        settings,
        prediction_id,
        verify_rows=False,
    )
    context = consistency.rows
    rows = [
        row
        for row_number, row in enumerate(
            _iter_regression_prediction_rows(context),
        )
        if offset <= row_number < offset + limit
    ]
    return RegressionPredictionRowsPageResponse(
        prediction_id=prediction_id,
        model_id=context.model_id,
        offset=offset,
        limit=limit,
        total=context.expected_total,
        returned=len(rows),
        has_previous=offset > 0,
        has_next=offset + len(rows) < context.expected_total,
        rows=rows,
    )


def iter_regression_prediction_rows(
    settings: Settings,
    prediction_id: UUID,
    *,
    consistency: RegressionPredictionConsistencyContext | None = None,
) -> Iterator[RegressionPredictionRow]:
    validated = consistency or validate_regression_prediction_consistency(
        settings,
        prediction_id,
        verify_rows=False,
    )
    return _iter_regression_prediction_rows(validated.rows)


def _iter_regression_prediction_rows(
    context: _PredictionRowsContext,
) -> Iterator[RegressionPredictionRow]:
    hasher = hashlib.sha256()
    actual_total = 0
    try:
        with context.path.open("rb") as handle:
            header_line = handle.readline()
            hasher.update(header_line)
            try:
                header = _PredictionRowsHeader.model_validate_json(header_line)
            except ValidationError as exc:
                raise _prediction_rows_artifact_error(
                    "regression_prediction_artifact_mismatch",
                ) from exc
            if header != context.header:
                raise _prediction_rows_artifact_error(
                    "regression_prediction_artifact_mismatch",
                )
            for raw_line in handle:
                hasher.update(raw_line)
                try:
                    payload = json.loads(raw_line.decode("utf-8"))
                    row = RegressionPredictionRow.model_validate(payload)
                except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
                    raise _prediction_rows_artifact_error(
                        "regression_prediction_rows_artifact_invalid",
                    ) from exc
                actual_total += 1
                yield row
    except OSError as exc:
        raise _prediction_rows_artifact_error(
            "regression_prediction_rows_artifact_unreadable",
        ) from exc

    if hasher.hexdigest() != context.sha256:
        raise _prediction_rows_artifact_error(
            "regression_prediction_rows_artifact_checksum_mismatch",
        )
    if actual_total != context.expected_total:
        raise _prediction_rows_artifact_error("regression_prediction_rows_artifact_invalid")


def validate_regression_prediction_consistency(
    settings: Settings,
    prediction_id: UUID,
    *,
    stored_result: StoredAnalysisRunResult | None = None,
    verify_rows: bool,
) -> RegressionPredictionConsistencyContext:
    record = get_analysis_run_record(settings.workspace_root, str(prediction_id))
    if record is None or record.method_id != REGRESSION_PREDICTION_METHOD_ID:
        raise ApiError(
            code="regression_prediction_not_found",
            message="요청한 회귀 예측 결과를 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    stored = stored_result or load_analysis_run_result_base(settings, prediction_id)
    try:
        config = _PredictionStoredConfig.model_validate_json(record.config_json)
        prediction = RegressionPredictionResponse.model_validate(stored.envelope.result)
        provenance = RegressionPredictionProvenance.model_validate(
            stored.envelope.provenance.model_dump(mode="json"),
        )
    except ValidationError as exc:
        raise _prediction_consistency_error(
            "regression_prediction_metadata_invalid",
            "저장된 회귀 예측 metadata 형식이 올바르지 않습니다.",
        ) from exc

    try:
        model_response = get_regression_model_manifest(settings, config.model_id)
    except ApiError as exc:
        if exc.code != "regression_model_not_found":
            raise _prediction_consistency_error(
                "regression_prediction_model_mismatch",
                "회귀 예측 model dependency를 검증할 수 없습니다.",
            ) from exc
        # A prediction is an immutable stored result. A deliberately removed model
        # disables new predictions, but does not erase the independently checksummed
        # result/config/rows relationships needed to restore the historical result.
        model_response = None
    try:
        source_context = get_dataset_rows_context(settings, config.source_dataset_version_id)
        target_context = get_dataset_rows_context(settings, config.target_dataset_version_id)
    except ApiError as exc:
        raise _prediction_consistency_error(
            "regression_prediction_model_mismatch",
            "회귀 예측 source/target dataset dependency를 검증할 수 없습니다.",
        ) from exc
    rows = _load_prediction_rows_context(settings, prediction_id, config)
    source_analysis = get_analysis_run_record(
        settings.workspace_root,
        str(config.source_analysis_id),
    )
    if source_analysis is None:
        raise _prediction_consistency_error(
            "regression_prediction_model_mismatch",
            "회귀 예측 source model metadata를 찾을 수 없습니다.",
        )

    current_method_version = get_method_version(REGRESSION_PREDICTION_METHOD_ID)
    if not (
        record.analysis_id == str(prediction_id)
        and config.prediction_id == prediction_id
        and config.analysis_id == prediction_id
        and stored.envelope.analysis_id == prediction_id
        and prediction.prediction_id == prediction_id
    ):
        raise _prediction_consistency_error(
            "regression_prediction_result_config_mismatch",
            "회귀 예측 result와 config의 prediction ID가 일치하지 않습니다.",
        )
    if not (
        record.method_version == current_method_version
        and config.method_version == current_method_version
        and stored.envelope.method_id == REGRESSION_PREDICTION_METHOD_ID
        and stored.envelope.method_version == current_method_version
        and provenance.method_id == REGRESSION_PREDICTION_METHOD_ID
        and provenance.method_version == current_method_version
    ):
        raise _prediction_consistency_error(
            "regression_prediction_result_config_mismatch",
            "회귀 예측 method version metadata가 일치하지 않습니다.",
        )
    if not (
        prediction.analysis_id == config.source_analysis_id
        and prediction.source_analysis_id == config.source_analysis_id
        and provenance.source_analysis_id == config.source_analysis_id
        and source_analysis.analysis_id == str(config.source_analysis_id)
        and source_analysis.method_id == "regression.linear_model"
    ):
        raise _prediction_consistency_error(
            "regression_prediction_model_mismatch",
            "회귀 예측 source analysis와 model metadata가 일치하지 않습니다.",
        )
    if model_response is not None and not (
        model_response.analysis_id == config.source_analysis_id
        and source_analysis.method_version == model_response.method_version
        and model_response.method_id == "regression.linear_model"
        and model_response.manifest.get("method_id") == "regression.linear_model"
        and model_response.manifest.get("method_version") == model_response.method_version
        and model_response.manifest.get("model_id") == str(config.model_id)
        and model_response.manifest.get("analysis_id") == str(config.source_analysis_id)
    ):
        raise _prediction_consistency_error(
            "regression_prediction_model_mismatch",
            "회귀 예측 source analysis와 model metadata가 일치하지 않습니다.",
        )
    if not (
        record.dataset_version_id == str(config.target_dataset_version_id)
        and stored.envelope.dataset_version_id == config.target_dataset_version_id
        and provenance.dataset_version_id == config.target_dataset_version_id
        and prediction.target_dataset_version_id == config.target_dataset_version_id
        and provenance.target_dataset_version_id == config.target_dataset_version_id
        and prediction.source_dataset_version_id == config.source_dataset_version_id
        and provenance.source_dataset_version_id == config.source_dataset_version_id
    ):
        raise _prediction_consistency_error(
            "regression_prediction_result_config_mismatch",
            "회귀 예측 source/target dataset metadata가 일치하지 않습니다.",
        )
    if model_response is not None and not (
        model_response.dataset_version_id == config.source_dataset_version_id
        and model_response.manifest.get("dataset_version_id")
        == str(config.source_dataset_version_id)
    ):
        raise _prediction_consistency_error(
            "regression_prediction_result_config_mismatch",
            "회귀 예측 source/target dataset metadata가 일치하지 않습니다.",
        )
    if not (
        prediction.model_id == config.model_id
        and provenance.model_id == config.model_id
        and prediction.model_manifest_sha256 == config.model_manifest_sha256
        and provenance.model_manifest_sha256 == config.model_manifest_sha256
    ):
        raise _prediction_consistency_error(
            "regression_prediction_model_mismatch",
            "회귀 예측 model manifest metadata가 일치하지 않습니다.",
        )
    if model_response is not None and not (
        model_response.model_id == config.model_id
        and model_response.manifest_sha256 == config.model_manifest_sha256
    ):
        raise _prediction_consistency_error(
            "regression_prediction_model_mismatch",
            "회귀 예측 model manifest metadata가 일치하지 않습니다.",
        )
    if not (
        prediction.target_schema_hash == config.target_schema_hash
        and provenance.target_schema_hash == config.target_schema_hash
        and provenance.source_schema_hash_at_fit == config.source_schema_hash_at_fit
        and provenance.source_schema_hash_current == config.source_schema_hash_current
        and config.source_schema_hash_at_fit == config.source_schema_hash_current
        and provenance.source_analysis_stale_at_prediction is False
        and provenance.source_canonical_artifact_sha256
        == source_context.canonical_rows_artifact.sha256
        and provenance.target_canonical_artifact_sha256
        == target_context.canonical_rows_artifact.sha256
    ):
        raise _prediction_consistency_error(
            "regression_prediction_result_config_mismatch",
            "회귀 예측 schema/freshness metadata가 일치하지 않습니다.",
        )
    if model_response is not None and not (
        model_response.schema_hash == config.source_schema_hash_at_fit
        and model_response.manifest.get("source_schema_hash") == config.source_schema_hash_at_fit
        and provenance.source_canonical_artifact_sha256
        == model_response.manifest.get("source_canonical_artifact_sha256")
    ):
        raise _prediction_consistency_error(
            "regression_prediction_result_config_mismatch",
            "회귀 예측 schema/freshness metadata가 일치하지 않습니다.",
        )
    if not (
        prediction.row_count_total == config.row_count_total
        and prediction.row_limit == config.row_limit
        and prediction.row_count_predicted == config.row_count_predicted
        and prediction.row_count_excluded == config.row_count_excluded
        and prediction.row_count_predicted + prediction.row_count_excluded
        == prediction.row_count_total
        and len(prediction.rows) == min(prediction.row_count_predicted, prediction.row_limit)
        and prediction.row_count_omitted == prediction.row_count_predicted - len(prediction.rows)
        and prediction.truncated == (prediction.row_count_omitted > 0)
        and provenance.row_count_total == prediction.row_count_total
        and provenance.row_count_included == prediction.row_count_predicted
    ):
        raise _prediction_consistency_error(
            "regression_prediction_result_config_mismatch",
            "회귀 예측 row count metadata가 일치하지 않습니다.",
        )
    if not (
        provenance.prediction_schema_version
        == config.prediction_schema_version
        == REGRESSION_PREDICTION_SCHEMA_VERSION
        and config.config_schema_version == REGRESSION_PREDICTION_CONFIG_SCHEMA_VERSION
        and config.rows_artifact_schema_version == REGRESSION_PREDICTION_ROWS_SCHEMA_VERSION
        and prediction.confidence_level == config.confidence_level
        and provenance.confidence_level == config.confidence_level
        and provenance.missing_policy == config.missing_policy
        and provenance.include_intervals == config.include_intervals
        and provenance.created_at == record.created_at
        and provenance.app_version == record.app_version
        and stored.envelope.provenance.model_dump(mode="json")
        == prediction.provenance.model_dump(mode="json")
    ):
        raise _prediction_consistency_error(
            "regression_prediction_result_config_mismatch",
            "회귀 예측 result provenance와 config가 일치하지 않습니다.",
        )
    if model_response is not None and (
        provenance.model_manifest_schema_version
        != model_response.manifest.get("manifest_schema_version")
    ):
        raise _prediction_consistency_error(
            "regression_prediction_result_config_mismatch",
            "회귀 예측 result provenance와 config가 일치하지 않습니다.",
        )
    _validate_prediction_rows_relationship(rows.header, config)

    context = RegressionPredictionConsistencyContext(
        stored_result=stored,
        config=config,
        prediction=prediction,
        model_response=model_response,
        rows=rows,
    )
    if verify_rows:
        for _row in _iter_regression_prediction_rows(rows):
            pass
    return context


def _load_prediction_rows_context(
    settings: Settings,
    prediction_id: UUID,
    config: _PredictionStoredConfig,
) -> _PredictionRowsContext:
    artifacts = [
        artifact
        for artifact in list_analysis_artifact_records(
            settings.workspace_root,
            str(prediction_id),
        )
        if artifact.kind == REGRESSION_PREDICTION_ROWS_ARTIFACT_KIND
    ]
    if len(artifacts) != 1:
        raise _prediction_rows_artifact_error("regression_prediction_rows_artifact_missing")
    artifact = artifacts[0]
    expected_path = _prediction_rows_relative_path(str(prediction_id)).as_posix()
    if (
        artifact.analysis_id != str(prediction_id)
        or artifact.path != expected_path
        or artifact.media_type != REGRESSION_PREDICTION_ROWS_MEDIA_TYPE
    ):
        raise _prediction_rows_artifact_error("regression_prediction_artifact_mismatch")
    rows_path = _safe_prediction_rows_path(settings.workspace_root, artifact.path)
    if not rows_path.exists():
        raise _prediction_rows_artifact_error("regression_prediction_rows_artifact_missing")
    try:
        with rows_path.open("rb") as handle:
            header = _PredictionRowsHeader.model_validate_json(handle.readline())
    except (OSError, ValidationError) as exc:
        raise _prediction_rows_artifact_error("regression_prediction_artifact_mismatch") from exc
    return _PredictionRowsContext(
        model_id=config.model_id,
        expected_total=config.row_count_predicted,
        path=rows_path,
        sha256=artifact.sha256,
        header=header,
    )


def _validate_prediction_rows_relationship(
    header: _PredictionRowsHeader,
    config: _PredictionStoredConfig,
) -> None:
    if not (
        header.prediction_id == config.prediction_id
        and header.analysis_id == config.analysis_id
        and header.method_id == config.method_id
        and header.method_version == config.method_version
        and header.model_id == config.model_id
        and header.source_analysis_id == config.source_analysis_id
        and header.source_dataset_version_id == config.source_dataset_version_id
        and header.target_dataset_version_id == config.target_dataset_version_id
        and header.model_manifest_sha256 == config.model_manifest_sha256
        and header.target_schema_hash == config.target_schema_hash
        and header.row_count_predicted == config.row_count_predicted
    ):
        raise _prediction_rows_artifact_error("regression_prediction_artifact_mismatch")


def _prediction_consistency_error(code: str, message: str) -> ApiError:
    return ApiError(code=code, message=message, status_code=status.HTTP_409_CONFLICT)


def _build_prediction_preflight_state(
    settings: Settings,
    model_id: UUID,
    dataset_version_id: UUID,
) -> _PredictionPreflightState:
    model_response = get_regression_model_manifest(settings, model_id)
    manifest = model_response.manifest
    if manifest.get("model_family") != "linear_regression_ols":
        raise ApiError(
            code="regression_model_family_unsupported",
            message="현재 회귀 예측 사전점검은 OLS 회귀모델 manifest만 지원합니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    try:
        source_version_id = UUID(str(manifest.get("dataset_version_id")))
    except (TypeError, ValueError) as exc:
        raise ApiError(
            code="regression_model_manifest_invalid",
            message="저장된 회귀모델 manifest 형식이 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc
    target_context = get_dataset_rows_context(settings, dataset_version_id)
    issues: list[RegressionPredictionPreflightIssue] = []
    source_context, source_analysis = _validated_source_model_dependencies(
        settings=settings,
        model_response=model_response,
        source_version_id=source_version_id,
        issues=issues,
    )
    if target_context.version.schema_hash != model_response.schema_hash:
        issues.append(
            RegressionPredictionPreflightIssue(
                code="prediction_schema_hash_mismatch",
                severity="warning",
                message="대상 데이터셋 schema hash가 모델 생성 시점과 다릅니다.",
            ),
        )

    source_row_indices: set[int] | None = None
    if source_context is not None and source_analysis is not None:
        try:
            source_row_indices = _model_source_row_indices(
                settings=settings,
                analysis_id=str(model_response.analysis_id),
                expected_sha256=str(manifest.get("row_snapshot_sha256")),
            )
        except ApiError:
            issues.append(
                RegressionPredictionPreflightIssue(
                    code="regression_prediction_source_analysis_invalid",
                    severity="error",
                    message="회귀모형 source analysis의 row snapshot을 검증할 수 없습니다.",
                ),
            )
    checks = _prediction_column_checks(
        manifest=manifest,
        source_columns=[] if source_context is None else source_context.columns,
        target_columns=target_context.columns,
        issues=issues,
    )
    if source_context is not None:
        _fill_training_ranges(
            checks=checks,
            source_context=source_context,
            source_row_indices=source_row_indices,
        )
    row_count_usable = _scan_target_rows(
        checks=checks,
        target_context=target_context,
    )
    _append_scan_issues(checks, issues)
    if row_count_usable == 0:
        issues.append(
            RegressionPredictionPreflightIssue(
                code="prediction_no_usable_rows",
                severity="error",
                message="예측에 사용할 수 있는 행이 없습니다.",
                count=0,
            ),
        )

    return _PredictionPreflightState(
        model_response=model_response,
        source_dataset_version_id=source_version_id,
        target_context=target_context,
        source_context=source_context,
        source_analysis_stale=None if source_analysis is None else source_analysis.stale,
        checks=checks,
        issues=issues,
        row_count_usable=row_count_usable,
    )


def _prediction_preflight_response(
    state: _PredictionPreflightState,
) -> RegressionPredictionPreflightResponse:
    model_response = state.model_response
    target_context = state.target_context
    prediction_ready = state.row_count_usable > 0 and not any(
        issue.severity == "error" for issue in state.issues
    )
    return RegressionPredictionPreflightResponse(
        model_id=model_response.model_id,
        analysis_id=model_response.analysis_id,
        source_dataset_version_id=state.source_dataset_version_id,
        target_dataset_version_id=UUID(target_context.version.version_id),
        model_manifest_sha256=model_response.manifest_sha256,
        source_schema_hash=model_response.schema_hash,
        source_schema_hash_current=(
            None if state.source_context is None else state.source_context.version.schema_hash
        ),
        source_analysis_stale=state.source_analysis_stale,
        target_schema_hash=target_context.version.schema_hash,
        schema_hash_match=target_context.version.schema_hash == model_response.schema_hash,
        row_count_total=target_context.version.row_count,
        row_count_usable=state.row_count_usable,
        prediction_ready=prediction_ready,
        required_columns=[_mapping_payload(check) for check in state.checks],
        numeric_checks=[
            _numeric_check_payload(check) for check in state.checks if _is_numeric_check(check)
        ],
        categorical_checks=[
            _categorical_check_payload(check)
            for check in state.checks
            if _is_categorical_check(check)
        ],
        issues=state.issues,
    )


def _validated_source_model_dependencies(
    *,
    settings: Settings,
    model_response: RegressionModelManifestResponse,
    source_version_id: UUID,
    issues: list[RegressionPredictionPreflightIssue],
) -> tuple[DatasetRowsContext | None, AnalysisRunRecord | None]:
    manifest = model_response.manifest
    source_analysis = get_analysis_run_record(
        settings.workspace_root,
        str(model_response.analysis_id),
    )
    if source_analysis is None:
        issues.append(
            RegressionPredictionPreflightIssue(
                code="regression_prediction_source_analysis_missing",
                severity="error",
                message="회귀모형을 생성한 source analysis를 찾을 수 없습니다.",
            ),
        )
    else:
        if (
            source_analysis.method_id != "regression.linear_model"
            or source_analysis.dataset_version_id != str(source_version_id)
        ):
            issues.append(
                RegressionPredictionPreflightIssue(
                    code="regression_prediction_source_analysis_invalid",
                    severity="error",
                    message="회귀모형 source analysis metadata가 model과 일치하지 않습니다.",
                ),
            )
        if (
            source_analysis.method_version != model_response.method_version
            or manifest.get("method_version") != model_response.method_version
        ):
            issues.append(
                RegressionPredictionPreflightIssue(
                    code="regression_prediction_source_method_version_mismatch",
                    severity="error",
                    message=(
                        "회귀모형 source analysis와 model의 method version이 " "일치하지 않습니다."
                    ),
                ),
            )
        if source_analysis.stale:
            issues.append(
                RegressionPredictionPreflightIssue(
                    code="regression_prediction_source_model_stale",
                    severity="error",
                    message=(
                        "source 회귀모형이 stale 상태입니다. 현재 schema로 "
                        "회귀모형을 다시 적합하세요."
                    ),
                ),
            )

    manifest_metadata_matches = (
        model_response.method_id == "regression.linear_model"
        and manifest.get("method_id") == "regression.linear_model"
        and manifest.get("model_id") == str(model_response.model_id)
        and manifest.get("analysis_id") == str(model_response.analysis_id)
        and manifest.get("dataset_version_id") == str(source_version_id)
        and manifest.get("source_schema_hash") == model_response.schema_hash
    )
    manifest_schema_version = manifest.get("manifest_schema_version")
    if (
        not manifest_metadata_matches
        or isinstance(manifest_schema_version, bool)
        or not isinstance(manifest_schema_version, int)
        or manifest_schema_version < 1
    ):
        issues.append(
            RegressionPredictionPreflightIssue(
                code="regression_prediction_source_analysis_invalid",
                severity="error",
                message="회귀모형 manifest metadata가 source analysis와 일치하지 않습니다.",
            ),
        )

    try:
        source_context = get_dataset_rows_context(settings, source_version_id)
    except ApiError:
        issues.append(
            RegressionPredictionPreflightIssue(
                code="regression_prediction_source_analysis_invalid",
                severity="error",
                message="회귀모형 source dataset version을 검증할 수 없습니다.",
            ),
        )
        return None, source_analysis

    if source_context.version.schema_hash != model_response.schema_hash:
        issues.append(
            RegressionPredictionPreflightIssue(
                code="regression_prediction_source_schema_mismatch",
                severity="error",
                message=(
                    "source dataset schema가 모델 적합 시점과 다릅니다. "
                    "회귀모형을 다시 적합하세요."
                ),
            ),
        )
    if (
        manifest.get("source_canonical_artifact_sha256")
        != source_context.canonical_rows_artifact.sha256
    ):
        issues.append(
            RegressionPredictionPreflightIssue(
                code="regression_prediction_source_analysis_invalid",
                severity="error",
                message="회귀모형 source canonical artifact가 manifest와 일치하지 않습니다.",
            ),
        )
    return source_context, source_analysis


@dataclass(frozen=True)
class _PredictionBasis:
    coefficient_order: list[str]
    xtx_inverse: list[list[float]]
    sigma_squared: float
    df_residual: int


def _validated_prediction_basis(manifest: dict[str, Any]) -> _PredictionBasis:
    basis = manifest.get("prediction_basis")
    if not isinstance(basis, dict):
        raise ApiError(
            code="regression_prediction_manifest_uncertainty_missing",
            message="저장된 회귀모델 manifest에 예측 구간 계산 정보가 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    coefficient_order_value = basis.get("coefficient_order")
    xtx_inverse_value = basis.get("xtx_inverse")
    sigma_squared_value = basis.get("sigma_squared")
    df_residual_value = basis.get("df_residual")
    if (
        not isinstance(coefficient_order_value, list)
        or not coefficient_order_value
        or not all(isinstance(term, str) for term in coefficient_order_value)
        or not isinstance(xtx_inverse_value, list)
        or not isinstance(sigma_squared_value, int | float)
        or not isinstance(df_residual_value, int)
    ):
        raise ApiError(
            code="regression_prediction_manifest_invalid",
            message="저장된 회귀모델 manifest의 예측 계산 정보가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    xtx_inverse: list[list[float]] = []
    row_length = len(coefficient_order_value)
    for row in xtx_inverse_value:
        if not isinstance(row, list) or len(row) != row_length:
            raise ApiError(
                code="regression_prediction_manifest_invalid",
                message="저장된 회귀모델 manifest의 예측 계산 정보가 올바르지 않습니다.",
                status_code=status.HTTP_409_CONFLICT,
            )
        numeric_row: list[float] = []
        for value in row:
            if not isinstance(value, int | float) or not isfinite(float(value)):
                raise ApiError(
                    code="regression_prediction_manifest_invalid",
                    message="저장된 회귀모델 manifest의 예측 계산 정보가 올바르지 않습니다.",
                    status_code=status.HTTP_409_CONFLICT,
                )
            numeric_row.append(float(value))
        xtx_inverse.append(numeric_row)
    if len(xtx_inverse) != row_length:
        raise ApiError(
            code="regression_prediction_manifest_invalid",
            message="저장된 회귀모델 manifest의 예측 계산 정보가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    sigma_squared = float(sigma_squared_value)
    if sigma_squared <= 0.0 or not isfinite(sigma_squared) or df_residual_value <= 0:
        raise ApiError(
            code="regression_prediction_manifest_invalid",
            message="저장된 회귀모델 manifest의 예측 계산 정보가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    return _PredictionBasis(
        coefficient_order=[str(term) for term in coefficient_order_value],
        xtx_inverse=xtx_inverse,
        sigma_squared=sigma_squared,
        df_residual=df_residual_value,
    )


def _coefficient_estimates(manifest: dict[str, Any]) -> list[float]:
    coefficients = manifest.get("coefficients")
    if not isinstance(coefficients, list) or not coefficients:
        raise ApiError(
            code="regression_prediction_manifest_invalid",
            message="저장된 회귀모델 manifest의 계수 정보가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    estimates: list[float] = []
    coefficient_terms: list[str] = []
    for item in coefficients:
        if not isinstance(item, dict):
            raise ApiError(
                code="regression_prediction_manifest_invalid",
                message="저장된 회귀모델 manifest의 계수 정보가 올바르지 않습니다.",
                status_code=status.HTTP_409_CONFLICT,
            )
        term = item.get("term")
        estimate = item.get("estimate")
        if not isinstance(term, str) or not isinstance(estimate, int | float):
            raise ApiError(
                code="regression_prediction_manifest_invalid",
                message="저장된 회귀모델 manifest의 계수 정보가 올바르지 않습니다.",
                status_code=status.HTTP_409_CONFLICT,
            )
        estimate_value = float(estimate)
        if not isfinite(estimate_value):
            raise ApiError(
                code="regression_prediction_manifest_invalid",
                message="저장된 회귀모델 manifest의 계수 정보가 올바르지 않습니다.",
                status_code=status.HTTP_409_CONFLICT,
            )
        coefficient_terms.append(term)
        estimates.append(estimate_value)

    basis = manifest.get("prediction_basis")
    if isinstance(basis, dict) and basis.get("coefficient_order") != coefficient_terms:
        raise ApiError(
            code="regression_prediction_manifest_invalid",
            message="저장된 회귀모델 manifest의 계수 순서가 예측 계산 정보와 일치하지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return estimates


def _validate_prediction_dimensions(
    *,
    basis: _PredictionBasis,
    coefficient_count: int,
) -> None:
    if len(basis.coefficient_order) != coefficient_count:
        raise ApiError(
            code="regression_prediction_manifest_invalid",
            message="저장된 회귀모델 manifest의 계수 차원이 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )


def _calculate_prediction_response(
    *,
    settings: Settings,
    prediction_id: UUID,
    created_at: str,
    request: RegressionPredictionRequest,
    preflight: RegressionPredictionPreflightResponse,
    state: _PredictionPreflightState,
    basis: _PredictionBasis,
    coefficient_estimates: list[float],
    row_sink: Callable[[RegressionPredictionRow], None],
) -> RegressionPredictionResponse:
    t_critical = float(
        stats.t.ppf(1.0 - ((1.0 - request.confidence_level) / 2.0), df=basis.df_residual),
    )
    if not isfinite(t_critical):
        raise ApiError(
            code="regression_prediction_manifest_invalid",
            message="저장된 회귀모델 manifest의 자유도 정보가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    rows: list[RegressionPredictionRow] = []
    row_count_predicted = 0
    row_count_excluded = 0
    row_count_omitted = 0
    warning_counts: dict[str, int] = {}
    for row_index, row in enumerate(iter_dataset_rows(state.target_context)):
        values, exclusion_codes, row_warning_codes = _prediction_row_values(
            row=row,
            checks=state.checks,
            target_context=state.target_context,
        )
        if exclusion_codes:
            row_count_excluded += 1
            for code in set(exclusion_codes):
                warning_counts[code] = warning_counts.get(code, 0) + 1
            continue

        design_vector = _design_vector_for_manifest(
            manifest=state.model_response.manifest,
            values_by_source_column_id=values,
        )
        if len(design_vector) != len(coefficient_estimates):
            raise ApiError(
                code="regression_prediction_manifest_invalid",
                message="저장된 회귀모델 manifest의 설계행렬 차원이 올바르지 않습니다.",
                status_code=status.HTTP_409_CONFLICT,
            )
        predicted_mean = _dot(design_vector, coefficient_estimates)
        leverage = _quadratic_form(design_vector, basis.xtx_inverse)
        if leverage < 0.0 and leverage > -1e-12:
            leverage = 0.0
        if leverage < 0.0 or not isfinite(leverage):
            raise ApiError(
                code="regression_prediction_manifest_invalid",
                message="저장된 회귀모델 manifest의 예측 분산 계산 정보가 올바르지 않습니다.",
                status_code=status.HTTP_409_CONFLICT,
            )

        mean_interval: RegressionPredictionInterval | None = None
        prediction_interval: RegressionPredictionInterval | None = None
        if request.include_intervals:
            mean_standard_error = sqrt(basis.sigma_squared * leverage)
            prediction_standard_error = sqrt(basis.sigma_squared * (1.0 + leverage))
            mean_interval = _prediction_interval(
                center=predicted_mean,
                standard_error=mean_standard_error,
                t_critical=t_critical,
                confidence_level=request.confidence_level,
            )
            prediction_interval = _prediction_interval(
                center=predicted_mean,
                standard_error=prediction_standard_error,
                t_critical=t_critical,
                confidence_level=request.confidence_level,
            )

        row_count_predicted += 1
        for code in set(row_warning_codes):
            warning_counts[code] = warning_counts.get(code, 0) + 1
        prediction_row = RegressionPredictionRow(
            row_index=row_index,
            predicted_mean=predicted_mean,
            mean_confidence_interval=mean_interval,
            prediction_interval=prediction_interval,
            warnings=sorted(set(row_warning_codes)),
        )
        row_sink(prediction_row)
        if len(rows) < MAX_REGRESSION_PREDICTION_INLINE_ROWS:
            rows.append(prediction_row)
        else:
            row_count_omitted += 1

    if row_count_predicted != preflight.row_count_usable:
        raise ApiError(
            code="regression_prediction_metadata_invalid",
            message="회귀 예측 행 수가 사전점검 결과와 일치하지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    if state.source_context is None or preflight.source_schema_hash_current is None:
        raise ApiError(
            code="regression_prediction_source_analysis_invalid",
            message="회귀모델 source dependency를 검증할 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    warnings = _prediction_warnings(
        preflight=preflight,
        row_count_excluded=row_count_excluded,
        row_count_omitted=row_count_omitted,
        row_warning_counts=warning_counts,
    )
    return RegressionPredictionResponse(
        prediction_id=prediction_id,
        model_id=preflight.model_id,
        analysis_id=preflight.analysis_id,
        source_analysis_id=preflight.analysis_id,
        source_dataset_version_id=preflight.source_dataset_version_id,
        target_dataset_version_id=preflight.target_dataset_version_id,
        model_manifest_sha256=preflight.model_manifest_sha256,
        target_schema_hash=preflight.target_schema_hash,
        row_count_total=preflight.row_count_total,
        row_count_predicted=row_count_predicted,
        row_count_excluded=row_count_excluded,
        row_count_omitted=row_count_omitted,
        row_limit=MAX_REGRESSION_PREDICTION_INLINE_ROWS,
        truncated=row_count_omitted > 0,
        confidence_level=request.confidence_level,
        warnings=warnings,
        provenance=RegressionPredictionProvenance(
            method_id=REGRESSION_PREDICTION_METHOD_ID,
            method_version=REGRESSION_PREDICTION_METHOD_VERSION,
            dataset_version_id=preflight.target_dataset_version_id,
            source_schema_hash=preflight.target_schema_hash,
            row_count_total=preflight.row_count_total,
            row_count_included=row_count_predicted,
            app_version=APP_VERSION,
            source_analysis_id=preflight.analysis_id,
            source_analysis_stale_at_prediction=False,
            source_dataset_version_id=preflight.source_dataset_version_id,
            source_schema_hash_at_fit=preflight.source_schema_hash,
            source_schema_hash_current=preflight.source_schema_hash_current,
            target_dataset_version_id=preflight.target_dataset_version_id,
            target_schema_hash=preflight.target_schema_hash,
            model_id=preflight.model_id,
            model_manifest_sha256=preflight.model_manifest_sha256,
            prediction_schema_version=REGRESSION_PREDICTION_SCHEMA_VERSION,
            model_manifest_schema_version=int(
                state.model_response.manifest["manifest_schema_version"],
            ),
            missing_policy=request.missing_policy,
            confidence_level=request.confidence_level,
            include_intervals=request.include_intervals,
            source_canonical_artifact_sha256=state.source_context.canonical_rows_artifact.sha256,
            target_canonical_artifact_sha256=(state.target_context.canonical_rows_artifact.sha256),
            created_at=created_at,
            **runtime_build_provenance(settings),
        ),
        columns=preflight.required_columns,
        rows=rows,
    )


def _prediction_row_values(
    *,
    row: Sequence[str | None],
    checks: list[_PredictionColumnCheck],
    target_context: DatasetRowsContext,
) -> tuple[dict[str, float | str], list[str], list[str]]:
    values: dict[str, float | str] = {}
    exclusion_codes: list[str] = []
    warning_codes: list[str] = []
    for check in checks:
        if check.target_column is None or check.status == "error":
            exclusion_codes.append("prediction_row_required_column_unavailable")
            continue
        raw_value = (
            row[check.target_column.column_index]
            if check.target_column.column_index < len(row)
            else None
        )
        if check.predictor_kind == "numeric":
            if raw_value is None or raw_value.strip() == "":
                exclusion_codes.append("prediction_row_missing_value")
                continue
            parsed = _parse_numeric_cell(
                raw_value,
                decimal=target_context.parsing.decimal,
                thousands=target_context.parsing.thousands,
            )
            if parsed is None:
                exclusion_codes.append("prediction_row_non_numeric_value")
                continue
            values[check.source_column_id] = parsed
            if (
                check.training_min is not None
                and check.training_max is not None
                and (parsed < check.training_min or parsed > check.training_max)
            ):
                warning_codes.append("prediction_extrapolation_risk")
            continue

        if raw_value is None or raw_value.strip() == "":
            exclusion_codes.append("prediction_row_missing_value")
            continue
        value = raw_value.strip()
        if check.training_levels is not None and value not in check.training_levels:
            exclusion_codes.append("prediction_row_unseen_categorical_level")
            continue
        values[check.source_column_id] = value
    return values, exclusion_codes, warning_codes


def _design_vector_for_manifest(
    *,
    manifest: dict[str, Any],
    values_by_source_column_id: dict[str, float | str],
) -> list[float]:
    model_specification = manifest.get("model_specification")
    if not isinstance(model_specification, dict):
        raise ApiError(
            code="regression_prediction_manifest_invalid",
            message="저장된 회귀모델 manifest의 모델 사양이 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    if model_specification.get("intercept") is not True:
        raise ApiError(
            code="regression_prediction_manifest_invalid",
            message="현재 예측 API는 절편을 포함한 OLS manifest만 지원합니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    terms = model_specification.get("terms")
    if not isinstance(terms, list):
        raise ApiError(
            code="regression_prediction_manifest_invalid",
            message="저장된 회귀모델 manifest의 모델 항 정보가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    vector = [1.0]
    for term in terms:
        if not isinstance(term, dict):
            raise ApiError(
                code="regression_prediction_manifest_invalid",
                message="저장된 회귀모델 manifest의 모델 항 정보가 올바르지 않습니다.",
                status_code=status.HTTP_409_CONFLICT,
            )
        kind = term.get("kind")
        source_column_ids = term.get("source_column_ids")
        if kind == "numeric_main_effect":
            column_id = _single_source_column_id(source_column_ids)
            vector.append(_numeric_prediction_value(values_by_source_column_id, column_id))
            continue
        if kind == "categorical_main_effect":
            categorical_column_id = term.get("column_id")
            levels = term.get("levels")
            if (
                not isinstance(categorical_column_id, str)
                or not isinstance(levels, list)
                or len(levels) < 2
            ):
                raise ApiError(
                    code="regression_prediction_manifest_invalid",
                    message="저장된 회귀모델 manifest의 범주형 항 정보가 올바르지 않습니다.",
                    status_code=status.HTTP_409_CONFLICT,
                )
            value = values_by_source_column_id.get(categorical_column_id)
            if not isinstance(value, str):
                raise ApiError(
                    code="regression_prediction_manifest_invalid",
                    message="저장된 회귀모델 manifest의 범주형 항 정보가 올바르지 않습니다.",
                    status_code=status.HTTP_409_CONFLICT,
                )
            for level in levels[1:]:
                if not isinstance(level, str):
                    raise ApiError(
                        code="regression_prediction_manifest_invalid",
                        message="저장된 회귀모델 manifest의 범주형 항 정보가 올바르지 않습니다.",
                        status_code=status.HTTP_409_CONFLICT,
                    )
                vector.append(1.0 if value == level else 0.0)
            continue
        if kind == "numeric_quadratic":
            column_id = _single_source_column_id(source_column_ids)
            value = _numeric_prediction_value(values_by_source_column_id, column_id)
            vector.append(value * value)
            continue
        if kind == "numeric_interaction":
            if (
                not isinstance(source_column_ids, list)
                or len(source_column_ids) != 2
                or not all(isinstance(column_id, str) for column_id in source_column_ids)
            ):
                raise ApiError(
                    code="regression_prediction_manifest_invalid",
                    message="저장된 회귀모델 manifest의 상호작용 항 정보가 올바르지 않습니다.",
                    status_code=status.HTTP_409_CONFLICT,
                )
            left = _numeric_prediction_value(values_by_source_column_id, source_column_ids[0])
            right = _numeric_prediction_value(values_by_source_column_id, source_column_ids[1])
            vector.append(left * right)
            continue
        raise ApiError(
            code="regression_prediction_manifest_invalid",
            message="저장된 회귀모델 manifest의 모델 항 종류가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return vector


def _single_source_column_id(value: object) -> str:
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], str):
        raise ApiError(
            code="regression_prediction_manifest_invalid",
            message="저장된 회귀모델 manifest의 모델 항 컬럼 정보가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return value[0]


def _numeric_prediction_value(
    values_by_source_column_id: dict[str, float | str],
    column_id: str,
) -> float:
    value = values_by_source_column_id.get(column_id)
    if not isinstance(value, float):
        raise ApiError(
            code="regression_prediction_manifest_invalid",
            message="저장된 회귀모델 manifest의 숫자형 항 정보가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return value


def _prediction_interval(
    *,
    center: float,
    standard_error: float,
    t_critical: float,
    confidence_level: float,
) -> RegressionPredictionInterval:
    margin = t_critical * standard_error
    return RegressionPredictionInterval(
        method="t",
        level=confidence_level,
        lower=center - margin,
        upper=center + margin,
    )


def _dot(left: list[float], right: list[float]) -> float:
    return float(
        sum(left_value * right_value for left_value, right_value in zip(left, right, strict=False)),
    )


def _quadratic_form(vector: list[float], matrix: list[list[float]]) -> float:
    total = 0.0
    for row_index, row in enumerate(matrix):
        total += vector[row_index] * _dot(row, vector)
    return float(total)


def _prediction_warnings(
    *,
    preflight: RegressionPredictionPreflightResponse,
    row_count_excluded: int,
    row_count_omitted: int,
    row_warning_counts: dict[str, int],
) -> list[RegressionPredictionWarning]:
    warnings = [
        RegressionPredictionWarning(
            code="regression_prediction_not_causation",
            severity="info",
            message="회귀 예측은 관찰 데이터 기반의 수학적 예측이며 인과 효과를 의미하지 않습니다.",
        ),
        RegressionPredictionWarning(
            code="regression_prediction_intervals_assumption",
            severity="info",
            message=(
                "신뢰구간과 예측구간은 OLS 선형성, 독립성, 등분산성, "
                "잔차 분포 가정에 민감합니다."
            ),
        ),
    ]
    for issue in preflight.issues:
        if issue.severity == "warning":
            warnings.append(
                RegressionPredictionWarning(
                    code=issue.code,
                    severity="warning",
                    message=issue.message,
                    count=issue.count,
                ),
            )
    if row_count_excluded > 0:
        warnings.append(
            RegressionPredictionWarning(
                code="regression_prediction_rows_excluded",
                severity="warning",
                message="complete-case 정책에 따라 일부 행은 예측에서 제외되었습니다.",
                count=row_count_excluded,
            ),
        )
    if row_count_omitted > 0:
        warnings.append(
            RegressionPredictionWarning(
                code="regression_prediction_rows_truncated",
                severity="warning",
                message="응답 크기 제한 때문에 일부 예측 행은 이번 응답에서 생략되었습니다.",
                count=row_count_omitted,
            ),
        )
    for code, count in sorted(row_warning_counts.items()):
        if code == "prediction_extrapolation_risk":
            continue
        warnings.append(
            RegressionPredictionWarning(
                code=code,
                severity="warning",
                message="일부 행이 예측 조건을 만족하지 않았습니다.",
                count=count,
            ),
        )
    return warnings


def _persist_prediction_response(
    settings: Settings,
    response: RegressionPredictionResponse,
    *,
    rows_relative_path: Path,
    rows_sha256: str,
) -> None:
    completed_at = response.provenance.created_at
    result_relative_path = _prediction_result_relative_path(str(response.prediction_id))
    result_path = settings.workspace_root / result_relative_path
    envelope = AnalysisResultEnvelope(
        analysis_id=response.prediction_id,
        method_id=REGRESSION_PREDICTION_METHOD_ID,
        method_version=REGRESSION_PREDICTION_METHOD_VERSION,
        dataset_version_id=response.target_dataset_version_id,
        status="succeeded",
        warnings=[
            AnalysisWarning(
                code=warning.code,
                severity=warning.severity,
                message=warning.message,
            )
            for warning in response.warnings
        ],
        provenance=response.provenance,
        result=response.model_dump(mode="json"),
    )
    result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
    result_sha256 = hashlib.sha256(result_bytes).hexdigest()

    try:
        atomic_write_bytes(result_path, result_bytes)
        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(response.prediction_id),
                method_id=REGRESSION_PREDICTION_METHOD_ID,
                method_version=REGRESSION_PREDICTION_METHOD_VERSION,
                dataset_version_id=str(response.target_dataset_version_id),
                config_json=_prediction_config_json(response),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            [
                AnalysisArtifactRecord(
                    artifact_id=str(uuid4()),
                    analysis_id=str(response.prediction_id),
                    kind=REGRESSION_PREDICTION_ROWS_ARTIFACT_KIND,
                    path=rows_relative_path.as_posix(),
                    sha256=rows_sha256,
                    media_type=REGRESSION_PREDICTION_ROWS_MEDIA_TYPE,
                    created_at=completed_at,
                ),
            ],
        )
    except Exception:
        _remove_file_if_exists(result_path)
        _remove_file_if_exists(settings.workspace_root / rows_relative_path)
        raise


def _prediction_config_json(response: RegressionPredictionResponse) -> str:
    payload = _PredictionStoredConfig(
        config_schema_version=3,
        prediction_id=response.prediction_id,
        analysis_id=response.prediction_id,
        method_id="regression.predict",
        method_version=REGRESSION_PREDICTION_METHOD_VERSION,
        model_id=response.model_id,
        source_analysis_id=response.source_analysis_id,
        source_dataset_version_id=response.source_dataset_version_id,
        source_schema_hash_at_fit=response.provenance.source_schema_hash_at_fit,
        source_schema_hash_current=response.provenance.source_schema_hash_current,
        target_dataset_version_id=response.target_dataset_version_id,
        target_schema_hash=response.target_schema_hash,
        model_manifest_sha256=response.model_manifest_sha256,
        prediction_schema_version=REGRESSION_PREDICTION_SCHEMA_VERSION,
        rows_artifact_schema_version=REGRESSION_PREDICTION_ROWS_SCHEMA_VERSION,
        confidence_level=response.confidence_level,
        missing_policy=response.provenance.missing_policy,
        include_intervals=response.provenance.include_intervals,
        row_limit=response.row_limit,
        row_count_total=response.row_count_total,
        row_count_predicted=response.row_count_predicted,
        row_count_excluded=response.row_count_excluded,
    )
    return json.dumps(
        payload.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _prediction_result_relative_path(prediction_id: str) -> Path:
    return Path("workspaces") / "analyses" / prediction_id / "result.json"


def _prediction_rows_relative_path(prediction_id: str) -> Path:
    return Path("workspaces") / "analyses" / prediction_id / "prediction_rows.jsonl"


def _safe_prediction_rows_path(workspace_root: Path, stored_path: str) -> Path:
    relative_path = Path(stored_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise _prediction_rows_artifact_error("regression_prediction_rows_artifact_path_invalid")
    return workspace_root / relative_path


def _prediction_rows_artifact_error(code: str) -> ApiError:
    return ApiError(
        code=code,
        message="저장된 회귀 예측 행 아티팩트를 안전하게 읽을 수 없습니다.",
        status_code=status.HTTP_409_CONFLICT,
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _remove_file_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return


def _model_source_row_indices(
    *,
    settings: Settings,
    analysis_id: str,
    expected_sha256: str,
) -> set[int] | None:
    record = get_analysis_run_record(settings.workspace_root, analysis_id)
    if record is None:
        raise ApiError(
            code="regression_model_analysis_missing",
            message="회귀모델을 생성한 분석 실행 메타데이터를 찾을 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    try:
        config = json.loads(record.config_json)
    except json.JSONDecodeError as exc:
        raise ApiError(
            code="regression_model_analysis_metadata_invalid",
            message="회귀모델 분석 실행 메타데이터를 읽을 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc
    row_snapshot = config.get("row_snapshot")
    if not isinstance(row_snapshot, dict):
        return None
    path = row_snapshot.get("path")
    sha256 = row_snapshot.get("sha256")
    if not isinstance(path, str) or not isinstance(sha256, str):
        return None
    if expected_sha256 and sha256 != expected_sha256:
        raise ApiError(
            code="regression_model_row_snapshot_mismatch",
            message="회귀모델 row snapshot 메타데이터가 manifest와 일치하지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    payload = _read_json_artifact(
        settings.workspace_root,
        path,
        sha256,
        invalid_code="regression_model_row_snapshot_invalid",
    )
    selection = payload.get("selection")
    if not isinstance(selection, dict) or selection.get("kind") == "all_rows":
        return None
    ranges = selection.get("row_ranges")
    if not isinstance(ranges, list):
        return None
    indices: set[int] = set()
    for item in ranges:
        if not isinstance(item, dict):
            continue
        start = item.get("start")
        end = item.get("end")
        if isinstance(start, int) and isinstance(end, int) and start <= end:
            indices.update(range(start, end + 1))
    return indices


def _read_json_artifact(
    workspace_root: Path,
    stored_path: str,
    expected_sha256: str,
    *,
    invalid_code: str,
) -> dict[str, object]:
    path = _safe_manifest_path(workspace_root, stored_path)
    if not path.exists():
        raise ApiError(
            code=invalid_code,
            message="저장된 회귀모델 보조 artifact를 찾을 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ApiError(
            code=invalid_code,
            message="저장된 회귀모델 보조 artifact가 메타데이터와 일치하지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ApiError(
            code=invalid_code,
            message="저장된 회귀모델 보조 artifact 형식이 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc
    if not isinstance(payload, dict):
        raise ApiError(
            code=invalid_code,
            message="저장된 회귀모델 보조 artifact 형식이 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return payload


def _prediction_column_checks(
    *,
    manifest: dict[str, object],
    source_columns: list[DatasetColumnRecord],
    target_columns: list[DatasetColumnRecord],
    issues: list[RegressionPredictionPreflightIssue],
) -> list[_PredictionColumnCheck]:
    predictors = manifest.get("predictors")
    if not isinstance(predictors, list) or not predictors:
        raise ApiError(
            code="regression_model_manifest_invalid",
            message="저장된 회귀모델 manifest 형식이 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    source_by_id = {column.column_id: column for column in source_columns}
    target_by_id = {column.column_id: column for column in target_columns}
    target_by_display_name: dict[str, list[DatasetColumnRecord]] = {}
    for column in target_columns:
        target_by_display_name.setdefault(column.display_name, []).append(column)

    categorical_levels = _manifest_categorical_levels(manifest)
    checks: list[_PredictionColumnCheck] = []
    for item in predictors:
        if not isinstance(item, dict):
            continue
        predictor_payload = cast(dict[str, object], item)
        source_column_id = predictor_payload.get("column_id")
        display_name = predictor_payload.get("display_name")
        if not isinstance(source_column_id, str) or not isinstance(display_name, str):
            continue
        source_column = source_by_id.get(source_column_id)
        predictor_kind: Literal["numeric", "categorical"] = (
            "numeric" if _is_manifest_numeric_predictor(predictor_payload) else "categorical"
        )
        target_column = target_by_id.get(source_column_id)
        match_type: Literal["column_id", "display_name", "missing", "ambiguous"] = "column_id"
        status_value: Literal["ok", "warning", "error"] = "ok"
        if target_column is None:
            display_matches = target_by_display_name.get(display_name, [])
            if len(display_matches) == 1:
                target_column = display_matches[0]
                match_type = "display_name"
                status_value = "warning"
                issues.append(
                    RegressionPredictionPreflightIssue(
                        code="prediction_column_matched_by_display_name",
                        severity="warning",
                        message="대상 컬럼 ID가 달라 display name으로 매핑했습니다.",
                        source_column_id=source_column_id,
                        target_column_id=target_column.column_id,
                        display_name=display_name,
                    ),
                )
            elif len(display_matches) > 1:
                match_type = "ambiguous"
                status_value = "error"
                issues.append(
                    RegressionPredictionPreflightIssue(
                        code="prediction_column_display_name_ambiguous",
                        severity="error",
                        message="대상 데이터셋에 같은 display name 컬럼이 여러 개 있습니다.",
                        source_column_id=source_column_id,
                        display_name=display_name,
                    ),
                )
            else:
                match_type = "missing"
                status_value = "error"
                issues.append(
                    RegressionPredictionPreflightIssue(
                        code="prediction_required_column_missing",
                        severity="error",
                        message="모델 예측에 필요한 컬럼을 대상 데이터셋에서 찾을 수 없습니다.",
                        source_column_id=source_column_id,
                        display_name=display_name,
                    ),
                )

        if target_column is not None and not _target_type_compatible(predictor_kind, target_column):
            status_value = "error"
            issues.append(
                RegressionPredictionPreflightIssue(
                    code="prediction_column_type_incompatible",
                    severity="error",
                    message="대상 컬럼의 타입 또는 측정수준이 모델 predictor와 호환되지 않습니다.",
                    source_column_id=source_column_id,
                    target_column_id=target_column.column_id,
                    display_name=display_name,
                ),
            )

        checks.append(
            _PredictionColumnCheck(
                source_column_id=source_column_id,
                display_name=display_name,
                predictor_kind=predictor_kind,
                target_column=target_column,
                match_type=match_type,
                status=status_value,
                training_levels=categorical_levels.get(source_column_id),
            ),
        )
        if source_column is None:
            issues.append(
                RegressionPredictionPreflightIssue(
                    code="prediction_source_column_metadata_missing",
                    severity="warning",
                    message="모델 source dataset의 컬럼 메타데이터를 찾을 수 없습니다.",
                    source_column_id=source_column_id,
                    display_name=display_name,
                ),
            )
    return checks


def _manifest_categorical_levels(manifest: dict[str, object]) -> dict[str, set[str]]:
    model_specification = manifest.get("model_specification")
    if not isinstance(model_specification, dict):
        return {}
    terms = model_specification.get("terms")
    if not isinstance(terms, list):
        return {}
    levels_by_column_id: dict[str, set[str]] = {}
    for term in terms:
        if not isinstance(term, dict) or term.get("kind") != "categorical_main_effect":
            continue
        column_id = term.get("column_id")
        levels = term.get("levels")
        if not isinstance(column_id, str) or not isinstance(levels, list):
            continue
        levels_by_column_id[column_id] = {str(level) for level in levels if isinstance(level, str)}
    return levels_by_column_id


def _is_manifest_numeric_predictor(payload: dict[str, object]) -> bool:
    return (
        payload.get("data_type") in {"integer", "decimal"}
        and payload.get("measurement_level") not in {"nominal", "binary", "ordinal"}
        and payload.get("role") != "factor"
    )


def _target_type_compatible(predictor_kind: str, column: DatasetColumnRecord) -> bool:
    if predictor_kind == "numeric":
        return (
            column.data_type in {"integer", "decimal"}
            and column.measurement_level not in {"nominal", "binary", "ordinal"}
            and column.role != "factor"
        )
    return column.data_type != "datetime" and (
        column.data_type in {"text", "boolean"}
        or column.measurement_level in {"nominal", "binary", "ordinal"}
        or column.role == "factor"
    )


def _fill_training_ranges(
    *,
    checks: list[_PredictionColumnCheck],
    source_context: DatasetRowsContext,
    source_row_indices: set[int] | None,
) -> None:
    numeric_checks = [
        check for check in checks if check.predictor_kind == "numeric" and check.status != "error"
    ]
    if not numeric_checks:
        return
    source_columns_by_id = {column.column_id: column for column in source_context.columns}
    for row_index, row in enumerate(iter_dataset_rows(source_context)):
        if source_row_indices is not None and row_index not in source_row_indices:
            continue
        for check in numeric_checks:
            source_column = source_columns_by_id.get(check.source_column_id)
            if source_column is None:
                continue
            parsed = _parse_numeric_cell(
                row[source_column.column_index] if source_column.column_index < len(row) else None,
                decimal=source_context.parsing.decimal,
                thousands=source_context.parsing.thousands,
            )
            if parsed is None:
                continue
            if check.training_min is None or parsed < check.training_min:
                check.training_min = parsed
            if check.training_max is None or parsed > check.training_max:
                check.training_max = parsed


def _scan_target_rows(
    *,
    checks: list[_PredictionColumnCheck],
    target_context: DatasetRowsContext,
) -> int:
    usable_rows = 0
    usable_checks = [
        check for check in checks if check.target_column is not None and check.status != "error"
    ]
    for row in iter_dataset_rows(target_context):
        row_usable = bool(usable_checks)
        for check in usable_checks:
            assert check.target_column is not None
            raw_value = (
                row[check.target_column.column_index]
                if check.target_column.column_index < len(row)
                else None
            )
            if check.predictor_kind == "numeric":
                parsed = _parse_numeric_cell(
                    raw_value,
                    decimal=target_context.parsing.decimal,
                    thousands=target_context.parsing.thousands,
                )
                if raw_value is None or (isinstance(raw_value, str) and raw_value.strip() == ""):
                    check.n_missing += 1
                    row_usable = False
                    continue
                if parsed is None:
                    check.n_non_numeric += 1
                    row_usable = False
                    continue
                check.n_valid += 1
                if check.training_min is not None and parsed < check.training_min:
                    check.n_below_training_range += 1
                if check.training_max is not None and parsed > check.training_max:
                    check.n_above_training_range += 1
                continue

            if raw_value is None or raw_value.strip() == "":
                check.n_missing += 1
                row_usable = False
                continue
            value = raw_value.strip()
            check.n_valid += 1
            if check.training_levels is not None and value not in check.training_levels:
                check.n_unseen_level += 1
                row_usable = False
        if row_usable:
            usable_rows += 1
    return usable_rows


def _parse_numeric_cell(
    value: str | None,
    *,
    decimal: str,
    thousands: str | None,
) -> float | None:
    if value is None or value.strip() == "":
        return None
    normalized = value.strip()
    if thousands is not None:
        normalized = normalized.replace(thousands, "")
    if decimal != ".":
        normalized = normalized.replace(decimal, ".")
    try:
        parsed = Decimal(normalized)
    except InvalidOperation:
        return None
    if not parsed.is_finite():
        return None
    as_float = float(parsed)
    if not isfinite(as_float):
        return None
    return as_float


def _append_scan_issues(
    checks: list[_PredictionColumnCheck],
    issues: list[RegressionPredictionPreflightIssue],
) -> None:
    for check in checks:
        target_column_id = (
            check.target_column.column_id if check.target_column is not None else None
        )
        if check.n_missing > 0:
            issues.append(
                RegressionPredictionPreflightIssue(
                    code="prediction_missing_values_detected",
                    severity="warning",
                    message="대상 predictor 컬럼에 결측값이 있어 일부 행은 예측에서 제외됩니다.",
                    source_column_id=check.source_column_id,
                    target_column_id=target_column_id,
                    display_name=check.display_name,
                    count=check.n_missing,
                ),
            )
        if check.n_non_numeric > 0:
            issues.append(
                RegressionPredictionPreflightIssue(
                    code="prediction_non_numeric_values_detected",
                    severity="warning",
                    message="숫자형 predictor 컬럼에 숫자로 해석할 수 없는 값이 있습니다.",
                    source_column_id=check.source_column_id,
                    target_column_id=target_column_id,
                    display_name=check.display_name,
                    count=check.n_non_numeric,
                ),
            )
        outside_count = check.n_below_training_range + check.n_above_training_range
        if outside_count > 0:
            issues.append(
                RegressionPredictionPreflightIssue(
                    code="prediction_extrapolation_risk",
                    severity="warning",
                    message="대상 predictor 값 일부가 모델 학습 범위 밖에 있습니다.",
                    source_column_id=check.source_column_id,
                    target_column_id=target_column_id,
                    display_name=check.display_name,
                    count=outside_count,
                ),
            )
        if check.n_unseen_level > 0:
            issues.append(
                RegressionPredictionPreflightIssue(
                    code="prediction_unseen_categorical_levels",
                    severity="warning",
                    message="대상 categorical predictor에 학습 시점에 없던 수준이 있습니다.",
                    source_column_id=check.source_column_id,
                    target_column_id=target_column_id,
                    display_name=check.display_name,
                    count=check.n_unseen_level,
                ),
            )


def _mapping_payload(check: _PredictionColumnCheck) -> RegressionPredictionColumnMapping:
    return RegressionPredictionColumnMapping(
        source_column_id=check.source_column_id,
        display_name=check.display_name,
        predictor_kind="numeric" if check.predictor_kind == "numeric" else "categorical",
        target_column_id=None if check.target_column is None else check.target_column.column_id,
        match_type=check.match_type,
        status=check.status,
    )


def _is_numeric_check(check: _PredictionColumnCheck) -> bool:
    return check.predictor_kind == "numeric" and check.target_column is not None


def _is_categorical_check(check: _PredictionColumnCheck) -> bool:
    return check.predictor_kind == "categorical" and check.target_column is not None


def _numeric_check_payload(check: _PredictionColumnCheck) -> RegressionPredictionNumericCheck:
    assert check.target_column is not None
    return RegressionPredictionNumericCheck(
        source_column_id=check.source_column_id,
        target_column_id=check.target_column.column_id,
        display_name=check.display_name,
        training_min=check.training_min,
        training_max=check.training_max,
        n_valid=check.n_valid,
        n_missing=check.n_missing,
        n_non_numeric=check.n_non_numeric,
        n_below_training_range=check.n_below_training_range,
        n_above_training_range=check.n_above_training_range,
    )


def _categorical_check_payload(
    check: _PredictionColumnCheck,
) -> RegressionPredictionCategoricalCheck:
    assert check.target_column is not None
    return RegressionPredictionCategoricalCheck(
        source_column_id=check.source_column_id,
        target_column_id=check.target_column.column_id,
        display_name=check.display_name,
        training_level_count=0 if check.training_levels is None else len(check.training_levels),
        n_valid=check.n_valid,
        n_missing=check.n_missing,
        n_unseen_level=check.n_unseen_level,
    )


def _safe_manifest_path(workspace_root: Path, stored_path: str) -> Path:
    relative_path = Path(stored_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ApiError(
            code="regression_model_manifest_path_invalid",
            message="저장된 회귀모델 manifest 메타데이터가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return workspace_root / relative_path
