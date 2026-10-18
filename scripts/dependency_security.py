"""Audit installed, hash-locked dependencies, never application data or editable code."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

AUDITOR_VERSION = "2.10.1"


def canonical_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def validate_python_report(report: dict, inventory: dict[str, str]) -> None:
    dependencies = report.get("dependencies", [])
    actual = {}
    for item in dependencies:
        if "skip_reason" in item or "version" not in item:
            raise ValueError("An installed dependency was not audited")
        name = canonical_name(item["name"])
        if name in actual:
            raise ValueError("Duplicate audited dependency")
        actual[name] = item["version"]
    if not actual or actual != inventory:
        raise ValueError("Audited dependencies do not match the installed inventory")
    if any(item.get("vulns") for item in dependencies):
        raise ValueError("Dependency advisories require remediation")


def validate_npm_report(report: dict) -> None:
    if report.get("auditReportVersion") != 2 or report.get("error"):
        raise ValueError("npm audit did not produce a supported report")
    metadata = report.get("metadata", {})
    if metadata.get("dependencies", {}).get("total", 0) <= 0:
        raise ValueError("npm audit returned an empty inventory")
    if metadata.get("vulnerabilities", {}).get("total") != 0 or report.get(
        "vulnerabilities"
    ):
        raise ValueError("npm dependency advisories require remediation")


def execute(
    command: list[str], output: Path, *, cwd: Path | None = None
) -> subprocess.CompletedProcess:
    result = subprocess.run(
        command, cwd=cwd, capture_output=True, text=True, encoding="utf-8"
    )
    output.with_suffix(".stdout.log").write_text(result.stdout, encoding="utf-8")
    output.with_suffix(".stderr.log").write_text(result.stderr, encoding="utf-8")
    return result


def audit_python(
    target: Path, auditor: Path, lock: Path, output: Path, profile: str
) -> None:
    probe = execute(
        [
            str(target),
            "-c",
            (
                "import importlib.metadata as m,json,platform,sys,sysconfig; "
                "print(json.dumps({'python':sys.version,'os':platform.system(),"
                "'architecture':platform.machine(),'paths':sorted(set([sysconfig.get_path('purelib'),"
                "sysconfig.get_path('platlib')])),'packages':"
                "{d.metadata['Name']:d.version for d in m.distributions()}}))"
            ),
        ],
        output / "inventory",
    )
    probe.check_returncode()
    environment = json.loads(probe.stdout)
    inventory = {canonical_name(k): v for k, v in environment["packages"].items()}
    pins = {
        canonical_name(name): version
        for name, version in re.findall(
            r"^([\w.-]+)==([^\s\\]+)", lock.read_text("ascii"), re.M
        )
    }
    if not inventory or inventory != pins:
        raise ValueError(
            "Target must contain exactly the selected hash lock; no editable app"
        )
    check = execute([str(target), "-m", "pip", "check"], output / "pip-check")
    check.check_returncode()
    tool = execute(
        [
            str(auditor),
            "-c",
            "import importlib.metadata as m; print(m.version('pip-audit'))",
        ],
        output / "auditor-version",
    )
    tool.check_returncode()
    if tool.stdout.strip() != AUDITOR_VERSION:
        raise ValueError("Unexpected pip-audit version")
    tools = execute(
        [str(auditor), "-m", "pip", "list", "--format=json"],
        output / "auditor-inventory",
    )
    tools.check_returncode()
    report_path = output / "python-audit.json"
    command = [
        str(auditor),
        "-m",
        "pip_audit",
        "--strict",
        "--progress-spinner",
        "off",
        "--timeout",
        "30",
        "--vulnerability-service",
        "pypi",
        "--format",
        "json",
        "--output",
        str(report_path),
    ]
    for path in environment["paths"]:
        command.extend(["--path", path])
    result = execute(command, output / "python-audit")
    manifest = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "lock": lock.name,
        "lock_sha256": hashlib.sha256(lock.read_bytes()).hexdigest(),
        "auditor": f"pip-audit=={AUDITOR_VERSION}",
        "service": "pypi",
        "python": environment["python"],
        "os": environment["os"],
        "architecture": environment["architecture"],
        "packages": inventory,
        "exit_code": result.returncode,
    }
    (output / "python-environment.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    result.check_returncode()
    validate_python_report(json.loads(report_path.read_text("utf-8")), inventory)


def audit_npm(frontend: Path, output: Path) -> None:
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if npm is None:
        raise ValueError("npm is required for the development dependency audit")
    failures = []
    for profile, arguments in (("runtime", ["--omit=dev"]), ("all", [])):
        result = execute(
            [npm, "audit", "--json", *arguments],
            output / f"npm-{profile}",
            cwd=frontend,
        )
        (output / f"npm-{profile}.json").write_text(result.stdout, encoding="utf-8")
        try:
            result.check_returncode()
            validate_npm_report(json.loads(result.stdout))
        except (ValueError, subprocess.CalledProcessError) as error:
            failures.append(f"{profile}: {type(error).__name__}")
    if failures:
        raise ValueError("npm audit failed: " + ", ".join(failures))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-python", type=Path)
    parser.add_argument("--audit-python", type=Path)
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--profile", choices=["runtime", "dev"], default="dev")
    parser.add_argument("--frontend", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.frontend:
        audit_npm(args.frontend.resolve(), args.output_dir.resolve())
    else:
        if not all([args.target_python, args.audit_python, args.lock]):
            parser.error(
                "Python audits require --target-python, --audit-python and --lock"
            )
        audit_python(
            args.target_python.resolve(),
            args.audit_python.resolve(),
            args.lock.resolve(),
            args.output_dir.resolve(),
            args.profile,
        )
    print("Dependency security checks passed for the recorded scope.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
