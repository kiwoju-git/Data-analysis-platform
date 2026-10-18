# Dependency and Upload Boundary Remediation

## Scope (A03)

Preserve numerical pins, immutable artifacts and Windows Python 3.10 / Linux
3.11 / 3.12. Reject oversized and malformed requests before application storage,
preserve typed File/OpenAPI binding, and keep worker-owned files alive through
cancellation. A committed upload is not deleted because its browser disconnected.

## Dependency Review, 2026-10-18

| Dependency | Previous | Selected | Reason |
|---|---|---|---|
| FastAPI | 0.115.6 | 0.135.4 | Python >=3.10, compatible with Starlette >=0.46; no mandatory telemetry dependency. |
| Starlette | 0.41.3 | 1.7.0 | Last Python 3.10-compatible release; reviewed upload/Range and later advisories. |
| annotated-doc | absent | 0.0.4 | Required FastAPI dependency; MIT, universal wheel, no additional dependencies. |
| pip | 26.1.2 | 26.2.1 | GHSA-qwm4-qh6w-59xr; installer tooling, including offline wheelhouse. |
| setuptools | venv seed 65.5.0 | 83.0.0 | GHSA-r9hx-vwmv-q579, GHSA-5rjg-fvgr-3xxf, GHSA-cx63-2mw6-8hw5, GHSA-h35f-9h28-mq5c. |
| pytest | 8.3.4 | 9.0.3 | GHSA-6w46-j5rx-g56g, dev-only temporary-directory issue; adds required Pygments. |
| Vitest | 4.1.9 | 4.1.12 | GHSA-82fw-gwwq-j7x9, mock redirect file-read boundary. |
| typescript-eslint | 8.18.2 | 8.71.2 | Removes vulnerable fast-glob/micromatch/braces chain (GHSA-vfj7-8cjw-p6xm). |
| brace-expansion / js-yaml / source-map-js | old transitive pins | patched compatible pins | Targeted CPU/stack/expansion denial-of-service fixes, no forced major update. |

FastAPI/annotated-doc use MIT and Starlette BSD-3-Clause. No GPU, external service,
CDN or application telemetry is added. Numerical pins are unchanged: NumPy 2.2.6,
SciPy 1.15.3, scikit-learn 1.7.2, joblib 1.5.2, threadpoolctl 3.6.0.

