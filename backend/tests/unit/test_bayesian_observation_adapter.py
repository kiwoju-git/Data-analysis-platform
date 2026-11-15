"""Reuse only the fixed schema, never observations or validation outcomes."""

from dataclasses import replace

import pydantic
import pytest

from app.core.errors import ApiError
from app.services import bayesian_studies as service
from app.storage.bayesian_studies import BayesianTrialRecord


def trial(payload='{"yield":40,"cost":3}'):
    return BayesianTrialRecord(
        trial_id="synthetic-trial",
        study_version_id="synthetic-version",
        trial_number=1,
        origin="initial_design",
        state="completed",
        actual_coordinates_json='{"x":1}',
        normalized_coordinates_json='{"x":0.1}',
        coordinates_sha256="a" * 64,
        objective_value=None,
        created_at="2026-11-14T00:00:00Z",
        closed_at="2026-11-14T00:00:00Z",
        response_values_json=payload,
    )


def test_500_vector_reads_do_not_rebuild_the_fixed_schema(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("The fixed response schema must not rebuild for each observation")

    monkeypatch.setattr(pydantic, "TypeAdapter", forbidden)
    source = trial()
    for index in range(500):
        assert service._trial_observation(replace(source, trial_number=index + 1)) == {
            "yield": 40.0,
            "cost": 3.0,
        }


@pytest.mark.parametrize(
    "payload",
    [
        '{"yield":40,"yield":40,"cost":3}',
        '{"yield":NaN}',
        '{"yield":Infinity}',
        '{"yield":true}',
        '{"yield":"40"}',
        '{"yield":null}',
        '{"invalid response id":40}',
        '{"a":1,"b":2,"c":3,"d":4,"e":5}',
        "{}",
        "[]",
        "null",
        "invalid JSON",
    ],
)
def test_every_vector_read_still_validates_and_redacts_corrupt_values(payload):
    source = trial()
    assert service._trial_observation(source) == {"yield": 40.0, "cost": 3.0}
    with pytest.raises(ApiError) as error:
        service._trial_observation(replace(source, response_values_json=payload))
    assert error.value.code == "bayesian_study_artifact_mismatch"
    assert payload not in error.value.message


def test_returned_values_are_not_cached_and_scalar_guard_is_unchanged():
    source = trial()
    first = service._trial_observation(source)
    assert isinstance(first, dict)
    first["yield"] = -1
    assert service._trial_observation(source) == {"yield": 40.0, "cost": 3.0}
    scalar = replace(source, response_values_json=None, objective_value=7.0)
    assert service._trial_observation(scalar) == 7.0
    assert service._trial_observation(replace(scalar, objective_value=None)) is None
    with pytest.raises(ApiError) as error:
        service._trial_observation(replace(source, objective_value=7.0))
    assert error.value.code == "bayesian_study_artifact_mismatch"
