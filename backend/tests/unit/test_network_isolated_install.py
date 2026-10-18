"""Pure/contract checks; these are not a native Linux namespace execution."""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "network_isolated_install", ROOT / "scripts/network_isolated_install.py"
)
assert SPEC is not None and SPEC.loader is not None
ISOLATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ISOLATION)


def configuration() -> dict:
    return {
        "uid": 1001,
        "gid": 1002,
        "host_namespace": "net:[11]",
        "ports": {"ipv4": 32101, "ipv6": 32102},
    }


def valid_probe() -> dict:
    return {
        "uid": 1001,
        "gid": 1002,
        "effective_uid": 1001,
        "effective_gid": 1002,
        "supplementary_groups": [],
        "namespace": "net:[22]",
        "interfaces": ["lo"],
        "inherited_socket_fds": [],
        "usable_routes": False,
        "ipv4_blocked": True,
        "ipv6_blocked": True,
    }


def valid_child() -> dict:
    return {
        "before": valid_probe(),
        "grandchild": valid_probe(),
        "after": valid_probe(),
        "install_exit_code": 0,
        "owned_entries_checked": 500,
    }


def test_environment_is_allowlisted_and_input_is_not_mutated(tmp_path: Path) -> None:
    supplied = {
        "PATH": str(tmp_path),
        "PYTHON": sys.executable,
        "HOME": "not-owner-home",
        "GH_TOKEN": "secret",
        "GITHUB_TOKEN": "secret",
        "ACTIONS_RUNTIME_TOKEN": "secret",
        "PYTHONPATH": "injected",
        "PYTHONSTARTUP": "injected",
        "BASH_ENV": "injected",
        "ENV": "injected",
        "LD_PRELOAD": "injected",
        "LD_LIBRARY_PATH": "injected",
        "HTTPS_PROXY": "secret",
        "DATALAB_WORKSPACE_ROOT": "user-workspace",
    }
    before = supplied.copy()
    result = ISOLATION._safe_environment(supplied, tmp_path)
    assert supplied == before
    assert set(result) == {
        "PATH",
        "PYTHON",
        "HOME",
        "TMPDIR",
        "LANG",
        "LC_ALL",
        "PIP_NO_INDEX",
        "PIP_DISABLE_PIP_VERSION_CHECK",
        "PIP_CONFIG_FILE",
        "PYTHONDONTWRITEBYTECODE",
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
    }
    assert result["HOME"] == str(tmp_path / "home")
    assert result["TMPDIR"] == str(tmp_path / "tmp")
    assert result["PIP_CONFIG_FILE"] == "/dev/null"
    assert result["PIP_NO_INDEX"] == "1"
    assert "secret" not in json.dumps(result)


@pytest.mark.parametrize(
    "key,value",
    [
        ("PYTHON", "python"),
        ("PYTHON", ""),
        ("PATH", "relative"),
        ("PATH", ""),
        ("PATH", "\n"),
    ],
)
def test_invalid_environment_is_rejected(tmp_path: Path, key: str, value: str) -> None:
    env = {"PYTHON": sys.executable, "PATH": str(tmp_path), key: value}
    with pytest.raises(ISOLATION.NetworkIsolationError):
        ISOLATION._safe_environment(env, tmp_path)


def test_namespace_argv_drops_ids_and_keeps_shell_content_as_argument(tmp_path: Path) -> None:
    tools = {name: f"/usr/bin/{name}" for name in ("sudo", "timeout", "unshare")}
    config = tmp_path / "space; $(not-executed).json"
    result = ISOLATION._namespace_argv(tools, config, 1001, 1002, "/opt/python/bin/python")
    assert result[:13] == [
        "/usr/bin/sudo",
        "-n",
        "--",
        "/usr/bin/timeout",
        "--kill-after=5s",
        "600s",
        "/usr/bin/unshare",
        "--net",
        "--setgid",
        "1002",
        "--setuid",
        "1001",
        "--",
    ]
    assert result[13:17] == ["/opt/python/bin/python", "-I", "-S", "-B"]
    assert result[-2:] == ["child", str(config)]
    assert "--fork" not in result and "--user" not in result
    assert "bash" not in result and "-c" not in result


