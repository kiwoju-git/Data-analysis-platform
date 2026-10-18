"""CI-only, fail-closed Linux network-namespace proof for release installation.

This is validation tooling, not a dependency of the distributed installer.
No application modules or third-party packages are imported.
"""

from __future__ import annotations

import contextlib
import json
import os
import platform
import select
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

INSTALL_SECONDS = 540
NAMESPACE_SECONDS = 600
KILL_SECONDS = 5
PARENT_SECONDS = NAMESPACE_SECONDS + KILL_SECONDS + 20
MAX_JSON_BYTES = 32_768
MAX_LOG_BYTES = 8 * 1024 * 1024
MAX_INSTALLED_ENTRIES = 250_000
HOST_PATH = "/usr/bin:/bin"


class NetworkIsolationError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise NetworkIsolationError(code)


def _read_json(path: Path) -> dict[str, Any]:
    if path.stat().st_size > MAX_JSON_BYTES:
        _fail("network_isolation_evidence_invalid")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as error:
        raise NetworkIsolationError("network_isolation_evidence_invalid") from error
    if not isinstance(value, dict):
        _fail("network_isolation_evidence_invalid")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if len(payload.encode("utf-8")) > MAX_JSON_BYTES:
        _fail("network_isolation_evidence_invalid")
    created = False
    try:
        with path.open("x", encoding="utf-8", newline="\n") as target:
            created = True
            target.write(payload)
            target.flush()
            os.fsync(target.fileno())
    except BaseException:
        if created:
            path.unlink()
        raise


