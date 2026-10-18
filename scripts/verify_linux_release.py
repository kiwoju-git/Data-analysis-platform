"""Verify the completed archive bytes via offline install and black-box application tests."""

from __future__ import annotations

import argparse
import errno
import hashlib
import ipaddress
import json
import os
import platform
import re
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
from pathlib import Path, PurePosixPath

from network_isolated_install import run_network_blocked_install

HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
MAX_ARCHIVE_FILES = 100_000
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    if destination.exists():
        raise ValueError("Release extraction requires a new destination")
    seen: set[str] = set()
    total_bytes = 0
    with tarfile.open(archive, "r:gz") as source:
        members = []
        for member in source:
            name = member.name.rstrip("/")
            parts = PurePosixPath(name).parts
            if (
                member.issym()
                or member.islnk()
                or not parts
                or parts[0] != "statistical-twin-linux"
                or any(part in {"", ".", ".."} for part in name.split("/"))
                or "\\" in name
                or ":" in name
                or "\x00" in name
                or name in seen
                or len(name) > 4096
                or member.size < 0
            ):
                raise ValueError("Unsafe release archive member")
            if not (member.isfile() or member.isdir()):
                raise ValueError("Unexpected special file in release")
            seen.add(name)
            total_bytes += member.size
            members.append(member)
            if len(members) > MAX_ARCHIVE_FILES or total_bytes > MAX_ARCHIVE_BYTES:
                raise ValueError("Release archive exceeds validation limits")
        destination.mkdir(parents=True)
        for member in members:
            target = destination.joinpath(*PurePosixPath(member.name).parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                stream = source.extractfile(member)
                if stream is None:
                    raise ValueError("Release archive file cannot be read")
                with stream, target.open("xb") as output:
                    shutil.copyfileobj(stream, output, 1024 * 1024)
                target.chmod(0o755 if member.mode & 0o111 else 0o644)
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


def bootstrap_identity(root: Path, env: dict[str, str], action: str) -> dict:
    if action not in {"verify-payload", "verify-installed"}:
        raise ValueError("Unsupported identity verification action")
    python = (
        env["PYTHON"] if action == "verify-payload" else str(root / ".venv/bin/python")
    )
    result = subprocess.run(
        [
            python,
            "-I",
            "-S",
            "-B",
            str(root / "release_bootstrap.py"),
            action,
            "--release-root",
            str(root),
        ],
        env=env,
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    evidence = json.loads(result.stdout)
    status = "payload_verified" if action == "verify-payload" else "verified"
    if not isinstance(evidence, dict) or evidence.get("verification_status") != status:
        raise ValueError("Release identity verification evidence is incomplete")
    return evidence


def require_expected_identity(info: dict, source_commit: str, version: str) -> None:
    if (
        info.get("source_commit") != source_commit
        or info.get("release_version") != version
    ):
        raise ValueError(
            "Archive/installed identity differs from the requested source/version"
        )


def run_browser_stage(repo: Path, output: Path, *arguments: str) -> dict:
    if output.exists():
        raise ValueError("Browser evidence requires a new output directory")
    process = subprocess.Popen(
        [
            sys.executable,
            str(repo / "tests/e2e/linux_release.py"),
            "--output",
            str(output),
            *arguments,
        ],
        cwd=output.parent,
        start_new_session=True,
    )
    try:
        returncode = process.wait(timeout=600)
        if returncode != 0:
            raise subprocess.CalledProcessError(returncode, process.args)
    finally:
        stop(process)
    filename = (
        "offline-smoke.json"
        if "--offline-reports" in arguments
        else "resume-smoke.json"
        if "--resume-evidence" in arguments
        else "application-smoke.json"
    )
    evidence = json.loads((output / filename).read_text(encoding="utf-8"))
    require_browser_evidence(evidence, filename)
    return evidence


def require_browser_evidence(evidence: object, filename: str) -> None:
    phases = {
        "application-smoke.json": "initial",
        "resume-smoke.json": "resume",
        "offline-smoke.json": "offline",
    }
    if (
        not isinstance(evidence, dict)
        or type(evidence.get("schema_version")) is not int
        or evidence["schema_version"] != 2
        or evidence.get("status") != "succeeded"
        or filename not in phases
        or evidence.get("phase") != phases[filename]
    ):
        raise ValueError("Browser journey did not produce successful current evidence")
    if filename != "offline-smoke.json":
        methods = {
            "eda.principal_components",
            "regression.partial_least_squares",
            "regression.gaussian_process",
            "quality.two_variances",
        }
        analyses, predictions = evidence.get("analyses"), evidence.get("predictions")
        if (
            not isinstance(analyses, list)
            or len(analyses) != len(methods)
            or any(not isinstance(item, dict) for item in analyses)
            or {item.get("method_id") for item in analyses} != methods
            or not isinstance(predictions, list)
            or len(predictions) != 2
            or any(not isinstance(item, dict) for item in predictions)
            or {item.get("family") for item in predictions}
            != {"pls", "gaussian_process"}
        ):
            raise ValueError("Analysis/model restore coverage is incomplete")
    if filename == "resume-smoke.json":
        if (
            type(evidence.get("analysis_post_count")) is not int
            or evidence["analysis_post_count"] != 0
        ):
            raise ValueError("Restore journey must not resubmit an analysis")
    elif filename == "offline-smoke.json":
        reports = evidence.get("reports")
        if (
            evidence.get("original_server_unreachable") is not True
            or evidence.get("browser_network_offline") is not True
            or type(evidence.get("http_request_count")) is not int
            or evidence["http_request_count"] != 0
            or not isinstance(reports, list)
            or len(reports) != 4
            or any(not isinstance(item, dict) for item in reports)
            or {(item.get("family"), item.get("locale")) for item in reports}
            != {
                (family, locale)
                for family in ("pls", "gaussian_process")
                for locale in ("ko", "en")
            }
        ):
            raise ValueError("Server-stopped offline report evidence is incomplete")
    elif filename == "application-smoke.json":
        checks = evidence.get("network_guard_checks")
        if (
            type(evidence.get("ui_analysis_post_count")) is not int
            or evidence["ui_analysis_post_count"] != 3
            or not isinstance(checks, list)
            or len(checks) != 9
            or any(not isinstance(item, str) or not item for item in checks)
            or len(set(checks)) != 9
        ):
            raise ValueError("Initial application journey evidence is incomplete")
    else:
        raise ValueError("Unknown browser evidence phase")


def verify_installed_refusal_probes(
    root: Path, env: dict[str, str], output: Path
) -> list[str]:
    """Mutate only disposable extracted files, restoring their exact bytes afterward."""
    marker = root / ".installed"
    original_marker = marker.read_bytes()
    site = root / ".venv/lib/python3.12/site-packages/app"
    initializer = site / "__init__.py"
    original_initializer = initializer.read_bytes()
    build_resource = site / "_release_build.json"
    original_build = build_resource.read_bytes()
    untouched_workspace = output / "must-not-be-created-workspace"
    sentinel = output / "must-not-run-old-application"
    probes = []

    def refused(name: str) -> None:
        process = subprocess.Popen(
            [
                str(root / "run.sh"),
                "--local-only",
                "--workspace-root",
                str(untouched_workspace),
            ],
            cwd=root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            stop(process)
            raise RuntimeError(
                f"Mixed-install refusal did not terminate: {name}"
            ) from None
        finally:
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()
        (output / f"refusal-{name}.log").write_text(stdout + stderr, encoding="utf-8")
        if process.returncode == 0 or untouched_workspace.exists() or sentinel.exists():
            raise RuntimeError(f"Mixed-install refusal failed: {name}")
        probes.append(name)

    try:
        marker.unlink()
        refused("missing-marker")
        marker.write_bytes(original_marker)
        changed = json.loads(original_marker)
        changed["source_commit"] = "0" * 40
        marker.write_text(json.dumps(changed), encoding="utf-8")
        refused("foreign-marker")
        marker.write_bytes(original_marker)
        changed = json.loads(original_build)
        changed["source_commit"] = "0" * 40
        build_resource.write_text(json.dumps(changed), encoding="utf-8")
        refused("foreign-installed-build")
        build_resource.write_bytes(original_build)
        # Even a matching new build-resource must not legitimize changed old code.
        initializer.write_bytes(
            original_initializer
            + (
                f"\nfrom pathlib import Path\nPath({str(sentinel)!r}).write_text('executed')\n"
            ).encode()
        )
        refused("changed-code-with-matching-build-resource")
        initializer.write_bytes(original_initializer)
        wheels = list((root / "wheels").glob("datalab_studio_backend-*.whl"))
        if len(wheels) != 1:
            raise ValueError(
                "Expected exactly one application wheel for refusal fixture"
            )
        wheel = wheels[0]
        wheel_bytes = wheel.read_bytes()
        try:
            wheel.write_bytes(wheel_bytes + b"corrupted fixture")
            refused("corrupt-wheelhouse")
        finally:
            wheel.write_bytes(wheel_bytes)
    finally:
        marker.write_bytes(original_marker)
        initializer.write_bytes(original_initializer)
        build_resource.write_bytes(original_build)
    return probes


def verify_live_reinstall_refusal(
    root: Path, env: dict[str, str], output: Path
) -> dict:
    marker_sha256 = file_sha256(root / ".installed")
    before = bootstrap_identity(root, env, "verify-installed")
    with (output / "live-reinstall-refusal.log").open("wb") as log:
        process = subprocess.Popen(
            [str(root / "install.sh")],
            cwd=root,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            returncode = process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            stop(process)
            raise RuntimeError(
                "Live installation lock refusal did not terminate"
            ) from None
    message = (output / "live-reinstall-refusal.log").read_text(encoding="utf-8")
    if returncode == 0 or "Release is in use" not in message:
        raise ValueError("Installer did not reject the running release")
    if file_sha256(root / ".installed") != marker_sha256:
        raise ValueError("Rejected installer changed the installation marker")
    after = bootstrap_identity(root, env, "verify-installed")
    if before != after:
        raise ValueError("Rejected installer changed the installed application")
    return {
        "status": "passed",
        "install_exit_code": returncode,
        "marker_sha256": marker_sha256,
        "installed_identity_unchanged": True,
    }


def immutable_workspace_files(workspace: Path) -> dict[str, str]:
    result = {}
    for namespace in ("workspaces", "artifacts"):
        directory = workspace / namespace
        if directory.is_symlink():
            raise ValueError("Unexpected linked synthetic workspace namespace")
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise ValueError("Unexpected link in synthetic validation workspace")
            if path.is_file():
                result[path.relative_to(workspace).as_posix()] = file_sha256(path)
    if not result:
        raise ValueError("No persisted synthetic artifacts were created")
    return result


def require_unchanged_artifacts(workspace: Path, expected: dict[str, str]) -> None:
    current = immutable_workspace_files(workspace)
    if any(current.get(path) != digest for path, digest in expected.items()):
        raise ValueError("A previously persisted source/model/report artifact changed")


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
        process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8600)
    parser.add_argument("--expected-source-commit", required=True)
    parser.add_argument("--expected-release-version", required=True)
    args = parser.parse_args()
    if sys.flags.optimize:
        parser.error("Run release validation without Python optimization")
    if platform.system() != "Linux" or sys.version_info[:2] != (3, 12):
        parser.error("Validate on Linux CPython 3.12")
    if not re.fullmatch(r"[a-f0-9]{40}", args.expected_source_commit):
        parser.error("Expected source must be a full commit SHA")
    archive = args.archive.resolve()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("Use a new empty validation output directory")
    output.mkdir(parents=True, exist_ok=True)
    archive_sha256 = file_sha256(archive)
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
            {
                key: os.environ[key]
                for key in ("HOME", "TMPDIR", "LANG", "LC_ALL", "LD_LIBRARY_PATH")
                if key in os.environ
            },
            PATH=str(binaries),
            PYTHON=sys._base_executable,
            PIP_NO_INDEX="1",
            PIP_DISABLE_PIP_VERSION_CHECK="1",
        )
        workspace = temp / "external workspace 검증"
        smoke = None
        installations = []
        isolated_installs = []
        restarts = []
        refusal_probes = []
        live_install_refusal = None
        offline = None
        artifact_hashes: dict[str, str] = {}
        initial_evidence = output / "initial/application-smoke.json"
        for index in range(2):
            root = unpack(archive, temp / f"installation {index} 검증")
            for dependency in ("react", "react-dom", "lucide-react", "noble_hashes"):
                notices = list(
                    (root / "THIRD_PARTY_NOTICES/frontend").glob(f"{dependency}-*")
                )
                assert notices and any(
                    path.name.lower().startswith("license")
                    for directory in notices
                    for path in directory.iterdir()
                ), f"Missing frontend license notice: {dependency}"
            payload = bootstrap_identity(root, env, "verify-payload")
            require_expected_identity(
                payload, args.expected_source_commit, args.expected_release_version
            )
            expected = json.loads(
                (root / "BUILD_INFO.json").read_text(encoding="utf-8")
            )
            require_expected_identity(
                expected, args.expected_source_commit, args.expected_release_version
            )
            isolated_installs.append(
                run_network_blocked_install(
                    root,
                    env,
                    output / f"install-{index}.log",
                    output / f"install-{index}-network.json",
                )
            )
            installed = bootstrap_identity(root, env, "verify-installed")
            require_expected_identity(
                installed, args.expected_source_commit, args.expected_release_version
            )
            if index == 0:
                refusal_probes = verify_installed_refusal_probes(root, env, output)
                isolated_installs.append(
                    run_network_blocked_install(
                        root,
                        env,
                        output / "reinstall-0.log",
                        output / "reinstall-0-network.json",
                    )
                )
                installed = bootstrap_identity(root, env, "verify-installed")
                require_expected_identity(
                    installed,
                    args.expected_source_commit,
                    args.expected_release_version,
                )
            installations.append(installed)
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
            for cycle in range(2 if index == 0 else 1):
                proof = bootstrap_identity(root, env, "verify-installed")
                require_expected_identity(
                    proof, args.expected_source_commit, args.expected_release_version
                )
                with (output / f"server-{index}-{cycle}.log").open("wb") as log:
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
                        else:
                            assert_interface_isolated(lan_address, args.port)
                        if index == 0 and cycle == 0:
                            live_install_refusal = verify_live_reinstall_refusal(
                                root, env, output
                            )
                            wait_ready(base, process, expected)
                            smoke = run_browser_stage(
                                repo, output / "initial", "--url", base
                            )
                        else:
                            restarts.append(
                                run_browser_stage(
                                    repo,
                                    output / f"resume-{index}-{cycle}",
                                    "--url",
                                    base,
                                    "--resume-evidence",
                                    str(initial_evidence),
                                )
                            )
                    finally:
                        stop(process)
                assert not listener_addresses(
                    args.port
                ), "Release listener survived shutdown"
                if index == 0 and cycle == 0:
                    artifact_hashes = immutable_workspace_files(workspace)
                    offline = run_browser_stage(
                        repo,
                        output / "server-stopped-offline",
                        "--offline-reports",
                        str(initial_evidence),
                    )
                else:
                    require_unchanged_artifacts(workspace, artifact_hashes)
        if (
            len(installations) != 2
            or len(isolated_installs) != 3
            or len(restarts) != 2
            or live_install_refusal is None
            or offline is None
            or smoke is None
        ):
            raise RuntimeError("Release verification phases are incomplete")
        if file_sha256(archive) != archive_sha256:
            raise ValueError("Archive bytes changed during validation")
        report = {
            "schema_version": 2,
            "status": "passed",
            "archive": archive.name,
            "archive_sha256": archive_sha256,
            "source_commit": expected["source_commit"],
            "release_version": expected["release_version"],
            "actual_platform": platform.platform(),
            "python": platform.python_version(),
            "node_and_git_in_install_runtime_path": False,
            "offline_installations": 2,
            "offline_reinstallations": 1,
            "network_blocked_installations": isolated_installs,
            "installed_identities": installations,
            "mixed_install_refusal_probes": refusal_probes,
            "live_installation_refusal": live_install_refusal,
            "same_install_restart_restore": True,
            "shared_external_workspace_restart_restore": True,
            "restart_journeys": restarts,
            "server_stopped_offline_reports": offline,
            "persisted_artifact_sha256": artifact_hashes,
            "persisted_artifacts_unchanged_after_restarts": True,
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
