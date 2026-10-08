#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec "$ROOT/.venv/bin/python" tests/e2e/critical_path.py "$@"
