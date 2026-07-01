import hashlib
import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from math import isfinite
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import status
from pydantic import ValidationError

from app.analyses.registry import get_analysis_method
from app.api.v1.schemas.analyses import (
    AnalysisFilterSnapshot,
    AnalysisProvenance,
    AnalysisResultEnvelope,
    AnalysisRunRequest,
    AnalysisRunState,
    AnalysisRunStatusResponse,
    AnalysisWarning,
    MethodAvailability,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.dataset_rows import (
    DatasetRowsContext,
    get_dataset_rows_context,
    iter_dataset_rows,
)
from app.statistics.chi_square_association import (
    ChiSquareAssociationColumn,
    ChiSquareAssociationError,
    calculate_chi_square_association,
)
from app.statistics.descriptive import DescriptiveColumn, describe_numeric_columns
from app.statistics.equal_variances import (
    EqualVarianceGroupColumn,
    EqualVarianceResponseColumn,
    calculate_equal_variances,
)
from app.statistics.equivalence_tost import (
    EquivalenceTostColumn,
    EquivalenceTostError,
    calculate_equivalence_tost,
)
from app.statistics.graphical_summary import (
    GraphicalSummaryColumn,
    summarize_numeric_graphics,
)
from app.statistics.kruskal_wallis import (
    KruskalWallisError,
    KruskalWallisGroupColumn,
    KruskalWallisResponseColumn,
    calculate_kruskal_wallis,
)
from app.statistics.linear_model import (
    LinearModelColumn,
    LinearModelError,
    calculate_linear_model,
)
from app.statistics.mann_whitney import (
    MannWhitneyError,
    MannWhitneyGroupColumn,
    MannWhitneyResponseColumn,
    calculate_mann_whitney,
)
from app.statistics.normality import NormalityColumn, calculate_normality
from app.statistics.one_proportion import (
    OneProportionColumn,
    OneProportionError,
    calculate_one_proportion,
)
from app.statistics.one_sample_t import (
    OneSampleTColumn,
    OneSampleTError,
    calculate_one_sample_t,
)
from app.statistics.one_sample_wilcoxon import (
    OneSampleWilcoxonColumn,
    OneSampleWilcoxonError,
    calculate_one_sample_wilcoxon,
)
from app.statistics.one_way_anova import (
    OneWayAnovaError,
    OneWayAnovaGroupColumn,
    OneWayAnovaResponseColumn,
    calculate_one_way_anova,
)
from app.statistics.paired_t import (
    PairedTColumn,
    PairedTError,
    calculate_paired_t,
)
from app.statistics.pearson import (
    PearsonCorrelationColumn,
    PearsonCorrelationError,
    calculate_pearson_correlation,
)
from app.statistics.two_proportion import (
    TwoProportionError,
    TwoProportionGroupColumn,
    TwoProportionResponseColumn,
    calculate_two_proportion,
)
from app.statistics.two_sample_t import (
    TwoSampleTError,
    TwoSampleTGroupColumn,
    TwoSampleTResponseColumn,
    calculate_two_sample_t,
)
from app.statistics.xy_correlation import (
    XyCorrelationColumn,
    XyCorrelationError,
    calculate_xy_correlation,
)
from app.storage.atomic import atomic_write_bytes
from app.storage.metadata import (
    AnalysisArtifactRecord,
    AnalysisRunRecord,
    DatasetColumnRecord,
    RegressionModelRecord,
    count_analysis_artifact_records,
    get_analysis_run_record,
    insert_analysis_run_record_with_artifacts,
    insert_analysis_run_record_with_artifacts_and_regression_model,
    update_analysis_run_status_record,
)

APP_VERSION = "0.1.0"
CONFIG_SCHEMA_VERSION = 2
ROW_SNAPSHOT_SCHEMA_VERSION = 1
ROW_SNAPSHOT_ARTIFACT_KIND = "analysis_row_snapshot"
ROW_SNAPSHOT_MEDIA_TYPE = "application/json"
REGRESSION_MODEL_MANIFEST_SCHEMA_VERSION = 2
REGRESSION_MODEL_ARTIFACT_KIND = "regression_model_manifest"
REGRESSION_MODEL_MEDIA_TYPE = "application/json"
MAX_DESCRIPTIVE_COLUMNS = 100
MAX_GRAPHICAL_SUMMARY_COLUMNS = 20
MAX_GRAPHICAL_POINT_LIMIT = 5000
MAX_GRAPHICAL_HISTOGRAM_BINS = 200
MAX_NORMALITY_COLUMNS = 20
MAX_NORMALITY_QQ_POINT_LIMIT = 5000
MAX_XY_CORRELATION_X_COLUMNS = 20
MAX_XY_CORRELATION_Y_COLUMNS = 20
MAX_LINEAR_MODEL_PREDICTORS = 20
MAX_FILTER_CONDITIONS = 20
MAX_FILTER_STRING_LENGTH = 200
NUMERIC_DATA_TYPES = {"integer", "decimal"}
FILTER_OPERATORS = {
    "is_missing",
    "is_not_missing",
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
}
NUMERIC_FILTER_OPERATORS = {"gt", "gte", "lt", "lte"}
CANCELLABLE_STATES = {AnalysisRunState.QUEUED.value, AnalysisRunState.RUNNING.value}
TERMINAL_STATES = {
    AnalysisRunState.SUCCEEDED.value,
    AnalysisRunState.FAILED.value,
    AnalysisRunState.CANCELLED.value,
}


@dataclass(frozen=True)
class _RowSnapshotArtifact:
    record: AnalysisArtifactRecord
    relative_path: Path
    payload: dict[str, Any]
    included_row_indices: tuple[int, ...] | None


@dataclass(frozen=True)
class _FilterCondition:
    column: DatasetColumnRecord
    operator: str
    value: object | None = None


def create_analysis_run(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    method = get_analysis_method(request.method_id)
    if method is None:
        raise ApiError(
            code="analysis_method_not_found",
            message="요청한 분석 메서드를 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if method.method_version != request.method_version:
        raise ApiError(
            code="analysis_method_version_mismatch",
            message="요청한 분석 메서드 버전이 현재 registry와 일치하지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    if method.availability != MethodAvailability.AVAILABLE:
        raise ApiError(
            code="analysis_method_not_available",
            message="이 분석 메서드는 아직 실행할 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
            developer_detail=method.availability.value,
        )

    if request.method_id == "eda.descriptive":
        return _run_descriptive_analysis(settings, request)
    if request.method_id == "eda.graphical_summary":
        return _run_graphical_summary_analysis(settings, request)
    if request.method_id == "eda.normality":
        return _run_normality_analysis(settings, request)
    if request.method_id == "eda.equal_variances":
        return _run_equal_variances_analysis(settings, request)
    if request.method_id == "hypothesis.one_sample_t":
        return _run_one_sample_t_analysis(settings, request)
    if request.method_id == "hypothesis.paired_t":
        return _run_paired_t_analysis(settings, request)
    if request.method_id == "hypothesis.one_sample_wilcoxon":
        return _run_one_sample_wilcoxon_analysis(settings, request)
    if request.method_id == "hypothesis.two_sample_t":
        return _run_two_sample_t_analysis(settings, request)
    if request.method_id == "hypothesis.mann_whitney":
        return _run_mann_whitney_analysis(settings, request)
    if request.method_id == "hypothesis.kruskal_wallis":
        return _run_kruskal_wallis_analysis(settings, request)
    if request.method_id == "hypothesis.one_way_anova":
        return _run_one_way_anova_analysis(settings, request)
    if request.method_id == "hypothesis.equivalence_tost":
        return _run_equivalence_tost_analysis(settings, request)
    if request.method_id == "categorical.one_proportion":
        return _run_one_proportion_analysis(settings, request)
    if request.method_id == "categorical.two_proportion":
        return _run_two_proportion_analysis(settings, request)
    if request.method_id == "categorical.chi_square_association":
        return _run_chi_square_association_analysis(settings, request)
    if request.method_id == "regression.pearson":
        return _run_pearson_analysis(settings, request)
    if request.method_id == "regression.xy_correlation":
        return _run_xy_correlation_analysis(settings, request)
    if request.method_id == "regression.linear_model":
        return _run_linear_model_analysis(settings, request)

    raise ApiError(
        code="analysis_method_not_available",
        message="이 분석 메서드는 아직 실행할 수 없습니다.",
        status_code=status.HTTP_409_CONFLICT,
        developer_detail=method.availability.value,
    )


def get_analysis_run_status(
    workspace_root: Path,
    analysis_id: UUID,
) -> AnalysisRunStatusResponse:
    record = get_analysis_run_record(workspace_root, str(analysis_id))
    if record is None:
        raise ApiError(
            code="analysis_run_not_found",
            message="요청한 분석 실행을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return _to_response(workspace_root, record)


def get_analysis_run_result(
    settings: Settings,
    analysis_id: UUID,
) -> AnalysisResultEnvelope:
    record = get_analysis_run_record(settings.workspace_root, str(analysis_id))
    if record is None:
        raise ApiError(
            code="analysis_run_not_found",
            message="요청한 분석 실행을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if record.result_path is None or record.result_sha256 is None:
        raise ApiError(
            code="analysis_result_not_available",
            message="저장된 분석 결과가 아직 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    result_path = _safe_result_path(settings.workspace_root, record.result_path)
    if not result_path.exists():
        raise ApiError(
            code="analysis_result_file_missing",
            message="저장된 분석 결과 파일을 찾을 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    result_bytes = result_path.read_bytes()
    if hashlib.sha256(result_bytes).hexdigest() != record.result_sha256:
        raise ApiError(
            code="analysis_result_checksum_mismatch",
            message="저장된 분석 결과 파일이 메타데이터와 일치하지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    try:
        return AnalysisResultEnvelope.model_validate_json(result_bytes)
    except ValidationError as exc:
        raise ApiError(
            code="analysis_result_envelope_invalid",
            message="저장된 분석 결과 형식이 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc


def request_analysis_run_cancellation(
    workspace_root: Path,
    analysis_id: UUID,
) -> AnalysisRunStatusResponse:
    record = get_analysis_run_record(workspace_root, str(analysis_id))
    if record is None:
        raise ApiError(
            code="analysis_run_not_found",
            message="요청한 분석 실행을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if record.status in TERMINAL_STATES:
        raise ApiError(
            code="analysis_run_not_cancellable",
            message="이미 종료된 분석 실행은 취소 요청할 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
            developer_detail=record.status,
        )

    if record.status in CANCELLABLE_STATES:
        updated = update_analysis_run_status_record(
            workspace_root=workspace_root,
            analysis_id=str(analysis_id),
            status=AnalysisRunState.CANCEL_REQUESTED.value,
            updated_at=_utc_now(),
        )
        if updated is not None:
            record = updated

    return _to_response(workspace_root, record)


def _run_descriptive_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="기술통계 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    selected_columns = _selected_descriptive_columns(context, request.options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    result_path: Path | None = None

    try:
        result = describe_numeric_columns(
            _iter_rows_for_snapshot(context, row_snapshot),
            selected_columns,
            decimal=context.parsing.decimal,
            thousands=context.parsing.thousands,
        )
        warnings = _descriptive_warnings(result)
        provenance = AnalysisProvenance(
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            source_schema_hash=context.version.schema_hash,
            filter_snapshot_sha256=str(row_snapshot.payload["filter_snapshot_sha256"]),
            row_snapshot_sha256=row_snapshot.record.sha256,
            row_count_total=context.version.row_count,
            row_count_included=int(row_snapshot.payload["selection"]["row_count_included"]),
            app_version=APP_VERSION,
        )
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=provenance,
            result=result,
        )

        result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = _analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=_analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=[row_snapshot.record],
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        if result_path is not None:
            _remove_file_if_exists(result_path)
        raise
    return envelope


def _selected_descriptive_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> list[DescriptiveColumn]:
    column_ids = options.get("column_ids")
    if not isinstance(column_ids, list) or not column_ids:
        raise ApiError(
            code="descriptive_columns_required",
            message="기술통계를 계산할 컬럼을 하나 이상 선택해야 합니다.",
        )
    if len(column_ids) > MAX_DESCRIPTIVE_COLUMNS:
        raise ApiError(
            code="too_many_descriptive_columns",
            message="한 번에 요청한 기술통계 컬럼 수가 허용 범위를 초과했습니다.",
        )
    if any(not isinstance(column_id, str) or not column_id for column_id in column_ids):
        raise ApiError(
            code="invalid_descriptive_columns",
            message="기술통계 컬럼 ID 목록이 올바르지 않습니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    seen: set[str] = set()
    selected: list[DescriptiveColumn] = []
    for column_id in column_ids:
        if column_id in seen:
            raise ApiError(
                code="duplicate_descriptive_column",
                message="기술통계 컬럼 ID가 중복되었습니다.",
            )
        seen.add(column_id)

        column = columns_by_id.get(column_id)
        if column is None:
            raise ApiError(
                code="descriptive_column_not_found",
                message="요청한 기술통계 컬럼을 찾을 수 없습니다.",
            )
        _validate_descriptive_column(column)
        selected.append(
            DescriptiveColumn(
                column_id=column.column_id,
                column_index=column.column_index,
                display_name=column.display_name,
                data_type=column.data_type,
                measurement_level=column.measurement_level,
                role=column.role,
                unit=column.unit,
            ),
        )
    return selected


def _validate_descriptive_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="descriptive_column_is_id",
            message="ID 컬럼은 기술통계 계산 대상에서 제외해야 합니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="descriptive_column_not_numeric",
            message="기술통계는 현재 숫자형 컬럼만 지원합니다.",
        )


def _descriptive_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    columns = result.get("columns")
    if not isinstance(columns, list):
        return warnings

    for column in columns:
        if not isinstance(column, dict):
            continue
        column_warnings = column.get("warnings")
        display_name = column.get("display_name")
        if not isinstance(column_warnings, list) or not isinstance(display_name, str):
            continue
        if "non_numeric_values_excluded" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="non_numeric_values_excluded",
                    severity="warning",
                    message=f"{display_name}: 숫자로 해석할 수 없는 값은 제외했습니다.",
                ),
            )
        if "no_numeric_values" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="no_numeric_values",
                    severity="warning",
                    message=f"{display_name}: 사용할 수 있는 숫자 값이 없습니다.",
                ),
            )
        if "constant_column" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="constant_column",
                    severity="info",
                    message=f"{display_name}: 모든 사용 값이 동일합니다.",
                ),
            )
    return warnings


def _run_graphical_summary_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="그래프 요약 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    selected_columns = _selected_graphical_summary_columns(context, request.options)
    histogram_bin_count = _graphical_histogram_bin_count(request.options)
    point_limit = _graphical_point_limit(request.options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    result_path: Path | None = None

    try:
        result = summarize_numeric_graphics(
            _iter_rows_for_snapshot(context, row_snapshot),
            selected_columns,
            decimal=context.parsing.decimal,
            thousands=context.parsing.thousands,
            histogram_bin_count=histogram_bin_count,
            point_limit=point_limit,
        )
        warnings = _graphical_summary_warnings(result)
        provenance = AnalysisProvenance(
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            source_schema_hash=context.version.schema_hash,
            filter_snapshot_sha256=str(row_snapshot.payload["filter_snapshot_sha256"]),
            row_snapshot_sha256=row_snapshot.record.sha256,
            row_count_total=context.version.row_count,
            row_count_included=int(row_snapshot.payload["selection"]["row_count_included"]),
            app_version=APP_VERSION,
        )
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=provenance,
            result=result,
        )

        result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = _analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=_analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=[row_snapshot.record],
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        if result_path is not None:
            _remove_file_if_exists(result_path)
        raise
    return envelope


def _selected_graphical_summary_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> list[GraphicalSummaryColumn]:
    column_ids = options.get("column_ids")
    if not isinstance(column_ids, list) or not column_ids:
        raise ApiError(
            code="graphical_summary_columns_required",
            message="그래프 요약을 계산할 컬럼을 하나 이상 선택해야 합니다.",
        )
    if len(column_ids) > MAX_GRAPHICAL_SUMMARY_COLUMNS:
        raise ApiError(
            code="too_many_graphical_summary_columns",
            message="한 번에 요청한 그래프 요약 컬럼 수가 허용 범위를 초과했습니다.",
        )
    if any(not isinstance(column_id, str) or not column_id for column_id in column_ids):
        raise ApiError(
            code="invalid_graphical_summary_columns",
            message="그래프 요약 컬럼 ID 목록이 올바르지 않습니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    seen: set[str] = set()
    selected: list[GraphicalSummaryColumn] = []
    for column_id in column_ids:
        if column_id in seen:
            raise ApiError(
                code="duplicate_graphical_summary_column",
                message="그래프 요약 컬럼 ID가 중복되었습니다.",
            )
        seen.add(column_id)

        column = columns_by_id.get(column_id)
        if column is None:
            raise ApiError(
                code="graphical_summary_column_not_found",
                message="요청한 그래프 요약 컬럼을 찾을 수 없습니다.",
            )
        _validate_graphical_summary_column(column)
        selected.append(
            GraphicalSummaryColumn(
                column_id=column.column_id,
                column_index=column.column_index,
                display_name=column.display_name,
                data_type=column.data_type,
                measurement_level=column.measurement_level,
                role=column.role,
                unit=column.unit,
            ),
        )
    return selected


def _validate_graphical_summary_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="graphical_summary_column_is_id",
            message="ID 컬럼은 그래프 요약 계산 대상에서 제외해야 합니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="graphical_summary_column_not_numeric",
            message="그래프 요약은 현재 숫자형 컬럼만 지원합니다.",
        )


def _graphical_histogram_bin_count(options: dict[str, Any]) -> int | None:
    raw_value = options.get("histogram_bin_count")
    if raw_value is None:
        return None
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise ApiError(
            code="invalid_histogram_bin_count",
            message="히스토그램 bin 수가 올바르지 않습니다.",
        )
    if raw_value < 1 or raw_value > MAX_GRAPHICAL_HISTOGRAM_BINS:
        raise ApiError(
            code="invalid_histogram_bin_count",
            message="히스토그램 bin 수가 허용 범위를 벗어났습니다.",
        )
    return raw_value


def _graphical_point_limit(options: dict[str, Any]) -> int:
    raw_value = options.get("point_limit", 1000)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise ApiError(
            code="invalid_graphical_point_limit",
            message="그래프 점 제한 값이 올바르지 않습니다.",
        )
    if raw_value < 10 or raw_value > MAX_GRAPHICAL_POINT_LIMIT:
        raise ApiError(
            code="invalid_graphical_point_limit",
            message="그래프 점 제한 값이 허용 범위를 벗어났습니다.",
        )
    return raw_value


def _graphical_summary_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    columns = result.get("columns")
    if not isinstance(columns, list):
        return warnings

    for column in columns:
        if not isinstance(column, dict):
            continue
        column_warnings = column.get("warnings")
        display_name = column.get("display_name")
        if not isinstance(column_warnings, list) or not isinstance(display_name, str):
            continue
        if "non_numeric_values_excluded" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="non_numeric_values_excluded",
                    severity="warning",
                    message=f"{display_name}: 숫자로 해석할 수 없는 값은 제외했습니다.",
                ),
            )
        if "no_numeric_values" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="no_numeric_values",
                    severity="warning",
                    message=f"{display_name}: 사용할 수 있는 숫자 값이 없습니다.",
                ),
            )
        if "constant_column" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="constant_column",
                    severity="info",
                    message=f"{display_name}: 모든 사용 값이 동일합니다.",
                ),
            )
        if "graphical_points_truncated" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="graphical_points_truncated",
                    severity="info",
                    message=f"{display_name}: Q-Q/ECDF 점은 결정적 방식으로 제한했습니다.",
                ),
            )
    return warnings


def _run_normality_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="정규성 검정 실행에는 데이터셋 버전이 필요합니다.",
        )

    _reject_normality_grouping(request)
    context = get_dataset_rows_context(settings, request.dataset_version_id)
    selected_columns = _selected_normality_columns(context, request.options)
    alpha = _normality_alpha(request.options)
    include_qq_points = _normality_include_qq_points(request.options)
    qq_point_limit = _normality_qq_point_limit(request.options)
    _normality_missing_policy(request.options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    result_path: Path | None = None

    try:
        result = calculate_normality(
            _iter_rows_for_snapshot(context, row_snapshot),
            selected_columns,
            decimal=context.parsing.decimal,
            thousands=context.parsing.thousands,
            alpha=alpha,
            include_qq_points=include_qq_points,
            qq_point_limit=qq_point_limit,
        )
        warnings = _normality_warnings(result)
        provenance = AnalysisProvenance(
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            source_schema_hash=context.version.schema_hash,
            filter_snapshot_sha256=str(row_snapshot.payload["filter_snapshot_sha256"]),
            row_snapshot_sha256=row_snapshot.record.sha256,
            row_count_total=context.version.row_count,
            row_count_included=int(row_snapshot.payload["selection"]["row_count_included"]),
            app_version=APP_VERSION,
        )
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=provenance,
            result=result,
        )

        result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = _analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=_analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=[row_snapshot.record],
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        if result_path is not None:
            _remove_file_if_exists(result_path)
        raise
    return envelope


