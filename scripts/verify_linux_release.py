"""Verify the completed archive bytes via offline install and black-box application tests."""

from __future__ import annotations

import argparse
import errno
import hashlib
import ipaddress
import json
import os
import platform
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def interface_ipv4() -> str:
    """Select an actual assigned address without contacting an external service."""
    import fcntl

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        for _, name in socket.if_nameindex():
            try:
                result = fcntl.ioctl(probe, 0x8915, struct.pack("256s", name.encode()))
            except OSError as error:
                # An interface may be IPv6-only; other failures must remain visible.
                if error.errno in {errno.EADDRNOTAVAIL, errno.ENODEV}:
                    continue
                raise
            address = ipaddress.IPv4Address(result[20:24])
            if not (
                address.is_loopback or address.is_unspecified or address.is_multicast
            ):
                return str(address)
    raise RuntimeError(
        "LAN archive verification requires a non-loopback IPv4 interface"
    )


def listener_addresses(port: int) -> set[str]:
    return {
        fields[1].split(":")[0]
        for line in Path("/proc/net/tcp").read_text().splitlines()[1:]
        if (fields := line.split())[3] == "0A"
        and int(fields[1].split(":")[1], 16) == port
    }


def assert_interface_isolated(address: str, port: int) -> None:
    with socket.socket() as probe:
        probe.settimeout(2)
        assert (
            probe.connect_ex((address, port)) != 0
        ), "Local-only server accepts LAN connections"


def unpack(archive: Path, destination: Path) -> Path:
    with tarfile.open(archive, "r:gz") as source:
        for member in source.getmembers():
            parts = Path(member.name).parts
            if (
                member.issym()
                or member.islnk()
                or not parts
                or parts[0] != "statistical-twin-linux"
                or ".." in parts
                or member.name.startswith("/")
            ):
                raise ValueError("Unsafe release archive member")
            if not (member.isfile() or member.isdir()):
                raise ValueError("Unexpected special file in release")
        source.extractall(destination, filter="data")
    root = destination / "statistical-twin-linux"
    forbidden = {".git", ".venv", "node_modules", ".env", "workspace", "__pycache__"}
    if any(
        part in forbidden
        for path in root.rglob("*")
        for part in path.relative_to(root).parts
    ):
        raise ValueError("Release contains development or user state")
    if any(
        path.suffix.lower() in {".sqlite", ".sqlite3", ".db"}
        for path in root.rglob("*")
    ):
        raise ValueError("Release contains a database")
    return root


def wait_ready(base: str, process: subprocess.Popen, expected: dict) -> dict:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                "Release server exited during startup; inspect server log"
            )
        try:
            with HTTP.open(base + "/api/v1/runtime-info", timeout=2) as response:
                info = json.load(response)
            assert info["build_commit"] == expected["source_commit"]
            assert info["api_contract_version"] == expected["api_contract_version"]
            assert (
                info["metadata_schema_version"] == expected["metadata_schema_version"]
            )
            assert info["service"] == "datalab-studio-api"
            assert all(
                info.get("capabilities", {}).get(key) is value
                for key, value in expected["required_capabilities"].items()
            )
            return info
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.3)
    raise RuntimeError("Release server startup timed out")


