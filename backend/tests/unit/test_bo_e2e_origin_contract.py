"""Manual Playwright API writes must obey the real same-origin dev proxy guard."""

from __future__ import annotations

import ast
from pathlib import Path


def _missing_origins(source: str) -> list[int]:
    missing = []
    for node in ast.walk(ast.parse(source)):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "request"
        ):
            continue
        method = node.func.attr
        if method == "fetch":
            value = next((item.value for item in node.keywords if item.arg == "method"), None)
            if value is None or isinstance(value, ast.Constant) and value.value in {"GET", "HEAD"}:
                continue
        elif method not in {"post", "put", "patch", "delete"}:
            continue
        headers = next((item.value for item in node.keywords if item.arg == "headers"), None)
        if not isinstance(headers, ast.Dict) or not any(
            isinstance(key, ast.Constant)
            and key.value == "Origin"
            and isinstance(value, ast.Name)
            and value.id == "base"
            for key, value in zip(headers.keys, headers.values, strict=True)
        ):
            missing.append(node.lineno)
    return missing


def test_bo_manual_api_mutations_have_explicit_same_origin() -> None:
    directory = Path(__file__).resolve().parents[3] / "tests" / "e2e"
    paths = sorted(directory.glob("bo*.py"))
    assert {path.stem for path in paths} >= {
        "bo_progress",
        "bo_vector_history",
        "bo_desirability_review",
        "bo_persistent_planning",
        "bo_augmentation",
        "bo_mixed_workflow",
        "bo_target_curve_preview",
        "bo_target_curve_recommendation",
    }
    failures = {
        path.name: lines
        for path in paths
        if (lines := _missing_origins(path.read_text(encoding="utf-8")))
    }
    assert failures == {}, f"Manual BO API writes lack exact Origin=base: {failures}"


def test_origin_ast_guard_rejects_missing_or_unbound_mutation_headers() -> None:
    for source in (
        "page.request.post(url, data=fixture)",
        "page.request.put(url, headers={'Origin': 'http://localhost:8600'})",
        "context.request.delete(url, headers=shared_headers)",
        "page.request.fetch(url, method='PATCH')",
    ):
        assert _missing_origins(source) == [1]
    for method in ("post", "put", "patch", "delete"):
        assert (
            _missing_origins(
                f"page.request.{method}(url, data=fixture, headers={{'Origin': base}})"
            )
            == []
        )


def test_origin_ast_guard_leaves_browser_route_replays_and_reads_alone() -> None:
    assert (
        _missing_origins(
            "route.fetch()\nheld[0].fetch()\npage.request.get(url)\n"
            "page.request.fetch(url, method='GET')\npage.request.head(url)"
        )
        == []
    )