def _run_equal_variances_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="등분산 검정 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column, group_column = _selected_equal_variances_columns(
        context,
        request.options,
    )
    alpha = _equal_variances_alpha(request.options)
    _equal_variances_missing_policy(request.options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    result_path: Path | None = None

    try:
        result = calculate_equal_variances(
            _iter_rows_for_snapshot(context, row_snapshot),
            response_column,
            group_column,
            decimal=context.parsing.decimal,
            thousands=context.parsing.thousands,
            alpha=alpha,
        )
        warnings = _equal_variances_warnings(result)
        provenance = AnalysisProvenance(
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            source_schema_hash=context.version.schema_hash,
            filter_snapshot_sha256=str(row_snapshot.payload["filter_snapshot_sha256"]),
            row_snapshot_sha256=row_snapshot.record.sha256,
            row_count_total=context.version.row_count,
            row_count_included=int(row_snapshot.payload["selection"]["row_count_included"]),
            app_version=APP_VERSION,
        )
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=provenance,
            result=result,
        )

        result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = _analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=_analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=[row_snapshot.record],
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        if result_path is not None:
            _remove_file_if_exists(result_path)
        raise
    return envelope


def _selected_equal_variances_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[EqualVarianceResponseColumn, EqualVarianceGroupColumn]:
    response_column_id = options.get("response_column_id")
    group_column_id = options.get("group_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="equal_variances_response_required",
            message="등분산 검정 반응 컬럼을 선택해야 합니다.",
        )
    if not isinstance(group_column_id, str) or not group_column_id:
        raise ApiError(
            code="equal_variances_group_required",
            message="등분산 검정 그룹 컬럼을 선택해야 합니다.",
        )
    if response_column_id == group_column_id:
        raise ApiError(
            code="equal_variances_same_response_and_group",
            message="반응 컬럼과 그룹 컬럼은 서로 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_column = columns_by_id.get(response_column_id)
    if response_column is None:
        raise ApiError(
            code="equal_variances_response_column_not_found",
            message="요청한 등분산 검정 반응 컬럼을 찾을 수 없습니다.",
        )
    group_column = columns_by_id.get(group_column_id)
    if group_column is None:
        raise ApiError(
            code="equal_variances_group_column_not_found",
            message="요청한 등분산 검정 그룹 컬럼을 찾을 수 없습니다.",
        )

    _validate_equal_variances_response_column(response_column)
    _validate_equal_variances_group_column(group_column)
    return (
        EqualVarianceResponseColumn(
            column_id=response_column.column_id,
            column_index=response_column.column_index,
            display_name=response_column.display_name,
            data_type=response_column.data_type,
            measurement_level=response_column.measurement_level,
            role=response_column.role,
            unit=response_column.unit,
        ),
        EqualVarianceGroupColumn(
            column_id=group_column.column_id,
            column_index=group_column.column_index,
            display_name=group_column.display_name,
            data_type=group_column.data_type,
            measurement_level=group_column.measurement_level,
            role=group_column.role,
            unit=group_column.unit,
        ),
    )


def _validate_equal_variances_response_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="equal_variances_response_column_is_id",
            message="ID 컬럼은 등분산 검정 반응 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="equal_variances_response_column_not_numeric",
            message="등분산 검정 반응 변수는 현재 숫자형 컬럼만 지원합니다.",
        )


def _validate_equal_variances_group_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="equal_variances_group_column_is_id",
            message="ID 컬럼은 등분산 검정 그룹 변수로 사용할 수 없습니다.",
        )


def _equal_variances_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_equal_variances_alpha",
            message="등분산 검정 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0:
        raise ApiError(
            code="invalid_equal_variances_alpha",
            message="등분산 검정 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _equal_variances_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="equal_variances_missing_policy_unsupported",
            message="등분산 검정은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _equal_variances_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings = [
        AnalysisWarning(
            code="equal_variances_not_method_switch",
            severity="info",
            message=(
                "등분산 검정 결과만으로 후속 pooled/Welch 또는 ANOVA 방식을 "
                "자동 전환하지 않습니다."
            ),
        ),
    ]
    result_warning_codes = result.get("warnings")
    if isinstance(result_warning_codes, list):
        if "missing_values_excluded" in result_warning_codes:
            warnings.append(
                AnalysisWarning(
                    code="missing_values_excluded",
                    severity="warning",
                    message="반응 또는 그룹 결측 행은 complete-case 정책으로 제외했습니다.",
                ),
            )
        if "non_numeric_values_excluded" in result_warning_codes:
            warnings.append(
                AnalysisWarning(
                    code="non_numeric_values_excluded",
                    severity="warning",
                    message="반응 값 중 숫자로 해석할 수 없는 값은 제외했습니다.",
                ),
            )
        if "equal_variances_insufficient_groups" in result_warning_codes:
            warnings.append(
                AnalysisWarning(
                    code="equal_variances_insufficient_groups",
                    severity="warning",
                    message="등분산 검정에는 사용 가능한 그룹이 2개 이상 필요합니다.",
                ),
            )
        if "equal_variances_group_n_too_small" in result_warning_codes:
            warnings.append(
                AnalysisWarning(
                    code="equal_variances_group_n_too_small",
                    severity="warning",
                    message="각 그룹에는 최소 2개 사용 값이 필요합니다.",
                ),
            )
        if "constant_response" in result_warning_codes:
            warnings.append(
                AnalysisWarning(
                    code="constant_response",
                    severity="warning",
                    message="모든 사용 반응 값이 동일해 등분산 검정을 계산하지 않았습니다.",
                ),
            )
    tests = result.get("tests")
    if not isinstance(tests, list):
        return warnings
    for test in tests:
        if not isinstance(test, dict):
            continue
        test_warnings = test.get("warnings")
        if not isinstance(test_warnings, list):
            continue
        if "equal_variances_statistic_not_finite" in test_warnings:
            warnings.append(
                AnalysisWarning(
                    code="equal_variances_statistic_not_finite",
                    severity="warning",
                    message="등분산 검정 통계량이 유한하지 않아 결과를 계산하지 않았습니다.",
                ),
            )
            break
    return warnings


def _run_one_sample_t_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="1-표본 t-검정 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column = _selected_one_sample_t_column(context, request.options)
    alpha = _one_sample_t_alpha(request.options)
    confidence_level = _one_sample_t_confidence_level(request.options)
    alternative = _one_sample_t_alternative(request.options)
    null_mean = _one_sample_t_null_mean(request.options)
    _one_sample_t_missing_policy(request.options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    result_path: Path | None = None

    try:
        try:
            result = calculate_one_sample_t(
                _iter_rows_for_snapshot(context, row_snapshot),
                response_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                alpha=alpha,
                confidence_level=confidence_level,
                alternative=alternative,
                null_mean=null_mean,
            )
        except OneSampleTError as exc:
            raise _one_sample_t_api_error(exc.code) from exc
        warnings = _one_sample_t_warnings(result)
        provenance = AnalysisProvenance(
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            source_schema_hash=context.version.schema_hash,
            filter_snapshot_sha256=str(row_snapshot.payload["filter_snapshot_sha256"]),
            row_snapshot_sha256=row_snapshot.record.sha256,
            row_count_total=context.version.row_count,
            row_count_included=int(row_snapshot.payload["selection"]["row_count_included"]),
            app_version=APP_VERSION,
        )
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=provenance,
            result=result,
        )

        result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = _analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=_analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=[row_snapshot.record],
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        if result_path is not None:
            _remove_file_if_exists(result_path)
        raise
    return envelope


def _selected_one_sample_t_column(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> OneSampleTColumn:
    response_column_id = options.get("response_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="one_sample_t_response_required",
            message="1-표본 t-검정 반응 컬럼을 선택해야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_column = columns_by_id.get(response_column_id)
    if response_column is None:
        raise ApiError(
            code="one_sample_t_response_column_not_found",
            message="요청한 1-표본 t-검정 반응 컬럼을 찾을 수 없습니다.",
        )

    _validate_one_sample_t_response_column(response_column)
    return OneSampleTColumn(
        column_id=response_column.column_id,
        column_index=response_column.column_index,
        display_name=response_column.display_name,
        data_type=response_column.data_type,
        measurement_level=response_column.measurement_level,
        role=response_column.role,
        unit=response_column.unit,
    )


def _validate_one_sample_t_response_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="one_sample_t_response_column_is_id",
            message="ID 컬럼은 1-표본 t-검정 반응 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="one_sample_t_response_column_not_numeric",
            message="1-표본 t-검정 반응 변수는 현재 숫자형 컬럼만 지원합니다.",
        )


def _one_sample_t_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_one_sample_t_alpha",
            message="1-표본 t-검정 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0:
        raise ApiError(
            code="invalid_one_sample_t_alpha",
            message="1-표본 t-검정 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _one_sample_t_confidence_level(options: dict[str, Any]) -> float:
    raw_value = options.get("confidence_level", 0.95)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_one_sample_t_confidence_level",
            message="1-표본 t-검정 신뢰수준이 올바르지 않습니다.",
        )
    confidence_level = float(raw_value)
    if confidence_level <= 0.0 or confidence_level >= 1.0:
        raise ApiError(
            code="invalid_one_sample_t_confidence_level",
            message="1-표본 t-검정 신뢰수준이 허용 범위를 벗어났습니다.",
        )
    return confidence_level


def _one_sample_t_alternative(options: dict[str, Any]) -> str:
    raw_value = options.get("alternative", "two_sided")
    if raw_value not in {"two_sided", "greater", "less"}:
        raise ApiError(
            code="invalid_one_sample_t_alternative",
            message="1-표본 t-검정 대립가설이 올바르지 않습니다.",
        )
    return str(raw_value)


def _one_sample_t_null_mean(options: dict[str, Any]) -> float:
    raw_value = options.get("null_mean", 0.0)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_one_sample_t_null_mean",
            message="1-표본 t-검정 기준 평균이 올바르지 않습니다.",
        )
    null_mean = float(raw_value)
    if not isfinite(null_mean):
        raise ApiError(
            code="invalid_one_sample_t_null_mean",
            message="1-표본 t-검정 기준 평균이 유한하지 않습니다.",
        )
    return null_mean


def _one_sample_t_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="one_sample_t_missing_policy_unsupported",
            message="1-표본 t-검정은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _one_sample_t_api_error(code: str) -> ApiError:
    messages = {
        "one_sample_t_n_too_small": "1-표본 t-검정에는 최소 2개 사용 값이 필요합니다.",
        "one_sample_t_standard_error_zero": (
            "평균 차이의 표준오차가 0이어서 1-표본 t-검정을 계산할 수 없습니다."
        ),
        "invalid_one_sample_t_alternative": "1-표본 t-검정 대립가설이 올바르지 않습니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "1-표본 t-검정을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _one_sample_t_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "one_sample_t_design_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_sample_t_design_assumption",
                severity="info",
                message="독립성 및 표본 설계는 데이터만으로 자동 검증하지 않습니다.",
            ),
        )
    if "one_sample_t_not_auto_switched" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_sample_t_not_auto_switched",
                severity="info",
                message="정규성 진단 결과로 1-표본 t-검정을 자동 전환하지 않습니다.",
            ),
        )
    if "missing_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="missing_values_excluded",
                severity="warning",
                message="반응 결측 행은 complete-case 정책으로 제외했습니다.",
            ),
        )
    if "non_numeric_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="non_numeric_values_excluded",
                severity="warning",
                message="반응 값 중 숫자로 해석할 수 없는 값은 제외했습니다.",
            ),
        )
    return warnings


def _run_equivalence_tost_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="동등성 검정 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column = _selected_equivalence_tost_column(context, request.options)
    design = _equivalence_tost_design(request.options)
    alpha = _equivalence_tost_alpha(request.options)
    reference_mean = _equivalence_tost_reference_mean(request.options)
    lower_bound = _equivalence_tost_lower_bound(request.options)
    upper_bound = _equivalence_tost_upper_bound(request.options)
    _equivalence_tost_missing_policy(request.options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    result_path: Path | None = None

    try:
        try:
            result = calculate_equivalence_tost(
                _iter_rows_for_snapshot(context, row_snapshot),
                response_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                design=design,
                reference_mean=reference_mean,
                lower_bound=lower_bound,
                upper_bound=upper_bound,
                alpha=alpha,
            )
        except EquivalenceTostError as exc:
            raise _equivalence_tost_api_error(exc.code) from exc
        warnings = _equivalence_tost_warnings(result)
        provenance = AnalysisProvenance(
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            source_schema_hash=context.version.schema_hash,
            filter_snapshot_sha256=str(row_snapshot.payload["filter_snapshot_sha256"]),
            row_snapshot_sha256=row_snapshot.record.sha256,
            row_count_total=context.version.row_count,
            row_count_included=int(row_snapshot.payload["selection"]["row_count_included"]),
            app_version=APP_VERSION,
        )
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=provenance,
            result=result,
        )

        result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = _analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=_analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=[row_snapshot.record],
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        if result_path is not None:
            _remove_file_if_exists(result_path)
        raise
    return envelope


def _selected_equivalence_tost_column(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> EquivalenceTostColumn:
    response_column_id = options.get("response_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="equivalence_tost_response_required",
            message="동등성 검정 반응 컬럼을 선택해야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_column = columns_by_id.get(response_column_id)
    if response_column is None:
        raise ApiError(
            code="equivalence_tost_response_column_not_found",
            message="요청한 동등성 검정 반응 컬럼을 찾을 수 없습니다.",
        )

    _validate_equivalence_tost_response_column(response_column)
    return EquivalenceTostColumn(
        column_id=response_column.column_id,
        column_index=response_column.column_index,
        display_name=response_column.display_name,
        data_type=response_column.data_type,
        measurement_level=response_column.measurement_level,
        role=response_column.role,
        unit=response_column.unit,
    )


def _validate_equivalence_tost_response_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="equivalence_tost_response_column_is_id",
            message="ID 컬럼은 동등성 검정 반응 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="equivalence_tost_response_column_not_numeric",
            message="동등성 검정 반응 변수는 현재 숫자형 컬럼만 지원합니다.",
        )


def _equivalence_tost_design(options: dict[str, Any]) -> str:
    raw_value = options.get("design")
    if raw_value != "one_sample_mean":
        raise ApiError(
            code="equivalence_tost_design_unsupported",
            message="현재 동등성 검정은 1표본 평균 설계만 지원합니다.",
        )
    return str(raw_value)


def _equivalence_tost_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_equivalence_tost_alpha",
            message="동등성 검정 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 0.5:
        raise ApiError(
            code="invalid_equivalence_tost_alpha",
            message="동등성 검정 유의수준은 0보다 크고 0.5보다 작아야 합니다.",
        )
    return alpha


def _equivalence_tost_reference_mean(options: dict[str, Any]) -> float:
    return _required_finite_float(
        options,
        "reference_mean",
        code="invalid_equivalence_tost_reference_mean",
        message="동등성 검정 기준 평균을 입력해야 합니다.",
    )


def _equivalence_tost_lower_bound(options: dict[str, Any]) -> float:
    return _required_finite_float(
        options,
        "lower_bound",
        code="invalid_equivalence_tost_bounds",
        message="동등성 검정 하한을 입력해야 합니다.",
    )


def _equivalence_tost_upper_bound(options: dict[str, Any]) -> float:
    return _required_finite_float(
        options,
        "upper_bound",
        code="invalid_equivalence_tost_bounds",
        message="동등성 검정 상한을 입력해야 합니다.",
    )


def _required_finite_float(
    options: dict[str, Any],
    key: str,
    *,
    code: str,
    message: str,
) -> float:
    raw_value = options.get(key)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(code=code, message=message)
    value = float(raw_value)
    if not isfinite(value):
        raise ApiError(code=code, message=message)
    return value


def _equivalence_tost_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="equivalence_tost_missing_policy_unsupported",
            message="동등성 검정은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _equivalence_tost_api_error(code: str) -> ApiError:
    messages = {
        "equivalence_tost_design_unsupported": "현재 동등성 검정은 1표본 평균 설계만 지원합니다.",
        "invalid_equivalence_tost_reference_mean": ("동등성 검정 기준 평균이 올바르지 않습니다."),
        "invalid_equivalence_tost_bounds": "동등성 검정 한계값이 올바르지 않습니다.",
        "equivalence_tost_bounds_order_invalid": "동등성 하한은 상한보다 작아야 합니다.",
        "invalid_equivalence_tost_alpha": (
            "동등성 검정 유의수준은 0보다 크고 0.5보다 작아야 합니다."
        ),
        "equivalence_tost_n_too_small": "동등성 검정에는 최소 2개 사용 값이 필요합니다.",
        "equivalence_tost_standard_error_zero": (
            "평균 차이의 표준오차가 0이어서 동등성 검정을 계산할 수 없습니다."
        ),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "동등성 검정을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _equivalence_tost_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "equivalence_tost_design_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="equivalence_tost_design_assumption",
                severity="info",
                message="독립성 및 1표본 평균 설계는 사용자가 확인해야 하는 설계 가정입니다.",
            ),
        )
    if "equivalence_bounds_user_defined" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="equivalence_bounds_user_defined",
                severity="info",
                message="동등성 한계는 앱이 추정하지 않으며 사용자가 사전에 정의해야 합니다.",
            ),
        )
    if "non_significance_is_not_equivalence" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="non_significance_is_not_equivalence",
                severity="info",
                message="일반 차이검정의 비유의성은 동등성 근거가 아닙니다.",
            ),
        )
    if "missing_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="missing_values_excluded",
                severity="warning",
                message="반응 결측 행은 complete-case 정책으로 제외했습니다.",
            ),
        )
    if "non_numeric_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="non_numeric_values_excluded",
                severity="warning",
                message="반응 값 중 숫자로 해석할 수 없는 값은 제외했습니다.",
            ),
        )
    return warnings


def _run_paired_t_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="대응표본 t-검정 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    before_column, after_column = _selected_paired_t_columns(context, request.options)
    alpha = _paired_t_alpha(request.options)
    confidence_level = _paired_t_confidence_level(request.options)
    alternative = _paired_t_alternative(request.options)
    null_difference = _paired_t_null_difference(request.options)
    _paired_t_missing_policy(request.options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    result_path: Path | None = None

    try:
        try:
            result = calculate_paired_t(
                _iter_rows_for_snapshot(context, row_snapshot),
                before_column,
                after_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                alpha=alpha,
                confidence_level=confidence_level,
                alternative=alternative,
                null_difference=null_difference,
            )
        except PairedTError as exc:
            raise _paired_t_api_error(exc.code) from exc
        warnings = _paired_t_warnings(result)
        provenance = AnalysisProvenance(
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            source_schema_hash=context.version.schema_hash,
            filter_snapshot_sha256=str(row_snapshot.payload["filter_snapshot_sha256"]),
            row_snapshot_sha256=row_snapshot.record.sha256,
            row_count_total=context.version.row_count,
            row_count_included=int(row_snapshot.payload["selection"]["row_count_included"]),
            app_version=APP_VERSION,
        )
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=provenance,
            result=result,
        )

        result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = _analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=_analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=[row_snapshot.record],
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        if result_path is not None:
            _remove_file_if_exists(result_path)
        raise
    return envelope


def _selected_paired_t_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[PairedTColumn, PairedTColumn]:
    before_column_id = options.get("before_column_id")
    after_column_id = options.get("after_column_id")
    if not isinstance(before_column_id, str) or not before_column_id:
        raise ApiError(
            code="paired_t_before_column_required",
            message="대응표본 t-검정의 첫 번째 측정 컬럼을 선택해야 합니다.",
        )
    if not isinstance(after_column_id, str) or not after_column_id:
        raise ApiError(
            code="paired_t_after_column_required",
            message="대응표본 t-검정의 두 번째 측정 컬럼을 선택해야 합니다.",
        )
    if before_column_id == after_column_id:
        raise ApiError(
            code="paired_t_same_before_and_after_column",
            message="대응표본 t-검정의 두 측정 컬럼은 서로 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    before_column = columns_by_id.get(before_column_id)
    if before_column is None:
        raise ApiError(
            code="paired_t_before_column_not_found",
            message="요청한 대응표본 t-검정 첫 번째 측정 컬럼을 찾을 수 없습니다.",
        )
    after_column = columns_by_id.get(after_column_id)
    if after_column is None:
        raise ApiError(
            code="paired_t_after_column_not_found",
            message="요청한 대응표본 t-검정 두 번째 측정 컬럼을 찾을 수 없습니다.",
        )

    _validate_paired_t_column(before_column, code_prefix="before")
    _validate_paired_t_column(after_column, code_prefix="after")
    return (
        _paired_t_column(before_column),
        _paired_t_column(after_column),
    )


def _validate_paired_t_column(column: DatasetColumnRecord, *, code_prefix: str) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code=f"paired_t_{code_prefix}_column_is_id",
            message="ID 컬럼은 대응표본 t-검정 측정 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code=f"paired_t_{code_prefix}_column_not_numeric",
            message="대응표본 t-검정 측정 변수는 현재 숫자형 컬럼만 지원합니다.",
        )


