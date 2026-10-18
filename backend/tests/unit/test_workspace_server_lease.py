"""Real loopback servers must not share a workspace merely by changing ports."""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


def _unused_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def _start(root: Path, port: int, log):
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("DATALAB_")
    }
    environment.update(
        {
            "DATALAB_WORKSPACE_ROOT": str(root),
            "DATALAB_BIND_HOST": "127.0.0.1",
            "DATALAB_BIND_PORT": str(port),
            "DATALAB_GIT_COMMIT": "synthetic-workspace-lease-test",
            "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
            "PYTHONUNBUFFERED": "1",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
        }
    )
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
        ],
        cwd=root.parent,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )


def _ready(process, port: int) -> None:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        assert process.poll() is None, f"Owned test server exited {process.returncode}"
        try:
            with urlopen(f"http://127.0.0.1:{port}/api/v1/runtime-info", timeout=1) as response:
                payload = json.load(response)
                assert payload["build_commit"] == "synthetic-workspace-lease-test"
                return
        except (URLError, TimeoutError):
            time.sleep(0.1)
    raise AssertionError("Owned test server did not become ready")


def _stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def test_distinct_ports_reject_shared_workspace_and_allow_distinct_workspace(tmp_path):
    first_port, second_port = _unused_port(), _unused_port()
    while second_port == first_port:
        second_port = _unused_port()
    shared = tmp_path / "shared \ud14c\uc2a4\ud2b8 workspace"
    processes = []
    with (
        (tmp_path / "owner.log").open("wb") as owner_log,
        (tmp_path / "contender.log").open("wb") as contender_log,
        (tmp_path / "independent.log").open("wb") as independent_log,
    ):
        try:
            owner = _start(shared, first_port, owner_log)
            processes.append(owner)
            _ready(owner, first_port)
            contender = _start(shared, second_port, contender_log)
            processes.append(contender)
            assert contender.wait(timeout=90) != 0
            contender_log.flush()
            assert "workspace_in_use" in (tmp_path / "contender.log").read_text(encoding="utf-8")
            _ready(owner, first_port)
            independent = _start(tmp_path / "independent workspace", second_port, independent_log)
            processes.append(independent)
            _ready(independent, second_port)
        finally:
            for process in reversed(processes):
                _stop(process)
