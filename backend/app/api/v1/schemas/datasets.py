from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DatasetFormat(str, Enum):
    CSV = "csv"
    TSV = "tsv"
    XLSX = "xlsx"
    DELIMITED_TEXT = "delimited_text"


class UploadWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class DelimiterCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delimiter: str
    label: str
    score: int


class ParsingSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["delimited_text", "xlsx"]
    encoding_candidates: list[str]
    suggested_encoding: str | None
    delimiter_candidates: list[DelimiterCandidate]
    suggested_delimiter: str | None
    quote_char: str | None
    decimal: str
    thousands: str | None
    header_row: int
    xlsx_requires_sheet_selection: bool


class DatasetUploadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: UUID
    original_filename: str
    size_bytes: int
    sha256: str
    detected_format: DatasetFormat
    parsing: ParsingSuggestion
    warnings: list[UploadWarning]
    next_step: Literal["confirm_schema"]
