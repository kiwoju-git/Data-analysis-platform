# Gage Part Identity Fix

Baseline: `21ccddc99250f69fd10e15379eddec63aa2da539` (fetched origin/main).
Branch: `fix/gage-part-identities`. User files/workspaces are not test inputs.

## Acceptance And Risks

- Original canonical part IDs are displayed and persisted, with natural display
  order 1,2,...,10. `1` and `01` remain distinct categorical identities.
- ANOVA/pooling/component calculations, grouping and filter snapshots are unchanged.
- All six charts, saved restore and stored-only HTML share the same ID/index mapping.
- Legacy results remain unchanged; missing original IDs cannot be reconstructed.
- New part IDs are intentionally visible in local result/report artifacts; operator
  and replicate IDs remain redacted. No new logging, telemetry or source reload.
- No SQL/dependency change. API29, Gage0.3.1/result4/plot2, renderer2.3.1;
  metadata24 unchanged. Existing UI/chart interaction and numeric formatting remain.
- Natural order is not numerical interpretation of negative/scientific-looking IDs.
  No case folding, numerical coercion or silent identity truncation is introduced.

## Cause And Evidence

`prepare_gage_data` sorted full strings, so 1,10,2,...,9 was legitimate lexical
order. `build_gage_rr_plot_bundle` stored only the resulting index; UI/report
then labeled index+1 as Part N. Original10 could therefore appear as Part2.
The defect was display identity, not merged groups or swapped measurements.

The synthetic60-row reproduction has ten parts, three operators, two repeats.
Original10 occupied plot index1. All60 source-row joins and30 cell means were
correct. Renaming IDs to zero-padded names kept retain/auto_pool ANOVA/components
exactly equal. An initial exact row-shuffle equality probe differed only in
total SS by2.91e-11; the follow-up explicitly used relative1e-14/absolute1e-12.
No production tolerance or statistic was changed. Actual user data was not supplied.

## Implementation And Validation Ledger

| Boundary | Current evidence |
| --- | --- |
| Source/cause | source-confirmed; reproduced with synthetic1..10 IDs |
| Backend identity | fixed; pre-fix two red cases; 59 focused tests green on local Windows3.10; exact pre-fix statistical payload digest matched there, not a cross-platform bitwise guarantee |
| UI | fixed; 37 focused tests green; original10 means68/raw-row55; separate01/1, long/Korean/escaped IDs; legacy DisplayN |
| HTML | fixed; 25 renderer and 36 coverage tests green; full IDs/means, escaped long IDs, malformed identity rejection |
| Legacy/API/source | 73 focused API/calculation tests green; real CSV/filter/report, schema3 frozen bytes; no source reread/refit |
| Wider reports | 72 tests passed, 2 Windows symlink skips; not browser evidence |
| Release receipt/runtime tests | 44 passed, 1 platform-specific skip; synthetic receipt rejection is not archive installation evidence |
| Static/build | full backend Ruff and mypy243files; frontend tsc/Vite build passed |
| Native Windows/Linux/Python compatibility | final-commit CI receipts are required before publication; not yet executed at this ledger commit |
| Exact Linux archive/offline/restart/report | final-commit archive receipts are required before publication; not yet executed at this ledger commit |

Commands/results and final release receipt will distinguish source/unit/API,
built-browser and exact-archive checks. Historical successful runs are not current
evidence. Final archive receipts are release assets, avoiding a source-SHA cycle.

### First Native Attempt

CI [41859324549](https://github.com/kiwoju-git/Data-analysis-platform/actions/runs/41859324549)
on1822844 failed before browser execution: Linux3.12 had three failing tests,
3248 passed/16 skipped; Python3.11 had the stale tutorial schema expectation and
one statistical JSON fingerprint mismatch. Remaining jobs were cancelled only
after those failures were recorded. This run is not release evidence.

The tutorial test still expected result3/plot1 and its warning fixture still
described all IDs as redacted. Those expectations are corrected to result4/plot2
and operator/replicate-only redaction; numeric reference values are unchanged.
The byte fingerprints were captured on Windows3.10 and are not valid universal
floating-point guarantees. Native tests instead isolate plot-order changes in
the same runtime and retain the independent hand-checkable numerical assertions.
No production calculation or numerical tolerance is relaxed. The failed logs
contain hashes, not field-level differences, so no specific math-library cause
is asserted. Final-source gates must all succeed before main/release publication.
After correction, 70 focused Gage tests and all11 tutorial tests passed locally.
The independent ANOVA algebra uses a60*ulp(2048) SS roundoff budget (below the
existing1e-10 gate), relative1e-12 for components/p-values and absolute0 for tiny
p-values; same-runtime plot-order statistical equality remains exact.

The built-browser journey now uses original CSV part IDs1..10, asserts every
visible main/interaction axis label, the accessible full-ID table, part10's
stored mean68 and keyboard tooltip. It repeats source/ID/value checks after
saved-result restoration, both locales and two archive restarts. Downloaded
HTML is checked for original axis/table IDs and part10 mean68 after server
shutdown. These assertions are mandatory archive receipts, not merely screenshots.

## Compatibility And Rollback

Reopening a legacy result does not repair missing IDs. Explicitly run a new analysis
from its intended dataset/filter to obtain part IDs; preserve the old artifact.
Revert only this task's commits, latest first, with `git revert <commit>` after
reviewing later dependent changes. Do not reset/force-push or delete workspaces,
datasets, models or results. Older code may not read new result4/plot2 artifacts;
code rollback does not rewrite them or downgrade metadata. No rollback is executed.
