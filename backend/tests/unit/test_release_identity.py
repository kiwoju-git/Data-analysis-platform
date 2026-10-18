"""Synthetic immutable wheels verify release identity without importing app code."""

import importlib.util
import json
import os
import re
import subprocess
import sys
import zipfile
from contextlib import nullcontext
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "release_identity_test_bootstrap", ROOT / "release_bootstrap.py"
)
assert SPEC is not None and SPEC.loader is not None
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)
DIST = "datalab_studio_backend-0.1.0.dist-info"


def manifest(root: Path) -> None:
    files = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and not path.relative_to(root).parts[0].startswith(".")
        and path.name != "FILES.sha256"
    ]
    (root / "FILES.sha256").write_text(
        "\n".join(
            f"{bootstrap.digest(path)}  {path.relative_to(root).as_posix()}"
            for path in sorted(files)
        )
        + "\n",
        encoding="utf-8",
    )


def synthetic_release(root: Path, *, installed: bool = True) -> tuple[dict, Path]:
    (root / "web").mkdir(parents=True)
    (root / "wheels").mkdir()
    for filename, value in {
        "web/index.html": "<html>synthetic</html>",
        "install.sh": "#!/bin/sh\n",
        "run.sh": "#!/bin/sh\n",
        "release_bootstrap.py": (ROOT / "release_bootstrap.py").read_text(encoding="utf-8"),
        "requirements-release.lock": "datalab-studio-backend==0.1.0\n",
    }.items():
        (root / filename).write_text(value, encoding="utf-8")
    identity = {
        "source_commit": "a" * 40,
        "release_version": "2026.10.3",
        "api_contract_version": 24,
        "metadata_schema_version": 22,
        "required_capabilities": {"asset_management": True},
        "python_target": "3.12",
        "os": "ubuntu24.04",
        "architecture": "x86_64",
    }
    wheel_files = {
        "app/__init__.py": b"",
        "app/launch.py": b"raise RuntimeError('old launcher must not execute')\n",
        "app/_release_build.json": json.dumps(identity).encode(),
        f"{DIST}/METADATA": (
            b"Metadata-Version: 2.1\nName: datalab-studio-backend\nVersion: 0.1.0\n"
        ),
        f"{DIST}/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        f"{DIST}/RECORD": b"",
    }
    wheel = root / "wheels/datalab_studio_backend-0.1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, data in wheel_files.items():
            archive.writestr(name, data)
    info = {
        **identity,
        "application_wheel": wheel.relative_to(root).as_posix(),
        "application_wheel_sha256": bootstrap.digest(wheel),
        "lock_sha256": bootstrap.digest(root / "requirements-release.lock"),
    }
    (root / "BUILD_INFO.json").write_text(json.dumps(info), encoding="utf-8")
    manifest(root)
    site = root / ".venv/lib/python3.12/site-packages"
    if installed:
        site.mkdir(parents=True)
        (root / ".venv/pyvenv.cfg").write_text(
            "include-system-site-packages = false\nversion = 3.12.8\n", encoding="utf-8"
        )
        for name, data in wheel_files.items():
            destination = site / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        bootstrap.commit_installation_marker(root, bootstrap.verify_release_payload(root))
    return info, site


def test_payload_is_independent_of_installation(tmp_path):
    info, _ = synthetic_release(tmp_path, installed=False)
    assert bootstrap.verify_release_payload(tmp_path)["source_commit"] == info["source_commit"]
    assert not (tmp_path / ".venv").exists()
    with pytest.raises(ValueError, match="virtual environment"):
        bootstrap.verify_installed_release(tmp_path)


def test_installed_evidence_comes_from_wheel_and_marker(tmp_path):
    info, _ = synthetic_release(tmp_path)
    evidence = bootstrap.verify_installed_release(tmp_path)
    assert evidence["verification_status"] == "verified"
    assert evidence["source_commit"] == info["source_commit"]
    assert evidence["application_wheel_sha256"] == info["application_wheel_sha256"]
    assert evidence["release_manifest_sha256"] == bootstrap.digest(tmp_path / "FILES.sha256")
    assert len(evidence["installed_application_files_sha256"]) == 64


