"""Collect numerical diagnostics; never overwrite references or change production policy.

Run separately on each CI Python target. Successful collection is not a passing
acceptance test: mismatches and bounded Bayesian failures remain explicit JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import sys
import tempfile
import time
import warnings
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import numpy as np
from threadpoolctl import threadpool_info, threadpool_limits

from generate_gp_kernel_reference import generate

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = (
    ROOT / "backend/tests/reference/fixtures/gp_kernel_comparison_reference.json"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def load_test(name: str):
    path = ROOT / "backend/tests/unit" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the existing diagnostic test fixture")
    module = importlib.util.module_from_spec(spec)
    # pytest adds the repository root; a directly executed script does not.
    with patch.object(sys, "path", [str(ROOT), *sys.path]):
        spec.loader.exec_module(module)
    return module


def pools() -> list[dict]:
    return [
        {
            **{key: value for key, value in item.items() if key != "filepath"},
            "library_filename": Path(item["filepath"]).name,
        }
        for item in threadpool_info()
    ]


def scalar_difference(actual: float, expected: float, *, relative: bool = True) -> dict:
    allowed = max(1e-6, 1e-6 * abs(expected)) if relative else 1e-6
    delta = abs(actual - expected)
    return {
        "actual": actual,
        "expected": expected,
        "absolute_difference": delta,
        "allowed_tolerance": allowed,
        "within_existing_tolerance": delta <= allowed,
    }


def candidate_differences(actual: dict, expected: dict) -> dict:
    if actual["status"] != "succeeded":
        return {"preset": actual["preset"], "status": actual["status"]}
    details = actual["details"]
    points = details["diagnostics"]["points"]
    differences = {
        "preset": actual["preset"],
        "status": actual["status"],
        "metrics": {
            key: scalar_difference(actual["metrics"][key], value)
            for key, value in expected["metrics"].items()
        },
        "lml": scalar_difference(
            details["kernel"]["log_marginal_likelihood"], expected["lml"]
        ),
    }
    for name, key in (
        ("oof_mean", "cross_validated_fitted"),
        ("oof_sd", "cross_validated_predictive_standard_deviation"),
    ):
        observed = [point[key] for point in points]
        differences[name] = [
            scalar_difference(left, right, relative=False)
            for left, right in zip(observed, expected[name], strict=True)
        ]
    return differences


def gp_probe(output: Path) -> dict:
    before = digest(REFERENCE)
    windows = json.loads(REFERENCE.read_text(encoding="utf-8"))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        independent = generate()
    write_json(output / "gp-independent-reference.json", independent)
    test = load_test("test_gaussian_process_kernel_selection")
    generated_cases = {case["name"]: case for case in independent["cases"]}
    runs = []
    input_comparison = []
    for original in windows["cases"]:
        fresh = generated_cases[original["name"]]
        input_comparison.append(
            {
                "name": original["name"],
                "x_identical": original["x"] == fresh["x"],
                "y_identical": original["y"] == fresh["y"],
                "maximum_x_delta": float(
                    np.max(np.abs(np.asarray(original["x"]) - fresh["x"]))
                ),
                "maximum_y_delta": float(
                    np.max(np.abs(np.asarray(original["y"]) - fresh["y"]))
                ),
            }
        )
        # Retain both inputs so platform-specific synthetic arithmetic cannot
        # silently replace the original Windows reference's test observations.
        for input_source, case in (
            ("independent_current_platform", fresh),
            ("committed_windows", original),
        ):
            result = test.calculate(case, test.options(retain_candidate_details=True))
            references = {item["preset"]: item for item in case["candidates"]}
            runs.append(
                {
                    "name": case["name"],
                    "input_source": input_source,
                    "expected_selected": case["selected"]["nlpd"],
                    "kernel_selection": result["kernel_selection"],
                    "candidates": result["kernel_candidates"],
                    "differences": [
                        candidate_differences(item, references[item["preset"]])
                        for item in result["kernel_candidates"]
                    ],
                }
            )
    report = {
        "committed_windows_fixture_sha256_before": before,
        "committed_windows_fixture_sha256_after": digest(REFERENCE),
        "independent_generator_warning_categories": dict(
            Counter(item.category.__name__ for item in caught)
        ),
        "input_comparison": input_comparison,
        "runs": runs,
    }
    assert report["committed_windows_fixture_sha256_after"] == before
    write_json(output / "gp-production-comparison.json", report)
    return {
        "independent_reference": "gp-independent-reference.json",
        "production_comparison": "gp-production-comparison.json",
        "windows_fixture_unchanged": True,
    }


def bayesian_probe(output: Path, temporary: Path, evaluations: int) -> dict:
    from fastapi.testclient import TestClient

    from app.core.config import Settings
    from app.statistics.bayesian_optimization import BayesianOptimizationError

    test = load_test("test_bayesian_recommendations_api")
    worker_results: list[dict] = []

    def run_in_process(payload: dict, *, timeout_ms: int) -> dict:
        assert timeout_ms > 0
        started = time.perf_counter()
        try:
            result = test.calculate_bayesian_recommendation(payload)
        except BayesianOptimizationError as exc:
            worker_results.append(
                {
                    "status": "failed",
                    "failure_code": exc.code,
                    "search": payload["search"],
                    "completed_observations": len(payload["observations"]),
                    "elapsed_seconds": time.perf_counter() - started,
                }
            )
            raise
        worker_results.append(
            {
                "status": "succeeded",
                "result": result,
                "search": payload["search"],
            }
        )
        return result

    report = {
        "model_max_evaluations_in_test_request": evaluations,
        "production_defaults_changed": False,
        "requested_records": 21,
        "completed_records": 0,
        "status": "running",
        "steps": [],
        "workers": worker_results,
    }
    settings = Settings(workspace_root=temporary / f"bayesian-{evaluations}")
    with patch("app.services.bayesian_recommendations._run_worker", run_in_process):
        with TestClient(test.create_app(settings)) as client:
            study = test._complete_initial_trials(client, test._create_study(client))
            ids = []
            for index in range(21):
                request = test._recommendation_request(
                    study["observation_history"]["history_revision_id"],
                    total_trial_budget=30,
                    random_seed=100 + index,
                    candidate_count=32,
                    local_start_count=0,
                )
                request["search"]["model_max_evaluations"] = evaluations
                try:
                    response = client.post(
                        f"/api/v1/bayesian-studies/{study['study_id']}/recommendations",
                        json=request,
                    )
                except BayesianOptimizationError as exc:
                    report.update(
                        status="failed", failure_code=exc.code, failed_record=index + 1
                    )
                    break
                if response.status_code != 201:
                    report.update(
                        status="failed",
                        failure_code=response.json().get("error", {}).get("code"),
                        http_status=response.status_code,
                        failed_record=index + 1,
                    )
                    break
                created = response.json()
                ids.append(created["recommendation_id"])
                x_value = created["trial"]["actual_coordinates"]["x"]
                completed = client.put(
                    f"/api/v1/bayesian-studies/{study['study_id']}"
                    f"/trials/{created['trial']['trial_id']}/observation",
                    json={
                        "objective_value": 1.0 - (x_value - 0.25) ** 2,
                        "expected_history_revision_id": study["observation_history"][
                            "history_revision_id"
                        ],
                    },
                )
                assert completed.status_code == 200
                restored = client.get(f"/api/v1/bayesian-studies/{study['study_id']}")
                assert restored.status_code == 200
                study = restored.json()
                report["completed_records"] = index + 1
                report["steps"].append(
                    {"record": index + 1, "random_seed": 100 + index, "x": x_value}
                )
            else:
                base = f"/api/v1/bayesian-studies/{study['study_id']}/recommendations"
                page = client.get(base + "?offset=0&limit=20")
                latest = client.get(base + "/latest")
                oldest = client.get(base + "/" + ids[0])
                assert (
                    page.status_code == latest.status_code == oldest.status_code == 200
                )
                checks = {
                    "total_is_21": page.json()["total"] == 21,
                    "page_length_is_20": len(page.json()["items"]) == 20,
                    "first_page_has_no_latest": all(
                        not row["is_latest"] for row in page.json()["items"]
                    ),
                    "latest_id_matches": latest.json()["item"]["recommendation_id"]
                    == ids[-1],
                    "latest_is_latest": latest.json()["item"]["is_latest"] is True,
                    "latest_snapshot_pending": latest.json()["item"]["trial"]["state"]
                    == "pending",
                    "latest_current_completed": latest.json()["item"]["current_trial"][
                        "state"
                    ]
                    == "completed",
                    "requested_trial_budget_is_30": latest.json()["item"][
                        "requested_total_trial_budget"
                    ]
                    == 30,
                    "oldest_is_not_latest": oldest.json()["is_latest"] is False,
                    "oldest_snapshot_pending": oldest.json()["trial"]["state"]
                    == "pending",
                    "oldest_current_completed": oldest.json()["current_trial"]["state"]
                    == "completed",
                }
                report.update(
                    status="succeeded" if all(checks.values()) else "failed",
                    checks=checks,
                )
    write_json(output / f"bayesian-lifecycle-evaluations-{evaluations}.json", report)
    return {
        key: report[key]
        for key in (
            "model_max_evaluations_in_test_request",
            "completed_records",
            "status",
        )
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if sys.flags.optimize:
        parser.error("Run diagnostics without Python optimization")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        parser.error("Use a new empty output directory to preserve earlier evidence")
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(
        prefix="numerics-workspace-", dir=output
    ) as temporary:
        with patch.dict(
            os.environ, {"DATALAB_WORKSPACE_ROOT": str(Path(temporary) / "import-only")}
        ):
            with threadpool_limits(limits=1):
                environment = {
                    "platform": platform.platform(),
                    "system": platform.system(),
                    "architecture": platform.machine(),
                    "python": platform.python_version(),
                    "python_implementation": platform.python_implementation(),
                    "source_commit_from_ci": os.environ.get("GITHUB_SHA"),
                    "native_threadpools_limited_to_one": pools(),
                    "generator_sha256": digest(
                        ROOT / "scripts/generate_gp_kernel_reference.py"
                    ),
                    "production_gp_sha256": digest(
                        ROOT / "backend/app/statistics/gaussian_process_regression.py"
                    ),
                    "production_kernel_selection_sha256": digest(
                        ROOT
                        / "backend/app/statistics/gaussian_process_kernel_selection.py"
                    ),
                    "production_bayesian_sha256": digest(
                        ROOT / "backend/app/statistics/bayesian_optimization.py"
                    ),
                    "comparison_tolerance_policy": "Existing tests: abs=1e-6, rel=1e-6; OOF abs=1e-6",
                }
                write_json(output / "environment.json", environment)
                gp = gp_probe(output)
                bayesian = [
                    bayesian_probe(output, Path(temporary), count)
                    for count in (100, 200)
                ]
    summary = {
        "status": "diagnostics_collected_not_acceptance",
        "gp": gp,
        "bayesian": bayesian,
        "elapsed_seconds": time.perf_counter() - started,
    }
    write_json(output / "probe-summary.json", summary)
    print(json.dumps(summary, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
