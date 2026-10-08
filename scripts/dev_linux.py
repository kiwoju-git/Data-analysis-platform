"""Linux source runner: own process groups, explicit LAN opt-in, verified identity."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


def source_files(root: Path) -> list[str]:
    ignored = re.compile(
        r"(^|/)(__pycache__|node_modules|dist|logs?|\.tmp|test-results|playwright-report|\.(pytest_cache|mypy_cache|ruff_cache))(/|$)|(~|\.bak|\.swp|\.tmp|\.log)$"
    )
    paths = {
        path.relative_to(root).as_posix()
        for relative in ("backend/app", "frontend/src", "scripts")
        for path in (root / relative).rglob("*")
        if path.is_file()
        and not path.is_symlink()
        and not ignored.search(path.relative_to(root).as_posix())
    }
    for relative in (
        "backend/pyproject.toml",
        "frontend/package.json",
        "frontend/package-lock.json",
        "frontend/index.html",
        "frontend/devNetwork.ts",
        ".gitattributes",
    ):
        if (root / relative).is_file():
            paths.add(relative)
    for pattern in (
        "backend/*.lock",
        "backend/requirements*.txt",
        "frontend/tsconfig*.json",
        "frontend/vite.config.*",
    ):
        paths.update(
            path.relative_to(root).as_posix()
            for path in root.glob(pattern)
            if path.is_file()
        )
    return sorted(paths)


def archive_fingerprint(root: Path) -> str:
    paths = source_files(root)
    if not paths:
        raise ValueError("No runtime source files found for archive fingerprint")
    aggregate = hashlib.sha256()
    for relative in paths:
        checksum = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        aggregate.update(f"{relative}\0{checksum}\n".encode("utf-8"))
    return "archive-sha256-" + aggregate.hexdigest()


def source_identity(root: Path) -> str:
    if (root / ".git").exists():
        try:
            top_level = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return archive_fingerprint(root)
        if (
            top_level.returncode == 0
            and Path(top_level.stdout.strip()).resolve() == root.resolve()
            and result.returncode == 0
        ) and re.fullmatch(r"[a-f0-9]{40}", result.stdout.strip()):
            return result.stdout.strip()
    return archive_fingerprint(root)


def verify_runtime(url: str, identity: str) -> None:
    from app.core.runtime_contract import API_CONTRACT_VERSION, RUNTIME_CAPABILITIES
    from app.storage.metadata import SCHEMA_VERSION

    with urllib.request.urlopen(url + "/api/v1/runtime-info", timeout=2) as response:
        info = json.load(response)
    if (
        info.get("service") != "datalab-studio-api"
        or info.get("build_commit") != identity
        or info.get("api_contract_version") != API_CONTRACT_VERSION
        or info.get("metadata_schema_version") != SCHEMA_VERSION
        or any(
            info.get("capabilities", {}).get(key) is not value
            for key, value in RUNTIME_CAPABILITIES.items()
        )
    ):
        raise ValueError("Frontend/backend runtime identity or capabilities mismatch")


def stop_owned(processes: list[subprocess.Popen[bytes]]) -> None:
    def send(group: int, signum: int) -> None:
        try:
            os.killpg(group, signum)
        except ProcessLookupError:
            pass

    # The process group can outlive its leader (for example Vite's esbuild child).
    for process in processes:
        send(process.pid, signal.SIGTERM)
    deadline = time.monotonic() + 8
    for process in processes:
        try:
            process.wait(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            send(process.pid, signal.SIGKILL)
            process.wait()
    for process in processes:
        send(process.pid, signal.SIGKILL)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Statistical Twin Linux source development"
    )
    parser.add_argument(
        "--lan",
        action="store_true",
        help="Expose only the guarded Vite frontend on the trusted LAN",
    )
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--frontend-port", type=int, default=8600)
    parser.add_argument("--open-browser", action="store_true")
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("Use scripts/dev.ps1 on Windows")
    root = Path(__file__).resolve().parents[1]
    if args.backend_port == args.frontend_port or any(
        not 1024 <= port <= 65535 for port in (args.backend_port, args.frontend_port)
    ):
        parser.error("Choose distinct unprivileged ports")
    for host, port in (
        ("127.0.0.1", args.backend_port),
        ("0.0.0.0" if args.lan else "127.0.0.1", args.frontend_port),
    ):
        try:
            with socket.socket() as probe:
                probe.bind((host, port))
        except OSError:
            parser.error(f"Port {port} is already in use; no process was stopped")
    identity = source_identity(root)
    env = dict(
        os.environ,
        DATALAB_GIT_COMMIT=identity,
        VITE_GIT_COMMIT=identity,
        VITE_API_BASE_URL="/",
        DATALAB_DEV_API_TARGET=f"http://127.0.0.1:{args.backend_port}",
        DATALAB_BIND_HOST="127.0.0.1",
        DATALAB_BIND_PORT=str(args.backend_port),
    )
    env.pop("DATALAB_FRONTEND_DIST", None)
    for name in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        env[name] = "1"
    processes: list[subprocess.Popen[bytes]] = []
    stopping = False

    def requested_stop(_signal: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, requested_stop)
    signal.signal(signal.SIGTERM, requested_stop)
    frontend = f"http://127.0.0.1:{args.frontend_port}"
    try:
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.backend_port),
                ],
                cwd=root,
                env=env,
                start_new_session=True,
            )
        )
        processes.append(
            subprocess.Popen(
                [
                    "node",
                    str(root / "frontend/node_modules/vite/bin/vite.js"),
                    "--host",
                    "0.0.0.0" if args.lan else "127.0.0.1",
                    "--port",
                    str(args.frontend_port),
                    "--strictPort",
                ],
                cwd=root / "frontend",
                env=env,
                start_new_session=True,
            )
        )
        deadline = time.monotonic() + 60
        while not stopping:
            if any(process.poll() is not None for process in processes):
                raise RuntimeError("A development server exited during startup")
            try:
                verify_runtime(f"http://127.0.0.1:{args.backend_port}", identity)
                verify_runtime(frontend, identity)
                break
            except (urllib.error.URLError, TimeoutError):
                if time.monotonic() >= deadline:
                    raise RuntimeError("Development server startup timed out") from None
                time.sleep(0.3)
        if not stopping:
            print(f"Ready: {frontend}/home ({identity})", flush=True)
            if args.lan:
                print(
                    "Trusted LAN only: shared single-user workspace, no authentication/RBAC/TLS. No firewall rules were changed.",
                    flush=True,
                )
            if args.open_browser:
                try:
                    webbrowser.open(frontend + "/home")
                except webbrowser.Error:
                    print("Browser unavailable; open the displayed URL manually.")
        while not stopping:
            if any(process.poll() is not None for process in processes):
                raise RuntimeError("A development server exited")
            time.sleep(0.3)
    finally:
        stop_owned(processes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
