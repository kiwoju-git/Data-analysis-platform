import os
import socket
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.name != "nt", reason="PowerShell dev entrypoint is Windows-only")


class _OldBackendHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        body = b'{"detail":"Not Found"}'
        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


def test_dev_rejects_occupied_old_backend_without_stopping_owner() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    server = ThreadingHTTPServer(("127.0.0.1", 0), _OldBackendHandler)
    port = int(server.server_address[1])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = _run_dev(repo_root, "-BackendOnly", "-BackendPort", str(port))

        assert result.returncode != 0
        assert f"Backend port {port} is already in use" in result.stdout
        assert "runtime-info unavailable" in result.stdout
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            pass
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_frontend_only_requires_matching_backend_before_starting_vite() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = int(probe.getsockname()[1])

    result = _run_dev(
        repo_root,
        "-FrontendOnly",
        "-BackendPort",
        str(port),
        "-FrontendPort",
        str(port + 1),
    )

    assert result.returncode != 0
    assert f"No backend is listening on port {port}" in result.stdout
    assert "VITE" not in result.stdout


def test_dev_and_diagnostics_keep_strict_ports_and_runtime_contract_checks() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    dev_text = (repo_root / "scripts/dev.ps1").read_text(encoding="utf-8")
    helper_text = (repo_root / "scripts/dev_runtime_helpers.ps1").read_text(encoding="utf-8")
    diagnostics_text = (repo_root / "scripts/diagnose-dev.ps1").read_text(encoding="utf-8")

    assert "--strictPort" in dev_text
    assert "Get-DevPortOwner" in dev_text
    assert "Get-DevRuntimeInfo" in dev_text
    assert "Receive-Job" in dev_text
    assert "Stop-Process" not in dev_text
    assert "$script:ExpectedApiContractVersion = 2" in helper_text
    assert '"dataset_version_metadata"' in helper_text
    assert '"bayesian_optimization"' in helper_text
    assert "/api/v1/runtime-info" in diagnostics_text
    assert "/api/v1/analysis-methods" in diagnostics_text


def test_dev_runtime_helper_returns_the_repository_commit() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    expected = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()
    command = (
        f". '{repo_root / 'scripts/dev_runtime_helpers.ps1'}'; "
        f"Get-DevRepositoryCommit -RepoRoot '{repo_root}'"
    )

    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == expected


def _run_dev(repo_root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(repo_root / "scripts/dev.ps1"),
            *arguments,
        ],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
