import json
import random
from math import floor, sqrt

import numpy as np
import pytest
from scipy import stats

from app.statistics.gage_rr import GageRrError, calculate_gage_rr_anova
from app.statistics.gage_rr_preflight import GageRrColumn, calculate_gage_rr_preflight


def column(name, index):
    return GageRrColumn(
        name,
        index,
        name,
        "decimal" if index == 2 else "text",
        "continuous" if index == 2 else "nominal",
        "response" if index == 2 else "group",
        None,
    )


def fixture(interaction=0.01):
    return [
        [
            f"part-{part}",
            f"operator-{operator}",
            str(100 + 2 * part + operator + interaction * (part - 4.5) * (operator - 1) + error),
            f"cell-{part}-{operator}-{repeat}",
        ]
        for part in range(10)
        for operator in range(3)
        for repeat, error in enumerate((-0.2, 0.2))
    ]


def run(rows, explicit=False, policy="auto_pool"):
    return calculate_gage_rr_anova(
        rows,
        measurement_column=column("measurement", 2),
        part_column=column("part", 0),
        operator_column=column("operator", 1),
        replicate_column=column("repeat", 3) if explicit else None,
        replicate_mode="explicit_column" if explicit else "infer_from_rows",
        interaction_policy=policy,
    )


def preflight(rows, explicit=False):
    return calculate_gage_rr_preflight(
        rows,
        measurement_column=column("measurement", 2),
        part_column=column("part", 0),
        operator_column=column("operator", 1),
        replicate_column=column("repeat", 3) if explicit else None,
    )


@pytest.mark.parametrize("strength,pooled", [(0.01, True), (1, False)])
def test_full_and_selected_anova_match_independent_balanced_array_calculation(strength, pooled):
    rows = fixture(strength)
    result = run(rows)
    y = np.asarray([float(row[2]) for row in rows]).reshape(10, 3, 2)
    grand = y.mean()
    part = y.mean(axis=(1, 2))
    operator = y.mean(axis=(0, 2))
    cells = y.mean(axis=2)
    ss = [
        6 * np.sum((part - grand) ** 2),
        20 * np.sum((operator - grand) ** 2),
        2 * np.sum((cells - part[:, None] - operator[None, :] + grand) ** 2),
        np.sum((y - cells[:, :, None]) ** 2),
    ]
    df = [9, 2, 18, 30]
    ms = np.asarray(ss) / df
    full = result["full_anova_table"]
    assert [row["sum_of_squares"] for row in full[:4]] == pytest.approx(ss, abs=1e-10)
    assert sum(row["degrees_of_freedom"] for row in full[:4]) == 59
    assert sum(row["sum_of_squares"] for row in full[:4]) == pytest.approx(
        full[-1]["sum_of_squares"], abs=1e-10
    )
    assert result["interaction_selection"]["pooled"] is pooled
    assert result["interaction_selection"]["interaction_p_value"] == pytest.approx(
        stats.f.sf(ms[2] / ms[3], 18, 30)
    )
    final = {row["source"]: row for row in result["anova_table"]}
    error_ms = (ss[2] + ss[3]) / 48 if pooled else ms[3]
    comparison_ms = error_ms if pooled else ms[2]
    assert final["part"]["f_statistic"] == pytest.approx(ms[0] / comparison_ms)
    assert final["part"]["p_value"] == pytest.approx(
        stats.f.sf(ms[0] / comparison_ms, 9, 48 if pooled else 18)
    )
    components = result["variance_components"]
    assert components["repeatability"]["raw_variance"] == pytest.approx(error_ms)
    assert components["operator"]["raw_variance"] == pytest.approx((ms[1] - comparison_ms) / 20)
    assert components["part_to_part"]["raw_variance"] == pytest.approx((ms[0] - comparison_ms) / 6)
    grr = components["total_gage_rr"]["final_variance"]
    part_variance = components["part_to_part"]["final_variance"]
    assert components["ndc"] == floor(1.41 * sqrt(part_variance / grr))
    assert components["total_gage_rr"]["percent_contribution"] == pytest.approx(
        100 * grr / (grr + part_variance)
    )
    assert components["total_gage_rr"]["percent_study_variation"] == pytest.approx(
        100 * sqrt(grr / (grr + part_variance))
    )
    assert result["sample"]["n_used"] == 60
    assert result["design"]["replicate_count"] == 2


def test_cell_local_replicate_ids_inference_shuffle_and_full_long_id_identity():
    rows = fixture()
    automatic = run(rows)
    explicit = run(rows, explicit=True)
    assert explicit["design"]["replicate_set_consistent"] is False
    assert explicit["design"]["balanced"] is True
    assert automatic["anova_table"] == explicit["anova_table"]
    random.Random(7).shuffle(rows)
    shuffled = run(rows)
    assert shuffled["variance_components"] == automatic["variance_components"]
    for row in rows:
        row[0] = "긴" * 130 + row[0]
        row[1] = "operator" * 30 + row[1]
    renamed = run(rows)
    assert renamed["variance_components"] == automatic["variance_components"]
    assert "긴" not in json.dumps(renamed, ensure_ascii=False)


def test_retain_remains_legacy_default_and_differs_from_auto_pool():
    rows = fixture()
    retained = run(rows, policy="retain")
    assert retained["interaction_selection"]["pooled"] is False
    assert len(retained["anova_table"]) == 5
    assert retained["variance_components"] != run(rows)["variance_components"]
    legacy = calculate_gage_rr_anova(
        rows,
        measurement_column=column("measurement", 2),
        part_column=column("part", 0),
        operator_column=column("operator", 1),
        replicate_column=column("repeat", 3),
    )
    assert legacy["interaction_selection"]["requested_policy"] == "retain"
    assert legacy["replicate_mode"] == "explicit_column"


@pytest.mark.parametrize(
    "edit,error",
    [
        (lambda rows: rows[::2], "gage_rr_replicate_count_too_small"),
        (lambda rows: rows[2:], "gage_rr_crossed_cells_missing"),
        (lambda rows: rows + [rows[0]], "gage_rr_unbalanced_crossed_design"),
    ],
)
def test_preflight_and_run_share_invalid_design_diagnosis(edit, error):
    rows = edit(fixture())
    checked = preflight(rows)
    assert checked["design"]["ready_for_anova"] is False
    assert error in [issue["code"] for issue in checked["issues"]]
    with pytest.raises(GageRrError, match=error):
        run(rows)


def test_explicit_duplicate_not_misdiagnosed_as_structural_imbalance():
    rows = fixture()
    rows[1][3] = rows[0][3]
    checked = preflight(rows, explicit=True)
    assert checked["design"]["balanced"] is True
    assert checked["design"]["ready_for_anova"] is False
    with pytest.raises(GageRrError, match="gage_rr_duplicate_replicates_per_cell"):
        run(rows, explicit=True)


def test_zero_noise_has_no_invented_interaction_p_value_or_pooling():
    rows = fixture()
    for start in range(0, len(rows), 2):
        rows[start + 1][2] = rows[start][2]
    result = run(rows)
    assert result["interaction_selection"]["interaction_p_value"] is None
    assert result["interaction_selection"]["pooled"] is False
    for row in rows:
        row[2] = "10"
    with pytest.raises(GageRrError, match="gage_rr_zero_total_variation"):
        run(rows)
