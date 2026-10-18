"""Create a verified offline backup without changing workspace assets."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.storage.workspace_backup import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main(["backup", *sys.argv[1:]]))