@pytest.mark.parametrize(
    "key,value,code",
    [
        ("uid", 0, "identity_invalid"),
        ("effective_uid", 0, "identity_invalid"),
        ("gid", 0, "identity_invalid"),
        ("effective_gid", 0, "identity_invalid"),
        ("supplementary_groups", [0], "identity_invalid"),
        ("namespace", "net:[11]", "namespace_invalid"),
        ("namespace", "not-a-namespace", "namespace_invalid"),
        ("interfaces", ["lo", "eth0"], "network_available"),
        ("interfaces", [], "network_available"),
        ("usable_routes", True, "network_available"),
        ("usable_routes", 0, "network_available"),
        ("inherited_socket_fds", [3], "inherited_socket"),
        ("ipv4_blocked", False, "control_accessible"),
        ("ipv6_blocked", False, "control_accessible"),
        ("ipv6_blocked", 1, "control_accessible"),
    ],
)
def test_every_isolation_proof_is_required(key: str, value, code: str) -> None:
    proof = valid_probe()
    proof[key] = value
    with pytest.raises(ISOLATION.NetworkIsolationError, match="network_isolation_" + code):
        ISOLATION._validate_probe(proof, configuration())


def test_child_and_grandchild_must_share_exact_namespace() -> None:
    child = valid_child()
    child["grandchild"]["namespace"] = "net:[33]"
    with pytest.raises(ISOLATION.NetworkIsolationError, match="namespace_changed"):
        ISOLATION._validate_evidence(child, configuration())


@pytest.mark.parametrize("phase", ["before", "grandchild", "after"])
def test_missing_phase_is_not_an_installation_proof(phase: str) -> None:
    child = valid_child()
    del child[phase]
    with pytest.raises(ISOLATION.NetworkIsolationError, match="evidence_invalid"):
        ISOLATION._validate_evidence(child, configuration())


@pytest.mark.parametrize(
    "key,value",
    [
        ("install_exit_code", 1),
        ("install_exit_code", 124),
        ("install_exit_code", False),
        ("owned_entries_checked", 0),
        ("owned_entries_checked", True),
        ("owned_entries_checked", ISOLATION.MAX_INSTALLED_ENTRIES + 1),
    ],
)
def test_partial_install_or_missing_ownership_cannot_succeed(key: str, value) -> None:
    child = valid_child()
    child[key] = value
    with pytest.raises(ISOLATION.NetworkIsolationError):
        ISOLATION._validate_evidence(child, configuration())


def test_complete_proof_is_accepted_without_mutation() -> None:
    child = valid_child()
    original = copy.deepcopy(child)
    ISOLATION._validate_evidence(child, configuration())
    assert child == original


def test_route_check_accepts_only_unusable_ipv6_loopback_pseudo_routes() -> None:
    reject = "0" * 32 + " 00 " + "0" * 32 + " 00 " + "0" * 32
    reject += " ffffffff 00000001 00000000 00200200 lo\n"
    assert (
        ISOLATION._usable_routes(
            "Iface Destination Gateway Flags RefCnt Use Metric Mask MTU Window IRTT\n", reject
        )
        is False
    )
    assert (
        ISOLATION._usable_routes("header\neth0 00000000 01020304 0003 0 0 100 00000000 0 0 0\n", "")
        is True
    )
    assert ISOLATION._usable_routes("header\n", reject.replace("00200200", "00000001")) is True


@pytest.mark.parametrize("ipv4,ipv6", [("header\nbroken", ""), ("header", "broken")])
def test_malformed_route_tables_fail_closed(ipv4: str, ipv6: str) -> None:
    with pytest.raises(ISOLATION.NetworkIsolationError, match="routes_invalid"):
        ISOLATION._usable_routes(ipv4, ipv6)


def test_real_parent_controls_are_reachable_with_both_protocols() -> None:
    try:
        with ISOLATION._host_controls() as ports:
            for _ in range(4):
                assert ISOLATION._host_proof(ports) == {
                    "ipv4_reachable": True,
                    "ipv6_reachable": True,
                }
    except OSError as error:
        pytest.skip(f"Local IPv6 control prerequisite unavailable: errno={error.errno}")


def test_unreachable_parent_control_is_hard_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ISOLATION, "_connects", lambda family, port: port == 1)
    with pytest.raises(ISOLATION.NetworkIsolationError, match="control_unreachable"):
        ISOLATION._host_proof({"ipv4": 1, "ipv6": 2})


def test_missing_host_tools_does_not_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ISOLATION.shutil, "which", lambda name, path: None)
    with pytest.raises(ISOLATION.NetworkIsolationError, match="tools_unavailable"):
        ISOLATION._tools()


def test_failed_evidence_write_removes_only_its_owned_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "proof.json"

    def fail(_fd):
        raise OSError("synthetic fsync failure")

    monkeypatch.setattr(ISOLATION.os, "fsync", fail)
    with pytest.raises(OSError):
        ISOLATION._write_json(path, {"status": "passed"})
    assert not path.exists()
    path.write_text("previous proof", encoding="utf-8")
    with pytest.raises(FileExistsError):
        ISOLATION._write_json(path, {"status": "passed"})
    assert path.read_text(encoding="utf-8") == "previous proof"


