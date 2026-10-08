#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${1:-python3.12}"
TARGET="${2:-py312-linux}"
PROFILE="${3:-dev}"
case "$TARGET:$PROFILE" in py312-linux:dev|py312-linux:runtime|py311-linux:dev|py311-linux:runtime) ;; *) echo "Unsupported target/profile" >&2; exit 2;; esac
STAGE="$(mktemp -d)"
trap 'rm -rf -- "$STAGE"' EXIT
"$PYTHON" -m venv "$STAGE/venv"
"$STAGE/venv/bin/python" -m pip install --only-binary=:all: 'packaging==25.0'
mkdir "$STAGE/wheels"
"$STAGE/venv/bin/python" -m pip download --only-binary=:all: --dest "$STAGE/wheels" -r "$ROOT/backend/requirements-$TARGET-$PROFILE.in"
"$STAGE/venv/bin/python" "$ROOT/scripts/generate_python_lock.py" "$STAGE/wheels" "$ROOT/backend/requirements-$TARGET-$PROFILE.lock" --target "$TARGET" --profile "$PROFILE"
