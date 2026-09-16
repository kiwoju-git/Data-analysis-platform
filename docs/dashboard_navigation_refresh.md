# Dashboard and navigation refresh

## Scope and acceptance

Base: `45e266542afb012dbb2a5b83a9f94dd134419758` on origin/main.
Branch: `feat/dashboard-navigation-refresh`.

- Top-level Analysis and Graphs labels open their workspaces, like Home shortcuts.
  Disclosure controls remain independently keyboard-operable and never navigate.
- Home contains six quick actions, eight existing analysis domains, then current
  dataset, dataset status, recent analyses, and model/report information.
- Reuse graph-type blue selection tokens, small decorative icons, compact text,
  and responsive grids. Preserve Korean/English, empty/loading/error states,
  dataset context, browser navigation, and existing statistical workflows.
- Verify desktop 1440/1280 and mobile 390 layouts, keyboard navigation, labels,
  selected colors, no page overflow, and real route transitions with Chromium.

## Design and risk decisions

Applied the installed ui-ux-pro-max skill: analytics dashboard design-system
search (density 8) and React/accessibility guidance. Its Data-Dense Dashboard
style fits this operational tool; marketing hero, remote fonts and CTA guidance
do not. User references inform icon-led entries, white/gray surfaces and a
quiet workspace overview, not copied artwork or large decorative cards.

No statistics, request/result contracts, method IDs, metadata schema, storage,
or checksums change. Main risks are navigation versus disclosure ambiguity,
lost dataset query context, KOR/ENG wrapping, and disabled methods appearing
executable. Existing handlers/catalogs remain the source of truth. No raw data,
workspace, or screenshot is committed. The absent root data_prd.md was noted;
the present addendum and implementation/navigation contracts govern this change.

## Dependency review (before installation)

`lucide-react` 1.46.0: one pinned icon-only dependency, no runtime dependencies
other than its React peer (supports the installed React 18). Pure JS/inline SVG,
no native binary, Python dependency, GPU, telemetry, CDN, or runtime network.
The existing app has no icon library; a coherent accessible icon set avoids
hand-drawing and duplicating individual paths. ISC, with MIT notices for
Feather-derived icons. Package unpacked size reported by npm: 35,021,074 bytes;
only statically imported icons are shipped by the production tree shaker.
Bundle impact and npm audit are checked after installation. No unrelated
dependency upgrade is intended.