def _paired_t_column(column: DatasetColumnRecord) -> PairedTColumn:
    return PairedTColumn(
        column_id=column.column_id,
        column_index=column.column_index,
        display_name=column.display_name,
        data_type=column.data_type,
        measurement_level=column.measurement_level,
        role=column.role,
        unit=column.unit,
    )


def _paired_t_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_paired_t_alpha",
            message="대응표본 t-검정 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0:
        raise ApiError(
            code="invalid_paired_t_alpha",
            message="대응표본 t-검정 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _paired_t_confidence_level(options: dict[str, Any]) -> float:
    raw_value = options.get("confidence_level", 0.95)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_paired_t_confidence_level",
            message="대응표본 t-검정 신뢰수준이 올바르지 않습니다.",
        )
    confidence_level = float(raw_value)
    if confidence_level <= 0.0 or confidence_level >= 1.0:
        raise ApiError(
            code="invalid_paired_t_confidence_level",
            message="대응표본 t-검정 신뢰수준이 허용 범위를 벗어났습니다.",
        )
    return confidence_level


def _paired_t_alternative(options: dict[str, Any]) -> str:
    raw_value = options.get("alternative", "two_sided")
    if raw_value not in {"two_sided", "greater", "less"}:
        raise ApiError(
            code="invalid_paired_t_alternative",
            message="대응표본 t-검정 대립가설이 올바르지 않습니다.",
        )
    return str(raw_value)


def _paired_t_null_difference(options: dict[str, Any]) -> float:
    raw_value = options.get("null_difference", 0.0)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_paired_t_null_difference",
            message="대응표본 t-검정 기준 차이가 올바르지 않습니다.",
        )
    null_difference = float(raw_value)
    if not isfinite(null_difference):
        raise ApiError(
            code="invalid_paired_t_null_difference",
            message="대응표본 t-검정 기준 차이가 유한하지 않습니다.",
        )
    return null_difference


def _paired_t_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_pair")
    if raw_value != "complete_pair":
        raise ApiError(
            code="paired_t_missing_policy_unsupported",
            message="대응표본 t-검정은 현재 complete-pair 결측 처리만 지원합니다.",
        )
    return raw_value


def _paired_t_api_error(code: str) -> ApiError:
    messages = {
        "paired_t_n_too_small": "대응표본 t-검정에는 최소 2개 완전한 pair가 필요합니다.",
        "paired_t_standard_error_zero": (
            "pair 차이의 표준오차가 0이어서 대응표본 t-검정을 계산할 수 없습니다."
        ),
        "invalid_paired_t_alternative": "대응표본 t-검정 대립가설이 올바르지 않습니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "대응표본 t-검정을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _paired_t_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "paired_t_design_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="paired_t_design_assumption",
                severity="info",
                message=(
                    "각 행이 같은 subject/pair의 두 측정값이라는 설계 가정은 "
                    "사용자가 확인해야 합니다."
                ),
            ),
        )
    if "paired_t_not_auto_switched" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="paired_t_not_auto_switched",
                severity="info",
                message="정규성 진단 결과로 대응표본 t-검정을 자동 전환하지 않습니다.",
            ),
        )
    if "incomplete_pairs_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="incomplete_pairs_excluded",
                severity="warning",
                message="한쪽 측정값이 없는 incomplete pair는 complete-pair 정책으로 제외했습니다.",
            ),
        )
    if "non_numeric_pairs_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="non_numeric_pairs_excluded",
                severity="warning",
                message="두 측정값 중 숫자로 해석할 수 없는 값이 있는 pair는 제외했습니다.",
            ),
        )
    return warnings


def _run_one_sample_wilcoxon_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="1-표본 Wilcoxon 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column = _selected_one_sample_wilcoxon_column(context, request.options)
    alpha = _one_sample_wilcoxon_alpha(request.options)
    alternative = _one_sample_wilcoxon_alternative(request.options)
    null_location = _one_sample_wilcoxon_null_location(request.options)
    method = _one_sample_wilcoxon_method(request.options)
    zero_method = _one_sample_wilcoxon_zero_method(request.options)
    _one_sample_wilcoxon_missing_policy(request.options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    result_path: Path | None = None

    try:
        try:
            result = calculate_one_sample_wilcoxon(
                _iter_rows_for_snapshot(context, row_snapshot),
                response_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                alpha=alpha,
                alternative=alternative,
                null_location=null_location,
                method=method,
                zero_method=zero_method,
            )
        except OneSampleWilcoxonError as exc:
            raise _one_sample_wilcoxon_api_error(exc.code) from exc
        warnings = _one_sample_wilcoxon_warnings(result)
        provenance = AnalysisProvenance(
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            source_schema_hash=context.version.schema_hash,
            filter_snapshot_sha256=str(row_snapshot.payload["filter_snapshot_sha256"]),
            row_snapshot_sha256=row_snapshot.record.sha256,
            row_count_total=context.version.row_count,
            row_count_included=int(row_snapshot.payload["selection"]["row_count_included"]),
            app_version=APP_VERSION,
        )
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=provenance,
            result=result,
        )

        result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = _analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=_analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=[row_snapshot.record],
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        if result_path is not None:
            _remove_file_if_exists(result_path)
        raise
    return envelope


def _selected_one_sample_wilcoxon_column(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> OneSampleWilcoxonColumn:
    response_column_id = options.get("response_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="one_sample_wilcoxon_response_required",
            message="1-표본 Wilcoxon 반응 컬럼을 선택해야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_column = columns_by_id.get(response_column_id)
    if response_column is None:
        raise ApiError(
            code="one_sample_wilcoxon_response_column_not_found",
            message="요청한 1-표본 Wilcoxon 반응 컬럼을 찾을 수 없습니다.",
        )

    _validate_one_sample_wilcoxon_response_column(response_column)
    return OneSampleWilcoxonColumn(
        column_id=response_column.column_id,
        column_index=response_column.column_index,
        display_name=response_column.display_name,
        data_type=response_column.data_type,
        measurement_level=response_column.measurement_level,
        role=response_column.role,
        unit=response_column.unit,
    )


def _validate_one_sample_wilcoxon_response_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="one_sample_wilcoxon_response_column_is_id",
            message="ID 컬럼은 1-표본 Wilcoxon 반응 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="one_sample_wilcoxon_response_column_not_numeric",
            message="1-표본 Wilcoxon 반응 변수는 현재 숫자형 컬럼만 지원합니다.",
        )


def _one_sample_wilcoxon_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_one_sample_wilcoxon_alpha",
            message="1-표본 Wilcoxon 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0:
        raise ApiError(
            code="invalid_one_sample_wilcoxon_alpha",
            message="1-표본 Wilcoxon 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _one_sample_wilcoxon_alternative(options: dict[str, Any]) -> str:
    raw_value = options.get("alternative", "two_sided")
    if raw_value not in {"two_sided", "greater", "less"}:
        raise ApiError(
            code="invalid_one_sample_wilcoxon_alternative",
            message="1-표본 Wilcoxon 대립가설이 올바르지 않습니다.",
        )
    return str(raw_value)


def _one_sample_wilcoxon_null_location(options: dict[str, Any]) -> float:
    raw_value = options.get("null_location", 0.0)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_one_sample_wilcoxon_null_location",
            message="1-표본 Wilcoxon 기준 위치가 올바르지 않습니다.",
        )
    null_location = float(raw_value)
    if not isfinite(null_location):
        raise ApiError(
            code="invalid_one_sample_wilcoxon_null_location",
            message="1-표본 Wilcoxon 기준 위치가 유한하지 않습니다.",
        )
    return null_location


def _one_sample_wilcoxon_method(options: dict[str, Any]) -> str:
    raw_value = options.get("method", "auto")
    if raw_value not in {"auto", "exact", "asymptotic"}:
        raise ApiError(
            code="invalid_one_sample_wilcoxon_method",
            message="1-표본 Wilcoxon p-value 계산 방식이 올바르지 않습니다.",
        )
    return str(raw_value)


def _one_sample_wilcoxon_zero_method(options: dict[str, Any]) -> str:
    raw_value = options.get("zero_method", "wilcox")
    if raw_value not in {"wilcox", "pratt", "zsplit"}:
        raise ApiError(
            code="invalid_one_sample_wilcoxon_zero_method",
            message="1-표본 Wilcoxon zero difference 처리 방식이 올바르지 않습니다.",
        )
    return str(raw_value)


def _one_sample_wilcoxon_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="one_sample_wilcoxon_missing_policy_unsupported",
            message="1-표본 Wilcoxon은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _one_sample_wilcoxon_api_error(code: str) -> ApiError:
    messages = {
        "one_sample_wilcoxon_no_nonzero_differences": (
            "기준 위치와 다른 사용 값이 없어 1-표본 Wilcoxon을 계산할 수 없습니다."
        ),
        "one_sample_wilcoxon_exact_with_zeros_or_ties": (
            "zero difference 또는 동률 절대차가 있을 때는 exact 1-표본 "
            "Wilcoxon p-value를 계산하지 않습니다."
        ),
        "one_sample_wilcoxon_statistic_not_finite": (
            "1-표본 Wilcoxon 통계량 또는 p-value가 유한하지 않습니다."
        ),
        "invalid_one_sample_wilcoxon_alternative": (
            "1-표본 Wilcoxon 대립가설이 올바르지 않습니다."
        ),
        "invalid_one_sample_wilcoxon_method": (
            "1-표본 Wilcoxon p-value 계산 방식이 올바르지 않습니다."
        ),
        "invalid_one_sample_wilcoxon_zero_method": (
            "1-표본 Wilcoxon zero difference 처리 방식이 올바르지 않습니다."
        ),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "1-표본 Wilcoxon을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _one_sample_wilcoxon_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "one_sample_wilcoxon_symmetry_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_sample_wilcoxon_symmetry_assumption",
                severity="info",
                message="차이값 분포의 대칭성은 설계/진단 가정이며 자동 검증하지 않습니다.",
            ),
        )
    if "one_sample_wilcoxon_not_median_test" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_sample_wilcoxon_not_median_test",
                severity="info",
                message=(
                    "대칭성 가정 없이 1-표본 Wilcoxon을 단순 중앙값 검정으로 " "단정하지 않습니다."
                ),
            ),
        )
    if "one_sample_wilcoxon_not_auto_switched" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_sample_wilcoxon_not_auto_switched",
                severity="info",
                message="정규성 진단 결과로 1-표본 Wilcoxon을 자동 선택하지 않습니다.",
            ),
        )
    if "zero_differences_detected" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="zero_differences_detected",
                severity="warning",
                message=(
                    "기준 위치와 같은 값이 있어 zero difference 처리 방식을 함께 "
                    "확인해야 합니다."
                ),
            ),
        )
    if "signed_rank_ties_detected" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="signed_rank_ties_detected",
                severity="warning",
                message="동률 절대차가 있어 p-value 방식과 rank 해석을 함께 확인해야 합니다.",
            ),
        )
    if "one_sample_wilcoxon_auto_asymptotic_due_to_zeros_or_ties" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_sample_wilcoxon_auto_asymptotic_due_to_zeros_or_ties",
                severity="info",
                message=(
                    "auto 방식에서 zero difference 또는 동률을 감지해 asymptotic "
                    "p-value를 사용했습니다."
                ),
            ),
        )
    if "small_nonzero_n" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="small_nonzero_n",
                severity="info",
                message="기준 위치와 다른 사용 값 수가 작아 p-value 방식과 설계를 함께 확인하세요.",
            ),
        )
    if "missing_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="missing_values_excluded",
                severity="warning",
                message="반응 결측 행은 complete-case 정책으로 제외했습니다.",
            ),
        )
    if "non_numeric_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="non_numeric_values_excluded",
                severity="warning",
                message="반응 값 중 숫자로 해석할 수 없는 값은 제외했습니다.",
            ),
        )
    return warnings


def _run_two_sample_t_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="2-표본 t-검정 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column, group_column = _selected_two_sample_t_columns(context, request.options)
    alpha = _two_sample_t_alpha(request.options)
    confidence_level = _two_sample_t_confidence_level(request.options)
    alternative = _two_sample_t_alternative(request.options)
    variance_assumption = _two_sample_t_variance_assumption(request.options)
    null_difference = _two_sample_t_null_difference(request.options)
    _two_sample_t_missing_policy(request.options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    result_path: Path | None = None

    try:
        try:
            result = calculate_two_sample_t(
                _iter_rows_for_snapshot(context, row_snapshot),
                response_column,
                group_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                alpha=alpha,
                confidence_level=confidence_level,
                alternative=alternative,
                variance_assumption=variance_assumption,
                null_difference=null_difference,
            )
        except TwoSampleTError as exc:
            raise _two_sample_t_api_error(exc.code) from exc
        warnings = _two_sample_t_warnings(result)
        provenance = AnalysisProvenance(
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            source_schema_hash=context.version.schema_hash,
            filter_snapshot_sha256=str(row_snapshot.payload["filter_snapshot_sha256"]),
            row_snapshot_sha256=row_snapshot.record.sha256,
            row_count_total=context.version.row_count,
            row_count_included=int(row_snapshot.payload["selection"]["row_count_included"]),
            app_version=APP_VERSION,
        )
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=provenance,
            result=result,
        )

        result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = _analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=_analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=[row_snapshot.record],
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        if result_path is not None:
            _remove_file_if_exists(result_path)
        raise
    return envelope


def _selected_two_sample_t_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[TwoSampleTResponseColumn, TwoSampleTGroupColumn]:
    response_column_id = options.get("response_column_id")
    group_column_id = options.get("group_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="two_sample_t_response_required",
            message="2-표본 t-검정 반응 컬럼을 선택해야 합니다.",
        )
    if not isinstance(group_column_id, str) or not group_column_id:
        raise ApiError(
            code="two_sample_t_group_required",
            message="2-표본 t-검정 그룹 컬럼을 선택해야 합니다.",
        )
    if response_column_id == group_column_id:
        raise ApiError(
            code="two_sample_t_same_response_and_group",
            message="반응 컬럼과 그룹 컬럼은 서로 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_column = columns_by_id.get(response_column_id)
    if response_column is None:
        raise ApiError(
            code="two_sample_t_response_column_not_found",
            message="요청한 2-표본 t-검정 반응 컬럼을 찾을 수 없습니다.",
        )
    group_column = columns_by_id.get(group_column_id)
    if group_column is None:
        raise ApiError(
            code="two_sample_t_group_column_not_found",
            message="요청한 2-표본 t-검정 그룹 컬럼을 찾을 수 없습니다.",
        )

    _validate_two_sample_t_response_column(response_column)
    _validate_two_sample_t_group_column(group_column)
    return (
        TwoSampleTResponseColumn(
            column_id=response_column.column_id,
            column_index=response_column.column_index,
            display_name=response_column.display_name,
            data_type=response_column.data_type,
            measurement_level=response_column.measurement_level,
            role=response_column.role,
            unit=response_column.unit,
        ),
        TwoSampleTGroupColumn(
            column_id=group_column.column_id,
            column_index=group_column.column_index,
            display_name=group_column.display_name,
            data_type=group_column.data_type,
            measurement_level=group_column.measurement_level,
            role=group_column.role,
            unit=group_column.unit,
        ),
    )


def _validate_two_sample_t_response_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="two_sample_t_response_column_is_id",
            message="ID 컬럼은 2-표본 t-검정 반응 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="two_sample_t_response_column_not_numeric",
            message="2-표본 t-검정 반응 변수는 현재 숫자형 컬럼만 지원합니다.",
        )


def _validate_two_sample_t_group_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="two_sample_t_group_column_is_id",
            message="ID 컬럼은 2-표본 t-검정 그룹 변수로 사용할 수 없습니다.",
        )


def _two_sample_t_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_two_sample_t_alpha",
            message="2-표본 t-검정 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0:
        raise ApiError(
            code="invalid_two_sample_t_alpha",
            message="2-표본 t-검정 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _two_sample_t_confidence_level(options: dict[str, Any]) -> float:
    raw_value = options.get("confidence_level", 0.95)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_two_sample_t_confidence_level",
            message="2-표본 t-검정 신뢰수준이 올바르지 않습니다.",
        )
    confidence_level = float(raw_value)
    if confidence_level <= 0.0 or confidence_level >= 1.0:
        raise ApiError(
            code="invalid_two_sample_t_confidence_level",
            message="2-표본 t-검정 신뢰수준이 허용 범위를 벗어났습니다.",
        )
    return confidence_level


def _two_sample_t_alternative(options: dict[str, Any]) -> str:
    raw_value = options.get("alternative", "two_sided")
    if raw_value not in {"two_sided", "greater", "less"}:
        raise ApiError(
            code="invalid_two_sample_t_alternative",
            message="2-표본 t-검정 대립가설이 올바르지 않습니다.",
        )
    return str(raw_value)


def _two_sample_t_variance_assumption(options: dict[str, Any]) -> str:
    raw_value = options.get("variance_assumption", "welch")
    if raw_value not in {"welch", "pooled"}:
        raise ApiError(
            code="invalid_two_sample_t_variance_assumption",
            message="2-표본 t-검정 분산 가정이 올바르지 않습니다.",
        )
    return str(raw_value)


def _two_sample_t_null_difference(options: dict[str, Any]) -> float:
    raw_value = options.get("null_difference", 0.0)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_two_sample_t_null_difference",
            message="2-표본 t-검정 기준 평균 차이가 올바르지 않습니다.",
        )
    null_difference = float(raw_value)
    if not isfinite(null_difference):
        raise ApiError(
            code="invalid_two_sample_t_null_difference",
            message="2-표본 t-검정 기준 평균 차이가 유한하지 않습니다.",
        )
    return null_difference


def _two_sample_t_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="two_sample_t_missing_policy_unsupported",
            message="2-표본 t-검정은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _two_sample_t_api_error(code: str) -> ApiError:
    messages = {
        "two_sample_t_requires_exactly_two_groups": (
            "2-표본 t-검정에는 사용 가능한 그룹이 정확히 2개 필요합니다."
        ),
        "two_sample_t_group_n_too_small": "각 그룹에는 최소 2개 사용 값이 필요합니다.",
        "two_sample_t_standard_error_zero": (
            "평균 차이의 표준오차가 0이어서 2-표본 t-검정을 계산할 수 없습니다."
        ),
        "invalid_two_sample_t_alternative": "2-표본 t-검정 대립가설이 올바르지 않습니다.",
        "invalid_two_sample_t_variance_assumption": (
            "2-표본 t-검정 분산 가정이 올바르지 않습니다."
        ),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "2-표본 t-검정을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _two_sample_t_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "two_sample_t_independence_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="two_sample_t_independence_assumption",
                severity="info",
                message="독립성은 설계 가정이며 데이터만으로 자동 검증하지 않습니다.",
            ),
        )
    if "two_sample_t_not_auto_switched" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="two_sample_t_not_auto_switched",
                severity="info",
                message="정규성/등분산 진단 결과로 2-표본 t-검정 방식을 자동 전환하지 않습니다.",
            ),
        )
    if "pooled_variance_assumption_selected" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="pooled_variance_assumption_selected",
                severity="warning",
                message="pooled Student 방식은 사용자가 명시적으로 선택한 경우에만 실행합니다.",
            ),
        )
    if "missing_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="missing_values_excluded",
                severity="warning",
                message="반응 또는 그룹 결측 행은 complete-case 정책으로 제외했습니다.",
            ),
        )
    if "non_numeric_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="non_numeric_values_excluded",
                severity="warning",
                message="반응 값 중 숫자로 해석할 수 없는 값은 제외했습니다.",
            ),
        )
    if "constant_group" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="constant_group",
                severity="warning",
                message="하나 이상의 그룹에서 반응 값이 모두 동일합니다.",
            ),
        )
    if "group_size_imbalance" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="group_size_imbalance",
                severity="info",
                message="그룹 크기 불균형이 큽니다. 설계와 영향점을 함께 확인하세요.",
            ),
        )
    return warnings


