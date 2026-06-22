import zipfile
from pathlib import Path

from app.api.v1.schemas.datasets import (
    DatasetFormat,
    DelimiterCandidate,
    ParsingSuggestion,
    UploadWarning,
)
from app.core.errors import ApiError

TEXT_ENCODINGS = ("utf-8-sig", "utf-8", "cp949")
TEXT_DELIMITERS = (
    (",", "comma"),
    ("\t", "tab"),
    (";", "semicolon"),
    ("|", "pipe"),
)
MAX_XLSX_UNCOMPRESSED_BYTES = 500 * 1024 * 1024
MAX_XLSX_COMPRESSION_RATIO = 100


def detect_dataset_format(filename: str, first_bytes: bytes) -> DatasetFormat:
    suffix = Path(filename).suffix.lower()
    is_zip = first_bytes.startswith(b"PK\x03\x04")

    if suffix == ".xlsx":
        if not is_zip:
            raise ApiError(
                code="file_type_mismatch",
                message="파일 확장자와 실제 형식이 일치하지 않습니다.",
            )
        return DatasetFormat.XLSX

    if suffix == ".csv":
        _reject_zip_or_binary(first_bytes)
        return DatasetFormat.CSV

    if suffix == ".tsv":
        _reject_zip_or_binary(first_bytes)
        return DatasetFormat.TSV

    if suffix == ".txt":
        _reject_zip_or_binary(first_bytes)
        return DatasetFormat.DELIMITED_TEXT

    raise ApiError(
        code="unsupported_file_type",
        message="지원하지 않는 파일 형식입니다.",
    )


def build_parsing_suggestion(
    detected_format: DatasetFormat,
    first_bytes: bytes,
    stored_path: Path,
) -> tuple[ParsingSuggestion, list[UploadWarning]]:
    if detected_format == DatasetFormat.XLSX:
        return _build_xlsx_suggestion(stored_path)

    return _build_text_suggestion(detected_format, first_bytes)


def _build_text_suggestion(
    detected_format: DatasetFormat,
    first_bytes: bytes,
) -> tuple[ParsingSuggestion, list[UploadWarning]]:
    warnings: list[UploadWarning] = []
    decoded_text: str | None = None
    encoding_candidates: list[str] = []

    for encoding in TEXT_ENCODINGS:
        try:
            candidate = first_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue

        encoding_candidates.append(encoding)
        if decoded_text is None:
            decoded_text = candidate

    if decoded_text is None:
        raise ApiError(
            code="unsupported_text_encoding",
            message="지원하는 텍스트 인코딩으로 파일을 읽을 수 없습니다.",
        )

    delimiter_candidates = _score_delimiters(decoded_text)
    suggested_delimiter = _choose_delimiter(detected_format, delimiter_candidates)
    if suggested_delimiter is None:
        warnings.append(
            UploadWarning(
                code="delimiter_not_detected",
                message=(
                    "구분자를 자동으로 확정하지 못했습니다. "
                    "사용자가 파싱 옵션을 확인해야 합니다."
                ),
            ),
        )

    if detected_format == DatasetFormat.DELIMITED_TEXT:
        warnings.append(
            UploadWarning(
                code="nonstandard_text_extension",
                message=(
                    "TXT 파일은 구분 텍스트로 처리 후보를 제시합니다. "
                    "파싱 옵션을 확인해야 합니다."
                ),
            ),
        )

    return (
        ParsingSuggestion(
            kind="delimited_text",
            encoding_candidates=encoding_candidates,
            suggested_encoding=encoding_candidates[0],
            delimiter_candidates=delimiter_candidates,
            suggested_delimiter=suggested_delimiter,
            quote_char='"',
            decimal=".",
            thousands=None,
            header_row=1,
            xlsx_requires_sheet_selection=False,
        ),
        warnings,
    )


def _build_xlsx_suggestion(stored_path: Path) -> tuple[ParsingSuggestion, list[UploadWarning]]:
    _validate_xlsx_container(stored_path)
    return (
        ParsingSuggestion(
            kind="xlsx",
            encoding_candidates=[],
            suggested_encoding=None,
            delimiter_candidates=[],
            suggested_delimiter=None,
            quote_char=None,
            decimal=".",
            thousands=None,
            header_row=1,
            xlsx_requires_sheet_selection=True,
        ),
        [
            UploadWarning(
                code="xlsx_sheet_selection_required",
                message="XLSX 파일은 다음 단계에서 시트와 헤더 행을 확인해야 합니다.",
            ),
        ],
    )


def _reject_zip_or_binary(first_bytes: bytes) -> None:
    if first_bytes.startswith(b"PK\x03\x04"):
        raise ApiError(
            code="file_type_mismatch",
            message="파일 확장자와 실제 형식이 일치하지 않습니다.",
        )
    if b"\x00" in first_bytes:
        raise ApiError(
            code="binary_file_rejected",
            message="텍스트 데이터 파일로 확인할 수 없습니다.",
        )


def _score_delimiters(text: str) -> list[DelimiterCandidate]:
    lines = [line for line in text.splitlines()[:20] if line.strip()]
    candidates: list[DelimiterCandidate] = []

    for delimiter, label in TEXT_DELIMITERS:
        score = sum(line.count(delimiter) for line in lines)
        if score > 0:
            candidates.append(
                DelimiterCandidate(
                    delimiter=delimiter,
                    label=label,
                    score=score,
                ),
            )

    return sorted(candidates, key=lambda item: item.score, reverse=True)


def _choose_delimiter(
    detected_format: DatasetFormat,
    candidates: list[DelimiterCandidate],
) -> str | None:
    if detected_format == DatasetFormat.CSV:
        return ","
    if detected_format == DatasetFormat.TSV:
        return "\t"
    if candidates:
        return candidates[0].delimiter
    return None


def _validate_xlsx_container(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = {info.filename for info in infos}
            total_uncompressed = sum(info.file_size for info in infos)
            total_compressed = sum(info.compress_size for info in infos)
    except zipfile.BadZipFile as exc:
        raise ApiError(
            code="invalid_xlsx_container",
            message="XLSX 컨테이너를 읽을 수 없습니다.",
        ) from exc

    if "[Content_Types].xml" not in names or "xl/workbook.xml" not in names:
        raise ApiError(
            code="invalid_xlsx_container",
            message="XLSX 필수 구조를 확인할 수 없습니다.",
        )

    if total_uncompressed > MAX_XLSX_UNCOMPRESSED_BYTES:
        raise ApiError(
            code="xlsx_uncompressed_size_limit_exceeded",
            message="XLSX 압축 해제 예상 크기가 허용 한도를 초과했습니다.",
        )

    if total_compressed == 0 and total_uncompressed > 0:
        raise ApiError(
            code="xlsx_compression_ratio_limit_exceeded",
            message="XLSX 압축 비율을 안전하게 확인할 수 없습니다.",
        )

    if total_compressed > 0 and total_uncompressed / total_compressed > MAX_XLSX_COMPRESSION_RATIO:
        raise ApiError(
            code="xlsx_compression_ratio_limit_exceeded",
            message="XLSX 압축 비율이 허용 한도를 초과했습니다.",
        )
