from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictStr, model_validator


class GpSurfaceViewSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    x_column_id: str = Field(min_length=1)
    y_column_id: str = Field(min_length=1)
    hold_values: dict[str, StrictFloat | StrictStr] = Field(default_factory=dict, max_length=12)
    grid_size: int = Field(ge=2, le=40, strict=True)
    display_mode: Literal["mean", "latent_sd", "predictive_sd"] = "mean"

    @model_validator(mode="after")
    def distinct_axes(self) -> "GpSurfaceViewSpec":
        if self.x_column_id == self.y_column_id:
            raise ValueError("gp_surface_view_invalid")
        return self
