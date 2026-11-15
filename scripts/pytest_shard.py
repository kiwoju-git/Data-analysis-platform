"""Opt-in file-balanced pytest collection receipts and a coverage-only validator.

The aggregate must separately require every shard job to succeed. A receipt proves
which tests were selected, not that they ran or passed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FIELDS = {
    "schema_version",
    "synthetic",
    "shard_index",
    "shard_count",
    "collected_node_ids",
    "selected_node_ids",
}


def _bounds(index: int, count: int) -> None:
    if type(index) is not int or type(count) is not int or not 0 <= index < count:
        raise ValueError("invalid shard index/count")


def _nodes(values: list[str]) -> list[str]:
    if not isinstance(values, list) or not values:
        raise ValueError("empty or invalid collection")
    for node in values:
        if not isinstance(node, str) or "::" not in node:
            raise ValueError("invalid node ID")
        file, case = node.split("::", 1)
        path = PurePosixPath(file)
        if (
            not case
            or path.is_absolute()
            or "\\" in file
            or ":" in file
            or ".." in path.parts
            or path.as_posix() != file
            or path.suffix != ".py"
        ):
            raise ValueError("node ID must use a repository-relative test path")
    if len(set(values)) != len(values):
        raise ValueError("duplicate node IDs")
    return sorted(values)


def shard_manifest(node_ids: list[str], index: int, count: int) -> dict[str, Any]:
    _bounds(index, count)
    collected = _nodes(node_ids)
    files = sorted({node.split("::", 1)[0] for node in collected})
    if count > len(files):
        raise ValueError("empty selected shard")
    selected_files = set(files[index::count])
    selected = [node for node in collected if node.split("::", 1)[0] in selected_files]
    if not selected:
        raise ValueError("empty selected shard")
    return {
        "schema_version": 1,
        "synthetic": True,
        "shard_index": index,
        "shard_count": count,
        "collected_node_ids": collected,
        "selected_node_ids": selected,
    }


def validate_shard_manifests(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(receipts, list) or not receipts:
        raise ValueError("missing shard receipts")
    collection = None
    shard_count = None
    seen_indices: set[int] = set()
    selected_union: set[str] = set()
    for receipt in receipts:
        if not isinstance(receipt, dict) or set(receipt) != FIELDS:
            raise ValueError("invalid receipt fields")
        if type(receipt["schema_version"]) is not int or receipt["schema_version"] != 1:
            raise ValueError("unsupported receipt schema")
        if receipt["synthetic"] is not True:
            raise ValueError("invalid synthetic metadata")
        index, count = receipt["shard_index"], receipt["shard_count"]
        _bounds(index, count)
        expected = shard_manifest(receipt["collected_node_ids"], index, count)
        if receipt != expected:
            raise ValueError("receipt does not match deterministic file partition")
        if collection is None:
            collection, shard_count = receipt["collected_node_ids"], count
        if receipt["collected_node_ids"] != collection or count != shard_count:
            raise ValueError("shards have different full collections or counts")
        if index in seen_indices:
            raise ValueError("duplicate shard index")
        selected = set(receipt["selected_node_ids"])
        if selected_union & selected:
            raise ValueError("overlapping shard selections")
        seen_indices.add(index)
        selected_union.update(selected)
    assert collection is not None and shard_count is not None
    if seen_indices != set(range(shard_count)):
        raise ValueError("missing shard indices")
    if selected_union != set(collection):
        raise ValueError("incomplete shard coverage")
    return {
        "schema_version": 1,
        "status": "passed",
        "shard_count": shard_count,
        "collected_count": len(collection),
        "selected_count": len(selected_union),
    }


def pytest_addoption(parser: Any) -> None:
    group = parser.getgroup("datalab-sharding")
    group.addoption("--datalab-shard-index", type=int, default=None)
    group.addoption("--datalab-shard-count", type=int, default=None)
    group.addoption("--datalab-shard-manifest", default=None)


def pytest_configure(config: Any) -> None:
    import pytest

    values = tuple(
        config.getoption(f"datalab_shard_{name}")
        for name in ("index", "count", "manifest")
    )
    config._datalab_shard_options = None
    if all(value is None for value in values):
        return
    if any(value is None for value in values):
        raise pytest.UsageError("all three --datalab-shard options are required")
    try:
        _bounds(values[0], values[1])
        if not values[2]:
            raise ValueError("empty manifest path")
    except ValueError as error:
        raise pytest.UsageError(str(error)) from error
    config._datalab_shard_options = values


def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
    import pytest

    options = getattr(config, "_datalab_shard_options", None)
    if options is None:
        return
    index, count, destination = options
    try:
        node_ids = [
            item.path.resolve().relative_to(REPO_ROOT).as_posix()
            + "::"
            + item.nodeid.split("::", 1)[1]
            for item in items
        ]
        receipt = shard_manifest(node_ids, index, count)
        selected_ids = set(receipt["selected_node_ids"])
        selected = [item for item, node in zip(items, node_ids) if node in selected_ids]
        deselected = [
            item for item, node in zip(items, node_ids) if node not in selected_ids
        ]
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
    except (ValueError, IndexError, OSError) as error:
        raise pytest.UsageError(
            "cannot produce a complete portable shard receipt"
        ) from error
    items[:] = selected
    config.hook.pytest_deselected(items=deselected)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("manifests", nargs="+", type=Path)
    args = parser.parse_args(argv)
    try:
        receipts = [
            json.loads(path.read_text(encoding="utf-8")) for path in args.manifests
        ]
        result = validate_shard_manifests(receipts)
    except (OSError, UnicodeError, ValueError):
        print(
            json.dumps(
                {"status": "failed", "error_code": "pytest_shard_manifest_invalid"}
            )
        )
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
