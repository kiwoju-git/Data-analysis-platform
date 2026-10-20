"""Exact stored sources for reports; no client paths or computed values."""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.v1.schemas.report_capabilities import ReportSectionCapability

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
ReportSourceKind = Literal[
    "analysis_run",
    "regression_prediction",
    "doe_analysis",
    "doe_optimizer_result",
    "lhs_design_revision",
    "bayesian_history_revision",
]


class ReportModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnalysisRunReportSource(ReportModel):
    kind: Literal["analysis_run"] = "analysis_run"
    analysis_id: UUID
    expected_source_sha256: Sha256


class ResponseRevisionRef(ReportModel):
    response_revision_id: UUID
    response_revision_sha256: Sha256


class RsmPlotViewRef(ReportModel):
    plot_view_id: UUID
    expected_sha256: Sha256


class DoeAnalysisReportSource(ReportModel):
    kind: Literal["doe_analysis"] = "doe_analysis"
    family: Literal["factorial", "general_factorial", "response_surface"]
    design_id: UUID
    design_version_id: UUID
    design_sha256: Sha256
    analysis_id: UUID
    expected_source_sha256: Sha256
    response_revision: ResponseRevisionRef
    plot_view: RsmPlotViewRef | None = None

    @model_validator(mode="after")
    def validate_plot_family(self) -> DoeAnalysisReportSource:
        if self.plot_view is not None and self.family != "response_surface":
            raise ValueError("report_plot_view_family_invalid")
        return self


class DoeOptimizerDependency(ReportModel):
    analysis_id: UUID
    analysis_sha256: Sha256
    response_revision: ResponseRevisionRef


class ResponseSurfaceOptimizerRef(ReportModel):
    workflow: Literal["response_surface"] = "response_surface"
    design_id: UUID
    design_version_id: UUID
    design_sha256: Sha256
    optimization_id: UUID
    expected_source_sha256: Sha256
    source_bundle_sha256: Sha256
    source_dependencies: list[DoeOptimizerDependency] = Field(min_length=1, max_length=32)


class RegressionOptimizerRef(ReportModel):
    workflow: Literal["regression"] = "regression"
    analysis_id: UUID
    expected_source_sha256: Sha256


class DoeOptimizerReportSource(ReportModel):
    kind: Literal["doe_optimizer_result"] = "doe_optimizer_result"
    optimizer: Annotated[
        ResponseSurfaceOptimizerRef | RegressionOptimizerRef, Field(discriminator="workflow")
    ]


class LhsDesignReportSource(ReportModel):
    kind: Literal["lhs_design_revision"] = "lhs_design_revision"
    design_id: UUID
    design_version_id: UUID
    expected_source_sha256: Sha256
    response_revisions: list[ResponseRevisionRef] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def unique_revisions(self) -> LhsDesignReportSource:
        ids = [revision.response_revision_id for revision in self.response_revisions]
        if len(ids) != len(set(ids)):
            raise ValueError("report_duplicate_response_revision")
        return self


class NoBayesianAttachment(ReportModel):
    kind: Literal["none"] = "none"


class BayesianRecommendationAttachment(ReportModel):
    kind: Literal["recommendation"] = "recommendation"
    recommendation_id: UUID
    result_json_sha256: Sha256
    result_payload_sha256: Sha256


class BayesianBatchAttachment(ReportModel):
    kind: Literal["batch"] = "batch"
    batch_id: UUID
    result_json_sha256: Sha256
    result_payload_sha256: Sha256


class BayesianHistoryReportSource(ReportModel):
    kind: Literal["bayesian_history_revision"] = "bayesian_history_revision"
    study_id: UUID
    study_version_id: UUID
    definition_sha256: Sha256
    history_revision_id: UUID
    expected_source_sha256: Sha256
    attachment: Annotated[
        NoBayesianAttachment | BayesianRecommendationAttachment | BayesianBatchAttachment,
        Field(discriminator="kind"),
    ] = Field(default_factory=NoBayesianAttachment)


class AnalysisPredictionRef(ReportModel):
    storage: Literal["analysis_run"] = "analysis_run"
    analysis_id: UUID
    expected_source_sha256: Sha256


class CompletedPredictionRef(ReportModel):
    storage: Literal["completed_prediction"] = "completed_prediction"
    family: Literal["pls", "gaussian_process"]
    source_analysis_id: UUID
    source_result_sha256: Sha256
    model_id: UUID
    model_manifest_sha256: Sha256
    prediction_artifact_id: UUID
    expected_source_sha256: Sha256


class DoePredictionRef(ReportModel):
    storage: Literal["doe_prediction"] = "doe_prediction"
    source: DoeAnalysisReportSource
    prediction_id: UUID
    expected_source_sha256: Sha256


class RegressionPredictionReportSource(ReportModel):
    kind: Literal["regression_prediction"] = "regression_prediction"
    prediction: Annotated[
        AnalysisPredictionRef | CompletedPredictionRef | DoePredictionRef,
        Field(discriminator="storage"),
    ]


ReportSourceRef = Annotated[
    AnalysisRunReportSource
    | RegressionPredictionReportSource
    | DoeAnalysisReportSource
    | DoeOptimizerReportSource
    | LhsDesignReportSource
    | BayesianHistoryReportSource,
    Field(discriminator="kind"),
]


class ReportSourceQuery(ReportModel):
    source: ReportSourceRef
    locale: Literal["en", "ko"] = "ko"


class CreateManagedReportRequest(ReportSourceQuery):
    expected_source_ref_sha256: Sha256


class ReportSourceDescriptor(ReportModel):
    source: ReportSourceRef
    source_ref_sha256: Sha256
    title: str
    created_at: str
    stale: bool
    open_target: str


class ReportSourceList(ReportModel):
    items: list[ReportSourceDescriptor]
    limit: int
    offset: int
    has_more: bool


class StoredSourceSnapshot(ReportModel):
    schema_version: Literal[1] = 1
    source: ReportSourceRef
    source_ref_sha256: Sha256
    locale: Literal["en", "ko"]
    title: str
    created_at: str
    stale: bool
    payload: dict[str, Any]


class StoredReportCapability(ReportModel):
    capability_schema_version: Literal[1] = 1
    source: ReportSourceRef
    source_ref_sha256: Sha256
    title: str
    locale: Literal["en", "ko"]
    stale: bool
    report_level: Literal["full", "summary", "unsupported"]
    renderer_id: str | None
    renderer_version: str | None
    sections: list[ReportSectionCapability]
    reason: str | None = None
    html_available: bool


class ManagedReportDescriptor(ReportModel):
    export_id: UUID
    source: ReportSourceRef
    source_ref_sha256: Sha256
    locale: Literal["en", "ko"]
    report_level: Literal["full", "summary"]
    renderer_version: str
    sha256: Sha256
    size_bytes: int
    created_at: str
    stale: bool
    media_type: Literal["text/html"] = "text/html"


class ManagedReportList(ReportModel):
    items: list[ManagedReportDescriptor]


class ManagedReportActionRequest(ReportModel):
    source: ReportSourceRef
    expected_sha256: Sha256


class SavedPredictionDescriptor(ReportModel):
    source: RegressionPredictionReportSource
    created_at: str
