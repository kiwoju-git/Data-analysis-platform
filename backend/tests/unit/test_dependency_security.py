import pytest
from scripts.dependency_security import validate_npm_report, validate_python_report


def test_python_audit_requires_exact_complete_inventory():
    clean = {"dependencies": [{"name": "Example_Package", "version": "1.0", "vulns": []}]}
    validate_python_report(clean, {"example-package": "1.0"})
    with pytest.raises(ValueError, match="inventory"):
        validate_python_report(clean, {"example-package": "2.0"})
    with pytest.raises(ValueError, match="inventory"):
        validate_python_report({"dependencies": []}, {})
    with pytest.raises(ValueError, match="not audited"):
        validate_python_report({"dependencies": [{"name": "app", "skip_reason": "unknown"}]}, {})
    clean["dependencies"][0]["vulns"] = [{"id": "GHSA-synthetic"}]
    with pytest.raises(ValueError, match="advisories"):
        validate_python_report(clean, {"example-package": "1.0"})


def test_npm_audit_does_not_treat_failure_or_empty_result_as_clean():
    clean = {
        "auditReportVersion": 2,
        "vulnerabilities": {},
        "metadata": {"dependencies": {"total": 7}, "vulnerabilities": {"total": 0}},
    }
    validate_npm_report(clean)
    with pytest.raises(ValueError):
        validate_npm_report({"error": {"code": "ENETUNREACH"}})
    clean["metadata"]["dependencies"]["total"] = 0
    with pytest.raises(ValueError, match="empty"):
        validate_npm_report(clean)
