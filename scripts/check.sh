#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="$ROOT/.venv/bin/python"
"$PYTHON" scripts/render_tutorial_results.py --check
"$PYTHON" -m ruff check backend
"$PYTHON" -m ruff format --check backend
"$PYTHON" -m mypy backend/app
"$PYTHON" -m pytest backend/tests
node scripts/check_frontend_localization.mjs
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend test -- --run
npm --prefix frontend run build
