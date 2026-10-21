from types import SimpleNamespace

import pytest

from app.api.v1.schemas.gp_views import GpSurfaceViewSpec
from app.services.gp_surface_views import validate_gp_surface_view


def fixture():
    spec = GpSurfaceViewSpec(
        x_column_id="x",
        y_column_id="y",
        hold_values={"category": "A"},
        grid_size=2,
        display_mode="latent_sd",
    )
    predictors = [
        {"column_id": "x", "kind": "numeric"},
        {"column_id": "y", "kind": "numeric"},
        {"column_id": "category", "kind": "nominal"},
    ]
    rows = [
        SimpleNamespace(client_row_id=f"{x}:{y}", values={"x": x, "y": y, "category": "A"})
        for x in [0.0, 1.0]
        for y in [10.0, 20.0]
    ]
    return spec, rows, predictors


def test_complete_grid_preserves_applied_pair_holds_and_mode():
    spec, rows, predictors = fixture()
    validate_gp_surface_view(spec, rows, predictors)
    validate_gp_surface_view(spec, list(reversed(rows)), predictors)
    assert spec.display_mode == "latent_sd"
    assert rows[0].values["category"] == "A"


@pytest.mark.parametrize("case", ["missing", "duplicate", "holds", "categorical_axis", "extra"])
def test_invalid_grid_or_identity_is_not_stored_as_a_surface(case):
    spec, rows, predictors = fixture()
    if case == "missing":
        rows.pop()
    elif case == "duplicate":
        rows[-1] = rows[0]
    elif case == "holds":
        rows[0].values["category"] = "B"
    elif case == "categorical_axis":
        spec = spec.model_copy(update={"x_column_id": "category"})
    else:
        rows[0].values["unexpected"] = 1
    with pytest.raises(ValueError, match="gp_surface_view_invalid"):
        validate_gp_surface_view(spec, rows, predictors)


def test_surface_metadata_is_optional_for_legacy_predictions():
    validate_gp_surface_view(None, [], [])
