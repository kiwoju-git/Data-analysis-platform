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
sets a success marker only after pip check and release verification. Reinstallation
does not trust an equal app_version as proof that backend code matches the archive.
User workspaces are not touched by installation.

The launcher verifies identity/files before setting environment and importing the
FastAPI app. It binds127.0.0.1:8600, one worker, no reload, CPU threads capped.
The existing workspace default and metadata20 migration/recovery rules remain.
Remote access is via SSH forwarding, not a public unauthenticated bind.
Linux port preflight uses SO_REUSEADDR (never SO_REUSEPORT), matching Uvicorn's
closed-connection TIME_WAIT restart behavior. An active listener still fails
preflight and is never stopped. Windows port behavior is unchanged.

Verification extracts the actual tar.gz twice into new locations, installs with
neither Node nor Git in PATH and pip no-index, uses an external synthetic workspace,
checks API/UI/deep links, PCA/PLS/GP/Two Variances, reports, restart and restore.
Browser assertions execute from the development test environment, not the archive.
Validation JSON and archive SHA are release assets, not source files rewritten
after FINAL_SHA. The exact tested bytes are published as a prerelease.
CI archive build/validation may run alongside Windows checks after Linux gates
pass. It only uploads a CI artifact: main and public Release publication still
require every Windows/Linux/E2E job to pass on that exact source commit.
