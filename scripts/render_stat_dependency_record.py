from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.validate_stat_dependency_smoke import load_payload, validate_payload
except ModuleNotFoundError:
    from validate_stat_dependency_smoke import load_payload, validate_payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render a markdown record from statistical dependency smoke output.",
    )
    parser.add_argument("result_path", type=Path)
    args = parser.parse_args()

    payload = load_payload(args.result_path)
    summary = validate_payload(payload)
    print(render_record(payload, summary, args.result_path))
    return 0


def render_record(
    payload: dict[str, Any],
    summary: dict[str, str],
    result_path: Path,
) -> str:
    smoke_results = payload["smoke_results"]
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "## Recorded Result",
        "",
        f"- Date: {generated_at}",
        "- Windows version: TODO",
        "- Python command: `.\\.venv\\Scripts\\python.exe`",
        f"- Python version: {summary['python_version']}",
        f"- NumPy version: {summary['numpy']}",
        f"- SciPy version: {summary['scipy']}",
        "- Install command: "
        "`powershell -ExecutionPolicy Bypass -File .\\scripts\\install-stat-deps-spike.ps1`",
        "- Smoke command: "
        "`powershell -ExecutionPolicy Bypass -File .\\scripts\\check-stat-deps.ps1`",
        f"- Smoke result file: `{result_path.as_posix()}`",
        "- Smoke result validation: passed",
        "- Full check command: `powershell -ExecutionPolicy Bypass -File .\\scripts\\check.ps1`",
        "- Full check result: TODO",
        "- Wheel-only install confirmed: TODO",
        "- License review: TODO",
        "- Offline runtime note: TODO",
        "- Startup/import time note: TODO",
        "- Known warnings: TODO",
        "- Decision: TODO",
        "",
        "### Smoke Summary",
        "",
        _result_line("Shapiro-Wilk", smoke_results["shapiro"]),
        _anderson_line(smoke_results["anderson_norm"]),
        _result_line("Levene mean", smoke_results["levene_mean"]),
        _result_line("Brown-Forsythe", smoke_results["brown_forsythe"]),
    ]
    return "\n".join(lines)


def _result_line(label: str, result: dict[str, Any]) -> str:
    return (
        f"- {label}: statistic={_format_number(result['statistic'])}, "
        f"pvalue={_format_number(result['pvalue'])}"
    )


def _anderson_line(result: dict[str, Any]) -> str:
    critical_count = len(result["critical_values"])
    return (
        f"- Anderson-Darling normal: statistic={_format_number(result['statistic'])}, "
        f"critical_values={critical_count}"
    )


def _format_number(value: object) -> str:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError("smoke result value must be numeric")
    return f"{float(value):.12g}"


if __name__ == "__main__":
    raise SystemExit(main())
