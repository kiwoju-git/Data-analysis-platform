# Linux Source and Release Contract

Linux adds Ubuntu 24.04 x86_64 / CPython 3.12; Python 3.11 is an additional
source/CI compatibility target. Python metadata is >=3.10,<3.13. Windows keeps
PowerShell, Python 3.10 and its existing hash lock. Numerical library pins remain
NumPy 2.2.6, SciPy 1.15.3 and scikit-learn 1.7.2. Linux locks are generated on
the actual target interpreter using wheel bytes, never copied Windows hashes.

## Source Runner

`bootstrap.sh --python python3.12` installs the target dev lock, then the backend
editable with no dependency resolution or build isolation, and npm ci.
`dev.sh` owns only the process groups it creates. API:127.0.0.1:8000;
frontend:127.0.0.1:8600 by default. Explicit --lan exposes the frontend only,
with the existing Host/Origin guard and same-origin loopback proxy. No firewall
rules, wildcard CORS or authentication claims are added. Windows LAN defaults
remain unchanged. Port conflicts fail instead of killing unrelated processes.

Git HEAD or archive-sha256 identity is shared by frontend/backend. Archive hashing
uses the same source-file selection and sorted relative-path/NUL/file-hash/newline
aggregation as dev_runtime_helpers.ps1. Install paths/mtimes are excluded.
Git must identify the source root itself, not an enclosing repository containing
an extracted archive with invalid Git metadata.
Startup verifies service, API, metadata, identity and required capabilities.

## Built UI

DATALAB_FRONTEND_DIST is optional. If unset, API-only root JSON is unchanged.
If set, index.html must exist outside the workspace. Explicit SPA paths mirror
appRoute; / redirects to /home. Unknown API/assets never become an HTML200.
Traversal, dotfiles, unknown public assets and symlinks are rejected. Index has
no-store; built assets are cacheable. No Vite server is used for a release.

## Offline Archive

Build from a clean tracked HEAD only. Git archive excludes untracked/user files.
The archive contains built web files, runtime/application wheels, hash requirements,
BUILD_INFO, FILES.sha256, install/run scripts, notices and instructions. It contains
no interpreter, node_modules, workspace, credentials, models or diagnostics.
Notices include Python wheel metadata/licenses and frontend production dependency
package metadata/licenses. BUILD_INFO records required capabilities as well as
the source, API and metadata identities; startup and archive verification check all.

Install requires Ubuntu24.04/x86_64/CPython3.12+venv/pip already available. It
verifies paths and hashes, force-reinstalls only the packaged wheels offline and
sets an atomic structured success marker only after pip check and release verification. Reinstallation
does not trust an equal app_version as proof that backend code matches the archive.
User workspaces are not touched by installation.

The release-owned stdlib bootstrap verifies the actual application wheel, installed
files and marker before importing any installed application module. It uses
`-I -S -B` and holds a shared installation lock; reinstall needs an exclusive lock.
See [release identity](release_identity_contract.md) for the staging-only wheel
resource and the distinction between payload and installed-code verification.
Owner approval on 2026-10-16 changes the release default to
0.0.0.0:8600 (built UI and API together), one worker, no reload, CPU threads capped.
`run.sh --local-only` restores 127.0.0.1:8600. Linux source development and Windows
development defaults are unchanged. Proxy headers are disabled in the release.
The existing workspace default remains. Remediation uses API 23 and additive
metadata migrations 21/22; historical artifacts are not rewritten. Workspace lease
acquisition precedes migration and interrupted-run recovery.
Local-only mode can be accessed remotely through SSH forwarding.
Linux port preflight uses SO_REUSEADDR (never SO_REUSEPORT), matching Uvicorn's
closed-connection TIME_WAIT restart behavior. An active listener still fails
preflight and is never stopped. Windows port behavior is unchanged.

### Trusted LAN Release Guard

This is a shared trusted-operator exception, not authenticated multi-user hosting.
All admitted clients can read/write/delete shared assets. HTTP is unencrypted;
operators must restrict inbound TCP to approved peers and never expose it to the
Internet. The application does not change firewall rules. See README-linux.md.

The launcher reads each Linux interface's assigned primary IPv4 address through
SIOCGIFADDR without DNS or external traffic. Allowed Host values are those
addresses, localhost and 127.0.0.1, with the configured port. Interface address
changes require restart; additional secondary addresses/DNS aliases are not
advertised or implicitly allowed. Malformed/duplicate/unknown Host headers fail
with `release_host_not_allowed`. Mismatched/duplicate/null Origin, cross-site
Sec-Fetch-Site, and mutations without exact same-origin headers fail with
`release_origin_not_allowed`. This guard wraps CORS and does not trust forwarded
headers. CORS remains narrow; browser same-origin requests need no CORS grant.
Native clients must supply Origin for mutations; they can forge these headers,
so the guard is browser request defense, not a network authorization boundary.

Settings permits a non-loopback bind only with trusted_lan=true, production
environment and a valid built UI directory separate from workspace. API-only
Settings remains loopback by default. The launcher explicitly clears the LAN
mode and host list in --local-only mode, including stale inherited values.
The LAN binding itself changes no numerical policy or statistical result/model
schema. API/metadata changes belong to the separate remediation contracts.

Verification extracts the actual tar.gz twice into new locations, installs with
neither Node nor Git in PATH in an actually isolated network namespace, uses an external synthetic workspace,
checks API/UI/deep links, PCA/PLS/GP/Two Variances, reports, restart and restore.
The LAN verifier uses the runner's actual non-loopback interface address and
browser same-origin requests, verifies rejected Host/Origin requests, and then
checks that --local-only cannot be reached through that interface. This is an
Ubuntu CI network test, not a claim about the user's physical LAN/firewall.
Browser assertions execute from the development test environment, not the archive.
Validation JSON and archive SHA are release assets, not source files rewritten
after FINAL_SHA. The exact tested bytes are published as a prerelease.
CI archive build/validation may run alongside Windows checks after Linux gates
pass. It only uploads a CI artifact: main and public Release publication still
require every Windows/Linux/E2E job to pass on that exact source commit.
The `release-ready` job additionally requires all dependency-security gates.
`release-version.json` or the validated workflow input supplies the archive version;
CI evidence is SHA-named. No failed/skipped/pending job is a publication success.
Namespace tooling is CI-only; the distributed offline installer needs no sudo.
