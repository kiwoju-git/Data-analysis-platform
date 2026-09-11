from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator


class WorkflowModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DoeModelSelectionOptions(WorkflowModel):
    method: Literal["none", "backward_elimination"] = "none"
    alpha_to_remove: FiniteFloat = Field(default=0.05, gt=0, lt=1)
    hierarchy_policy: Literal["strong"] = "strong"
    saturated_start_policy: Literal["pool_smallest_adjusted_ss"] = "pool_smallest_adjusted_ss"
    display_step_details: bool = True


class SelectionStepCoefficient(WorkflowModel):
    column_index: int
    coefficient: FiniteFloat


class DoeModelSelectionStep(WorkflowModel):
    step: int
    phase: Literal["initial_full_model", "initial_pooling", "backward_elimination"]
    active_term_ids: list[str]
    removed_term_id: str | None
    removal_df: int | None
    removal_adjusted_ss: FiniteFloat | None
    removal_p_value: FiniteFloat | None
    stop_reason: str | None
    coefficients: list[SelectionStepCoefficient]
    sse: FiniteFloat
    residual_df: int
    residual_standard_error: FiniteFloat | None
    r_squared: FiniteFloat
    adjusted_r_squared: FiniteFloat | None
    press: FiniteFloat | None
    predicted_r_squared: FiniteFloat | None


class DoeModelSelectionResult(DoeModelSelectionOptions):
    tie_break_policy: str
    initial_model_saturated: bool
    initial_parameter_count: int
    initial_residual_df: int
    target_pool_count: int
    initial_term_ids: list[str]
    pooled_term_ids: list[str]
    removed_term_ids: list[str]
    final_term_ids: list[str]
    fixed_term_ids: list[str]
    stop_reason: str
    steps: list[DoeModelSelectionStep]
    post_selection_inference: Literal["exploratory", "not_selected"]


class DoeFinalCoefficient(WorkflowModel):
    term_id: str
    label: str
    kind: str
    factor_names: list[str]
    coefficient: FiniteFloat
    effect: FiniteFloat | None
    standard_error: FiniteFloat | None
    t_statistic: FiniteFloat | None
    p_value: FiniteFloat | None
    vif: FiniteFloat | None
    ci_lower: FiniteFloat | None
    ci_upper: FiniteFloat | None
    status: Literal["structural", "retained"]


class DoeFinalEquation(WorkflowModel):
    scale: Literal["coded", "treatment"]
    response_name: str
    intercept: FiniteFloat
    terms: list[DoeFinalCoefficient]
    display_equation: str


class DoePredictionFeature(WorkflowModel):
    term_id: str
    label: str
    kind: Literal["intercept", "main_effect", "interaction", "center_curvature", "block"]
    factor_names: list[str]
    level_indices: list[int]
    block_index: int | None


class DoePredictionBasis(WorkflowModel):
    schema_version: Literal[1]
    coding: Literal["coded", "treatment"]
    features: list[DoePredictionFeature]
    coefficients: list[FiniteFloat]
    xtx_inverse: list[list[FiniteFloat]]
    residual_mean_square: FiniteFloat | None
    residual_df: int
    confidence_level: FiniteFloat
    block_levels: list[int | None]
    center_settings: list[dict[str, FiniteFloat]]


class DoeResidualHistogramBin(WorkflowModel):
    lower: FiniteFloat
    upper: FiniteFloat
    count: int


class DoeResidualQqPoint(WorkflowModel):
    run_order: int
    theoretical_quantile: FiniteFloat
    residual: FiniteFloat


class DoeResidualReferenceLine(WorkflowModel):
    slope: FiniteFloat
    intercept: FiniteFloat


class DoeResidualScatterPoint(WorkflowModel):
    run_order: int
    fitted: FiniteFloat
    residual: FiniteFloat


class DoeResidualView(WorkflowModel):
    n: int
    histogram: list[DoeResidualHistogramBin]
    qq_points: list[DoeResidualQqPoint]
    reference_line: DoeResidualReferenceLine | None
    points: list[DoeResidualScatterPoint]


class DoeFinalDiagnosticPoint(DoeResidualScatterPoint):
    observed: FiniteFloat
    standardized_residual: FiniteFloat | None
    leverage: FiniteFloat
    cooks_distance: FiniteFloat | None


class DoeFinalResidualPlots(WorkflowModel):
    raw: DoeResidualView
    standardized: DoeResidualView
    points: list[DoeFinalDiagnosticPoint]
    n_total: int
    point_limit: int
    truncated: bool


class DoeFactorialPlotCell(WorkflowModel):
    settings: dict[str, FiniteFloat]
    fitted_mean: FiniteFloat
    data_mean: FiniteFloat | None
    n: int


class DoeFinalFactorialPlots(WorkflowModel):
    cells: list[DoeFactorialPlotCell]
    available: bool
    reason: str | None
    marginalization: Literal["equal_level_and_block_weights"]


