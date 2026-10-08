import hashlib
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("dev_linux", ROOT / "scripts/dev_linux.py")
assert SPEC is not None and SPEC.loader is not None
DEV = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEV)


def test_archive_fingerprint_is_path_and_bytes_only(tmp_path: Path) -> None:
    (tmp_path / "backend/app/__pycache__").mkdir(parents=True)
    (tmp_path / "backend/app/a.py").write_bytes(b"x=1\n")
    (tmp_path / "backend/app/__pycache__/a.pyc").write_bytes(b"ignored")
    file_hash = hashlib.sha256(b"x=1\n").hexdigest()
    expected = hashlib.sha256(f"backend/app/a.py\0{file_hash}\n".encode()).hexdigest()
    assert DEV.archive_fingerprint(tmp_path) == "archive-sha256-" + expected
    (tmp_path / "backend/app/a.py").touch()
    assert DEV.archive_fingerprint(tmp_path) == "archive-sha256-" + expected


def test_linux_direct_dependency_pins_match_pyproject() -> None:
    contents = (ROOT / "backend/pyproject.toml").read_text(encoding="utf-8")
    base = contents.split("dependencies = [", 1)[1].split("\n]", 1)[0]
    dependencies = set(re.findall(r'"([^"\n]+==[^"\n]+)"', base))
    assert dependencies
    for target in ("py311-linux", "py312-linux"):
        for profile in ("runtime", "dev"):
            inputs = (
                (ROOT / f"backend/requirements-{target}-{profile}.in")
                .read_text(encoding="utf-8")
                .splitlines()
            )
            assert dependencies <= set(inputs)
            assert "joblib==1.5.2" in inputs
            assert "threadpoolctl==3.6.0" in inputs
