"""Synthetic package byte checks; these do not claim native installation evidence."""

from __future__ import annotations

import hashlib
import importlib.util
import shutil
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "contour_release_verification", ROOT / "scripts/verify_linux_release.py"
)
assert SPEC is not None and SPEC.loader is not None
VERIFY = importlib.util.module_from_spec(SPEC)
with pytest.MonkeyPatch.context() as imports:
    imports.syspath_prepend(str(ROOT / "scripts"))
    SPEC.loader.exec_module(VERIFY)

METADATA = (
    b"Metadata-Version: 2.1\nName: contourpy\nVersion: 1.3.2\n"
    b"Requires-Python: >=3.10\nRequires-Dist: numpy>=1.23\n\nSynthetic test metadata.\n"
)
LICENSE = b"BSD 3-Clause License\n\nSynthetic test license; not a redistributed package.\n"


@pytest.fixture(autouse=True)
def forbid_processes(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*args, **kwargs):
        pytest.fail("Package byte tests must not run installers or native extensions")

    monkeypatch.setattr(VERIFY.subprocess, "run", blocked)
    monkeypatch.setattr(VERIFY.subprocess, "Popen", blocked)


def update_manifest(root: Path) -> None:
    records = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}\n"
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "FILES.sha256"
    ]
    (root / "FILES.sha256").write_text("".join(records), encoding="utf-8")


def update_lock(root: Path) -> None:
    wheel = next((root / "wheels").glob("*.whl"))
    (root / "requirements-release.lock").write_text(
        "# Target: CPython 3.12, Linux x86_64, wheel-only; profile: runtime.\n"
        "contourpy==1.3.2 \\\n"
        f"    --hash=sha256:{hashlib.sha256(wheel.read_bytes()).hexdigest()}\n",
        encoding="ascii",
    )


def package(tmp_path: Path, metadata: bytes = METADATA, license_text: bytes = LICENSE) -> Path:
    root = tmp_path / "synthetic package"
    (root / "wheels").mkdir(parents=True)
    wheel = root / "wheels" / VERIFY.CONTOUR_WHEEL_NAME
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("contourpy/__init__.py", b"raise AssertionError('never import')\n")
        archive.writestr("contourpy-1.3.2.dist-info/METADATA", metadata)
        archive.writestr("contourpy-1.3.2.dist-info/LICENSE", license_text)
    notices = root / "THIRD_PARTY_NOTICES" / wheel.stem
    notices.mkdir(parents=True)
    (notices / "1-METADATA").write_bytes(metadata)
    (notices / "2-LICENSE").write_bytes(license_text)
    update_lock(root)
    update_manifest(root)
    return root


def notice(root: Path, leaf: str) -> Path:
    return next((root / "THIRD_PARTY_NOTICES").glob(f"*/*-{leaf}"))


def test_exact_wheel_lock_notices_and_manifest_are_verified_without_mutation(
    tmp_path: Path,
) -> None:
    root = package(tmp_path)
    before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    proof = VERIFY.verify_contour_dependency(root)
    assert proof["status"] == "verified"
    assert proof["name"] == "contourpy"
    assert proof["version"] == "1.3.2"
    assert proof["python_target"] == "3.12"
    assert proof["license"] == "BSD-3-Clause"
    assert proof["wheel"] == VERIFY.CONTOUR_WHEEL_NAME
    assert proof["license_sha256"] == hashlib.sha256(LICENSE).hexdigest()
    assert proof["metadata_sha256"] == hashlib.sha256(METADATA).hexdigest()
    assert (
        proof["release_manifest_sha256"]
        == hashlib.sha256(before[root / "FILES.sha256"]).hexdigest()
    )
    assert len(proof["verified_file_sha256"]) == 4
    assert before == {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}


@pytest.mark.parametrize("leaf", ["METADATA", "LICENSE"])
@pytest.mark.parametrize("change", ["missing", "different", "duplicate", "wrong_index"])
def test_notice_must_be_exact_builder_copy(tmp_path: Path, leaf: str, change: str) -> None:
    root = package(tmp_path)
    path = notice(root, leaf)
    if change == "missing":
        path.unlink()
    elif change == "different":
        path.write_bytes(path.read_bytes() + b"changed\n")
    elif change == "duplicate":
        shutil.copyfile(path, path.with_name(f"99-{leaf}"))
    else:
        path.rename(path.with_name(f"99-{leaf}"))
    update_manifest(root)
    with pytest.raises(ValueError, match="notice differs"):
        VERIFY.verify_contour_dependency(root)


