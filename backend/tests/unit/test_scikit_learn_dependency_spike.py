from pathlib import Path

import pytest
from scripts.validate_scikit_learn_spike import EXPECTED_PACKAGES, validate_payload

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_scikit_learn_spike_validator_accepts_complete_isolated_record() -> None:
    payload = _valid_payload()

    summary = validate_payload(payload)

    assert summary == {
        "status": "passed",
        "python_version": "3.10.11",
        "scikit_learn": "1.7.2",
        "deterministic_fingerprint": "a" * 64,
        "candidate_approved_for_future_pin": False,
    }


def test_scikit_learn_spike_validator_rejects_nondeterministic_gp() -> None:
    payload = _valid_payload()
    payload["offline_runtime"]["fingerprints"][1] = "b" * 64

    with pytest.raises(ValueError, match="fingerprints must match"):
        validate_payload(payload)


def test_scikit_learn_spike_validator_rejects_source_archive() -> None:
    payload = _valid_payload()
    payload["installation"]["wheels"][0]["filename"] = "joblib-1.5.2.tar.gz"

    with pytest.raises(ValueError, match="source archives"):
        validate_payload(payload)


def test_scikit_learn_spike_validator_rejects_approval_without_windows_11() -> None:
    payload = _valid_payload()
    payload["decision"]["candidate_approved_for_future_pin"] = True

    with pytest.raises(ValueError, match="candidate approval OS gate"):
        validate_payload(payload)


def test_scikit_learn_spike_validator_excludes_windows_server_2025() -> None:
    payload = _valid_payload()
    payload["environment"].update(
        {
            "platform": "Microsoft Windows Server 2025 build 26100",
            "os_caption": "Microsoft Windows Server 2025",
            "os_build_number": 26100,
            "os_product_type": 3,
            "windows_11_verified": False,
        }
    )

    summary = validate_payload(payload)
    assert summary["candidate_approved_for_future_pin"] is False

    payload["environment"]["windows_11_verified"] = True
    payload["decision"]["candidate_approved_for_future_pin"] = True
    with pytest.raises(ValueError, match="windows 11 environment gate"):
        validate_payload(payload)


def test_scikit_learn_spike_validator_accepts_windows_11_workstation() -> None:
    payload = _valid_payload()
    payload["environment"].update(
        {
            "platform": "Microsoft Windows 11 Pro build 22631",
            "os_caption": "Microsoft Windows 11 Pro",
            "os_build_number": 22631,
            "os_product_type": 1,
            "windows_11_verified": True,
        }
    )
    payload["decision"]["candidate_approved_for_future_pin"] = True

    summary = validate_payload(payload)

    assert summary["candidate_approved_for_future_pin"] is True


def test_scikit_learn_spike_validator_rejects_candidate_wheel_tamper() -> None:
    payload = _valid_payload()
    payload["candidate_metadata"]["windows_cp310_wheel_sha256"] = "d" * 64

    with pytest.raises(ValueError, match="candidate wheel manifest SHA-256"):
        validate_payload(payload)


def test_dependency_promotion_uses_the_reviewed_scikit_learn_candidate() -> None:
    pyproject = (REPO_ROOT / "backend" / "pyproject.toml").read_text(encoding="utf-8")

    assert pyproject.count('"scikit-learn==1.7.2"') == 1
    assert '"scikit-learn>=' not in pyproject


def test_spike_runner_uses_temp_wheel_only_offline_environment() -> None:
    runner = (REPO_ROOT / "scripts" / "run-scikit-learn-spike.ps1").read_text(encoding="utf-8")

    assert 'Join-Path $env:TEMP "datalab-scikit-learn-spike' in runner
    assert "--only-binary=:all:" in runner
    assert "--no-index" in runner
    assert "Spike output must stay outside the repository" in runner


def _valid_payload() -> dict:
    package_records = [
        {
            "name": name,
            "version": version,
            "license": "BSD-3-Clause",
            "installed_size_bytes": 1024,
        }
        for name, version in EXPECTED_PACKAGES.items()
    ]
    wheel_names = {
        "joblib": "joblib-1.5.2-py3-none-any.whl",
        "numpy": "numpy-2.2.6-cp310-cp310-win_amd64.whl",
        "scikit-learn": "scikit_learn-1.7.2-cp310-cp310-win_amd64.whl",
        "scipy": "scipy-1.15.3-cp310-cp310-win_amd64.whl",
        "threadpoolctl": "threadpoolctl-3.6.0-py3-none-any.whl",
    }
    wheels = [
        {"filename": wheel_names[name], "size_bytes": 1024, "sha256": "c" * 64}
        for name in EXPECTED_PACKAGES
    ]
    return {
        "schema_version": 2,
        "status": "passed",
        "environment": {
            "platform": "Microsoft Windows 10 Home build 19045",
            "os_caption": "Microsoft Windows 10 Home",
            "os_build_number": 19045,
            "os_product_type": 1,
            "python_version": "3.10.11",
            "architecture": "64bit",
            "cpu_only": True,
            "thread_limit": 1,
            "windows_11_verified": False,
        },
        "candidates": dict(EXPECTED_PACKAGES),
        "candidate_metadata": {
            "requires_python": ">=3.10",
            "license_expression": "BSD-3-Clause",
            "windows_cp310_wheel": "scikit_learn-1.7.2-cp310-cp310-win_amd64.whl",
            "windows_cp310_wheel_size_bytes": 1024,
            "windows_cp310_wheel_sha256": "c" * 64,
        },
        "installation": {
            "wheel_only": True,
            "offline_install": True,
            "pip_check_passed": True,
            "wheels": wheels,
        },
        "offline_runtime": {
            "no_index": True,
            "invalid_proxy": True,
            "run_count": 2,
            "deterministic": True,
            "fingerprints": ["a" * 64, "a" * 64],
        },
        "smoke": {
            "status": "passed",
            "deterministic_fingerprint": "a" * 64,
            "packages": package_records,
        },
        "benchmarks": {
            "runs": 5,
            "baseline": _metric(),
            "scientific_import": _metric(),
            "gp_smoke": _metric(),
            "median_import_elapsed_delta_ms": 10.0,
            "median_import_peak_working_set_delta_mib": 20.0,
        },
        "decision": {
            "candidate_approved_for_future_pin": False,
            "production_dependency_changed": False,
            "gp_api_added": False,
        },
    }


def _metric() -> dict[str, float]:
    return {
        "min_elapsed_ms": 1.0,
        "median_elapsed_ms": 2.0,
        "max_elapsed_ms": 3.0,
        "median_peak_working_set_mib": 4.0,
    }
