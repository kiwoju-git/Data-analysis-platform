from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


EXPECTED_PACKAGES = {
    "joblib": "1.5.2",
    "numpy": "2.2.6",
    "scikit-learn": "1.7.2",
    "scipy": "1.15.3",
    "threadpoolctl": "3.6.0",
}
EXPECTED_WHEEL_PREFIXES = {
    "joblib": "joblib-1.5.2-",
    "numpy": "numpy-2.2.6-",
    "scikit-learn": "scikit_learn-1.7.2-",
    "scipy": "scipy-1.15.3-",
    "threadpoolctl": "threadpoolctl-3.6.0-",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate scikit-learn dependency spike JSON."
    )
    parser.add_argument("result_path", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.result_path.read_text(encoding="utf-8-sig"))
    summary = validate_payload(_object(payload, "payload"))
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
    return 0


def validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    _equal(payload.get("schema_version"), 2, "schema_version")
    _equal(payload.get("status"), "passed", "status")

    environment = _object(payload.get("environment"), "environment")
    python_version = _string(
        environment.get("python_version"), "environment.python_version"
    )
    if not python_version.startswith("3.10."):
        raise ValueError("environment.python_version must be 3.10.x")
    platform_name = _string(environment.get("platform"), "environment.platform")
    if "Windows" not in platform_name:
        raise ValueError("environment.platform must describe Windows")
    os_caption = _string(environment.get("os_caption"), "environment.os_caption")
    if "Windows" not in os_caption:
        raise ValueError("environment.os_caption must describe Windows")
    os_build_number = _positive_integer(
        environment.get("os_build_number"), "environment.os_build_number"
    )
    os_product_type = _positive_integer(
        environment.get("os_product_type"), "environment.os_product_type"
    )
    if os_product_type not in (1, 2, 3):
        raise ValueError("environment.os_product_type must be 1, 2, or 3")
    _equal(
        platform_name,
        f"{os_caption} build {os_build_number}",
        "environment platform identity",
    )
    _equal(environment.get("architecture"), "64bit", "environment.architecture")
    _equal(environment.get("cpu_only"), True, "environment.cpu_only")
    _equal(environment.get("thread_limit"), 1, "environment.thread_limit")
    windows_11_verified = _boolean(
        environment.get("windows_11_verified"), "environment.windows_11_verified"
    )
    _equal(
        windows_11_verified,
        os_product_type == 1 and os_build_number >= 22000,
        "windows 11 environment gate",
    )

    candidates = _object(payload.get("candidates"), "candidates")
    for name, version in EXPECTED_PACKAGES.items():
        _equal(candidates.get(name), version, f"candidates.{name}")

    metadata = _object(payload.get("candidate_metadata"), "candidate_metadata")
    _equal(
        metadata.get("requires_python"), ">=3.10", "candidate_metadata.requires_python"
    )
    _equal(metadata.get("license_expression"), "BSD-3-Clause", "license_expression")
    wheel_name = _string(metadata.get("windows_cp310_wheel"), "windows_cp310_wheel")
    if not wheel_name.endswith("-cp310-cp310-win_amd64.whl"):
        raise ValueError("candidate wheel must be a CPython 3.10 Windows AMD64 wheel")
    candidate_wheel_size = _positive_integer(
        metadata.get("windows_cp310_wheel_size_bytes"),
        "windows_cp310_wheel_size_bytes",
    )
    candidate_wheel_sha = _sha256(
        metadata.get("windows_cp310_wheel_sha256"), "windows_cp310_wheel_sha256"
    )

    installation = _object(payload.get("installation"), "installation")
    _equal(installation.get("wheel_only"), True, "installation.wheel_only")
    _equal(installation.get("offline_install"), True, "installation.offline_install")
    _equal(installation.get("pip_check_passed"), True, "installation.pip_check_passed")
    wheels = _array(installation.get("wheels"), "installation.wheels")
    if len(wheels) != len(EXPECTED_PACKAGES):
        raise ValueError("installation.wheels must contain exactly five pinned wheels")
    wheel_manifest: dict[str, dict[str, Any]] = {}
    for index, wheel in enumerate(wheels):
        record = _object(wheel, f"installation.wheels[{index}]")
        filename = _string(record.get("filename"), f"wheels[{index}].filename")
        if not filename.endswith(".whl"):
            raise ValueError("source archives are not allowed in the wheel manifest")
        _positive_integer(record.get("size_bytes"), f"wheels[{index}].size_bytes")
        _sha256(record.get("sha256"), f"wheels[{index}].sha256")
        if filename in wheel_manifest:
            raise ValueError("installation.wheels must not contain duplicate filenames")
        wheel_manifest[filename] = record
    for package_name, prefix in EXPECTED_WHEEL_PREFIXES.items():
        matches = [
            filename for filename in wheel_manifest if filename.startswith(prefix)
        ]
        if len(matches) != 1:
            raise ValueError(
                f"wheel manifest must contain exactly one {package_name} wheel"
            )
    candidate_manifest = wheel_manifest.get(wheel_name)
    if candidate_manifest is None:
        raise ValueError("candidate wheel must exist in the downloaded wheel manifest")
    _equal(
        candidate_manifest.get("size_bytes"),
        candidate_wheel_size,
        "candidate wheel manifest size",
    )
    _equal(
        candidate_manifest.get("sha256"),
        candidate_wheel_sha,
        "candidate wheel manifest SHA-256",
    )

    offline = _object(payload.get("offline_runtime"), "offline_runtime")
    _equal(offline.get("no_index"), True, "offline_runtime.no_index")
    _equal(offline.get("invalid_proxy"), True, "offline_runtime.invalid_proxy")
    _equal(offline.get("run_count"), 2, "offline_runtime.run_count")
    _equal(offline.get("deterministic"), True, "offline_runtime.deterministic")
    fingerprints = _array(offline.get("fingerprints"), "offline_runtime.fingerprints")
    if len(fingerprints) != 2 or fingerprints[0] != fingerprints[1]:
        raise ValueError("offline GP fingerprints must match across two processes")
    _sha256(fingerprints[0], "offline_runtime.fingerprints[0]")

    smoke = _object(payload.get("smoke"), "smoke")
    _equal(smoke.get("status"), "passed", "smoke.status")
    _equal(smoke.get("deterministic_fingerprint"), fingerprints[0], "smoke fingerprint")
    package_records = _array(smoke.get("packages"), "smoke.packages")
    if len(package_records) != len(EXPECTED_PACKAGES):
        raise ValueError("smoke.packages must contain exactly five package records")
    resolved = {
        _string(_object(item, "package").get("name"), "package.name"): _string(
            _object(item, "package").get("version"), "package.version"
        )
        for item in package_records
    }
    _equal(resolved, EXPECTED_PACKAGES, "resolved package versions")
    for package in package_records:
        record = _object(package, "package")
        _string(record.get("license"), "package.license")
        _positive_number(
            record.get("installed_size_bytes"), "package.installed_size_bytes"
        )

    benchmarks = _object(payload.get("benchmarks"), "benchmarks")
    _equal(benchmarks.get("runs"), 5, "benchmarks.runs")
    for key in ("baseline", "scientific_import", "gp_smoke"):
        _validate_metric(_object(benchmarks.get(key), f"benchmarks.{key}"), key)
    _number(benchmarks.get("median_import_elapsed_delta_ms"), "import elapsed delta")
    _number(benchmarks.get("median_import_peak_working_set_delta_mib"), "memory delta")

    decision = _object(payload.get("decision"), "decision")
    candidate_approved = _boolean(
        decision.get("candidate_approved_for_future_pin"), "candidate approval"
    )
    _equal(candidate_approved, windows_11_verified, "candidate approval OS gate")
    _equal(
        decision.get("production_dependency_changed"), False, "production dependency"
    )
    _equal(decision.get("gp_api_added"), False, "GP API")

    return {
        "status": "passed",
        "python_version": python_version,
        "scikit_learn": EXPECTED_PACKAGES["scikit-learn"],
        "deterministic_fingerprint": fingerprints[0],
        "candidate_approved_for_future_pin": candidate_approved,
    }


def _validate_metric(metric: dict[str, Any], name: str) -> None:
    _positive_number(metric.get("min_elapsed_ms"), f"{name}.min_elapsed_ms")
    _positive_number(metric.get("median_elapsed_ms"), f"{name}.median_elapsed_ms")
    _positive_number(metric.get("max_elapsed_ms"), f"{name}.max_elapsed_ms")
    _positive_number(metric.get("median_peak_working_set_mib"), f"{name}.memory")


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _array(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be an array")
    return value


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _boolean(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")
    return value


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _positive_number(value: Any, name: str) -> float:
    result = _number(value, name)
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def _positive_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _sha256(value: Any, name: str) -> str:
    result = _string(value, name)
    if len(result) != 64 or any(
        character not in "0123456789abcdef" for character in result
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return result


def _equal(value: Any, expected: Any, name: str) -> None:
    if value != expected:
        raise ValueError(f"{name} must be {expected!r}, got {value!r}")


if __name__ == "__main__":
    raise SystemExit(main())