def _run_mann_whitney_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="Mann-Whitney U 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column, group_column = _selected_mann_whitney_columns(context, request.options)
    alpha = _mann_whitney_alpha(request.options)
    alternative = _mann_whitney_alternative(request.options)
    method = _mann_whitney_method(request.options)
    _mann_whitney_missing_policy(request.options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    result_path: Path | None = None

    try:
        try:
            result = calculate_mann_whitney(
                _iter_rows_for_snapshot(context, row_snapshot),
                response_column,
                group_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                alpha=alpha,
                alternative=alternative,
                method=method,
            )
        except MannWhitneyError as exc:
            raise _mann_whitney_api_error(exc.code) from exc
        warnings = _mann_whitney_warnings(result)
        provenance = AnalysisProvenance(
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            source_schema_hash=context.version.schema_hash,
            filter_snapshot_sha256=str(row_snapshot.payload["filter_snapshot_sha256"]),
            row_snapshot_sha256=row_snapshot.record.sha256,
            row_count_total=context.version.row_count,
            row_count_included=int(row_snapshot.payload["selection"]["row_count_included"]),
            app_version=APP_VERSION,
        )
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=provenance,
            result=result,
        )

        result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = _analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=_analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=[row_snapshot.record],
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        if result_path is not None:
            _remove_file_if_exists(result_path)
        raise
    return envelope


def _selected_mann_whitney_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[MannWhitneyResponseColumn, MannWhitneyGroupColumn]:
    response_column_id = options.get("response_column_id")
    group_column_id = options.get("group_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="mann_whitney_response_required",
            message="Mann-Whitney U 반응 컬럼을 선택해야 합니다.",
        )
    if not isinstance(group_column_id, str) or not group_column_id:
        raise ApiError(
            code="mann_whitney_group_required",
            message="Mann-Whitney U 그룹 컬럼을 선택해야 합니다.",
        )
    if response_column_id == group_column_id:
        raise ApiError(
            code="mann_whitney_same_response_and_group",
            message="반응 컬럼과 그룹 컬럼은 서로 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_column = columns_by_id.get(response_column_id)
    if response_column is None:
        raise ApiError(
            code="mann_whitney_response_column_not_found",
            message="요청한 Mann-Whitney U 반응 컬럼을 찾을 수 없습니다.",
        )
    group_column = columns_by_id.get(group_column_id)
    if group_column is None:
        raise ApiError(
            code="mann_whitney_group_column_not_found",
            message="요청한 Mann-Whitney U 그룹 컬럼을 찾을 수 없습니다.",
        )

    _validate_mann_whitney_response_column(response_column)
    _validate_mann_whitney_group_column(group_column)
    return (
        MannWhitneyResponseColumn(
            column_id=response_column.column_id,
            column_index=response_column.column_index,
            display_name=response_column.display_name,
            data_type=response_column.data_type,
            measurement_level=response_column.measurement_level,
            role=response_column.role,
            unit=response_column.unit,
        ),
        MannWhitneyGroupColumn(
            column_id=group_column.column_id,
            column_index=group_column.column_index,
            display_name=group_column.display_name,
            data_type=group_column.data_type,
            measurement_level=group_column.measurement_level,
            role=group_column.role,
            unit=group_column.unit,
        ),
    )


def _validate_mann_whitney_response_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="mann_whitney_response_column_is_id",
            message="ID 컬럼은 Mann-Whitney U 반응 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="mann_whitney_response_column_not_numeric",
            message="Mann-Whitney U 반응 변수는 현재 숫자형 컬럼만 지원합니다.",
        )


def _validate_mann_whitney_group_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="mann_whitney_group_column_is_id",
            message="ID 컬럼은 Mann-Whitney U 그룹 변수로 사용할 수 없습니다.",
        )


def _mann_whitney_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_mann_whitney_alpha",
            message="Mann-Whitney U 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0:
        raise ApiError(
            code="invalid_mann_whitney_alpha",
            message="Mann-Whitney U 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _mann_whitney_alternative(options: dict[str, Any]) -> str:
    raw_value = options.get("alternative", "two_sided")
    if raw_value not in {"two_sided", "greater", "less"}:
        raise ApiError(
            code="invalid_mann_whitney_alternative",
            message="Mann-Whitney U 대립가설이 올바르지 않습니다.",
        )
    return str(raw_value)


def _mann_whitney_method(options: dict[str, Any]) -> str:
    raw_value = options.get("method", "auto")
    if raw_value not in {"auto", "exact", "asymptotic"}:
        raise ApiError(
            code="invalid_mann_whitney_method",
            message="Mann-Whitney U p-value 계산 방식이 올바르지 않습니다.",
        )
    return str(raw_value)


def _mann_whitney_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="mann_whitney_missing_policy_unsupported",
            message="Mann-Whitney U는 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _mann_whitney_api_error(code: str) -> ApiError:
    messages = {
        "mann_whitney_requires_exactly_two_groups": (
            "Mann-Whitney U에는 사용 가능한 그룹이 정확히 2개 필요합니다."
        ),
        "mann_whitney_group_n_too_small": "각 그룹에는 최소 1개 사용 값이 필요합니다.",
        "mann_whitney_exact_with_ties": (
            "동률 값이 있을 때는 exact Mann-Whitney U p-value를 계산하지 않습니다."
        ),
        "mann_whitney_statistic_not_finite": (
            "Mann-Whitney U 통계량 또는 p-value가 유한하지 않습니다."
        ),
        "invalid_mann_whitney_alternative": "Mann-Whitney U 대립가설이 올바르지 않습니다.",
        "invalid_mann_whitney_method": "Mann-Whitney U p-value 계산 방식이 올바르지 않습니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "Mann-Whitney U를 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _mann_whitney_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "mann_whitney_independence_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="mann_whitney_independence_assumption",
                severity="info",
                message="독립성은 설계 가정이며 데이터만으로 자동 검증하지 않습니다.",
            ),
        )
    if "mann_whitney_not_median_test" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="mann_whitney_not_median_test",
                severity="info",
                message="Mann-Whitney U 결과를 단순 중앙값 차이 검정으로 해석하지 않습니다.",
            ),
        )
    if "mann_whitney_ties_detected" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="mann_whitney_ties_detected",
                severity="warning",
                message="동률 값이 있어 p-value 방식과 rank 해석을 함께 확인해야 합니다.",
            ),
        )
    if "mann_whitney_auto_asymptotic_due_to_ties" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="mann_whitney_auto_asymptotic_due_to_ties",
                severity="info",
                message="auto 방식에서 동률 값을 감지해 asymptotic p-value를 사용했습니다.",
            ),
        )
    if "missing_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="missing_values_excluded",
                severity="warning",
                message="반응 또는 그룹 결측 행은 complete-case 정책으로 제외했습니다.",
            ),
        )
    if "non_numeric_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="non_numeric_values_excluded",
                severity="warning",
                message="반응 값 중 숫자로 해석할 수 없는 값은 제외했습니다.",
            ),
        )
    if "constant_group" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="constant_group",
                severity="warning",
                message="하나 이상의 그룹에서 반응 값이 모두 동일합니다.",
            ),
        )
    if "small_group_size" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="small_group_size",
                severity="info",
                message="그룹 표본 수가 작아 exact/asymptotic 방식과 설계를 함께 확인하세요.",
            ),
        )
    if "group_size_imbalance" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="group_size_imbalance",
                severity="info",
                message="그룹 크기 불균형이 큽니다. 설계와 영향점을 함께 확인하세요.",
            ),
        )
    return warnings


def _run_kruskal_wallis_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="Kruskal-Wallis 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column, group_column = _selected_kruskal_wallis_columns(
        context,
        request.options,
    )
    alpha = _kruskal_wallis_alpha(request.options)
    posthoc_method = _kruskal_wallis_posthoc_method(request.options)
    posthoc_policy = _kruskal_wallis_posthoc_policy(request.options)
    _kruskal_wallis_missing_policy(request.options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    result_path: Path | None = None

    try:
        try:
            result = calculate_kruskal_wallis(
                _iter_rows_for_snapshot(context, row_snapshot),
                response_column,
                group_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                alpha=alpha,
                posthoc_method=posthoc_method,
                posthoc_policy=posthoc_policy,
            )
        except KruskalWallisError as exc:
            raise _kruskal_wallis_api_error(exc.code) from exc
        warnings = _kruskal_wallis_warnings(result)
        provenance = AnalysisProvenance(
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            source_schema_hash=context.version.schema_hash,
            filter_snapshot_sha256=str(row_snapshot.payload["filter_snapshot_sha256"]),
            row_snapshot_sha256=row_snapshot.record.sha256,
            row_count_total=context.version.row_count,
            row_count_included=int(row_snapshot.payload["selection"]["row_count_included"]),
            app_version=APP_VERSION,
        )
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=provenance,
            result=result,
        )

        result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = _analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=_analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=[row_snapshot.record],
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        if result_path is not None:
            _remove_file_if_exists(result_path)
        raise
    return envelope


def _selected_kruskal_wallis_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[KruskalWallisResponseColumn, KruskalWallisGroupColumn]:
    response_column_id = options.get("response_column_id")
    group_column_id = options.get("group_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="kruskal_wallis_response_required",
            message="Kruskal-Wallis 반응 컬럼을 선택해야 합니다.",
        )
    if not isinstance(group_column_id, str) or not group_column_id:
        raise ApiError(
            code="kruskal_wallis_group_required",
            message="Kruskal-Wallis 그룹 컬럼을 선택해야 합니다.",
        )
    if response_column_id == group_column_id:
        raise ApiError(
            code="kruskal_wallis_same_response_and_group",
            message="반응 컬럼과 그룹 컬럼은 서로 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_column = columns_by_id.get(response_column_id)
    if response_column is None:
        raise ApiError(
            code="kruskal_wallis_response_column_not_found",
            message="요청한 Kruskal-Wallis 반응 컬럼을 찾을 수 없습니다.",
        )
    group_column = columns_by_id.get(group_column_id)
    if group_column is None:
        raise ApiError(
            code="kruskal_wallis_group_column_not_found",
            message="요청한 Kruskal-Wallis 그룹 컬럼을 찾을 수 없습니다.",
        )

    _validate_kruskal_wallis_response_column(response_column)
    _validate_kruskal_wallis_group_column(group_column)
    return (
        KruskalWallisResponseColumn(
            column_id=response_column.column_id,
            column_index=response_column.column_index,
            display_name=response_column.display_name,
            data_type=response_column.data_type,
            measurement_level=response_column.measurement_level,
            role=response_column.role,
            unit=response_column.unit,
        ),
        KruskalWallisGroupColumn(
            column_id=group_column.column_id,
            column_index=group_column.column_index,
            display_name=group_column.display_name,
            data_type=group_column.data_type,
            measurement_level=group_column.measurement_level,
            role=group_column.role,
            unit=group_column.unit,
        ),
    )


def _validate_kruskal_wallis_response_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="kruskal_wallis_response_column_is_id",
            message="ID 컬럼은 Kruskal-Wallis 반응 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="kruskal_wallis_response_column_not_numeric",
            message="Kruskal-Wallis 반응 변수는 현재 숫자형 컬럼만 지원합니다.",
        )


def _validate_kruskal_wallis_group_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="kruskal_wallis_group_column_is_id",
            message="ID 컬럼은 Kruskal-Wallis 그룹 변수로 사용할 수 없습니다.",
        )


def _kruskal_wallis_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_kruskal_wallis_alpha",
            message="Kruskal-Wallis 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0:
        raise ApiError(
            code="invalid_kruskal_wallis_alpha",
            message="Kruskal-Wallis 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _kruskal_wallis_posthoc_method(options: dict[str, Any]) -> str:
    raw_value = options.get("posthoc_method", "dunn_holm")
    if raw_value not in {"dunn_holm", "none"}:
        raise ApiError(
            code="invalid_kruskal_wallis_posthoc_method",
            message="Kruskal-Wallis 사후검정 방식이 올바르지 않습니다.",
        )
    return str(raw_value)


def _kruskal_wallis_posthoc_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("posthoc_policy", "after_significant")
    if raw_value != "after_significant":
        raise ApiError(
            code="invalid_kruskal_wallis_posthoc_policy",
            message="Kruskal-Wallis 사후검정 정책이 올바르지 않습니다.",
        )
    return str(raw_value)


def _kruskal_wallis_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="kruskal_wallis_missing_policy_unsupported",
            message="Kruskal-Wallis는 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _kruskal_wallis_api_error(code: str) -> ApiError:
    messages = {
        "kruskal_wallis_requires_at_least_three_groups": (
            "Kruskal-Wallis에는 사용 가능한 그룹이 최소 3개 필요합니다."
        ),
        "kruskal_wallis_group_n_too_small": ("각 그룹에는 최소 1개 사용 값이 필요합니다."),
        "kruskal_wallis_all_values_identical": (
            "전체 반응 값이 모두 동일해 Kruskal-Wallis 통계량을 계산할 수 없습니다."
        ),
        "kruskal_wallis_statistic_not_finite": (
            "Kruskal-Wallis 통계량 또는 p-value가 유한하지 않습니다."
        ),
        "kruskal_wallis_posthoc_variance_zero": (
            "Dunn 사후검정의 rank 분산이 0이어서 계산할 수 없습니다."
        ),
        "invalid_kruskal_wallis_posthoc_method": (
            "Kruskal-Wallis 사후검정 방식이 올바르지 않습니다."
        ),
        "invalid_kruskal_wallis_posthoc_policy": (
            "Kruskal-Wallis 사후검정 정책이 올바르지 않습니다."
        ),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "Kruskal-Wallis를 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _kruskal_wallis_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "kruskal_wallis_independence_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="kruskal_wallis_independence_assumption",
                severity="info",
                message="독립성은 설계 가정이며 데이터만으로 자동 검증하지 않습니다.",
            ),
        )
    if "kruskal_wallis_not_median_test" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="kruskal_wallis_not_median_test",
                severity="info",
                message="Kruskal-Wallis 결과를 단순 중앙값 차이 검정으로 해석하지 않습니다.",
            ),
        )
    if "dunn_holm_after_significant" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="dunn_holm_after_significant",
                severity="info",
                message="overall 검정이 유의한 경우에만 Dunn 사후검정과 Holm 보정을 수행했습니다.",
            ),
        )
    if "posthoc_skipped_overall_not_significant" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="posthoc_skipped_overall_not_significant",
                severity="info",
                message="overall 검정이 유의하지 않아 Dunn 사후검정을 실행하지 않았습니다.",
            ),
        )
    if "kruskal_wallis_ties_detected" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="kruskal_wallis_ties_detected",
                severity="warning",
                message="동률 값이 있어 tie correction과 rank 해석을 함께 확인해야 합니다.",
            ),
        )
    if "missing_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="missing_values_excluded",
                severity="warning",
                message="반응 또는 그룹 결측 행은 complete-case 정책으로 제외했습니다.",
            ),
        )
    if "non_numeric_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="non_numeric_values_excluded",
                severity="warning",
                message="반응 값 중 숫자로 해석할 수 없는 값은 제외했습니다.",
            ),
        )
    if "constant_group" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="constant_group",
                severity="warning",
                message="하나 이상의 그룹에서 반응 값이 모두 동일합니다.",
            ),
        )
    if "small_group_size" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="small_group_size",
                severity="info",
                message="그룹 표본 수가 작아 rank 기반 근사와 설계를 함께 확인하세요.",
            ),
        )
    if "group_size_imbalance" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="group_size_imbalance",
                severity="info",
                message="그룹 크기 불균형이 큽니다. 설계와 영향점을 함께 확인하세요.",
            ),
        )
    return warnings


def _run_one_way_anova_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="일원분산분석 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column, group_column = _selected_one_way_anova_columns(
        context,
        request.options,
    )
    alpha = _one_way_anova_alpha(request.options)
    confidence_level = _one_way_anova_confidence_level(request.options)
    anova_type = _one_way_anova_type(request.options)
    posthoc_method = _one_way_anova_posthoc_method(request.options)
    posthoc_policy = _one_way_anova_posthoc_policy(request.options)
    _one_way_anova_missing_policy(request.options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    result_path: Path | None = None

    try:
        try:
            result = calculate_one_way_anova(
                _iter_rows_for_snapshot(context, row_snapshot),
                response_column,
                group_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                alpha=alpha,
                confidence_level=confidence_level,
                anova_type=anova_type,
                posthoc_method=posthoc_method,
                posthoc_policy=posthoc_policy,
            )
        except OneWayAnovaError as exc:
            raise _one_way_anova_api_error(exc.code) from exc
        warnings = _one_way_anova_warnings(result)
        provenance = AnalysisProvenance(
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            source_schema_hash=context.version.schema_hash,
            filter_snapshot_sha256=str(row_snapshot.payload["filter_snapshot_sha256"]),
            row_snapshot_sha256=row_snapshot.record.sha256,
            row_count_total=context.version.row_count,
            row_count_included=int(row_snapshot.payload["selection"]["row_count_included"]),
            app_version=APP_VERSION,
        )
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=provenance,
            result=result,
        )

        result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = _analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=_analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=[row_snapshot.record],
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        if result_path is not None:
            _remove_file_if_exists(result_path)
        raise
    return envelope


def _selected_one_way_anova_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[OneWayAnovaResponseColumn, OneWayAnovaGroupColumn]:
    response_column_id = options.get("response_column_id")
    group_column_id = options.get("group_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="one_way_anova_response_required",
            message="일원분산분석 반응 컬럼을 선택해야 합니다.",
        )
    if not isinstance(group_column_id, str) or not group_column_id:
        raise ApiError(
            code="one_way_anova_group_required",
            message="일원분산분석 그룹 컬럼을 선택해야 합니다.",
        )
    if response_column_id == group_column_id:
        raise ApiError(
            code="one_way_anova_same_response_and_group",
            message="일원분산분석 반응 컬럼과 그룹 컬럼은 서로 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_column = columns_by_id.get(response_column_id)
    group_column = columns_by_id.get(group_column_id)
    if response_column is None:
        raise ApiError(
            code="one_way_anova_response_column_not_found",
            message="요청한 일원분산분석 반응 컬럼을 찾을 수 없습니다.",
        )
    if group_column is None:
        raise ApiError(
            code="one_way_anova_group_column_not_found",
            message="요청한 일원분산분석 그룹 컬럼을 찾을 수 없습니다.",
        )

    _validate_one_way_anova_response_column(response_column)
    _validate_one_way_anova_group_column(group_column)
    return (
        OneWayAnovaResponseColumn(
            column_id=response_column.column_id,
            column_index=response_column.column_index,
            display_name=response_column.display_name,
            data_type=response_column.data_type,
            measurement_level=response_column.measurement_level,
            role=response_column.role,
            unit=response_column.unit,
        ),
        OneWayAnovaGroupColumn(
            column_id=group_column.column_id,
            column_index=group_column.column_index,
            display_name=group_column.display_name,
            data_type=group_column.data_type,
            measurement_level=group_column.measurement_level,
            role=group_column.role,
            unit=group_column.unit,
        ),
    )


def _validate_one_way_anova_response_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="one_way_anova_response_column_is_id",
            message="ID 컬럼은 일원분산분석 반응 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="one_way_anova_response_column_not_numeric",
            message="일원분산분석 반응 변수는 현재 숫자형 컬럼만 지원합니다.",
        )


def _validate_one_way_anova_group_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="one_way_anova_group_column_is_id",
            message="ID 컬럼은 일원분산분석 그룹 변수로 사용할 수 없습니다.",
        )


def _one_way_anova_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_one_way_anova_alpha",
            message="일원분산분석 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0 or not isfinite(alpha):
        raise ApiError(
            code="invalid_one_way_anova_alpha",
            message="일원분산분석 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _one_way_anova_confidence_level(options: dict[str, Any]) -> float:
    raw_value = options.get("confidence_level", 0.95)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_one_way_anova_confidence_level",
            message="일원분산분석 신뢰수준이 올바르지 않습니다.",
        )
    confidence_level = float(raw_value)
    if confidence_level <= 0.0 or confidence_level >= 1.0 or not isfinite(confidence_level):
        raise ApiError(
            code="invalid_one_way_anova_confidence_level",
            message="일원분산분석 신뢰수준이 허용 범위를 벗어났습니다.",
        )
    return confidence_level


def _one_way_anova_type(options: dict[str, Any]) -> str:
    raw_value = options.get("anova_type", "standard")
    if raw_value != "standard":
        raise ApiError(
            code="invalid_one_way_anova_type",
            message="이번 slice는 표준 일원분산분석만 지원합니다.",
        )
    return str(raw_value)


