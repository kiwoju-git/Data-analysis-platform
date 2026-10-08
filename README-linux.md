# Statistical Twin Linux Prerelease

Full application, not a presentation-only build. Validated target: Ubuntu 24.04,
x86_64, CPython 3.12, CPU only. This archive does **not** bundle Python.
Python 3.12 with venv/pip must already be installed. Node.js, Git, sudo and an
Internet connection are not required for archive installation or runtime.

## Install and Run

Verify the downloaded archive against the accompanying SHA256SUMS, then:

```sh
sha256sum -c SHA256SUMS
tar -xzf statistical-twin-linux-2026.10.1-ubuntu24.04-x86_64-py312.tar.gz
cd statistical-twin-linux
./install.sh
./run.sh
```

Open http://127.0.0.1:8600/home. The API and built UI share this single origin.
Ctrl+C stops the server. A port conflict is an error; no other process is killed.
The default workspace remains `~/.datalabstudio`. To use an existing external
workspace explicitly:

```sh
./run.sh --workspace-root "$HOME/statistical-twin-workspace" --port 8600
```

Do not open the same workspace concurrently from multiple application processes.
Installation never deletes/migrates existing user files. Normal application
startup performs the repository's existing metadata upgrade/recovery protocol.
Back up a workspace before using a newer application release.

For a remote Linux machine use SSH forwarding, **not** an unauthenticated public
bind:

```sh
ssh -L 8600:127.0.0.1:8600 user@linux-host
```

Then open http://127.0.0.1:8600/home locally. This is a single-user local-first
application, not an authenticated multi-user intranet service. No TLS/RBAC is
provided. Windows trusted-LAN development policy is unchanged.

## Identity and Integrity

`BUILD_INFO.json` records source commit, API contract, metadata schema, Python
target and lock hash. Release version (for example 2026.10.1) is independent of
app_version and API contract. `FILES.sha256` verifies packaged files at install
and launch. An absent or mismatched file fails startup instead of mixing builds.
Static files cannot serve workspace files, arbitrary paths or missing API URLs.

`requirements-release.lock` includes the application wheel and every dependency
wheel hash. Installation uses `--no-index --only-binary=:all: --require-hashes`.
It does not upgrade system Python or fetch pip from the Internet. Licenses are
under `THIRD_PARTY_NOTICES` and in wheel metadata. Keep the packaged files intact;
install a later archive in a new directory and point it at the external workspace.

## Source Development

Linux source development supports Python 3.11/3.12 (separate Linux locks); the
release above targets only 3.12. Windows continues to use PowerShell/Python 3.10.
Source development additionally requires Node.js 22 and npm.

```sh
bash scripts/bootstrap.sh --python python3.12
bash scripts/dev.sh
bash scripts/check.sh
bash scripts/e2e.sh
```

Development defaults to loopback. `bash scripts/dev.sh --lan` exposes only the
Host/Origin-guarded Vite frontend on 0.0.0.0:8600, with the API still on loopback
through the same-origin proxy. No firewall rule is changed. Use only a trusted
restricted LAN. Offline source use requires dependencies/browser installation
in advance; archive runtime needs neither Node nor Playwright.

## Rollback

Code rollback does not reverse saved analysis/model files. Preserve workspaces.
Older code may not understand new Two Variances results; do not delete those
results to work around compatibility. Exact change-specific revert commands and
verification scope accompany the GitHub prerelease validation report.
