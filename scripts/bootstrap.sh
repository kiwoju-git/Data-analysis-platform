#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON=python3.12
if [[ ${1:-} == --python && $# == 2 ]]; then PYTHON=$2
elif [[ $# != 0 ]]; then echo 'Usage: bootstrap.sh [--python python3.12]' >&2; exit 2; fi
TARGET="$("$PYTHON" -c 'import platform,sys; valid=platform.system()=="Linux" and platform.machine()=="x86_64" and platform.python_implementation()=="CPython" and sys.version_info[:2] in ((3,11),(3,12)); sys.exit("Requires Linux x86_64 CPython 3.11/3.12") if not valid else print("py%d%d-linux" % sys.version_info[:2])')"
cd "$ROOT"
if [[ -d .venv && ! -x .venv/bin/python ]]; then echo 'Existing .venv is not a Linux environment; use a separate source checkout.' >&2; exit 1; fi
if [[ -x .venv/bin/python ]]; then
  .venv/bin/python -c 'import sys; sys.exit(0 if "py%d%d-linux" % sys.version_info[:2] == sys.argv[1] else "Existing venv Python differs; choose a separate checkout")' "$TARGET"
else "$PYTHON" -m venv .venv; fi
.venv/bin/python -m pip install --only-binary=:all: --require-hashes -r "backend/requirements-${TARGET}-dev.lock"
.venv/bin/python -m pip install --no-deps --no-build-isolation -e './backend[dev]'
.venv/bin/python -m pip check
npm --prefix frontend ci
