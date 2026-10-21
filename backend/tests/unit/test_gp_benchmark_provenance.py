from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "benchmark_gp_resources.py"
SPEC = importlib.util.spec_from_file_location("tested_gp_benchmark", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-c", "user.name=Synthetic Test", "-c", "user.email=test@example.invalid", *args],
        cwd=root,
        text=True,
    ).strip()


@pytest.fixture
def source(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "source.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(tmp_path, "add", "source.py")
    git(tmp_path, "commit", "-q", "-m", "synthetic baseline")
    return tmp_path


def test_clean_unchanged_run_is_attributed_to_starting_commit(source):
    before = benchmark.capture_source_identity(source)
    after = benchmark.capture_source_identity(source)
    provenance = benchmark.source_provenance(before, after)
    assert provenance["status"] == "verified_clean_unchanged"
    assert provenance["valid_for_release"] is True
    assert provenance["source_commit"] == before["head_commit"]


def test_changed_bytes_at_same_head_invalidate_benchmark(source):
    before = benchmark.capture_source_identity(source)
    (source / "source.py").write_text("VALUE = 2\n", encoding="utf-8")
    after = benchmark.capture_source_identity(source)
    assert before["head_commit"] == after["head_commit"]
    assert before["tracked_tree_sha256"] != after["tracked_tree_sha256"]
    provenance = benchmark.source_provenance(before, after)
    assert provenance["status"] == "invalid_source_changed"
    assert provenance["valid_for_release"] is False
    assert provenance["source_commit"] is None


def test_commit_during_measurement_is_not_misattributed_to_final_head(source):
    before = benchmark.capture_source_identity(source)
    (source / "source.py").write_text("VALUE = 3\n", encoding="utf-8")
    git(source, "add", "source.py")
    git(source, "commit", "-q", "-m", "changed during run")
    after = benchmark.capture_source_identity(source)
    provenance = benchmark.source_provenance(before, after)
    assert not after["dirty"]
    assert before["head_commit"] != after["head_commit"]
    assert provenance["source_commit"] is None
    assert provenance["status"] == "invalid_source_changed"


def test_stable_dirty_source_is_diagnostic_only(source):
    (source / "source.py").write_text("VALUE = 4\n", encoding="utf-8")
    before = benchmark.capture_source_identity(source)
    provenance = benchmark.source_provenance(before, benchmark.capture_source_identity(source))
    assert provenance["status"] == "diagnostic_dirty_source"
    assert provenance["valid_for_release"] is False
    assert provenance["source_commit"] is None


def test_untracked_source_prevents_clean_release_attribution(source):
    (source / "new_module.py").write_text("VALUE = 5\n", encoding="utf-8")
    before = benchmark.capture_source_identity(source)
    assert before["dirty"]
    assert not benchmark.source_provenance(before, before)["valid_for_release"]


def test_default_cli_rejects_dirty_source_before_running_models(source, monkeypatch, tmp_path):
    (source / "source.py").write_text("VALUE = 6\n", encoding="utf-8")
    monkeypatch.setattr(benchmark, "ROOT", source)
    monkeypatch.setattr(
        benchmark.sys, "argv", [str(SCRIPT), "--output", str(tmp_path / "evidence.json")]
    )
    monkeypatch.setattr(benchmark, "run_case", lambda case: pytest.fail("No fit is allowed."))
    with pytest.raises(SystemExit) as error:
        benchmark.main()
    assert error.value.code == 2


def test_case_changed_during_measurement_keeps_results_but_returns_invalid(source, monkeypatch):
    output = source / "evidence.json"
    case = {"rows": 501, "predictors": "numeric", "mode": "single", "validation": "k_fold"}
    monkeypatch.setattr(benchmark, "ROOT", source)
    monkeypatch.setattr(
        benchmark.sys,
        "argv",
        [str(SCRIPT), "--output", str(output), "--case", json.dumps(case)],
    )

    def measured(_case, **_kwargs):
        (source / "source.py").write_text("VALUE = 7\n", encoding="utf-8")
        return {"status": "passed", "execution_seconds": 1.25}

    monkeypatch.setattr(benchmark, "run_case", measured)
    assert benchmark.main() == 1
    evidence = json.loads(output.read_text(encoding="utf-8"))
    assert evidence["status"] == "passed"
    assert evidence["execution_seconds"] == 1.25
    assert evidence["source_provenance"]["status"] == "invalid_source_changed"
    assert evidence["source_provenance"]["source_commit"] is None


def test_explicit_dirty_case_is_nonrelease_evidence_even_when_measurement_passes(
    source, monkeypatch
):
    (source / "source.py").write_text("VALUE = 8\n", encoding="utf-8")
    output = source / "evidence.json"
    case = {"rows": 501, "predictors": "numeric", "mode": "single", "validation": "k_fold"}
    monkeypatch.setattr(benchmark, "ROOT", source)
    monkeypatch.setattr(
        benchmark.sys,
        "argv",
        [str(SCRIPT), "--output", str(output), "--allow-dirty-source", "--case", json.dumps(case)],
    )
    monkeypatch.setattr(benchmark, "run_case", lambda _case, **_kwargs: {"status": "passed"})
    assert benchmark.main() == 1
    evidence = json.loads(output.read_text(encoding="utf-8"))
    assert evidence["source_provenance"]["status"] == "diagnostic_dirty_source"
    assert evidence["source_provenance"]["source_commit"] is None


def test_matrix_keeps_invalid_partial_evidence_when_changed_source_blocks_a_child(
    source, monkeypatch
):
    output = source / "evidence.json"
    monkeypatch.setattr(benchmark, "ROOT", source)
    monkeypatch.setattr(
        benchmark.sys, "argv", [str(SCRIPT), "--output", str(output), "--rows", "501"]
    )

    def child(command):
        (source / "source.py").write_text("VALUE = 9\n", encoding="utf-8")
        return subprocess.CompletedProcess(
            command, 2, stdout="", stderr="Dirty source rejected."
        ), False

    monkeypatch.setattr(benchmark, "_run_case_process", child)
    assert benchmark.main() == 1
    evidence = json.loads(output.read_text(encoding="utf-8"))
    assert evidence["source_commit"] is None
    assert evidence["source_provenance"]["status"] == "invalid_source_changed"
    assert evidence["completed_case_count"] == 1
    assert evidence["not_run_case_count"] == 11
    assert evidence["cases"][0]["status"] == "failed"
    assert evidence["cases"][0]["error_code"] == "benchmark_case_process_failed"


@pytest.mark.parametrize("system", ["Windows", "Linux"])
def test_outer_timeout_terminates_only_the_case_process_group(monkeypatch, system):
    calls = []
    command = ["python", "synthetic_case.py"]

    class Process:
        pid = 4321
        returncode = -9
        attempts = 0

        def communicate(self, timeout):
            self.attempts += 1
            if self.attempts == 1:
                assert timeout == 240
                raise subprocess.TimeoutExpired(command, timeout)
            assert timeout == 15
            return "synthetic stdout", "synthetic stack"

    def popen(actual, **kwargs):
        assert actual == command
        assert kwargs["start_new_session"] is (system != "Windows")
        return Process()

    monkeypatch.setattr(benchmark.platform, "system", lambda: system)
    monkeypatch.setattr(benchmark.subprocess, "CREATE_NEW_PROCESS_GROUP", 512, raising=False)
    monkeypatch.setattr(benchmark.signal, "SIGKILL", 9, raising=False)
    monkeypatch.setattr(benchmark.subprocess, "Popen", popen)
    monkeypatch.setattr(
        benchmark.subprocess, "run", lambda command, **kwargs: calls.append(command)
    )
    monkeypatch.setattr(
        benchmark.os, "killpg", lambda pid, signum: calls.append([pid, signum]), raising=False
    )
    result, timed_out = benchmark._run_case_process(command)
    assert timed_out is True
    assert result.stderr == "synthetic stack"
    if system == "Windows":
        assert calls == [["taskkill", "/PID", "4321", "/T", "/F"]]
    else:
        assert calls == [[4321, benchmark.signal.SIGKILL]]


def test_matrix_timeout_preserves_partial_results_stage_and_failed_exit(source, monkeypatch):
    output = source / "evidence.json"
    monkeypatch.setattr(benchmark, "ROOT", source)
    monkeypatch.setattr(
        benchmark.sys, "argv", [str(SCRIPT), "--output", str(output), "--rows", "501"]
    )

    def timeout(command):
        case_output = Path(command[command.index("--output") + 1])
        case_output.with_suffix(".progress.json").write_text(
            json.dumps({"stage": "analyzing", "elapsed_seconds": 12.0}), encoding="utf-8"
        )
        return subprocess.CompletedProcess(command, -9, "", "synthetic traceback"), True

    monkeypatch.setattr(benchmark, "_run_case_process", timeout)
    assert benchmark.main() == 1
    evidence = json.loads(output.read_text(encoding="utf-8"))
    assert evidence["cases"][0]["error_code"] == "benchmark_case_timeout"
    assert evidence["cases"][0]["last_progress"]["stage"] == "analyzing"
    assert evidence["not_run_case_count"] == 11
    assert "synthetic traceback" in output.with_suffix(".failure.log").read_text(encoding="utf-8")
