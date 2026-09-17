# Grouped Mean Menu and Trusted LAN Validation

Date: 2026-09-18. Base: `43d20ae5580c3013276462e6b95bea16e42550d2`.
Branch: `feat/grouped-mean-menu-and-lan-dev`.

## Changes and boundaries

- The mean/equivalence landing page retains all ten executable method IDs and
  their original order, grouped into four semantic sections. Its existing
  blue cards, icons, planned item and collapsed selection guide remain.
- The installed ui-ux-pro-max heading-hierarchy guidance was applied; details
  are in `analysis_domain_navigation_implementation.md`. No other domain or
  sidebar taxonomy was redesigned.
- The default development entry point is `0.0.0.0:8600`, with a same-origin
  `/api` proxy to a loopback-only API. `-LocalOnly` disables LAN binding.
  Host/Origin checks, strict ports and build compatibility checks remain.
- API contract 21, metadata 20, all statistical methods/results/manifests and
  existing workspace assets are unchanged. No database migration or refit.
- No firewall/profile changes, authentication, RBAC or TLS were introduced.
  Read `trusted_lan_development.md` before admitting shared-workspace operators.
- The pre-existing untracked `examples/image2.png` was not modified or staged.
  `data_prd.md` was absent; the available addendum and instructions were read.

## Environment and commands

Actual validation host: Windows 10 Home (19045), PowerShell 5.1, CPython 3.10.11,
Node 22.23.2, CPU only. Windows 11 and a second physical client were not available.
Node 22 was prepended to PATH for npm and PowerShell entry points.
Native exit codes were captured and propagated after log redirection.
The LAN address below is parameterized; the actual private adapter address is
kept only in ignored local diagnostics.

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_dev_startup_contract.py backend/tests/unit/test_app_startup.py backend/tests/unit/test_analysis_domain_navigation_contract.py
npm --prefix frontend test -- --run src/analysisDomains.test.tsx src/SidebarNavigation.test.tsx src/runtimeCompatibility.test.tsx
npm --prefix frontend test -- --run src/analysisDomains.test.tsx src/devNetwork.test.ts src/App.test.tsx src/api/visualizations.test.ts
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend run build
.\.venv\Scripts\python.exe tests/e2e/lan_grouped_menu.py --lan-host $LanIPv4 --diagnostics .tmp/e2e-grouped-menu-lan-retry
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/e2e.ps1 -DiagnosticsRoot .tmp/e2e-grouped-menu-release
git diff --check
```

## Executed checks

- Baseline focused backend: 16 passed. Baseline navigation/runtime frontend:
  17 passed.
- Updated focused backend startup/app/domain checks: 17 passed (63.08 seconds).
- Updated focused frontend checks: 130 passed (10.19 seconds).
- Final navigation/runtime focused rerun: 19 passed (3.91 seconds).
- Complete frontend suite: 47 files / 361 tests passed (30.51 seconds).
- OpenAPI/frontend contract focused rerun: 214 passed (6.69 seconds).
- Standalone strict TypeScript, ESLint and production build passed. ESLint
  retained nine pre-existing Fast Refresh warnings; the build retained its
  large-chunk warning.
- Actual Wi-Fi IPv4 browser checks passed in Korean and English at 1440x900,
  1280x800, 1024x768 and 390x844. All ten menu routes, back/reload, keyboard,
  collapsed guidance, group counts and page overflow assertions passed.
- LAN runtime/API requests, same-origin mutation, hostile Host/Origin rejection
  and LocalOnly isolation passed. A virtual adapter was also checked separately.
- Full Chromium critical-path E2E passed with same-origin API proxying, including
  OLS/regularized/PLS/GPR models, PCA, DOE/BO, predictions, reports, revision
  history, graphs, imports, bilingual navigation and preserved drafts.
- Final `scripts/check.ps1` returned native exit 0: 1,225 backend tests passed
  in 1,380.80 seconds; 361 frontend tests across 47 files passed in 21.91 seconds.
  Tutorial synchronization (18 blocks), Ruff lint/format (260 files), mypy
  (158 source files), localization (2,964 sources / 3,835 keys), ESLint,
  strict TypeScript and production build (3.68 seconds) passed. Existing
  stderr build warnings did not change the native exit code.
- `scripts/test.ps1` was not separately duplicated: `check.ps1` executes its
  complete backend and frontend suites plus the additional static/build checks.
- Git diff whitespace checks passed. Remote CI is checked against the published
  SHA separately; local success is not reported as remote CI success.

## Diagnostics and corrected failures

Synthetic-only screenshots and logs are ignored local artifacts, not Git assets:

- `.tmp/e2e-grouped-menu-lan-retry`: eight bilingual viewport screenshots and
  `results.json`; desktop Korean and mobile English images visually inspected.
- `.tmp/e2e-grouped-menu-lan-virtual`: additional adapter check.
- `.tmp/e2e-grouped-menu-release`: complete proxy-based critical path.
- `.tmp/check-grouped-menu-lan-complete.log`: final full check log.
- `.tmp/e2e-gpr-ui-report-final/screenshots/compact-mean-domain-ko-1440.png`:
  archived prior-release comparison image, not a newly executed baseline capture.
  Compared with `mean-groups-ko-1440.png`: same palette/card treatment, named
  gray section bands instead of an ungrouped ten-card grid.

Initial checks exposed missing Node type declarations, absolute-URL expectations
in frontend tests, a single-grid assumption in E2E, and native E2E cleanup calls
without an Origin header. These were corrected while retaining path/payload,
navigation and deletion assertions. Browser response waiters now match the
frontend proxy origin rather than the private API origin; no statistical
assertion or response timeout was weakened.

The first full backend run also exposed a static route-ownership check scanning
test assertions as production API calls. The checker now excludes `*.test.ts`
while still scanning every production API module. Independent literal URL
expectations remain in the frontend tests, rather than comparing the route
helper to itself. Its complete 214-test contract file passed after correction.
The first full run finished with 1 failed / 1,224 passed in 1,662.25 seconds;
that result is not labeled as a full pass. A subsequent format preflight caught
mixed LF/CRLF in an edited test block; Ruff normalized only line endings before
the complete rerun.

One initial Wi-Fi free-port probe timed out. A later isolated test using the same
physical adapter passed; no firewall/profile was changed and the initial cause
was not established. Server-side LAN-address success does not prove that an
office firewall permits another physical PC. The current Wi-Fi profile was
Public, so IT-approved Private/Domain firewall scoping is still a deployment
prerequisite, not an application setting.

## Limitations and rollback

The targeted dependency patch removed the PostCSS/nanoid advisories. Four npm
audit findings remain in development tooling (two moderate, two high), involving
ESLint transitive dependencies and Vitest/mocker. This is not a clean security
audit; the Vitest server remains loopback. No unsupported package upgrade was
bundled with the menu change.

Use ordinary `git revert` on this task's individual commits, newest first, to
undo code without rewriting remote history. The UI commit can be reverted
independently from LAN startup. Code revert does not delete or restore workspace
data. No schema change in this task creates an older-reader incompatibility.
