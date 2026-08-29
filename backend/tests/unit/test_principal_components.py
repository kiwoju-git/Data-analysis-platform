from math import sqrt

import numpy as np
import pytest
from sklearn.decomposition import PCA

from app.statistics.principal_components import (
    PrincipalComponentsColumn,
    PrincipalComponentsError,
    PrincipalComponentsOptions,
    calculate_principal_components,
)


def _columns(count: int = 2) -> list[PrincipalComponentsColumn]:
    return [
        PrincipalComponentsColumn(
            column_id=f"c{index + 1}",
            column_index=index,
            display_name=f"X{index + 1}",
            data_type="decimal",
            measurement_level="continuous",
            role="feature",
            unit=None,
        )
        for index in range(count)
    ]


def test_correlation_pca_matches_hand_checkable_perfect_correlation() -> None:
    result = calculate_principal_components(
        [["1", "2"], ["2", "4"], ["3", "6"], ["4", "8"]],
        _columns(),
    )

    assert result["preprocessing"] == {
        "matrix_type": "correlation",
        "centered": True,
        "standardized": True,
        "degrees_of_freedom": 1,
    }
    eigenanalysis = result["eigenanalysis"]
    assert eigenanalysis[0]["eigenvalue"] == pytest.approx(2.0, abs=1e-12)
    assert eigenanalysis[1]["eigenvalue"] == pytest.approx(0.0, abs=1e-12)
    assert eigenanalysis[0]["proportion"] == pytest.approx(1.0, abs=1e-12)
    eigenvectors = result["eigenvectors"]
    assert eigenvectors[0]["values"][0] == pytest.approx(1 / sqrt(2), abs=1e-12)
    assert eigenvectors[1]["values"][0] == pytest.approx(1 / sqrt(2), abs=1e-12)


def test_covariance_pca_preserves_original_scale() -> None:
    result = calculate_principal_components(
        [["1", "2"], ["2", "4"], ["3", "6"], ["4", "8"]],
        _columns(),
        options=PrincipalComponentsOptions(matrix_type="covariance"),
    )

    assert result["matrix"][0] == pytest.approx([5 / 3, 10 / 3], abs=1e-12)
    assert result["matrix"][1] == pytest.approx([10 / 3, 20 / 3], abs=1e-12)
    assert result["eigenanalysis"][0]["eigenvalue"] == pytest.approx(25 / 3, abs=1e-12)
    assert result["preprocessing"]["standardized"] is False


def test_complete_case_exclusions_do_not_change_source_row_identity() -> None:
    result = calculate_principal_components(
        [["1", "2"], ["", "4"], ["3", "bad"], ["4", "8"], ["5", "10"]],
        _columns(),
    )

    assert result["sample"] == {
        "n_total": 5,
        "n_used": 3,
        "n_excluded": 2,
        "n_excluded_missing": 1,
        "n_excluded_non_numeric": 1,
        "variable_count": 2,
    }
    assert [row["source_row_number"] for row in result["scores"]] == [1, 4, 5]
    assert "pca_complete_case_rows_excluded" in result["warnings"]


def test_cumulative_selection_uses_smallest_component_count_meeting_target() -> None:
    result = calculate_principal_components(
        [["1", "2", "1"], ["2", "4", "0"], ["3", "6", "1"], ["4", "8", "0"]],
        _columns(3),
        options=PrincipalComponentsOptions(
            component_selection="cumulative_threshold",
            cumulative_threshold=0.8,
        ),
    )

    selection = result["component_selection"]
    assert selection["selected_components"] >= 1
    selected = selection["selected_components"]
    assert result["eigenanalysis"][selected - 1]["cumulative_proportion"] >= 0.8
    if selected > 1:
        assert result["eigenanalysis"][selected - 2]["cumulative_proportion"] < 0.8


def test_constant_variable_is_rejected_instead_of_silently_removed() -> None:
    with pytest.raises(PrincipalComponentsError, match="pca_constant_variable"):
        calculate_principal_components(
            [["1", "2"], ["1", "3"], ["1", "4"]],
            _columns(),
        )


@pytest.mark.parametrize("matrix_type", ["correlation", "covariance"])
def test_pca_matches_independent_sklearn_svd_reference(matrix_type: str) -> None:
    raw = np.asarray(
        [
            [2.5, 2.4, 1.2],
            [0.5, 0.7, 0.8],
            [2.2, 2.9, 1.5],
            [1.9, 2.2, 1.1],
            [3.1, 3.0, 2.0],
            [2.3, 2.7, 1.4],
            [2.0, 1.6, 0.9],
            [1.0, 1.1, 0.5],
        ]
    )
    production = calculate_principal_components(
        [[str(value) for value in row] for row in raw],
        _columns(3),
        options=PrincipalComponentsOptions(matrix_type=matrix_type),
    )

    transformed = raw - raw.mean(axis=0)
    if matrix_type == "correlation":
        transformed = transformed / raw.std(axis=0, ddof=1)
    reference = PCA(svd_solver="full").fit(transformed)
    reference_scores = reference.transform(transformed)
    reference_components = reference.components_.T
    for component_index in range(reference_components.shape[1]):
        pivot = int(np.argmax(np.abs(reference_components[:, component_index])))
        if reference_components[pivot, component_index] < 0:
            reference_components[:, component_index] *= -1
            reference_scores[:, component_index] *= -1

    actual_vectors = np.asarray(
        [row["values"] for row in production["eigenvectors"]], dtype=float
    )
    actual_scores = np.asarray(
        [row["scores"] for row in production["scores"]], dtype=float
    )
    assert [row["eigenvalue"] for row in production["eigenanalysis"]] == pytest.approx(
        reference.explained_variance_, abs=1e-12
    )
    assert actual_vectors == pytest.approx(reference_components, abs=1e-12)
    assert actual_scores == pytest.approx(reference_scores, abs=1e-12)
