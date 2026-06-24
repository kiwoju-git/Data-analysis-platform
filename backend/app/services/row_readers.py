import csv
from collections.abc import Iterator
from pathlib import Path
from typing import TextIO

from app.api.v1.schemas.datasets import ConfirmedParsingOptions
from app.core.errors import ApiError


def iter_delimited_rows(
    source_path: Path,
    options: ConfirmedParsingOptions,
    column_count: int,
) -> Iterator[list[str | None]]:
    if options.encoding is None or options.delimiter is None:
        raise ApiError(
            code="incomplete_parsing_options",
            message="텍스트 파싱에는 인코딩과 구분자가 필요합니다.",
        )

    try:
        with source_path.open("r", encoding=options.encoding, newline="") as handle:
            reader = _csv_reader(handle, options)
            first_data_row_number = _first_data_row_number(options)
            for line_number, row in enumerate(reader, start=1):
                if line_number < first_data_row_number:
                    continue
                if _is_blank_row(row):
                    continue
                yield _row_values(row, options, column_count)
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


def _row_values(
    row: list[str],
    options: ConfirmedParsingOptions,
    column_count: int,
) -> list[str | None]:
    values: list[str | None] = []
    for index in range(column_count):
        value = row[index] if index < len(row) else ""
        values.append(None if value in options.missing_tokens else value)
    return values


def _csv_reader(handle: TextIO, options: ConfirmedParsingOptions) -> Iterator[list[str]]:
    if options.delimiter is None:
        raise ApiError(
            code="incomplete_parsing_options",
            message="텍스트 파싱에는 구분자가 필요합니다.",
        )
    if options.quote_char is None:
        return csv.reader(handle, delimiter=options.delimiter, quoting=csv.QUOTE_NONE)
    return csv.reader(handle, delimiter=options.delimiter, quotechar=options.quote_char)


def _first_data_row_number(options: ConfirmedParsingOptions) -> int:
    if options.has_header:
        if options.data_start_row is not None:
            return options.data_start_row
        return options.header_row + 1
    return options.data_start_row if options.data_start_row is not None else options.header_row


def _is_blank_row(row: list[str]) -> bool:
    return not row or all(cell == "" for cell in row)
