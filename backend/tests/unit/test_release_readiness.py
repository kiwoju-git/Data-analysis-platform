"""CI admission is independent of a successful intermediate archive job."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/release_readiness.py"
SPEC = importlib.util.spec_from_file_location("release_readiness", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
readiness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(readiness)
SHA = "a" * 40


def successful_jobs(kind: str = "release") -> dict:
    return {name: {"result": "success"} for name in readiness.REQUIRED_JOBS[kind]}


def test_all_jobs_required_and_bound_to_source() -> None:
    report = readiness.require_successful_jobs(successful_jobs(), "release", SHA)
    assert report["source_commit"] == SHA
    assert report["status"] == "passed"
    assert report["publication_performed"] is False
    assert set(report["jobs"]) == {
        "windows",
        "e2e",
        "linux",
        "python311",
        "linux-release",
        "dependency-security",
        "gp-resources",
    }


@pytest.mark.parametrize("job", readiness.REQUIRED_JOBS["release"])
@pytest.mark.parametrize("result", ["failure", "cancelled", "skipped", "in_progress", None])
def test_no_non_success_job_can_pass(job: str, result: str | None) -> None:
    jobs = successful_jobs()
    jobs[job]["result"] = result
    with pytest.raises(ValueError, match="did not succeed"):
        readiness.require_successful_jobs(jobs, "release", SHA)


@pytest.mark.parametrize("change", ["missing", "extra", "wrong_shape"])
def test_incomplete_or_drifted_gate_is_rejected(change: str) -> None:
    jobs = successful_jobs()
    if change == "missing":
        del jobs["windows"]
    elif change == "extra":
        jobs["unreviewed_gate"] = {"result": "success"}
    else:
        jobs = []
    with pytest.raises(ValueError, match="exactly match"):
        readiness.require_successful_jobs(jobs, "release", SHA)


def test_security_gate_requires_both_runtime_and_dev_matrix_groups() -> None:
    jobs = successful_jobs("dependencies")
    assert readiness.require_successful_jobs(jobs, "dependencies", SHA)["status"] == "passed"
    jobs["security-python"]["result"] = "skipped"
    with pytest.raises(ValueError):
        readiness.require_successful_jobs(jobs, "dependencies", SHA)


@pytest.mark.parametrize("result", ["failure", "cancelled", "skipped", "in_progress", None])
def test_windows_e2e_matrix_aggregate_requires_every_suite_success(result) -> None:
    jobs = successful_jobs("windows-e2e")
    assert readiness.require_successful_jobs(jobs, "windows-e2e", SHA)["status"] == "passed"
    jobs["windows-e2e"]["result"] = result
    with pytest.raises(ValueError, match="did not succeed"):
        readiness.require_successful_jobs(jobs, "windows-e2e", SHA)


def test_version_uses_metadata_or_explicit_validated_override(tmp_path: Path) -> None:
    metadata = tmp_path / "release.json"
    metadata.write_text(
        json.dumps(
            {"schema_version": 1, "linux_release_version": "2026.10.3", "channel": "prerelease"}
        ),
        encoding="utf-8",
    )
    assert readiness.resolve_release_version(metadata) == "2026.10.3"
    assert readiness.resolve_release_version(metadata, "2026.10.4") == "2026.10.4"


@pytest.mark.parametrize(
    "version",
    [
        "../2026.10.3",
        "2026.10.3\nINJECT=1",
        "$(command)",
        "2026.10",
        " 2026.10.3",
        "2026.10.3 ",
        "2026.10.3-beta",
        "999999999.1.1",
        "2026.01.3",
    ],
)
def test_untrusted_version_cannot_enter_shell_or_file_path(version: str) -> None:
    with pytest.raises(ValueError, match="numeric"):
        readiness.resolve_release_version(ROOT / "release-version.json", version)


def test_optimized_python_still_fails_and_removes_old_success(tmp_path: Path) -> None:
    output = tmp_path / "검증 결과.json"
    output.write_text('{"status":"passed"}', encoding="utf-8")
    jobs = successful_jobs()
    jobs["linux-release"]["result"] = "cancelled"
    process = subprocess.run(
        [
            sys.executable,
            "-O",
            str(SCRIPT),
            "gate",
            "--kind",
            "release",
            "--source-commit",
            SHA,
            "--output",
            str(output),
        ],
        env=dict(os.environ, GATE_RESULTS=json.dumps(jobs)),
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert process.returncode == 1
    assert "linux-release" in process.stderr
    assert not output.exists()


def test_version_cli_appends_only_validated_github_env(tmp_path: Path) -> None:
    target = tmp_path / "github env"
    process = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "version",
            "--override",
            "2026.10.4",
            "--github-env",
            str(target),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert process.returncode == 0, process.stderr
    assert target.read_text(encoding="utf-8") == "RELEASE_VERSION=2026.10.4\n"


def test_workflow_admits_only_the_complete_gate_and_parameterizes_archive() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    aggregate = workflow.split("  release-ready:", 1)[1]
    assert "if: always()" in aggregate
    assert (
        "needs: [windows, e2e, linux, python311, linux-release, dependency-security, gp-resources]"
        in aggregate
    )
    assert "release_readiness.py gate --kind release" in aggregate
    assert "GATE_RESULTS: ${{ toJSON(needs) }}" in aggregate
    archive = workflow.split("  linux-release:", 1)[1].split("  release-ready:", 1)[0]
    assert '--release-version "$RELEASE_VERSION"' in archive
    assert "statistical-twin-linux-$RELEASE_VERSION-ubuntu24.04-x86_64-py312.tar.gz" in archive
    assert "2026.10.2" not in archive
    assert "${{ inputs.release_version }}" not in archive.split("run:", 1)[1]


def test_gp_resource_evidence_runs_both_native_targets_without_replacing_checks() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    job = workflow.split("  gp-resources:", 1)[1].split("  linux-release:", 1)[0]
    assert "os: windows-latest" in job and 'python: "3.10"' in job
    assert "os: ubuntu-24.04" in job and 'python: "3.12"' in job
    assert "benchmark_gp_resources.py --rows 501 1000 2000" in job
    assert "gp-resources-${{ matrix.target }}-${{ github.sha }}" in job
    assert "if: always()" in job