@pytest.mark.parametrize(
    "old,new",
    [
        (b"Name: contourpy", b"Name: unrelated"),
        (b"Version: 1.3.2", b"Version: 1.3.1"),
        (b"Requires-Python: >=3.10", b"Requires-Python: >=3.11"),
        (b"Name: contourpy", b"Name: contourpy\nName: contourpy"),
    ],
)
def test_wrong_metadata_rejected_even_with_matching_notice_and_hashes(
    tmp_path: Path, old: bytes, new: bytes
) -> None:
    root = package(tmp_path, metadata=METADATA.replace(old, new))
    with pytest.raises(ValueError, match="package metadata"):
        VERIFY.verify_contour_dependency(root)


def test_wrong_license_rejected_even_with_matching_notice(tmp_path: Path) -> None:
    root = package(tmp_path, license_text=b"Unreviewed license\n")
    with pytest.raises(ValueError, match="license"):
        VERIFY.verify_contour_dependency(root)


@pytest.mark.parametrize("change", ["missing", "windows", "py311", "multiple"])
def test_exact_target_and_one_package_version_required(tmp_path: Path, change: str) -> None:
    root = package(tmp_path)
    wheel = next((root / "wheels").glob("*.whl"))
    if change == "missing":
        wheel.unlink()
    elif change == "multiple":
        shutil.copyfile(wheel, wheel.with_name(wheel.name.replace("1.3.2", "1.3.1")))
    else:
        name = (
            "contourpy-1.3.2-cp310-cp310-win_amd64.whl"
            if change == "windows"
            else wheel.name.replace("cp312", "cp311")
        )
        wheel.rename(wheel.with_name(name))
    with pytest.raises(ValueError, match="locked Linux CPython 3.12"):
        VERIFY.verify_contour_dependency(root)


@pytest.mark.parametrize("change", ["wheel", "lock_hash", "lock_version", "lock_duplicate"])
def test_lock_and_wheel_must_match(tmp_path: Path, change: str) -> None:
    root = package(tmp_path)
    path = root / "requirements-release.lock"
    text = path.read_text(encoding="ascii")
    if change == "wheel":
        with next((root / "wheels").glob("*.whl")).open("ab") as output:
            output.write(b"changed")
    elif change == "lock_hash":
        text = text.split("--hash=sha256:")[0] + "--hash=sha256:" + "0" * 64 + "\n"
    elif change == "lock_version":
        text = text.replace("contourpy==1.3.2", "contourpy==1.3.1")
    else:
        text += "\n".join(text.splitlines()[1:]) + "\n"
    path.write_text(text, encoding="ascii")
    update_manifest(root)
    with pytest.raises(ValueError):
        VERIFY.verify_contour_dependency(root)


@pytest.mark.parametrize("suffix", [".whl", "1-METADATA", "2-LICENSE", ".lock"])
@pytest.mark.parametrize("change", ["missing", "wrong", "duplicate"])
def test_manifest_covers_all_dependency_records(tmp_path: Path, suffix: str, change: str) -> None:
    root = package(tmp_path)
    path = root / "FILES.sha256"
    lines = path.read_text(encoding="utf-8").splitlines()
    matching = next(line for line in lines if line.endswith(suffix))
    if change == "missing":
        lines.remove(matching)
    elif change == "wrong":
        lines[lines.index(matching)] = "0" * 64 + matching[64:]
    else:
        lines.append(matching)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        VERIFY.verify_contour_dependency(root)


@pytest.mark.parametrize("leaf", ["METADATA", "LICENSE"])
def test_duplicate_wheel_member_rejected(tmp_path: Path, leaf: str) -> None:
    root = package(tmp_path)
    wheel = next((root / "wheels").glob("*.whl"))
    with pytest.warns(UserWarning, match="Duplicate name"):
        with zipfile.ZipFile(wheel, "a") as archive:
            archive.writestr(f"contourpy-1.3.2.dist-info/{leaf}", b"duplicate")
    update_lock(root)
    update_manifest(root)
    with pytest.raises(ValueError, match="member inventory"):
        VERIFY.verify_contour_dependency(root)