class DoeFinalAnovaRow(WorkflowModel):
    label: str
    df: int
    adjusted_ss: FiniteFloat
    mean_square: FiniteFloat | None
    f_statistic: FiniteFloat | None
    p_value: FiniteFloat | None


class DoeFinalAnovaGroup(DoeFinalAnovaRow):
    kind: str
    terms: list[DoeFinalAnovaRow]


class DoeFinalModelWorkflow(WorkflowModel):
    equation: DoeFinalEquation
    coded_coefficients: list[DoeFinalCoefficient]
    anova_groups: list[DoeFinalAnovaGroup] = Field(default_factory=list)
    prediction_basis: DoePredictionBasis
    press: FiniteFloat | None
    predicted_r_squared: FiniteFloat | None
    residual_plots: DoeFinalResidualPlots
    factorial_plots: DoeFinalFactorialPlots
    warnings: list[str]


class DoePredictionRowRequest(WorkflowModel):
    row_id: str = Field(min_length=1, max_length=80)
    factor_settings: dict[str, FiniteFloat | str]
    block_index: int | None = None

    @field_validator("factor_settings", mode="before")
    @classmethod
    def bounded_settings(cls, value: object) -> object:
        if not isinstance(value, dict) or not 1 <= len(value) <= 10:
            raise ValueError("doe_factorial_prediction_factor_set_invalid")
        for name, setting in value.items():
            if not isinstance(name, str) or len(name) > 120:
                raise ValueError("doe_factorial_prediction_factor_set_invalid")
            if isinstance(setting, bool) or not isinstance(setting, str | int | float):
                raise ValueError("doe_factorial_prediction_input_invalid")
            if isinstance(setting, str) and (
                len(setting) > 120 or any(ord(char) < 32 for char in setting)
            ):
                raise ValueError("doe_factorial_prediction_input_invalid")
        return value


class DoePredictionPreflightRequest(WorkflowModel):
    rows: list[DoePredictionRowRequest] = Field(min_length=1, max_length=256)
    confidence_level: FiniteFloat = Field(default=0.95, gt=0, lt=1)


class DoePredictionCreateRequest(DoePredictionPreflightRequest):
    expected_preflight_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class DoePredictionRowIssue(WorkflowModel):
    row_id: str
    code: str
    factor_name: str | None = None


class DoePredictionPreflightResponse(WorkflowModel):
    schema_version: Literal[1] = 1
    design_id: UUID
    analysis_id: UUID
    source_analysis_sha256: str
    preflight_sha256: str
    valid: bool
    row_count: int
    issues: list[DoePredictionRowIssue]
    warnings: list[str]


class DoePredictionInterval(WorkflowModel):
    lower: FiniteFloat
    upper: FiniteFloat
    level: FiniteFloat


class DoePredictedRow(WorkflowModel):
    row_id: str
    factor_settings: dict[str, FiniteFloat | str]
    block_index: int | None
    fitted_mean: FiniteFloat
    standard_error_fit: FiniteFloat | None
    mean_confidence_interval: DoePredictionInterval | None
    individual_prediction_interval: DoePredictionInterval | None
    interval_unavailability_reason: str | None
    domain_status: Literal["in_domain"] = "in_domain"


class DoePredictionResponse(WorkflowModel):
    schema_version: Literal[1] = 1
    prediction_id: UUID
    design_id: UUID
    analysis_id: UUID
    response_revision_id: UUID
    response_revision_sha256: str
    source_analysis_sha256: str
    created_at: str
    rows: list[DoePredictedRow]
    warnings: list[str]


class DoeAnalysisAssetDescriptor(WorkflowModel):
    asset_id: UUID
    analysis_id: UUID
    kind: Literal["prediction", "html_report"]
    schema_version: Literal[1]
    locale: Literal["en", "ko"] | None
    source_analysis_sha256: str
    sha256: str
    media_type: str
    size_bytes: int
    created_at: str


class DoeAnalysisAssetList(WorkflowModel):
    analysis_id: UUID
    items: list[DoeAnalysisAssetDescriptor]


class DoeAnalysisAssetDeleteRequest(WorkflowModel):
    confirmation_asset_id: UUID
    expected_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class DoeAnalysisAssetDeleteResponse(WorkflowModel):
    asset_id: UUID
    deleted: Literal[True] = True


class DoeAnalysisHtmlExportRequest(WorkflowModel):
    locale: Literal["en", "ko"] = "ko"


class DoeAnalysisDeletionPreflight(WorkflowModel):
    analysis_id: UUID
    prediction_count: int
    report_count: int
    deletion_manifest_sha256: str


class DoeAnalysisDeleteRequest(WorkflowModel):
    confirmation_analysis_id: UUID
    expected_deletion_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