def test_non_linux_entrypoint_does_not_launch_any_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ISOLATION.platform, "system", lambda: "Windows")
    monkeypatch.setattr(ISOLATION, "_tools", lambda: pytest.fail("Must not launch tools"))
    with pytest.raises(ISOLATION.NetworkIsolationError, match="platform_unsupported"):
        ISOLATION.run_network_blocked_install(tmp_path, {}, tmp_path / "log", tmp_path / "proof")


@pytest.fixture
def mocked_native_boundary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "release directory"
    root.mkdir()
    (root / "install.sh").write_text("synthetic installer\n", encoding="utf-8")
    monkeypatch.setattr(ISOLATION.platform, "system", lambda: "Linux")
    monkeypatch.setattr(ISOLATION.platform, "platform", lambda: "Synthetic Linux unit fixture")
    monkeypatch.setattr(ISOLATION.platform, "python_version", lambda: "3.12.0")
    monkeypatch.setattr(ISOLATION.sys, "version_info", (3, 12, 0))
    for name, value in (("getuid", 1001), ("geteuid", 1001), ("getgid", 1002), ("getegid", 1002)):
        monkeypatch.setattr(ISOLATION.os, name, lambda value=value: value, raising=False)
    original_readlink = os.readlink
    monkeypatch.setattr(
        ISOLATION.os,
        "readlink",
        lambda path, *args, **kwargs: "net:[11]"
        if str(path) == "/proc/self/ns/net"
        else original_readlink(path, *args, **kwargs),
    )
    tools = {name: f"/usr/bin/{name}" for name in ("sudo", "timeout", "unshare")}
    monkeypatch.setattr(ISOLATION, "_tools", lambda: tools)
    monkeypatch.setattr(ISOLATION, "_tool_versions", lambda tools, env: {"timeout": "synthetic"})
    monkeypatch.setattr(
        ISOLATION.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0)
    )

    @contextlib.contextmanager
    def controls():
        yield {"ipv4": 32101, "ipv6": 32102}

    monkeypatch.setattr(ISOLATION, "_host_controls", controls)
    monkeypatch.setattr(
        ISOLATION, "_host_proof", lambda ports: {"ipv4_reachable": True, "ipv6_reachable": True}
    )

    def run(argv, env, log_path):
        config = ISOLATION._read_json(Path(argv[-1]))
        ISOLATION._write_json(Path(config["child_evidence"]), valid_child())
        log_path.write_text("synthetic subprocess\n", encoding="utf-8")

    monkeypatch.setattr(ISOLATION, "_run_namespace", run)
    return (
        root,
        {"PYTHON": sys.executable, "PATH": str(tmp_path)},
        tmp_path / "install.log",
        tmp_path / "proof.json",
    )


def test_mocked_complete_entrypoint_publishes_exact_evidence(mocked_native_boundary) -> None:
    root, env, log, proof = mocked_native_boundary
    original = env.copy()
    result = ISOLATION.run_network_blocked_install(root, env, log, proof)
    assert result == json.loads(proof.read_text(encoding="utf-8"))
    assert result["network_blocked_installation"] is True
    assert result["before"]["namespace"] != result["host_namespace"]
    assert result["grandchild"]["namespace"] == result["after"]["namespace"]
    assert result["runner_uid"] == 1001 and result["runner_gid"] == 1002
    assert result["installer_timeout_seconds"] < result["namespace_timeout_seconds"] == 600
    assert env == original
    assert not list(proof.parent.glob("network-proof-*"))


@pytest.mark.parametrize("existing", ["proof", "log"])
def test_previous_diagnostics_are_not_overwritten(mocked_native_boundary, existing: str) -> None:
    root, env, log, proof = mocked_native_boundary
    target = proof if existing == "proof" else log
    target.write_bytes(b"previous evidence")
    with pytest.raises(ISOLATION.NetworkIsolationError, match="output_invalid"):
        ISOLATION.run_network_blocked_install(root, env, log, proof)
    assert target.read_bytes() == b"previous evidence"


