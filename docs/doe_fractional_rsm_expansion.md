# DOE Fractional and RSM Expansion

## Baseline and Acceptance

BASE_SHA: `391539438c1b80e6c615dc99a0f56cd7fc45c7b6`.
Branch: `feat/doe-fractional-rsm-contours`.
`origin/main` and local HEAD matched after fetch. User-owned
`examples/image2.png` is untracked and excluded. `data_prd.md` is absent.

Implement A through L in the requested order. Acceptance includes actual
regular-fraction second-order matrices and disclosed alias representatives,
hierarchy-safe selection, explicit lack-of-fit inference availability, shared
CCC/CCI/CCF coding, final-model-only prediction/plots/optimizer, immutable legacy
readers, and exact-source Linux release validation. No existing workspace or
artifact is rewritten. API 25 is reserved for the completed integrated contract;
metadata remains 22 unless a real storage migration is required.

Risks: response/source races; alias versus rank/saturation confusion; zero pure
error; post-selection inference; legacy CCI coding; optimizer/model divergence;
contour holes/axis orientation; dependency wheels on every supported platform.
No main push or prerelease publication until required checks succeed.

## Evidence Ledger

| Stage | Code inspection | Implementation | Verification |
| --- | --- | --- | --- |
| A response/context | Blank response uses `Number`; edits do not invalidate; history failure shares save catch | strict shared parser, source epochs/request lanes, independent history retry | 37 focused frontend tests, typecheck, targeted lint; browser pending |
| B alias | Existing contract reviewed | pending | not run |
| C fractional estimability | Historical main-only restriction confirmed in contract | pending | baseline only |
| D selection summary | scoped implementation planned | pending | not run |
| E lack of fit | physical replication policy retained | pending | baseline only |
| F compact plots | existing interaction/frame preserved | pending | not run |
| G CCC/coding | current CCI-only transform contract reviewed | pending | baseline only |
| H center recommendation | conditional product default specified | pending | not run |
| I RSM terms/selection | full-quadratic-only contract reviewed | pending | baseline only |
| J contour | official dependency API review started | pending | not run |
| K integration/legacy/report | current ownership contracts reviewed | pending | not run |
| L CI/main/release | no publication yet | pending | not run |

## Baseline Checks (Windows, 2026-10-20)

Use current locked Python environment with `PYTHONPATH=<repo>/backend` and
OMP/OpenBLAS/MKL threads set to 1.

- `pytest backend/tests/unit/test_response_surface.py
  backend/tests/unit/test_factorial_analysis.py
  backend/tests/unit/test_factorial_model_workflow.py
  backend/tests/unit/test_term_block_model_selection.py -q`: **41 passed**.
- `npm --prefix frontend test -- --run src/doe/doeResponsePaste.test.ts
  src/FactorialModelWorkflow.test.tsx src/GeneralFactorialDesignPanel.test.tsx`:
  **30 passed**, 3 files.

These are narrow baseline tests, not whole-product or archive verification.

## A Implementation and Checks

`parseDoeResponseNumber` reuses the paste parser's decimal/scientific syntax;
`parseRsmResponseDraft` requires the exact complete run identity set. It rejects
empty/whitespace/nonfinite/partial numeric text while preserving genuine zero.
`createRsmRequestContext` composes existing source and latest-request guards.
Design/response edit handlers invalidate synchronously; create/save/analyze
snapshot their payload/source identities. Stale success/error/finally handlers
cannot apply. History has a separate lane, loading/error state and retry action.
Saved revision identities survive history failures. No API or calculation changes.

- New test file initially failed to import its not-yet-implemented helper. This
  is test-first evidence, not an actual browser reproduction of the old defect.
- Focused response parser/context/paste tests: **37 passed**, 3 files.
- `npm --prefix frontend run typecheck`: passed.
- Targeted ESLint for the six changed/new TS/TSX files: passed. An earlier
  invocation used an incorrect relative Node path and did not run ESLint.
- `node scripts/check_frontend_localization.mjs`: passed, 2875 source strings
  and 4151 translation keys at this stage.
- `ruff check tests/e2e/rsm_context.py`: passed. The formatting check initially
  required formatting; `ruff format` applied it.
- `tests/e2e/rsm_context.py` is connected to the context/full suites. It uses
  actual synthetic design/save/analysis API responses with delayed delivery,
  verifies blank rejection/zero/save-plus-history-failure/stale completion, and
  checks the committed obsolete analysis remains readable.
- Browser test **not executed yet**: a hidden Vite startup command on isolated
  port 5271 was denied by tool execution policy. No test success inferred from
  source inspection. Separate test backend/workspace is outside the repository.

## UI Guidance

Installed `ui-ux-pro-max/SKILL.md` consulted. Targeted UX search
`long summary text wrapping` selected Long Token Wrapping: shrinkable grid/flex
children and `overflow-wrap:anywhere`, not global `nowrap` or truncation of
stop reasons. Keep existing statistical workbench tokens and density.
React search returned effect cleanup/dependency guidance; React 19-only Actions
and Effect Events are not applicable to this repository's React 18.3.1.

## External References

- [Minitab factorial stepwise](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/analyze-factorial-design/methods-and-formulas/stepwise/):
  saturated initial pooling is separate from p-value elimination.
- [NIST CCD definitions](https://www.itl.nist.gov/div898/handbook/pri/section3/pri3361.htm):
  CCC cube bounds and CCI axial bounds have different coding.
- [ContourPy 1.3.2 metadata](https://pypi.org/project/contourpy/1.3.2/):
  Python >=3.10, BSD-3-Clause, native wheels; not claimed to be latest.
- [ContourPy line types](https://contourpy.readthedocs.io/en/v1.3.2/user_guide/calculate/line_type.html):
  server geometry must use an explicit serial output format.

No identical-data Minitab output has been provided; independent numerical
fixtures will not be described as a Minitab binary-output comparison.
