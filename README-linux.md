# Statistical Twin Linux Prerelease

Full application, not a presentation-only build. Validated target: Ubuntu 24.04,
x86_64, CPython 3.12, CPU only. This archive does **not** bundle Python.
Python 3.12 with venv/pip must already be installed. Node.js, Git, sudo and an
Internet connection are not required for archive installation or runtime.

## Install and Run

Use a new empty download directory, not the previous installation directory.
Verify the downloaded archive against the accompanying SHA256SUMS, then:

```sh
sha256sum -c SHA256SUMS
tar -xzf statistical-twin-linux-2026.10.2-ubuntu24.04-x86_64-py312.tar.gz
cd statistical-twin-linux
./install.sh
./run.sh
```

`./run.sh` now listens on **0.0.0.0:8600** (all IPv4 interfaces). On another
approved company PC, open **http://SERVER-IP:8600/home**, using one of the
`LAN URL` addresses printed at startup. Do not enter `0.0.0.0` in the browser;
`127.0.0.1` on another PC refers to that PC, not the server.
On the server itself, http://127.0.0.1:8600/home still works.
The API and built UI share this single origin; no additional API port is opened.
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

## Trusted LAN Boundary

This owner-approved release default is for a restricted, trusted company LAN,
**not the public Internet**. There is no login, TLS, RBAC or per-user isolation.
Every admitted peer shares the same workspace with read, upload, edit and delete
access. HTTP traffic is unencrypted. Coordinate edits; this is not a production
multi-user service. No firewall rules are changed by installation or launch.

Before starting, have the administrator restrict inbound TCP 8600 to approved
company PCs/subnets. Do not use Internet port forwarding or unrestricted cloud
security groups. A reachable server IP, routing and an allowed firewall port are
still required; being on the same company network alone does not guarantee them.

Host headers accept only localhost, 127.0.0.1 and locally assigned interface IPv4
addresses detected at startup. DNS aliases and proxy-forwarded host overrides
are not accepted. After an address change, restart the app. Browser mutations
require the exact same Origin, including port; cross-site browser requests are
blocked. These checks are **not authentication** and do not stop an admitted
native client. Native API clients must send the matching `Origin` header too.

To disable remote LAN access explicitly:

```sh
./run.sh --local-only
```

This binds only **127.0.0.1:8600**. For remote private access, keep the server in
this mode and use SSH forwarding:

```sh
ssh -L 8600:127.0.0.1:8600 user@linux-host
```

Then open http://127.0.0.1:8600/home on the SSH client.
Windows trusted-LAN development policy is unchanged.

## Identity and Integrity

`BUILD_INFO.json` records source commit, API contract, metadata schema, Python
target and lock hash. Release version (for example 2026.10.2) is independent of
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
