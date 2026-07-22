from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    has_header: bool
    header_row: int
    data_start_row: int
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


class PastedDatasetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1)
    original_filename: str | None = Field(default=None, max_length=180)


class DatasetColumnDataType(str, Enum):
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    TEXT = "text"


class DatasetMeasurementLevel(str, Enum):
    UNKNOWN = "unknown"
    CONTINUOUS = "continuous"
    ORDINAL = "ordinal"
    NOMINAL = "nominal"
    BINARY = "binary"
    COUNT = "count"
    DATETIME = "datetime"
    ID = "id"


class DatasetColumnRole(str, Enum):
    UNSPECIFIED = "unspecified"
    ID = "id"
    FEATURE = "feature"
    TARGET = "target"
    GROUP = "group"
    TIME = "time"
    ORDER = "order"
    SUBGROUP_ID = "subgroup_id"
    PART_ID = "part_id"
    OPERATOR_ID = "operator_id"
    REPLICATE_ID = "replicate_id"
    SAMPLE_SIZE = "sample_size"
    OPPORTUNITIES = "opportunities"
    FACTOR = "factor"
    RESPONSE = "response"


class ConfirmedParsingOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["delimited_text", "xlsx"]
    encoding: str | None = None
    delimiter: str | None = None
    quote_char: str | None = '"'
    decimal: str = "."
    thousands: str | None = None
    has_header: bool = True
    header_row: int = Field(default=1, ge=1, le=1000)
    data_start_row: int | None = Field(default=None, ge=1, le=1000)
    missing_tokens: list[str] = Field(default_factory=lambda: ["", "NA", "N/A", "null", "N/T"])
    xlsx_sheet_name: str | None = None


class DatasetColumnConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    column_index: int = Field(ge=0)
    display_name: str | None = Field(default=None, max_length=120)
    data_type: DatasetColumnDataType | None = None
    measurement_level: DatasetMeasurementLevel = DatasetMeasurementLevel.UNKNOWN
    role: DatasetColumnRole = DatasetColumnRole.UNSPECIFIED
    unit: str | None = Field(default=None, max_length=40)


class DatasetParsingConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parsing: ConfirmedParsingOptions
    columns: list[DatasetColumnConfirmation] = Field(default_factory=list)


class DatasetColumnResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    column_id: UUID
    version_id: UUID
    column_index: int
    original_name: str
    display_name: str
    data_type: DatasetColumnDataType
    measurement_level: DatasetMeasurementLevel
    role: DatasetColumnRole
    unit: str | None


class DatasetVersionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_id: UUID
    dataset_id: UUID
    version_number: int
    row_count: int
    column_count: int
    schema_hash: str
    created_at: str


class DatasetArtifactResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: UUID
    version_id: UUID
    kind: str
    path: str
    sha256: str
    media_type: str
    size_bytes: int
    created_at: str


class DatasetVersionResponse(DatasetVersionSummary):
    source_sha256: str
    parsing: ConfirmedParsingOptions
    columns: list[DatasetColumnResponse]
    canonical_artifact: DatasetArtifactResponse | None


class DatasetVersionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: UUID
    versions: list[DatasetVersionSummary]


class DatasetVersionCatalogItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_id: UUID
    dataset_id: UUID
    original_filename: str
    version_number: int = Field(ge=1)
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=1)
    created_at: str
    user_label: str | None
    note: str | None
    pinned: bool
    metadata_updated_at: str | None


class DatasetVersionMetadataUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_label: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=500)
    pinned: bool | None = None
    expected_metadata_updated_at: str | None = None

    @field_validator("user_label", "note", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
            raise ValueError("asset_metadata_control_character")
        return normalized or None


class DatasetVersionMetadataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_id: UUID
    user_label: str | None
    note: str | None
    pinned: bool
    metadata_updated_at: str


class DatasetVersionDeletionCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_version_count: Literal[1]
    dataset_root_count: int = Field(ge=0, le=1)
    dataset_column_count: int = Field(ge=0)
    dataset_artifact_count: int = Field(ge=0)
    artifact_file_count: int = Field(ge=0)
    artifact_file_bytes: int = Field(ge=0)
    raw_upload_file_count: int = Field(ge=0, le=1)
    raw_upload_file_bytes: int = Field(ge=0)
    sibling_version_count: int = Field(ge=0)
    analysis_run_count: int = Field(ge=0)
    regression_model_count: int = Field(ge=0)
    prediction_source_count: int = Field(ge=0)
    prediction_target_count: int = Field(ge=0)
    analysis_export_count: int = Field(ge=0)
    job_count: int = Field(ge=0)
    attribute_control_limit_set_count: int = Field(ge=0)
    phase_2_analysis_count: int = Field(ge=0)


class DatasetVersionDeletionPreflightResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preflight_schema_version: Literal[1]
    version_id: UUID
    dataset_id: UUID
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=1)
    version_number: int = Field(ge=1)
    deletion_scope: Literal["version_only", "dataset_root"]
    deletion_ready: bool
    blockers: list[str]
    counts: DatasetVersionDeletionCounts
    deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class DatasetVersionDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_version_id: UUID
    expected_deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class DatasetVersionDeleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deletion_schema_version: Literal[1]
    version_id: UUID
    dataset_id: UUID
    deletion_scope: Literal["version_only", "dataset_root"]
    deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    deleted_at: str
    deleted_counts: DatasetVersionDeletionCounts
    cleanup_status: Literal["deleted", "quarantined_pending_cleanup"]


class DatasetVersionCatalogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    returned: int = Field(ge=0)
    has_previous: bool
    has_next: bool
    versions: list[DatasetVersionCatalogItem]


class DatasetColumnSchemaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    column_id: UUID
    display_name: str = Field(min_length=1, max_length=120)
    measurement_level: DatasetMeasurementLevel
    role: DatasetColumnRole
    unit: str | None = Field(default=None, max_length=40)


class DatasetSchemaUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    columns: list[DatasetColumnSchemaUpdate] = Field(min_length=1)


class DatasetSchemaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_id: UUID
    dataset_id: UUID
    schema_hash: str
    columns: list[DatasetColumnResponse]


class DatasetPreviewRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_index: int
    values: list[str | None]


class DatasetRowsPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_id: UUID
    offset: int
    limit: int
    total_rows: int
    returned_rows: int
    columns: list[DatasetColumnResponse]
    rows: list[DatasetPreviewRow]


class DatasetProfileIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    severity: Literal["info", "warning", "error"]
    message: str


class DatasetDateTimeFormatCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: str
    n_matched: int


class DatasetDateTimeProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n_datetime: int
    n_non_datetime: int
    datetime_min: str | None
    datetime_max: str | None
    timezone_aware_count: int
    timezone_naive_count: int
    mixed_timezone_awareness: bool
    format_candidates: list[DatasetDateTimeFormatCandidate]


class DatasetColumnProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    column_id: UUID
    column_index: int
    display_name: str
    data_type: DatasetColumnDataType
    measurement_level: DatasetMeasurementLevel
    role: DatasetColumnRole
    n_total: int
    n_present: int
    n_missing: int
    missing_rate: float
    unique_count: int
    unique_count_capped: bool
    n_numeric: int
    n_non_numeric: int
    numeric_min: float | None
    numeric_max: float | None
    numeric_mean: float | None
    datetime_profile: DatasetDateTimeProfile | None
    constant: bool
    warnings: list[DatasetProfileIssue]


class DatasetProfilePreflight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estimated_memory_bytes: int
    duplicate_row_count: int
    duplicate_row_count_capped: bool
    duplicate_row_check_limit: int


class DatasetProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_schema_version: int
    version_id: UUID
    dataset_id: UUID
    row_count: int
    column_count: int
    schema_hash: str
    computed_at: str
    unique_count_limit: int
    canonical_artifact: DatasetArtifactResponse | None
    profile_artifact: DatasetArtifactResponse | None
    preflight: DatasetProfilePreflight
    columns: list[DatasetColumnProfile]
    warnings: list[DatasetProfileIssue]
