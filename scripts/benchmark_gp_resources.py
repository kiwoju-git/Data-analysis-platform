"""Synthetic native-target Exact GP admission, execution and restoration benchmark."""

from __future__ import annotations

import argparse
import faulthandler
import hashlib
import itertools
import json
import os
import platform
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def capture_source_identity(root: Path | None = None) -> dict[str, Any]:
    source = ROOT if root is None else root
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=source, text=True
    ).strip()
    status = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=normal"],
        cwd=source,
    )
    names = subprocess.check_output(["git", "ls-files", "--cached", "-z"], cwd=source)
    tracked = sorted(set(name for name in names.split(b"\0") if name))
    aggregate = hashlib.sha256()
    for name in tracked:
        path = source / name.decode("utf-8")
        digest = hashlib.sha256()
        if path.is_symlink():
            digest.update(b"symlink\0" + os.fsencode(os.readlink(path)))
        elif path.is_file():
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
        else:
            digest.update(b"missing_or_nonregular")
        aggregate.update(name + b"\0" + digest.hexdigest().encode("ascii") + b"\n")
    return {
        "head_commit": head,
        "tracked_tree_sha256": aggregate.hexdigest(),
        "tracked_file_count": len(tracked),
        "status_sha256": hashlib.sha256(status).hexdigest(),
        "dirty": bool(status),
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def _same_source(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return all(
        left.get(key) == right.get(key)
        for key in ("head_commit", "tracked_tree_sha256", "status_sha256", "dirty")
    )


def source_provenance(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    unchanged = _same_source(before, after)
    clean = not before["dirty"] and not after["dirty"]
    valid = unchanged and clean
    return {
        "status": "verified_clean_unchanged"
        if valid
        else "diagnostic_dirty_source"
        if unchanged
        else "invalid_source_changed",
        "valid_for_release": valid,
        "source_commit": before["head_commit"] if valid else None,
        "start": before,
        "end": after,
    }


def _record_case_stage(path: Path | None, stage: str, started: float) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"stage": stage, "elapsed_seconds": time.perf_counter() - started})
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _run_case_process(
    command: list[str],
) -> tuple[subprocess.CompletedProcess[str], bool]:
    windows = platform.system() == "Windows"
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if windows else 0,
        start_new_session=not windows,
    )
    try:
        stdout, stderr = process.communicate(timeout=240)
        return subprocess.CompletedProcess(
            command, process.returncode, stdout, stderr
        ), False
    except subprocess.TimeoutExpired:
        # The process group contains only this synthetic case and workers it started.
        if windows:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                capture_output=True,
                timeout=15,
            )
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        stdout, stderr = process.communicate(timeout=15)
        return subprocess.CompletedProcess(
            command, process.returncode, stdout, stderr
        ), True


def run_case(
    case: dict[str, Any], *, progress_path: Path | None = None
) -> dict[str, Any]:
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
    _record_case_stage(progress_path, "starting_app", started)
    with tempfile.TemporaryDirectory(prefix="gp-benchmark-") as directory:
        workspace = Path(directory) / "synthetic workspace"
        with TestClient(create_app(Settings(workspace_root=workspace))) as client:
            _record_case_stage(progress_path, "uploading", started)
            upload = client.post(
                "/api/v1/datasets", files={"file": ("synthetic.csv", csv_bytes)}
            )
            upload.raise_for_status()
            _record_case_stage(progress_path, "confirming_parsing", started)
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
                _record_case_stage(progress_path, "saving_schema", started)
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
            _record_case_stage(progress_path, "analyzing", started)
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
                _record_case_stage(
                    progress_path, "stopping_after_analysis_failure", started
                )
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
            _record_case_stage(progress_path, "restoring_result", started)
            restored = client.get(
                f"/api/v1/analysis-runs/{envelope['analysis_id']}/result"
            )
            assert restored.status_code == 200
            assert restored.json()["result"] == result
            pointer = result["model_manifest"]
            _record_case_stage(progress_path, "predicting_from_restored_model", started)
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
            _record_case_stage(progress_path, "stopping_app", started)
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
    parser.add_argument(
        "--allow-dirty-source",
        action="store_true",
        help="Run diagnostic-only measurements; never valid as release evidence.",
    )
    parser.add_argument("--case", help=argparse.SUPPRESS)
    args = parser.parse_args()
    source_before = capture_source_identity()
    if source_before["dirty"] and not args.allow_dirty_source:
        parser.error(
            "A clean source tree is required; --allow-dirty-source is diagnostic only."
        )
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
        faulthandler.dump_traceback_later(210)
        try:
            result = run_case(
                case, progress_path=args.output.with_suffix(".progress.json")
            )
        finally:
            faulthandler.cancel_dump_traceback_later()
        provenance = source_provenance(source_before, capture_source_identity())
        result["source_provenance"] = provenance
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        return int(result["status"] == "failed" or not provenance["valid_for_release"])
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
            process, timed_out = _run_case_process(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--case",
                    json.dumps(case),
                    "--output",
                    str(output),
                    *(["--allow-dirty-source"] if args.allow_dirty_source else []),
                ]
            )
            if timed_out or not output.is_file():
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.with_suffix(".failure.log").write_text(
                    "Synthetic benchmark only\n" + process.stdout + process.stderr,
                    encoding="utf-8",
                )
                progress_path = output.with_suffix(".progress.json")
                progress = (
                    json.loads(progress_path.read_text(encoding="utf-8"))
                    if progress_path.is_file()
                    else None
                )
                results.append(
                    {
                        **case,
                        "status": "failed",
                        "error_code": "benchmark_case_timeout"
                        if timed_out
                        else "benchmark_case_process_failed",
                        "process_exit_code": process.returncode,
                        "last_progress": progress,
                        "source_provenance": source_provenance(
                            source_before, capture_source_identity()
                        ),
                    }
                )
                break
            result = json.loads(output.read_text(encoding="utf-8"))
            results.append(result)
            print(json.dumps({**case, "status": result["status"]}), flush=True)
    source_after = capture_source_identity()
    provenance = source_provenance(source_before, source_after)
    different_cases = [
        index
        for index, result in enumerate(results)
        if not _same_source(
            source_before, result.get("source_provenance", {}).get("start", {})
        )
        or not _same_source(
            source_before, result.get("source_provenance", {}).get("end", {})
        )
    ]
    if different_cases:
        provenance.update(
            status="invalid_source_changed",
            valid_for_release=False,
            source_commit=None,
            different_source_case_indices=different_cases,
        )
    evidence = {
        "schema_version": 2,
        "synthetic_fixture": True,
        "system": platform.platform(),
        "python": platform.python_version(),
        "machine": platform.machine(),
        "source_commit": provenance["source_commit"],
        "source_tree_dirty": source_before["dirty"] or source_after["dirty"],
        "source_provenance": provenance,
        "requested_case_count": len(cases),
        "completed_case_count": len(results),
        "not_run_case_count": len(cases) - len(results),
        "cases": results,
        "memory_scope": "Separate worker and parent lifetime RSS peaks; not simultaneous combined peak",
        "memory_enforcement": "admission_estimate_not_os_limit",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return int(
        any(result["status"] == "failed" for result in results)
        or not provenance["valid_for_release"]
    )


if __name__ == "__main__":
    raise SystemExit(main())