def _safe_environment(env: dict[str, str], private: Path) -> dict[str, str]:
    # No ambient HOME, proxies, Python hooks, shell hooks, tokens or loader paths.
    python = env.get("PYTHON", "")
    path = env.get("PATH", "")
    if not python or not Path(python).is_absolute() or not Path(python).is_file():
        _fail("network_isolation_python_invalid")
    if not path or any(not Path(part).is_absolute() for part in path.split(os.pathsep)):
        _fail("network_isolation_path_invalid")
    if any("\0" in part or "\n" in part or "\r" in part for part in (python, path)):
        _fail("network_isolation_environment_invalid")
    return {
        "PATH": path,
        "PYTHON": python,
        "HOME": str(private / "home"),
        "TMPDIR": str(private / "tmp"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_CONFIG_FILE": "/dev/null",
        "PYTHONDONTWRITEBYTECODE": "1",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
    }


def _namespace_argv(
    tools: dict[str, str], config: Path, uid: int, gid: int, python: str
) -> list[str]:
    return [
        tools["sudo"],
        "-n",
        "--",
        tools["timeout"],
        f"--kill-after={KILL_SECONDS}s",
        f"{NAMESPACE_SECONDS}s",
        tools["unshare"],
        "--net",
        "--setgid",
        str(gid),
        "--setuid",
        str(uid),
        "--",
        python,
        "-I",
        "-S",
        "-B",
        str(Path(__file__).resolve()),
        "child",
        str(config),
    ]


def _tools() -> dict[str, str]:
    result = {}
    for name in ("sudo", "timeout", "unshare"):
        executable = shutil.which(name, path=HOST_PATH)
        if executable is None or not Path(executable).is_absolute():
            _fail("network_isolation_tools_unavailable")
        result[name] = executable
    return result


def _tool_versions(tools: dict[str, str], env: dict[str, str]) -> dict[str, str]:
    versions = {}
    for name, executable in tools.items():
        try:
            result = subprocess.run(
                [executable, "--version"],
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise NetworkIsolationError(
                "network_isolation_tools_unavailable"
            ) from error
        if result.returncode != 0 or len(result.stdout) > MAX_JSON_BYTES:
            _fail("network_isolation_tools_unavailable")
        lines = result.stdout.decode("utf-8", errors="replace").splitlines()
        if not lines:
            _fail("network_isolation_tools_unavailable")
        versions[name] = lines[0]
    if (
        "GNU coreutils" not in versions["timeout"]
        or "util-linux" not in versions["unshare"]
    ):
        _fail("network_isolation_tools_unsupported")
    return versions


def _connects(family: int, port: int) -> bool:
    address = "127.0.0.1" if family == socket.AF_INET else "::1"
    with socket.socket(family, socket.SOCK_STREAM) as connection:
        connection.settimeout(1)
        return connection.connect_ex((address, port)) == 0


@contextlib.contextmanager
def _host_controls():
    with contextlib.ExitStack() as stack:
        sockets = []
        for family, address in (
            (socket.AF_INET, "127.0.0.1"),
            (socket.AF_INET6, "::1"),
        ):
            listener = stack.enter_context(socket.socket(family, socket.SOCK_STREAM))
            if family == socket.AF_INET6:
                listener.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            listener.bind((address, 0))
            listener.listen(8)
            sockets.append(listener)
        stop = threading.Event()

        def accept_controls() -> None:
            while not stop.is_set():
                ready, _, _ = select.select(sockets, [], [], 0.1)
                for listener in ready:
                    connection, _ = listener.accept()
                    connection.close()

        thread = threading.Thread(target=accept_controls, daemon=True)
        thread.start()
        try:
            yield {
                "ipv4": sockets[0].getsockname()[1],
                "ipv6": sockets[1].getsockname()[1],
            }
        finally:
            stop.set()
            thread.join(timeout=2)
            if thread.is_alive():
                _fail("network_isolation_control_cleanup_failed")


def _host_proof(ports: dict[str, int]) -> dict[str, bool]:
    proof = {
        "ipv4_reachable": _connects(socket.AF_INET, ports["ipv4"]),
        "ipv6_reachable": _connects(socket.AF_INET6, ports["ipv6"]),
    }
    if not all(proof.values()):
        _fail("network_isolation_control_unreachable")
    return proof


def _usable_routes(ipv4: str, ipv6: str) -> bool:
    for line in ipv4.splitlines()[1:]:
        fields = line.split()
        if len(fields) != 11:
            _fail("network_isolation_routes_invalid")
        flags = int(fields[3], 16)
        if flags & 1 and not flags & 0x200:
            return True
    for line in ipv6.splitlines():
        fields = line.split()
        if len(fields) != 10:
            _fail("network_isolation_routes_invalid")
        flags = int(fields[8], 16)
        if flags & 1 and not flags & 0x200:
            return True
    return False


def _socket_fds() -> list[int]:
    result = []
    for path in Path("/proc/self/fd").iterdir():
        try:
            target = os.readlink(path)
        except FileNotFoundError:
            continue  # The directory enumeration's own descriptor is already closed.
        if target.startswith("socket:"):
            result.append(int(path.name))
    return result


def _probe(config: dict[str, Any]) -> dict[str, Any]:
    uid, gid = os.getuid(), os.getgid()
    groups = os.getgroups()
    namespace = os.readlink("/proc/self/ns/net")
    interfaces = sorted(name for _, name in socket.if_nameindex())
    inherited = _socket_fds()
    routes = _usable_routes(
        Path("/proc/self/net/route").read_text(encoding="ascii"),
        Path("/proc/self/net/ipv6_route").read_text(encoding="ascii"),
    )
    proof = {
        "uid": uid,
        "gid": gid,
        "effective_uid": os.geteuid(),
        "effective_gid": os.getegid(),
        "supplementary_groups": groups,
        "namespace": namespace,
        "interfaces": interfaces,
        "inherited_socket_fds": inherited,
        "usable_routes": routes,
        "ipv4_blocked": not _connects(socket.AF_INET, config["ports"]["ipv4"]),
        "ipv6_blocked": not _connects(socket.AF_INET6, config["ports"]["ipv6"]),
    }
    _validate_probe(proof, config)
    return proof


def _validate_probe(proof: dict[str, Any], config: dict[str, Any]) -> None:
    if (
        any(
            proof.get(key) != config[expected]
            for key, expected in (
                ("uid", "uid"),
                ("gid", "gid"),
                ("effective_uid", "uid"),
                ("effective_gid", "gid"),
            )
        )
        or config["uid"] <= 0
        or config["gid"] <= 0
    ):
        _fail("network_isolation_identity_invalid")
    if (
        not isinstance(proof.get("supplementary_groups"), list)
        or 0 in proof["supplementary_groups"]
    ):
        _fail("network_isolation_identity_invalid")
    namespace = proof.get("namespace")
    if (
        not isinstance(namespace, str)
        or not namespace.startswith("net:[")
        or namespace == config["host_namespace"]
    ):
        _fail("network_isolation_namespace_invalid")
    if proof.get("interfaces") != ["lo"] or proof.get("usable_routes") is not False:
        _fail("network_isolation_network_available")
    if proof.get("inherited_socket_fds") != []:
        _fail("network_isolation_inherited_socket")
    if proof.get("ipv4_blocked") is not True or proof.get("ipv6_blocked") is not True:
        _fail("network_isolation_control_accessible")


def _verify_ownership(root: Path, uid: int, gid: int) -> int:
    count = 0
    deadline = time.monotonic() + 20
    for directory, subdirectories, files in os.walk(root, followlinks=False):
        for name in [".", *subdirectories, *files]:
            count += 1
            if count > MAX_INSTALLED_ENTRIES or time.monotonic() > deadline:
                _fail("network_isolation_ownership_budget_exceeded")
            info = (Path(directory) / name).lstat()
            if info.st_uid != uid or info.st_gid != gid:
                _fail("network_isolation_install_owner_invalid")
    return count


def _stop_installer_group(process: subprocess.Popen) -> None:
    """Clean only the original runner's process group created for this install."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + KILL_SECONDS
    while time.monotonic() < deadline:
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=KILL_SECONDS)
    deadline = time.monotonic() + KILL_SECONDS
    while time.monotonic() < deadline:
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    _fail("network_isolation_installer_cleanup_unconfirmed")


def _install(config: dict[str, Any]) -> int:
    process = subprocess.Popen(
        [
            config["timeout"],
            f"--kill-after={KILL_SECONDS}s",
            f"{INSTALL_SECONDS}s",
            str(Path(config["root"]) / "install.sh"),
        ],
        cwd=config["root"],
        env=config["env"],
        stdin=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=True,
    )
    try:
        return process.wait(timeout=INSTALL_SECONDS + KILL_SECONDS + 10)
    finally:
        # Includes installer descendants left behind even after a nominal exit 0.
        _stop_installer_group(process)


def _child(config_path: Path) -> None:
    config = _read_json(config_path)
    env = config["env"]
    os.environ.clear()
    os.environ.update(env)
    before = _probe(config)
    grandchild = subprocess.run(
        [
            env["PYTHON"],
            "-I",
            "-S",
            "-B",
            str(Path(__file__).resolve()),
            "probe",
            str(config_path),
        ],
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
        close_fds=True,
    )
    if grandchild.returncode != 0 or len(grandchild.stdout) > MAX_JSON_BYTES:
        _fail("network_isolation_grandchild_failed")
    try:
        inherited = json.loads(grandchild.stdout)
    except (ValueError, UnicodeError) as error:
        raise NetworkIsolationError("network_isolation_grandchild_failed") from error
    if not isinstance(inherited, dict):
        _fail("network_isolation_grandchild_failed")
    _validate_probe(inherited, config)
    if inherited["namespace"] != before["namespace"]:
        _fail("network_isolation_grandchild_failed")
    # An unprivileged watchdog also owns the installer descendants. It expires
    # before the privileged outer watchdog, leaving time for evidence/cleanup.
    returncode = _install(config)
    if returncode != 0:
        _fail("network_isolation_installer_failed")
    after = _probe(config)
    if after["namespace"] != before["namespace"]:
        _fail("network_isolation_namespace_changed")
    entries = _verify_ownership(Path(config["root"]), config["uid"], config["gid"])
    _write_json(
        Path(config["child_evidence"]),
        {
            "before": before,
            "grandchild": inherited,
            "after": after,
            "install_exit_code": returncode,
            "owned_entries_checked": entries,
        },
    )


def _run_namespace(argv: list[str], env: dict[str, str], log_path: Path) -> None:
    started = time.monotonic()
    with log_path.open("xb") as log:
        process = subprocess.Popen(
            argv,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            close_fds=True,
            start_new_session=True,
        )
        total = 0
        reader_failed = []

        def drain() -> None:
            nonlocal total
            try:
                if process.stdout is None:
                    _fail("network_isolation_log_unavailable")
                while block := process.stdout.read(8192):
                    remaining = max(0, MAX_LOG_BYTES - total)
                    log.write(block[:remaining])
                    total += len(block)
            except (OSError, NetworkIsolationError) as error:
                reader_failed.append(error)

        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        try:
            returncode = process.wait(timeout=PARENT_SECONDS)
        except BaseException:
            # sudo/timeout may still be privileged: do not pretend the runner
            # can kill them. Their fixed watchdog remains the authoritative cap.
            remaining = max(1, PARENT_SECONDS - (time.monotonic() - started))
            try:
                process.wait(timeout=remaining)
            except subprocess.TimeoutExpired as error:
                raise NetworkIsolationError(
                    "network_isolation_cleanup_unconfirmed"
                ) from error
            raise
        finally:
            reader.join(timeout=5)
            if process.stdout is not None and not reader.is_alive():
                process.stdout.close()
        if reader.is_alive():
            _fail("network_isolation_descendant_cleanup_unconfirmed")
        if reader_failed or total > MAX_LOG_BYTES:
            _fail("network_isolation_log_budget_exceeded")
        if returncode != 0:
            _fail("network_isolation_child_failed")


def _validate_evidence(child: dict[str, Any], config: dict[str, Any]) -> None:
    namespaces = set()
    for phase in ("before", "grandchild", "after"):
        proof = child.get(phase)
        if not isinstance(proof, dict):
            _fail("network_isolation_evidence_invalid")
        _validate_probe(proof, config)
        namespaces.add(proof["namespace"])
    if len(namespaces) != 1:
        _fail("network_isolation_namespace_changed")
    if (
        type(child.get("install_exit_code")) is not int
        or child["install_exit_code"] != 0
    ):
        _fail("network_isolation_installer_failed")
    entries = child.get("owned_entries_checked")
    if type(entries) is not int or not 1 <= entries <= MAX_INSTALLED_ENTRIES:
        _fail("network_isolation_evidence_invalid")


def run_network_blocked_install(
    root: Path,
    env: dict[str, str],
    log_path: Path,
    evidence_path: Path,
) -> dict[str, object]:
    """Install the verified extracted archive, or fail without a success proof.

    Requires native Linux CPython 3.12 and passwordless CI sudo for unshare.
    The product installer itself always runs as the original nonroot runner.
    """
    if platform.system() != "Linux" or sys.version_info[:2] != (3, 12):
        _fail("network_isolation_platform_unsupported")
    uid, gid = os.getuid(), os.getgid()
    if uid <= 0 or gid <= 0 or os.geteuid() != uid or os.getegid() != gid:
        _fail("network_isolation_runner_invalid")
    root = root.resolve(strict=True)
    if not root.is_dir() or not stat.S_ISREG((root / "install.sh").lstat().st_mode):
        _fail("network_isolation_release_invalid")
    for path in (log_path, evidence_path):
        if path.exists() or path.is_symlink() or path.resolve().is_relative_to(root):
            _fail("network_isolation_output_invalid")
        path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.resolve() == evidence_path.resolve():
        _fail("network_isolation_output_invalid")
    started = time.monotonic()
    tools = _tools()
    with tempfile.TemporaryDirectory(
        prefix="network-proof-", dir=evidence_path.parent
    ) as temporary:
        private = Path(temporary)
        private.chmod(0o700)
        (private / "home").mkdir()
        (private / "tmp").mkdir()
        installer_env = _safe_environment(env, private)
        host_env = dict(installer_env, PATH=HOST_PATH)
        versions = _tool_versions(tools, host_env)
        try:
            check_python = subprocess.run(
                [
                    installer_env["PYTHON"],
                    "-I",
                    "-S",
                    "-B",
                    "-c",
                    "import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 2)",
                ],
                env=host_env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                check=False,
            )
            if check_python.returncode != 0:
                _fail("network_isolation_python_unavailable")
            with _host_controls() as ports:
                before = _host_proof(ports)
                config = {
                    "uid": uid,
                    "gid": gid,
                    "root": str(root),
                    "env": installer_env,
                    "host_namespace": os.readlink("/proc/self/ns/net"),
                    "ports": ports,
                    "child_evidence": str(private / "child.json"),
                    "timeout": tools["timeout"],
                }
                config_path = private / "config.json"
                _write_json(config_path, config)
                _run_namespace(
                    _namespace_argv(
                        tools, config_path, uid, gid, installer_env["PYTHON"]
                    ),
                    host_env,
                    log_path,
                )
                after = _host_proof(ports)
                child = _read_json(private / "child.json")
                _validate_evidence(child, config)
                evidence: dict[str, object] = {
                    "schema_version": 1,
                    "status": "passed",
                    "network_blocked_installation": True,
                    "platform": platform.platform(),
                    "python": platform.python_version(),
                    "tools": versions,
                    "runner_uid": uid,
                    "runner_gid": gid,
                    "host_namespace": config["host_namespace"],
                    "host_before": before,
                    "host_after": after,
                    **child,
                    "namespace_timeout_seconds": NAMESPACE_SECONDS,
                    "installer_timeout_seconds": INSTALL_SECONDS,
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                }
                _write_json(evidence_path, evidence)
                return evidence
        except NetworkIsolationError:
            raise
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            raise NetworkIsolationError(
                "network_isolation_verification_failed"
            ) from error


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in {"child", "probe"}:
        print("This helper is invoked by verify_linux_release.py.", file=sys.stderr)
        return 2
    try:
        if sys.argv[1] == "child":
            _child(Path(sys.argv[2]))
        else:
            print(json.dumps(_probe(_read_json(Path(sys.argv[2]))), allow_nan=False))
        return 0
    except (
        OSError,
        ValueError,
        KeyError,
        subprocess.SubprocessError,
        NetworkIsolationError,
    ) as error:
        print(
            getattr(error, "code", "network_isolation_verification_failed"),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
