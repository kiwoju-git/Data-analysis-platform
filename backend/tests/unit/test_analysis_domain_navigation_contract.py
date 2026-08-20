from __future__ import annotations

import re
from pathlib import Path

from app.analyses.registry import METHODS


def test_frontend_analysis_domains_cover_current_registry_exactly_once() -> None:
    source = (
        Path(__file__).resolve().parents[3] / "frontend" / "src" / "analysisDomains.ts"
    ).read_text(encoding="utf-8")
    blocks = re.findall(
        r"(?:methodIds|contextualMethodIds|directMethodIds|directContextualMethodIds):\s*\[(.*?)\]",
        source,
        flags=re.DOTALL,
    )
    mapped_ids = re.findall(r'"([a-z][a-z0-9_]*\.[a-z0-9_]+)"', "\n".join(blocks))
    registry_ids = [method.method_id for method in METHODS]

    assert len(mapped_ids) == len(set(mapped_ids)), "domain mapping contains duplicate method IDs"
    assert set(mapped_ids) == set(registry_ids)
