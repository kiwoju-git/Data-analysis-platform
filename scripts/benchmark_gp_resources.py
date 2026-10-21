"""Synthetic native-target Exact GP admission, execution and restoration benchmark."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    import math

    from fastapi.testclient import TestClient

    from app.analyses.registry import METHOD_VERSIONS
    from app.core.config import Settings
    from app.main import create_app
    from app.services.gp_worker import worker_peak_resident_bytes
    from app.storage.metadata import get_analysis_run_record

    n, mixed, mode, validation = (
        case["rows"],
        case["predictors"] == "mixed",
        case["mode"],
        case["validation"],
    )
    lines = ["response,x,category,group,time"]
    for index in range(n):
        x = index / (n - 1)
        y = math.sin(8 * x) + (index % 2) * 0.4 + 0.03 * math.sin(index * 0.7)
        lines.append(
            f"{y:.17g},{x:.17g},{'A' if index % 2 else 'B'},batch-{index % 7},{index}"
        )
    csv_bytes = "\n".join(lines).encode("utf-8")
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="gp-benchmark-") as directory:
        workspace = Path(directory) / "synthetic workspace"
        with TestClient(create_app(Settings(workspace_root=workspace))) as client:
            upload = client.post(
                "/api/v1/datasets", files={"file": ("synthetic.csv", csv_bytes)}
            )
            upload.raise_for_status()
            parsed = client.post(
                f"/api/v1/datasets/{upload.json()['dataset_id']}/confirm-parsing",
                json={
                    "parsing": {
                        "kind": "delimited_text",
                        "encoding": "utf-8",
                        "delimiter": ",",
                        "quote_char": '"',
                        "decimal": ".",
                        "thousands": None,
                        "has_header": True,
                        "header_row": 1,
                        "data_start_row": 2,
                        "missing_tokens": ["", "NA"],
                    },
                    "columns": [],
                },
            )
            parsed.raise_for_status()
            version = parsed.json()
            ids = [column["column_id"] for column in version["columns"]]
            if mixed:
                schema = client.patch(
                    f"/api/v1/dataset-versions/{version['version_id']}/schema",
                    json={
                        "expected_schema_hash": version["schema_hash"],
                        "columns": [
                            {
                                "column_id": ids[2],
                                "display_name": "Synthetic category",
                                "measurement_level": "nominal",
                                "role": "feature",
                                "unit": None,
                            }
                        ],
                    },
                )
                schema.raise_for_status()
            cv: dict[str, Any] = {
                "method": validation,
                "folds": 3,
                "shuffle": False,
                "seed": 103,
            }
            if validation == "group_k_fold":
                cv["group_column_id"] = ids[3]
            elif validation == "time_series_split":
                cv.update(
                    time_column_id=ids[4], time_format="numeric", time_unit="second"
                )
            options = {
                "response_column_id": ids[0],
                "predictor_column_ids": [ids[1], ids[2]] if mixed else [ids[1]],
                "resource_profile": "extended_exact",
                "optimizer_restarts": 0,
                "cv_optimizer_restarts": 0,
                "cv": cv,
                "noise_mode": "fixed",
                "fixed_noise_standard_deviation": 0.03,
                "profile_points": 10,
                "surface_grid_size": 10,
                "time_budget_seconds": 180,
                "kernel_selection": {
                    "mode": "single",
                    "kernel_preset": "matern_5_2_ard",
                }
                if mode == "single"
                else {
                    "mode": "compare",
                    "kernel_candidates": ["matern_5_2_ard", "rbf_ard"],
                    "criterion": "cv_nlpd",
                    "retain_candidate_details": False,
                },
            }
            analysis_started = time.perf_counter()
            created = client.post(
                "/api/v1/analysis-runs",
                json={
                    "method_id": "regression.gaussian_process",
                    "method_version": METHOD_VERSIONS["regression.gaussian_process"],
                    "dataset_version_id": version["version_id"],
                    "roles": {},
                    "options": options,
                },
            )
            execution_seconds = time.perf_counter() - analysis_started
            if created.status_code != 201:
                error = created.json().get("error", {}).get("code")
                return {
                    **case,
                    "status": "admission_rejected"
                    if error == "gp_memory_budget_exceeded"
                    else "failed",
                    "error_code": error,
                    "http_status": created.status_code,
                    "execution_seconds": execution_seconds,
                    "parent_process_peak_rss_bytes": worker_peak_resident_bytes(),
                }
            envelope = created.json()
            result = envelope["result"]
            assert result["sample"]["n_used"] == n
            owner = get_analysis_run_record(workspace, envelope["analysis_id"])
            assert owner is not None
            stored = (workspace / owner.result_path).read_bytes()
            restored = client.get(
                f"/api/v1/analysis-runs/{envelope['analysis_id']}/result"
            )
            assert restored.status_code == 200
            assert restored.json()["result"] == result
            pointer = result["model_manifest"]
            predicted = client.post(
                f"/api/v1/regression-models/{pointer['model_id']}/gaussian-process-predictions",
                json={
                    "expected_model_manifest_sha256": pointer["manifest_sha256"],
                    "rows": [
                        {
                            "client_row_id": "verify-training",
                            "values": {ids[1]: 0.0, **({ids[2]: "B"} if mixed else {})},
                        }
                    ],
                },
            )
            assert predicted.status_code == 200, predicted.text
            first = next(
                point
                for point in result["diagnostics"]["points"]
                if point["row_index"] == 0
            )
            prediction_error = abs(
                predicted.json()["rows"][0]["predicted_mean"] - first["fitted"]
            )
            assert prediction_error <= 1e-9
            assert (workspace / owner.result_path).read_bytes() == stored
            return {
                **case,
                "status": "passed",
                "execution_seconds": execution_seconds,
                "total_seconds": time.perf_counter() - started,
                "fit_seconds": result["optimization"].get("final_fit_elapsed_seconds"),
                "cv_fit_seconds": result["optimization"].get("cv_fit_elapsed_seconds"),
                "resource_budget": result["resource_budget"],
                "parent_process_peak_rss_bytes": worker_peak_resident_bytes(),
                "restored_prediction_absolute_error": prediction_error,
                "result_sha256": hashlib.sha256(stored).hexdigest(),
                "fixture_sha256": hashlib.sha256(csv_bytes).hexdigest(),
                "source_checksum_unchanged": True,
            }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rows", type=int, nargs="+", default=[501, 1000, 2000])
    parser.add_argument("--case", help=argparse.SUPPRESS)
    args = parser.parse_args()
    for key in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        os.environ[key] = "1"
    if args.case:
        case = json.loads(args.case)
        if (
            case.get("rows") not in {501, 1000, 2000}
            or case.get("predictors") not in {"numeric", "mixed"}
            or case.get("mode") not in {"single", "compare"}
            or case.get("validation")
            not in {"k_fold", "group_k_fold", "time_series_split"}
        ):
            parser.error("Unsupported synthetic benchmark case")
        result = run_case(case)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        return int(result["status"] == "failed")
    if not set(args.rows) <= {501, 1000, 2000}:
        parser.error("--rows supports 501 1000 2000")
    cases = [
        dict(rows=n, predictors=kind, mode=mode, validation=cv)
        for n, kind, mode, cv in itertools.product(
            args.rows,
            ["numeric", "mixed"],
            ["single", "compare"],
            ["k_fold", "group_k_fold", "time_series_split"],
        )
    ]
    results = []
    with tempfile.TemporaryDirectory(prefix="gp-benchmark-cases-") as directory:
        for index, case in enumerate(cases):
            output = Path(directory) / f"case-{index}.json"
            process = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--case",
                    json.dumps(case),
                    "--output",
                    str(output),
                ],
                check=False,
                timeout=240,
                capture_output=True,
                text=True,
            )
            if not output.is_file():
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.with_suffix(".failure.log").write_text(
                    "Synthetic benchmark only\n" + process.stdout + process.stderr,
                    encoding="utf-8",
                )
                raise RuntimeError(
                    f"Synthetic benchmark process failed at case {case}; exit={process.returncode}"
                )
            result = json.loads(output.read_text(encoding="utf-8"))
            results.append(result)
            print(json.dumps({**case, "status": result["status"]}), flush=True)
    evidence = {
        "schema_version": 1,
        "synthetic_fixture": True,
        "system": platform.platform(),
        "python": platform.python_version(),
        "machine": platform.machine(),
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_tree_dirty": bool(
            subprocess.check_output(
                ["git", "status", "--porcelain", "--untracked-files=normal"],
                cwd=ROOT,
                text=True,
            ).strip()
        ),
        "cases": results,
        "memory_scope": "Separate worker and parent lifetime RSS peaks; not simultaneous combined peak",
        "memory_enforcement": "admission_estimate_not_os_limit",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return int(any(result["status"] == "failed" for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