def _one_way_anova_posthoc_method(options: dict[str, Any]) -> str:
    raw_value = options.get("posthoc_method", "tukey_kramer")
    if raw_value not in {"tukey_kramer", "none"}:
        raise ApiError(
            code="invalid_one_way_anova_posthoc_method",
            message="일원분산분석 사후검정 방식이 올바르지 않습니다.",
        )
    return str(raw_value)


def _one_way_anova_posthoc_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("posthoc_policy", "after_significant")
    if raw_value != "after_significant":
        raise ApiError(
            code="invalid_one_way_anova_posthoc_policy",
            message="일원분산분석 사후검정 정책이 올바르지 않습니다.",
        )
    return str(raw_value)


def _one_way_anova_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="one_way_anova_missing_policy_unsupported",
            message="일원분산분석은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _one_way_anova_api_error(code: str) -> ApiError:
    messages = {
        "invalid_one_way_anova_type": "이번 slice는 표준 일원분산분석만 지원합니다.",
        "invalid_one_way_anova_alpha": "일원분산분석 유의수준이 허용 범위를 벗어났습니다.",
        "invalid_one_way_anova_confidence_level": (
            "일원분산분석 신뢰수준이 허용 범위를 벗어났습니다."
        ),
        "invalid_one_way_anova_posthoc_method": ("일원분산분석 사후검정 방식이 올바르지 않습니다."),
        "invalid_one_way_anova_posthoc_policy": ("일원분산분석 사후검정 정책이 올바르지 않습니다."),
        "one_way_anova_requires_at_least_two_groups": (
            "일원분산분석에는 사용 가능한 그룹이 최소 2개 필요합니다."
        ),
        "one_way_anova_group_n_too_small": (
            "일원분산분석의 각 그룹에는 최소 2개 사용 값이 필요합니다."
        ),
        "one_way_anova_all_values_identical": (
            "전체 반응 값이 모두 동일해 일원분산분석을 계산할 수 없습니다."
        ),
        "one_way_anova_degrees_of_freedom_invalid": ("일원분산분석 자유도가 유효하지 않습니다."),
        "one_way_anova_zero_residual_variance": (
            "잔차 분산이 0이어서 일원분산분석 F 통계량을 계산할 수 없습니다."
        ),
        "one_way_anova_statistic_not_finite": (
            "일원분산분석 통계량 또는 p-value가 유한하지 않습니다."
        ),
        "one_way_anova_posthoc_standard_error_zero": (
            "Tukey-Kramer 사후비교 표준오차가 0이어서 계산할 수 없습니다."
        ),
        "one_way_anova_posthoc_not_finite": ("Tukey-Kramer 사후비교 결과가 유한하지 않습니다."),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "일원분산분석을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _one_way_anova_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "one_way_anova_independence_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_way_anova_independence_assumption",
                severity="info",
                message="독립성은 설계 가정이며 데이터만으로 자동 검증하지 않습니다.",
            ),
        )
    if "one_way_anova_normality_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_way_anova_normality_assumption",
                severity="info",
                message="잔차 정규성은 별도 진단과 설계 맥락으로 확인해야 합니다.",
            ),
        )
    if "one_way_anova_equal_variance_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_way_anova_equal_variance_assumption",
                severity="info",
                message="표준 일원분산분석은 등분산 가정을 사용합니다.",
            ),
        )
    if "one_way_anova_not_auto_switched" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_way_anova_not_auto_switched",
                severity="info",
                message="진단 결과만으로 Welch ANOVA나 비모수 검정으로 자동 전환하지 않습니다.",
            ),
        )
    if "tukey_kramer_after_standard_anova" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="tukey_kramer_after_standard_anova",
                severity="info",
                message="표준 ANOVA가 유의한 경우 Tukey-Kramer 사후비교를 수행했습니다.",
            ),
        )
    if "posthoc_skipped_overall_not_significant" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="posthoc_skipped_overall_not_significant",
                severity="info",
                message="overall ANOVA가 유의하지 않아 사후비교를 실행하지 않았습니다.",
            ),
        )
    if "missing_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="missing_values_excluded",
                severity="warning",
                message="반응 또는 그룹 결측 행은 complete-case 정책으로 제외했습니다.",
            ),
        )
    if "non_numeric_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="non_numeric_values_excluded",
                severity="warning",
                message="반응 값 중 숫자로 해석할 수 없는 값은 제외했습니다.",
            ),
        )
    if "constant_group" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="constant_group",
                severity="warning",
                message="하나 이상의 그룹에서 반응 값이 모두 동일합니다.",
            ),
        )
    if "small_group_size" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="small_group_size",
                severity="info",
                message="그룹 표본 수가 작아 ANOVA 가정과 영향점을 함께 확인하세요.",
            ),
        )
    if "group_size_imbalance" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="group_size_imbalance",
                severity="info",
                message="그룹 크기 불균형이 큽니다. 설계와 영향점을 함께 확인하세요.",
            ),
        )
    if "two_group_anova_equivalent_to_t_test" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="two_group_anova_equivalent_to_t_test",
                severity="info",
                message="그룹이 2개인 ANOVA는 표준 2표본 t-검정과 동등한 구조입니다.",
            ),
        )
    return warnings


def _run_one_proportion_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="1-비율 검정 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column = _selected_one_proportion_column(context, request.options)
    event_level = _one_proportion_event_level(request.options)
    null_proportion = _one_proportion_null_proportion(request.options)
    alpha = _one_proportion_alpha(request.options)
    confidence_level = _one_proportion_confidence_level(request.options)
    alternative = _one_proportion_alternative(request.options)
    ci_method = _one_proportion_ci_method(request.options)
    _one_proportion_missing_policy(request.options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    result_path: Path | None = None

    try:
        try:
            result = calculate_one_proportion(
                _iter_rows_for_snapshot(context, row_snapshot),
                response_column,
                event_level=event_level,
                null_proportion=null_proportion,
                alpha=alpha,
                confidence_level=confidence_level,
                alternative=alternative,
                ci_method=ci_method,
            )
        except OneProportionError as exc:
            raise _one_proportion_api_error(exc.code) from exc
        warnings = _one_proportion_warnings(result)
        provenance = AnalysisProvenance(
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            source_schema_hash=context.version.schema_hash,
            filter_snapshot_sha256=str(row_snapshot.payload["filter_snapshot_sha256"]),
            row_snapshot_sha256=row_snapshot.record.sha256,
            row_count_total=context.version.row_count,
            row_count_included=int(row_snapshot.payload["selection"]["row_count_included"]),
            app_version=APP_VERSION,
        )
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=provenance,
            result=result,
        )

        result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = _analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=_analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=[row_snapshot.record],
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        if result_path is not None:
            _remove_file_if_exists(result_path)
        raise
    return envelope


def _selected_one_proportion_column(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> OneProportionColumn:
    response_column_id = options.get("response_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="one_proportion_response_required",
            message="1-비율 검정 반응 컬럼을 선택해야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_column = columns_by_id.get(response_column_id)
    if response_column is None:
        raise ApiError(
            code="one_proportion_response_column_not_found",
            message="요청한 1-비율 검정 반응 컬럼을 찾을 수 없습니다.",
        )
    if response_column.role == "id" or response_column.measurement_level == "id":
        raise ApiError(
            code="one_proportion_response_column_is_id",
            message="ID 컬럼은 1-비율 검정 반응 변수로 사용할 수 없습니다.",
        )
    return OneProportionColumn(
        column_id=response_column.column_id,
        column_index=response_column.column_index,
        display_name=response_column.display_name,
        data_type=response_column.data_type,
        measurement_level=response_column.measurement_level,
        role=response_column.role,
        unit=response_column.unit,
    )


def _one_proportion_event_level(options: dict[str, Any]) -> str:
    raw_value = options.get("event_level")
    if not isinstance(raw_value, str) or raw_value.strip() == "":
        raise ApiError(
            code="one_proportion_event_level_required",
            message="1-비율 검정 사건 수준을 입력해야 합니다.",
        )
    return raw_value.strip()


def _one_proportion_null_proportion(options: dict[str, Any]) -> float:
    raw_value = options.get("null_proportion", 0.5)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_one_proportion_null_proportion",
            message="1-비율 검정 기준 비율이 올바르지 않습니다.",
        )
    null_proportion = float(raw_value)
    if null_proportion <= 0.0 or null_proportion >= 1.0 or not isfinite(null_proportion):
        raise ApiError(
            code="invalid_one_proportion_null_proportion",
            message="1-비율 검정 기준 비율이 허용 범위를 벗어났습니다.",
        )
    return null_proportion


def _one_proportion_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_one_proportion_alpha",
            message="1-비율 검정 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0:
        raise ApiError(
            code="invalid_one_proportion_alpha",
            message="1-비율 검정 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _one_proportion_confidence_level(options: dict[str, Any]) -> float:
    raw_value = options.get("confidence_level", 0.95)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_one_proportion_confidence_level",
            message="1-비율 검정 신뢰수준이 올바르지 않습니다.",
        )
    confidence_level = float(raw_value)
    if confidence_level <= 0.0 or confidence_level >= 1.0:
        raise ApiError(
            code="invalid_one_proportion_confidence_level",
            message="1-비율 검정 신뢰수준이 허용 범위를 벗어났습니다.",
        )
    return confidence_level


def _one_proportion_alternative(options: dict[str, Any]) -> str:
    raw_value = options.get("alternative", "two_sided")
    if raw_value not in {"two_sided", "greater", "less"}:
        raise ApiError(
            code="invalid_one_proportion_alternative",
            message="1-비율 검정 대립가설이 올바르지 않습니다.",
        )
    return str(raw_value)


def _one_proportion_ci_method(options: dict[str, Any]) -> str:
    raw_value = options.get("ci_method", "wilson")
    if raw_value not in {"wilson", "clopper_pearson"}:
        raise ApiError(
            code="invalid_one_proportion_ci_method",
            message="1-비율 검정 신뢰구간 방식이 올바르지 않습니다.",
        )
    return str(raw_value)


def _one_proportion_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="one_proportion_missing_policy_unsupported",
            message="1-비율 검정은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _one_proportion_api_error(code: str) -> ApiError:
    messages = {
        "one_proportion_n_too_small": "1-비율 검정에는 최소 1개 사용 값이 필요합니다.",
        "one_proportion_requires_binary_column": (
            "1-비율 검정 반응 컬럼은 사건 수준과 하나의 비사건 수준만 포함해야 합니다."
        ),
        "one_proportion_p_value_not_finite": ("1-비율 검정 p-value가 유한하지 않습니다."),
        "one_proportion_ci_not_finite": ("1-비율 검정 신뢰구간이 유한하지 않습니다."),
        "invalid_one_proportion_alternative": "1-비율 검정 대립가설이 올바르지 않습니다.",
        "invalid_one_proportion_ci_method": "1-비율 검정 신뢰구간 방식이 올바르지 않습니다.",
        "invalid_one_proportion_null_proportion": (
            "1-비율 검정 기준 비율이 허용 범위를 벗어났습니다."
        ),
        "invalid_one_proportion_alpha": "1-비율 검정 유의수준이 허용 범위를 벗어났습니다.",
        "invalid_one_proportion_confidence_level": (
            "1-비율 검정 신뢰수준이 허용 범위를 벗어났습니다."
        ),
        "one_proportion_event_level_required": "1-비율 검정 사건 수준을 입력해야 합니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "1-비율 검정을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _one_proportion_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "one_proportion_binary_design_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_proportion_binary_design_assumption",
                severity="info",
                message=(
                    "이 컬럼이 분석 목적상 이진 사건/비사건 변수라는 가정은 "
                    "사용자가 확인해야 합니다."
                ),
            ),
        )
    if "one_proportion_exact_binomial" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="one_proportion_exact_binomial",
                severity="info",
                message="p-value는 exact binomial test로 계산했습니다.",
            ),
        )
    if "missing_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="missing_values_excluded",
                severity="warning",
                message="반응 결측 행은 complete-case 정책으로 제외했습니다.",
            ),
        )
    if "event_level_not_observed" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="event_level_not_observed",
                severity="warning",
                message="선택한 사건 수준이 사용 데이터에서 관측되지 않았습니다.",
            ),
        )
    if "all_events_or_no_events" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="all_events_or_no_events",
                severity="info",
                message="사용 데이터가 모두 사건 또는 모두 비사건입니다.",
            ),
        )
    if "single_observed_level" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="single_observed_level",
                severity="info",
                message="사용 데이터에서 하나의 수준만 관측되었습니다.",
            ),
        )
    return warnings


def _run_two_proportion_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="2-비율 검정 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column, group_column = _selected_two_proportion_columns(
        context,
        request.options,
    )
    event_level = _two_proportion_event_level(request.options)
    alpha = _two_proportion_alpha(request.options)
    confidence_level = _two_proportion_confidence_level(request.options)
    alternative = _two_proportion_alternative(request.options)
    _two_proportion_missing_policy(request.options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    result_path: Path | None = None

    try:
        try:
            result = calculate_two_proportion(
                _iter_rows_for_snapshot(context, row_snapshot),
                response_column,
                group_column,
                event_level=event_level,
                alpha=alpha,
                confidence_level=confidence_level,
                alternative=alternative,
            )
        except TwoProportionError as exc:
            raise _two_proportion_api_error(exc.code) from exc
        warnings = _two_proportion_warnings(result)
        provenance = AnalysisProvenance(
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            source_schema_hash=context.version.schema_hash,
            filter_snapshot_sha256=str(row_snapshot.payload["filter_snapshot_sha256"]),
            row_snapshot_sha256=row_snapshot.record.sha256,
            row_count_total=context.version.row_count,
            row_count_included=int(row_snapshot.payload["selection"]["row_count_included"]),
            app_version=APP_VERSION,
        )
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=provenance,
            result=result,
        )

        result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = _analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=_analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=[row_snapshot.record],
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        if result_path is not None:
            _remove_file_if_exists(result_path)
        raise
    return envelope


def _selected_two_proportion_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[TwoProportionResponseColumn, TwoProportionGroupColumn]:
    response_column_id = options.get("response_column_id")
    group_column_id = options.get("group_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="two_proportion_response_required",
            message="2-비율 검정 반응 컬럼을 선택해야 합니다.",
        )
    if not isinstance(group_column_id, str) or not group_column_id:
        raise ApiError(
            code="two_proportion_group_required",
            message="2-비율 검정 그룹 컬럼을 선택해야 합니다.",
        )
    if response_column_id == group_column_id:
        raise ApiError(
            code="two_proportion_same_response_and_group",
            message="2-비율 검정 반응 컬럼과 그룹 컬럼은 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_column = columns_by_id.get(response_column_id)
    group_column = columns_by_id.get(group_column_id)
    if response_column is None:
        raise ApiError(
            code="two_proportion_response_column_not_found",
            message="요청한 2-비율 검정 반응 컬럼을 찾을 수 없습니다.",
        )
    if group_column is None:
        raise ApiError(
            code="two_proportion_group_column_not_found",
            message="요청한 2-비율 검정 그룹 컬럼을 찾을 수 없습니다.",
        )
    if response_column.role == "id" or response_column.measurement_level == "id":
        raise ApiError(
            code="two_proportion_response_column_is_id",
            message="ID 컬럼은 2-비율 검정 반응 변수로 사용할 수 없습니다.",
        )
    if group_column.role == "id" or group_column.measurement_level == "id":
        raise ApiError(
            code="two_proportion_group_column_is_id",
            message="ID 컬럼은 2-비율 검정 그룹 변수로 사용할 수 없습니다.",
        )
    return (
        TwoProportionResponseColumn(
            column_id=response_column.column_id,
            column_index=response_column.column_index,
            display_name=response_column.display_name,
            data_type=response_column.data_type,
            measurement_level=response_column.measurement_level,
            role=response_column.role,
            unit=response_column.unit,
        ),
        TwoProportionGroupColumn(
            column_id=group_column.column_id,
            column_index=group_column.column_index,
            display_name=group_column.display_name,
            data_type=group_column.data_type,
            measurement_level=group_column.measurement_level,
            role=group_column.role,
            unit=group_column.unit,
        ),
    )


def _two_proportion_event_level(options: dict[str, Any]) -> str:
    raw_value = options.get("event_level")
    if not isinstance(raw_value, str) or raw_value.strip() == "":
        raise ApiError(
            code="two_proportion_event_level_required",
            message="2-비율 검정 사건 수준을 입력해야 합니다.",
        )
    return raw_value.strip()


def _two_proportion_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_two_proportion_alpha",
            message="2-비율 검정 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0 or not isfinite(alpha):
        raise ApiError(
            code="invalid_two_proportion_alpha",
            message="2-비율 검정 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _two_proportion_confidence_level(options: dict[str, Any]) -> float:
    raw_value = options.get("confidence_level", 0.95)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_two_proportion_confidence_level",
            message="2-비율 검정 신뢰수준이 올바르지 않습니다.",
        )
    confidence_level = float(raw_value)
    if confidence_level <= 0.0 or confidence_level >= 1.0 or not isfinite(confidence_level):
        raise ApiError(
            code="invalid_two_proportion_confidence_level",
            message="2-비율 검정 신뢰수준이 허용 범위를 벗어났습니다.",
        )
    return confidence_level


def _two_proportion_alternative(options: dict[str, Any]) -> str:
    raw_value = options.get("alternative", "two_sided")
    if raw_value not in {"two_sided", "greater", "less"}:
        raise ApiError(
            code="invalid_two_proportion_alternative",
            message="2-비율 검정 대립가설이 올바르지 않습니다.",
        )
    return str(raw_value)


def _two_proportion_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="two_proportion_missing_policy_unsupported",
            message="2-비율 검정은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _two_proportion_api_error(code: str) -> ApiError:
    messages = {
        "invalid_two_proportion_alternative": "2-비율 검정 대립가설이 올바르지 않습니다.",
        "invalid_two_proportion_alpha": "2-비율 검정 유의수준이 허용 범위를 벗어났습니다.",
        "invalid_two_proportion_confidence_level": (
            "2-비율 검정 신뢰수준이 허용 범위를 벗어났습니다."
        ),
        "two_proportion_event_level_required": "2-비율 검정 사건 수준을 입력해야 합니다.",
        "two_proportion_requires_exactly_two_groups": (
            "2-비율 검정에는 정확히 2개의 사용 가능한 그룹이 필요합니다."
        ),
        "two_proportion_group_n_too_small": (
            "2-비율 검정의 각 그룹에는 최소 1개 사용 값이 필요합니다."
        ),
        "two_proportion_requires_binary_response": (
            "2-비율 검정 반응 컬럼은 사건 수준과 하나의 비사건 수준만 포함해야 합니다."
        ),
        "two_proportion_p_value_not_finite": "2-비율 검정 p-value가 유한하지 않습니다.",
        "two_proportion_ci_not_finite": "2-비율 검정 신뢰구간이 유한하지 않습니다.",
        "two_proportion_effect_ci_not_finite": (
            "2-비율 검정 효과크기 신뢰구간이 유한하지 않습니다."
        ),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "2-비율 검정을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _two_proportion_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "two_proportion_binary_design_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="two_proportion_binary_design_assumption",
                severity="info",
                message="반응 컬럼이 이진 사건/비사건 변수라는 가정은 사용자가 확인해야 합니다.",
            ),
        )
    if "two_proportion_independence_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="two_proportion_independence_assumption",
                severity="info",
                message="두 그룹 관측치의 독립성은 설계 가정이며 자동 검증하지 않습니다.",
            ),
        )
    if "two_proportion_fisher_exact" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="two_proportion_fisher_exact",
                severity="info",
                message="p-value는 2x2 Fisher exact test로 계산했습니다.",
            ),
        )
    if "small_expected_counts" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="small_expected_counts",
                severity="info",
                message="기대도수가 작은 셀이 있어 exact test 결과와 설계를 함께 확인하세요.",
            ),
        )
    if "missing_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="missing_values_excluded",
                severity="warning",
                message="반응 또는 그룹 결측 행은 complete-case 정책으로 제외했습니다.",
            ),
        )
    if "zero_cell_effect_ci_unavailable" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="zero_cell_effect_ci_unavailable",
                severity="warning",
                message="0 cell이 있어 일부 효과크기 CI는 계산하지 않았습니다.",
            ),
        )
    if "event_level_not_observed" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="event_level_not_observed",
                severity="warning",
                message="선택한 사건 수준이 사용 데이터에서 관측되지 않았습니다.",
            ),
        )
    if "all_events_or_no_events" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="all_events_or_no_events",
                severity="info",
                message="사용 데이터가 모두 사건 또는 모두 비사건입니다.",
            ),
        )
    if "group_size_imbalance" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="group_size_imbalance",
                severity="info",
                message="그룹 크기 불균형이 큽니다. 설계를 함께 확인하세요.",
            ),
        )
    return warnings


