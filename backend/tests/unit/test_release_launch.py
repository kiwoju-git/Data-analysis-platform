import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.runtime_contract import API_CONTRACT_VERSION, RUNTIME_CAPABILITIES
from app.launch import verify_release
from app.storage.metadata import SCHEMA_VERSION


def release_fixture(root: Path) -> None:
    (root / "web").mkdir()
    (root / "wheels").mkdir()
    for filename, contents in {
        "web/index.html": "<html>release</html>",
        "requirements-release.lock": "# fixture\n",
        "install.sh": "#!/bin/sh\n",
        "run.sh": "#!/bin/sh\n",
    }.items():
        (root / filename).write_text(contents, encoding="utf-8")
    info = {
        "source_commit": "a" * 40,
        "api_contract_version": API_CONTRACT_VERSION,
        "metadata_schema_version": SCHEMA_VERSION,
        "required_capabilities": RUNTIME_CAPABILITIES,
        "python_target": "3.12",
        "os": "ubuntu24.04",
        "architecture": "x86_64",
        "lock_sha256": hashlib.sha256(
            (root / "requirements-release.lock").read_bytes()
        ).hexdigest(),
    }
    (root / "BUILD_INFO.json").write_text(json.dumps(info), encoding="utf-8")
    manifest = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}"
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]
    (root / "FILES.sha256").write_text("\n".join(manifest) + "\n", encoding="utf-8")


def test_release_verification_and_tamper_rejection(tmp_path: Path) -> None:
    release_fixture(tmp_path)
    assert verify_release(tmp_path)["source_commit"] == "a" * 40
    (tmp_path / "web/index.html").write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_release(tmp_path)


def test_unmanifested_asset_and_traversal_rejected(tmp_path: Path) -> None:
    release_fixture(tmp_path)
    (tmp_path / "web/extra.js").write_text("extra", encoding="utf-8")
    with pytest.raises(ValueError, match="unverified"):
        verify_release(tmp_path)
    (tmp_path / "FILES.sha256").write_text("a" * 64 + "  ../outside\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsafe"):
        verify_release(tmp_path)


def test_launcher_sets_environment_before_uvicorn_import() -> None:
    import app.launch

    source = Path(app.launch.__file__).read_text(encoding="utf-8")
    assert source.index("os.environ.update(") < source.index("    import uvicorn")
    assert '"app.main:app"' in source
    assert "from app.main" not in source


