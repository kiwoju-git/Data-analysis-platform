import csv
import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Final, TextIO
from uuid import UUID, uuid4

from fastapi import status

from app.api.v1.schemas.datasets import (
    ConfirmedParsingOptions,
    DatasetArtifactResponse,
    DatasetColumnConfirmation,
    DatasetColumnDataType,
    DatasetColumnResponse,
    DatasetColumnRole,
    DatasetColumnSchemaUpdate,
    DatasetMeasurementLevel,
    DatasetParsingConfirmationRequest,
    DatasetPreviewRow,
    DatasetRowsPreviewResponse,
    DatasetSchemaResponse,
    DatasetSchemaUpdateRequest,
    DatasetVersionListResponse,
    DatasetVersionResponse,
    DatasetVersionSummary,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.canonical_artifacts import (
    CANONICAL_ROWS_KIND,
    materialize_canonical_dataset_artifacts,
)
from app.services.dataset_rows import (
    DatasetRowsContext,
    get_dataset_rows_context,
    iter_dataset_rows,
    verify_canonical_rows_artifact,
)
from app.services.xlsx_reader import XlsxSheetRow, iter_xlsx_sheet_rows
from app.storage.metadata import (
    DatasetArtifactRecord,
    DatasetColumnRecord,
    DatasetRecord,
    DatasetVersionRecord,
    get_dataset_artifact_record,
    get_dataset_record,
    get_dataset_version_record,
    insert_dataset_version_record,
    list_dataset_column_records,
    list_dataset_version_records,
    update_dataset_schema_records,
)

ALLOWED_TEXT_ENCODINGS: Final = {"utf-8", "utf-8-sig", "cp949"}
ALLOWED_TEXT_DELIMITERS: Final = {",", "\t", ";", "|"}
ALLOWED_DECIMALS: Final = {".", ","}
ALLOWED_THOUSANDS: Final = {",", ".", " ", "'", None}
SUPPORTED_TEXT_CONFIRMATION_FORMATS: Final = {"csv", "tsv", "delimited_text"}
MAX_MISSING_TOKENS: Final = 50
MAX_MISSING_TOKEN_LENGTH: Final = 40


@dataclass
class _ColumnInference:
    has_value: bool = False
    integer: bool = True
    decimal: bool = True
    boolean: bool = True
    datetime: bool = True


@dataclass(frozen=True)
class _ParsedSchema:
    headers: list[str]
    row_count: int
    data_types: list[DatasetColumnDataType]


def confirm_dataset_parsing(
    settings: Settings,
    dataset_id: UUID,
    request: DatasetParsingConfirmationRequest,
) -> DatasetVersionResponse:
    dataset = _get_existing_dataset(settings, dataset_id)
    source_path = _safe_workspace_path(settings.workspace_root, dataset.stored_path)
    _validate_source_file_integrity(source_path, dataset)

    existing_versions = list_dataset_version_records(settings.workspace_root, str(dataset_id))
    if existing_versions:
        raise ApiError(
            code="dataset_already_confirmed",
            message="이미 확정된 데이터셋 버전이 있습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    options = request.parsing
    _validate_confirmation_options(dataset.detected_format, options)

    parsed_schema = _scan_dataset_schema(source_path, options)
    columns = _build_column_records(parsed_schema, request.columns)
    parsing_options_json = _dump_parsing_options(options)

    version = DatasetVersionRecord(
        version_id=str(uuid4()),
        dataset_id=str(dataset_id),
        version_number=1,
        source_sha256=dataset.sha256,
        parsing_options_json=parsing_options_json,
        row_count=parsed_schema.row_count,
        column_count=len(columns),
        schema_hash=_schema_hash(
            source_sha256=dataset.sha256,
            parsing_options_json=parsing_options_json,
            row_count=parsed_schema.row_count,
            columns=columns,
        ),
        created_at=_utc_now(),
    )
    version_columns = [
        DatasetColumnRecord(
            column_id=column.column_id,
            version_id=version.version_id,
            column_index=column.column_index,
            original_name=column.original_name,
            display_name=column.display_name,
            data_type=column.data_type,
            measurement_level=column.measurement_level,
            role=column.role,
            unit=column.unit,
        )
        for column in columns
    ]
    artifact_records = materialize_canonical_dataset_artifacts(
        settings=settings,
        dataset=dataset,
        version=version,
        columns=version_columns,
        parsing=options,
    )
    try:
        insert_dataset_version_record(
            settings.workspace_root,
            version,
            version_columns,
            artifacts=artifact_records,
        )
    except Exception:
        _remove_artifact_files(settings.workspace_root, artifact_records)
        raise

    return dataset_version_response_from_records(
        version,
        version_columns,
        canonical_artifact=_artifact_by_kind(artifact_records, CANONICAL_ROWS_KIND),
    )


def list_dataset_versions(
    settings: Settings,
    dataset_id: UUID,
) -> DatasetVersionListResponse:
    _get_existing_dataset(settings, dataset_id)
    records = list_dataset_version_records(settings.workspace_root, str(dataset_id))
    return DatasetVersionListResponse(
        dataset_id=dataset_id,
        versions=[dataset_version_summary_from_record(record) for record in records],
    )


def get_dataset_version(
    settings: Settings,
    version_id: UUID,
) -> DatasetVersionResponse:
    version = _get_existing_version(settings, version_id)
    columns = list_dataset_column_records(settings.workspace_root, str(version_id))
    canonical_artifact = get_dataset_artifact_record(
        settings.workspace_root,
        str(version_id),
        CANONICAL_ROWS_KIND,
    )
    return dataset_version_response_from_records(version, columns, canonical_artifact)


def get_dataset_schema(
    settings: Settings,
    version_id: UUID,
) -> DatasetSchemaResponse:
    version = _get_existing_version(settings, version_id)
    columns = list_dataset_column_records(settings.workspace_root, str(version_id))
    return dataset_schema_response_from_records(version, columns)


def update_dataset_schema(
    settings: Settings,
    version_id: UUID,
    request: DatasetSchemaUpdateRequest,
) -> DatasetSchemaResponse:
    version = _get_existing_version(settings, version_id)
    current_columns = list_dataset_column_records(settings.workspace_root, str(version_id))
    updated_columns = _apply_schema_updates(current_columns, request)
    if _schema_update_is_noop(current_columns, updated_columns):
        return dataset_schema_response_from_records(version, current_columns)

    schema_hash = _schema_hash_for_records(
        source_sha256=version.source_sha256,
        parsing_options_json=version.parsing_options_json,
        row_count=version.row_count,
        columns=updated_columns,
    )
    update_dataset_schema_records(
        settings.workspace_root,
        str(version_id),
        schema_hash,
        updated_columns,
        stale_updated_at=_utc_now(),
    )
    updated_version = DatasetVersionRecord(
        version_id=version.version_id,
        dataset_id=version.dataset_id,
        version_number=version.version_number,
        source_sha256=version.source_sha256,
        parsing_options_json=version.parsing_options_json,
        row_count=version.row_count,
        column_count=version.column_count,
        schema_hash=schema_hash,
        created_at=version.created_at,
    )
    return dataset_schema_response_from_records(updated_version, updated_columns)


def get_dataset_rows_preview(
    settings: Settings,
    version_id: UUID,
    offset: int,
    limit: int,
) -> DatasetRowsPreviewResponse:
    context = get_dataset_rows_context(settings, version_id)
    verify_canonical_rows_artifact(context)
    rows = _read_canonical_preview_rows(context, offset=offset, limit=limit)
    return DatasetRowsPreviewResponse(
        version_id=version_id,
        offset=offset,
        limit=limit,
        total_rows=context.version.row_count,
        returned_rows=len(rows),
        columns=dataset_column_responses(context.columns),
        rows=rows,
    )


def dataset_version_summary_from_record(record: DatasetVersionRecord) -> DatasetVersionSummary:
    return DatasetVersionSummary(
        version_id=UUID(record.version_id),
        dataset_id=UUID(record.dataset_id),
        version_number=record.version_number,
        row_count=record.row_count,
        column_count=record.column_count,
        schema_hash=record.schema_hash,
        created_at=record.created_at,
    )


def dataset_version_response_from_records(
    version: DatasetVersionRecord,
    columns: list[DatasetColumnRecord],
    canonical_artifact: DatasetArtifactRecord | None = None,
) -> DatasetVersionResponse:
    summary = dataset_version_summary_from_record(version)
    parsing = ConfirmedParsingOptions.model_validate(json.loads(version.parsing_options_json))
    return DatasetVersionResponse(
        **summary.model_dump(),
        source_sha256=version.source_sha256,
        parsing=parsing,
        columns=dataset_column_responses(columns),
        canonical_artifact=dataset_artifact_response_from_record(canonical_artifact),
    )


def dataset_schema_response_from_records(
    version: DatasetVersionRecord,
    columns: list[DatasetColumnRecord],
) -> DatasetSchemaResponse:
    return DatasetSchemaResponse(
        version_id=UUID(version.version_id),
        dataset_id=UUID(version.dataset_id),
        schema_hash=version.schema_hash,
        columns=dataset_column_responses(columns),
    )


def dataset_column_responses(columns: list[DatasetColumnRecord]) -> list[DatasetColumnResponse]:
    return [
        DatasetColumnResponse(
            column_id=UUID(column.column_id),
            version_id=UUID(column.version_id),
            column_index=column.column_index,
            original_name=column.original_name,
            display_name=column.display_name,
            data_type=DatasetColumnDataType(column.data_type),
            measurement_level=DatasetMeasurementLevel(column.measurement_level),
            role=DatasetColumnRole(column.role),
            unit=column.unit,
        )
        for column in columns
    ]


def dataset_artifact_response_from_record(
    artifact: DatasetArtifactRecord | None,
) -> DatasetArtifactResponse | None:
    if artifact is None:
        return None
    return DatasetArtifactResponse(
        artifact_id=UUID(artifact.artifact_id),
        version_id=UUID(artifact.version_id),
        kind=artifact.kind,
        path=artifact.path,
        sha256=artifact.sha256,
        media_type=artifact.media_type,
        size_bytes=artifact.size_bytes,
        created_at=artifact.created_at,
    )


def _artifact_by_kind(
    artifacts: list[DatasetArtifactRecord],
    kind: str,
) -> DatasetArtifactRecord | None:
    for artifact in artifacts:
        if artifact.kind == kind:
            return artifact
    return None


def _get_existing_version(settings: Settings, version_id: UUID) -> DatasetVersionRecord:
    version = get_dataset_version_record(settings.workspace_root, str(version_id))
    if version is None:
        raise ApiError(
            code="dataset_version_not_found",
            message="요청한 데이터셋 버전을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return version


def _apply_schema_updates(
    current_columns: list[DatasetColumnRecord],
    request: DatasetSchemaUpdateRequest,
) -> list[DatasetColumnRecord]:
    current_by_id = {column.column_id: column for column in current_columns}
    updates_by_id: dict[str, DatasetColumnSchemaUpdate] = {}
    for requested_update in request.columns:
        column_id = str(requested_update.column_id)
        if column_id in updates_by_id:
            raise ApiError(
                code="duplicate_column_update",
                message="같은 컬럼에 대한 수정 요청이 중복되었습니다.",
            )
        if column_id not in current_by_id:
            raise ApiError(
                code="column_update_not_found",
                message="수정할 컬럼을 찾을 수 없습니다.",
            )
        updates_by_id[column_id] = requested_update

    updated_columns: list[DatasetColumnRecord] = []
    used_display_names: set[str] = set()
    for column in current_columns:
        column_update = updates_by_id.get(column.column_id)
        if column_update is None:
            display_name = column.display_name
            measurement_level = column.measurement_level
            role = column.role
            unit = column.unit
        else:
            display_name = _display_name_base(column_update.display_name, column.column_index)
            measurement_level = column_update.measurement_level.value
            role = column_update.role.value
            unit = _clean_unit(column_update.unit)

        if display_name in used_display_names:
            raise ApiError(
                code="duplicate_column_display_name",
                message="컬럼 표시명이 중복됩니다.",
            )
        used_display_names.add(display_name)
        updated_columns.append(
            DatasetColumnRecord(
                column_id=column.column_id,
                version_id=column.version_id,
                column_index=column.column_index,
                original_name=column.original_name,
                display_name=display_name,
                data_type=column.data_type,
                measurement_level=measurement_level,
                role=role,
                unit=unit,
            ),
        )
    return updated_columns


def _schema_update_is_noop(
    current_columns: list[DatasetColumnRecord],
    updated_columns: list[DatasetColumnRecord],
) -> bool:
    if len(current_columns) != len(updated_columns):
        return False
    return all(
        current.column_id == updated.column_id
        and current.display_name == updated.display_name
        and current.measurement_level == updated.measurement_level
        and current.role == updated.role
        and current.unit == updated.unit
        for current, updated in zip(current_columns, updated_columns, strict=True)
    )


def _read_canonical_preview_rows(
    context: DatasetRowsContext,
    *,
    offset: int,
    limit: int,
) -> list[DatasetPreviewRow]:
    rows: list[DatasetPreviewRow] = []
    for row_index, values in enumerate(iter_dataset_rows(context)):
        if row_index < offset:
            continue
        if len(rows) >= limit:
            break
        rows.append(DatasetPreviewRow(row_index=row_index, values=values))
    return rows


def _schema_hash_for_records(
    source_sha256: str,
    parsing_options_json: str,
    row_count: int,
    columns: list[DatasetColumnRecord],
) -> str:
    return _schema_hash_from_column_payload(
        source_sha256=source_sha256,
        parsing_options_json=parsing_options_json,
        row_count=row_count,
        columns=[
            {
                "column_index": column.column_index,
                "original_name": column.original_name,
                "display_name": column.display_name,
                "data_type": column.data_type,
                "measurement_level": column.measurement_level,
                "role": column.role,
                "unit": column.unit,
            }
            for column in columns
        ],
    )


def _get_existing_dataset(settings: Settings, dataset_id: UUID) -> DatasetRecord:
    dataset = get_dataset_record(settings.workspace_root, str(dataset_id))
    if dataset is None:
        raise ApiError(
            code="dataset_not_found",
            message="요청한 데이터셋을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return dataset


def _validate_source_file_integrity(path: Path, dataset: DatasetRecord) -> None:
    digest = hashlib.sha256()
    size_bytes = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size_bytes += len(chunk)
            digest.update(chunk)

    if size_bytes != dataset.size_bytes or digest.hexdigest() != dataset.sha256:
        raise ApiError(
            code="source_file_integrity_mismatch",
            message="저장된 원본 업로드 파일이 업로드 시점의 메타데이터와 일치하지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )


def _validate_confirmation_options(
    detected_format: str,
    options: ConfirmedParsingOptions,
) -> None:
    if detected_format == "xlsx":
        if options.kind != "xlsx":
            raise ApiError(
                code="inconsistent_parsing_options",
                message="업로드 형식과 파싱 확정 옵션이 일치하지 않습니다.",
            )
        if options.xlsx_sheet_name is not None and len(options.xlsx_sheet_name.strip()) > 120:
            raise ApiError(
                code="xlsx_sheet_name_too_long",
                message="XLSX 시트명이 허용 길이를 초과했습니다.",
            )
        _validate_header_and_data_rows(options)
        _validate_missing_tokens(options)
        return

    if (
        detected_format not in SUPPORTED_TEXT_CONFIRMATION_FORMATS
        or options.kind != "delimited_text"
    ):
        raise ApiError(
            code="inconsistent_parsing_options",
            message="업로드 형식과 파싱 확정 옵션이 일치하지 않습니다.",
        )

    if options.encoding not in ALLOWED_TEXT_ENCODINGS:
        raise ApiError(
            code="unsupported_text_encoding",
            message="지원하지 않는 텍스트 인코딩입니다.",
        )

    if options.delimiter not in ALLOWED_TEXT_DELIMITERS:
        raise ApiError(
            code="unsupported_delimiter",
            message="지원하지 않는 구분자입니다.",
        )

    if options.quote_char is not None and len(options.quote_char) != 1:
        raise ApiError(
            code="invalid_quote_char",
            message="따옴표 문자는 한 글자여야 합니다.",
        )

    if options.decimal not in ALLOWED_DECIMALS or options.thousands not in ALLOWED_THOUSANDS:
        raise ApiError(
            code="unsupported_number_format",
            message="지원하지 않는 숫자 형식입니다.",
        )

    if options.thousands is not None and options.decimal == options.thousands:
        raise ApiError(
            code="invalid_number_format",
            message="소수점과 천 단위 구분자는 같을 수 없습니다.",
        )

    _validate_header_and_data_rows(options)
    _validate_missing_tokens(options)


def _validate_header_and_data_rows(options: ConfirmedParsingOptions) -> None:
    if options.has_header:
        if options.data_start_row is not None and options.data_start_row != options.header_row + 1:
            raise ApiError(
                code="invalid_data_start_row",
                message="헤더가 있는 데이터의 데이터 시작 행은 헤더 바로 다음 행이어야 합니다.",
            )
    elif options.data_start_row is not None and options.data_start_row < 1:
        raise ApiError(
            code="invalid_data_start_row",
            message="데이터 시작 행은 1 이상이어야 합니다.",
        )


def _validate_missing_tokens(options: ConfirmedParsingOptions) -> None:
    if len(options.missing_tokens) > MAX_MISSING_TOKENS:
        raise ApiError(
            code="too_many_missing_tokens",
            message="결측 토큰 수가 허용 범위를 초과했습니다.",
        )

    if any(len(token) > MAX_MISSING_TOKEN_LENGTH for token in options.missing_tokens):
        raise ApiError(
            code="missing_token_too_long",
            message="결측 토큰 길이가 허용 범위를 초과했습니다.",
        )


def _safe_workspace_path(workspace_root: Path, stored_path: str) -> Path:
    relative_path = Path(stored_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ApiError(
            code="stored_upload_invalid",
            message="저장된 업로드 메타데이터가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    source_path = workspace_root / relative_path
    if not source_path.exists():
        raise ApiError(
            code="stored_upload_missing",
            message="저장된 원본 업로드 파일을 찾을 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return source_path


def _remove_artifact_files(
    workspace_root: Path,
    artifacts: list[DatasetArtifactRecord],
) -> None:
    for artifact in artifacts:
        relative_path = Path(artifact.path)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            continue
        try:
            (workspace_root / relative_path).unlink()
        except FileNotFoundError:
            continue


def _scan_dataset_schema(path: Path, options: ConfirmedParsingOptions) -> _ParsedSchema:
    if options.kind == "delimited_text":
        return _scan_delimited_schema(path, options)
    if options.kind == "xlsx":
        return _scan_xlsx_schema(path, options)
    raise ApiError(
        code="unsupported_parsing_kind",
        message="지원하지 않는 파싱 방식입니다.",
    )


def _scan_delimited_schema(path: Path, options: ConfirmedParsingOptions) -> _ParsedSchema:
    if options.encoding is None or options.delimiter is None:
        raise ApiError(
            code="incomplete_parsing_options",
            message="텍스트 파싱에는 인코딩과 구분자가 필요합니다.",
        )

    try:
        with path.open("r", encoding=options.encoding, newline="") as handle:
            reader = _csv_reader(handle, options)
            first_data_row: list[str] | None = None
            if options.has_header:
                headers = _read_header(reader, options.header_row)
            else:
                first_data_row = _read_data_start_row(reader, _first_data_row_number(options))
                headers = _generated_headers(len(first_data_row))
            inferences = [_ColumnInference() for _ in headers]
            row_count = 0

            if first_data_row is not None:
                row_count += 1
                _observe_row(first_data_row, inferences, options)

            for row in reader:
                if _is_blank_row(row):
                    continue
                row_count += 1
                _observe_row(row, inferences, options)
    except UnicodeDecodeError as exc:
        raise ApiError(
            code="text_decoding_failed",
            message="확정한 인코딩으로 텍스트 파일을 읽을 수 없습니다.",
        ) from exc
    except csv.Error as exc:
        raise ApiError(
            code="text_parsing_failed",
            message="확정한 파싱 옵션으로 텍스트 파일을 읽을 수 없습니다.",
        ) from exc

    if row_count == 0:
        raise ApiError(
            code="no_data_rows",
            message="헤더 아래에 데이터 행이 없습니다.",
        )

    return _ParsedSchema(
        headers=headers,
        row_count=row_count,
        data_types=[_data_type_for_inference(inference) for inference in inferences],
    )


def _scan_xlsx_schema(path: Path, options: ConfirmedParsingOptions) -> _ParsedSchema:
    rows = iter_xlsx_sheet_rows(path, options.xlsx_sheet_name)
    first_data_row: list[str] | None = None
    if options.has_header:
        headers = _read_xlsx_header(rows, options.header_row)
    else:
        first_data_row = _read_xlsx_data_start_row(rows, _first_data_row_number(options))
        headers = _generated_headers(len(first_data_row))

    inferences = [_ColumnInference() for _ in headers]
    row_count = 0
    if first_data_row is not None:
        row_count += 1
        _observe_row(first_data_row, inferences, options)

    first_data_row_number = _first_data_row_number(options)
    for sheet_row in rows:
        if sheet_row.row_number < first_data_row_number:
            continue
        if _is_blank_row(sheet_row.cells):
            continue
        row_count += 1
        _observe_row(sheet_row.cells, inferences, options)

    if row_count == 0:
        raise ApiError(
            code="no_data_rows",
            message="헤더 아래에 데이터 행이 없습니다.",
        )

    return _ParsedSchema(
        headers=headers,
        row_count=row_count,
        data_types=[_data_type_for_inference(inference) for inference in inferences],
    )


def _csv_reader(handle: TextIO, options: ConfirmedParsingOptions) -> Iterator[list[str]]:
    if options.delimiter is None:
        raise ApiError(
            code="incomplete_parsing_options",
            message="텍스트 파싱에는 구분자가 필요합니다.",
        )

    if options.quote_char is None:
        return csv.reader(handle, delimiter=options.delimiter, quoting=csv.QUOTE_NONE)
    return csv.reader(handle, delimiter=options.delimiter, quotechar=options.quote_char)


def _read_header(reader: Iterator[list[str]], header_row: int) -> list[str]:
    header: list[str] | None = None
    for line_number, row in enumerate(reader, start=1):
        if line_number < header_row:
            continue
        header = row
        break

    if header is None:
        raise ApiError(
            code="header_row_not_found",
            message="지정한 헤더 행을 찾을 수 없습니다.",
        )

    if not header or all(cell.strip() == "" for cell in header):
        raise ApiError(
            code="header_row_empty",
            message="헤더 행에 사용할 수 있는 컬럼명이 없습니다.",
        )

    return header


def _read_xlsx_header(reader: Iterator[XlsxSheetRow], header_row: int) -> list[str]:
    header: list[str] | None = None
    for sheet_row in reader:
        if sheet_row.row_number < header_row:
            continue
        if sheet_row.row_number == header_row:
            header = sheet_row.cells
        break

    if header is None:
        raise ApiError(
            code="header_row_not_found",
            message="지정한 헤더 행을 찾을 수 없습니다.",
        )

    if not header or all(cell.strip() == "" for cell in header):
        raise ApiError(
            code="header_row_empty",
            message="헤더 행에 사용할 수 있는 컬럼명이 없습니다.",
        )

    return header


def _read_data_start_row(reader: Iterator[list[str]], data_start_row: int) -> list[str]:
    data_row: list[str] | None = None
    for line_number, row in enumerate(reader, start=1):
        if line_number < data_start_row:
            continue
        data_row = row
        break

    if data_row is None:
        raise ApiError(
            code="data_start_row_not_found",
            message="지정한 데이터 시작 행을 찾을 수 없습니다.",
        )

    if _is_blank_row(data_row):
        raise ApiError(
            code="data_start_row_empty",
            message="데이터 시작 행에 사용할 수 있는 값이 없습니다.",
        )

    return data_row


def _read_xlsx_data_start_row(reader: Iterator[XlsxSheetRow], data_start_row: int) -> list[str]:
    data_row: list[str] | None = None
    for sheet_row in reader:
        if sheet_row.row_number < data_start_row:
            continue
        data_row = sheet_row.cells
        break

    if data_row is None:
        raise ApiError(
            code="data_start_row_not_found",
            message="지정한 데이터 시작 행을 찾을 수 없습니다.",
        )

    if _is_blank_row(data_row):
        raise ApiError(
            code="data_start_row_empty",
            message="데이터 시작 행에 사용할 수 있는 값이 없습니다.",
        )

    return data_row


def _first_data_row_number(options: ConfirmedParsingOptions) -> int:
    if options.has_header:
        if options.data_start_row is not None:
            return options.data_start_row
        return options.header_row + 1
    return options.data_start_row if options.data_start_row is not None else options.header_row


def _generated_headers(column_count: int) -> list[str]:
    if column_count == 0:
        raise ApiError(
            code="data_start_row_empty",
            message="데이터 시작 행에 사용할 수 있는 값이 없습니다.",
        )
    return [f"column_{index + 1}" for index in range(column_count)]


def _is_blank_row(row: list[str]) -> bool:
    return not row or all(cell == "" for cell in row)


def _observe_value(
    inference: _ColumnInference,
    value: str,
    options: ConfirmedParsingOptions,
) -> None:
    if value in options.missing_tokens:
        return

    inference.has_value = True
    stripped = value.strip()
    inference.integer = inference.integer and _is_integer(stripped, options)
    inference.decimal = inference.decimal and _is_decimal(stripped, options)
    inference.boolean = inference.boolean and stripped.lower() in {"true", "false", "yes", "no"}
    inference.datetime = inference.datetime and _is_datetime(stripped)


def _observe_row(
    row: list[str],
    inferences: list[_ColumnInference],
    options: ConfirmedParsingOptions,
) -> None:
    for column_index, inference in enumerate(inferences):
        value = row[column_index] if column_index < len(row) else ""
        _observe_value(inference, value, options)


def _is_integer(value: str, options: ConfirmedParsingOptions) -> bool:
    decimal_value = _parse_decimal(value, options)
    if decimal_value is None:
        return False
    return decimal_value == decimal_value.to_integral_value()


def _is_decimal(value: str, options: ConfirmedParsingOptions) -> bool:
    return _parse_decimal(value, options) is not None


def _parse_decimal(value: str, options: ConfirmedParsingOptions) -> Decimal | None:
    if value == "":
        return None
    normalized = value
    if options.thousands is not None:
        normalized = normalized.replace(options.thousands, "")
    if options.decimal != ".":
        normalized = normalized.replace(options.decimal, ".")

    try:
        parsed = Decimal(normalized)
    except InvalidOperation:
        return None
    if not parsed.is_finite():
        return None
    return parsed


def _is_datetime(value: str) -> bool:
    if value == "":
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _data_type_for_inference(inference: _ColumnInference) -> DatasetColumnDataType:
    if not inference.has_value:
        return DatasetColumnDataType.TEXT
    if inference.integer:
        return DatasetColumnDataType.INTEGER
    if inference.decimal:
        return DatasetColumnDataType.DECIMAL
    if inference.boolean:
        return DatasetColumnDataType.BOOLEAN
    if inference.datetime:
        return DatasetColumnDataType.DATETIME
    return DatasetColumnDataType.TEXT


@dataclass(frozen=True)
class _ColumnDraft:
    column_id: str
    column_index: int
    original_name: str
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


def _build_column_records(
    parsed_schema: _ParsedSchema,
    confirmations: list[DatasetColumnConfirmation],
) -> list[_ColumnDraft]:
    overrides = _column_overrides_by_index(confirmations, len(parsed_schema.headers))
    used_display_names: set[str] = set()
    columns: list[_ColumnDraft] = []

    for index, original_name in enumerate(parsed_schema.headers):
        override = overrides.get(index)
        display_name_base = _display_name_base(original_name, index)
        data_type = parsed_schema.data_types[index]
        measurement_level = DatasetMeasurementLevel.UNKNOWN
        role = DatasetColumnRole.UNSPECIFIED
        unit: str | None = None

        if override is not None:
            if override.display_name is not None:
                display_name_base = _display_name_base(override.display_name, index)
            if override.data_type is not None:
                data_type = override.data_type
            measurement_level = override.measurement_level
            role = override.role
            unit = _clean_unit(override.unit)

        if override is not None and override.display_name is not None:
            display_name = display_name_base
            if display_name in used_display_names:
                raise ApiError(
                    code="duplicate_column_display_name",
                    message="컬럼 표시명이 중복됩니다.",
                )
            used_display_names.add(display_name)
        else:
            display_name = _unique_display_name(display_name_base, used_display_names)

        columns.append(
            _ColumnDraft(
                column_id=str(uuid4()),
                column_index=index,
                original_name=original_name,
                display_name=display_name,
                data_type=data_type.value,
                measurement_level=measurement_level.value,
                role=role.value,
                unit=unit,
            ),
        )

    return columns


def _column_overrides_by_index(
    confirmations: list[DatasetColumnConfirmation],
    column_count: int,
) -> dict[int, DatasetColumnConfirmation]:
    overrides: dict[int, DatasetColumnConfirmation] = {}
    for confirmation in confirmations:
        if confirmation.column_index >= column_count:
            raise ApiError(
                code="column_override_out_of_range",
                message="컬럼 확정 정보가 실제 컬럼 범위를 벗어났습니다.",
            )
        if confirmation.column_index in overrides:
            raise ApiError(
                code="duplicate_column_override",
                message="같은 컬럼에 대한 확정 정보가 중복되었습니다.",
            )
        overrides[confirmation.column_index] = confirmation
    return overrides


def _display_name_base(value: str, index: int) -> str:
    cleaned = "".join(character for character in value.strip() if character.isprintable())
    if not cleaned:
        cleaned = f"column_{index + 1}"
    return cleaned[:120]


def _unique_display_name(base: str, used_names: set[str]) -> str:
    candidate = base
    suffix = 2
    while candidate in used_names:
        candidate = f"{base}_{suffix}"
        suffix += 1
    used_names.add(candidate)
    return candidate


def _clean_unit(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = "".join(character for character in value.strip() if character.isprintable())
    return cleaned[:40] or None


def _dump_parsing_options(options: ConfirmedParsingOptions) -> str:
    return json.dumps(
        options.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _schema_hash(
    source_sha256: str,
    parsing_options_json: str,
    row_count: int,
    columns: list[_ColumnDraft],
) -> str:
    return _schema_hash_from_column_payload(
        source_sha256=source_sha256,
        parsing_options_json=parsing_options_json,
        row_count=row_count,
        columns=[
            {
                "column_index": column.column_index,
                "original_name": column.original_name,
                "display_name": column.display_name,
                "data_type": column.data_type,
                "measurement_level": column.measurement_level,
                "role": column.role,
                "unit": column.unit,
            }
            for column in columns
        ],
    )


def _schema_hash_from_column_payload(
    source_sha256: str,
    parsing_options_json: str,
    row_count: int,
    columns: list[dict[str, object]],
) -> str:
    payload = {
        "columns": columns,
        "parsing": json.loads(parsing_options_json),
        "row_count": row_count,
        "source_sha256": source_sha256,
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
