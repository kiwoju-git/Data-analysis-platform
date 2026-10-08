import hashlib
import json
from pathlib import Path

import pytest

from app.core.runtime_contract import API_CONTRACT_VERSION, RUNTIME_CAPABILITIES
from app.launch import verify_release
from app.storage.metadata import SCHEMA_VERSION


def release_fixture(root: Path) -> None:
    (root / "web").mkdir()
    (root / "wheels").mkdir()
    for filename, contents in {
        "web/index.html": "<html>release</html>",
        "requirements-release.lock": "# fixture\n",
        "install.sh": "#!/bin/sh\n",
        "run.sh": "#!/bin/sh\n",
    }.items():
        (root / filename).write_text(contents, encoding="utf-8")
    info = {
        "source_commit": "a" * 40,
        "api_contract_version": API_CONTRACT_VERSION,
        "metadata_schema_version": SCHEMA_VERSION,
        "required_capabilities": RUNTIME_CAPABILITIES,
        "python_target": "3.12",
        "os": "ubuntu24.04",
        "architecture": "x86_64",
        "lock_sha256": hashlib.sha256(
            (root / "requirements-release.lock").read_bytes()
        ).hexdigest(),
    }
    (root / "BUILD_INFO.json").write_text(json.dumps(info), encoding="utf-8")
    manifest = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}"
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]
    (root / "FILES.sha256").write_text("\n".join(manifest) + "\n", encoding="utf-8")


def test_release_verification_and_tamper_rejection(tmp_path: Path) -> None:
    release_fixture(tmp_path)
    assert verify_release(tmp_path)["source_commit"] == "a" * 40
    (tmp_path / "web/index.html").write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_release(tmp_path)


def test_unmanifested_asset_and_traversal_rejected(tmp_path: Path) -> None:
    release_fixture(tmp_path)
    (tmp_path / "web/extra.js").write_text("extra", encoding="utf-8")
    with pytest.raises(ValueError, match="unverified"):
        verify_release(tmp_path)
    (tmp_path / "FILES.sha256").write_text("a" * 64 + "  ../outside\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsafe"):
        verify_release(tmp_path)


def test_launcher_sets_environment_before_uvicorn_import() -> None:
    import app.launch

    source = Path(app.launch.__file__).read_text(encoding="utf-8")
    assert source.index("os.environ.update(") < source.index("    import uvicorn")
    assert 'uvicorn.run("app.main:app"' in source
    assert "from app.main" not in source
