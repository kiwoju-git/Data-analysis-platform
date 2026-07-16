from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REQUIRED_LOCK_PACKAGES = {
    "editables": "0.5",
    "fastapi": "0.115.6",
    "hatchling": "1.26.3",
    "httpx": "0.28.1",
    "joblib": "1.5.2",
    "mypy": "1.13.0",
    "numpy": "2.2.6",
    "pip": "26.1.2",
    "playwright": "1.61.0",
    "pydantic-settings": "2.7.0",
    "pytest": "8.3.4",
    "python-multipart": "0.0.32",
    "ruff": "0.8.4",
    "scikit-learn": "1.7.2",
    "scipy": "1.15.3",
    "threadpoolctl": "3.6.0",
    "uvicorn": "0.32.1",
}
ENTRY_PATTERN = re.compile(r"^([a-z0-9][a-z0-9-]*)==([^\s\\]+) \\$", re.ASCII)
HASH_PATTERN = re.compile(r"^    --hash=sha256:([0-9a-f]{64})$", re.ASCII)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the Windows Python hash lock."
    )
    parser.add_argument("lock_path", type=Path)
    args = parser.parse_args()
    packages = validate_lock_text(args.lock_path.read_text(encoding="ascii"))
    print(
        json.dumps(
            {
                "status": "passed",
                "package_count": len(packages),
                "scikit_learn": packages["scikit-learn"]["version"],
                "target": "CPython 3.10 Windows AMD64",
            },
            sort_keys=True,
        )
    )
    return 0


def validate_lock_text(
    text: str,
    required_packages: dict[str, str] | None = None,
) -> dict[str, dict[str, str]]:
    if "# Target: CPython 3.10, Windows AMD64, wheel-only installation." not in text:
        raise ValueError("lock target header is missing")
    if "git+" in text or "http://" in text or "https://" in text or " -e " in text:
        raise ValueError("lock must not contain URLs or editable requirements")

    meaningful = [
        line for line in text.splitlines() if line and not line.startswith("#")
    ]
    if len(meaningful) % 2 != 0:
        raise ValueError(
            "each locked package must have one requirement and one hash line"
        )

    packages: dict[str, dict[str, str]] = {}
    for index in range(0, len(meaningful), 2):
        entry_match = ENTRY_PATTERN.fullmatch(meaningful[index])
        hash_match = HASH_PATTERN.fullmatch(meaningful[index + 1])
        if entry_match is None or hash_match is None:
            raise ValueError(
                "lock entries must use exact versions and one lowercase SHA-256"
            )
        name, version = entry_match.groups()
        if name in packages:
            raise ValueError(f"duplicate locked package: {name}")
        packages[name] = {"version": version, "sha256": hash_match.group(1)}

    if not packages:
        raise ValueError("lock must contain packages")
    expected = (
        REQUIRED_LOCK_PACKAGES if required_packages is None else required_packages
    )
    for name, version in expected.items():
        record = packages.get(name)
        if record is None:
            raise ValueError(f"required locked package is missing: {name}")
        if record["version"] != version:
            raise ValueError(
                f"locked package {name} must be {version}, got {record['version']}"
            )
    return packages


if __name__ == "__main__":
    raise SystemExit(main())
