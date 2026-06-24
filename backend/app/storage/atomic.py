import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import TypeAlias

BytesWriter: TypeAlias = Callable[[Path], None]


def atomic_write_bytes(target_path: Path, data: bytes) -> None:
    def writer(temp_path: Path) -> None:
        with temp_path.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())

    atomic_replace(target_path, writer)


def atomic_write_text(target_path: Path, text: str, encoding: str = "utf-8") -> None:
    atomic_write_bytes(target_path, text.encode(encoding))


def atomic_replace(target_path: Path, write_temp: BytesWriter) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = _create_temp_path(target_path)

    try:
        write_temp(temp_path)
        os.replace(temp_path, target_path)
    except Exception:
        _remove_if_exists(temp_path)
        raise


def _create_temp_path(target_path: Path) -> Path:
    handle = tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=".tmp-",
        suffix=".tmp",
        dir=target_path.parent,
        delete=False,
    )
    try:
        return Path(handle.name)
    finally:
        handle.close()


def _remove_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return
