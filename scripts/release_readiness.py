"""Validate release naming and require every declared CI gate to succeed."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

REQUIRED_JOBS = {
    "release": (
        "windows",
        "e2e",
        "linux",
        "python311",
        "linux-release",
        "dependency-security",
    ),
    "dependencies": ("security-python", "security-npm"),
    "windows-e2e": ("windows-e2e",),
}
VERSION_PATTERN = r"(?:0|[1-9][0-9]{0,7})\.(?:0|[1-9][0-9]{0,7})\.(?:0|[1-9][0-9]{0,7})"


def resolve_release_version(metadata_path: Path, override: str = "") -> str:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if (
        not isinstance(metadata, dict)
        or metadata.get("schema_version") != 1
        or metadata.get("channel") != "prerelease"
    ):
        raise ValueError("Invalid Linux release version metadata")
    default = metadata.get("linux_release_version")
    if not isinstance(default, str) or re.fullmatch(VERSION_PATTERN, default) is None:
        raise ValueError("Invalid default Linux release version")
    version = override if override else default
    if re.fullmatch(VERSION_PATTERN, version) is None:
        raise ValueError("Release version must be three bounded numeric components")
    return version


def require_successful_jobs(
    results: Any, kind: str, source_commit: str
) -> dict[str, Any]:
    if kind not in REQUIRED_JOBS:
        raise ValueError("Unknown gate kind")
    if re.fullmatch(r"[a-f0-9]{40}", source_commit) is None:
        raise ValueError("A full source commit is required")
    required = REQUIRED_JOBS[kind]
    if not isinstance(results, dict) or set(results) != set(required):
        raise ValueError("Gate dependencies must exactly match the required jobs")
    failed = [
        name
        for name in required
        if not isinstance(results[name], dict)
        or results[name].get("result") != "success"
    ]
    if failed:
        raise ValueError("Required jobs did not succeed: " + ", ".join(failed))
    return {
        "schema_version": 1,
        "gate": kind,
        "source_commit": source_commit,
        "status": "passed",
        "jobs": {name: "success" for name in required},
        "publication_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    version = subcommands.add_parser("version")
    version.add_argument(
        "--metadata",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "release-version.json",
    )
    version.add_argument("--override", default="")
    version.add_argument("--github-env", type=Path)
    gate = subcommands.add_parser("gate")
    gate.add_argument("--kind", choices=tuple(REQUIRED_JOBS), required=True)
    gate.add_argument("--source-commit", required=True)
    gate.add_argument("--results-env", default="GATE_RESULTS")
    gate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "version":
            selected = resolve_release_version(args.metadata, args.override)
            if args.github_env is not None:
                with args.github_env.open(
                    "a", encoding="utf-8", newline="\n"
                ) as stream:
                    stream.write(f"RELEASE_VERSION={selected}\n")
            print(selected)
        else:
            # Remove stale success evidence before evaluating this attempt.
            args.output.unlink(missing_ok=True)
            encoded = os.environ.get(args.results_env, "")
            if len(encoded) > 65536:
                raise ValueError("Gate result input is too large")
            report = require_successful_jobs(
                json.loads(encoded), args.kind, args.source_commit
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(report, indent=2) + "\n", encoding="utf-8"
            )
            print(f"{args.kind} gate passed for {args.source_commit}")
    except (ValueError, OSError) as error:
        parser.exit(1, f"Release readiness failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