def _run_chi_square_association_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="카이제곱 독립성 검정 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    row_column, column_column = _selected_chi_square_association_columns(
        context,
        request.options,
    )
    alpha = _chi_square_association_alpha(request.options)
    _chi_square_association_missing_policy(request.options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    result_path: Path | None = None

    try:
        try:
            result = calculate_chi_square_association(
                _iter_rows_for_snapshot(context, row_snapshot),
                row_column,
                column_column,
                alpha=alpha,
            )
        except ChiSquareAssociationError as exc:
            raise _chi_square_association_api_error(exc.code) from exc
        warnings = _chi_square_association_warnings(result)
        provenance = AnalysisProvenance(
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            source_schema_hash=context.version.schema_hash,
            filter_snapshot_sha256=str(row_snapshot.payload["filter_snapshot_sha256"]),
            row_snapshot_sha256=row_snapshot.record.sha256,
            row_count_total=context.version.row_count,
            row_count_included=int(row_snapshot.payload["selection"]["row_count_included"]),
            app_version=APP_VERSION,
        )
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=provenance,
            result=result,
        )

        result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = _analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=_analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=[row_snapshot.record],
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        if result_path is not None:
            _remove_file_if_exists(result_path)
        raise
    return envelope


def _selected_chi_square_association_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[ChiSquareAssociationColumn, ChiSquareAssociationColumn]:
    row_column_id = options.get("row_column_id")
    column_column_id = options.get("column_column_id")
    if not isinstance(row_column_id, str) or not row_column_id:
        raise ApiError(
            code="chi_square_row_column_required",
            message="카이제곱 독립성 검정 행 변수를 선택해야 합니다.",
        )
    if not isinstance(column_column_id, str) or not column_column_id:
        raise ApiError(
            code="chi_square_column_column_required",
            message="카이제곱 독립성 검정 열 변수를 선택해야 합니다.",
        )
    if row_column_id == column_column_id:
        raise ApiError(
            code="chi_square_same_row_and_column",
            message="카이제곱 독립성 검정 행 변수와 열 변수는 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    row_column = columns_by_id.get(row_column_id)
    column_column = columns_by_id.get(column_column_id)
    if row_column is None:
        raise ApiError(
            code="chi_square_row_column_not_found",
            message="요청한 카이제곱 독립성 검정 행 변수를 찾을 수 없습니다.",
        )
    if column_column is None:
        raise ApiError(
            code="chi_square_column_column_not_found",
            message="요청한 카이제곱 독립성 검정 열 변수를 찾을 수 없습니다.",
        )
    _validate_chi_square_association_column(row_column, axis="row")
    _validate_chi_square_association_column(column_column, axis="column")
    return (
        ChiSquareAssociationColumn(
            column_id=row_column.column_id,
            column_index=row_column.column_index,
            display_name=row_column.display_name,
            data_type=row_column.data_type,
            measurement_level=row_column.measurement_level,
            role=row_column.role,
            unit=row_column.unit,
        ),
        ChiSquareAssociationColumn(
            column_id=column_column.column_id,
            column_index=column_column.column_index,
            display_name=column_column.display_name,
            data_type=column_column.data_type,
            measurement_level=column_column.measurement_level,
            role=column_column.role,
            unit=column_column.unit,
        ),
    )


def _validate_chi_square_association_column(
    column: DatasetColumnRecord,
    *,
    axis: str,
) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code=f"chi_square_{axis}_column_is_id",
            message="ID 컬럼은 카이제곱 독립성 검정 변수로 사용할 수 없습니다.",
        )


def _chi_square_association_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_chi_square_alpha",
            message="카이제곱 독립성 검정 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0 or not isfinite(alpha):
        raise ApiError(
            code="invalid_chi_square_alpha",
            message="카이제곱 독립성 검정 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _chi_square_association_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="chi_square_missing_policy_unsupported",
            message="카이제곱 독립성 검정은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _chi_square_association_api_error(code: str) -> ApiError:
    messages = {
        "invalid_chi_square_alpha": ("카이제곱 독립성 검정 유의수준이 허용 범위를 벗어났습니다."),
        "chi_square_requires_at_least_two_row_levels": (
            "카이제곱 독립성 검정에는 행 변수의 사용 가능한 수준이 최소 2개 필요합니다."
        ),
        "chi_square_requires_at_least_two_column_levels": (
            "카이제곱 독립성 검정에는 열 변수의 사용 가능한 수준이 최소 2개 필요합니다."
        ),
        "chi_square_too_many_row_levels": (
            "카이제곱 독립성 검정 행 변수 수준 수가 허용 범위를 초과했습니다."
        ),
        "chi_square_too_many_column_levels": (
            "카이제곱 독립성 검정 열 변수 수준 수가 허용 범위를 초과했습니다."
        ),
        "chi_square_statistic_not_finite": (
            "카이제곱 독립성 검정 통계량 또는 p-value가 유한하지 않습니다."
        ),
    }
    return ApiError(
        code=code,
        message=messages.get(code, "카이제곱 독립성 검정을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _chi_square_association_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "chi_square_independence_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="chi_square_independence_assumption",
                severity="info",
                message="관측치 독립성은 설계 가정이며 데이터만으로 자동 검증하지 않습니다.",
            ),
        )
    if "pearson_chi_square_no_continuity_correction" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="pearson_chi_square_no_continuity_correction",
                severity="info",
                message="Pearson 카이제곱 검정은 연속성 보정 없이 계산했습니다.",
            ),
        )
    if "missing_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="missing_values_excluded",
                severity="warning",
                message="행 또는 열 변수 결측 행은 complete-case 정책으로 제외했습니다.",
            ),
        )
    if "small_expected_counts" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="small_expected_counts",
                severity="warning",
                message="기대도수가 작은 셀이 있어 카이제곱 근사 해석에 주의가 필요합니다.",
            ),
        )
    if "two_by_two_table" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="two_by_two_table",
                severity="info",
                message="2x2 분할표입니다. Fisher exact 검정 필요 여부를 함께 확인하세요.",
            ),
        )
    if "fisher_exact_recommended_for_sparse_2x2" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="fisher_exact_recommended_for_sparse_2x2",
                severity="warning",
                message=(
                    "희소한 2x2 분할표입니다. 이번 slice는 Fisher exact로 자동 전환하지 않고 "
                    "권장 대안으로만 기록합니다."
                ),
            ),
        )
    if "large_contingency_table" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="large_contingency_table",
                severity="info",
                message="분할표 셀 수가 많아 residual 해석과 표시 비용을 함께 확인하세요.",
            ),
        )
    return warnings


def _run_pearson_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="Pearson 상관 분석 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    x_column, y_column = _selected_pearson_columns(context, request.options)
    alpha = _pearson_alpha(request.options)
    confidence_level = _pearson_confidence_level(request.options)
    _pearson_missing_policy(request.options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    result_path: Path | None = None

    try:
        try:
            result = calculate_pearson_correlation(
                _iter_rows_for_snapshot(context, row_snapshot),
                x_column,
                y_column,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                alpha=alpha,
                confidence_level=confidence_level,
            )
        except PearsonCorrelationError as exc:
            raise _pearson_api_error(exc.code) from exc
        warnings = _pearson_warnings(result)
        provenance = AnalysisProvenance(
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            source_schema_hash=context.version.schema_hash,
            filter_snapshot_sha256=str(row_snapshot.payload["filter_snapshot_sha256"]),
            row_snapshot_sha256=row_snapshot.record.sha256,
            row_count_total=context.version.row_count,
            row_count_included=int(row_snapshot.payload["selection"]["row_count_included"]),
            app_version=APP_VERSION,
        )
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=provenance,
            result=result,
        )

        result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = _analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=_analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=[row_snapshot.record],
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        if result_path is not None:
            _remove_file_if_exists(result_path)
        raise
    return envelope


def _selected_pearson_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[PearsonCorrelationColumn, PearsonCorrelationColumn]:
    x_column_id = options.get("x_column_id")
    y_column_id = options.get("y_column_id")
    if not isinstance(x_column_id, str) or not x_column_id:
        raise ApiError(
            code="pearson_x_column_required",
            message="Pearson 상관 분석 X 컬럼을 선택해야 합니다.",
        )
    if not isinstance(y_column_id, str) or not y_column_id:
        raise ApiError(
            code="pearson_y_column_required",
            message="Pearson 상관 분석 Y 컬럼을 선택해야 합니다.",
        )
    if x_column_id == y_column_id:
        raise ApiError(
            code="pearson_same_x_and_y_column",
            message="Pearson 상관 분석 X/Y 컬럼은 서로 달라야 합니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    x_column = columns_by_id.get(x_column_id)
    y_column = columns_by_id.get(y_column_id)
    if x_column is None:
        raise ApiError(
            code="pearson_x_column_not_found",
            message="요청한 Pearson 상관 분석 X 컬럼을 찾을 수 없습니다.",
        )
    if y_column is None:
        raise ApiError(
            code="pearson_y_column_not_found",
            message="요청한 Pearson 상관 분석 Y 컬럼을 찾을 수 없습니다.",
        )
    _validate_pearson_column(x_column, axis="x")
    _validate_pearson_column(y_column, axis="y")
    return (
        PearsonCorrelationColumn(
            column_id=x_column.column_id,
            column_index=x_column.column_index,
            display_name=x_column.display_name,
            data_type=x_column.data_type,
            measurement_level=x_column.measurement_level,
            role=x_column.role,
            unit=x_column.unit,
        ),
        PearsonCorrelationColumn(
            column_id=y_column.column_id,
            column_index=y_column.column_index,
            display_name=y_column.display_name,
            data_type=y_column.data_type,
            measurement_level=y_column.measurement_level,
            role=y_column.role,
            unit=y_column.unit,
        ),
    )


def _validate_pearson_column(
    column: DatasetColumnRecord,
    *,
    axis: str,
) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code=f"pearson_{axis}_column_is_id",
            message="ID 컬럼은 Pearson 상관 분석 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code=f"pearson_{axis}_column_not_numeric",
            message="Pearson 상관 분석 변수는 현재 숫자형 컬럼만 지원합니다.",
        )


def _pearson_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_pearson_alpha",
            message="Pearson 상관 분석 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0 or not isfinite(alpha):
        raise ApiError(
            code="invalid_pearson_alpha",
            message="Pearson 상관 분석 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _pearson_confidence_level(options: dict[str, Any]) -> float:
    raw_value = options.get("confidence_level", 0.95)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_pearson_confidence_level",
            message="Pearson 상관 분석 신뢰수준이 올바르지 않습니다.",
        )
    confidence_level = float(raw_value)
    if confidence_level <= 0.0 or confidence_level >= 1.0 or not isfinite(confidence_level):
        raise ApiError(
            code="invalid_pearson_confidence_level",
            message="Pearson 상관 분석 신뢰수준이 허용 범위를 벗어났습니다.",
        )
    return confidence_level


def _pearson_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="pearson_missing_policy_unsupported",
            message="Pearson 상관 분석은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _pearson_api_error(code: str) -> ApiError:
    messages = {
        "invalid_pearson_alpha": "Pearson 상관 분석 유의수준이 허용 범위를 벗어났습니다.",
        "invalid_pearson_confidence_level": (
            "Pearson 상관 분석 신뢰수준이 허용 범위를 벗어났습니다."
        ),
        "pearson_n_too_small": "Pearson 상관 분석에는 complete-case 수치 쌍이 최소 4개 필요합니다.",
        "pearson_x_constant": "X 컬럼의 사용 값이 모두 같아 Pearson 상관을 계산할 수 없습니다.",
        "pearson_y_constant": "Y 컬럼의 사용 값이 모두 같아 Pearson 상관을 계산할 수 없습니다.",
        "pearson_result_not_finite": "Pearson 상관 분석 결과가 유한하지 않습니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "Pearson 상관 분석을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _pearson_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    result_warning_codes = result.get("warnings")
    if not isinstance(result_warning_codes, list):
        return warnings
    if "pearson_correlation_not_causation" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="pearson_correlation_not_causation",
                severity="info",
                message="상관은 인과를 의미하지 않습니다. 설계와 도메인 근거를 별도로 확인하세요.",
            ),
        )
    if "pearson_linear_relationship_assumption" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="pearson_linear_relationship_assumption",
                severity="info",
                message=(
                    "Pearson 상관은 선형 관계 요약입니다. 비선형 패턴은 별도 진단이 " "필요합니다."
                ),
            ),
        )
    if "pearson_outlier_sensitive" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="pearson_outlier_sensitive",
                severity="info",
                message=(
                    "Pearson 상관은 이상값에 민감합니다. 산점도와 영향점 후보를 함께 " "확인하세요."
                ),
            ),
        )
    if "missing_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="missing_values_excluded",
                severity="warning",
                message="X 또는 Y 결측 행은 complete-case 정책으로 제외했습니다.",
            ),
        )
    if "non_numeric_values_excluded" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="non_numeric_values_excluded",
                severity="warning",
                message="X 또는 Y 값 중 숫자로 해석할 수 없는 값은 제외했습니다.",
            ),
        )
    if "pearson_perfect_sample_correlation_ci_unavailable" in result_warning_codes:
        warnings.append(
            AnalysisWarning(
                code="pearson_perfect_sample_correlation_ci_unavailable",
                severity="warning",
                message="표본 상관이 완전하여 Fisher z 신뢰구간을 계산하지 않았습니다.",
            ),
        )
    return warnings


def _run_xy_correlation_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="X-Y 상관행렬 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    x_columns, y_columns = _selected_xy_correlation_columns(context, request.options)
    alpha = _xy_correlation_alpha(request.options)
    confidence_level = _xy_correlation_confidence_level(request.options)
    _xy_correlation_missing_policy(request.options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    result_path: Path | None = None

    try:
        try:
            result = calculate_xy_correlation(
                _iter_rows_for_snapshot(context, row_snapshot),
                x_columns,
                y_columns,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                alpha=alpha,
                confidence_level=confidence_level,
            )
        except XyCorrelationError as exc:
            raise _xy_correlation_api_error(exc.code) from exc
        warnings = _xy_correlation_warnings(result)
        provenance = AnalysisProvenance(
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            source_schema_hash=context.version.schema_hash,
            filter_snapshot_sha256=str(row_snapshot.payload["filter_snapshot_sha256"]),
            row_snapshot_sha256=row_snapshot.record.sha256,
            row_count_total=context.version.row_count,
            row_count_included=int(row_snapshot.payload["selection"]["row_count_included"]),
            app_version=APP_VERSION,
        )
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=provenance,
            result=result,
        )

        result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = _analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=_analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=[row_snapshot.record],
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        if result_path is not None:
            _remove_file_if_exists(result_path)
        raise
    return envelope


def _selected_xy_correlation_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[list[XyCorrelationColumn], list[XyCorrelationColumn]]:
    x_column_ids = _column_id_list(
        options.get("x_column_ids"),
        required_code="xy_correlation_x_columns_required",
        invalid_code="invalid_xy_correlation_x_columns",
        duplicate_code="duplicate_xy_correlation_x_column",
        max_count=MAX_XY_CORRELATION_X_COLUMNS,
        too_many_code="too_many_xy_correlation_x_columns",
    )
    y_column_ids = _column_id_list(
        options.get("y_column_ids"),
        required_code="xy_correlation_y_columns_required",
        invalid_code="invalid_xy_correlation_y_columns",
        duplicate_code="duplicate_xy_correlation_y_column",
        max_count=MAX_XY_CORRELATION_Y_COLUMNS,
        too_many_code="too_many_xy_correlation_y_columns",
    )

    columns_by_id = {column.column_id: column for column in context.columns}
    x_columns = [
        _xy_correlation_column(
            columns_by_id,
            column_id,
            axis="x",
        )
        for column_id in x_column_ids
    ]
    y_columns = [
        _xy_correlation_column(
            columns_by_id,
            column_id,
            axis="y",
        )
        for column_id in y_column_ids
    ]
    return (x_columns, y_columns)


def _column_id_list(
    value: object,
    *,
    required_code: str,
    invalid_code: str,
    duplicate_code: str,
    max_count: int,
    too_many_code: str,
) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ApiError(
            code=required_code,
            message="분석에 사용할 컬럼을 하나 이상 선택해야 합니다.",
        )
    if len(value) > max_count:
        raise ApiError(
            code=too_many_code,
            message="한 번에 요청한 X-Y 상관행렬 컬럼 수가 허용 범위를 초과했습니다.",
        )

    column_ids: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item:
            raise ApiError(
                code=invalid_code,
                message="컬럼 ID 목록이 올바르지 않습니다.",
            )
        if item in seen:
            raise ApiError(
                code=duplicate_code,
                message="컬럼 ID가 중복되었습니다.",
            )
        seen.add(item)
        column_ids.append(item)
    return column_ids


def _xy_correlation_column(
    columns_by_id: dict[str, DatasetColumnRecord],
    column_id: str,
    *,
    axis: str,
) -> XyCorrelationColumn:
    column = columns_by_id.get(column_id)
    if column is None:
        raise ApiError(
            code=f"xy_correlation_{axis}_column_not_found",
            message="요청한 X-Y 상관행렬 컬럼을 찾을 수 없습니다.",
        )
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code=f"xy_correlation_{axis}_column_is_id",
            message="ID 컬럼은 X-Y 상관행렬 변수로 사용할 수 없습니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code=f"xy_correlation_{axis}_column_not_numeric",
            message="X-Y 상관행렬 변수는 현재 숫자형 컬럼만 지원합니다.",
        )
    return XyCorrelationColumn(
        column_id=column.column_id,
        column_index=column.column_index,
        display_name=column.display_name,
        data_type=column.data_type,
        measurement_level=column.measurement_level,
        role=column.role,
        unit=column.unit,
    )


def _xy_correlation_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_xy_correlation_alpha",
            message="X-Y 상관행렬 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0 or not isfinite(alpha):
        raise ApiError(
            code="invalid_xy_correlation_alpha",
            message="X-Y 상관행렬 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _xy_correlation_confidence_level(options: dict[str, Any]) -> float:
    raw_value = options.get("confidence_level", 0.95)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_xy_correlation_confidence_level",
            message="X-Y 상관행렬 신뢰수준이 올바르지 않습니다.",
        )
    confidence_level = float(raw_value)
    if confidence_level <= 0.0 or confidence_level >= 1.0 or not isfinite(confidence_level):
        raise ApiError(
            code="invalid_xy_correlation_confidence_level",
            message="X-Y 상관행렬 신뢰수준이 허용 범위를 벗어났습니다.",
        )
    return confidence_level