def prepare_launcher(monkeypatch, tmp_path, *, arguments=(), addresses=None):
    import app.launch as launch

    root = tmp_path / "release with spaces"
    root.mkdir()
    release_fixture(root)
    monkeypatch.setattr(launch.platform, "system", lambda: "Linux")
    monkeypatch.setattr(launch.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(launch.platform, "python_implementation", lambda: "CPython")
    monkeypatch.setattr(launch.sys, "version_info", (3, 12, 0, "final", 0))
    monkeypatch.setattr(launch.sys, "argv", ["app.launch", "--release-root", str(root), *arguments])
    port_probe = Mock()
    discovery = Mock(return_value=["192.168.40.12"] if addresses is None else addresses)
    monkeypatch.setattr(launch, "check_tcp_port_available", port_probe)
    monkeypatch.setattr(launch, "local_linux_ipv4_addresses", discovery)
    names = [
        "DATALAB_GIT_COMMIT",
        "DATALAB_FRONTEND_DIST",
        "DATALAB_ENVIRONMENT",
        "DATALAB_BIND_HOST",
        "DATALAB_BIND_PORT",
        "DATALAB_TRUSTED_LAN",
        "DATALAB_TRUSTED_LAN_HOSTS",
        "DATALAB_WORKSPACE_ROOT",
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ]
    for name in names:
        monkeypatch.setenv(name, "prior-value")
    snapshots = []
    run = Mock()
    import builtins

    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "uvicorn":
            snapshots.append({key: os.environ.get(key) for key in names})
            return SimpleNamespace(run=run)
        if name == "app.main":
            raise AssertionError("Launcher must defer app import to Uvicorn")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    return launch, root, port_probe, discovery, snapshots, run


@pytest.mark.parametrize("local_only", [False, True])
def test_launcher_applies_network_mode_and_identity_before_uvicorn_import(
    tmp_path, monkeypatch, capsys, local_only
):
    workspace = tmp_path / "external workspace"
    arguments = ["--workspace-root", str(workspace), "--port", "18600"]
    if local_only:
        arguments.append("--local-only")
    launch, root, probe, discovery, snapshots, run = prepare_launcher(
        monkeypatch, tmp_path, arguments=arguments
    )
    launch.main()
    host = "127.0.0.1" if local_only else "0.0.0.0"
    probe.assert_called_once_with(host, 18600)
    if local_only:
        discovery.assert_not_called()
    else:
        discovery.assert_called_once_with()
    assert len(snapshots) == 1
    environment = snapshots[0]
    assert environment["DATALAB_GIT_COMMIT"] == "a" * 40
    assert environment["DATALAB_FRONTEND_DIST"] == str(root / "web")
    assert environment["DATALAB_ENVIRONMENT"] == "production"
    assert environment["DATALAB_BIND_HOST"] == host
    assert environment["DATALAB_BIND_PORT"] == "18600"
    assert environment["DATALAB_TRUSTED_LAN"] == ("false" if local_only else "true")
    assert json.loads(environment["DATALAB_TRUSTED_LAN_HOSTS"]) == (
        [] if local_only else ["192.168.40.12"]
    )
    assert environment["DATALAB_WORKSPACE_ROOT"] == str(workspace)
    for name in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        assert environment[name] == "1"
    run.assert_called_once_with(
        "app.main:app", host=host, port=18600, workers=1, reload=False, proxy_headers=False
    )
    output = capsys.readouterr().out
    assert "Local URL: http://127.0.0.1:18600/home" in output
    assert ("LAN URL: http://192.168.40.12:18600/home" in output) is not local_only
    assert ("share read/write/delete access" in output) is not local_only
    assert not workspace.exists()


def test_launcher_default_is_lan_on_port_8600_and_preserves_workspace_override(
    tmp_path, monkeypatch, capsys
):
    launch, _, probe, _, snapshots, run = prepare_launcher(monkeypatch, tmp_path)
    launch.main()
    probe.assert_called_once_with("0.0.0.0", 8600)
    assert snapshots[0]["DATALAB_WORKSPACE_ROOT"] == "prior-value"
    assert run.call_args.kwargs["host"] == "0.0.0.0"
    assert "No login, RBAC or TLS" in capsys.readouterr().out


@pytest.mark.parametrize("failure_phase", ["manifest", "port", "discovery"])
def test_launcher_fails_before_environment_or_server_on_startup_error(
    tmp_path, monkeypatch, failure_phase
):
    launch, root, probe, discovery, snapshots, run = prepare_launcher(monkeypatch, tmp_path)
    if failure_phase == "manifest":
        (root / "web/index.html").write_text("tampered", encoding="utf-8")
    elif failure_phase == "port":
        probe.side_effect = OSError("occupied")
    else:
        discovery.side_effect = OSError("address discovery failed")
    with pytest.raises(SystemExit) as error:
        launch.main()
    assert error.value.code == 2
    assert os.environ["DATALAB_GIT_COMMIT"] == "prior-value"
    assert snapshots == []
    run.assert_not_called()


def test_empty_discovery_is_explicit_and_does_not_invent_a_lan_url(tmp_path, monkeypatch, capsys):
    launch, _, _, _, snapshots, run = prepare_launcher(monkeypatch, tmp_path, addresses=[])
    launch.main()
    output = capsys.readouterr().out
    assert "No non-loopback IPv4 address found" in output
    assert "LAN URL:" not in output
    assert snapshots[0]["DATALAB_TRUSTED_LAN_HOSTS"] == "[]"
    run.assert_called_once()
