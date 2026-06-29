import pytest
from scripts.validate_normality_reference import validate_reference


def test_normality_reference_validator_accepts_matching_reference() -> None:
    fixture = _fixture()
    reference = _reference()

    summary = validate_reference(reference, fixture)

    assert summary == {
        "status": "passed",
        "case_count": 2,
        "numpy": "2.2.6",
        "scipy": "1.15.3",
        "python_version": "3.10.11",
    }


def test_normality_reference_validator_rejects_missing_case() -> None:
    fixture = _fixture()
    reference = _reference()
    reference["cases"] = reference["cases"][:1]

    with pytest.raises(ValueError, match="case count"):
        validate_reference(reference, fixture)


def test_normality_reference_validator_rejects_invalid_pvalue() -> None:
    fixture = _fixture()
    reference = _reference()
    reference["cases"][0]["shapiro"]["pvalue"] = 1.2

    with pytest.raises(ValueError, match="must be in \\[0, 1\\]"):
        validate_reference(reference, fixture)


def _fixture() -> dict[str, object]:
    return {
        "fixture_schema_version": 1,
        "fixture_id": "normality_reference_inputs_v1",
        "cases": [
            {
                "case_id": "near_normal_10",
                "values": [-1.5, -0.9, -0.4, -0.1, 0.0, 0.2, 0.5, 0.8, 1.1, 1.6],
                "methods": ["shapiro", "anderson_norm"],
            },
            {
                "case_id": "large_deterministic_6001",
                "values_spec": {
                    "kind": "linear_space",
                    "start": -3.0,
                    "stop": 3.0,
                    "count": 6001,
                },
                "methods": ["shapiro", "anderson_norm"],
                "expected_warning_codes": ["shapiro_large_n_pvalue_limitation"],
            },
        ],
    }


def _reference() -> dict[str, object]:
    return {
        "reference_schema_version": 1,
        "source_fixture_id": "normality_reference_inputs_v1",
        "python_version": "3.10.11",
        "dependencies": {
            "numpy": "2.2.6",
            "scipy": "1.15.3",
        },
        "cases": [
            _case("near_normal_10", 10, []),
            _case(
                "large_deterministic_6001",
                6001,
                ["shapiro_large_n_pvalue_limitation"],
            ),
        ],
    }


def _case(case_id: str, n: int, warnings: list[str]) -> dict[str, object]:
    return {
        "case_id": case_id,
        "n": n,
        "methods": ["shapiro", "anderson_norm"],
        "expected_warning_codes": warnings,
        "shapiro": {
            "statistic": 0.98,
            "pvalue": 0.95,
        },
        "anderson_norm": {
            "statistic": 0.25,
            "critical_values": [0.501, 0.57, 0.684],
            "significance_level": [15.0, 10.0, 5.0],
        },
    }