def _xy_correlation_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "pairwise_complete_case")
    if raw_value != "pairwise_complete_case":
        raise ApiError(
            code="xy_correlation_missing_policy_unsupported",
            message="X-Y 상관행렬은 현재 pairwise complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _xy_correlation_api_error(code: str) -> ApiError:
    messages = {
        "invalid_xy_correlation_alpha": "X-Y 상관행렬 유의수준이 허용 범위를 벗어났습니다.",
        "invalid_xy_correlation_confidence_level": (
            "X-Y 상관행렬 신뢰수준이 허용 범위를 벗어났습니다."
        ),
        "xy_correlation_columns_required": "X-Y 상관행렬에는 X/Y 컬럼이 필요합니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "X-Y 상관행렬을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _xy_correlation_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warning_codes = result.get("warnings")
    if not isinstance(warning_codes, list):
        return []

    messages = {
        "xy_correlation_not_causation": (
            "상관은 인과를 의미하지 않습니다. 설계와 도메인 근거를 별도로 확인하세요."
        ),
        "xy_correlation_linear_relationship_assumption": (
            "Pearson 상관은 선형 관계 요약입니다. 비선형 패턴은 별도 진단이 필요합니다."
        ),
        "xy_correlation_outlier_sensitive": (
            "Pearson 상관은 이상값에 민감합니다. 산점도와 영향점 후보를 함께 확인하세요."
        ),
        "xy_correlation_pair_failed": (
            "일부 X/Y 조합은 표본 부족, 상수열, 비유한 결과 때문에 r/p 값을 만들지 않았습니다."
        ),
        "xy_correlation_pairwise_n_varies": (
            "pairwise complete-case 처리로 X/Y 조합마다 사용 N이 다를 수 있습니다."
        ),
        "xy_correlation_overlapping_x_y_columns": (
            "X 변수 집합과 Y 변수 집합에 같은 컬럼이 포함되어 자기상관 셀이 생길 수 있습니다."
        ),
        "missing_values_excluded": "결측 행은 해당 X/Y 조합에서 제외했습니다.",
        "non_numeric_values_excluded": "숫자로 해석할 수 없는 값은 해당 X/Y 조합에서 제외했습니다.",
        "xy_correlation_perfect_sample_correlation_ci_unavailable": (
            "표본 상관이 완전한 셀은 Fisher z 신뢰구간을 계산하지 않았습니다."
        ),
    }
    severities: dict[str, Literal["info", "warning", "error"]] = {
        "xy_correlation_not_causation": "info",
        "xy_correlation_linear_relationship_assumption": "info",
        "xy_correlation_outlier_sensitive": "info",
        "xy_correlation_overlapping_x_y_columns": "info",
    }
    warnings: list[AnalysisWarning] = []
    for code in warning_codes:
        if not isinstance(code, str):
            continue
        message = messages.get(code)
        if message is None:
            continue
        severity: Literal["info", "warning", "error"] = severities.get(code, "warning")
        warnings.append(
            AnalysisWarning(
                code=code,
                severity=severity,
                message=message,
            ),
        )
    return warnings


def _run_linear_model_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="회귀모형 적합에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    response_column, predictor_columns = _selected_linear_model_columns(context, request.options)
    alpha = _linear_model_alpha(request.options)
    confidence_level = _linear_model_confidence_level(request.options)
    quadratic_terms = _linear_model_quadratic_terms(request.options, predictor_columns)
    interaction_terms = _linear_model_interaction_terms(request.options, predictor_columns)
    _linear_model_missing_policy(request.options)
    _linear_model_include_intercept(request.options)
    _linear_model_covariance_type(request.options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    result_path: Path | None = None
    manifest_path: Path | None = None

    try:
        try:
            result = calculate_linear_model(
                _iter_rows_for_snapshot(context, row_snapshot),
                response_column,
                predictor_columns,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                alpha=alpha,
                confidence_level=confidence_level,
                quadratic_terms=quadratic_terms,
                interaction_terms=interaction_terms,
            )
        except LinearModelError as exc:
            raise _linear_model_api_error(exc.code) from exc
        warnings = _linear_model_warnings(result)
        model_id = uuid4()
        manifest_relative_path = _regression_model_manifest_relative_path(
            str(analysis_id),
            str(model_id),
        )
        manifest_payload = _linear_model_manifest_payload(
            model_id=str(model_id),
            analysis_id=str(analysis_id),
            context=context,
            request=request,
            result=result,
            row_snapshot=row_snapshot,
            created_at=completed_at,
        )
        manifest_bytes = _canonical_json_bytes(manifest_payload)
        manifest_path = settings.workspace_root / manifest_relative_path
        atomic_write_bytes(manifest_path, manifest_bytes)
        manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
        result_payload = dict(result)
        result_payload.pop("prediction_basis", None)
        result_payload["model_manifest"] = {
            "model_id": str(model_id),
            "manifest_schema_version": REGRESSION_MODEL_MANIFEST_SCHEMA_VERSION,
            "manifest_sha256": manifest_sha256,
        }
        provenance = AnalysisProvenance(
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            source_schema_hash=context.version.schema_hash,
            filter_snapshot_sha256=str(row_snapshot.payload["filter_snapshot_sha256"]),
            row_snapshot_sha256=row_snapshot.record.sha256,
            row_count_total=context.version.row_count,
            row_count_included=int(row_snapshot.payload["selection"]["row_count_included"]),
            app_version=APP_VERSION,
        )
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=provenance,
            result=result_payload,
        )

        result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = _analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        model_artifact = AnalysisArtifactRecord(
            artifact_id=str(uuid4()),
            analysis_id=str(analysis_id),
            kind=REGRESSION_MODEL_ARTIFACT_KIND,
            path=manifest_relative_path.as_posix(),
            sha256=manifest_sha256,
            media_type=REGRESSION_MODEL_MEDIA_TYPE,
            created_at=completed_at,
        )
        insert_analysis_run_record_with_artifacts_and_regression_model(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=_analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=[row_snapshot.record, model_artifact],
            regression_model=RegressionModelRecord(
                model_id=str(model_id),
                analysis_id=str(analysis_id),
                dataset_version_id=str(request.dataset_version_id),
                method_id=request.method_id,
                method_version=request.method_version,
                manifest_path=manifest_relative_path.as_posix(),
                manifest_sha256=manifest_sha256,
                schema_hash=context.version.schema_hash,
                created_at=completed_at,
                app_version=APP_VERSION,
            ),
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        if manifest_path is not None:
            _remove_file_if_exists(manifest_path)
        if result_path is not None:
            _remove_file_if_exists(result_path)
        raise
    return envelope


def _selected_linear_model_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> tuple[LinearModelColumn, list[LinearModelColumn]]:
    response_column_id = options.get("response_column_id")
    if not isinstance(response_column_id, str) or not response_column_id:
        raise ApiError(
            code="linear_model_response_column_required",
            message="회귀모형 반응 컬럼을 선택해야 합니다.",
        )
    predictor_column_ids = _linear_model_predictor_ids(options.get("predictor_column_ids"))
    if response_column_id in predictor_column_ids:
        raise ApiError(
            code="linear_model_response_predictor_overlap",
            message="회귀모형 반응 컬럼은 예측변수에 동시에 포함할 수 없습니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    response_record = columns_by_id.get(response_column_id)
    if response_record is None:
        raise ApiError(
            code="linear_model_response_column_not_found",
            message="요청한 회귀모형 반응 컬럼을 찾을 수 없습니다.",
        )
    _validate_linear_model_column(response_record, role="response")

    predictor_columns: list[LinearModelColumn] = []
    for predictor_column_id in predictor_column_ids:
        predictor_record = columns_by_id.get(predictor_column_id)
        if predictor_record is None:
            raise ApiError(
                code="linear_model_predictor_column_not_found",
                message="요청한 회귀모형 예측 컬럼을 찾을 수 없습니다.",
            )
        _validate_linear_model_column(predictor_record, role="predictor")
        predictor_columns.append(_linear_model_column(predictor_record))

    return (_linear_model_column(response_record), predictor_columns)


def _linear_model_predictor_ids(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ApiError(
            code="linear_model_predictors_required",
            message="회귀모형 예측 컬럼을 하나 이상 선택해야 합니다.",
        )
    if len(value) > MAX_LINEAR_MODEL_PREDICTORS:
        raise ApiError(
            code="too_many_linear_model_predictors",
            message="한 번에 요청한 회귀모형 예측 컬럼 수가 허용 범위를 초과했습니다.",
        )

    predictor_ids: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item:
            raise ApiError(
                code="invalid_linear_model_predictors",
                message="회귀모형 예측 컬럼 ID 목록이 올바르지 않습니다.",
            )
        if item in seen:
            raise ApiError(
                code="duplicate_linear_model_predictor",
                message="회귀모형 예측 컬럼 ID가 중복되었습니다.",
            )
        seen.add(item)
        predictor_ids.append(item)
    return predictor_ids


def _validate_linear_model_column(
    column: DatasetColumnRecord,
    *,
    role: str,
) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code=f"linear_model_{role}_column_is_id",
            message="ID 컬럼은 회귀모형 변수로 사용할 수 없습니다.",
        )
    if role == "response" and column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code=f"linear_model_{role}_column_not_numeric",
            message="회귀모형 반응 변수는 숫자형 컬럼이어야 합니다.",
        )
    if role == "predictor" and not _linear_model_predictor_supported(column):
        raise ApiError(
            code="linear_model_predictor_column_unsupported_type",
            message="회귀모형 예측변수는 숫자형 또는 범주형 factor 컬럼만 지원합니다.",
        )


def _linear_model_predictor_supported(column: DatasetColumnRecord) -> bool:
    if column.data_type in NUMERIC_DATA_TYPES and column.measurement_level not in {
        "nominal",
        "binary",
        "ordinal",
    }:
        return column.role != "factor"
    return column.data_type != "datetime" and (
        column.data_type in {"text", "boolean"}
        or column.measurement_level in {"nominal", "binary", "ordinal"}
        or column.role == "factor"
    )


def _linear_model_column(column: DatasetColumnRecord) -> LinearModelColumn:
    return LinearModelColumn(
        column_id=column.column_id,
        column_index=column.column_index,
        display_name=column.display_name,
        data_type=column.data_type,
        measurement_level=column.measurement_level,
        role=column.role,
        unit=column.unit,
    )


def _linear_model_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_linear_model_alpha",
            message="회귀모형 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0 or not isfinite(alpha):
        raise ApiError(
            code="invalid_linear_model_alpha",
            message="회귀모형 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _linear_model_confidence_level(options: dict[str, Any]) -> float:
    raw_value = options.get("confidence_level", 0.95)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_linear_model_confidence_level",
            message="회귀모형 신뢰수준이 올바르지 않습니다.",
        )
    confidence_level = float(raw_value)
    if confidence_level <= 0.0 or confidence_level >= 1.0 or not isfinite(confidence_level):
        raise ApiError(
            code="invalid_linear_model_confidence_level",
            message="회귀모형 신뢰수준이 허용 범위를 벗어났습니다.",
        )
    return confidence_level


def _linear_model_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "complete_case")
    if raw_value != "complete_case":
        raise ApiError(
            code="linear_model_missing_policy_unsupported",
            message="회귀모형은 현재 complete-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _linear_model_include_intercept(options: dict[str, Any]) -> bool:
    raw_value = options.get("include_intercept", True)
    if raw_value is not True:
        raise ApiError(
            code="linear_model_no_intercept_unsupported",
            message="이번 회귀모형 slice는 intercept 포함 OLS만 지원합니다.",
        )
    return True


def _linear_model_covariance_type(options: dict[str, Any]) -> str:
    raw_value = options.get("covariance_type", "standard")
    if raw_value != "standard":
        raise ApiError(
            code="linear_model_covariance_type_unsupported",
            message="이번 회귀모형 slice는 standard covariance만 지원합니다.",
        )
    return raw_value


def _linear_model_quadratic_terms(
    options: dict[str, Any],
    predictor_columns: Sequence[LinearModelColumn],
) -> list[str]:
    raw_value = options.get("quadratic_terms", [])
    if raw_value is None:
        return []
    if not isinstance(raw_value, list):
        raise ApiError(
            code="invalid_linear_model_quadratic_terms",
            message="회귀모형 2차항 목록이 올바르지 않습니다.",
        )
    selected_columns = {column.column_id: column for column in predictor_columns}
    terms: list[str] = []
    seen: set[str] = set()
    for item in raw_value:
        if not isinstance(item, str) or not item:
            raise ApiError(
                code="invalid_linear_model_quadratic_terms",
                message="회귀모형 2차항 목록이 올바르지 않습니다.",
            )
        if item in seen:
            raise ApiError(
                code="duplicate_linear_model_quadratic_term",
                message="회귀모형 2차항이 중복되었습니다.",
            )
        column = selected_columns.get(item)
        if column is None:
            raise ApiError(
                code="linear_model_term_predictor_not_selected",
                message="2차항은 선택된 예측변수에서만 만들 수 있습니다.",
            )
        if not _linear_model_numeric_predictor(column):
            raise ApiError(
                code="linear_model_term_requires_numeric_predictor",
                message="2차항은 숫자형 예측변수에서만 만들 수 있습니다.",
            )
        seen.add(item)
        terms.append(item)
    return terms


def _linear_model_interaction_terms(
    options: dict[str, Any],
    predictor_columns: Sequence[LinearModelColumn],
) -> list[tuple[str, str]]:
    raw_value = options.get("interaction_terms", [])
    if raw_value is None:
        return []
    if not isinstance(raw_value, list):
        raise ApiError(
            code="invalid_linear_model_interaction_terms",
            message="회귀모형 상호작용 항 목록이 올바르지 않습니다.",
        )
    selected_columns = {column.column_id: column for column in predictor_columns}
    predictor_order = {column.column_id: index for index, column in enumerate(predictor_columns)}
    terms: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in raw_value:
        if not isinstance(item, dict):
            raise ApiError(
                code="invalid_linear_model_interaction_terms",
                message="회귀모형 상호작용 항 목록이 올바르지 않습니다.",
            )
        left_column_id = item.get("left_column_id")
        right_column_id = item.get("right_column_id")
        if (
            not isinstance(left_column_id, str)
            or not left_column_id
            or not isinstance(right_column_id, str)
            or not right_column_id
        ):
            raise ApiError(
                code="invalid_linear_model_interaction_terms",
                message="회귀모형 상호작용 항 목록이 올바르지 않습니다.",
            )
        if left_column_id == right_column_id:
            raise ApiError(
                code="linear_model_interaction_same_predictor",
                message="상호작용 항은 서로 다른 두 예측변수로만 만들 수 있습니다.",
            )
        seen_key = tuple(sorted((left_column_id, right_column_id)))
        if len(seen_key) != 2:
            raise ApiError(
                code="invalid_linear_model_interaction_terms",
                message="회귀모형 상호작용 항 목록이 올바르지 않습니다.",
            )
        typed_seen_key = (seen_key[0], seen_key[1])
        if typed_seen_key in seen:
            raise ApiError(
                code="duplicate_linear_model_interaction_term",
                message="회귀모형 상호작용 항이 중복되었습니다.",
            )
        if predictor_order.get(left_column_id, 10**9) <= predictor_order.get(
            right_column_id,
            10**9,
        ):
            ordered = (left_column_id, right_column_id)
        else:
            ordered = (right_column_id, left_column_id)
        left_column = selected_columns.get(ordered[0])
        right_column = selected_columns.get(ordered[1])
        if left_column is None or right_column is None:
            raise ApiError(
                code="linear_model_term_predictor_not_selected",
                message="상호작용 항은 선택된 예측변수에서만 만들 수 있습니다.",
            )
        if not _linear_model_numeric_predictor(left_column) or not _linear_model_numeric_predictor(
            right_column,
        ):
            raise ApiError(
                code="linear_model_term_requires_numeric_predictor",
                message="이번 slice의 상호작용 항은 숫자형 예측변수끼리만 지원합니다.",
            )
        seen.add(typed_seen_key)
        terms.append((ordered[0], ordered[1]))
    return terms


def _linear_model_numeric_predictor(column: LinearModelColumn) -> bool:
    return (
        column.data_type in NUMERIC_DATA_TYPES
        and column.measurement_level not in {"nominal", "binary", "ordinal"}
        and column.role != "factor"
    )


def _linear_model_api_error(code: str) -> ApiError:
    messages = {
        "invalid_linear_model_alpha": "회귀모형 유의수준이 허용 범위를 벗어났습니다.",
        "invalid_linear_model_confidence_level": "회귀모형 신뢰수준이 허용 범위를 벗어났습니다.",
        "linear_model_predictors_required": "회귀모형 예측 컬럼을 하나 이상 선택해야 합니다.",
        "linear_model_residual_df_too_small": (
            "회귀모형에는 예측변수 수보다 충분히 많은 complete-case 행이 필요합니다."
        ),
        "linear_model_response_constant": (
            "반응 컬럼의 사용 값이 모두 같아 회귀모형을 적합할 수 없습니다."
        ),
        "linear_model_predictor_constant": (
            "예측 컬럼 중 사용 값이 모두 같은 컬럼이 있어 회귀모형을 적합할 수 없습니다."
        ),
        "linear_model_factor_single_level": (
            "사용 가능한 범주형 예측변수에 수준이 하나만 남아 회귀모형을 적합할 수 없습니다."
        ),
        "linear_model_factor_too_many_levels": (
            "범주형 예측변수 수준 수가 현재 회귀모형 slice의 허용 범위를 초과했습니다."
        ),
        "linear_model_predictor_column_unsupported_type": (
            "회귀모형 예측변수는 숫자형 또는 범주형 factor 컬럼만 지원합니다."
        ),
        "invalid_linear_model_quadratic_terms": "회귀모형 2차항 목록이 올바르지 않습니다.",
        "duplicate_linear_model_quadratic_term": "회귀모형 2차항이 중복되었습니다.",
        "invalid_linear_model_interaction_terms": "회귀모형 상호작용 항 목록이 올바르지 않습니다.",
        "duplicate_linear_model_interaction_term": "회귀모형 상호작용 항이 중복되었습니다.",
        "linear_model_interaction_same_predictor": (
            "상호작용 항은 서로 다른 두 예측변수로만 만들 수 있습니다."
        ),
        "linear_model_term_predictor_not_selected": (
            "추가 회귀 항은 선택된 예측변수에서만 만들 수 있습니다."
        ),
        "linear_model_term_requires_numeric_predictor": (
            "이번 slice의 2차항과 상호작용 항은 숫자형 예측변수만 지원합니다."
        ),
        "linear_model_quadratic_term_constant": (
            "2차항 값이 모두 같아 회귀모형을 적합할 수 없습니다."
        ),
        "linear_model_interaction_term_constant": (
            "상호작용 항 값이 모두 같아 회귀모형을 적합할 수 없습니다."
        ),
        "linear_model_design_rank_deficient": (
            "회귀 설계행렬이 rank deficient입니다. "
            "중복되거나 완전히 선형 종속인 예측변수를 제거하세요."
        ),
        "linear_model_residual_variance_zero": (
            "잔차 분산이 0이어서 계수 표준오차와 검정을 안정적으로 계산할 수 없습니다."
        ),
        "linear_model_standard_error_not_finite": "회귀 계수 표준오차가 유한하지 않습니다.",
    }
    return ApiError(
        code=code,
        message=messages.get(code, "회귀모형을 계산할 수 없습니다."),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def _linear_model_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warning_codes = result.get("warnings")
    if not isinstance(warning_codes, list):
        return []

    messages = {
        "linear_model_not_causation": (
            "회귀계수는 관찰 데이터만으로 인과 효과를 의미하지 않습니다."
        ),
        "linear_model_linearity_assumption": (
            "OLS는 반응과 예측변수의 평균 관계가 선형이라는 가정을 사용합니다."
        ),
        "linear_model_independence_assumption": (
            "관측 독립성은 소프트웨어가 증명할 수 없으며 연구 설계로 확인해야 합니다."
        ),
        "linear_model_homoscedasticity_assumption": (
            "OLS 계수 검정은 잔차 분산이 일정하다는 가정에 민감할 수 있습니다."
        ),
        "linear_model_residual_normality_assumption": (
            "작은 표본에서는 잔차 정규성 위반이 계수 검정과 CI에 영향을 줄 수 있습니다."
        ),
        "linear_model_outlier_influence_sensitive": (
            "OLS는 이상점과 영향점에 민감합니다. 잔차와 leverage 진단을 함께 확인하세요."
        ),
        "linear_model_categorical_treatment_coding": (
            "범주형 예측변수는 첫 수준을 기준으로 하는 treatment coding으로 적합했습니다."
        ),
        "linear_model_quadratic_terms_selected": (
            "선택한 숫자형 2차항은 탐색적 모형 항이며, 해석에는 설계 근거가 필요합니다."
        ),
        "linear_model_interaction_terms_selected": (
            "선택한 숫자형 상호작용 항은 주효과와 함께 해석해야 합니다."
        ),
        "linear_model_high_condition_number": (
            "condition number가 높아 계수 추정이 다중공선성 또는 스케일 차이에 민감할 수 있습니다."
        ),
        "linear_model_high_vif": ("일부 예측변수의 VIF가 높아 계수 해석이 불안정할 수 있습니다."),
        "linear_model_large_standardized_residual": (
            "표준화 잔차가 큰 행이 있어 이상점 후보를 확인해야 합니다."
        ),
        "linear_model_high_leverage": (
            "leverage가 높은 행이 있어 적합선에 큰 영향을 줄 수 있습니다."
        ),
        "linear_model_high_cooks_distance": (
            "Cook's distance가 큰 행이 있어 영향점 후보를 확인해야 합니다."
        ),
        "missing_values_excluded": "결측 행은 complete-case 정책으로 제외했습니다.",
        "non_numeric_values_excluded": "숫자로 해석할 수 없는 행은 제외했습니다.",
    }
    severities: dict[str, Literal["info", "warning", "error"]] = {
        "linear_model_not_causation": "info",
        "linear_model_linearity_assumption": "info",
        "linear_model_independence_assumption": "info",
        "linear_model_homoscedasticity_assumption": "info",
        "linear_model_residual_normality_assumption": "info",
        "linear_model_outlier_influence_sensitive": "info",
        "linear_model_categorical_treatment_coding": "info",
        "linear_model_quadratic_terms_selected": "info",
        "linear_model_interaction_terms_selected": "info",
    }
    warnings: list[AnalysisWarning] = []
    for code in warning_codes:
        if not isinstance(code, str):
            continue
        message = messages.get(code)
        if message is None:
            continue
        severity: Literal["info", "warning", "error"] = severities.get(code, "warning")
        warnings.append(AnalysisWarning(code=code, severity=severity, message=message))
    return warnings


def _selected_normality_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> list[NormalityColumn]:
    column_ids = options.get("column_ids")
    if not isinstance(column_ids, list) or not column_ids:
        raise ApiError(
            code="normality_columns_required",
            message="정규성을 검정할 컬럼을 하나 이상 선택해야 합니다.",
        )
    if len(column_ids) > MAX_NORMALITY_COLUMNS:
        raise ApiError(
            code="too_many_normality_columns",
            message="한 번에 요청한 정규성 검정 컬럼 수가 허용 범위를 초과했습니다.",
        )
    if any(not isinstance(column_id, str) or not column_id for column_id in column_ids):
        raise ApiError(
            code="invalid_normality_columns",
            message="정규성 검정 컬럼 ID 목록이 올바르지 않습니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    seen: set[str] = set()
    selected: list[NormalityColumn] = []
    for column_id in column_ids:
        if column_id in seen:
            raise ApiError(
                code="duplicate_normality_column",
                message="정규성 검정 컬럼 ID가 중복되었습니다.",
            )
        seen.add(column_id)

        column = columns_by_id.get(column_id)
        if column is None:
            raise ApiError(
                code="normality_column_not_found",
                message="요청한 정규성 검정 컬럼을 찾을 수 없습니다.",
            )
        _validate_normality_column(column)
        selected.append(
            NormalityColumn(
                column_id=column.column_id,
                column_index=column.column_index,
                display_name=column.display_name,
                data_type=column.data_type,
                measurement_level=column.measurement_level,
                role=column.role,
                unit=column.unit,
            ),
        )
    return selected


def _validate_normality_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="normality_column_is_id",
            message="ID 컬럼은 정규성 검정 대상에서 제외해야 합니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="normality_column_not_numeric",
            message="정규성 검정은 현재 숫자형 컬럼만 지원합니다.",
        )


def _reject_normality_grouping(request: AnalysisRunRequest) -> None:
    if "group" in request.roles or request.options.get("group_column_id") is not None:
        raise ApiError(
            code="normality_grouping_not_supported",
            message="이번 정규성 검정 slice는 그룹별 실행을 아직 지원하지 않습니다.",
        )


def _normality_alpha(options: dict[str, Any]) -> float:
    raw_value = options.get("alpha", 0.05)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
        raise ApiError(
            code="invalid_normality_alpha",
            message="정규성 검정 유의수준이 올바르지 않습니다.",
        )
    alpha = float(raw_value)
    if alpha <= 0.0 or alpha >= 1.0:
        raise ApiError(
            code="invalid_normality_alpha",
            message="정규성 검정 유의수준이 허용 범위를 벗어났습니다.",
        )
    return alpha


def _normality_include_qq_points(options: dict[str, Any]) -> bool:
    raw_value = options.get("include_qq_points", True)
    if not isinstance(raw_value, bool):
        raise ApiError(
            code="invalid_normality_include_qq_points",
            message="Q-Q 점 포함 옵션이 올바르지 않습니다.",
        )
    return raw_value


def _normality_qq_point_limit(options: dict[str, Any]) -> int:
    raw_value = options.get("qq_point_limit", 1000)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise ApiError(
            code="invalid_normality_qq_point_limit",
            message="Q-Q 점 제한 값이 올바르지 않습니다.",
        )
    if raw_value < 10 or raw_value > MAX_NORMALITY_QQ_POINT_LIMIT:
        raise ApiError(
            code="invalid_normality_qq_point_limit",
            message="Q-Q 점 제한 값이 허용 범위를 벗어났습니다.",
        )
    return raw_value


def _normality_missing_policy(options: dict[str, Any]) -> str:
    raw_value = options.get("missing_policy", "available_case_by_column")
    if raw_value != "available_case_by_column":
        raise ApiError(
            code="normality_missing_policy_unsupported",
            message="정규성 검정은 현재 컬럼별 available-case 결측 처리만 지원합니다.",
        )
    return raw_value


def _normality_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings = [
        AnalysisWarning(
            code="normality_not_method_switch",
            severity="info",
            message="정규성 검정 결과만으로 후속 모수/비모수 검정을 자동 전환하지 않습니다.",
        ),
    ]
    columns = result.get("columns")
    if not isinstance(columns, list):
        return warnings

    for column in columns:
        if not isinstance(column, dict):
            continue
        column_warnings = column.get("warnings")
        display_name = column.get("display_name")
        if not isinstance(column_warnings, list) or not isinstance(display_name, str):
            continue
        if "non_numeric_values_excluded" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="non_numeric_values_excluded",
                    severity="warning",
                    message=f"{display_name}: 숫자로 해석할 수 없는 값은 제외했습니다.",
                ),
            )
        if "no_numeric_values" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="no_numeric_values",
                    severity="warning",
                    message=f"{display_name}: 사용할 수 있는 숫자 값이 없습니다.",
                ),
            )
        if "normality_insufficient_observations" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="normality_insufficient_observations",
                    severity="warning",
                    message=(
                        f"{display_name}: Shapiro-Wilk/Anderson-Darling에는 "
                        "최소 3개 사용 값이 필요합니다."
                    ),
                ),
            )
        if "constant_column" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="constant_column",
                    severity="warning",
                    message=(
                        f"{display_name}: 모든 사용 값이 동일해 정규성 검정을 "
                        "계산하지 않았습니다."
                    ),
                ),
            )
        if "shapiro_large_n_pvalue_limitation" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="shapiro_large_n_pvalue_limitation",
                    severity="warning",
                    message=(
                        f"{display_name}: Shapiro-Wilk p-value는 N>5000에서 "
                        "정확도 제한이 있습니다."
                    ),
                ),
            )
        if "normality_qq_points_truncated" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="normality_qq_points_truncated",
                    severity="info",
                    message=f"{display_name}: Q-Q 점은 결정적 방식으로 제한했습니다.",
                ),
            )
    return warnings


