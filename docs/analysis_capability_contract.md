# Capability and Guidance Consistency

## Scope

The A14 inventory joins existing implementation declarations. It does not add a
method, change a calculation/default, migrate metadata, read a workspace, or
rewrite results/models. Runtime versions are read from the actual constants;
see the [generated matrix](generated/analysis_capability_matrix.md).

Keep these independent dimensions distinct:

- Catalog availability is implementation availability, not current input eligibility.
- Dataset/model/analysis prerequisites are explicit and remain subject to live preflight.
- A supported option may have limits: frozen Phase II limits, full-design-only
  factorial selection, maximum factor/run counts, or an unavailable ratio CI.
- Report declarations say which stored schemas/variants readers understand. Only
  the exact stored-source capability determines `full`, `summary`, or `unsupported`.
- Historical-readable and stale are separate. Old revisions can remain readable;
  accepted schema declarations do not certify every historic artifact.
- Current non-menu subworkflows, legacy aliases, contextual explanatory items,
  visible planned items, and roadmap-only items are not extra executable menus.

## Authoritative Inputs

`backend/app/analyses/capabilities.py` reads the current registry, generic handler
specs and actual runner map. The small dedicated-entry bindings name actual
router functions; the generator parses their POST decorators/prefixes instead of
maintaining another URL list. Missing/duplicate/unknown bindings fail generation.
It does not import `app.main`, instantiate Settings, start lifespan, or open SQLite.

Report definitions are reused from `report_coverage`, `dedicated_report_renderers`,
`stored_prediction_report`, and `completed_prediction_report`. Renderer/core/variant
declarations are not copied into an independent frontend support allowlist.
Internal renderer IDs are associated with their real owner methods, not advertised
as new menu methods. Explicit `ReportSourceKind` values define source kinds.

`scripts/read_frontend_capability_metadata.mjs` uses the project's installed
TypeScript parser. It reads the canonical `ANALYSIS_DOMAINS` literal and guidance
object keys without executing application code. Calls, spreads, computed keys,
duplicate keys and malformed TS are rejected. Existing order and direct/family/
contextual placement are preserved; each catalog method must appear exactly once
and have guidance. Informational workflows remain separate and ordered.

The two generated UTF-8/LF files contain no timestamp, machine path, source SHA,
user data, runtime test pass count, or mutable workspace state:

- `frontend/src/generated/analysisCapabilities.json`
- `docs/generated/analysis_capability_matrix.md`

The frontend may consume limits and known subworkflow identities, but the live API
catalog remains authoritative for availability and prerequisites. The matrix never
enables an HTML action without exact source/hash/locale capability verification.

## Conditional-Policy Evidence

| Statement | Existing execution evidence |
| --- | --- |
| Normality has no grouping in this implementation | `analysis_runners_eda._reject_normality_grouping`; stable `normality_grouping_not_supported` |
| Graphical Summary uses numeric ungrouped input | `GraphicalSummaryOptions`; `_validate_graphical_summary_column` |
| ANOVA defaults to requested post-hoc, not significance gating | `OneWayAnovaOptions.posthoc_policy`; `one_way_anova` explicitly handles `after_significant` |
| Attribute Phase II needs eligible frozen limits | `AttributeControlChartOptions.validate_phase_dependency`; `attribute_control_phase_2` validation |
| Manual/backward factorial selection excludes aliased fractional/PB | `doe_factorial_analysis.create_factorial_analysis` rejects those option combinations |
| Brown-Forsythe does not provide a variance-ratio CI | `two_variances` returns `not_provided_by_selected_method`; no substituted F interval |
| DOE authoring limits | `core/doe_capabilities.py`, referenced by actual request schemas |

These bounded claims are checked against schemas/validators and existing method
fixtures. They do not imply comprehensive automatic inference of arbitrary Python
control flow. New conditional behavior needs a corresponding declaration, focused
test, and help update. No statistical validation is replaced by generator checks.

## Commands

After installing existing Python and Node development dependencies:

```powershell
.\.venv\Scripts\python.exe .\scripts\generate_capability_matrix.py --write
.\.venv\Scripts\python.exe .\scripts\generate_capability_matrix.py --check
node --test .\scripts\read_frontend_capability_metadata.test.mjs
.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_capability_matrix.py
```

`--check` is also the default: no files are written, and drift exits nonzero.
`--write` validates all inputs before atomically replacing only the two outputs.
The generator resolves paths from its own source location and requires neither
Git nor an internet connection. It never invokes analysis, CV, prediction, or a
data reader. Node is a development-time parser dependency, not a Linux Release
runtime dependency. Python-only unit tests consume checked-in presentation facts
and do not launch Node; explicit full-generation checks run in Node-equipped
Windows/Linux checks. This distinction keeps Python 3.11 compatibility CI honest.

## UI Boundaries

The installed `ui-ux-pro-max` skill's interaction/disabled-state guidance is applied
only to truthful compact labels: source-needed is not disabled, roadmap-only is
not currently executable, and report summary is not full. Existing colors,
density, hierarchy, navigation and input state are retained. No new design system,
chart library, icon package or remote dependency is introduced.

Corrected guidance is separate from calculation behavior: numeric ungrouped
Graphical Summary, ungrouped Normality, selected ANOVA post-hoc policy, conditional
Attribute Phase II, complete PCA/general-factorial help, existing factorial
variants, and actual LHS/BO limits. Korean/English render from static semantic keys;
user-entered names and request values are never translated.

## Verification Limits

Declaration, AST, deterministic-byte and drift tests are source consistency checks.
They are not numerical reference tests or evidence that every option/platform/UI
journey ran. Actual execution evidence remains in
[end-to-end remediation](end_to_end_remediation.md) and the
[journey matrix](remediation_journey_matrix.md). Historical report audit rows keep
their original scope rather than being relabelled as current full verification.
