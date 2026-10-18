import json
import os
import subprocess
import sys
import venv
from pathlib import Path

import pytest
from scripts import dependency_security
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


def test_audit_cli_preserves_virtual_environment_interpreter_paths(tmp_path, monkeypatch):
    target = tmp_path / "target" / "bin" / "python"
    auditor = tmp_path / "auditor" / "bin" / "python"
    base = tmp_path / "base" / "python"
    resolve = Path.resolve

    def dereference(path, *args, **kwargs):
        return base if path in (target, auditor) else resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", dereference)
    received = []
    monkeypatch.setattr(dependency_security, "audit_python", lambda *args: received.append(args))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dependency_security.py",
            "--target-python",
            str(target),
            "--audit-python",
            str(auditor),
            "--lock",
            str(tmp_path / "requirements.lock"),
            "--output-dir",
            str(tmp_path / "audit"),
        ],
    )

    assert dependency_security.main() == 0
    assert received[0][:2] == (target, auditor)


@pytest.mark.skipif(os.name == "nt", reason="Linux venv interpreter symlink regression")
def test_audit_cli_runs_real_symlinked_virtual_environment(tmp_path, monkeypatch):
    environment = tmp_path / "audit target"
    venv.EnvBuilder(with_pip=False, symlinks=True).create(environment)
    interpreter = environment / "bin" / "python"
    assert interpreter.is_symlink()
    observed = []

    def probe(target, auditor, *_args):
        for executable in (target, auditor):
            output = subprocess.check_output(
                [str(executable), "-c", "import json,sys; print(json.dumps(sys.prefix))"],
                text=True,
            )
            observed.append(Path(json.loads(output)))

    monkeypatch.setattr(dependency_security, "audit_python", probe)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dependency_security.py",
            "--target-python",
            str(interpreter),
            "--audit-python",
            str(interpreter),
            "--lock",
            str(tmp_path / "requirements.lock"),
            "--output-dir",
            str(tmp_path / "audit"),
        ],
    )

    assert dependency_security.main() == 0
    assert observed == [environment, environment]