@pytest.mark.parametrize("target", ["app/launch.py", "app/_release_build.json", f"{DIST}/METADATA"])
def test_mutated_installed_files_rejected_even_with_unchanged_marker(tmp_path, target):
    _, site = synthetic_release(tmp_path)
    replacement = (
        "Name: datalab-studio-backend\nVersion: 0.0.1\n"
        if target.endswith("/METADATA")
        else "old code"
    )
    (site / target).write_text(replacement, encoding="utf-8")
    with pytest.raises(ValueError, match="Installed application checksum mismatch"):
        bootstrap.verify_installed_release(tmp_path)


def test_copied_build_resource_does_not_certify_old_code(tmp_path):
    _, site = synthetic_release(tmp_path)
    resource = (site / bootstrap.RESOURCE).read_bytes()
    (site / "app/launch.py").write_text("old = True\n", encoding="utf-8")
    (site / bootstrap.RESOURCE).write_bytes(resource)
    # Even a fabricated marker cannot remove the independent wheel-file check.
    with pytest.raises(ValueError, match="checksum mismatch"):
        bootstrap.commit_installation_marker(tmp_path, bootstrap.verify_release_payload(tmp_path))


@pytest.mark.parametrize("extra", ["app/extra.py", "app/__pycache__/launch.cpython-312.pyc"])
def test_unowned_application_code_and_bytecode_rejected(tmp_path, extra):
    _, site = synthetic_release(tmp_path)
    path = site / extra
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(b"unowned")
    with pytest.raises(ValueError, match="unowned code or bytecode"):
        bootstrap.verify_installed_release(tmp_path)


@pytest.mark.parametrize(
    "content", [b"", b"a" * 40, b"{}", b'{"schema_version":1,"schema_version":1}']
)
def test_partial_or_foreign_marker_rejected(tmp_path, content):
    synthetic_release(tmp_path)
    (tmp_path / ".installed").write_bytes(content)
    with pytest.raises(ValueError):
        bootstrap.verify_installed_release(tmp_path)


def test_marker_replace_failure_does_not_publish_partial_marker(tmp_path, monkeypatch):
    info, _ = synthetic_release(tmp_path)
    (tmp_path / ".installed").unlink()

    def fail_replace(*args):
        raise OSError("simulated crash before publication")

    monkeypatch.setattr(bootstrap.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated"):
        bootstrap.commit_installation_marker(tmp_path, bootstrap.verify_release_payload(tmp_path))
    assert not (tmp_path / ".installed").exists()
    assert not list(tmp_path.glob(".installed-*.tmp"))
    assert bootstrap.verify_release_payload(tmp_path)["source_commit"] == info["source_commit"]


@pytest.mark.parametrize("failure_call", [1, 2])
def test_install_or_pip_check_failure_invalidates_marker(tmp_path, monkeypatch, failure_call):
    synthetic_release(tmp_path)
    binary = tmp_path / ".venv/bin/python"
    binary.parent.mkdir()
    binary.write_bytes(b"synthetic interpreter; subprocess is injected")
    monkeypatch.setattr(bootstrap, "release_lock", lambda *args, **kwargs: nullcontext())
    calls = []

    def fail_command(command, **kwargs):
        calls.append(command)
        if len(calls) == failure_call:
            raise subprocess.CalledProcessError(1, "synthetic pip failure")

    monkeypatch.setattr(bootstrap.subprocess, "run", fail_command)
    with pytest.raises(subprocess.CalledProcessError):
        bootstrap.install(tmp_path)
    assert not (tmp_path / ".installed").exists()
    assert calls[0][1:4] == ["-I", "-S", "-B"]
    assert "--no-index" in calls[0] and "--no-compile" in calls[0]
    assert "--require-hashes" in calls[0]


def test_changed_installed_record_cannot_hide_modified_application(tmp_path):
    _, site = synthetic_release(tmp_path)
    (site / "app/launch.py").write_text("modified = True\n", encoding="utf-8")
    (site / DIST / "RECORD").write_text("app/launch.py,sha256=fabricated,16\n")
    with pytest.raises(ValueError, match="checksum mismatch"):
        bootstrap.verify_installed_release(tmp_path)


def test_actual_hatch_wheel_includes_staging_only_resource(tmp_path):
    import shutil

    source = tmp_path / "staged source"
    source.mkdir()
    shutil.copy2(ROOT / "backend/pyproject.toml", source / "pyproject.toml")
    shutil.copy2(ROOT / "backend/README.md", source / "README.md")
    # A real wheel build, without importing statistics or copying a user workspace.
    app = source / "app"
    app.mkdir()
    (app / "__init__.py").write_text("", encoding="utf-8")
    resource = {"source_commit": "b" * 40, "release_version": "2026.10.3"}
    (app / "_release_build.json").write_text(json.dumps(resource), encoding="utf-8")
    output = tmp_path / "wheels"
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--no-build-isolation",
            "--no-index",
            "--wheel-dir",
            str(output),
            str(source),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        env=dict(os.environ, PIP_NO_INDEX="1", PIP_DISABLE_PIP_VERSION_CHECK="1"),
    )
    assert result.returncode == 0, result.stderr
    wheels = list(output.glob("datalab_studio_backend-*.whl"))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as archive:
        assert json.loads(archive.read("app/_release_build.json")) == resource
        assert not any(name.endswith(".pyc") for name in archive.namelist())


