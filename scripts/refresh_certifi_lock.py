"""Native, narrowly scoped remediation for GHSA-6q48-6c7w-9gw2."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

from generate_python_lock import collect_wheel_records, read_wheel_identity
from validate_python_lock import validate_lock_text

ROOT = Path(__file__).resolve().parents[1]
CERTIFI_VERSION = "2026.10.19"


def validate_refresh(before: dict, after: dict) -> None:
    if set(before) != set(after) or "certifi" not in before:
        raise ValueError("The distribution set must not change")
    if after["certifi"]["version"] != CERTIFI_VERSION:
        raise ValueError("Unexpected certifi version")
    for name, record in before.items():
        if name != "certifi" and after[name] != record:
            raise ValueError(f"Unrelated version/hash changed: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target", choices=["py310-win", "py311-linux", "py312-linux"], required=True
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    expected = {
        "py310-win": ("Windows", 10),
        "py311-linux": ("Linux", 11),
        "py312-linux": ("Linux", 12),
    }[args.target]
    if (
        platform.system(),
        sys.version_info.minor,
    ) != expected or sys.version_info.major != 3:
        parser.error("Run on the exact native target OS and Python version")
    if platform.machine().lower() not in {"amd64", "x86_64"}:
        parser.error("The target requires x86_64")
    name = f"requirements-{args.target}" + (
        "" if args.target == "py310-win" else "-dev"
    )
    baseline = ROOT / "backend" / f"{name}.lock"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir.resolve() / baseline.name
    output.with_suffix(".in").write_bytes(baseline.with_suffix(".in").read_bytes())
    before = validate_lock_text(baseline.read_text("ascii"), {}, target=args.target)
    with tempfile.TemporaryDirectory(prefix="certifi-native-lock-") as temporary:
        stage = Path(temporary)
        wheels = stage / "wheels"
        wheels.mkdir()
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--only-binary=:all:",
                "--require-hashes",
                "-r",
                str(baseline),
                "--dest",
                str(wheels),
            ],
            check=True,
        )
        old = [
            path
            for path in wheels.glob("*.whl")
            if read_wheel_identity(path)[0].lower() == "certifi"
        ]
        if len(old) != 1:
            raise ValueError("Expected exactly one original certifi wheel")
        old[0].unlink()
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--only-binary=:all:",
                "--no-deps",
                f"certifi=={CERTIFI_VERSION}",
                "--dest",
                str(wheels),
            ],
            check=True,
        )
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/generate_python_lock.py"),
                str(wheels),
                str(output),
                "--target",
                args.target,
                "--profile",
                "dev",
            ],
            check=True,
        )
        after = validate_lock_text(output.read_text("ascii"), {}, target=args.target)
        validate_refresh(before, after)
        venv.EnvBuilder(with_pip=True).create(stage / "verify")
        python = (
            stage
            / "verify"
            / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")
        )
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-index",
                "--find-links",
                str(wheels),
                "--only-binary=:all:",
                "--require-hashes",
                "-r",
                str(output),
            ],
            check=True,
        )
        subprocess.run([str(python), "-m", "pip", "check"], check=True)
        receipt = {
            "schema_version": 1,
            "purpose": "certifi_native_dev_lock_security_refresh",
            "target": args.target,
            "system": platform.platform(),
            "python": platform.python_version(),
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "baseline_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
            "generated_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "only_changed_distribution": "certifi",
            "wheel_records": collect_wheel_records(wheels),
            "offline_install_and_pip_check": "passed",
            "network_block_enforced": False,
            "product_validation_complete": False,
        }
        (args.output_dir / "receipt.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
