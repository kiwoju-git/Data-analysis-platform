"""One-off native lock preparation, kept off the product branch."""

import argparse
import json
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

from packaging.requirements import Requirement

from generate_python_lock import canonicalize_name, collect_wheel_records
from validate_python_lock import ENTRY_PATTERN

UPDATES = {"fastapi": "0.135.4", "starlette": "1.7.0", "annotated-doc": "0.0.4"}
NUMERICS = {"numpy", "scipy", "scikit-learn", "joblib", "threadpoolctl"}


def run(*args):
    subprocess.run([str(arg) for arg in args], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    profiles = ["dev"] if args.target == "py310-win" else ["runtime", "dev"]
    for profile in profiles:
        stem = "requirements-py310-win" if args.target == "py310-win" else f"requirements-{args.target}-{profile}"
        original = root / "backend" / (stem + ".lock")
        old = dict(match.groups() for line in original.read_text().splitlines() if (match := ENTRY_PATTERN.fullmatch(line)))
        inputs = []
        for line in original.with_suffix(".in").read_text().splitlines():
            if not line or line.startswith("#"):
                continue
            requirement = Requirement(line)
            if canonicalize_name(requirement.name) not in UPDATES:
                inputs.append(line)
        inputs.extend(f"{name}=={version}" for name, version in UPDATES.items())
        generated_in = args.output_dir / (stem + ".in")
        generated_lock = args.output_dir / (stem + ".lock")
        generated_in.write_text("# Security refresh; other direct and transitive versions preserved.\n" + "\n".join(inputs) + "\n", encoding="ascii")
        with tempfile.TemporaryDirectory(prefix="security-lock-") as temporary:
            temp = Path(temporary)
            constraints = temp / "constraints.txt"
            constraints.write_text("\n".join(f"{name}=={version}" for name, version in old.items() if name not in UPDATES) + "\n", encoding="ascii")
            wheels = temp / "wheels"
            run(sys.executable, "-m", "pip", "download", "--only-binary=:all:", "--dest", wheels, "-r", generated_in, "-c", constraints)
            run(sys.executable, root / "scripts/generate_python_lock.py", wheels, generated_lock, "--target", args.target, "--profile", profile)
            records = {record["name"]: record["version"] for record in collect_wheel_records(wheels)}
            assert all(records[name] == old[name] for name in NUMERICS)
            environment = temp / "validation"
            venv.EnvBuilder(with_pip=True).create(environment)
            python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            run(python, "-m", "pip", "install", "--no-index", "--find-links", wheels, "--only-binary=:all:", "--require-hashes", "-r", generated_lock)
            run(python, "-m", "pip", "check")
        (args.output_dir / (stem + ".validation.json")).write_text(json.dumps({"target": args.target, "profile": profile, "python": sys.version, "installed": True, "pip_check": "passed", "numeric_versions_unchanged": True, "versions": records}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
