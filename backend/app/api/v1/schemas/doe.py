from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from app.api.v1.schemas.doe_model_workflow import (
    DoeFinalModelWorkflow,
    DoeFractionalEstimability,
    DoeModelSelectionOptions,
    DoeModelSelectionResult,
    RsmModelSelectionOptions,
)
from app.api.v1.schemas.rsm_plots import RsmPlotBundle
from app.core.doe_capabilities import (
    FACTORIAL_AUTHORING_FACTOR_LIMIT,
    GENERAL_FACTORIAL_AUTHORING_FACTOR_LIMIT,
    LATIN_HYPERCUBE_FACTOR_LIMIT,
)
from app.statistics.doe_factor_domain import DoeFactorDomain, validate_factor_domain


class DoeFactorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    low: FiniteFloat
    high: FiniteFloat
    unit: str | None = Field(default=None, max_length=40)
    domain_kind: Literal["continuous", "discrete_numeric"] = "continuous"
    step: FiniteFloat | None = None
    display_decimals: int | None = Field(default=None, ge=0, le=12)

    @model_validator(mode="after")
    def validate_domain(self) -> DoeFactorRequest:
        validate_factor_domain(
            DoeFactorDomain(
                low=float(self.low),
                high=float(self.high),
                domain_kind=self.domain_kind,
                step=None if self.step is None else float(self.step),
                display_decimals=self.display_decimals,
            )
        )
        return self


class TwoLevelNumericFactorRequest(DoeFactorRequest):
    factor_kind: Literal["numeric"] = "numeric"


class TwoLevelCategoricalFactorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor_kind: Literal["categorical"]
    name: str = Field(min_length=1, max_length=80)
    low_label: str = Field(min_length=1, max_length=120)
    high_label: str = Field(min_length=1, max_length=120)
    unit: str | None = Field(default=None, max_length=40)

    @model_validator(mode="after")
    def validate_labels(self) -> TwoLevelCategoricalFactorRequest:
        low = self.low_label.strip()
        high = self.high_label.strip()
        if not low or not high or low == high:
            raise ValueError("categorical low/high labels must be nonempty and distinct")
        if any(ord(character) < 32 for character in f"{low}{high}"):
            raise ValueError("categorical labels cannot contain control characters")
        return self


TwoLevelFactorRequest = Annotated[
    TwoLevelNumericFactorRequest | TwoLevelCategoricalFactorRequest,
    Field(discriminator="factor_kind"),
]


class FactorialDesignCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="2-level full factorial design", min_length=1, max_length=120)
    factors: list[TwoLevelFactorRequest] = Field(
        min_length=2,
        max_length=FACTORIAL_AUTHORING_FACTOR_LIMIT,
    )
    replicates: int = Field(default=1, ge=1, le=16)
    center_points: int = Field(default=0, ge=0, le=32)
    randomize: bool = True
    randomization_seed: int = Field(ge=0, le=2_147_483_647)
    block_count: int = Field(default=1, ge=1, le=64)
    design_type: Literal[
        "two_level_full",
        "two_level_fractional",
        "plackett_burman_screening",
    ] = "two_level_full"
    fraction_id: str | None = Field(default=None, max_length=80)
    screening_catalog_id: str | None = Field(default=None, max_length=80)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_numeric_factors(cls, value: object) -> object:
        if not isinstance(value, dict) or not isinstance(value.get("factors"), list):
            return value
        normalized = dict(value)
        normalized["factors"] = [
            (
                {**factor, "factor_kind": "numeric"}
                if isinstance(factor, dict) and "factor_kind" not in factor
                else factor
            )
            for factor in value["factors"]
        ]
        return normalized

    @model_validator(mode="after")
    def validate_fraction_selection(self) -> FactorialDesignCreateRequest:
        if self.design_type == "two_level_fractional" and not self.fraction_id:
            raise ValueError("fraction_id is required for a fractional factorial design")
        if self.design_type != "two_level_fractional" and self.fraction_id is not None:
            raise ValueError("fraction_id is only valid for a fractional factorial design")
        if self.design_type == "plackett_burman_screening" and not self.screening_catalog_id:
            raise ValueError("screening_catalog_id is required for Plackett-Burman")
        if (
            self.design_type != "plackett_burman_screening"
            and self.screening_catalog_id is not None
        ):
            raise ValueError("screening_catalog_id is only valid for Plackett-Burman")
        if self.design_type == "plackett_burman_screening" and self.center_points != 0:
            raise ValueError("Plackett-Burman P0 does not support center points")
        return self


class DoeFactorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    low: float
    high: float
    unit: str | None
    domain_kind: Literal["continuous", "discrete_numeric"] = "continuous"
    step: float | None = None
    display_decimals: int | None = Field(default=None, ge=0, le=12)
    level_count: int | None = Field(default=None, ge=2)

    @model_validator(mode="after")
    def populate_and_validate_domain(self) -> DoeFactorResponse:
        domain = DoeFactorDomain(
            low=self.low,
            high=self.high,
            domain_kind=self.domain_kind,
            step=self.step,
            display_decimals=self.display_decimals,
        )
        validate_factor_domain(domain)
        expected = domain.level_count
        if self.level_count is None:
            self.level_count = expected
        elif self.level_count != expected:
            raise ValueError("level_count does not match factor domain")
        return self


class TwoLevelNumericFactorResponse(DoeFactorResponse):
    factor_kind: Literal["numeric"] = "numeric"


class TwoLevelCategoricalFactorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor_kind: Literal["categorical"]
    name: str
    low_label: str
    high_label: str
    unit: str | None
    level_count: Literal[2] = 2


TwoLevelFactorResponse = Annotated[
    TwoLevelNumericFactorResponse | TwoLevelCategoricalFactorResponse,
    Field(discriminator="factor_kind"),
]


class FactorialDesignOptionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    replicates: int = Field(ge=1)
    center_points: int = Field(ge=0)
    randomize: bool
    randomization_seed: int = Field(ge=0)
    block_count: int = Field(ge=1)
    design_type: Literal[
        "two_level_full",
        "two_level_fractional",
        "plackett_burman_screening",
    ] = "two_level_full"
    fraction_id: str | None = None
    screening_catalog_id: str | None = None
    design_schema_version: int = Field(default=1, ge=1)


class FractionalAliasTermResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor_indices: list[int]
    sign: Literal[-1, 1]
    order: int = Field(ge=0, le=6)
    compact_label: str
    full_label: str

    @model_validator(mode="after")
    def validate_identity(self) -> FractionalAliasTermResponse:
        indices = self.factor_indices
        expected = "".join(chr(65 + index) for index in indices) or "I"
        if (
            indices != sorted(set(indices))
            or any(index < 0 or index > 5 for index in indices)
            or self.order != len(indices)
            or self.compact_label != expected
        ):
            raise ValueError("Alias identity must use canonical factor indices")
        return self


class FractionalFactorialMetadataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_entry_id: str
    base_factor_count: int = Field(ge=2)
    fraction_exponent: int = Field(ge=1)
    fraction: str
    resolution: int = Field(ge=3)
    generators: list[str]
    defining_relation: list[str]
    alias_groups: list[list[str]]
    estimable_terms: list[str]
    non_estimable_terms: list[str]
    principal_fraction: bool
    alias_view_schema_version: Literal[1] | None = None
    alias_classes: list[list[FractionalAliasTermResponse]] | None = None

    @model_validator(mode="after")
    def validate_alias_view(self) -> FractionalFactorialMetadataResponse:
        if (self.alias_view_schema_version is None) != (self.alias_classes is None):
            raise ValueError("Alias view version and classes must be provided together")
        if self.alias_classes is not None:
            factor_count = self.base_factor_count + self.fraction_exponent
            identities = [
                tuple(term.factor_indices) for group in self.alias_classes for term in group
            ]
            if (
                factor_count > 6
                or any(len(group) != 2**self.fraction_exponent for group in self.alias_classes)
                or any(any(index >= factor_count for index in indices) for indices in identities)
                or len(identities) != len(set(identities))
                or len(identities) != 2**factor_count
            ):
                raise ValueError("Alias view must partition the complete bounded effect set")
        return self


class PlackettBurmanMetadataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_entry_id: Literal["pb-12-run-v1"]
    run_count: Literal[12]
    available_columns: Literal[11]
    used_columns: int = Field(ge=7, le=10)
    unused_column_indices: list[int]
    matrix_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    resolution: Literal[3]


class FactorialDesignRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    standard_order: int = Field(ge=1)
    run_order: int = Field(ge=1)
    replicate_index: int = Field(ge=1)
    center_point: bool
    block_index: int | None = Field(default=None, ge=1)
    factor_levels: dict[str, float | str]
    coded_levels: dict[str, int]


class DoeResponseValueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_order: int = Field(ge=1)
    value: FiniteFloat


class DoeDesignResponsesUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_name: str = Field(min_length=1, max_length=80)
    unit: str | None = Field(default=None, max_length=40)
    values: list[DoeResponseValueRequest] = Field(min_length=1, max_length=256)


class DoeDesignResponseValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_order: int = Field(ge=1)
    value: float


class DoeDesignResponseSeries(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_name: str
    unit: str | None
    response_revision_id: UUID
    response_revision_number: int = Field(ge=1)
    response_revision_schema_version: Literal[1]
    response_revision_sha256: str
    created_at: str
    closed_at: str | None
    response_count: int = Field(ge=0)
    values: list[DoeDesignResponseValue]


class DoeDesignResponsesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design_id: UUID
    design_version_id: UUID
    version_number: int = Field(ge=1)
    status: str
    responses: list[DoeDesignResponseSeries]


class DoeResponseRevisionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_name: str = Field(min_length=1, max_length=80)
    unit: str | None = Field(default=None, max_length=40)
    values: list[DoeResponseValueRequest] = Field(min_length=1, max_length=256)
    supersedes_response_revision_id: UUID | None = None


class DoeResponseRevisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_revision_id: UUID
    design_id: UUID
    design_version_id: UUID
    response_revision_schema_version: Literal[1]
    response_revision_sha256: str
    response_name: str
    unit: str | None
    revision_number: int = Field(ge=1)
    state: Literal["completed", "abandoned"]
    is_current: bool
    response_count: int = Field(ge=1)
    supersedes_response_revision_id: UUID | None
    created_at: str
    closed_at: str | None
    values: list[DoeDesignResponseValue]


class DoeResponseRevisionHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design_id: UUID
    design_version_id: UUID
    response_name: str
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    items: list[DoeResponseRevisionResponse]


class FactorialDesignResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design_id: UUID
    design_version_id: UUID
    version_number: int = Field(ge=1)
    method_id: str
    method_version: str
    family: str
    name: str
    status: str
    created_at: str
    updated_at: str
    app_version: str
    factors: list[TwoLevelFactorResponse]
    options: FactorialDesignOptionsResponse
    run_count: int = Field(ge=1)
    design_sha256: str
    runs: list[FactorialDesignRunResponse]
    design_schema_version: int = Field(default=1, ge=1)
    fractional: FractionalFactorialMetadataResponse | None = None
    screening: PlackettBurmanMetadataResponse | None = None


class GeneralFactorialFactorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    levels: list[FiniteFloat | str] = Field(min_length=2, max_length=10)
    unit: str | None = Field(default=None, max_length=40)


class GeneralFactorialDesignCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="General full factorial design", min_length=1, max_length=120)
    factors: list[GeneralFactorialFactorRequest] = Field(
        min_length=2,
        max_length=GENERAL_FACTORIAL_AUTHORING_FACTOR_LIMIT,
    )
    replicates: int = Field(default=1, ge=1, le=16)
    randomize: bool = True
    randomization_seed: int = Field(ge=0, le=2_147_483_647)
    max_interaction_order: int = Field(default=2, ge=1, le=3)


class GeneralFactorialFactorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    levels: list[float | str]
    unit: str | None


class GeneralFactorialOptionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    replicates: int = Field(ge=1)
    randomize: bool
    randomization_seed: int = Field(ge=0)
    max_interaction_order: int = Field(ge=1, le=3)


class GeneralFactorialRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    standard_order: int = Field(ge=1)
    run_order: int = Field(ge=1)
    replicate_index: int = Field(ge=1)
    factor_levels: dict[str, float | str]
    level_indices: dict[str, int]


class GeneralFactorialDesignResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design_schema_version: Literal[1]
    design_id: UUID
    design_version_id: UUID
    version_number: Literal[1]
    method_id: Literal["doe.general_factorial_design"]
    method_version: Literal["0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.4.1"]
    family: Literal["general_full_factorial"]
    name: str
    status: str
    created_at: str
    updated_at: str
    app_version: str
    factors: list[GeneralFactorialFactorResponse]
    options: GeneralFactorialOptionsResponse
    run_count: int = Field(ge=1, le=256)
    design_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runs: list[GeneralFactorialRunResponse]


class GeneralFactorialAnalysisCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_selection: DoeModelSelectionOptions = Field(default_factory=DoeModelSelectionOptions)
    confidence_level: FiniteFloat = Field(default=0.95, gt=0, lt=1)
    point_limit: int = Field(default=256, ge=1, le=256)

    response_name: str = Field(min_length=1, max_length=80)
    response_revision_id: UUID | None = None
    max_interaction_order: int = Field(default=2, ge=1, le=3)


class GeneralFactorialAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: UUID
    design_id: UUID
    design_version_id: UUID
    design_version_number: int = Field(ge=1)
    method_id: Literal["doe.general_factorial_design"]
    method_version: Literal["0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.4.1"]
    analysis_schema_version: Literal[1]
    design_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    response_revision_id: UUID
    response_revision_number: int = Field(ge=1)
    response_revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    response_name: str
    created_at: str
    app_version: str
    result: dict[str, object]


class DoeDesignDeletionCounts(BaseModel):
    prediction_count: int = Field(default=0, ge=0)
    report_count: int = Field(default=0, ge=0)
    plot_view_count: int = Field(default=0, ge=0)
    model_config = ConfigDict(extra="forbid")

    version_count: int = Field(ge=1)
    run_count: int = Field(ge=1)
    response_count: int = Field(ge=0)
    response_revision_count: int = Field(ge=0)
    analysis_count: int = Field(ge=0)


class DoeDesignDeletionPreflightResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preflight_schema_version: Literal[1]
    design_id: UUID
    method_id: str
    status: str
    counts: DoeDesignDeletionCounts
    deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class DoeDesignDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_design_id: UUID
    expected_deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class DoeDesignDeleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deletion_schema_version: Literal[1]
    design_id: UUID
    deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    deleted_at: str
    deleted_counts: DoeDesignDeletionCounts


class LatinHypercubeDesignCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="LHS space-filling design", min_length=1, max_length=120)
    factors: list[DoeFactorRequest] = Field(
        min_length=1,
        max_length=LATIN_HYPERCUBE_FACTOR_LIMIT,
    )
    run_count: int = Field(ge=2, le=200)
    seed: int = Field(ge=0, le=2_147_483_647)
    randomize_run_order: bool = True
    run_order_seed: int = Field(ge=0, le=2_147_483_647)
    optimization: Literal["random_cd", "none"] = "random_cd"


class LatinHypercubeDesignOptionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy: Literal[
        "scipy_latin_hypercube_random_cd_v1",
        "mixed_lhs_balanced_discrete_v1",
    ]
    run_count: int = Field(ge=2, le=200)
    seed: int = Field(ge=0)
    scramble: Literal[True]
    strength: Literal[1]
    optimization: Literal["random_cd", "none"]
    randomize_run_order: bool
    run_order_seed: int = Field(ge=0)
    numpy_version: str
    scipy_version: str


class LatinHypercubeDesignQualityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    centered_discrepancy: float
    minimum_pairwise_distance: float
    maximum_absolute_factor_correlation: float
    per_factor_strata_occupancy: list[list[int]]
    strata_valid: bool
    continuous_strata_valid: bool | None = None
    discrete_level_balance: dict[str, list[int]] = Field(default_factory=dict)
    duplicate_count: int = Field(default=0, ge=0)
    executable_point_count: int | None = Field(default=None, ge=0)


class LatinHypercubeRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    standard_order: int = Field(ge=1)
    run_order: int = Field(ge=1)
    replicate_index: Literal[1]
    center_point: Literal[False]
    block_index: None
    factor_levels: dict[str, float]
    normalized_levels: dict[str, float]


class LatinHypercubeDesignResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design_schema_version: Literal[1, 2]
    design_id: UUID
    design_version_id: UUID
    version_number: Literal[1]
    method_id: Literal["doe.latin_hypercube"]
    method_version: Literal["0.1.0", "0.2.0", "0.3.0"]
    family: Literal["latin_hypercube_space_filling"]
    name: str
    status: str
    created_at: str
    updated_at: str
    app_version: str
    factors: list[DoeFactorResponse]
    options: LatinHypercubeDesignOptionsResponse
    quality: LatinHypercubeDesignQualityResponse
    run_count: int = Field(ge=2, le=200)
    design_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runs: list[LatinHypercubeRunResponse]


class DoeFactorialAnalysisCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_selection: DoeModelSelectionOptions = Field(default_factory=DoeModelSelectionOptions)

    response_name: str = Field(min_length=1, max_length=80)
    response_revision_id: UUID | None = None
    max_interaction_order: int = Field(default=2, ge=1, le=3)
    confidence_level: FiniteFloat = Field(default=0.95, gt=0, lt=1)
    point_limit: int = Field(default=256, ge=1, le=256)


class DoeFactorialResponseMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    unit: str | None


class DoeFactorialCodingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    low: int
    high: int
    center: int
    effect_definition: str


class DoeFactorialModelPolicyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hierarchy_enforced: bool
    max_interaction_order: int
    automatic_term_selection: bool
    center_curvature_included: bool
    center_curvature_available: bool | None = None
    center_curvature_disposition: Literal["candidate", "forced", "excluded", "removed"] | None = (
        None
    )
    center_curvature_removed_step: int | None = None
    block_fixed_effects_included: bool
    sum_of_squares: str
    requested_interaction_order: int | None = None
    effective_interaction_order: int | None = None
    requested_term_ids: list[str] | None = None
    estimable_representative_term_ids: list[str] | None = None
    alias_rank_excluded_term_ids: list[str] | None = None


class DoeFactorialSampleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n_observations: int
    factorial_point_count: int
    center_point_count: int
    block_count: int
    parameter_count: int
    rank: int
    df_model: int
    df_residual: int


class DoeFactorialFitResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_mean: float
    sse: float
    model_ss: float
    total_ss: float
    residual_mean_square: float | None
    residual_standard_error: float | None
    r_squared: float
    adjusted_r_squared: float | None
    f_statistic: float | None
    f_p_value: float | None


class DoeConfidenceIntervalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: float
    lower: float
    upper: float


class DoeFactorialTermResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    term_id: str
    label: str
    kind: str
    factor_names: list[str]
    coefficient: float
    effect: float | None
    standard_error: float | None
    statistic: float | None
    p_value: float | None
    confidence_interval: DoeConfidenceIntervalResponse | None
    effect_confidence_interval: DoeConfidenceIntervalResponse | None
    partial_sum_squares: float | None
    f_statistic: float | None
    f_p_value: float | None


class DoeRankedEffectResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    term_id: str
    label: str
    effect: float
    absolute_effect: float


class DoeAnovaRowResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    df: int
    sum_squares: float | None
    mean_square: float | None = None
    f_statistic: float | None = None
    p_value: float | None = None


class DoeLackOfFitBreakdownResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: bool
    reason: (
        Literal[
            "no_replicated_design_points",
            "no_lack_of_fit_df",
            "pure_error_variance_zero",
            "numerical_decomposition_failure",
        ]
        | None
    ) = None
    decomposition_available: bool | None = None
    replication_grouping_policy: Literal["all_design_factor_settings_and_block"] | None = None
    decomposition_tolerance: float | None = None
    non_curvature_reason: str | None = None
    unique_design_point_count: int
    pure_error: DoeAnovaRowResponse
    lack_of_fit: DoeAnovaRowResponse
    residual_df: int
    curvature_in_error: DoeAnovaRowResponse | None = None
    non_curvature_lack_of_fit: DoeAnovaRowResponse | None = None


class DoeFactorialAnovaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sum_of_squares_policy: str
    model: DoeAnovaRowResponse
    residual: DoeAnovaRowResponse
    total: DoeAnovaRowResponse
    lack_of_fit: DoeLackOfFitBreakdownResponse


class DoeShapiroWilkResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statistic: float | None
    p_value: float | None


class DoeDiagnosticPointResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_order: int
    standard_order: int
    observed: float
    fitted: float
    residual: float
    standardized_residual: float | None
    leverage: float
    cooks_distance: float | None


class DoeQqPointResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theoretical: float
    ordered_residual: float


class DoeFactorialDiagnosticsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    residual_mean: float
    residual_min: float
    residual_max: float
    max_abs_standardized_residual: float | None
    high_standardized_residual_count: int
    max_leverage: float
    high_leverage_threshold: float
    high_leverage_count: int
    max_cooks_distance: float | None
    cooks_distance_threshold: float
    high_cooks_distance_count: int
    durbin_watson: float | None
    shapiro_wilk: DoeShapiroWilkResponse
    point_limit: int
    points_truncated: bool
    points: list[DoeDiagnosticPointResponse]
    qq_points: list[DoeQqPointResponse]


class DoeMainEffectPlotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor: str
    low_mean: float
    high_mean: float


class DoeInteractionCellResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_level: int
    second_level: int
    mean: float
    n: int


class DoeInteractionPlotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_factor: str
    second_factor: str
    cells: list[DoeInteractionCellResponse]


class DoeFactorialPlotsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    main_effects: list[DoeMainEffectPlotResponse]
    interactions: list[DoeInteractionPlotResponse]


class DoeFactorialAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1, 2, 3, 4]
    estimability: DoeFractionalEstimability | None = None
    model_selection: DoeModelSelectionResult | None = None
    final_model: DoeFinalModelWorkflow | None = None
    config_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    summary_type: Literal["factorial_analysis"]
    method: str
    response: DoeFactorialResponseMetadata
    factor_names: list[str]
    coding: DoeFactorialCodingResponse
    model_policy: DoeFactorialModelPolicyResponse
    sample: DoeFactorialSampleResponse
    fit: DoeFactorialFitResponse
    terms: list[DoeFactorialTermResponse]
    ranked_effects: list[DoeRankedEffectResponse]
    anova: DoeFactorialAnovaResponse
    diagnostics: DoeFactorialDiagnosticsResponse
    plots: DoeFactorialPlotsResponse
    warnings: list[str]
    fractional_design: FractionalFactorialMetadataResponse | None = None
    screening_design: PlackettBurmanMetadataResponse | None = None

    @model_validator(mode="after")
    def validate_final_model(self) -> DoeFactorialAnalysisResult:
        if self.schema_version >= 2 and (self.model_selection is None or self.final_model is None):
            raise ValueError("doe_factorial_final_model_missing")
        if self.schema_version == 4:
            plan = self.estimability
            policy = self.model_policy
            if (
                plan is None
                or policy.requested_interaction_order not in {1, 2}
                or policy.requested_term_ids is None
                or policy.estimable_representative_term_ids != plan.representative_term_ids
                or policy.alias_rank_excluded_term_ids != [item.term_id for item in plan.exclusions]
                or plan.rank != plan.estimable_parameter_count
                or plan.rank + plan.expected_residual_df != self.sample.n_observations
                or plan.saturated != (plan.expected_residual_df == 0)
            ):
                raise ValueError("doe_fractional_estimability_contract_invalid")
        return self


class DoeFactorialAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: UUID
    design_id: UUID
    design_version_id: UUID
    design_version_number: int
    method_id: str
    method_version: str
    analysis_schema_version: int
    design_sha256: str
    response_revision_id: UUID
    response_revision_number: int = Field(ge=1)
    response_revision_sha256: str
    response_sha256: str
    response_name: str
    created_at: str
    app_version: str
    python_version: str
    platform: str
    build_commit: str | None
    package_versions: dict[str, str]
    result: DoeFactorialAnalysisResult


class ResponseSurfaceDesignCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="Central composite design", min_length=1, max_length=120)
    factors: list[DoeFactorRequest] = Field(min_length=2, max_length=5)
    alpha_mode: Literal["rotatable", "face_centered"] = "rotatable"
    ccd_type: Literal["circumscribed", "inscribed", "face_centered"] | None = None
    axial_points_confirmed: bool = False
    factorial_replicates: int = Field(default=1, ge=1, le=4)
    axial_replicates: int = Field(default=1, ge=1, le=4)
    center_points: int = Field(default=5, ge=1, le=32)
    center_point_mode: Literal["recommended", "custom"] = "custom"
    randomize: bool = True
    randomization_seed: int = Field(ge=0, le=2_147_483_647)

    @model_validator(mode="after")
    def validate_ccd_mode(self) -> ResponseSurfaceDesignCreateRequest:
        if self.ccd_type is not None:
            expected: Literal["rotatable", "face_centered"] = (
                "face_centered" if self.ccd_type == "face_centered" else "rotatable"
            )
            if "alpha_mode" in self.model_fields_set and self.alpha_mode != expected:
                raise ValueError("doe_rsm_ccd_type_alpha_mode_mismatch")
            self.alpha_mode = expected
        if self.ccd_type == "circumscribed" and not self.axial_points_confirmed:
            raise ValueError("doe_rsm_axial_confirmation_required")
        if self.center_point_mode == "recommended":
            from app.statistics.ccd_recommendations import recommend_ccd_centers

            recommendation = recommend_ccd_centers(
                len(self.factors),
                factorial_replicates=self.factorial_replicates,
                axial_replicates=self.axial_replicates,
            ).center_points
            if recommendation is None:
                raise ValueError("doe_rsm_center_recommendation_unavailable")
            if "center_points" in self.model_fields_set and self.center_points != recommendation:
                raise ValueError("doe_rsm_center_recommendation_mismatch")
            self.center_points = recommendation
        return self


class RsmFactorCodingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    center: FiniteFloat
    scale: FiniteFloat = Field(gt=0)
    input_bounds_role: Literal["factorial", "axial", "factorial_and_axial"]
    factorial_low: FiniteFloat
    factorial_high: FiniteFloat
    axial_low: FiniteFloat
    axial_high: FiniteFloat
    alpha: FiniteFloat = Field(ge=1)


class ResponseSurfaceDesignOptionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alpha_mode: Literal["rotatable", "face_centered"]
    ccd_type: Literal["circumscribed", "inscribed", "face_centered"] | None = None
    center_point_mode: Literal["recommended", "custom"] | None = None
    alpha: float = Field(ge=1)
    factorial_replicates: int = Field(ge=1)
    axial_replicates: int = Field(ge=1)
    center_points: int = Field(ge=1)
    randomize: bool
    randomization_seed: int = Field(ge=0)


class ResponseSurfaceDesignRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    standard_order: int = Field(ge=1)
    run_order: int = Field(ge=1)
    replicate_index: int = Field(ge=1)
    point_type: Literal["factorial", "axial", "center"]
    center_point: bool
    factor_levels: dict[str, float]
    coded_levels: dict[str, float]


class ResponseSurfaceDesignResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design_id: UUID
    design_version_id: UUID
    version_number: int = Field(ge=1)
    method_id: Literal["doe.response_surface"]
    method_version: str
    design_schema_version: Literal[1, 2, 3]
    family: Literal["central_composite", "central_composite_inscribed"]
    name: str
    status: str
    created_at: str
    updated_at: str
    app_version: str
    factors: list[DoeFactorResponse]
    options: ResponseSurfaceDesignOptionsResponse
    run_count: int = Field(ge=1)
    design_sha256: str
    runs: list[ResponseSurfaceDesignRunResponse]
    coding: dict[str, RsmFactorCodingResponse] | None = None


class DoeResponseSurfaceAnalysisCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_name: str = Field(min_length=1, max_length=80)
    response_revision_id: UUID | None = None
    confidence_level: FiniteFloat = Field(default=0.95, gt=0, lt=1)
    point_limit: int = Field(default=256, ge=1, le=256)
    contour_grid_size: int = Field(default=21, ge=11, le=51)
    term_preset: Literal["linear", "linear_squares", "linear_interactions", "full_quadratic"] = (
        "full_quadratic"
    )
    model_selection: RsmModelSelectionOptions = Field(default_factory=RsmModelSelectionOptions)


class DoeResponseSurfaceCodingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    center: float
    factorial_low: float
    factorial_high: float
    axial_distance: float = Field(ge=1)
    actual_bounds_are_axial_bounds: bool
    factors: dict[str, RsmFactorCodingResponse] | None = None


class DoeResponseSurfaceModelPolicyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_quadratic: bool
    automatic_term_selection: bool
    hierarchy_enforced: bool
    sum_of_squares: str
    contour_other_factors_held_at_center: bool


class DoeResponseSurfaceSampleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n_observations: int
    factorial_point_count: int
    axial_point_count: int
    center_point_count: int
    unique_design_point_count: int
    parameter_count: int
    rank: int
    df_model: int
    df_residual: int


class DoeResponseSurfaceTermResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    term_id: str
    label: str
    kind: Literal["intercept", "main_effect", "interaction", "quadratic"]
    factor_names: list[str]
    coefficient: float
    standard_error: float | None
    statistic: float | None
    p_value: float | None
    confidence_interval: DoeConfidenceIntervalResponse | None
    partial_sum_squares: float | None
    f_statistic: float | None
    f_p_value: float | None


class DoeResponseSurfaceStationaryPointResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: bool
    reason: Literal["singular_hessian"] | None = None
    classification: Literal["minimum", "maximum", "saddle", "indeterminate"]
    coded_coordinates: dict[str, float]
    actual_coordinates: dict[str, float]
    predicted_response: float | None
    within_axial_bounds: bool
    within_factorial_cube: bool
    hessian_eigenvalues: list[float]


class DoeResponseSurfaceContourPointResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x_coded: float
    y_coded: float
    x_actual: float
    y_actual: float
    predicted: float


class DoeResponseSurfaceContourResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x_factor: str
    y_factor: str
    held_coded_levels: dict[str, float]
    grid_size: int
    coded_range: list[float] = Field(min_length=2, max_length=2)
    points: list[DoeResponseSurfaceContourPointResponse]


class DoeResponseSurfaceDiagnosticPointResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_order: int
    standard_order: int
    point_type: Literal["factorial", "axial", "center"]
    observed: float
    fitted: float
    residual: float
    standardized_residual: float | None
    leverage: float
    cooks_distance: float | None


class DoeResponseSurfaceDiagnosticsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    residual_mean: float
    residual_min: float
    residual_max: float
    max_abs_standardized_residual: float | None
    high_standardized_residual_count: int
    max_leverage: float
    high_leverage_threshold: float
    high_leverage_count: int
    max_cooks_distance: float | None
    cooks_distance_threshold: float
    high_cooks_distance_count: int
    durbin_watson: float | None
    shapiro_wilk: DoeShapiroWilkResponse
    point_limit: int
    points_truncated: bool
    points: list[DoeResponseSurfaceDiagnosticPointResponse]
    qq_points: list[DoeQqPointResponse]


class RsmFinalBasisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    factor_names: list[str] = Field(min_length=2, max_length=5)
    term_ids: list[str]
    powers: list[list[int]]
    coefficients: list[FiniteFloat]
    covariance: list[list[FiniteFloat]] | None
    residual_df: int = Field(ge=0)
    residual_mean_square: FiniteFloat | None
    coding: dict[str, RsmFactorCodingResponse]

    @model_validator(mode="after")
    def validate_basis(self) -> RsmFinalBasisResponse:
        count = len(self.term_ids)
        if (
            count < 1
            or len(set(self.term_ids)) != count
            or len(set(self.factor_names)) != len(self.factor_names)
            or len(self.powers) != count
            or len(self.coefficients) != count
            or set(self.coding) != set(self.factor_names)
            or any(
                len(powers) != len(self.factor_names)
                or any(power < 0 for power in powers)
                or sum(powers) > 2
                for powers in self.powers
            )
            or len({tuple(powers) for powers in self.powers}) != count
            or self.powers[0] != [0] * len(self.factor_names)
            or self.term_ids[0] != "intercept"
            or (
                self.covariance is not None
                and (
                    len(self.covariance) != count
                    or any(len(row) != count for row in self.covariance)
                )
            )
        ):
            raise ValueError("doe_rsm_basis_invalid")
        return self


class DoeResponseSurfaceAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1, 2]
    summary_type: Literal["response_surface_analysis"]
    method: Literal[
        "full_quadratic_ordinary_least_squares",
        "hierarchical_response_surface_ordinary_least_squares",
    ]
    response: DoeFactorialResponseMetadata
    factor_names: list[str]
    coding: DoeResponseSurfaceCodingResponse
    model_policy: DoeResponseSurfaceModelPolicyResponse
    sample: DoeResponseSurfaceSampleResponse
    fit: DoeFactorialFitResponse
    terms: list[DoeResponseSurfaceTermResponse]
    anova: DoeFactorialAnovaResponse
    stationary_point: DoeResponseSurfaceStationaryPointResponse
    contour: DoeResponseSurfaceContourResponse
    diagnostics: DoeResponseSurfaceDiagnosticsResponse
    warnings: list[str]
    term_preset: (
        Literal["linear", "linear_squares", "linear_interactions", "full_quadratic"] | None
    ) = None
    model_selection: DoeModelSelectionResult | None = None
    final_basis: RsmFinalBasisResponse | None = None
    press: FiniteFloat | None = None
    predicted_r_squared: FiniteFloat | None = None
    plot_bundle: RsmPlotBundle | None = None
    plot_overview: list[RsmPlotBundle] | None = None

    @model_validator(mode="after")
    def validate_final_basis(self) -> DoeResponseSurfaceAnalysisResult:
        if self.schema_version < 2:
            return self
        basis = self.final_basis
        if (
            basis is None
            or self.model_selection is None
            or self.term_preset is None
            or basis.factor_names != self.factor_names
            or basis.term_ids != [term.term_id for term in self.terms]
            or basis.coefficients != [term.coefficient for term in self.terms]
            or basis.residual_df != self.sample.df_residual
            or len(basis.term_ids) != self.sample.parameter_count
            or basis.coding != self.coding.factors
            or self.model_selection.final_term_ids != basis.term_ids[1:]
        ):
            raise ValueError("doe_rsm_final_basis_mismatch")
        return self


class DoeResponseSurfaceAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: UUID
    design_id: UUID
    design_version_id: UUID
    design_version_number: int
    method_id: Literal["doe.response_surface"]
    method_version: str
    analysis_schema_version: int
    design_sha256: str
    response_revision_id: UUID
    response_revision_number: int = Field(ge=1)
    response_revision_sha256: str
    response_sha256: str
    response_name: str
    created_at: str
    app_version: str
    python_version: str
    platform: str
    build_commit: str | None
    package_versions: dict[str, str]
    result: DoeResponseSurfaceAnalysisResult


class DoeResponseSurfaceAnalysisCatalogItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: UUID
    design_id: UUID
    design_name: str
    response_name: str
    response_revision_id: UUID | None
    response_revision_number: int | None = Field(ge=1)
    method_id: Literal["doe.response_surface"]
    method_version: str
    created_at: str
    eligibility_status: Literal[
        "eligible",
        "acknowledgment_required",
        "ineligible",
        "integrity_error",
        "incompatible_method_version",
    ]
    blocking_issue_count: int = Field(ge=0)
    advisory_issue_count: int = Field(ge=0)
    informational_issue_count: int = Field(ge=0)
    availability_code: str | None


class DoeResponseSurfaceAnalysisCatalogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analyses: list[DoeResponseSurfaceAnalysisCatalogItem]
    total: int = Field(ge=0)
    returned: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    has_previous: bool
    has_next: bool


class ResponseOptimizerObjectiveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_analysis_id: UUID
    goal: Literal["maximize", "minimize", "target", "range"]
    lower: FiniteFloat | None = None
    target: FiniteFloat | None = None
    upper: FiniteFloat | None = None
    lower_weight: FiniteFloat = Field(default=1.0, gt=0, le=10)
    upper_weight: FiniteFloat = Field(default=1.0, gt=0, le=10)
    importance: FiniteFloat = Field(default=1.0, gt=0, le=10)


class ResponseOptimizerFactorBoundRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor_name: str = Field(min_length=1, max_length=80)
    lower: FiniteFloat
    upper: FiniteFloat


class ResponseOptimizerLinearConstraintRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    coefficients: dict[str, FiniteFloat] = Field(min_length=1, max_length=5)
    relation: Literal["less_than_or_equal", "greater_than_or_equal"]
    bound: FiniteFloat


class ResponseOptimizerSearchOptionsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    random_seed: int = Field(default=20260714, ge=0, le=2_147_483_647)
    random_candidate_count: int = Field(default=256, ge=0, le=4096)
    multi_start_count: int = Field(default=8, ge=1, le=32)
    max_iterations: int = Field(default=120, ge=1, le=500)
    max_evaluations: int = Field(default=5000, ge=32, le=100_000)
    time_budget_ms: int = Field(default=5000, ge=100, le=30_000)


class ResponseOptimizerCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objectives: list[ResponseOptimizerObjectiveRequest] = Field(min_length=1, max_length=8)
    factor_bounds: list[ResponseOptimizerFactorBoundRequest] = Field(
        default_factory=list, max_length=5
    )
    linear_constraints: list[ResponseOptimizerLinearConstraintRequest] = Field(
        default_factory=list, max_length=16
    )
    search: ResponseOptimizerSearchOptionsRequest = Field(
        default_factory=ResponseOptimizerSearchOptionsRequest
    )
    acknowledged_source_warning_codes: list[str] = Field(default_factory=list, max_length=32)


class ResponseOptimizerEligibilityIssueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_analysis_id: UUID | None
    code: str
    severity: Literal["blocking", "acknowledgment_required", "informational"]
    source_warning_code: str | None


class ResponseOptimizerSourceEligibilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eligible: bool
    acknowledgment_required: bool
    issues: list[ResponseOptimizerEligibilityIssueResponse]
    acknowledged_source_warning_codes: list[str]


class ResponseOptimizerModelPolicyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    individual_desirability: Literal["derringer_suich"]
    composite_desirability: Literal["importance_weighted_geometric_mean"]
    bounded_to_declared_design_region: bool
    linear_constraints_supported: bool
    global_optimum_guaranteed: bool
    point_predictions_only: bool


class ResponseOptimizerDesignBoundResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor_name: str
    lower: float
    upper: float
    unit: str | None
    domain_kind: Literal["continuous", "discrete_numeric"] = "continuous"
    step: float | None = None
    display_decimals: int | None = None


class ResponseOptimizerSearchBoundResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor_name: str
    lower: float
    upper: float


class ResponseOptimizerLinearConstraintResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    coefficients: dict[str, float]
    relation: Literal["less_than_or_equal", "greater_than_or_equal"]
    bound: float


class ResponseOptimizerFactorRegionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design_bounds: list[ResponseOptimizerDesignBoundResponse]
    search_bounds: list[ResponseOptimizerSearchBoundResponse]
    linear_constraints: list[ResponseOptimizerLinearConstraintResponse]


class ResponseOptimizerObjectiveResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_analysis_id: UUID
    response_name: str
    response_unit: str | None
    goal: Literal["maximize", "minimize", "target", "range"]
    lower: float | None
    target: float | None
    upper: float | None
    lower_weight: float
    upper_weight: float
    importance: float


class ResponseOptimizerRecommendationObjectiveResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_analysis_id: UUID
    response_name: str
    goal: Literal["maximize", "minimize", "target", "range"]
    predicted_response: float
    individual_desirability: float = Field(ge=0, le=1)
    importance: float = Field(gt=0)


class ResponseOptimizerConstraintEvaluationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    relation: Literal["less_than_or_equal", "greater_than_or_equal"]
    lhs: float
    bound: float
    slack: float
    satisfied: bool


class ResponseOptimizerRecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actual_coordinates: dict[str, float]
    coded_coordinates: dict[str, float]
    composite_desirability: float = Field(ge=0, le=1)
    objectives: list[ResponseOptimizerRecommendationObjectiveResponse]
    constraints: list[ResponseOptimizerConstraintEvaluationResponse]
    all_constraints_satisfied: bool


class ResponseOptimizerSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    algorithm: Literal["seeded_candidates_plus_slsqp_multistart"]
    random_seed: int
    random_candidate_count: int
    multi_start_count: int
    max_iterations: int
    max_evaluations: int
    time_budget_ms: int
    evaluation_count: int
    local_starts_attempted: int
    local_success_count: int
    local_iterations: int
    elapsed_ms: float = Field(ge=0)
    termination_reason: Literal["search_completed", "evaluation_budget", "time_budget"]
    global_optimum_guaranteed: bool


class ResponseOptimizerResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[2]
    summary_type: Literal["response_optimizer"]
    method: Literal["derringer_suich_bounded_multistart_slsqp"]
    model_policy: ResponseOptimizerModelPolicyResponse
    factor_region: ResponseOptimizerFactorRegionResponse
    objectives: list[ResponseOptimizerObjectiveResponse]
    recommendation: ResponseOptimizerRecommendationResponse
    search: ResponseOptimizerSearchResponse
    source_model_eligibility: ResponseOptimizerSourceEligibilityResponse
    acknowledged_source_warning_codes: list[str]
    warnings: list[str]


class ResponseOptimizerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    optimization_id: UUID
    design_id: UUID
    design_version_id: UUID
    design_version_number: int
    method_id: Literal[
        "doe.response_optimizer",
        "regression.response_optimizer",
    ]
    method_version: str
    config_schema_version: Literal[2]
    result_schema_version: Literal[2]
    config_sha256: str
    design_sha256: str
    source_analysis_ids: list[UUID]
    source_bundle_sha256: str
    acknowledged_source_warning_codes: list[str]
    created_at: str
    app_version: str
    python_version: str
    platform: str
    build_commit: str | None
    package_versions: dict[str, str]
    result: ResponseOptimizerResult
    factor_kind: Literal["numeric"] = "numeric"