Sources: [React package](https://lucide.dev/guide/react),
[license](https://lucide.dev/license). The project is actively publishing;
npm metadata and final lockfile pin the exact reviewed version.

## Validation

Baseline frontend: 44 files, 333 tests passed. This UI-only change requires no
migration. Host: Windows 10 Home 19045, PowerShell 5.1, Python 3.10.11,
Node 22.23.2. A separate Windows 11 device and other browser engines were not
available; Chromium was tested at 1440x900, 1280x800, 1024x768 and 390x844.

The first new browser pass found a locale-dependent selector in the test;
language switching is now selected by the stable KOR/ENG controls. The next
pass correctly failed an old assertion for the shortened Home subtitle; that
assertion was updated. Neither failed attempt is counted as a passing suite.
The third pass reached the existing final visual checks and found their old
direct-child sidebar selector. It now checks the selected group heading,
which contains the separate navigation and disclosure buttons.
Localization subsequently detected five unused source-fragment mappings after
shortening Home copy. Only those mappings were removed (existing translations
retained); the complete localization check then passed.

Dependency audit: `npm --prefix frontend audit --omit=dev` passed with zero
findings. Full `npm audit --json` reports six existing development-tool findings
(two moderate, four high: Vitest/mocker, brace-expansion, js-yaml, nanoid,
PostCSS). Lucide adds no audit findings or transitive runtime dependency. These
unrelated development-tool upgrades remain a separate maintenance task. npm's
incidental removal of Linux `libc` metadata was restored, keeping the lockfile
change limited to Lucide.

### Executed commands

The local Node 22 directory was prepended to PATH before npm/PowerShell checks.

```powershell
npm --prefix .\frontend test -- --run
npm --prefix .\frontend run typecheck
npm --prefix .\frontend run lint
npm --prefix .\frontend run build
npm --prefix .\frontend audit --omit=dev
npm --prefix .\frontend audit --json
node .\scripts\check_frontend_localization.mjs
.\.venv\Scripts\python.exe -m ruff check tests\e2e\dashboard_navigation.py tests\e2e\refined_ui.py
.\.venv\Scripts\python.exe -m ruff format --check tests\e2e\dashboard_navigation.py tests\e2e\refined_ui.py
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-diagnostics-dashboard-refresh
git diff --check
```

- Full-project backend: 1,166 tests passed in 1,718.10 seconds. The complete
  existing statistical/reference/API/storage suite ran, not only UI contracts.
- Final Vitest: 44 files / 335 tests passed in 23.49 seconds in the full gate
  (also 30.93 seconds in the earlier standalone run).
- Focused App/Sidebar/domain tests: 114 passed; strict TypeScript passed.
- ESLint: zero errors, seven preexisting Fast Refresh helper-export warnings.
- Production build: 4.82 seconds in the full gate; explicitly captured native
  exit 0 on the subsequent 3.70-second build. Main chunk 633.90 kB / 162.25 kB
  gzip; shared runtime/catalog chunk 705.74 kB / 263.06 kB gzip. Vite reports
  existing large-chunk and localization plugin timing warnings. These totals
  are the resulting bundle sizes, not an isolated measurement of icon cost.
- Ruff lint/format for the new navigation E2E and adjusted visual test passed
  after normalizing formatting; `git diff --check` passed.
- Localization: 2,964 source strings and 3,811 matching KOR/ENG keys passed.
- Complete Chromium E2E: exit 0. Includes prior regression/GP/DOE/Bayesian,
  export, restore, bilingual UI, retained drafts and responsive critical paths.
- `check.ps1` completed all stages above, plus 18 tutorial blocks, backend Ruff
  lint/format (253 files) and mypy (154 files). The outer PowerShell 5.1 `*>`
  log-capture invocation returned 1 after Vite wrote warnings to stderr; it is
  not reported as a clean wrapper exit. No stage reported a failed check.
  The build was rerun with `$buildExit = $LASTEXITCODE; exit $buildExit`, which
  explicitly returned 0. Future log captures should preserve native exit codes
  or use separate stdout/stderr process streams. `test.ps1` was not run
  separately because it duplicates the complete suites already executed.

Diagnostics remain ignored under `.tmp/e2e-diagnostics-dashboard-refresh`:
`screenshots/dashboard-refresh-{ko,en}-{1440,1280,1024,390}.png`,
`screenshots/analysis-domain-refresh-{ko,en}-{1440,1280,1024,390}.png`,
`screenshots/navigation-graph-types.png`, and `refined-ui/` including measured
regression-card bounds. Failed-attempt screenshots are historical, not passes.

## Source inventory and rollback

- Shared presentation: `AnalysisDomainGrid.tsx`, `components/NavigationIcon.tsx`,
  `dashboardNavigation.css`, `App.css`, the domain method/family/landing cards,
  `GraphBuilderPage.tsx`, and `ProjectOverviewPage.tsx`.
- Navigation wiring: `App.tsx`, `AppChrome.tsx`, `WorkspaceRouter.tsx`,
  `SidebarNavigation.tsx`, and `sidebarNavigationModel.ts`.
- Contracts and checks: paired keys in `i18n/catalog.generated.json`, frontend
  App/Sidebar/model tests, `tests/e2e/dashboard_navigation.py`, `critical_path.py`,
  `refined_ui.py`, package manifests, README, navigation/E2E/CI documentation.
- No backend/statistical source, result/model schema, API version, database
  migration, user dataset, or stored artifact changes. API 20 / metadata 20
  remain unchanged. Preexisting untracked user files are not staged.

The UI release is a standalone commit on `feat/dashboard-navigation-refresh`.
Reverting that commit restores the prior UI/dependency without rewriting Git
history or touching stored analyses. Main publication uses a fast-forward and
ordinary push, followed by local/remote SHA verification.
