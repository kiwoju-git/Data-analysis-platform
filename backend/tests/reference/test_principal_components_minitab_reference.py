import json
from pathlib import Path

import numpy as np
import pytest

from app.statistics.principal_components import (
    PrincipalComponentsColumn,
    calculate_principal_components,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "pca_minitab_loan_applicant_reference.json"


def test_correlation_pca_matches_official_minitab_loan_applicant_output() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    fixture_columns = fixture["columns"]
    values_by_column = [column["values"] for column in fixture_columns]
    rows = [
        [str(values_by_column[column_index][row_index]) for column_index in range(8)]
        for row_index in range(30)
    ]
    columns = [
        PrincipalComponentsColumn(
            column_id=f"c{index + 1}",
            column_index=index,
            display_name=column["name"],
            data_type="decimal",
            measurement_level="continuous",
            role="feature",
            unit=None,
        )
        for index, column in enumerate(fixture_columns)
    ]

    result = calculate_principal_components(rows, columns)

    assert [item["eigenvalue"] for item in result["eigenanalysis"]] == pytest.approx(
        fixture["eigenvalues"], abs=5.1e-5
    )
    assert [item["proportion"] for item in result["eigenanalysis"]] == pytest.approx(
        fixture["proportions"], abs=5.1e-4
    )

    actual_vectors = np.asarray([item["values"] for item in result["eigenvectors"]])
    expected_vectors = np.asarray(fixture["eigenvectors_by_variable"], dtype=float)
    for component_index in range(expected_vectors.shape[1]):
        if np.dot(actual_vectors[:, component_index], expected_vectors[:, component_index]) < 0:
            expected_vectors[:, component_index] *= -1
    assert actual_vectors == pytest.approx(expected_vectors, abs=5.1e-4)
