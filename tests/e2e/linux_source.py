"""Exercise dev.sh itself with private workspaces and only owned processes."""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from app.core.runtime_contract import API_CONTRACT_VERSION, RUNTIME_CAPABILITIES
from app.storage.metadata import SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[2]


def reserve() -> socket.socket:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    return listener


def read_url(port: int, path: str) -> str:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=2) as response:
        return response.read().decode("utf-8")


def processes() -> dict[int, tuple[int, str, str]]:
    result = {}
    for path in Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = path.read_text().rpartition(") ")[2].split()
            result[int(path.parent.name)] = (int(fields[1]), fields[19], fields[0])
        except (FileNotFoundError, ProcessLookupError):
            continue
    return result


def owned_processes(pid: int) -> dict[int, tuple[int, str, str]]:
    current = processes()
    owned = {pid: current[pid]} if pid in current else {}
    while True:
        descendants = {key: value for key, value in current.items() if value[0] in owned}
        if descendants.keys() <= owned.keys():
            return owned
        owned.update(descendants)


def listener_addresses(port: int) -> set[str]:
    return {
        fields[1].split(":")[0]
        for line in Path("/proc/net/tcp").read_text().splitlines()[1:]
        if (fields := line.split())[3] == "0A"
        and int(fields[1].split(":")[1], 16) == port
    }


def stop_owned(runner: subprocess.Popen, owned: dict) -> None:
    if runner.poll() is None:
        runner.send_signal(signal.SIGTERM)
    try:
        runner.wait(timeout=20)
    except subprocess.TimeoutExpired:
        current = processes()
        for pid, identity in owned.items():
            if pid in current and current[pid][1] == identity[1]:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        runner.wait(timeout=5)
        raise AssertionError("Source runner did not gracefully stop owned children") from None
    current = processes()
    assert not any(
        pid in current and current[pid][1] == identity[1] and current[pid][2] != "Z"
        for pid, identity in owned.items()
    ), "Owned development child remained alive after SIGTERM"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostics-root", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("This source-runner smoke requires Linux")
    args.diagnostics_root.mkdir(parents=True, exist_ok=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    with tempfile.TemporaryDirectory(prefix="statistical-twin-source-smoke-") as temporary:
        env = dict(os.environ, DATALAB_WORKSPACE_ROOT=str(Path(temporary) / "workspace"))
        command = ["bash", str(ROOT / "scripts/dev.sh")]
        with reserve() as backend, reserve() as frontend:
            ports = [backend.getsockname()[1], frontend.getsockname()[1]]
            options = ["--backend-port", str(ports[0]), "--frontend-port", str(ports[1])]
            backend.close()
            refused = subprocess.run(command + options, cwd=ROOT, env=env, capture_output=True, text=True, timeout=15)
            assert refused.returncode != 0 and "already in use" in refused.stderr
            assert listener_addresses(ports[1]) == {"0100007F"}
            assert not listener_addresses(ports[0])
        for lan in (False, True):
            with reserve() as backend, reserve() as frontend:
                ports = [backend.getsockname()[1], frontend.getsockname()[1]]
            options = ["--backend-port", str(ports[0]), "--frontend-port", str(ports[1])]
            if lan:
                options.append("--lan")
            with (args.diagnostics_root / f"source-{'lan' if lan else 'loopback'}.log").open("w", encoding="utf-8") as log:
                runner = subprocess.Popen(command + options, cwd=ROOT, env=env, stdout=log, stderr=log, start_new_session=True)
                try:
                    deadline = time.monotonic() + 70
                    while True:
                        assert runner.poll() is None, "Source runner exited before readiness"
                        try:
                            infos = [json.loads(read_url(port, "/api/v1/runtime-info")) for port in ports]
                            break
                        except (urllib.error.URLError, TimeoutError):
                            assert time.monotonic() < deadline, "Source runner readiness timed out"
                            time.sleep(0.3)
                    for info in infos:
                        assert info["service"] == "datalab-studio-api" and info["build_commit"] == head
                        assert info["api_contract_version"] == API_CONTRACT_VERSION
                        assert info["metadata_schema_version"] == SCHEMA_VERSION
                        assert all(info["capabilities"].get(key) is value for key, value in RUNTIME_CAPABILITIES.items())
                    assert 'id="root"' in read_url(ports[1], "/home")
                    assert head in read_url(ports[1], "/src/runtimeCompatibility.ts")
                    assert listener_addresses(ports[0]) == {"0100007F"}
                    assert listener_addresses(ports[1]) == {"00000000" if lan else "0100007F"}
                finally:
                    stop_owned(runner, owned_processes(runner.pid))
                assert runner.returncode == 0
                assert all(not listener_addresses(port) for port in ports)
    print(json.dumps({"source_commit": head, "status": "passed", "modes": ["loopback", "lan"], "port_collision_refused": True, "owned_sigterm_cleanup": True}))


if __name__ == "__main__":
    main()
