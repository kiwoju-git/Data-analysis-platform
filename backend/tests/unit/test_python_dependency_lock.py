from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from scripts.generate_python_lock import collect_wheel_records, render_lock
from scripts.validate_python_lock import validate_lock_text

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_lock_generator_reads_wheel_metadata_and_renders_hash(tmp_path: Path) -> None:
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    wheel_path = wheelhouse / "Example_Package-1.2.3-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as archive:
        archive.writestr(
            "example_package-1.2.3.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: Example_Package\nVersion: 1.2.3\n",
        )

    records = collect_wheel_records(wheelhouse)
    rendered = render_lock(records)

    assert records[0]["name"] == "example-package"
    assert "example-package==1.2.3 \\" in rendered
    assert "    --hash=sha256:" in rendered


def test_lock_validator_rejects_unhashed_requirement() -> None:
    text = "# Target: CPython 3.10, Windows AMD64, wheel-only installation.\n\n" "example==1.0.0\n"

    with pytest.raises(ValueError, match="requirement and one hash"):
        validate_lock_text(text, {"example": "1.0.0"})


def test_repository_lock_is_valid_and_contains_reviewed_candidate() -> None:
    lock_path = REPO_ROOT / "backend" / "requirements-py310-win.lock"

    packages = validate_lock_text(lock_path.read_text(encoding="ascii"))

    assert packages["scikit-learn"]["version"] == "1.7.2"
    assert packages["joblib"]["version"] == "1.5.2"
    assert packages["threadpoolctl"]["version"] == "3.6.0"


def test_pyproject_promotes_only_reviewed_scikit_learn_direct_pin() -> None:
    pyproject = (REPO_ROOT / "backend" / "pyproject.toml").read_text(encoding="utf-8")

    assert pyproject.count('"scikit-learn==1.7.2"') == 1
    assert '"joblib==' not in pyproject
    assert '"threadpoolctl==' not in pyproject


def test_bootstrap_consumes_hash_lock_without_hidden_dependency_resolution() -> None:
    bootstrap = (REPO_ROOT / "scripts" / "bootstrap.ps1").read_text(encoding="utf-8")

    assert "requirements-py310-win.lock" in bootstrap
    assert "--require-hashes" in bootstrap
    assert "--only-binary=:all:" in bootstrap
    assert "--no-deps --no-build-isolation" in bootstrap
    assert "pip check" in bootstrap
    assert "backend[dev]" not in bootstrap


def test_only_bayesian_worker_module_references_sklearn_and_startup_does_not_import_it() -> None:
    app_root = REPO_ROOT / "backend" / "app"
    matches = [
        path for path in app_root.rglob("*.py") if "sklearn" in path.read_text(encoding="utf-8")
    ]

    assert matches == [app_root / "statistics" / "bayesian_optimization.py"]

    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(REPO_ROOT / "backend")
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import app.main; "
                "print(any(name == 'sklearn' or name.startswith('sklearn.') "
                "for name in sys.modules))"
            ),
        ],
        cwd=REPO_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert probe.returncode == 0, probe.stderr
    assert probe.stdout.strip() == "False"
