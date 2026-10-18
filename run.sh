#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -f "$ROOT/.installed" || ! -x "$ROOT/.venv/bin/python" ]]; then echo 'Run ./install.sh successfully first.' >&2; exit 1; fi
exec "$ROOT/.venv/bin/python" -I -S -B "$ROOT/release_bootstrap.py" launch --release-root "$ROOT" "$@"
