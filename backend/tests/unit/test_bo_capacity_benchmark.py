"""The resource receipt must represent real independent fits, not copied states."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "benchmark_bo_capacity.py"


def _module():
    spec = importlib.util.spec_from_file_location("bo_capacity_benchmark", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("kind", ["numeric", "mixed"])
def test_capacity_fixture_retains_500_distinct_rows_and_six_distinct_targets(kind):
    module = _module()
    payload = module.synthetic_request(kind, 500, 6)
    assert len(payload["observations"]) == 500
    assert len(payload["response_models"]) == 6
    assert len({row["trial_id"] for row in payload["observations"]}) == 500
    assert (
        len({tuple(row["actual_coordinates"].values()) for row in payload["observations"]}) == 500
    )
    vectors = [
        tuple(row["response_values"][f"y{i}"] for row in payload["observations"]) for i in range(6)
    ]
    assert len(set(vectors)) == 6
    assert all(m["surrogate"]["noise_mode"] == "estimate" for m in payload["response_models"])
    assert payload["search"]["time_budget_ms"] == 60_000
    assert module.synthetic_request(kind, 500, 6) == payload


def test_benchmark_rejects_unsupported_capacity_without_silent_sampling():
    module = _module()
    for rows, responses in [(501, 6), (500, 7), (1, 6), (500, 0)]:
        with pytest.raises(ValueError):
            module.synthetic_request("numeric", rows, responses)


def test_small_benchmark_runs_each_model_and_checks_disk_restore(tmp_path):
    module = _module()
    receipt = module.run_case("numeric", 12, 2, tmp_path)
    assert receipt["status"] == "passed"
    assert receipt["raw_observations_per_model"] == [12, 12]
    assert receipt["optimized_models"] == 2
    assert len(receipt["optimizer_records"]) == 2
    assert receipt["restore_predictions_identical"]
    assert receipt["source_unchanged"]
    assert receipt["fit_evaluations"] > 0
    assert receipt["snapshot_bytes"] > 0
