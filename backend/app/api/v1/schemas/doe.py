from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat


class DoeFactorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    low: FiniteFloat
    high: FiniteFloat
    unit: str | None = Field(default=None, max_length=40)


class FactorialDesignCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="2-level full factorial design", min_length=1, max_length=120)
    factors: list[DoeFactorRequest] = Field(min_length=2, max_length=6)
    replicates: int = Field(default=1, ge=1, le=16)
    center_points: int = Field(default=0, ge=0, le=32)
    randomize: bool = True
    randomization_seed: int = Field(ge=0, le=2_147_483_647)
    block_count: int = Field(default=1, ge=1, le=64)


class DoeFactorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    low: float
    high: float
    unit: str | None


class FactorialDesignOptionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    replicates: int = Field(ge=1)
    center_points: int = Field(ge=0)
    randomize: bool
    randomization_seed: int = Field(ge=0)
    block_count: int = Field(ge=1)


class FactorialDesignRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    standard_order: int = Field(ge=1)
    run_order: int = Field(ge=1)
    replicate_index: int = Field(ge=1)
    center_point: bool
    block_index: int | None = Field(default=None, ge=1)
    factor_levels: dict[str, float]
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
    factors: list[DoeFactorResponse]
    options: FactorialDesignOptionsResponse
    run_count: int = Field(ge=1)
    design_sha256: str
    runs: list[FactorialDesignRunResponse]


class DoeFactorialAnalysisCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    block_fixed_effects_included: bool
    sum_of_squares: str


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
    sum_squares: float
    mean_square: float | None = None
    f_statistic: float | None = None
    p_value: float | None = None


class DoeLackOfFitBreakdownResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: bool
    unique_design_point_count: int
    pure_error: DoeAnovaRowResponse
    lack_of_fit: DoeAnovaRowResponse
    residual_df: int


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

    schema_version: Literal[1]
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
    factorial_replicates: int = Field(default=1, ge=1, le=4)
    axial_replicates: int = Field(default=1, ge=1, le=4)
    center_points: int = Field(default=5, ge=1, le=32)
    randomize: bool = True
    randomization_seed: int = Field(ge=0, le=2_147_483_647)


class ResponseSurfaceDesignOptionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alpha_mode: Literal["rotatable", "face_centered"]
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
    design_schema_version: Literal[1, 2]
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


class DoeResponseSurfaceAnalysisCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_name: str = Field(min_length=1, max_length=80)
    response_revision_id: UUID | None = None
    confidence_level: FiniteFloat = Field(default=0.95, gt=0, lt=1)
    point_limit: int = Field(default=256, ge=1, le=256)
    contour_grid_size: int = Field(default=21, ge=11, le=51)


class DoeResponseSurfaceCodingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    center: float
    factorial_low: float
    factorial_high: float
    axial_distance: float = Field(ge=1)
    actual_bounds_are_axial_bounds: bool


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


class DoeResponseSurfaceAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    summary_type: Literal["response_surface_analysis"]
    method: Literal["full_quadratic_ordinary_least_squares"]
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
    method_id: Literal["regression.response_optimizer"]
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
