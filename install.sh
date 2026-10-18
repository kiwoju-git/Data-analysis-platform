#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON=${PYTHON:-python3.12}
if [[ $# != 0 ]]; then echo 'Usage: PYTHON=python3.12 ./install.sh' >&2; exit 2; fi
exec "$PYTHON" -I -S -B "$ROOT/release_bootstrap.py" install --release-root "$ROOT"
