from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat


class AttributeControlLimitSetCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_analysis_id: UUID


class AttributeControlLimitSetColumnDependency(BaseModel):
    model_config = ConfigDict(extra="forbid")

    column_id: UUID
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


class AttributeControlLimitSetEligibility(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eligible: Literal[True]
    policy: Literal["phase_2_baseline_eligibility_v1"]
    minimum_point_count: Literal[20]
    checks_passed: list[
        Literal[
            "minimum_point_count",
            "no_phase_1_limit_signals",
            "usable_normal_approximation",
            "pearson_dispersion_not_above_two",
            "complete_untruncated_point_payload",
        ]
    ]


class AttributeControlLimitSetCreatorProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_version: str
    python_version: str
    platform: str
    build_commit: str | None
    package_versions: dict[str, str]


class AttributeControlLimitSetAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_schema_version: Literal[1]
    limit_set_id: UUID
    status: Literal["closed"]
    method_id: Literal["quality.attribute_control_chart"]
    source_method_version: Literal["0.1.0"]
    phase2_method_version: Literal["0.2.0"]
    source_result_schema_version: Literal[1]
    source_analysis_id: UUID
    source_dataset_version_id: UUID
    source_schema_hash: str = Field(min_length=64, max_length=64)
    source_canonical_sha256: str = Field(min_length=64, max_length=64)
    source_config_sha256: str = Field(min_length=64, max_length=64)
    source_result_sha256: str = Field(min_length=64, max_length=64)
    filter_snapshot_sha256: str = Field(min_length=64, max_length=64)
    row_snapshot_sha256: str = Field(min_length=64, max_length=64)
    chart_type: Literal["p", "np", "c", "u"]
    count_definition: Literal["defectives", "defects"]
    count: AttributeControlLimitSetColumnDependency
    denominator: AttributeControlLimitSetColumnDependency | None
    denominator_role: Literal["sample_size", "inspection_opportunity"] | None
    baseline_point_count: int = Field(ge=20)
    total_count: int = Field(ge=0)
    total_denominator: FiniteFloat | None
    frozen_center_line: FiniteFloat
    fixed_sample_size: int | None = Field(default=None, ge=1)
    constant_opportunity_confirmed: bool
    sigma_multiplier: FiniteFloat
    calculation_policy: Literal["phase_2_frozen_three_sigma_v1"]
    natural_bound_policy: Literal[
        "binomial_zero_one",
        "binomial_zero_fixed_sample_size",
        "poisson_zero",
    ]
    eligibility: AttributeControlLimitSetEligibility
    creator_provenance: AttributeControlLimitSetCreatorProvenance
    created_at: str
    closed_at: str


class AttributeControlLimitSetResponse(AttributeControlLimitSetAsset):
    asset_sha256: str = Field(min_length=64, max_length=64)


class AttributeControlLimitSetListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    items: list[AttributeControlLimitSetResponse]
