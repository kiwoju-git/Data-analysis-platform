from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from app.analyses.registry import METHOD_VERSIONS

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TUTORIAL_ROOT = REPOSITORY_ROOT / "examples" / "tutorial"
GENERATOR_PATH = TUTORIAL_ROOT / "generate_studio_tutorial_data.py"
EXPECTED_RESULTS_PATH = TUTORIAL_ROOT / "tutorial_expected_results.json"
MANIFEST_PATH = TUTORIAL_ROOT / "tutorial_data_manifest.json"
TUTORIAL_PATH = REPOSITORY_ROOT / "docs" / "studio_end_to_end_tutorial_ko.md"
TUTORIAL_RENDERER_PATH = REPOSITORY_ROOT / "scripts" / "render_tutorial_results.py"


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
    payload = json.loads(EXPECTED_RESULTS_PATH.read_text(encoding="utf-8"))
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


def test_tutorial_expected_versions_and_input_hashes_match_sources() -> None:
    payload = json.loads(EXPECTED_RESULTS_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    input_hashes = {item["sha256"] for item in manifest["files"]}

    for method_id, section in payload["results"].items():
        assert section["method_id"] == method_id
        assert section["method_version"] == METHOD_VERSIONS[method_id]
        assert section["input_file_sha256"] in input_hashes


def test_tutorial_markdown_result_blocks_are_in_sync() -> None:
    completed = subprocess.run(
        [sys.executable, str(TUTORIAL_RENDERER_PATH), "--check"],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Verified 18 tutorial result blocks." in completed.stdout


def test_tutorial_markdown_drift_reports_method_and_field_paths(tmp_path: Path) -> None:
    drifted_tutorial = tmp_path / "tutorial.md"
    text = TUTORIAL_PATH.read_text(encoding="utf-8")
    assert "mean=80.3656" in text
    drifted_tutorial.write_text(
        text.replace("mean=80.3656", "mean=80.0000", 1),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(TUTORIAL_RENDERER_PATH),
            "--check",
            "--tutorial-path",
            str(drifted_tutorial),
        ],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "eda.descriptive" in completed.stderr
    assert "result.yield_pct" in completed.stderr


def test_tutorial_uses_current_korean_module_labels() -> None:
    text = TUTORIAL_PATH.read_text(encoding="utf-8")
    required_labels = {
        "탐색적 분석",
        "가설 검정",
        "범주형 데이터 분석",
        "상관관계 및 회귀분석",
        "품질 관리",
        "실험 계획법",
    }
    stale_labels = {
        "가설검정",
        "범주형 분석",
        "상관관계 및 회귀`",
        "품질 분석",
        "실험계획법",
    }

    assert required_labels <= set(text.split("`")) | {
        label for label in required_labels if label in text
    }
    for label in stale_labels:
        assert label not in text
