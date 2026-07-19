"""Generate the deterministic, fully synthetic DataLab Studio tutorial data pack."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
import tempfile
from pathlib import Path
from typing import Iterable, Sequence

SEED = 20260718
GENERATOR_VERSION = "1.0.0"
OUTPUT_ROOT = Path(__file__).resolve().parent
TRAINING_COLUMNS = [
    "run_id",
    "timestamp",
    "temperature_c",
    "pressure_bar",
    "cycle_time_s",
    "catalyst_pct",
    "feed_rate_kg_h",
    "material_grade",
    "yield_pct",
    "tensile_strength_mpa",
    "production_line",
    "supplier",
    "pass_flag",
    "inspected_count",
    "defectives_count",
]
PREDICTOR_COLUMNS = [
    "temperature_c",
    "pressure_bar",
    "cycle_time_s",
    "catalyst_pct",
    "feed_rate_kg_h",
    "material_grade",
]


def _rounded(value: float, digits: int = 4) -> float:
    return round(float(value), digits)


def _binomial(rng: random.Random, trials: int, probability: float) -> int:
    return sum(1 for _ in range(trials) if rng.random() < probability)


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _csv_bytes(
    columns: Sequence[str],
    rows: Iterable[dict[str, object]],
    *,
    delimiter: str = ",",
) -> bytes:
    from io import StringIO

    stream = StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=list(columns),
        delimiter=delimiter,
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _training_rows() -> list[dict[str, object]]:
    rng = random.Random(SEED)
    rows: list[dict[str, object]] = []
    grades = ["A", "B", "C"]
    lines = ["Line-A", "Line-B", "Line-C"]
    suppliers = ["Supplier-1", "Supplier-2"]
    for index in range(240):
        temperature = rng.uniform(60.0, 90.0)
        pressure = rng.uniform(5.0, 15.0)
        cycle_time = rng.uniform(30.0, 90.0)
        catalyst = rng.uniform(0.5, 2.5)
        feed_rate = rng.uniform(80.0, 140.0)
        grade = grades[index % len(grades)]
        line = lines[(index // 3) % len(lines)]
        supplier = suppliers[(index // 9) % len(suppliers)]
        t = (temperature - 75.0) / 10.0
        p = (pressure - 10.0) / 3.0
        c = (catalyst - 1.5) / 0.5
        cycle = (cycle_time - 60.0) / 20.0
        feed = (feed_rate - 110.0) / 20.0
        line_effect = {"Line-A": 1.2, "Line-B": 0.0, "Line-C": -1.1}[line]
        supplier_effect = {"Supplier-1": 1.15, "Supplier-2": -1.15}[supplier]
        yield_value = (
            82.0
            + 3.1 * t
            + 2.0 * p
            + 1.55 * c
            + 0.45 * cycle
            - 0.35 * feed
            - 2.15 * t * t
            - 0.85 * p * p
            + 1.35 * t * p
            + line_effect
            + supplier_effect
            + rng.gauss(0.0, 2.15)
        )
        grade_effect = {"A": 5.0, "B": 0.0, "C": -4.0}[grade]
        tensile = (
            430.0
            + 8.0 * p
            - 7.0 * cycle
            + 2.5 * feed
            + grade_effect
            + 1.4 * t
            + rng.gauss(0.0, 8.5)
        )
        inspected = rng.randint(85, 135)
        # The tutorial baseline is intentionally stable and promotable to frozen
        # Phase II limits. Bounded deterministic count variation avoids embedding a
        # known Phase I special-cause signal in the training exercise.
        defectives = max(
            0, min(inspected, round(inspected * 0.06) + (index * 7 % 5) - 2)
        )
        pass_flag = (
            "Pass"
            if yield_value >= 77.0 and defectives / inspected <= 0.075
            else "Fail"
        )
        rows.append(
            {
                "run_id": f"SYN-{index + 1:04d}",
                "timestamp": f"2026-01-{1 + index // 24:02d}T{index % 24:02d}:00:00",
                "temperature_c": _rounded(temperature, 3),
                "pressure_bar": _rounded(pressure, 3),
                "cycle_time_s": _rounded(cycle_time, 3),
                "catalyst_pct": _rounded(catalyst, 4),
                "feed_rate_kg_h": _rounded(feed_rate, 3),
                "material_grade": grade,
                "yield_pct": _rounded(max(55.0, min(96.0, yield_value)), 4),
                "tensile_strength_mpa": _rounded(tensile, 4),
                "production_line": line,
                "supplier": supplier,
                "pass_flag": pass_flag,
                "inspected_count": inspected,
                "defectives_count": defectives,
            }
        )
    return rows


def _prediction_rows() -> list[dict[str, object]]:
    rng = random.Random(SEED + 1)
    rows: list[dict[str, object]] = []
    grades = ["A", "B", "C"]
    for index in range(48):
        temperature = rng.uniform(62.0, 88.0)
        pressure = rng.uniform(5.5, 14.5)
        cycle_time = rng.uniform(34.0, 86.0)
        catalyst = rng.uniform(0.65, 2.35)
        feed_rate = rng.uniform(84.0, 136.0)
        if index == 3:
            temperature = 94.0
        elif index == 14:
            pressure = 16.5
        elif index == 27:
            catalyst = 0.25
        elif index == 41:
            feed_rate = 148.0
        inspected = rng.randint(90, 130)
        rows.append(
            {
                "temperature_c": _rounded(temperature, 3),
                "pressure_bar": _rounded(pressure, 3),
                "cycle_time_s": _rounded(cycle_time, 3),
                "catalyst_pct": _rounded(catalyst, 4),
                "feed_rate_kg_h": _rounded(feed_rate, 3),
                "material_grade": grades[index % 3],
                "inspected_count": inspected,
                "defectives_count": _binomial(
                    rng, inspected, 0.035 + 0.005 * (index % 3)
                ),
            }
        )
    return rows


def _invalid_prediction_rows() -> list[dict[str, object]]:
    return [
        {
            "temperature_c": 75.0,
            "pressure_bar": 10.0,
            "cycle_time_s": 55.0,
            "catalyst_pct": 1.4,
            "material_grade": "D",
            "inspected_count": 100,
            "defectives_count": 4,
        },
        {
            "temperature_c": 76.0,
            "pressure_bar": "not-a-number",
            "cycle_time_s": 58.0,
            "catalyst_pct": 1.5,
            "material_grade": "A",
            "inspected_count": 100,
            "defectives_count": 3,
        },
        {
            "temperature_c": 74.0,
            "pressure_bar": 9.5,
            "cycle_time_s": 60.0,
            "catalyst_pct": "",
            "material_grade": "B",
            "inspected_count": 100,
            "defectives_count": 2,
        },
    ]


def _gage_rows() -> list[dict[str, object]]:
    rng = random.Random(SEED + 2)
    rows: list[dict[str, object]] = []
    operators = ["Operator-A", "Operator-B", "Operator-C"]
    operator_effects = {"Operator-A": -0.75, "Operator-B": 0.05, "Operator-C": 0.7}
    for part_index in range(10):
        part_value = 98.0 + 2.2 * part_index + rng.gauss(0.0, 0.35)
        for operator_index, operator in enumerate(operators):
            for replicate in (1, 2):
                interaction = 0.32 * math.sin((part_index + 1) * (operator_index + 1))
                rows.append(
                    {
                        "part_id": f"Part-{part_index + 1:02d}",
                        "operator_id": operator,
                        "replicate": replicate,
                        "measurement_mpa": _rounded(
                            part_value
                            + operator_effects[operator]
                            + interaction
                            + rng.gauss(0.0, 0.24),
                            4,
                        ),
                    }
                )
    return rows


def _factorial_rows() -> list[dict[str, object]]:
    rng = random.Random(SEED + 3)
    rows: list[dict[str, object]] = []
    run_order = 0
    for replicate in (1, 2):
        for temperature_code in (-1, 1):
            for pressure_code in (-1, 1):
                for catalyst_code in (-1, 1):
                    run_order += 1
                    response = (
                        84.0
                        + 3.2 * temperature_code
                        + 2.0 * pressure_code
                        + 0.45 * catalyst_code
                        + 1.7 * temperature_code * pressure_code
                        + rng.gauss(0.0, 0.45)
                    )
                    rows.append(
                        {
                            "run_order": run_order,
                            "replicate": replicate,
                            "temperature_c": 68.0 if temperature_code == -1 else 84.0,
                            "pressure_bar": 7.0 if pressure_code == -1 else 13.0,
                            "catalyst_pct": 0.8 if catalyst_code == -1 else 2.2,
                            "response_yield_pct": _rounded(response, 4),
                        }
                    )
    return rows


def _rsm_rows() -> list[dict[str, object]]:
    rng = random.Random(SEED + 4)
    coded_points = [
        (-1.0, -1.0),
        (-1.0, 1.0),
        (1.0, -1.0),
        (1.0, 1.0),
        (-1.0, 0.0),
        (1.0, 0.0),
        (0.0, -1.0),
        (0.0, 1.0),
        (0.0, 0.0),
        (0.0, 0.0),
        (0.0, 0.0),
        (0.0, 0.0),
        (0.0, 0.0),
    ]
    center_noise = iter([-0.24, 0.12, 0.18, -0.09, 0.03])
    rows: list[dict[str, object]] = []
    for index, (temperature_code, pressure_code) in enumerate(coded_points, start=1):
        noise = (
            next(center_noise)
            if temperature_code == pressure_code == 0.0
            else rng.gauss(0.0, 0.14)
        )
        response = (
            91.0
            - 4.0 * (temperature_code - 0.15) ** 2
            - 3.0 * (pressure_code + 0.10) ** 2
            + 0.8 * temperature_code * pressure_code
            + noise
        )
        rows.append(
            {
                "run_order": index,
                "temperature_c": _rounded(75.0 + 10.0 * temperature_code, 3),
                "pressure_bar": _rounded(10.0 + 4.0 * pressure_code, 3),
                "response_yield_pct": _rounded(response, 4),
            }
        )
    return rows


def _counter_uniform(seed: int, attempt: int, factor_order: int) -> float:
    digest = hashlib.sha256(f"{seed}:{attempt}:{factor_order}".encode("ascii")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False) / 2**64


def _bayesian_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for attempt in range(1, 6):
        temperature = 60.0 + 30.0 * _counter_uniform(SEED, attempt, 1)
        pressure = 5.0 + 10.0 * _counter_uniform(SEED, attempt, 2)
        t = (temperature - 77.0) / 7.0
        p = (pressure - 11.0) / 3.0
        objective = 89.0 - 3.2 * t * t - 2.4 * p * p + 0.55 * t * p
        rows.append(
            {
                "trial_number": attempt,
                "temperature_c": _rounded(temperature, 8),
                "pressure_bar": _rounded(pressure, 8),
                "objective_yield_pct": _rounded(objective, 8),
            }
        )
    return rows


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _manifest_entry(
    path: str,
    content: bytes,
    *,
    row_count: int,
    column_count: int,
    delimiter: str,
    intended_use: str,
) -> dict[str, object]:
    return {
        "relative_path": path,
        "sha256": _sha256(content),
        "row_count": row_count,
        "column_count": column_count,
        "delimiter": "tab" if delimiter == "\t" else delimiter,
        "encoding": "utf-8",
        "line_ending": "LF",
        "intended_tutorial_use": intended_use,
    }


def generate() -> dict[str, object]:
    training = _training_rows()
    prediction = _prediction_rows()
    invalid_prediction = _invalid_prediction_rows()
    gage = _gage_rows()
    factorial = _factorial_rows()
    rsm = _rsm_rows()
    bayesian = _bayesian_rows()
    file_specs = [
        (
            "studio_process_training.csv",
            TRAINING_COLUMNS,
            training,
            ",",
            "upload, schema, EDA, inference, regression, and quality tutorials",
        ),
        (
            "studio_process_paste_60.tsv",
            TRAINING_COLUMNS,
            training[:60],
            "\t",
            "exact-text paste staging and parsing confirmation tutorial",
        ),
        (
            "studio_process_prediction.csv",
            [*PREDICTOR_COLUMNS, "inspected_count", "defectives_count"],
            prediction,
            ",",
            "compatible prediction target and Phase II monitoring tutorial",
        ),
        (
            "studio_process_prediction_invalid.csv",
            [
                "temperature_c",
                "pressure_bar",
                "cycle_time_s",
                "catalyst_pct",
                "material_grade",
                "inspected_count",
                "defectives_count",
            ],
            invalid_prediction,
            ",",
            "prediction preflight troubleshooting only",
        ),
        (
            "studio_gage_rr.csv",
            ["part_id", "operator_id", "replicate", "measurement_mpa"],
            gage,
            ",",
            "balanced crossed Gage R&R tutorial",
        ),
        (
            "studio_factorial_responses.csv",
            [
                "run_order",
                "replicate",
                "temperature_c",
                "pressure_bar",
                "catalyst_pct",
                "response_yield_pct",
            ],
            factorial,
            ",",
            "three-factor replicated full-factorial response-entry tutorial",
        ),
        (
            "studio_rsm_responses.csv",
            ["run_order", "temperature_c", "pressure_bar", "response_yield_pct"],
            rsm,
            ",",
            "two-factor face-centered CCD and Response Optimizer tutorial",
        ),
        (
            "studio_bayesian_observations.csv",
            ["trial_number", "temperature_c", "pressure_bar", "objective_yield_pct"],
            bayesian,
            ",",
            "manual Bayesian initial observations and recommendation tutorial",
        ),
    ]
    generated: dict[str, bytes] = {}
    entries: list[dict[str, object]] = []
    for path, columns, rows, delimiter, use in file_specs:
        content = _csv_bytes(columns, rows, delimiter=delimiter)
        generated[path] = content
        entries.append(
            _manifest_entry(
                path,
                content,
                row_count=len(rows),
                column_count=len(columns),
                delimiter=delimiter,
                intended_use=use,
            )
        )

    training_predictors = set(PREDICTOR_COLUMNS)
    if not training_predictors.issubset(
        training[0]
    ) or not training_predictors.issubset(prediction[0]):
        raise RuntimeError("training and prediction predictor schemas do not match")
    if any(row["material_grade"] not in {"A", "B", "C"} for row in prediction):
        raise RuntimeError("compatible prediction target contains an unseen category")
    if (
        invalid_prediction[0]["material_grade"] != "D"
        or "feed_rate_kg_h" in invalid_prediction[0]
    ):
        raise RuntimeError(
            "invalid prediction target no longer contains the intended errors"
        )

    generator_sha = _sha256(Path(__file__).read_bytes())
    manifest = {
        "manifest_schema_version": 1,
        "generator_version": GENERATOR_VERSION,
        "generator_file_sha256": generator_sha,
        "seed": SEED,
        "generation_marker": "deterministic-seed-20260718",
        "synthetic_data_statement": (
            "All records are deterministic synthetic examples and contain no real person, "
            "company, product, equipment, or production data."
        ),
        "columns": {
            "predictors_x": PREDICTOR_COLUMNS,
            "responses_y": ["yield_pct", "tensile_strength_mpa"],
            "supporting": [
                "run_id",
                "timestamp",
                "production_line",
                "supplier",
                "pass_flag",
                "inspected_count",
                "defectives_count",
            ],
        },
        "formula_descriptions": {
            "yield_pct": (
                "Seeded noisy response with temperature, pressure, catalyst, cycle/feed, "
                "temperature/pressure quadratic terms, temperature-by-pressure interaction, "
                "line, and supplier effects."
            ),
            "tensile_strength_mpa": (
                "Seeded noisy response with pressure, cycle time, feed rate, material grade, "
                "and a small temperature effect."
            ),
            "factorial_response": (
                "Replicated coded response with temperature and pressure main effects and a "
                "temperature-by-pressure interaction."
            ),
            "rsm_response": (
                "Noisy full-quadratic response with an interior stationary point in a "
                "two-factor face-centered CCD."
            ),
            "bayesian_objective": (
                "Deterministic bounded two-factor quadratic objective used only as manually "
                "entered synthetic observations."
            ),
        },
        "files": entries,
    }
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    for path, content in generated.items():
        _atomic_write(OUTPUT_ROOT / path, content)
    _atomic_write(OUTPUT_ROOT / "tutorial_data_manifest.json", manifest_bytes)
    return manifest


if __name__ == "__main__":
    result = generate()
    print(
        f"Generated {len(result['files'])} deterministic tutorial files with seed {SEED}."
    )