def test_payload_tampering_and_unmanifested_assets_rejected(tmp_path):
    synthetic_release(tmp_path)
    (tmp_path / "web/foreign.js").write_bytes(b"foreign")
    with pytest.raises(ValueError, match="unverified"):
        bootstrap.verify_release_payload(tmp_path)
    (tmp_path / "web/foreign.js").unlink()
    (tmp_path / "FILES.sha256").write_text("a" * 64 + "  ../outside\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsafe"):
        bootstrap.verify_release_payload(tmp_path)


def test_duplicate_distribution_rejected(tmp_path):
    _, site = synthetic_release(tmp_path)
    duplicate = site / "DATALAB_Studio_Backend-0.0.1.dist-info"
    duplicate.mkdir()
    (duplicate / "METADATA").write_text("Name: DATALAB_Studio_Backend\nVersion: 0.0.1\n")
    with pytest.raises(ValueError, match="duplicated"):
        bootstrap.verify_installed_release(tmp_path)


def test_mismatched_wheel_resource_rejected_before_install(tmp_path):
    synthetic_release(tmp_path, installed=False)
    info = json.loads((tmp_path / "BUILD_INFO.json").read_text())
    info["source_commit"] = "b" * 40
    (tmp_path / "BUILD_INFO.json").write_text(json.dumps(info))
    manifest(tmp_path)
    with pytest.raises(ValueError, match="wheel source identity mismatch"):
        bootstrap.verify_release_payload(tmp_path)


def test_preimport_subprocess_rejects_old_app_without_pth_or_app_execution(tmp_path):
    _, site = synthetic_release(tmp_path)
    sentinel = tmp_path / "executed.txt"
    malicious = f"from pathlib import Path; Path({str(sentinel)!r}).write_text('executed')\n"
    (site / "app/__init__.py").write_text(malicious)
    (site / "unexpected.pth").write_text("import pathlib; " + malicious.split("; ", 1)[1])
    script = (
        "import importlib.util,sys; from pathlib import Path; "
        "s=importlib.util.spec_from_file_location('bootstrap',sys.argv[1]); "
        "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
        "m.verify_installed_release(Path(sys.argv[2]))"
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-B",
            "-c",
            script,
            str(ROOT / "release_bootstrap.py"),
            str(tmp_path),
        ],
        cwd=tmp_path,
        env=dict(os.environ, PYTHONPATH=str(site)),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode != 0
    assert "Installed application checksum mismatch" in completed.stderr
    assert not sentinel.exists()


