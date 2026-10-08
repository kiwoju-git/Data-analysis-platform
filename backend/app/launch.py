"""Verified, loopback-only release launcher. Import the app only after setting identity."""

import argparse
import hashlib
import json
import os
import platform
import re
import sys
from pathlib import Path
from typing import Any

from app.core.network_ports import check_tcp_port_available


def verify_release(root: Path) -> dict[str, Any]:
    root = root.resolve()
    manifest = root / "FILES.sha256"
    if not manifest.is_file() or manifest.is_symlink():
        raise ValueError("Release checksum manifest is missing")
    seen: set[str] = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  ([^\r\n]+)", line)
        if match is None:
            raise ValueError("Invalid release checksum entry")
        checksum, relative = match.groups()
        parts = relative.split("/")
        if (
            relative in seen
            or any(part in {"", ".", ".."} for part in parts)
            or "\\" in relative
            or ":" in relative
        ):
            raise ValueError("Unsafe or duplicate release checksum path")
        seen.add(relative)
        path = root.joinpath(*parts)
        if root not in path.resolve().parents or any(
            parent.is_symlink()
            for parent in [path, *path.parents]
            if parent != root and root in parent.parents
        ):
            raise ValueError("Release contains an unsafe link")
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
            raise ValueError(f"Release checksum mismatch: {relative}")
    if not {
        "BUILD_INFO.json",
        "web/index.html",
        "requirements-release.lock",
        "install.sh",
        "run.sh",
    }.issubset(seen):
        raise ValueError("Release manifest is incomplete")
    for directory in ("web", "wheels"):
        actual = {
            path.relative_to(root).as_posix()
            for path in (root / directory).rglob("*")
            if path.is_file()
        }
        if not actual.issubset(seen):
            raise ValueError("Release contains unverified static files or wheels")
    info: dict[str, Any] = json.loads((root / "BUILD_INFO.json").read_text(encoding="utf-8"))
    from app.core.runtime_contract import API_CONTRACT_VERSION, RUNTIME_CAPABILITIES
    from app.storage.metadata import SCHEMA_VERSION

    if not re.fullmatch(r"[a-f0-9]{40}", str(info.get("source_commit", ""))):
        raise ValueError("Release source commit is invalid")
    if (
        info.get("api_contract_version") != API_CONTRACT_VERSION
        or info.get("metadata_schema_version") != SCHEMA_VERSION
        or info.get("required_capabilities") != RUNTIME_CAPABILITIES
    ):
        raise ValueError("Release runtime contract mismatch")
    if (
        info.get("python_target") != "3.12"
        or info.get("os") != "ubuntu24.04"
        or info.get("architecture") != "x86_64"
    ):
        raise ValueError("Unsupported release target")
    lock_hash = hashlib.sha256((root / "requirements-release.lock").read_bytes()).hexdigest()
    if info.get("lock_sha256") != lock_hash:
        raise ValueError("Release lock identity mismatch")
    return info


def main() -> None:
    parser = argparse.ArgumentParser(description="Statistical Twin verified Linux release")
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path)
    parser.add_argument("--port", type=int, default=8600)
    args = parser.parse_args()
    if (
        platform.system() != "Linux"
        or platform.machine().lower() != "x86_64"
        or platform.python_implementation() != "CPython"
        or sys.version_info[:2] != (3, 12)
    ):
        parser.error("This release requires Linux x86_64 and CPython 3.12")
    if not 1024 <= args.port <= 65535:
        parser.error("Port must be between 1024 and 65535")
    root = args.release_root.resolve()
    try:
        info = verify_release(root)
        check_tcp_port_available("127.0.0.1", args.port)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    os.environ.update(
        DATALAB_GIT_COMMIT=info["source_commit"],
        DATALAB_FRONTEND_DIST=str(root / "web"),
        DATALAB_ENVIRONMENT="production",
        DATALAB_BIND_HOST="127.0.0.1",
        DATALAB_BIND_PORT=str(args.port),
    )
    for name in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        os.environ[name] = "1"
    if args.workspace_root is not None:
        os.environ["DATALAB_WORKSPACE_ROOT"] = str(args.workspace_root.resolve())
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=args.port, workers=1, reload=False)


if __name__ == "__main__":
    main()
