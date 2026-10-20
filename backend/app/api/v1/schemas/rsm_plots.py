"""Bounded, source-locked RSM plot views; clients never submit geometry."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
FactorId = Annotated[str, Field(pattern=r"^factor_[1-5]$")]
Vertex = tuple[FiniteFloat, FiniteFloat]


class PlotModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RsmContourLevels(PlotModel):
    count: int = Field(default=6, ge=2, le=11, strict=True)
    thresholds: list[FiniteFloat] | None = Field(default=None, min_length=2, max_length=11)

    @model_validator(mode="after")
    def ordered(self) -> RsmContourLevels:
        if self.thresholds is not None and any(
            first >= second
            for first, second in zip(self.thresholds, self.thresholds[1:], strict=False)
        ):
            raise ValueError("doe_rsm_contour_levels_invalid")
        return self


class RsmPlotSettings(PlotModel):
    plot_kind: Literal["contour", "main_effect", "interaction"] = "contour"
    x_factor_id: FactorId
    y_factor_id: FactorId | None = None
    held_actual_values: dict[FactorId, FiniteFloat] = Field(default_factory=dict, max_length=4)
    axis_scale: Literal["actual", "coded"] = "actual"
    grid_size: int = Field(default=21, ge=11, le=51, strict=True)
    contour_levels: RsmContourLevels = Field(default_factory=RsmContourLevels)
    trace_actual_values: list[FiniteFloat] | None = Field(default=None, min_length=2, max_length=5)
    filled: bool = True
    lines: bool = True
    design_points: bool = False

    @model_validator(mode="after")
    def axes(self) -> RsmPlotSettings:
        if self.grid_size % 2 == 0:
            raise ValueError("doe_rsm_contour_grid_size_invalid")
        if self.plot_kind == "main_effect":
            if self.y_factor_id is not None or self.trace_actual_values is not None:
                raise ValueError("doe_rsm_plot_axes_invalid")
        elif self.y_factor_id is None or self.x_factor_id == self.y_factor_id:
            raise ValueError("doe_rsm_plot_axes_invalid")
        if self.plot_kind != "interaction" and self.trace_actual_values is not None:
            raise ValueError("doe_rsm_plot_trace_invalid")
        return self


class RsmPlotSource(PlotModel):
    expected_result_sha256: Sha256
    response_revision_id: UUID
    response_revision_sha256: Sha256


class RsmPlotViewRequest(RsmPlotSource):
    settings: RsmPlotSettings


class RsmPlotAxis(PlotModel):
    factor_id: FactorId
    name: str
    unit: str | None = None
    minimum: FiniteFloat
    maximum: FiniteFloat


class RsmContourLine(PlotModel):
    level: FiniteFloat
    paths: list[list[Vertex]]


class RsmFilledPolygon(PlotModel):
    # Ring zero is the exterior; remaining rings are holes. Render with evenodd.
    rings: list[list[Vertex]]


class RsmContourBand(PlotModel):
    lower: FiniteFloat | None
    upper: FiniteFloat | None
    polygons: list[RsmFilledPolygon]


class RsmContourGeometry(PlotModel):
    algorithm: Literal["contourpy.serial"] = "contourpy.serial"
    algorithm_version: Literal["1.3.2"] = "1.3.2"
    grid_orientation: Literal["z[y_index][x_index]"] = "z[y_index][x_index]"
    minimum: FiniteFloat
    maximum: FiniteFloat
    constant: bool
    levels: list[FiniteFloat]
    lines: list[RsmContourLine]
    bands: list[RsmContourBand]


class RsmPlotPoint(PlotModel):
    point_id: str
    x: FiniteFloat
    y: FiniteFloat
    predicted: FiniteFloat
    outside_design_hull: bool


class RsmDesignPlotPoint(PlotModel):
    run_order: int
    x: FiniteFloat
    y: FiniteFloat
    on_slice: bool


class RsmCurve(PlotModel):
    series_id: str
    trace_actual_value: FiniteFloat | None = None
    points: list[RsmPlotPoint]


class RsmPlotBundle(PlotModel):
    schema_version: Literal[1] = 1
    settings: RsmPlotSettings
    x_axis: RsmPlotAxis
    y_axis: RsmPlotAxis | None
    response_name: str
    response_unit: str | None
    held_actual_values: dict[str, FiniteFloat]
    points: list[RsmPlotPoint]
    curves: list[RsmCurve]
    geometry: RsmContourGeometry | None
    design_points: list[RsmDesignPlotPoint]
    hull_slice_polygon: list[Vertex]
    hull_policy: Literal["full_design_coded_convex_hull"] = "full_design_coded_convex_hull"
    final_term_ids: list[str]


class RsmPlotViewResponse(RsmPlotSource):
    schema_version: Literal[1] = 1
    design_id: UUID
    design_version_id: UUID
    design_sha256: Sha256
    analysis_id: UUID
    view_sha256: Sha256
    bundle: RsmPlotBundle


class RsmPlotViewSaveRequest(RsmPlotViewRequest):
    expected_view_sha256: Sha256


class RsmPlotViewDescriptor(PlotModel):
    asset_id: UUID
    sha256: Sha256
    created_at: str


class RsmSavedPlotView(RsmPlotViewDescriptor):
    view: RsmPlotViewResponse