def stop(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        pass
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8600)
    args = parser.parse_args()
    if sys.flags.optimize:
        parser.error("Run release validation without Python optimization")
    if platform.system() != "Linux" or sys.version_info[:2] != (3, 12):
        parser.error("Validate on Linux CPython 3.12")
    archive = args.archive.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    repo = Path(__file__).resolve().parents[1]
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("0.0.0.0", args.port))
    lan_address = interface_ipv4()
    lan_base = f"http://{lan_address}:{args.port}"
    loopback_base = f"http://127.0.0.1:{args.port}"
    with tempfile.TemporaryDirectory(
        prefix="statistical-twin-archive-check-"
    ) as temporary:
        temp = Path(temporary)
        binaries = temp / "runtime-path"
        binaries.mkdir()
        for name in ("bash", "dirname"):
            executable = shutil.which(name)
            if executable is None:
                raise RuntimeError(f"Missing prerequisite: {name}")
            (binaries / name).symlink_to(executable)
        # Installation and server PATH deliberately contain neither Node nor Git.
        env = dict(
            os.environ,
            PATH=str(binaries),
            PYTHON=sys._base_executable,
            PIP_NO_INDEX="1",
            PIP_DISABLE_PIP_VERSION_CHECK="1",
        )
        env.pop("PYTHONPATH", None)
        env.pop("DATALAB_FRONTEND_DIST", None)
        workspace = temp / "external workspace"
        smoke = None
        for index in range(2):
            root = unpack(archive, temp / f"installation-{index}")
            for dependency in ("react", "react-dom", "lucide-react", "noble_hashes"):
                notices = list(
                    (root / "THIRD_PARTY_NOTICES/frontend").glob(f"{dependency}-*")
                )
                assert notices and any(
                    path.name.lower().startswith("license")
                    for directory in notices
                    for path in directory.iterdir()
                ), f"Missing frontend license notice: {dependency}"
            expected = json.loads((root / "BUILD_INFO.json").read_text())
            with (output / f"install-{index}.log").open("wb") as log:
                subprocess.run(
                    [str(root / "install.sh")],
                    cwd=root,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=True,
                )
            assert (
                not workspace.exists() or index == 1
            ), "Installer must not create a workspace"
            command = [str(root / "run.sh"), "--workspace-root", str(workspace)]
            # Omit --port at 8600 to exercise the published launcher default itself.
            if args.port != 8600:
                command.extend(["--port", str(args.port)])
            if index == 1:
                command.append("--local-only")
            base = lan_base if index == 0 else loopback_base
            with (output / f"server-{index}.log").open("wb") as log:
                process = subprocess.Popen(
                    command,
                    cwd=root,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                try:
                    wait_ready(base, process, expected)
                    assert listener_addresses(args.port) == {
                        "00000000" if index == 0 else "0100007F"
                    }, "Release bound a different interface than requested"
                    if index == 0:
                        wait_ready(loopback_base, process, expected)
                        subprocess.run(
                            [
                                sys.executable,
                                str(repo / "tests/e2e/linux_release.py"),
                                "--url",
                                base,
                                "--output",
                                str(output),
                            ],
                            cwd=temp,
                            check=True,
                        )
                        smoke = json.loads(
                            (output / "application-smoke.json").read_text()
                        )
                    else:
                        assert_interface_isolated(lan_address, args.port)
                        assert smoke is not None
                        for analysis in smoke["analyses"]:
                            with HTTP.open(
                                base
                                + f"/api/v1/analysis-runs/{analysis['analysis_id']}/result",
                                timeout=30,
                            ) as response:
                                restored = json.load(response)
                            checksum = hashlib.sha256(
                                json.dumps(restored["result"], sort_keys=True).encode()
                            ).hexdigest()
                            assert checksum == analysis["result_sha256"]
                finally:
                    stop(process)
                assert not listener_addresses(
                    args.port
                ), "Release listener survived shutdown"
        report = {
            "status": "passed",
            "archive": archive.name,
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "source_commit": expected["source_commit"],
            "actual_platform": platform.platform(),
            "python": platform.python_version(),
            "node_and_git_in_install_runtime_path": False,
            "offline_installations": 2,
            "shared_external_workspace_restart_restore": True,
            "default_port_exercised": args.port == 8600,
            "listen_port": args.port,
            "lan_interface_ipv4": lan_address,
            "default_lan_bind": "0.0.0.0",
            "local_only_bind": "127.0.0.1",
            "local_only_interface_connection_rejected": True,
            "company_peer_or_firewall_tested": False,
            "application": smoke,
        }
        (output / "validation-report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    key: report[key]
                    for key in ("status", "archive_sha256", "source_commit")
                }
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
