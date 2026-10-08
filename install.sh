#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON=${PYTHON:-python3.12}
if [[ $# != 0 ]]; then echo 'Usage: PYTHON=python3.12 ./install.sh' >&2; exit 2; fi
"$PYTHON" - "$ROOT" <<'PY'
import hashlib, json, pathlib, platform, re, sys
root = pathlib.Path(sys.argv[1]).resolve()
def require(condition, message):
    if not condition:
        raise SystemExit(message)
require(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'Requires Linux x86_64')
require(sys.version_info[:2] == (3, 12) and platform.python_implementation() == 'CPython', 'Requires CPython 3.12 with venv/pip')
release = platform.freedesktop_os_release()
require(release.get('ID') == 'ubuntu' and release.get('VERSION_ID') == '24.04', 'Validated release target is Ubuntu 24.04')
seen = set()
for line in (root / 'FILES.sha256').read_text(encoding='utf-8').splitlines():
    match = re.fullmatch(r'([a-f0-9]{64})  ([^\r\n]+)', line)
    require(match is not None, 'Malformed checksum manifest')
    digest, relative = match.groups()
    require(relative not in seen and not any(p in ('', '.', '..') for p in relative.split('/')) and '\\' not in relative and ':' not in relative, 'Unsafe manifest path')
    seen.add(relative)
    path = root.joinpath(*relative.split('/'))
    require(root in path.resolve().parents and not path.is_symlink(), 'Unsafe release path')
    require(not any(p.is_symlink() for p in path.parents if root in p.parents), 'Unsafe release directory')
    require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest, 'Release checksum mismatch: ' + relative)
require({'BUILD_INFO.json', 'web/index.html', 'requirements-release.lock', 'run.sh', 'install.sh'} <= seen, 'Incomplete release')
info = json.loads((root / 'BUILD_INFO.json').read_text(encoding='utf-8'))
require(info['python_target'] == '3.12' and info['os'] == 'ubuntu24.04' and info['architecture'] == 'x86_64', 'Release target mismatch')
require(re.fullmatch('[a-f0-9]{40}', info['source_commit']) is not None, 'Invalid source identity')
require(hashlib.sha256((root / 'requirements-release.lock').read_bytes()).hexdigest() == info['lock_sha256'], 'Lock checksum mismatch')
PY
if [[ -e "$ROOT/.venv" ]]; then
  if [[ -L "$ROOT/.venv" ]]; then echo 'Refusing a symlinked .venv; install into a new directory.' >&2; exit 1; fi
  if [[ ! -x "$ROOT/.venv/bin/python" ]]; then echo 'Existing .venv is not usable. Install into a new directory.' >&2; exit 1; fi
  "$ROOT/.venv/bin/python" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3,12) else "Existing venv Python differs; use a new directory")'
else "$PYTHON" -m venv "$ROOT/.venv"; fi
"$ROOT/.venv/bin/python" -c 'import pathlib,sys; (pathlib.Path(sys.argv[1]) / ".installed").unlink(missing_ok=True)' "$ROOT"
"$ROOT/.venv/bin/python" -m pip install --force-reinstall --no-index --find-links "$ROOT/wheels" --only-binary=:all: --require-hashes -r "$ROOT/requirements-release.lock"
"$ROOT/.venv/bin/python" -m pip check
"$ROOT/.venv/bin/python" - "$ROOT" <<'PY'
import pathlib, sys
from app.launch import verify_release
root = pathlib.Path(sys.argv[1])
info = verify_release(root)
(root / '.installed').write_text(info['source_commit'] + '\n', encoding='ascii')
PY
printf 'Installed offline. Run: %s/run.sh\n' "$ROOT"
