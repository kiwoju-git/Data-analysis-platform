"""Validate and render stored GP grid requests without fitting or predicting."""

import math
from collections.abc import Sequence
from typing import Any

from app.api.v1.schemas.gp_views import GpSurfaceViewSpec
from app.statistics.gaussian_process_regression import GaussianProcessRegressionError


def validate_gp_surface_view(
    view: GpSurfaceViewSpec | None,
    rows: Sequence[Any],
    predictors: Sequence[dict[str, Any]],
) -> None:
    if view is None:
        return
    by_id = {item["column_id"]: item for item in predictors}
    axes = {view.x_column_id, view.y_column_id}
    if (
        len(axes) != 2
        or not axes <= set(by_id)
        or any(by_id[key].get("kind", "numeric") != "numeric" for key in axes)
        or set(view.hold_values) != set(by_id) - axes
        or len(rows) != view.grid_size**2
    ):
        raise GaussianProcessRegressionError("gp_surface_view_invalid")
    pairs: set[tuple[float, float]] = set()
    ids: set[str] = set()
    for row in rows:
        values = row.values
        if (
            set(values) != set(by_id)
            or row.client_row_id in ids
            or any(values[key] != value for key, value in view.hold_values.items())
        ):
            raise GaussianProcessRegressionError("gp_surface_view_invalid")
        coordinates = (values[view.x_column_id], values[view.y_column_id])
        if any(
            type(value) not in {int, float} or not math.isfinite(value) for value in coordinates
        ):
            raise GaussianProcessRegressionError("gp_surface_view_invalid")
        pair = (float(coordinates[0]), float(coordinates[1]))
        if pair in pairs:
            raise GaussianProcessRegressionError("gp_surface_view_invalid")
        pairs.add(pair)
        ids.add(row.client_row_id)
    if (
        len({pair[0] for pair in pairs}) != view.grid_size
        or len({pair[1] for pair in pairs}) != view.grid_size
    ):
        raise GaussianProcessRegressionError("gp_surface_view_invalid")


def stored_surface_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], str] | None:
    view = payload["request"].get("surface_view")
    if view is None:
        return None
    spec = GpSurfaceViewSpec.model_validate(view)
    predictors = payload["predictors"]
    by_column = {item["column_id"]: item for item in predictors}
    by_row = {row["client_row_id"]: row for row in payload["result"]["rows"]}
    points = []
    for row in payload["request"]["rows"]:
        predicted = by_row[row["client_row_id"]]
        points.append(
            {
                "x": row["values"][spec.x_column_id],
                "y": row["values"][spec.y_column_id],
                "predicted_mean": predicted["predicted_mean"],
                "latent_standard_deviation": predicted["latent_standard_deviation"],
                "predictive_standard_deviation": predicted["predictive_standard_deviation"],
            }
        )
    return {
        "predictors": predictors,
        "response": payload["response"],
        "two_predictor_surface": {
            "x_column_id": spec.x_column_id,
            "y_column_id": spec.y_column_id,
            "x_display_name": by_column[spec.x_column_id]["display_name"],
            "y_display_name": by_column[spec.y_column_id]["display_name"],
            "fixed_values": [spec.hold_values.get(item["column_id"]) for item in predictors],
            "points": points,
        },
    }, spec.display_mode
