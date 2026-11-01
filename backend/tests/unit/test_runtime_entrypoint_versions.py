"""Cross-platform source checks; executing PowerShell remains a Windows test."""

import re
from pathlib import Path

from app.core.runtime_contract import API_CONTRACT_VERSION


def _declared_integer(path: Path, pattern: str) -> int:
    match = re.search(pattern, path.read_text(encoding="utf-8"), re.MULTILINE)
    assert match is not None, f"Missing version declaration in {path.name}"
    return int(match.group(1))


def test_backend_frontend_and_windows_launcher_require_same_api_contract() -> None:
    root = Path(__file__).resolve().parents[3]
    frontend = _declared_integer(
        root / "frontend/src/runtimeCompatibility.ts",
        r"^export const EXPECTED_API_CONTRACT_VERSION = (\d+);$",
    )
    launcher = _declared_integer(
        root / "scripts/dev_runtime_helpers.ps1",
        r"^\$script:ExpectedApiContractVersion = (\d+)$",
    )
    assert frontend == launcher == API_CONTRACT_VERSION


def test_frontend_and_windows_launcher_keep_metadata24_minimum() -> None:
    root = Path(__file__).resolve().parents[3]
    frontend = _declared_integer(
        root / "frontend/src/runtimeCompatibility.ts",
        r"^export const MINIMUM_METADATA_SCHEMA_VERSION = (\d+);$",
    )
    launcher = _declared_integer(
        root / "scripts/dev_runtime_helpers.ps1",
        r"^\$script:MinimumMetadataSchemaVersion = (\d+)$",
    )
    assert frontend == launcher == 24
