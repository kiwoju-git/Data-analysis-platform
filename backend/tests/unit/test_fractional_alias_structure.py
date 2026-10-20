from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.statistics.factorial_design import (
    FactorialDesignOptions,
    FactorialFactor,
    fractional_metadata_for,
    generate_two_level_factorial_design,
    list_fractional_factorial_catalog,
)


def test_aliases_use_factor_indices_not_name_delimiters() -> None:
    names = ["온도 × A", "B=* = 이름", "C 공백", "<D>", "I"]
    factors = [FactorialFactor(name=name, low=-1, high=1, unit=None) for name in names]
    entry = next(
        entry for entry in list_fractional_factorial_catalog(5) if entry.base_factor_count == 4
    )
    metadata = fractional_metadata_for(factors, entry.catalog_entry_id)
    labels = [[term.compact_label for term in group] for group in metadata.alias_classes]
    assert labels[0] == ["I", "ABCDE"]
    assert ["A", "BCDE"] in labels
    assert ["AB", "CDE"] in labels
    assert len(metadata.alias_classes) == 16
    all_indices = [term.factor_indices for group in metadata.alias_classes for term in group]
    assert len(all_indices) == len(set(all_indices)) == 32
    for group in metadata.alias_classes:
        for term in group:
            assert term.order == len(term.factor_indices)
            assert term.sign == 1
            assert term.factor_indices == tuple(sorted(term.factor_indices))
            assert term.full_label == (
                " × ".join(names[index] for index in term.factor_indices) or "I"
            )
    # Renaming changes display names, not the structured algebra or ordering.
    renamed = fractional_metadata_for(
        [replace(factor, name=chr(65 + index)) for index, factor in enumerate(factors)],
        entry.catalog_entry_id,
    )
    assert labels == [[term.compact_label for term in group] for group in renamed.alias_classes]


def test_alias_view_is_not_part_of_design_hash_or_run_generation() -> None:
    factors = [
        FactorialFactor(name=chr(65 + index), low=-1, high=1, unit=None) for index in range(4)
    ]
    entry = next(
        entry for entry in list_fractional_factorial_catalog(4) if entry.base_factor_count == 3
    )
    options = FactorialDesignOptions(
        replicates=1,
        center_points=0,
        randomize=False,
        randomization_seed=7,
        design_type="two_level_fractional",
        fraction_id=entry.catalog_entry_id,
    )
    design = generate_two_level_factorial_design(factors, options)
    assert design.fractional is not None
    assert ["AB", "CD"] in [
        [term.compact_label for term in group] for group in design.fractional.alias_classes
    ]
    restored = generate_two_level_factorial_design(factors, options)
    assert design.design_sha256 == restored.design_sha256
    assert design.runs == restored.runs


def test_alias_api_restore_and_visible_report_preserve_names_and_source(tmp_path: Path) -> None:
    names = ["온도 × X", "압력 = <B>", "C * C", "D with spaces", "I"]
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        response = client.post(
            "/api/v1/doe-designs/factorial",
            json={
                "name": "Synthetic alias identity",
                "design_type": "two_level_fractional",
                "fraction_id": "5-factor-half-r5",
                "factors": [{"name": name, "low": -1, "high": 1} for name in names],
                "replicates": 1,
                "center_points": 0,
                "randomize": False,
                "randomization_seed": 7,
                "block_count": 1,
            },
        )
        assert response.status_code == 201, response.text
        original = response.json()
        path = f"/api/v1/doe-designs/{original['design_id']}"
        report = client.get(path + "/report.html")
        assert report.status_code == 200
        assert "I = ABCDE" in report.text
        assert "A = BCDE" in report.text
        assert "AB = CDE" in report.text
        assert "압력 = &lt;B&gt;" in report.text
        assert "<B>" not in report.text
        assert client.get(path).json() == original
        classes = original["fractional"]["alias_classes"]
        assert len(classes) == 16
        assert classes[0][0]["factor_indices"] == []
