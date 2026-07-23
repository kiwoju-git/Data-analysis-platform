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
    archived: bool
    archived_at: str | None


class DatasetVersionMetadataUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_label: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=500)
    pinned: bool | None = None
    archived: bool | None = None
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
    archived: bool
    archived_at: str | None
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


DatasetDeletionDependencyAssetType = Literal[
    "analysis_run",
    "regression_model",
    "prediction",
    "analysis_export",
    "attribute_control_limit_set",
    "phase_2_analysis",
    "job",
]


class DatasetDeletionDependencyDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_type: DatasetDeletionDependencyAssetType
    asset_id: UUID
    display_name: str
    method_id: str | None
    relationship: Literal[
        "direct_analysis",
        "model_fitted_from_dataset",
        "prediction_uses_as_source",
        "prediction_uses_as_target",
        "export_owned_by_analysis",
        "limit_set_derived_from_dataset",
        "phase_2_uses_limit_set",
        "job_owned_by_analysis",
    ]
    created_at: str | None
    status: str | None
    stale: bool | None
    result_available: bool | None
    related_dataset_version_id: UUID | None
    related_dataset_display_name: str | None
    integrity_state: Literal["verified", "unverified", "not_applicable"]
    blocker_codes: list[str]


class DatasetDeletionDependencyPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_id: UUID
    asset_type: DatasetDeletionDependencyAssetType | None
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    returned: int = Field(ge=0)
    has_previous: bool
    has_next: bool
    dependencies: list[DatasetDeletionDependencyDescriptor]


DatasetDeletionOperationId = Literal[
    "delete_dataset_verified",
    "remove_dataset_metadata_preserve_files",
    "delete_dataset_and_dependents_verified",
    "delete_dataset_and_dependents_preserve_unverified",
]


class DatasetVersionDeletionOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_id: DatasetDeletionOperationId
    dependency_policy: Literal["block", "cascade"]
    unverified_file_policy: Literal["block", "preserve"]
    ready: bool
    manifest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    affected_asset_count: int = Field(ge=0)
    verified_file_count: int = Field(ge=0)
    verified_file_bytes: int = Field(ge=0)
    preserved_unverified_file_count: int = Field(ge=0)
    blockers: list[str]


class DatasetVersionDeletionPreflightResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preflight_schema_version: Literal[3]
    version_id: UUID
    dataset_id: UUID
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=1)
    version_number: int = Field(ge=1)
    deletion_scope: Literal["version_only", "dataset_root"]
    deletion_ready: bool
    dependency_ready: bool
    integrity_state: Literal["verified", "legacy_repairable", "unverified"]
    integrity_issue_codes: list[str]
    verified_delete_ready: bool
    metadata_only_cleanup_ready: bool
    preserved_unverified_file_count: int = Field(ge=0)
    blockers: list[str]
    counts: DatasetVersionDeletionCounts
    deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    verified_deletion_manifest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    metadata_only_deletion_manifest_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    available_operations: list[DatasetVersionDeletionOperation]
    dependency_preview: list[DatasetDeletionDependencyDescriptor]
    dependency_preview_truncated: bool


class DatasetVersionDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_version_id: UUID
    expected_deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    mode: Literal[
        "verified_files_and_metadata",
        "metadata_only_preserve_unverified_files",
    ] = "verified_files_and_metadata"
    operation_id: DatasetDeletionOperationId | None = None


class DatasetVersionDeleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deletion_schema_version: Literal[3]
    version_id: UUID
    dataset_id: UUID
    deletion_scope: Literal["version_only", "dataset_root"]
    deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    deleted_at: str
    deleted_counts: DatasetVersionDeletionCounts
    deletion_mode: Literal[
        "verified_files_and_metadata",
        "metadata_only_preserve_unverified_files",
        "delete_dataset_and_dependents_verified",
        "delete_dataset_and_dependents_preserve_unverified",
    ]
    operation_id: DatasetDeletionOperationId
    preserved_unverified_file_count: int = Field(ge=0)
    deleted_dependency_count: int = Field(ge=0)
    cleanup_status: Literal[
        "deleted",
        "quarantined_pending_cleanup",
        "metadata_removed_files_preserved",
    ]


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
