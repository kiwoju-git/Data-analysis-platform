"""Build only committed source into a hash-locked offline Linux application archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from generate_python_lock import collect_wheel_records, render_lock


def checked(arguments: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(arguments, cwd=cwd, env=env, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--release-version", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if (
        platform.system() != "Linux"
        or platform.machine() != "x86_64"
        or platform.python_implementation() != "CPython"
        or sys.version_info[:2] != (3, 12)
    ):
        parser.error("Build on Linux x86_64 CPython 3.12")
    if not re.fullmatch(r"[a-f0-9]{40}", args.source_commit) or not re.fullmatch(
        r"[0-9]+\.[0-9]+\.[0-9]+", args.release_version
    ):
        parser.error("Use a full source SHA and numeric release version")
    repo = Path(__file__).resolve().parents[1]
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    if head != args.source_commit:
        parser.error("Source commit must be checked-out HEAD")
    checked(["git", "diff", "--exit-code"], repo)
    checked(["git", "diff", "--cached", "--exit-code"], repo)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    name = (
        f"statistical-twin-linux-{args.release_version}-ubuntu24.04-x86_64-py312.tar.gz"
    )
    if (output / name).exists():
        parser.error("Output archive already exists; use a new output directory")
    with tempfile.TemporaryDirectory(prefix="statistical-twin-build-") as temporary:
        stage = Path(temporary)
        source = stage / "source"
        source.mkdir()
        source_tar = stage / "source.tar"
        checked(
            [
                "git",
                "archive",
                "--format=tar",
                f"--output={source_tar}",
                args.source_commit,
            ],
            repo,
        )
        with tarfile.open(source_tar) as archive:
            archive.extractall(source, filter="data")
        env = dict(
            os.environ, VITE_API_BASE_URL="/", VITE_GIT_COMMIT=args.source_commit
        )
        checked(["npm", "ci"], source / "frontend", env)
        checked(["npm", "run", "build"], source / "frontend", env)
        package = stage / "statistical-twin-linux"
        wheels = package / "wheels"
        wheels.mkdir(parents=True)
        checked(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--only-binary=:all:",
                "--require-hashes",
                "-r",
                str(source / "backend/requirements-py312-linux-runtime.lock"),
                "--dest",
                str(wheels),
            ],
            source,
        )
        checked(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                "--no-deps",
                "--no-build-isolation",
                "--wheel-dir",
                str(wheels),
                str(source / "backend"),
            ],
            source,
        )
        lock = render_lock(collect_wheel_records(wheels), "py312-linux", "runtime")
        lock = lock.replace(
            "# Source roots: backend/requirements-py312-linux-runtime.in",
            "# Source: runtime lock plus the application wheel built from BUILD_INFO.source_commit",
        )
        (package / "requirements-release.lock").write_text(
            lock, encoding="ascii", newline="\n"
        )
        shutil.copytree(source / "frontend/dist", package / "web")
        for filename in ("install.sh", "run.sh", "README-linux.md"):
            contents = (source / filename).read_text(encoding="utf-8")
            (package / filename).write_text(contents, encoding="utf-8", newline="\n")
        notices = package / "THIRD_PARTY_NOTICES"
        notices.mkdir()
        for wheel in wheels.glob("*.whl"):
            destination = notices / wheel.stem
            destination.mkdir()
            with zipfile.ZipFile(wheel) as archive:
                for index, member in enumerate(archive.namelist()):
                    leaf = Path(member).name
                    if ".dist-info/" in member and (
                        leaf == "METADATA"
                        or any(
                            token in leaf.lower()
                            for token in ("license", "copying", "notice")
                        )
                    ):
                        (destination / f"{index}-{leaf}").write_bytes(
                            archive.read(member)
                        )
        if (source / "LICENSE").is_file():
            shutil.copy2(source / "LICENSE", notices / "APPLICATION-LICENSE")
        contract_env = dict(os.environ, PYTHONPATH=str(source / "backend"))
        contract = json.loads(
            subprocess.check_output(
                [
                    sys.executable,
                    "-c",
                    "import json; from app.core.runtime_contract import API_CONTRACT_VERSION; from app.storage.metadata import SCHEMA_VERSION; print(json.dumps([API_CONTRACT_VERSION,SCHEMA_VERSION]))",
                ],
                cwd=source,
                env=contract_env,
                text=True,
            )
        )
        info = {
            "release_version": args.release_version,
            "source_commit": args.source_commit,
            "api_contract_version": contract[0],
            "metadata_schema_version": contract[1],
            "python_target": "3.12",
            "os": "ubuntu24.04",
            "architecture": "x86_64",
            "build_timestamp": datetime.now(timezone.utc).isoformat(),
            "lock_sha256": hashlib.sha256(
                (package / "requirements-release.lock").read_bytes()
            ).hexdigest(),
        }
        (package / "BUILD_INFO.json").write_text(
            json.dumps(info, indent=2) + "\n", encoding="utf-8"
        )
        manifest = []
        for path in sorted(package.rglob("*")):
            if path.is_file():
                path.chmod(0o755 if path.suffix == ".sh" else 0o644)
                manifest.append(
                    f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(package).as_posix()}"
                )
        (package / "FILES.sha256").write_text(
            "\n".join(manifest) + "\n", encoding="utf-8"
        )
        with tarfile.open(output / name, "w:gz") as archive:
            archive.add(package, arcname="statistical-twin-linux")
    checksum = hashlib.sha256((output / name).read_bytes()).hexdigest()
    (output / "SHA256SUMS").write_text(f"{checksum}  {name}\n", encoding="ascii")
    shutil.copy2(repo / "README-linux.md", output / "README-linux.md")
    print(
        json.dumps(
            {"archive": name, "sha256": checksum, "source_commit": args.source_commit}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
