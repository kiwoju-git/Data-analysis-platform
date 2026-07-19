from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


@pytest.mark.parametrize("relative_readme", [Path("README.md"), Path("backend/README.md")])
def test_repository_readme_relative_links_exist(relative_readme: Path) -> None:
    readme = REPOSITORY_ROOT / relative_readme
    missing: list[str] = []
    for raw_target in MARKDOWN_LINK_PATTERN.findall(readme.read_text(encoding="utf-8")):
        target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
        parsed = urlsplit(target)
        if parsed.scheme or target.startswith("#"):
            continue
        relative_target = Path(*PurePosixPath(unquote(parsed.path)).parts)
        resolved = (readme.parent / relative_target).resolve()
        try:
            resolved.relative_to(REPOSITORY_ROOT)
        except ValueError:
            missing.append(f"{target} (outside repository)")
            continue
        if not resolved.exists():
            missing.append(target)

    assert missing == [], f"Missing relative Markdown links in {relative_readme}: {missing}"
