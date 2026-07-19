from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TUTORIAL_ROOT = REPOSITORY_ROOT / "examples" / "tutorial"
GENERATOR_PATH = TUTORIAL_ROOT / "generate_studio_tutorial_data.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location("studio_tutorial_generator", GENERATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_tutorial_generator_is_deterministic_and_atomic(tmp_path: Path) -> None:
    generator = _load_generator()
    generator.OUTPUT_ROOT = tmp_path
    first_manifest = generator.generate()
    first_hashes = {
        item["relative_path"]: _sha256(tmp_path / item["relative_path"])
        for item in first_manifest["files"]
    }
    second_manifest = generator.generate()
    second_hashes = {
        item["relative_path"]: _sha256(tmp_path / item["relative_path"])
        for item in second_manifest["files"]
    }

    assert first_hashes == second_hashes
    assert first_manifest == second_manifest
    assert not [path for path in tmp_path.iterdir() if path.name.startswith(".")]


def test_tutorial_manifest_matches_committed_files_and_shapes() -> None:
    manifest = json.loads(
        (TUTORIAL_ROOT / "tutorial_data_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["seed"] == 20260718
    assert manifest["generator_file_sha256"] == _sha256(GENERATOR_PATH)
    assert "synthetic" in manifest["synthetic_data_statement"].lower()
    expected_shapes = {
        "studio_process_training.csv": (240, 15),
        "studio_process_paste_60.tsv": (60, 15),
        "studio_process_prediction.csv": (48, 8),
        "studio_process_prediction_invalid.csv": (3, 7),
        "studio_gage_rr.csv": (60, 4),
        "studio_factorial_responses.csv": (16, 6),
        "studio_rsm_responses.csv": (13, 4),
        "studio_bayesian_observations.csv": (5, 4),
    }
    for item in manifest["files"]:
        path = TUTORIAL_ROOT / item["relative_path"]
        delimiter = "\t" if item["delimiter"] == "tab" else item["delimiter"]
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle, delimiter=delimiter))
        assert path.is_file()
        assert item["sha256"] == _sha256(path)
        assert (len(rows) - 1, len(rows[0])) == expected_shapes[item["relative_path"]]
        assert (item["row_count"], item["column_count"]) == expected_shapes[item["relative_path"]]


def test_tutorial_expected_results_are_api_normalized_and_identifier_free() -> None:
    payload = json.loads(
        (TUTORIAL_ROOT / "tutorial_expected_results.json").read_text(encoding="utf-8")
    )
    expected_method_ids = {
        "eda.descriptive",
        "eda.graphical_summary",
        "hypothesis.two_sample_t",
        "hypothesis.one_way_anova",
        "categorical.one_proportion",
        "categorical.chi_square_association",
        "regression.pearson",
        "regression.xy_correlation",
        "regression.linear_model",
        "regression.predict",
        "quality.run_chart",
        "quality.capability",
        "quality.attribute_control_chart",
        "quality.gage_rr",
        "doe.factorial_design",
        "doe.response_surface",
        "regression.response_optimizer",
        "doe.bayesian_optimization",
    }
    assert payload["generated_by"] == "DataLab Studio API tutorial smoke"
    assert payload["dynamic_ids_and_timestamps_omitted"] is True
    assert set(payload["results"]) == expected_method_ids
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    assert str(REPOSITORY_ROOT) not in serialized
    assert "analysis_id" not in serialized
    assert "model_id" not in serialized
    assert "study_id" not in serialized
