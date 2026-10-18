"""Archive/proof helper tests, not native Linux installation or browser evidence."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "linux_release_verification_tests", ROOT / "scripts/verify_linux_release.py"
)
assert SPEC is not None and SPEC.loader is not None
VERIFY = importlib.util.module_from_spec(SPEC)
with pytest.MonkeyPatch.context() as imports:
    imports.syspath_prepend(str(ROOT / "scripts"))
    SPEC.loader.exec_module(VERIFY)

SHA = "a" * 40
HASH = "b" * 64
METHODS = (
    "eda.principal_components",
    "regression.partial_least_squares",
    "regression.gaussian_process",
    "quality.two_variances",
)
FAMILIES = ("pls", "gaussian_process")


@pytest.fixture(autouse=True)
def forbid_unmocked_processes(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*args, **kwargs):
        pytest.fail("These unit tests must never launch a real installer or browser process")

    monkeypatch.setattr(VERIFY.subprocess, "Popen", blocked)
    monkeypatch.setattr(VERIFY.subprocess, "run", blocked)


def tar_fixture(tmp_path: Path, entries: list[tuple[str, bytes, bytes]]) -> Path:
    archive = tmp_path / "synthetic.tar.gz"
    with tarfile.open(archive, "w:gz") as target:
        for name, kind, content in entries:
            info = tarfile.TarInfo(name)
            info.type = kind
            info.mode = 0o755 if name.endswith(".sh") else 0o644
            if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                info.linkname = "../../outside"
            info.size = len(content) if kind == tarfile.REGTYPE else 0
            target.addfile(info, io.BytesIO(content) if kind == tarfile.REGTYPE else None)
    return archive


def test_archive_roundtrip_preserves_unicode_bytes_and_new_destination(tmp_path: Path) -> None:
    contents = "synthetic Unicode payload: \uac80\uc99d".encode()
    archive = tar_fixture(
        tmp_path,
        [
            ("statistical-twin-linux", tarfile.DIRTYPE, b""),
            ("statistical-twin-linux/web/assets/\uac80\uc99d data.txt", tarfile.REGTYPE, contents),
            ("statistical-twin-linux/run.sh", tarfile.REGTYPE, b"#!/usr/bin/env bash\n"),
        ],
    )
    before = archive.read_bytes()
    destination = tmp_path / "new folder \uac80\uc99d"
    root = VERIFY.unpack(archive, destination)
    assert root == destination / "statistical-twin-linux"
    assert (root / "web/assets/\uac80\uc99d data.txt").read_bytes() == contents
    assert archive.read_bytes() == before
    if os.name != "nt":
        assert (root / "run.sh").stat().st_mode & 0o111
        assert not (root / "web/assets/\uac80\uc99d data.txt").stat().st_mode & 0o111


@pytest.mark.parametrize(
    "name",
    [
        "../outside",
        "/statistical-twin-linux/absolute",
        "other-root/file",
        "statistical-twin-linux/../outside",
        "statistical-twin-linux/web/../../outside",
        "statistical-twin-linux/./file",
        "statistical-twin-linux/web//file",
        "statistical-twin-linux\\outside",
        "statistical-twin-linux/C:drive",
        "statistical-twin-linux/" + "x" * 4096,
    ],
    ids=[
        "parent",
        "absolute",
        "wrong-root",
        "root-traversal",
        "nested-traversal",
        "dot",
        "empty-segment",
        "backslash",
        "drive",
        "overlong",
    ],
)
def test_unsafe_archive_paths_rejected_before_destination_creation(
    tmp_path: Path, name: str
) -> None:
    archive = tar_fixture(tmp_path, [(name, tarfile.REGTYPE, b"untrusted")])
    destination = tmp_path / "destination"
    with pytest.raises(ValueError, match="Unsafe"):
        VERIFY.unpack(archive, destination)
    assert not destination.exists()
    assert not (tmp_path / "outside").exists()


@pytest.mark.parametrize(
    "kind",
    [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE],
    ids=["symlink", "hardlink", "fifo", "char-device", "block-device"],
)
def test_links_and_special_archive_entries_rejected_without_materialization(
    tmp_path: Path, kind: bytes
) -> None:
    archive = tar_fixture(tmp_path, [("statistical-twin-linux/entry", kind, b"")])
    destination = tmp_path / "destination"
    with pytest.raises(ValueError):
        VERIFY.unpack(archive, destination)
    assert not destination.exists()


def test_duplicate_archive_member_is_not_last_writer_wins(tmp_path: Path) -> None:
    archive = tar_fixture(
        tmp_path,
        [
            ("statistical-twin-linux/file", tarfile.REGTYPE, b"first"),
            ("statistical-twin-linux/file", tarfile.REGTYPE, b"second"),
        ],
    )
    with pytest.raises(ValueError, match="Unsafe"):
        VERIFY.unpack(archive, tmp_path / "destination")


@pytest.mark.parametrize(
    "limit,value,entries",
    [
        (
            "MAX_ARCHIVE_FILES",
            1,
            [
                ("statistical-twin-linux/a", tarfile.REGTYPE, b"a"),
                ("statistical-twin-linux/b", tarfile.REGTYPE, b"b"),
            ],
        ),
        (
            "MAX_ARCHIVE_BYTES",
            3,
            [
                ("statistical-twin-linux/a", tarfile.REGTYPE, b"ab"),
                ("statistical-twin-linux/b", tarfile.REGTYPE, b"cd"),
            ],
        ),
    ],
)
def test_archive_limits_are_checked_before_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, limit: str, value: int, entries: list
) -> None:
    monkeypatch.setattr(VERIFY, limit, value)
    archive = tar_fixture(tmp_path, entries)
    destination = tmp_path / "destination"
    with pytest.raises(ValueError, match="limits"):
        VERIFY.unpack(archive, destination)
    assert not destination.exists()


@pytest.mark.parametrize("existing_file", [False, True])
def test_existing_destination_is_never_merged_or_overwritten(
    tmp_path: Path, existing_file: bool
) -> None:
    archive = tar_fixture(tmp_path, [("statistical-twin-linux/file", tarfile.REGTYPE, b"new")])
    destination = tmp_path / "destination"
    destination.mkdir()
    if existing_file:
        (destination / "keep.txt").write_bytes(b"user-owned")
    with pytest.raises(ValueError, match="new destination"):
        VERIFY.unpack(archive, destination)
    assert destination.is_dir()
    assert not (destination / "statistical-twin-linux").exists()
    if existing_file:
        assert (destination / "keep.txt").read_bytes() == b"user-owned"


@pytest.mark.parametrize(
    "relative",
    [
        ".git/config",
        ".venv/pyvenv.cfg",
        "node_modules/code",
        ".env",
        "workspace/data",
        "web/__pycache__/code.pyc",
        "workspace.sqlite",
        "saved.db",
    ],
)
def test_development_and_user_state_not_accepted_in_release(tmp_path: Path, relative: str) -> None:
    archive = tar_fixture(
        tmp_path, [("statistical-twin-linux/" + relative, tarfile.REGTYPE, b"synthetic")]
    )
    with pytest.raises(ValueError, match="development|database"):
        VERIFY.unpack(archive, tmp_path / "destination")


@pytest.mark.parametrize(
    "action,status", [("verify-payload", "payload_verified"), ("verify-installed", "verified")]
)
def test_bootstrap_identity_uses_isolated_interpreter_and_exact_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, action: str, status: str
) -> None:
    env = {"PYTHON": "/trusted/base/python", "PATH": "/restricted/bin"}
    evidence = {"verification_status": status, "source_commit": SHA, "release_version": "2026.10.3"}
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(stdout=json.dumps(evidence))

    monkeypatch.setattr(VERIFY.subprocess, "run", run)
    assert VERIFY.bootstrap_identity(tmp_path, env, action) == evidence
    argv, kwargs = calls[0]
    assert argv[0] == (
        env["PYTHON"] if action == "verify-payload" else str(tmp_path / ".venv/bin/python")
    )
    assert argv[1:4] == ["-I", "-S", "-B"]
    assert argv[4:] == [
        str(tmp_path / "release_bootstrap.py"),
        action,
        "--release-root",
        str(tmp_path),
    ]
    assert kwargs["check"] is True and kwargs["timeout"] == 120
    assert kwargs["cwd"] == tmp_path and kwargs["env"] is env


@pytest.mark.parametrize(
    "evidence",
    [None, [], {}, {"verification_status": "verified"}, {"verification_status": "failed"}],
)
def test_bootstrap_action_status_mismatch_is_not_identity_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, evidence
) -> None:
    monkeypatch.setattr(
        VERIFY.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout=json.dumps(evidence)),
    )
    with pytest.raises(ValueError, match="incomplete"):
        VERIFY.bootstrap_identity(tmp_path, {"PYTHON": sys.executable}, "verify-payload")


def test_unknown_bootstrap_action_never_executes_subprocess(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        VERIFY.subprocess, "run", lambda *args, **kwargs: pytest.fail("Unknown action must not run")
    )
    with pytest.raises(ValueError, match="Unsupported"):
        VERIFY.bootstrap_identity(tmp_path, {}, "install")


def test_failed_bootstrap_process_cannot_supply_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(2, "synthetic bootstrap")

    monkeypatch.setattr(VERIFY.subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        VERIFY.bootstrap_identity(tmp_path, {"PYTHON": sys.executable}, "verify-payload")


@pytest.mark.parametrize(
    "field,replacement",
    [("source_commit", "c" * 40), ("release_version", "2026.10.4"), ("source_commit", None)],
)
def test_source_and_version_must_match_requested_archive(field: str, replacement) -> None:
    identity = {"source_commit": SHA, "release_version": "2026.10.3", field: replacement}
    with pytest.raises(ValueError, match="differs"):
        VERIFY.require_expected_identity(identity, SHA, "2026.10.3")


def valid_evidence(phase: str) -> dict:
    base = {"schema_version": 2, "status": "succeeded", "phase": phase}
    analyses = [
        {
            "analysis_id": f"analysis-{index}",
            "method_id": method,
            "result_payload_sha256": HASH,
            "source_result_artifact_sha256": HASH,
        }
        for index, method in enumerate(METHODS)
    ]
    predictions = [
        {
            "family": family,
            "manifest_sha256": HASH,
            "request": {"rows": []},
            "prediction": {"rows": []},
        }
        for family in FAMILIES
    ]
    if phase == "initial":
        return {
            **base,
            "runtime": {"build_commit": SHA},
            "dataset_version_id": "version-1",
            "ui_analysis_post_count": 3,
            "analyses": analyses,
            "predictions": predictions,
            "network_guard_checks": [f"check-{index}" for index in range(9)],
        }
    if phase == "resume":
        return {
            **base,
            "runtime": {"build_commit": SHA},
            "dataset_version_id": "version-1",
            "analysis_post_count": 0,
            "analyses": analyses,
            "predictions": predictions,
        }
    return {
        **base,
        "original_server_unreachable": True,
        "browser_network_offline": True,
        "http_request_count": 0,
        "reports": [
            {"family": family, "locale": locale, "sha256": HASH}
            for family in FAMILIES
            for locale in ("ko", "en")
        ],
    }


PHASE_FILES = {
    "initial": "application-smoke.json",
    "resume": "resume-smoke.json",
    "offline": "offline-smoke.json",
}


@pytest.mark.parametrize("phase", PHASE_FILES)
def test_complete_browser_phase_evidence_is_accepted_without_mutation(phase: str) -> None:
    evidence = valid_evidence(phase)
    original = copy.deepcopy(evidence)
    VERIFY.require_browser_evidence(evidence, PHASE_FILES[phase])
    assert evidence == original


@pytest.mark.parametrize("phase", PHASE_FILES)
@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "running"),
        ("status", "failed"),
        ("schema_version", 1),
        ("schema_version", True),
        ("schema_version", "2"),
    ],
)
def test_failed_or_old_browser_evidence_is_not_success(phase: str, field: str, value) -> None:
    evidence = valid_evidence(phase)
    evidence[field] = value
    with pytest.raises(ValueError):
        VERIFY.require_browser_evidence(evidence, PHASE_FILES[phase])


@pytest.mark.parametrize("phase", PHASE_FILES)
@pytest.mark.parametrize("replacement", [None, "other-phase"])
def test_wrong_or_missing_browser_phase_is_rejected(phase: str, replacement: str | None) -> None:
    evidence = valid_evidence(phase)
    if replacement is None:
        del evidence["phase"]
    else:
        evidence["phase"] = replacement
    with pytest.raises(ValueError):
        VERIFY.require_browser_evidence(evidence, PHASE_FILES[phase])


@pytest.mark.parametrize("phase", ["initial", "resume"])
@pytest.mark.parametrize("field", ["analyses", "predictions"])
def test_restore_or_initial_evidence_cannot_omit_actual_collections(phase: str, field: str) -> None:
    evidence = valid_evidence(phase)
    del evidence[field]
    with pytest.raises(ValueError):
        VERIFY.require_browser_evidence(evidence, PHASE_FILES[phase])


@pytest.mark.parametrize("phase", ["initial", "resume"])
@pytest.mark.parametrize("field", ["analyses", "predictions"])
def test_same_length_wrong_collection_type_does_not_pass(phase: str, field: str) -> None:
    evidence = valid_evidence(phase)
    evidence[field] = "x" * len(evidence[field])
    with pytest.raises(ValueError):
        VERIFY.require_browser_evidence(evidence, PHASE_FILES[phase])


@pytest.mark.parametrize("phase", ["initial", "resume"])
def test_duplicate_method_cannot_replace_a_missing_method(phase: str) -> None:
    evidence = valid_evidence(phase)
    evidence["analyses"][0] = copy.deepcopy(evidence["analyses"][1])
    with pytest.raises(ValueError):
        VERIFY.require_browser_evidence(evidence, PHASE_FILES[phase])


def test_resume_must_not_post_new_analysis() -> None:
    evidence = valid_evidence("resume")
    evidence["analysis_post_count"] = 1
    with pytest.raises(ValueError):
        VERIFY.require_browser_evidence(evidence, PHASE_FILES["resume"])


@pytest.mark.parametrize(
    "field,value",
    [
        ("original_server_unreachable", False),
        ("browser_network_offline", False),
        ("http_request_count", 1),
        ("http_request_count", False),
        ("reports", []),
        ("reports", "xxxx"),
    ],
)
def test_offline_phase_requires_stopped_server_and_actual_reports(field: str, value) -> None:
    evidence = valid_evidence("offline")
    evidence[field] = value
    with pytest.raises(ValueError):
        VERIFY.require_browser_evidence(evidence, PHASE_FILES["offline"])


def test_browser_runner_does_not_reuse_existing_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "previous"
    output.mkdir()
    monkeypatch.setattr(
        VERIFY.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("Existing evidence cannot run"),
    )
    with pytest.raises(ValueError, match="new output"):
        VERIFY.run_browser_stage(ROOT, output, "--url", "http://127.0.0.1:8600")


def test_browser_runner_requires_current_success_after_zero_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "new"
    cleanup = []
    process = SimpleNamespace(wait=lambda timeout: 0)

    def popen(argv, **kwargs):
        assert kwargs["start_new_session"] is True
        assert kwargs["cwd"] == output.parent
        assert "--output" in argv and str(output) in argv
        output.mkdir()
        (output / "application-smoke.json").write_text(
            json.dumps({"schema_version": 2, "status": "failed"}), encoding="utf-8"
        )
        return process

    monkeypatch.setattr(VERIFY.subprocess, "Popen", popen)
    monkeypatch.setattr(VERIFY, "stop", lambda child: cleanup.append(child))
    with pytest.raises(ValueError, match="successful"):
        VERIFY.run_browser_stage(ROOT, output, "--url", "http://127.0.0.1:8600")
    assert cleanup == [process]


@pytest.mark.parametrize("timeout", [False, True])
def test_browser_failure_always_cleans_owned_process_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, timeout: bool
) -> None:
    cleaned = []

    def wait(*, timeout: float):
        assert timeout == 600
        if should_timeout:
            raise subprocess.TimeoutExpired("synthetic driver", timeout)
        return 2

    should_timeout = timeout
    process = SimpleNamespace(wait=wait, args=["synthetic driver"], pid=321)
    monkeypatch.setattr(VERIFY.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(VERIFY, "stop", lambda child: cleaned.append(child))
    with pytest.raises(subprocess.SubprocessError):
        VERIFY.run_browser_stage(ROOT, tmp_path / "new", "--url", "http://127.0.0.1:8600")
    assert cleaned == [process]
    assert not (tmp_path / "new/application-smoke.json").exists()


def test_stop_uses_only_owned_group_and_finite_graceful_and_kill_waits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signals = []
    waits = []
    monkeypatch.setattr(VERIFY.signal, "SIGKILL", 9, raising=False)
    monkeypatch.setattr(
        VERIFY.os, "killpg", lambda pid, sig: signals.append((pid, sig)), raising=False
    )

    def wait(*, timeout):
        waits.append(timeout)
        if len(waits) == 1:
            raise subprocess.TimeoutExpired("synthetic driver", timeout)
        return 0

    VERIFY.stop(SimpleNamespace(pid=321, wait=wait))
    assert signals == [(321, VERIFY.signal.SIGTERM), (321, VERIFY.signal.SIGKILL)]
    assert waits == [15, 5]


def test_artifact_hashes_exclude_mutable_database_and_root_files(tmp_path: Path) -> None:
    for name, contents in {
        "workspaces/v1/canonical.jsonl": b"data",
        "artifacts/model.npz": b"model",
        "db/metadata.sqlite": b"database",
        ".workspace.lock": b"lock",
        "runtime.log": b"mutable log",
    }.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
    result = VERIFY.immutable_workspace_files(tmp_path)
    assert result == {
        "workspaces/v1/canonical.jsonl": hashlib.sha256(b"data").hexdigest(),
        "artifacts/model.npz": hashlib.sha256(b"model").hexdigest(),
    }
    (tmp_path / "db/metadata.sqlite").write_bytes(b"new metadata")
    (tmp_path / "artifacts/new-report.html").write_bytes(b"new report")
    VERIFY.require_unchanged_artifacts(tmp_path, result)


@pytest.mark.parametrize("delete", [False, True])
def test_original_artifact_missing_or_mutated_is_rejected(tmp_path: Path, delete: bool) -> None:
    directory = tmp_path / "artifacts"
    directory.mkdir()
    path = directory / "result.json"
    path.write_bytes(b"original")
    expected = VERIFY.immutable_workspace_files(tmp_path)
    (directory / "other.json").write_bytes(b"other")
    if delete:
        path.unlink()
    else:
        path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        VERIFY.require_unchanged_artifacts(tmp_path, expected)


def test_empty_workspace_is_not_artifact_integrity_proof(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No persisted"):
        VERIFY.immutable_workspace_files(tmp_path)


def test_linked_namespace_root_is_rejected_before_traversal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    linked = tmp_path / "workspaces"
    original_is_symlink = Path.is_symlink
    original_rglob = Path.rglob

    def is_symlink(path):
        return path == linked or original_is_symlink(path)

    def rglob(path, pattern):
        if path == linked:
            pytest.fail("Linked namespace root must not be traversed")
        return original_rglob(path, pattern)

    monkeypatch.setattr(Path, "is_symlink", is_symlink)
    monkeypatch.setattr(Path, "rglob", rglob)
    with pytest.raises(ValueError, match="link"):
        VERIFY.immutable_workspace_files(tmp_path)


@pytest.mark.parametrize(
    "returncode,message,change_marker",
    [
        (0, "Release is in use", False),
        (2, "different failure", False),
        (2, "Release is in use", True),
    ],
)
def test_live_installer_refusal_requires_exact_reason_and_unchanged_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    message: str,
    change_marker: bool,
) -> None:
    root = tmp_path / "release"
    root.mkdir()
    (root / ".installed").write_bytes(b"synthetic marker")
    monkeypatch.setattr(
        VERIFY,
        "bootstrap_identity",
        lambda *args: {"source_commit": SHA, "verification_status": "verified"},
    )

    def popen(argv, **kwargs):
        assert argv == [str(root / "install.sh")]
        assert kwargs["start_new_session"] is True
        kwargs["stdout"].write(message.encode())
        if change_marker:
            (root / ".installed").write_bytes(b"changed")
        return SimpleNamespace(wait=lambda timeout: returncode)

    monkeypatch.setattr(VERIFY.subprocess, "Popen", popen)
    with pytest.raises(ValueError):
        VERIFY.verify_live_reinstall_refusal(root, {}, tmp_path)


def test_live_installer_refusal_accepts_unchanged_locked_installation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "release"
    root.mkdir()
    (root / ".installed").write_bytes(b"synthetic marker")
    monkeypatch.setattr(
        VERIFY,
        "bootstrap_identity",
        lambda *args: {"source_commit": SHA, "verification_status": "verified"},
    )

    def popen(argv, **kwargs):
        kwargs["stdout"].write(b"Release is in use; stop it before reinstalling")
        return SimpleNamespace(wait=lambda timeout: 2)

    monkeypatch.setattr(VERIFY.subprocess, "Popen", popen)
    result = VERIFY.verify_live_reinstall_refusal(root, {}, tmp_path)
    assert result["status"] == "passed" and result["installed_identity_unchanged"] is True
    assert result["marker_sha256"] == hashlib.sha256(b"synthetic marker").hexdigest()


def test_live_refusal_rechecks_installed_files_not_just_unchanged_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "release"
    root.mkdir()
    (root / ".installed").write_bytes(b"unchanged marker")
    evidence = iter(
        [
            {"source_commit": SHA, "files_sha256": HASH},
            {"source_commit": SHA, "files_sha256": "c" * 64},
        ]
    )
    monkeypatch.setattr(VERIFY, "bootstrap_identity", lambda *args: next(evidence))

    def popen(argv, **kwargs):
        kwargs["stdout"].write(b"Release is in use; stop it before reinstalling")
        return SimpleNamespace(wait=lambda timeout: 2)

    monkeypatch.setattr(VERIFY.subprocess, "Popen", popen)
    with pytest.raises(ValueError, match="installed application"):
        VERIFY.verify_live_reinstall_refusal(root, {}, tmp_path)