def test_post_install_host_control_failure_leaves_no_success(
    mocked_native_boundary, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, env, log, proof = mocked_native_boundary
    calls = 0

    def controls(ports):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ISOLATION.NetworkIsolationError("network_isolation_control_unreachable")
        return {"ipv4_reachable": True, "ipv6_reachable": True}

    monkeypatch.setattr(ISOLATION, "_host_proof", controls)
    with pytest.raises(ISOLATION.NetworkIsolationError, match="control_unreachable"):
        ISOLATION.run_network_blocked_install(root, env, log, proof)
    assert calls == 2 and not proof.exists()


def test_namespace_failure_never_runs_ordinary_installer(
    mocked_native_boundary, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, env, log, proof = mocked_native_boundary
    calls = []

    def fails(argv, env, log_path):
        calls.append(argv)
        raise ISOLATION.NetworkIsolationError("network_isolation_child_failed")

    monkeypatch.setattr(ISOLATION, "_run_namespace", fails)
    with pytest.raises(ISOLATION.NetworkIsolationError, match="child_failed"):
        ISOLATION.run_network_blocked_install(root, env, log, proof)
    assert len(calls) == 1 and not proof.exists()


def test_namespace_process_has_closed_fds_no_shell_and_bounded_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    class Process:
        stdout = io.BytesIO(b"synthetic installer output")

        def wait(self, *, timeout):
            assert timeout == ISOLATION.PARENT_SECONDS
            return 0

    def popen(argv, **kwargs):
        calls.append((argv, kwargs))
        return Process()

    monkeypatch.setattr(ISOLATION.subprocess, "Popen", popen)
    log = tmp_path / "install.log"
    ISOLATION._run_namespace(["sudo", "fixed-args"], {"PATH": "/usr/bin"}, log)
    assert log.read_bytes() == b"synthetic installer output"
    assert calls[0][1]["close_fds"] is True
    assert calls[0][1]["start_new_session"] is True
    assert calls[0][1]["stdin"] is subprocess.DEVNULL
    assert "shell" not in calls[0][1]


def test_log_overflow_is_drained_but_not_successful(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ISOLATION, "MAX_LOG_BYTES", 12)
    process = SimpleNamespace(stdout=io.BytesIO(b"x" * 100), wait=lambda timeout: 0)
    monkeypatch.setattr(ISOLATION.subprocess, "Popen", lambda *args, **kwargs: process)
    log = tmp_path / "install.log"
    with pytest.raises(ISOLATION.NetworkIsolationError, match="log_budget_exceeded"):
        ISOLATION._run_namespace(["sudo"], {}, log)
    assert log.stat().st_size == 12


def test_privileged_watchdog_timeout_never_claims_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    timeouts = []

    def wait(timeout):
        timeouts.append(timeout)
        raise subprocess.TimeoutExpired("synthetic", timeout)

    process = SimpleNamespace(stdout=io.BytesIO(b""), wait=wait)
    monkeypatch.setattr(ISOLATION.subprocess, "Popen", lambda *args, **kwargs: process)
    with pytest.raises(ISOLATION.NetworkIsolationError, match="cleanup_unconfirmed"):
        ISOLATION._run_namespace(["sudo"], {}, tmp_path / "install.log")
    assert len(timeouts) == 2 and all(0 < value <= ISOLATION.PARENT_SECONDS for value in timeouts)


@pytest.mark.parametrize("returncode", [0, 1, 124])
def test_installer_group_cleanup_runs_even_on_success(
    returncode: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = SimpleNamespace(pid=321, wait=lambda timeout: returncode)
    calls = []

    def popen(argv, **kwargs):
        assert kwargs["start_new_session"] is True
        assert kwargs["close_fds"] is True
        assert argv[:3] == ["/usr/bin/timeout", "--kill-after=5s", "540s"]
        return process

    monkeypatch.setattr(ISOLATION.subprocess, "Popen", popen)
    monkeypatch.setattr(ISOLATION, "_stop_installer_group", lambda item: calls.append(item))
    assert (
        ISOLATION._install({"timeout": "/usr/bin/timeout", "root": "release", "env": {}})
        == returncode
    )
    assert calls == [process]


def test_installer_timeout_still_cleans_only_owned_group(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def timeout(*, timeout):
        raise subprocess.TimeoutExpired("fixture", timeout)

    process = SimpleNamespace(pid=321, wait=timeout)
    monkeypatch.setattr(ISOLATION.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(ISOLATION, "_stop_installer_group", lambda item: calls.append(item))
    with pytest.raises(subprocess.TimeoutExpired):
        ISOLATION._install({"timeout": "/usr/bin/timeout", "root": "release", "env": {}})
    assert calls == [process]


def test_child_checks_grandchild_then_installs_then_checks_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = {
        **configuration(),
        "env": {"PYTHON": sys.executable, "PATH": "fixed"},
        "root": str(tmp_path),
        "timeout": "/usr/bin/timeout",
        "child_evidence": str(tmp_path / "child-proof.json"),
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(ISOLATION.os, "environ", {"GH_TOKEN": "not-inherited"})
    events = []

    def probe(_config):
        assert dict(os.environ) == config["env"]
        events.append("probe")
        return valid_probe()

    def grandchild(argv, **kwargs):
        events.append("grandchild")
        assert argv[1:4] == ["-I", "-S", "-B"]
        assert argv[-2:] == ["probe", str(config_path)]
        assert kwargs["close_fds"] is True
        assert kwargs["timeout"] == 10
        assert kwargs["env"] == config["env"]
        return SimpleNamespace(returncode=0, stdout=json.dumps(valid_probe()).encode())

    def install(_config):
        events.append("install")
        return 0

    def ownership(root, uid, gid):
        events.append("ownership")
        assert (root, uid, gid) == (tmp_path, 1001, 1002)
        return 50

    monkeypatch.setattr(ISOLATION, "_probe", probe)
    monkeypatch.setattr(ISOLATION.subprocess, "run", grandchild)
    monkeypatch.setattr(ISOLATION, "_install", install)
    monkeypatch.setattr(ISOLATION, "_verify_ownership", ownership)
    ISOLATION._child(config_path)
    assert events == ["probe", "grandchild", "install", "probe", "ownership"]
    proof = json.loads((tmp_path / "child-proof.json").read_text(encoding="utf-8"))
    ISOLATION._validate_evidence(proof, config)


@pytest.mark.parametrize(
    "returncode,output",
    [(2, b""), (0, b"null"), (0, b"invalid JSON"), (0, b"x" * (ISOLATION.MAX_JSON_BYTES + 1))],
    ids=["failed-process", "null-proof", "malformed-json", "oversized-proof"],
)
def test_invalid_grandchild_prevents_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, returncode: int, output: bytes
) -> None:
    config = {
        **configuration(),
        "env": {"PYTHON": sys.executable},
        "child_evidence": str(tmp_path / "child-proof.json"),
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(ISOLATION.os, "environ", {})
    monkeypatch.setattr(ISOLATION, "_probe", lambda _config: valid_probe())
    monkeypatch.setattr(
        ISOLATION.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=returncode, stdout=output),
    )
    monkeypatch.setattr(
        ISOLATION, "_install", lambda _: pytest.fail("Unverified child cannot install")
    )
    with pytest.raises(ISOLATION.NetworkIsolationError, match="grandchild_failed"):
        ISOLATION._child(config_path)
    assert not (tmp_path / "child-proof.json").exists()


def test_process_group_kill_escalates_only_its_owned_group(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    monkeypatch.setattr(ISOLATION.signal, "SIGKILL", 9, raising=False)
    ticks = iter([0, 6, 7, 7.1])
    monkeypatch.setattr(ISOLATION.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(ISOLATION.time, "sleep", lambda seconds: None)

    def killpg(pid, sig):
        calls.append((pid, sig))
        if sig == 0:
            raise ProcessLookupError

    monkeypatch.setattr(ISOLATION.os, "killpg", killpg, raising=False)
    process = SimpleNamespace(pid=321, wait=lambda timeout: 0)
    ISOLATION._stop_installer_group(process)
    assert calls == [(321, ISOLATION.signal.SIGTERM), (321, ISOLATION.signal.SIGKILL), (321, 0)]


def test_process_group_liveness_after_kill_is_not_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ISOLATION.signal, "SIGKILL", 9, raising=False)
    ticks = iter([0, 6, 7, 13])
    monkeypatch.setattr(ISOLATION.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(ISOLATION.os, "killpg", lambda pid, sig: None, raising=False)
    process = SimpleNamespace(pid=321, wait=lambda timeout: 0)
    with pytest.raises(ISOLATION.NetworkIsolationError, match="installer_cleanup_unconfirmed"):
        ISOLATION._stop_installer_group(process)


def test_unsupported_timeout_and_empty_tool_output_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    tools = {"timeout": "/usr/bin/timeout", "unshare": "/usr/bin/unshare"}
    monkeypatch.setattr(
        ISOLATION.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=b""),
    )
    with pytest.raises(ISOLATION.NetworkIsolationError, match="tools_unavailable"):
        ISOLATION._tool_versions(tools, {})
    monkeypatch.setattr(
        ISOLATION.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=b"unexpected implementation"),
    )
    with pytest.raises(ISOLATION.NetworkIsolationError, match="tools_unsupported"):
        ISOLATION._tool_versions(tools, {})