Official references:
- [FastAPI metadata](https://pypi.org/pypi/fastapi/0.135.4/json),
  [release notes](https://fastapi.tiangolo.com/release-notes/),
  [Starlette metadata](https://pypi.org/pypi/starlette/1.7.0/json).
- [GHSA-7f5h-v6xp-fcq8](https://github.com/advisories/GHSA-7f5h-v6xp-fcq8),
  [GHSA-2c2j-9gv5-cj73](https://github.com/advisories/GHSA-2c2j-9gv5-cj73).
- Further Starlette findings: GHSA-82w8-qh3p-5jfq, GHSA-jp82-jpqv-5vv3,
  GHSA-wqp7-x3pw-xc5r, GHSA-x746-7m8f-x49c, GHSA-86qp-5c8j-p5mr.
- [Vitest advisory](https://github.com/advisories/GHSA-82fw-gwwq-j7x9),
  [braces advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm),
  [source-map-js advisory](https://github.com/advisories/GHSA-68fv-2mgg-jv7q),
  [js-yaml advisory](https://github.com/advisories/GHSA-2883-xcg3-v3hh).

Starlette 1.8 drops Python 3.10. Its additional multi-range EOF fix
([upstream PR](https://github.com/Kludex/starlette/pull/3583)) is mitigated here by
limiting built-UI FileResponse to one range. Multiple ranges fall back to full
200; single ranges retain 206. Tests forbid entering the multi-range handler,
including an EOF range. This is a scoped mitigation, not a Starlette 1.8 backport.

## Locks and Security Gate

Five native wheel locks were generated in
[run 39088021308](https://github.com/kiwoju-git/Data-analysis-platform/actions/runs/39088021308):
Windows 3.10 dev and Linux 3.11/3.12 runtime/dev. Each installed with hashes,
wheel-only and `pip check`. Old transitive pins are preserved except security
updates and their required dependencies. No Windows wheel hash was reused for
a Linux platform wheel.

`scripts/dependency_security.py` verifies the exact installed inventory against
the lock, runs `pip check`, then pinned pip-audit 2.10.1 from a separate tool venv
with `--path --strict`. The target contains no editable application. Auditor
inventory is separate. Empty, skipped, mismatched or failed audits fail the gate.
No advisory exceptions exist. Future exceptions require ID, scope, rationale,
owner and expiry; blanket ignore flags are not an accepted policy.

Interpreter paths are made absolute without dereferencing venv executable
symlinks. In candidate run 39090939567 (source 5839914), all four Linux security
jobs stopped before pip-audit because the CLI resolved both venv Python paths to
the hosted base interpreter. The uploaded inventory confirmed the base toolcache
site-packages, not the installed hash-locked target. This failed run is not a
clean security audit. A portable CLI regression and a Linux real-symlink venv
test guard this boundary; native audits must be rerun on the corrected commit.

CI covers all five Python profiles and npm runtime/all profiles. Windows has one
combined dev lock containing runtime dependencies, not a separate runtime-only
environment. The aggregate requires every audit to succeed. Only public package
names/versions are sent to advisory services; no user data. Audits are online
development/CI checks, not an online requirement for the installed product.

Vite's approved LAN use makes the development dependency tree relevant. Vitest
mock plugins are not registered in the application server; they were patched,
not exempted. npm 10.9.8 encountered an Arborist optional-peer resolver error
during the update. npm 12.2.0 generated the lock; npm 10.9.8 subsequently passed
`npm ci`. Node 22 remains supported. New ESLint identified redundant fixture
assertions; only these and an unused type import were removed.

## Intake Policy

`GET /api/v1/datasets/intake-limits` exposes actual settings. Registration shows
file, pasted UTF-8, serialized JSON and parsed dimensions in both locales.
Lookup failure displays retry, not an invented default.

| Environment setting | Default | Boundary |
|---|---:|---|
| DATALAB_MAX_UPLOAD_BYTES | 104857600 | One file or pasted UTF-8 text; existing allowance unchanged. |
| DATALAB_MAX_REQUEST_BYTES | derived | 6 x upload cap + overhead, preserving worst-case JSON escaping; explicit override supported. |
| DATALAB_MAX_MULTIPART_OVERHEAD_BYTES | 1048576 | Upload HTTP cap = file + overhead, bounded by total request cap. |
| DATALAB_MAX_MULTIPART_FIELDS | 16 | Ordinary field count; exactly one file allowed. |
| DATALAB_MAX_MULTIPART_FIELD_BYTES | 65536 | Per ordinary field; per-part headers separately capped at 16 KiB. |
| DATALAB_MAX_DATASET_ROWS | 1048576 | New, visible parsed-data limit before version/artifact creation. |
| DATALAB_MAX_DATASET_COLUMNS | 16384 | New, visible parsed-data limit before column inference allocation. |

Parsed limits are a new explicit safety policy, configurable by the operator.
They do not guarantee every admitted dataset fits every machine/statistical
method. No truncation/sampling; no revalidation or rewrite of saved datasets.
XLSX's existing 500 MiB decompressed-size and compression-ratio caps stay separate.

Pure ASGI receive counting does not trust Content-Length. Declared or streamed
overflow returns stable 413 codes. The route parses multipart once with strict
limits and checks the final boundary (not validated by the underlying finalizer).
Disconnect/error closes even spools not yet listed in FormData.

`await_owned_io` protects spool write/seek/close and the complete upload
write/hash/fsync/rename/sniff/metadata thread worker. Cancellation waits for owned
I/O before file cleanup, but does not shield waiting for more network input.
Unexpected errors remain errors; uncommitted storage/parsing failures clean files.

LAN defaults, `--local-only`, narrow Host/Origin/CORS and firewall policy remain.
Host/Origin is not authentication: admitted peers share the same workspace and
can edit/delete shared assets. Authentication/RBAC/TLS remain deployment gates.

## Validation Evidence

Local evidence: `.tmp/remediation-a03-security` and native artifact records under
`.tmp/remediation-generated-locks-v2`, outside Git. Windows strict candidate
audit, `pip check` and npm runtime/all audits passed at lookup time. All native
lock installations passed; this is not a complete application/Release claim.

Focused upload/static/security checks: 34 passed / one Windows symlink privilege
skip. Subsequent CSV/XLSX dimension and parser cancellation tests: 49 passed.
Frontend Vitest: 57 files / 404 tests passed. Full Windows Chromium critical path
passed with ports 8033/5233 (`scripts/e2e.ps1`, diagnostics
`.tmp/e2e-remediation-a03`). Whole checks and candidate CI remain pending until
recorded in the main remediation ledger. No A03 main
push or Release publication has occurred.

The same candidate Linux application run had 1398 passes, 11 skips and one
failure: the new `datasetIntakeLimits` frontend route was missing from the
backend OpenAPI operation contract table. The GET path and response schema are
now registered in that table; no application route or intake policy changed.

Post-fix focused Windows checks (the A03 worktree's own Python 3.10 environment):
`python -m pytest backend/tests/unit/test_dependency_security.py
backend/tests/unit/test_openapi_frontend_contract.py -q` passed 220 tests, skipped
the one Linux-only real-symlink test, and emitted two existing Starlette
deprecation warnings. The portable interpreter-path regression failed before
the fix and passed afterward. Targeted Ruff lint/format checks passed. These
results do not replace the required full-check and native Linux audit reruns.
