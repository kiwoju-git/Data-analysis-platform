from __future__ import annotations

import json
from html.parser import HTMLParser

import numpy as np
import pytest
from test_gp_validation_extension import _columns, _options

from app.services.gaussian_process_report import gp_saved_sections
from app.statistics.gaussian_process_regression import calculate_gaussian_process_regression


class _PlotPoints(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.coordinates: list[tuple[float, float]] = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "data-x" in values and "data-y" in values:
            self.coordinates.append((float(values["data-x"]), float(values["data-y"])))


@pytest.mark.parametrize("with_lag", [False, True])
def test_time_report_uses_only_scored_points_and_preserves_stored_plan(with_lag, monkeypatch):
    columns = _columns()
    result = calculate_gaussian_process_regression(
        [[str(np.sin(index / 3)), str(index), "series-a", str(index)] for index in range(24)],
        columns[0],
        columns[1:2],
        metadata_columns=columns[2:],
        options=_options(
            validation_method="time_series_split",
            cv_shuffle=False,
            time_column_id="time",
            time_format="numeric",
            time_unit="seconds",
            lagged_column_ids=("y",) if with_lag else (),
            lags=(1,) if with_lag else (),
            gap_time_blocks=1,
        ),
    )
    payload = {key: value for key, value in result.items() if key != "prediction_basis"}
    before = json.dumps(payload, sort_keys=True, allow_nan=False)
    points = payload["diagnostics"]["points"]
    expected = [
        (point["observed"], point["cross_validated_fitted"])
        for point in points
        if point["cross_validated_fitted"] is not None
    ]
    assert 0 < len(expected) < len(points)
    assert len(expected) == payload["validation_plan"]["n_scored"]

    def forbidden(*args, **kwargs):
        raise AssertionError("stored report must not fit, predict, or read raw rows")

    monkeypatch.setattr("app.statistics.gaussian_process_regression._fit_model", forbidden)
    monkeypatch.setattr("app.services.dataset_rows.get_dataset_rows_context", forbidden)
    monkeypatch.setattr(
        "app.services.gaussian_process_predictions.predict_from_gaussian_process_state", forbidden
    )
    for locale in ("en", "ko"):
        sections = {section.section_id: section for section in gp_saved_sections(payload, locale)}
        graph = _PlotPoints()
        graph.feed(sections["gp_cv_plot"].markup)
        assert graph.coordinates == expected
        plan = sections["gp_validation_plan"].markup
        assert payload["validation_plan"]["split_plan_sha256"] in plan
        assert "n_scored" in plan and "n_excluded_lag_embargo" in plan
        assert "<table" in plan
        lineage = sections["gp_feature_lineage"]
        assert lineage.status == ("rendered" if with_lag else "not_applicable")
        if with_lag:
            assert "gp_lag:y:1" in lineage.markup
    assert json.dumps(payload, sort_keys=True, allow_nan=False) == before
