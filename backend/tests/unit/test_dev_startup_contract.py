import os
import re
import shutil
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
    assert "Get-DevRepositoryBuildId" in dev_text
    assert "$env:DATALAB_GIT_COMMIT = $RepositoryBuildId" in dev_text
    assert "$env:VITE_GIT_COMMIT = $RepositoryBuildId" in dev_text
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
        f"Get-DevRepositoryBuildId -RepoRoot '{repo_root}'"
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


def test_archive_source_fingerprint_is_path_independent_and_content_sensitive(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    first = tmp_path / "첫 번째 폴더"
    second = tmp_path / "second folder"
    _write_archive_source(first)
    shutil.copytree(first, second)

    first_id = _get_build_id(repo_root, first)
    second_id = _get_build_id(repo_root, second)

    assert re.fullmatch(r"archive-sha256-[0-9a-f]{64}", first_id)
    assert second_id == first_id

    (second / "frontend/src/main.tsx").write_text(
        "export const build = 'changed';\n",
        encoding="utf-8",
    )
    changed_id = _get_build_id(repo_root, second)
    assert changed_id != first_id


def test_archive_source_fingerprint_ignores_generated_and_workspace_files(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    source = tmp_path / "archive"
    _write_archive_source(source)
    original_id = _get_build_id(repo_root, source)

    generated_files = {
        ".venv/ignored.txt": "venv",
        "frontend/node_modules/pkg/index.js": "module",
        "frontend/dist/app.js": "bundle",
        ".tmp/runtime.log": "temporary",
        "local-workspace/metadata.sqlite3": "database",
    }
    for relative_path, content in generated_files.items():
        path = source / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    assert _get_build_id(repo_root, source) == original_id


def test_detached_head_returns_the_exact_git_commit(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    source = tmp_path / "detached repository"
    _write_archive_source(source)
    for command in (
        ["git", "init"],
        ["git", "config", "user.email", "test@example.invalid"],
        ["git", "config", "user.name", "DataLab Test"],
        ["git", "add", "."],
        ["git", "commit", "-m", "fixture"],
        ["git", "checkout", "--detach"],
    ):
        subprocess.run(
            command,
            cwd=source,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    expected = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()

    assert _get_build_id(repo_root, source) == expected


def test_missing_git_and_ambiguous_head_use_archive_fingerprint_without_git_error(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    source = tmp_path / "broken git archive"
    _write_archive_source(source)
    (source / ".git").mkdir()

    result = _run_build_id(repo_root, source, clear_path=True)

    assert result.returncode == 0
    assert re.fullmatch(r"archive-sha256-[0-9a-f]{64}", result.stdout.strip())
    assert "fatal:" not in result.stdout
    assert "NativeCommandError" not in result.stdout

    result_with_git = _run_build_id(repo_root, source)
    assert result_with_git.returncode == 0
    assert re.fullmatch(
        r"archive-sha256-[0-9a-f]{64}",
        result_with_git.stdout.strip(),
    )
    assert "fatal:" not in result_with_git.stdout
    assert "NativeCommandError" not in result_with_git.stdout


def _write_archive_source(root: Path) -> None:
    files = {
        "backend/app/main.py": "APP = 'datalab'\n",
        "backend/pyproject.toml": "[project]\nname = 'datalab'\n",
        "frontend/src/main.tsx": "export const build = 'initial';\n",
        "frontend/package.json": '{"name":"datalab"}\n',
        "frontend/package-lock.json": '{"lockfileVersion":3}\n',
        "frontend/index.html": "<div id=\"root\"></div>\n",
        "frontend/tsconfig.json": '{"compilerOptions":{"strict":true}}\n',
        "frontend/vite.config.ts": "export default {};\n",
        "scripts/dev.ps1": "Write-Host 'dev'\n",
        ".gitattributes": "* text=auto\n",
    }
    for relative_path, content in files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _get_build_id(helper_repo_root: Path, source_root: Path) -> str:
    result = _run_build_id(helper_repo_root, source_root)
    assert result.returncode == 0, result.stdout
    return result.stdout.strip()


def _run_build_id(
    helper_repo_root: Path,
    source_root: Path,
    *,
    clear_path: bool = False,
) -> subprocess.CompletedProcess[str]:
    helper = helper_repo_root / "scripts/dev_runtime_helpers.ps1"
    path_setup = "$env:PATH = '';" if clear_path else ""
    command = (
        f". '{helper}'; {path_setup} "
        "Get-DevRepositoryBuildId -RepoRoot $env:TEST_REPO_ROOT"
    )
    environment = os.environ.copy()
    environment["TEST_REPO_ROOT"] = str(source_root)
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        cwd=helper_repo_root,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )


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
