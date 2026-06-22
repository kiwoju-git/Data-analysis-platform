import os
from pathlib import Path

import pytest

from app.storage.atomic import atomic_replace, atomic_write_bytes, atomic_write_text


def test_atomic_write_text_creates_parent_and_supports_unicode_path(tmp_path) -> None:
    target_path = tmp_path / "workspace with spaces" / "한글 경로" / "result.txt"

    atomic_write_text(target_path, "안전한 저장")

    assert target_path.read_text(encoding="utf-8") == "안전한 저장"
    assert not list(target_path.parent.glob("*.tmp"))


def test_atomic_write_bytes_replaces_existing_file(tmp_path) -> None:
    target_path = tmp_path / "artifact.bin"
    target_path.write_bytes(b"old")

    atomic_write_bytes(target_path, b"new")

    assert target_path.read_bytes() == b"new"


def test_atomic_replace_keeps_existing_file_when_writer_fails(tmp_path) -> None:
    target_path = tmp_path / "manifest.json"
    target_path.write_text('{"version": 1}', encoding="utf-8")

    def failing_writer(temp_path: Path) -> None:
        temp_path.write_text("partial", encoding="utf-8")
        raise RuntimeError("simulated write failure")

    with pytest.raises(RuntimeError, match="simulated write failure"):
        atomic_replace(target_path, failing_writer)

    assert target_path.read_text(encoding="utf-8") == '{"version": 1}'
    assert not list(target_path.parent.glob("*.tmp"))


def test_atomic_replace_uses_same_directory_temp_file(tmp_path) -> None:
    target_path = tmp_path / "nested" / "value.txt"
    seen_temp_paths: list[Path] = []

    def writer(temp_path: Path) -> None:
        seen_temp_paths.append(temp_path)
        assert temp_path.parent == target_path.parent
        temp_path.write_text("done", encoding="utf-8")

    atomic_replace(target_path, writer)

    assert target_path.read_text(encoding="utf-8") == "done"
    assert seen_temp_paths
    assert os.path.dirname(seen_temp_paths[0]) == os.path.dirname(target_path)