def test_real_venv_pth_cannot_execute_under_guarded_entry(tmp_path):
    virtual = tmp_path / "actual venv"
    created = subprocess.run(
        [sys.executable, "-I", "-B", "-m", "venv", "--without-pip", str(virtual)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert created.returncode == 0, created.stderr
    python = virtual / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    site = virtual / (
        "Lib/site-packages"
        if os.name == "nt"
        else f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
    )
    sentinel = tmp_path / "pth-sentinel"
    (site / "probe.pth").write_text(
        f"import pathlib; pathlib.Path({str(sentinel)!r}).write_text('executed')\n",
        encoding="utf-8",
    )
    control = subprocess.run(
        [str(python), "-I", "-B", "-c", "pass"], capture_output=True, text=True, timeout=30
    )
    assert control.returncode == 0 and sentinel.is_file()
    sentinel.unlink()
    guarded = subprocess.run(
        [str(python), "-I", "-S", "-B", "-c", "import sys; print(sys.flags.no_site)"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert guarded.returncode == 0 and guarded.stdout.strip() == "1"
    assert not sentinel.exists()


@pytest.mark.parametrize(
    "version,valid",
    [
        ("2026.10.3", True),
        ("2026.1234.1", True),
        ("99999999.99999999.99999999", True),
        ("0.0.0", True),
        ("01.2.3", False),
        ("2026.01.3", False),
        ("2026.1.03", False),
        ("100000000.1.1", False),
        ("1.2.3\n", False),
        ("../1.2.3", False),
        ("1.2", False),
    ],
)
def test_builder_and_bootstrap_share_bounded_version_contract(
    tmp_path, monkeypatch, version, valid
):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "identity_builder_test", ROOT / "scripts/build_linux_release.py"
    )
    assert spec is not None and spec.loader is not None
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    assert builder.RELEASE_VERSION_PATTERN == bootstrap.RELEASE_VERSION_PATTERN
    assert bool(re.fullmatch(builder.RELEASE_VERSION_PATTERN, version)) is valid
    info, _ = synthetic_release(tmp_path, installed=False)
    info["release_version"] = version
    if valid:
        assert bootstrap._identity(info)["release_version"] == version
    else:
        with pytest.raises(ValueError, match="Invalid release version"):
            bootstrap._identity(info)


@pytest.mark.skipif(sys.platform != "linux", reason="Actual POSIX flock lifecycle")
def test_release_lock_shared_run_exclusive_install_and_crash_release(tmp_path):
    script = (
        "import importlib.util,sys,time; from pathlib import Path; "
        "s=importlib.util.spec_from_file_location('bootstrap',sys.argv[1]); "
        "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
        "lock=m.release_lock(Path(sys.argv[2]),exclusive=True); lock.__enter__(); "
        "print('locked',flush=True); time.sleep(30)"
    )
    with bootstrap.release_lock(tmp_path, exclusive=False):
        with bootstrap.release_lock(tmp_path, exclusive=False):
            with pytest.raises(ValueError, match="in use"):
                with bootstrap.release_lock(tmp_path, exclusive=True):
                    pass
    process = subprocess.Popen(
        [
            sys.executable,
            "-I",
            "-S",
            "-B",
            "-c",
            script,
            str(ROOT / "release_bootstrap.py"),
            str(tmp_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout is not None and process.stdout.readline().strip() == "locked"
        inode = (tmp_path / ".release.lock").stat().st_ino
        with pytest.raises(ValueError, match="in use"):
            with bootstrap.release_lock(tmp_path, exclusive=False):
                pass
        process.kill()
        process.wait(timeout=10)
        with bootstrap.release_lock(tmp_path, exclusive=True):
            assert (tmp_path / ".release.lock").stat().st_ino == inode
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=10)
