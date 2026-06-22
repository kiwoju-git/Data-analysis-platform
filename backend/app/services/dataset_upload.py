import hashlib
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile, status

from app.api.v1.schemas.datasets import DatasetUploadResponse
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.parsing_options import build_parsing_suggestion, detect_dataset_format
from app.storage.metadata import DatasetRecord, insert_dataset_record

CHUNK_SIZE = 1024 * 1024
SNIFF_BYTES = 8192


@dataclass(frozen=True)
class StoredUpload:
    dataset_id: str
    safe_filename: str
    relative_path: Path
    absolute_path: Path
    sha256: str
    size_bytes: int


async def create_dataset_from_upload(
    upload_file: UploadFile,
    settings: Settings,
) -> DatasetUploadResponse:
    safe_filename = sanitize_filename(upload_file.filename)
    stored_upload = await _store_upload(upload_file, settings, safe_filename)

    try:
        with stored_upload.absolute_path.open("rb") as handle:
            first_bytes = handle.read(SNIFF_BYTES)

        detected_format = detect_dataset_format(safe_filename, first_bytes)
        parsing, warnings = build_parsing_suggestion(
            detected_format=detected_format,
            first_bytes=first_bytes,
            stored_path=stored_upload.absolute_path,
        )

        insert_dataset_record(
            settings.workspace_root,
            DatasetRecord(
                dataset_id=stored_upload.dataset_id,
                original_filename=safe_filename,
                safe_filename=safe_filename,
                media_type=upload_file.content_type,
                detected_format=detected_format.value,
                stored_path=stored_upload.relative_path.as_posix(),
                sha256=stored_upload.sha256,
                size_bytes=stored_upload.size_bytes,
                created_at=_utc_now(),
            ),
        )
    except Exception:
        _remove_if_exists(stored_upload.absolute_path)
        raise

    return DatasetUploadResponse(
        dataset_id=UUID(stored_upload.dataset_id),
        original_filename=safe_filename,
        size_bytes=stored_upload.size_bytes,
        sha256=stored_upload.sha256,
        detected_format=detected_format,
        parsing=parsing,
        warnings=warnings,
        next_step="confirm_schema",
    )


def sanitize_filename(filename: str | None) -> str:
    raw_name = (filename or "upload").replace("\\", "/").split("/")[-1].strip()
    if raw_name in {"", ".", ".."}:
        raw_name = "upload"

    cleaned = "".join(character for character in raw_name if character.isprintable())
    cleaned = cleaned.strip().strip(".")
    if not cleaned:
        cleaned = "upload"
    return cleaned[:180]


async def _store_upload(
    upload_file: UploadFile,
    settings: Settings,
    safe_filename: str,
) -> StoredUpload:
    dataset_id = str(uuid4())
    relative_path = _raw_upload_relative_path(dataset_id, safe_filename)
    absolute_path = settings.workspace_root / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = _create_temp_path(absolute_path)
    digest = hashlib.sha256()
    size_bytes = 0

    try:
        with temp_path.open("wb") as handle:
            while True:
                chunk = await upload_file.read(CHUNK_SIZE)
                if not chunk:
                    break

                size_bytes += len(chunk)
                if size_bytes > settings.max_upload_bytes:
                    raise ApiError(
                        code="file_too_large",
                        message="업로드 파일 크기가 허용 한도를 초과했습니다.",
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    )

                digest.update(chunk)
                handle.write(chunk)

            handle.flush()
            os.fsync(handle.fileno())

        if size_bytes == 0:
            raise ApiError(
                code="empty_file",
                message="빈 파일은 업로드할 수 없습니다.",
            )

        os.replace(temp_path, absolute_path)
    except Exception:
        _remove_if_exists(temp_path)
        _remove_if_exists(absolute_path)
        raise

    return StoredUpload(
        dataset_id=dataset_id,
        safe_filename=safe_filename,
        relative_path=relative_path,
        absolute_path=absolute_path,
        sha256=digest.hexdigest(),
        size_bytes=size_bytes,
    )


def _raw_upload_relative_path(dataset_id: str, safe_filename: str) -> Path:
    suffix = Path(safe_filename).suffix.lower()
    if suffix not in {".csv", ".tsv", ".txt", ".xlsx"}:
        suffix = ".upload"
    return Path("workspaces") / "datasets" / dataset_id / "raw" / f"source{suffix}"


def _create_temp_path(target_path: Path) -> Path:
    handle = tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{target_path.name}.",
        suffix=".tmp",
        dir=target_path.parent,
        delete=False,
    )
    try:
        return Path(handle.name)
    finally:
        handle.close()


def _remove_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
