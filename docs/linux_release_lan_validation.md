# Linux Trusted LAN Release Validation

## Scope and Acceptance

Base: `8ac33267e31be98c93fbe1dea604f5b4dc3e9fb7` (origin/main fetched before work).
Branch: `feat/linux-release-trusted-lan`. Release target: 2026.10.2, Ubuntu 24.04
x86_64 / CPython 3.12. Preserve the earlier 2026.10.1 release and its bytes.

The owner requested LAN access for the offline Linux release. Acceptance:

1. `run.sh` binds 0.0.0.0:8600; a browser can use the server's assigned IPv4 URL.
2. `run.sh --local-only` binds only 127.0.0.1 and clears inherited LAN settings.
3. Reject unexpected Host/Origin and cross-site mutations without wildcard CORS.
4. Actual packaged UI/API, analysis, saved-result restore and HTML download work
   through a non-loopback interface; local-only mode rejects that connection.
5. Windows/source runner defaults and all existing numerical policies are intact.
6. Publish a new prerelease only after the exact committed archive passes CI;
   verified/downloaded asset hashes and tag/source identity must match.

## Risks and Boundaries

This is a deliberate network exposure change, not a cosmetic default. Admitted
clients share read/write/delete access and unencrypted HTTP. Browser Host/Origin
checks are not authentication. No firewall changes, TLS, RBAC, per-user isolation
or concurrency guarantees are added. Restrict TCP to approved company peers.
The single release listener serves UI and API; the source development loopback
API/proxy contract remains separate. Local-only plus SSH forwarding is available.

No schema/API/capability changes: API22, metadata20. No migration, dataset/model
rewrite, numerical option changes, production dependency additions or frontend
redesign. `data_prd.md` is absent. User file `examples/image2.png` is not included.

## Implementation

- `app.launch`: verified archive first, then explicit network environment, then
  uvicorn import; one worker, no reload, no forwarded-header trust, CPU caps.
- `app.core.trusted_lan`: local Linux primary IPv4 discovery and exact Host/port,
  Origin and fetch-site validation in a streaming-preserving ASGI middleware.
- `Settings`: LAN allowed only for the explicitly guarded production built UI.
- `app.main`: LAN guard outside CORS; existing API-only defaults unchanged.
- Archive verifier: actual non-loopback browser/API, rejected browser-origin
  requests, restart across install folders and explicit loopback isolation.

## Evidence Policy

The attempted pre-edit local baseline was interrupted and produced no completed
result. It is not reported as a pass. The base main repeat CI (run 37725717716)
passed Windows, Windows E2E and Python 3.11, but its Linux browser E2E failed a
drawer focus assertion; its release job was consequently skipped. This existing
failure is tracked separately from the LAN change.

Local focused verification on Windows / Python 3.10.11:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_trusted_lan.py backend/tests/unit/test_release_launch.py
```

98 passed, exit 0. New tests cover launch environment ordering, default port and
bind, local-only stale-environment reset, discovery failures, exact Host/Origin,
malformed/duplicate headers, forwarded spoofing and CORS guard ordering. Linux
ioctl/launcher target behavior is mocked here, not claimed as actual Linux.
Ruff check/format of the two focused test files and changed production modules,
and mypy of the three changed launch/config/guard modules passed.

Related release/web/network/source/startup/health tests on edited source:
37 passed, 2 skipped in 105.36s, exit 0. Skips are Windows symlink permissions and
Linux-only TIME_WAIT behavior. These are not pre-edit baseline results.

The historical drawer failure was independently reproduced in Chromium by
deferring only AppChrome's scheduled initial-focus animation frame: Tab correctly
wrapped to the first link, then the pending initial-focus callback moved focus
to the active menu. The browser test now waits for initial active-menu focus
before testing Tab wrapping; no application UI or trap assertion is weakened.

The full `scripts/check.ps1` is also run; its final results and any verification
fixes are captured with the exact committed source in the release evidence.
Exact final Ubuntu/Windows CI outcomes, package smoke results, source SHA and
archive SHA are recorded in the new release's validation assets and linked CI.
Do not copy historical test counts as evidence for this change. A CI-hosted
Ubuntu interface test does not verify the user's physical PCs, routing or firewall.

## Rollback

The release notes list this change's actual commit(s). Revert only those explicit
SHAs, newest first, with `git revert`; never reset or force-push main. A previous
archive can instead be installed in a separate directory using the same external
workspace after backup, with only one application process using it at a time.
Code rollback does not delete or roll back user datasets, results or models.
For an immediate network-only restriction use `./run.sh --local-only`.
