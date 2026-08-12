# Localization Coverage Audit

Last updated: 2026-08-12

## Contract

Statistical Twin supports `en` and `ko`. English is the product default when
`statistical-twin.locale` is missing or invalid. Locale changes never remount
the workspace, alter routes, recalculate statistics, or translate user data and
technical identifiers.

The frontend inventory is produced from the TypeScript AST by
`scripts/check_frontend_localization.mjs`. At implementation time it contains
2,951 unique Korean source strings across 171 non-test files. Each source maps
to one canonical catalog key; the Vite transform replaces only static
application-owned literals. The custom JSX runtime resolves those typed keys
during render, so values read from datasets, files, columns, category levels,
notes, models, studies, and API identifiers are not translated.

## Inventory

| Area | Main sources | Previous hard-coding | Translation source | Variables / plural | Status | E2E |
|---|---|---|---|---|---|---|
| App shell | `App.tsx`, `AppChrome.tsx`, sidebar | Korean labels and aria text | catalog plus backend labels | health enum | localized | default/switch/mobile |
| Home | `ProjectOverviewPage.tsx` | headings, cards, empty states | catalog | counts | localized | en/ko screenshots |
| Datasets | preparation/profile/schema/preview panels | labels, validation, dialogs | catalog and localized API messages | rows/columns | localized | critical path |
| Analysis | shell, workbench, all method panels | method UI, tables, warnings | catalog, backend labels, warning codes | N/alpha/CI | localized | six-module smoke |
| Graphs | Graph Builder and `charts/**` | controls, SVG title/desc, tooltips | catalog | point counts | localized | graph workflows |
| Reports | Report Center and export panels | status, filters, actions | catalog | dates/counts | localized | HTML export |
| Assets | manage/catalog/detail panels | tabs, status, retention dialogs | catalog and API errors | dependencies | localized | management path |
| Help | Help Center, guidance, tutorial | long explanations and tags | catalog and backend labels | none | localized | preserved-input switch |
| DOE/Bayesian | factorial, LHS, RSM, optimizer, Bayesian | workflows, charts, states | catalog | trials/runs | localized | critical path |
| Regression/quality | prediction/optimizer/quality panels | results, warnings, chart aria | catalog and warning boundary | rows/signals | localized | critical path |
| Errors/status | API client and error helpers | raw backend messages | stable code plus safe fallback | code/request ID | localized | unit payload tests |
| HTML reports | backend export renderer | locale-fixed headings | backend report text | locale request | localized, schema 3 | en/ko API tests |

## Explicitly Not Translated

- dataset/file/model/study/report names, column names, factor and response names;
- category levels, user notes, pasted text, and raw cell values;
- method IDs, UUIDs, schema keys, error/warning codes, hashes, filenames, and
  canonical JSON/CSV headers;
- statistical symbols and units such as `p-value`, `R`, `VIF`, `PRESS`, `Cp`,
  `SHA-256`, `bar`, `kg/h`, and `%`.

## Enforcement

The localization check fails on missing/orphan keys, empty translations,
placeholder mismatch, Korean text in the English dictionary, or a Korean
frontend literal without a source mapping. Production E2E also scans visible
English text and `aria-label`, `title`, `placeholder`, and `alt` attributes for
Hangul using synthetic English-only data.
