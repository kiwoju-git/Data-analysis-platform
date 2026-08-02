from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.v1.schemas.analyses import AnalysisFilterSnapshot

GraphType = Literal[
    "box_plot",
    "individual_value_plot",
    "histogram",
    "qq_plot",
    "ecdf",
    "scatter_plot",
    "run_chart",
    "imr_chart",
]
GraphLayout = Literal["combined", "overlay", "small_multiples"]
GraphComparisonMode = Literal["multiple_values", "one_value_by_group"]


class GraphPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_version_id: UUID
    filter_snapshot: AnalysisFilterSnapshot = Field(default_factory=AnalysisFilterSnapshot)
    graph_type: GraphType
    value_column_ids: list[str] = Field(default_factory=list)
    x_column_id: str | None = None
    y_column_ids: list[str] = Field(default_factory=list)
    group_column_id: str | None = None
    order_column_id: str | None = None
    point_limit: int = Field(default=1000, ge=10, le=2000)
    histogram_bin_count: int | None = Field(default=None, ge=1, le=200)
    layout: GraphLayout = "small_multiples"
    comparison_mode: GraphComparisonMode = "multiple_values"
    group_order_policy: Literal["first_occurrence"] = "first_occurrence"
    missing_group_policy: Literal["exclude"] = "exclude"

    @model_validator(mode="after")
    def validate_roles(self) -> "GraphPreviewRequest":
        if self.graph_type == "scatter_plot":
            if self.x_column_id is None or not self.y_column_ids:
                raise ValueError("scatter_plot requires x_column_id and y_column_ids")
            if len(self.y_column_ids) > 6:
                raise ValueError("scatter_plot supports at most 6 Y columns")
            return self

        if not self.value_column_ids:
            raise ValueError(f"{self.graph_type} requires value_column_ids")
        limits = {
            "box_plot": 12,
            "individual_value_plot": 8,
            "histogram": 8,
            "qq_plot": 8,
            "ecdf": 6,
            "run_chart": 6,
            "imr_chart": 6,
        }
        if len(self.value_column_ids) > limits[self.graph_type]:
            raise ValueError(f"{self.graph_type} has too many value columns")
        comparison_graphs = {"box_plot", "individual_value_plot", "imr_chart"}
        if self.comparison_mode == "one_value_by_group":
            if self.graph_type not in comparison_graphs:
                raise ValueError("group comparison is not supported for this graph type")
            if self.group_column_id is None or len(self.value_column_ids) != 1:
                raise ValueError("group comparison requires one value and one group column")
        elif self.group_column_id is not None and self.graph_type in comparison_graphs:
            raise ValueError("multiple value comparison does not accept group_column_id")
        return self


class GraphPreviewPanel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    panel_id: str
    kind: Literal[
        "graphical_summary",
        "individual_values",
        "scatter",
        "run_chart",
        "imr_chart",
    ]
    label: str
    unit: str | None
    status: Literal["succeeded", "failed"]
    error_code: str | None = None
    result: dict[str, Any] | None = None


class GraphPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    visualization_schema_version: Literal[2] = 2
    graph_type: GraphType
    dataset_version_id: UUID
    source_schema_hash: str
    filter_snapshot_sha256: str
    preview_config_sha256: str
    row_count_total: int
    row_count_included: int
    warnings: list[str]
    layout: GraphLayout
    comparison_mode: GraphComparisonMode
    group_order_policy: Literal["first_occurrence"]
    missing_group_policy: Literal["exclude"]
    missing_group_row_count: int = Field(ge=0)
    panels: list[GraphPreviewPanel]