def _create_row_snapshot_artifact(
    *,
    settings: Settings,
    analysis_id: str,
    context: DatasetRowsContext,
    filter_snapshot: AnalysisFilterSnapshot,
    created_at: str,
) -> _RowSnapshotArtifact:
    filter_snapshot_payload = filter_snapshot.model_dump(mode="json")
    filter_snapshot_sha256 = hashlib.sha256(
        _canonical_json_bytes(filter_snapshot_payload),
    ).hexdigest()
    included_row_indices = _freeze_row_indices(context, filter_snapshot)
    row_count_included = (
        context.version.row_count if included_row_indices is None else len(included_row_indices)
    )
    row_count_excluded = context.version.row_count - row_count_included
    selection: dict[str, Any] = {
        "kind": "all_rows" if included_row_indices is None else "row_ranges",
        "row_count_total": context.version.row_count,
        "row_count_included": row_count_included,
        "row_count_excluded": row_count_excluded,
    }
    if included_row_indices is not None:
        selection["row_ranges"] = _row_ranges(included_row_indices)

    artifact_id = str(uuid4())
    relative_path = _row_snapshot_relative_path(analysis_id)
    payload: dict[str, Any] = {
        "artifact_schema_version": ROW_SNAPSHOT_SCHEMA_VERSION,
        "artifact_kind": ROW_SNAPSHOT_ARTIFACT_KIND,
        "analysis_id": analysis_id,
        "dataset_version_id": context.version.version_id,
        "source_schema_hash": context.version.schema_hash,
        "source_canonical_artifact": {
            "kind": context.canonical_rows_artifact.kind,
            "sha256": context.canonical_rows_artifact.sha256,
            "media_type": context.canonical_rows_artifact.media_type,
            "size_bytes": context.canonical_rows_artifact.size_bytes,
        },
        "filter_snapshot": filter_snapshot_payload,
        "filter_snapshot_sha256": filter_snapshot_sha256,
        "row_identity": {
            "kind": "canonical_row_index",
            "base": 0,
        },
        "selection": selection,
        "created_at": created_at,
    }
    artifact_bytes = _canonical_json_bytes(payload)
    artifact_path = settings.workspace_root / relative_path
    atomic_write_bytes(artifact_path, artifact_bytes)

    return _RowSnapshotArtifact(
        record=AnalysisArtifactRecord(
            artifact_id=artifact_id,
            analysis_id=analysis_id,
            kind=ROW_SNAPSHOT_ARTIFACT_KIND,
            path=relative_path.as_posix(),
            sha256=hashlib.sha256(artifact_bytes).hexdigest(),
            media_type=ROW_SNAPSHOT_MEDIA_TYPE,
            created_at=created_at,
        ),
        relative_path=relative_path,
        payload=payload,
        included_row_indices=included_row_indices,
    )


def _linear_model_manifest_payload(
    *,
    model_id: str,
    analysis_id: str,
    context: DatasetRowsContext,
    request: AnalysisRunRequest,
    result: dict[str, object],
    row_snapshot: _RowSnapshotArtifact,
    created_at: str,
) -> dict[str, Any]:
    return {
        "manifest_schema_version": REGRESSION_MODEL_MANIFEST_SCHEMA_VERSION,
        "model_id": model_id,
        "analysis_id": analysis_id,
        "model_family": "linear_regression_ols",
        "method_id": request.method_id,
        "method_version": request.method_version,
        "app_version": APP_VERSION,
        "created_at": created_at,
        "dataset_version_id": context.version.version_id,
        "source_schema_hash": context.version.schema_hash,
        "source_canonical_artifact_sha256": context.canonical_rows_artifact.sha256,
        "filter_snapshot_sha256": row_snapshot.payload["filter_snapshot_sha256"],
        "row_snapshot_sha256": row_snapshot.record.sha256,
        "row_count_total": context.version.row_count,
        "row_count_included": row_snapshot.payload["selection"]["row_count_included"],
        "linear_model_result_schema_version": result.get("schema_version"),
        "response": result.get("response"),
        "predictors": result.get("predictors"),
        "model_specification": result.get("model_specification"),
        "coefficients": result.get("coefficients"),
        "sample": result.get("sample"),
        "prediction_basis": result.get("prediction_basis"),
        "fit": result.get("fit"),
        "diagnostics_summary": _linear_model_manifest_diagnostics(result.get("diagnostics")),
        "missing_policy": result.get("missing_policy"),
        "alpha": result.get("alpha"),
        "confidence_level": result.get("confidence_level"),
        "package_versions": result.get("package_versions"),
        "limitations": [
            "This manifest stores only app-created JSON model metadata, not pickle or joblib.",
            "Prediction is limited to schema-checked app-created OLS manifests.",
            (
                "Regression coefficients from observational data must not be interpreted "
                "as causal effects."
            ),
        ],
    }


def _linear_model_manifest_diagnostics(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None

    return {
        "rank": value.get("rank"),
        "parameter_count": value.get("parameter_count"),
        "condition_number": value.get("condition_number"),
        "max_vif": value.get("max_vif"),
        "residual_summary": _copy_without_keys(
            value.get("residual_summary"),
            {"large_standardized_row_indices"},
        ),
        "leverage": _copy_without_keys(value.get("leverage"), {"high_row_indices"}),
        "influence": _copy_without_keys(
            value.get("influence"),
            {"high_cooks_distance_row_indices"},
        ),
    }


def _copy_without_keys(value: object, excluded_keys: set[str]) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items() if str(key) not in excluded_keys}


def _freeze_row_indices(
    context: DatasetRowsContext,
    filter_snapshot: AnalysisFilterSnapshot,
) -> tuple[int, ...] | None:
    if not filter_snapshot.conditions:
        return None

    conditions = _parse_filter_conditions(context, filter_snapshot)
    included_row_indices: list[int] = []
    for row_index, row in enumerate(iter_dataset_rows(context)):
        if all(_row_matches_condition(row, condition, context) for condition in conditions):
            included_row_indices.append(row_index)
    return tuple(included_row_indices)


def _parse_filter_conditions(
    context: DatasetRowsContext,
    filter_snapshot: AnalysisFilterSnapshot,
) -> list[_FilterCondition]:
    if filter_snapshot.expression_version != 1:
        raise ApiError(
            code="filter_expression_version_unsupported",
            message="지원하지 않는 필터 표현식 버전입니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    if len(filter_snapshot.conditions) > MAX_FILTER_CONDITIONS:
        raise ApiError(
            code="too_many_filter_conditions",
            message="필터 조건 수가 허용 범위를 초과했습니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    conditions: list[_FilterCondition] = []
    for raw_condition in filter_snapshot.conditions:
        if not isinstance(raw_condition, dict):
            raise _invalid_filter_condition()

        column_id = raw_condition.get("column_id")
        operator = raw_condition.get("operator")
        if not isinstance(column_id, str) or not column_id:
            raise _invalid_filter_condition()
        if not isinstance(operator, str) or operator not in FILTER_OPERATORS:
            raise ApiError(
                code="filter_operator_not_supported",
                message="지원하지 않는 필터 연산자입니다.",
            )

        column = columns_by_id.get(column_id)
        if column is None:
            raise ApiError(
                code="filter_column_not_found",
                message="필터 컬럼을 찾을 수 없습니다.",
            )

        if operator in {"is_missing", "is_not_missing"}:
            conditions.append(_FilterCondition(column=column, operator=operator))
            continue

        if "value" not in raw_condition:
            raise ApiError(
                code="filter_value_required",
                message="필터 조건 값이 필요합니다.",
            )
        value = raw_condition["value"]
        _validate_filter_value(column, operator, value)
        conditions.append(_FilterCondition(column=column, operator=operator, value=value))

    return conditions


def _validate_filter_value(
    column: DatasetColumnRecord,
    operator: str,
    value: object,
) -> None:
    if value is None:
        raise ApiError(
            code="filter_value_invalid",
            message="필터 조건 값이 올바르지 않습니다.",
        )
    if operator in NUMERIC_FILTER_OPERATORS and column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="filter_operator_not_supported_for_column",
            message="이 컬럼에는 요청한 필터 연산자를 사용할 수 없습니다.",
        )
    if column.data_type in NUMERIC_DATA_TYPES:
        _filter_decimal_value(value)
        return
    if not isinstance(value, str) or len(value) > MAX_FILTER_STRING_LENGTH:
        raise ApiError(
            code="filter_value_invalid",
            message="필터 조건 값이 올바르지 않습니다.",
        )


def _row_matches_condition(
    row: list[str | None],
    condition: _FilterCondition,
    context: DatasetRowsContext,
) -> bool:
    value = row[condition.column.column_index] if condition.column.column_index < len(row) else None
    missing = value is None or value.strip() == ""

    if condition.operator == "is_missing":
        return missing
    if condition.operator == "is_not_missing":
        return not missing
    if missing:
        return False
    assert value is not None

    if condition.column.data_type in NUMERIC_DATA_TYPES:
        row_value = _parse_filter_decimal(
            value,
            decimal=context.parsing.decimal,
            thousands=context.parsing.thousands,
        )
        filter_value = _filter_decimal_value(condition.value)
        if row_value is None:
            return False
        return _compare_values(row_value, filter_value, condition.operator)

    string_filter_value = condition.value
    if not isinstance(string_filter_value, str):
        return False
    return _compare_values(value, string_filter_value, condition.operator)


def _iter_rows_for_snapshot(
    context: DatasetRowsContext,
    row_snapshot: _RowSnapshotArtifact,
) -> Iterator[list[str | None]]:
    if row_snapshot.included_row_indices is None:
        yield from iter_dataset_rows(context)
        return

    included = set(row_snapshot.included_row_indices)
    for row_index, row in enumerate(iter_dataset_rows(context)):
        if row_index in included:
            yield row


def _compare_values(left: Any, right: Any, operator: str) -> bool:
    if operator == "eq":
        return left == right
    if operator == "ne":
        return left != right
    if operator == "gt":
        return left > right
    if operator == "gte":
        return left >= right
    if operator == "lt":
        return left < right
    if operator == "lte":
        return left <= right
    return False


def _parse_filter_decimal(
    value: str,
    *,
    decimal: str,
    thousands: str | None,
) -> Decimal | None:
    normalized = value.strip()
    if normalized == "":
        return None
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
    return parsed


def _filter_decimal_value(value: object) -> Decimal:
    if isinstance(value, bool):
        raise ApiError(
            code="filter_value_invalid",
            message="필터 조건 값이 올바르지 않습니다.",
        )
    if not isinstance(value, int | float | str):
        raise ApiError(
            code="filter_value_invalid",
            message="필터 조건 값이 올바르지 않습니다.",
        )
    try:
        parsed = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise ApiError(
            code="filter_value_invalid",
            message="필터 조건 값이 올바르지 않습니다.",
        ) from exc
    if not parsed.is_finite():
        raise ApiError(
            code="filter_value_invalid",
            message="필터 조건 값이 올바르지 않습니다.",
        )
    return parsed


def _row_ranges(row_indices: tuple[int, ...]) -> list[dict[str, int]]:
    if not row_indices:
        return []

    ranges: list[dict[str, int]] = []
    range_start = row_indices[0]
    previous = row_indices[0]
    for row_index in row_indices[1:]:
        if row_index == previous + 1:
            previous = row_index
            continue
        ranges.append({"start": range_start, "end": previous + 1})
        range_start = row_index
        previous = row_index
    ranges.append({"start": range_start, "end": previous + 1})
    return ranges


def _invalid_filter_condition() -> ApiError:
    return ApiError(
        code="invalid_filter_condition",
        message="필터 조건 형식이 올바르지 않습니다.",
    )


def _analysis_config_json(
    request: AnalysisRunRequest,
    row_snapshot: _RowSnapshotArtifact,
) -> str:
    return json.dumps(
        {
            "schema_version": CONFIG_SCHEMA_VERSION,
            "filter_snapshot": request.filter_snapshot.model_dump(mode="json"),
            "filter_snapshot_sha256": row_snapshot.payload["filter_snapshot_sha256"],
            "row_snapshot": {
                "artifact_id": row_snapshot.record.artifact_id,
                "kind": row_snapshot.record.kind,
                "path": row_snapshot.record.path,
                "sha256": row_snapshot.record.sha256,
                "media_type": row_snapshot.record.media_type,
                "row_count_total": row_snapshot.payload["selection"]["row_count_total"],
                "row_count_included": row_snapshot.payload["selection"]["row_count_included"],
            },
            "roles": request.roles,
            "options": request.options,
        },
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


def _analysis_result_relative_path(analysis_id: str) -> Path:
    return Path("workspaces") / "analyses" / analysis_id / "result.json"


def _row_snapshot_relative_path(analysis_id: str) -> Path:
    return Path("workspaces") / "analyses" / analysis_id / "row_snapshot.json"


def _regression_model_manifest_relative_path(analysis_id: str, model_id: str) -> Path:
    return Path("workspaces") / "analyses" / analysis_id / f"model-{model_id}.json"


def _safe_result_path(workspace_root: Path, stored_path: str) -> Path:
    relative_path = Path(stored_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ApiError(
            code="analysis_result_path_invalid",
            message="저장된 분석 결과 메타데이터가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return workspace_root / relative_path


def _remove_file_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return


def _to_response(workspace_root: Path, record: AnalysisRunRecord) -> AnalysisRunStatusResponse:
    config_schema_version = _config_schema_version(record.config_json)
    artifact_count = count_analysis_artifact_records(workspace_root, record.analysis_id)
    return AnalysisRunStatusResponse(
        analysis_id=UUID(record.analysis_id),
        method_id=record.method_id,
        method_version=record.method_version,
        dataset_version_id=None
        if record.dataset_version_id is None
        else UUID(record.dataset_version_id),
        status=AnalysisRunState(record.status),
        config_schema_version=config_schema_version,
        result_available=record.result_path is not None and record.result_sha256 is not None,
        artifact_count=artifact_count,
        stale=record.stale,
        created_at=record.created_at,
        updated_at=record.updated_at,
        completed_at=record.completed_at,
    )


def _config_schema_version(config_json: str) -> int:
    try:
        payload = json.loads(config_json)
    except json.JSONDecodeError as exc:
        raise ApiError(
            code="analysis_run_metadata_invalid",
            message="분석 실행 메타데이터를 읽을 수 없습니다.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc

    if not isinstance(payload, dict):
        raise ApiError(
            code="analysis_run_metadata_invalid",
            message="분석 실행 메타데이터를 읽을 수 없습니다.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, int) or schema_version < 1:
        raise ApiError(
            code="analysis_run_metadata_invalid",
            message="분석 실행 메타데이터를 읽을 수 없습니다.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return schema_version


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
