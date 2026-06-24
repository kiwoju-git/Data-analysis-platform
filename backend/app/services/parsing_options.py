import csv
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

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
MAX_TEXT_LAYOUT_SCAN_LINES: Final = 50


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

    encodings = (
        TEXT_ENCODINGS
        if first_bytes.startswith(b"\xef\xbb\xbf")
        else (
            "utf-8",
            "utf-8-sig",
            "cp949",
        )
    )

    for encoding in encodings:
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
    layout = _detect_delimited_layout(decoded_text, suggested_delimiter)
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
            has_header=layout.has_header,
            header_row=layout.header_row,
            data_start_row=layout.data_start_row,
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
            has_header=True,
            header_row=1,
            data_start_row=2,
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


@dataclass(frozen=True)
class _DelimitedLayout:
    has_header: bool
    header_row: int
    data_start_row: int


@dataclass(frozen=True)
class _DelimitedLine:
    line_number: int
    cells: list[str]


def _detect_delimited_layout(text: str, delimiter: str | None) -> _DelimitedLayout:
    if delimiter is None:
        return _DelimitedLayout(has_header=True, header_row=1, data_start_row=2)

    rows = _parse_nonblank_delimited_lines(text, delimiter)
    run = _best_tabular_run(rows)
    if not run:
        return _DelimitedLayout(has_header=True, header_row=1, data_start_row=2)

    first_row = run[0]
    second_row = run[1] if len(run) > 1 else None
    has_header = _looks_like_header(first_row.cells, second_row.cells if second_row else None)
    if has_header:
        return _DelimitedLayout(
            has_header=True,
            header_row=first_row.line_number,
            data_start_row=first_row.line_number + 1,
        )
    return _DelimitedLayout(
        has_header=False,
        header_row=1,
        data_start_row=first_row.line_number,
    )


def _parse_nonblank_delimited_lines(text: str, delimiter: str) -> list[_DelimitedLine]:
    parsed_rows: list[_DelimitedLine] = []
    for line_number, line in enumerate(text.splitlines()[:MAX_TEXT_LAYOUT_SCAN_LINES], start=1):
        if line.strip() == "":
            continue
        try:
            cells = next(csv.reader([line], delimiter=delimiter, quotechar='"'))
        except csv.Error:
            continue
        if len(cells) >= 2 and any(cell.strip() != "" for cell in cells):
            parsed_rows.append(_DelimitedLine(line_number=line_number, cells=cells))
    return parsed_rows


def _best_tabular_run(rows: list[_DelimitedLine]) -> list[_DelimitedLine]:
    best_run: list[_DelimitedLine] = []
    best_score = 0
    index = 0
    while index < len(rows):
        field_count = len(rows[index].cells)
        run = [rows[index]]
        lookahead = index + 1
        while lookahead < len(rows) and len(rows[lookahead].cells) == field_count:
            run.append(rows[lookahead])
            lookahead += 1

        score = len(run) * field_count
        if score > best_score:
            best_score = score
            best_run = run
        index = lookahead
    return best_run


def _looks_like_header(first_cells: list[str], second_cells: list[str] | None) -> bool:
    if second_cells is None:
        return True

    first_values = [cell.strip() for cell in first_cells]
    second_values = [cell.strip() for cell in second_cells]
    first_numeric = sum(1 for value in first_values if _is_numeric_like(value))
    second_numeric = sum(1 for value in second_values if _is_numeric_like(value))

    if first_numeric > 0:
        return False
    return second_numeric >= max(1, len(second_values) // 2)


def _is_numeric_like(value: str) -> bool:
    if value == "":
        return False
    normalized = value.replace(",", "")
    if normalized.endswith("%"):
        normalized = normalized[:-1]
    try:
        float(normalized)
    except ValueError:
        return False
    return True


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
