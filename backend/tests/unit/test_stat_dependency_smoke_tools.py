import pytest
from scripts.render_stat_dependency_record import render_record
from scripts.validate_stat_dependency_smoke import validate_payload


def test_stat_dependency_smoke_validator_accepts_recorded_pass_payload(tmp_path) -> None:
    payload = _valid_payload()

    summary = validate_payload(payload)

    assert summary == {
        "status": "passed",
        "numpy": "2.2.6",
        "scipy": "1.15.3",
        "python_version": "3.10.11",
    }


def test_stat_dependency_smoke_validator_rejects_non_python_310_payload() -> None:
    payload = _valid_payload()
    payload["python_version"] = "3.12.3"

    with pytest.raises(ValueError, match="python_version must be 3.10.x"):
        validate_payload(payload)


def test_stat_dependency_record_renderer_keeps_todos_for_manual_evidence(tmp_path) -> None:
    payload = _valid_payload()
    result_path = tmp_path / "stat-dependency-smoke.json"

    rendered = render_record(payload, validate_payload(payload), result_path)

    assert "## Recorded Result" in rendered
    assert "NumPy version: 2.2.6" in rendered
    assert "SciPy version: 1.15.3" in rendered
    assert "Shapiro-Wilk: statistic=0.98, pvalue=0.95" in rendered
    assert "Full check result: TODO" in rendered
    assert "Decision: TODO" in rendered


def _valid_payload() -> dict[str, object]:
    return {
        "status": "passed",
        "python_version": "3.10.11",
        "platform": "Windows-11",
        "dependencies": {
            "numpy": "2.2.6",
            "scipy": "1.15.3",
        },
        "smoke_results": {
            "shapiro": {
                "statistic": 0.98,
                "pvalue": 0.95,
                "n": 10,
            },
            "anderson_norm": {
                "statistic": 0.25,
                "critical_values": [0.501, 0.57, 0.684],
                "significance_level": [15.0, 10.0, 5.0],
                "n": 10,
            },
            "levene_mean": {
                "statistic": 1.2,
                "pvalue": 0.31,
                "group_count": 3,
            },
            "brown_forsythe": {
                "statistic": 1.1,
                "pvalue": 0.34,
                "group_count": 3,
            },
        },
    }
