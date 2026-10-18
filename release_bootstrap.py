"""Release-owned, stdlib-only verification before importing installed application code."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import runpy
import stat
import subprocess
import sys
import tempfile
import zipfile
from contextlib import contextmanager
from email.parser import BytesParser
from pathlib import Path
from typing import Any, Iterator, cast

APPLICATION = "datalab-studio-backend"
RESOURCE = "app/_release_build.json"
IDENTITY_FIELDS = (
    "source_commit",
    "release_version",
    "api_contract_version",
    "metadata_schema_version",
    "required_capabilities",
    "python_target",
    "os",
    "architecture",
)
MARKER = ".installed"
RELEASE_VERSION_PATTERN = (
    r"(?:0|[1-9][0-9]{0,7})\.(?:0|[1-9][0-9]{0,7})\.(?:0|[1-9][0-9]{0,7})"
)


class ReleaseVerificationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReleaseVerificationError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _relative_parts(relative: str) -> list[str]:
    require(isinstance(relative, str), "Unsafe release path")
    parts = relative.split("/")
    require(
        len(relative) <= 1024
        and not any(part in {"", ".", ".."} for part in parts)
        and "\\" not in relative
        and ":" not in relative
        and not any(ord(char) < 32 for char in relative),
        "Unsafe release path",
    )
    return parts


def safe_path(root: Path, relative: str) -> Path:
    parts = _relative_parts(relative)
    path = root
    for part in parts:
        path = path / part
        require(not path.is_symlink(), "Release contains an unsafe link")
    require(root in path.resolve().parents, "Unsafe release path")
    return path


def read_bounded(path: Path, limit: int) -> bytes:
    require(
        path.is_file() and not path.is_symlink(),
        "Required release file is missing or linked",
    )
    with path.open("rb") as stream:
        contents = stream.read(limit + 1)
    require(len(contents) <= limit, "Release metadata exceeds its limit")
    return contents


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "Duplicate release JSON key")
        result[key] = value
    return result


def parse_json(contents: bytes) -> dict[str, Any]:
    try:
        value = json.loads(contents, object_pairs_hook=_unique_object)
    except (ValueError, UnicodeError) as exc:
        raise ReleaseVerificationError("Invalid release JSON") from exc
    require(isinstance(value, dict), "Release JSON must be an object")
    return cast(dict[str, Any], value)


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()


def _identity(info: dict[str, Any]) -> dict[str, Any]:
    require(all(key in info for key in IDENTITY_FIELDS), "Incomplete release identity")
    require(
        re.fullmatch(r"[a-f0-9]{40}", str(info["source_commit"])) is not None,
        "Invalid release source commit",
    )
    require(
        re.fullmatch(RELEASE_VERSION_PATTERN, str(info["release_version"])) is not None,
        "Invalid release version",
    )
    require(
        info["python_target"] == "3.12"
        and info["os"] == "ubuntu24.04"
        and info["architecture"] == "x86_64",
        "Unsupported release target",
    )
    for key in ("api_contract_version", "metadata_schema_version"):
        require(type(info[key]) is int and info[key] > 0, "Invalid runtime contract")
    caps = info["required_capabilities"]
    require(
        isinstance(caps, dict)
        and len(caps) <= 512
        and all(
            isinstance(key, str) and 0 < len(key) <= 200 and type(value) is bool
            for key, value in caps.items()
        ),
        "Invalid runtime capabilities",
    )
    return {key: info[key] for key in IDENTITY_FIELDS}


def application_wheel_files(wheel: Path) -> tuple[dict[str, str], dict[str, Any]]:
    require(wheel.stat().st_size <= 64 * 1024 * 1024, "Application wheel exceeds limit")
    try:
        with zipfile.ZipFile(wheel) as archive:
            entries = archive.infolist()
            require(0 < len(entries) <= 10000, "Invalid application wheel file count")
            names = [entry.filename for entry in entries]
            require(len(names) == len(set(names)), "Duplicate wheel entry")
            total = 0
            files: dict[str, str] = {}
            metadata_names = []
            resource = None
            for entry in entries:
                name = entry.filename
                _relative_parts(name.rstrip("/"))
                require(
                    not stat.S_ISLNK(entry.external_attr >> 16), "Linked wheel entry"
                )
                if entry.is_dir():
                    continue
                total += entry.file_size
                require(
                    entry.file_size <= 16 * 1024 * 1024 and total <= 128 * 1024 * 1024,
                    "Application wheel contents exceed limit",
                )
                require(
                    name.startswith("app/") or ".dist-info/" in name,
                    "Unexpected application wheel layout",
                )
                require(
                    not name.endswith((".pyc", ".pyo")),
                    "Application wheel contains bytecode",
                )
                data = archive.read(entry)
                files[name] = hashlib.sha256(data).hexdigest()
                if name.endswith(".dist-info/METADATA"):
                    metadata_names.append(name)
                    metadata = BytesParser().parsebytes(data)
                    require(
                        metadata.get("Name") == APPLICATION,
                        "Wrong application distribution",
                    )
                if name == RESOURCE:
                    require(len(data) <= 65536, "Build resource exceeds limit")
                    resource = parse_json(data)
            require(
                len(metadata_names) == 1 and resource is not None,
                "Application wheel build identity is missing",
            )
            return files, _identity(cast(dict[str, Any], resource))
    except (zipfile.BadZipFile, RuntimeError) as exc:
        raise ReleaseVerificationError("Invalid application wheel") from exc


def verify_release_payload(root: Path) -> dict[str, Any]:
    root = root.resolve()
    manifest = read_bounded(root / "FILES.sha256", 4 * 1024 * 1024)
    seen: set[str] = set()
    try:
        lines = manifest.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise ReleaseVerificationError("Invalid release checksum manifest") from exc
    require(0 < len(lines) <= 20000, "Invalid release manifest count")
    for line in lines:
        match = re.fullmatch(r"([a-f0-9]{64})  ([^\r\n]+)", line)
        require(match is not None, "Invalid release checksum entry")
        assert match is not None
        expected, relative = match.groups()
        require(relative not in seen, "Unsafe or duplicate release checksum path")
        require(
            relative.split("/")[0]
            not in {".venv", ".installed", ".release.lock", "FILES.sha256"},
            "Mutable installation state cannot be a payload file",
        )
        seen.add(relative)
        path = safe_path(root, relative)
        require(
            path.is_file() and digest(path) == expected,
            f"Release checksum mismatch: {relative}",
        )
    require(
        {
            "BUILD_INFO.json",
            "web/index.html",
            "requirements-release.lock",
            "install.sh",
            "run.sh",
            "release_bootstrap.py",
        }
        <= seen,
        "Release manifest is incomplete",
    )
    for directory in ("web", "wheels"):
        for path in (root / directory).rglob("*"):
            require(not path.is_symlink(), "Release contains an unsafe link")
            if path.is_file():
                require(
                    path.relative_to(root).as_posix() in seen,
                    "Release contains unverified files",
                )
    info = parse_json(read_bounded(root / "BUILD_INFO.json", 65536))
    identity = _identity(info)
    lock_sha = digest(root / "requirements-release.lock")
    require(info.get("lock_sha256") == lock_sha, "Release lock identity mismatch")
    wheel_name = info.get("application_wheel")
    require(
        isinstance(wheel_name, str)
        and wheel_name.startswith("wheels/")
        and wheel_name.endswith(".whl")
        and wheel_name in seen,
        "Application wheel is missing",
    )
    wheel = safe_path(root, cast(str, wheel_name))
    wheel_sha = digest(wheel)
    require(
        info.get("application_wheel_sha256") == wheel_sha,
        "Application wheel identity mismatch",
    )
    _, resource = application_wheel_files(wheel)
    require(resource == identity, "Application wheel source identity mismatch")
    return {**info, "release_manifest_sha256": hashlib.sha256(manifest).hexdigest()}


def _site_packages(root: Path) -> Path:
    venv = safe_path(root, ".venv")
    require(venv.is_dir(), "Release virtual environment is missing")
    config = read_bounded(safe_path(root, ".venv/pyvenv.cfg"), 16384).decode("utf-8")
    values = dict(line.split("=", 1) for line in config.splitlines() if "=" in line)
    values = {key.strip(): value.strip() for key, value in values.items()}
    require(
        values.get("include-system-site-packages", "").lower() == "false",
        "System site packages are not permitted",
    )
    require(
        re.fullmatch(r"3\.12(?:\.\d+)?", values.get("version", "")) is not None,
        "Existing venv Python differs; use a new directory",
    )
    site = safe_path(root, ".venv/lib/python3.12/site-packages")
    require(site.is_dir(), "Release site-packages is missing")
    return site


def _installed_files(root: Path, info: dict[str, Any]) -> str:
    site = _site_packages(root)
    files, identity = application_wheel_files(
        safe_path(root, info["application_wheel"])
    )
    expected_dist = next(
        name.split("/")[0] for name in files if name.endswith(".dist-info/METADATA")
    )
    matches = []
    metadata_dirs = list(site.glob("*.dist-info"))
    require(len(metadata_dirs) <= 512, "Too many installed distributions")
    for directory in metadata_dirs:
        metadata_path = safe_path(site, f"{directory.name}/METADATA")
        metadata = BytesParser().parsebytes(read_bounded(metadata_path, 1024 * 1024))
        name = re.sub(r"[-_.]+", "-", str(metadata.get("Name", ""))).lower()
        if name == APPLICATION:
            matches.append(directory)
    require(
        len(matches) == 1 and matches[0].name == expected_dist,
        "Application distribution is missing or duplicated",
    )
    require(
        not list(site.glob("*datalab*studio*backend*.egg-link")),
        "Editable application is forbidden",
    )
    for name, checksum in files.items():
        # pip rewrites RECORD; immutable wheel bytes, not installed RECORD, are authoritative.
        if name.endswith(".dist-info/RECORD"):
            continue
        path = safe_path(site, name)
        require(
            path.is_file() and digest(path) == checksum,
            f"Installed application checksum mismatch: {name}",
        )
    app_root = safe_path(site, "app")
    for path in app_root.rglob("*"):
        require(not path.is_symlink(), "Installed application contains a link")
        if path.is_file():
            require(
                path.relative_to(site).as_posix() in files,
                "Installed application contains unowned code or bytecode",
            )
    installed_identity = parse_json(read_bounded(safe_path(site, RESOURCE), 65536))
    require(
        _identity(installed_identity) == identity, "Installed build identity mismatch"
    )
    return hashlib.sha256(_canonical(files)).hexdigest()


def _marker_identity(root: Path, info: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        **_identity(info),
        "application_wheel_sha256": info["application_wheel_sha256"],
        "release_manifest_sha256": info["release_manifest_sha256"],
        "lock_sha256": info["lock_sha256"],
        "installed_application_files_sha256": _installed_files(root, info),
    }


def verify_installed_release(root: Path) -> dict[str, Any]:
    root = root.resolve()
    info = verify_release_payload(root)
    actual = _marker_identity(root, info)
    saved = parse_json(read_bounded(safe_path(root, MARKER), 65536))
    require(saved == actual, "Installation marker identity mismatch; rerun install.sh")
    return {**actual, "verification_status": "verified"}


def _sync_directory(root: Path) -> None:
    if os.name != "nt":
        descriptor = os.open(root, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def commit_installation_marker(root: Path, info: dict[str, Any]) -> None:
    marker = safe_path(root, MARKER)
    contents = _canonical(_marker_identity(root, info)) + b"\n"
    descriptor, name = tempfile.mkstemp(prefix=".installed-", suffix=".tmp", dir=root)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, marker)
        _sync_directory(root)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def release_lock(root: Path, *, exclusive: bool) -> Iterator[None]:
    # Persistent inode: never unlink it on release or steal it using PID metadata.
    if sys.platform == "win32":
        raise ReleaseVerificationError("Archive installation locks require Linux")
    else:
        import fcntl

        path = safe_path(root, ".release.lock")
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            try:
                fcntl.flock(descriptor, operation | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ReleaseVerificationError(
                    "Release is in use; stop it before reinstalling"
                ) from exc
            yield
        finally:
            os.close(descriptor)


def _enable_site(root: Path) -> None:
    site = _site_packages(root)
    sys.prefix = sys.exec_prefix = str(root / ".venv")
    sys.path.insert(0, str(site))
    # Deliberately do not call site.addsitedir: .pth files must not execute.


def install(root: Path) -> None:
    with release_lock(root, exclusive=True):
        info = verify_release_payload(root)
        marker = safe_path(root, MARKER)
        marker.unlink(missing_ok=True)
        _sync_directory(root)
        venv = safe_path(root, ".venv")
        if not venv.exists():
            subprocess.run(
                [sys.executable, "-I", "-S", "-B", "-m", "venv", str(venv)], check=True
            )
        _site_packages(root)
        python = venv / "bin/python"
        require(python.is_file(), "Release venv Python is missing")
        command = [
            str(python),
            "-I",
            "-S",
            "-B",
            str(root / "release_bootstrap.py"),
            "_pip",
            "--release-root",
            str(root),
        ]
        subprocess.run(
            command
            + [
                "install",
                "--force-reinstall",
                "--no-compile",
                "--no-index",
                "--find-links",
                str(root / "wheels"),
                "--only-binary=:all:",
                "--require-hashes",
                "-r",
                str(root / "requirements-release.lock"),
            ],
            check=True,
        )
        subprocess.run(command + ["check"], check=True)
        # Revalidate payload after pip; a marker never certifies a changed payload.
        info = verify_release_payload(root)
        commit_installation_marker(root, info)


def validate_platform() -> None:
    require(
        platform.system() == "Linux"
        and platform.machine() == "x86_64"
        and platform.python_implementation() == "CPython"
        and sys.version_info[:2] == (3, 12),
        "Requires Linux x86_64 CPython 3.12",
    )
    release = platform.freedesktop_os_release()
    require(
        release.get("ID") == "ubuntu" and release.get("VERSION_ID") == "24.04",
        "Validated release target is Ubuntu 24.04",
    )
    require(
        bool(
            sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode
        ),
        "Run release bootstrap with -I -S -B",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "verify-payload",
            "verify-installed",
            "install",
            "launch",
            "workspace-backup",
            "_pip",
        ),
    )
    parser.add_argument("--release-root", required=True, type=Path)
    args, remaining = parser.parse_known_args()
    root = args.release_root.resolve()
    try:
        validate_platform()
        if args.action == "install":
            require(not remaining, "Unexpected installer arguments")
            install(root)
            print(json.dumps(verify_installed_release(root), sort_keys=True))
        elif args.action == "_pip":
            _enable_site(root)
            sys.argv = ["pip", *remaining]
            runpy.run_module("pip", run_name="__main__")
        elif args.action in {"launch", "workspace-backup"}:
            with release_lock(root, exclusive=False):
                evidence = verify_installed_release(root)
                _enable_site(root)
                if args.action == "launch":
                    from app.launch import launch_verified

                    launch_verified(root, evidence, remaining)
                else:
                    sys.argv = ["app.storage.workspace_backup", *remaining]
                    runpy.run_module(
                        "app.storage.workspace_backup", run_name="__main__"
                    )
        else:
            require(not remaining, "Unexpected verifier arguments")
            with release_lock(root, exclusive=False):
                evidence = (
                    verify_installed_release(root)
                    if args.action == "verify-installed"
                    else {
                        **verify_release_payload(root),
                        "verification_status": "payload_verified",
                    }
                )
                print(json.dumps(evidence, sort_keys=True))
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"Release verification failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
