"""Synthetic shard receipts prove selection coverage, not test execution success."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "pytest_shard_tests", ROOT / "scripts/pytest_shard.py"
)
assert SPEC is not None and SPEC.loader is not None
SHARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SHARD)

NODES = [
    "backend/tests/unit/test_a.py::test_first[a]",
    "backend/tests/unit/test_a.py::test_first[b]",
    "backend/tests/unit/test_b.py::test_second",
    "backend/tests/unit/test_c.py::test_third",
]


def receipts():
    return [SHARD.shard_manifest(NODES, index, 2) for index in range(2)]


def config(index=None, count=None, manifest=None):
    values = {
        "datalab_shard_index": index,
        "datalab_shard_count": count,
        "datalab_shard_manifest": manifest,
    }
    deselected = []
    return SimpleNamespace(
        getoption=values.__getitem__,
        hook=SimpleNamespace(pytest_deselected=lambda items: deselected.extend(items)),
        deselected=deselected,
    )


def test_file_partition_is_reproducible_and_covers_every_case():
    first, second = receipts()
    assert first["selected_node_ids"] == [NODES[0], NODES[1], NODES[3]]
    assert second["selected_node_ids"] == [NODES[2]]
    assert SHARD.shard_manifest(list(reversed(NODES)), 0, 2) == first
    assert SHARD.validate_shard_manifests([second, first]) == {
        "schema_version": 1,
        "status": "passed",
        "shard_count": 2,
        "collected_count": 4,
        "selected_count": 4,
    }


@pytest.mark.parametrize("index,count", [(-1, 2), (2, 2), (0, 0), (True, 2), (0, 1.5), (0, 10**9)])
def test_invalid_shard_bounds_fail(index, count):
    with pytest.raises(ValueError):
        SHARD.shard_manifest(NODES, index, count)


@pytest.mark.parametrize(
    "nodes",
    [
        [],
        [NODES[0], NODES[0]],
        ["/private/test_a.py::x"],
        ["../test_a.py::x"],
        ["C:/private/test_a.py::x"],
        ["backend\\tests\\test_a.py::x"],
    ],
)
def test_empty_duplicate_or_nonportable_collection_fails(nodes):
    with pytest.raises(ValueError):
        SHARD.shard_manifest(nodes, 0, 1)


def test_empty_selected_shard_fails():
    with pytest.raises(ValueError, match="empty"):
        SHARD.shard_manifest(NODES[:1], 1, 2)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "duplicate",
        "collection",
        "overlap",
        "omitted_case",
        "swapped_partition",
        "schema",
        "count",
        "synthetic",
        "selected_duplicate",
        "extra_field",
    ],
)
def test_invalid_or_tampered_receipts_fail(mutation):
    evidence = copy.deepcopy(receipts())
    if mutation == "missing":
        evidence.pop()
    elif mutation == "duplicate":
        evidence[1] = copy.deepcopy(evidence[0])
    elif mutation == "collection":
        evidence[1]["collected_node_ids"].append("backend/tests/unit/test_z.py::test_added")
    elif mutation == "overlap":
        evidence[1]["selected_node_ids"].append(NODES[0])
        evidence[1]["selected_node_ids"].sort()
    elif mutation == "omitted_case":
        evidence[0]["selected_node_ids"].pop()
    elif mutation == "swapped_partition":
        evidence[0]["selected_node_ids"], evidence[1]["selected_node_ids"] = (
            evidence[1]["selected_node_ids"],
            evidence[0]["selected_node_ids"],
        )
    elif mutation == "schema":
        evidence[0]["schema_version"] = True
    elif mutation == "count":
        evidence[0]["shard_count"] = 3
    elif mutation == "synthetic":
        evidence[0]["synthetic"] = False
    elif mutation == "selected_duplicate":
        evidence[0]["selected_node_ids"].append(NODES[0])
    else:
        evidence[0]["extra"] = "not allowed"
    with pytest.raises(ValueError):
        SHARD.validate_shard_manifests(evidence)


def test_no_receipts_fails():
    with pytest.raises(ValueError):
        SHARD.validate_shard_manifests([])


def test_plugin_is_inert_without_explicit_options():
    options = config()
    items = [object(), object()]
    before = items.copy()
    SHARD.pytest_configure(options)
    SHARD.pytest_collection_modifyitems(options, items)
    assert items == before
    assert not options.deselected


@pytest.mark.parametrize(
    "options",
    [
        config(index=0),
        config(count=2),
        config(index=0, count=2),
        config(index=0, count=0, manifest="unused.json"),
    ],
)
def test_plugin_rejects_partial_or_invalid_options(options):
    with pytest.raises(pytest.UsageError):
        SHARD.pytest_configure(options)


def test_plugin_writes_portable_receipt_and_reports_deselection(tmp_path, monkeypatch):
    monkeypatch.setattr(SHARD, "REPO_ROOT", tmp_path)
    manifest = tmp_path / "receipts" / "shard.json"
    options = config(index=0, count=2, manifest=str(manifest))
    items = [
        SimpleNamespace(path=tmp_path / node.split("::")[0], nodeid=node.removeprefix("backend/"))
        for node in NODES
    ]
    SHARD.pytest_configure(options)
    SHARD.pytest_collection_modifyitems(options, items)
    assert [item.nodeid for item in items] == [
        node.removeprefix("backend/") for node in (NODES[0], NODES[1], NODES[3])
    ]
    assert len(options.deselected) == 1
    assert json.loads(manifest.read_text(encoding="utf-8")) == receipts()[0]
    assert str(tmp_path) not in manifest.read_text(encoding="utf-8")


def test_cli_validates_explicit_manifest_paths(tmp_path, capsys):
    paths = []
    for index, receipt in enumerate(receipts()):
        path = tmp_path / f"shard-{index}.json"
        path.write_text(json.dumps(receipt), encoding="utf-8")
        paths.append(str(path))
    assert SHARD.main(["validate", *paths]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "passed"
    assert SHARD.main(["validate", paths[0]]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "failed"
    assert SHARD.main(["validate", paths[0], paths[0]]) == 1
    capsys.readouterr()
    assert SHARD.main(["validate", str(tmp_path / "missing.json")]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "failed"
