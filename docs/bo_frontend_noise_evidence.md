# BO Noise-Aware Frontend Contract and Evidence

## Preserved Behavior

- The existing sequential UI still sends a one-item batch; there is no second single-target form.
- Legacy recommendation and mean-fantasy batch readers/rendering remain separate from V2.
- The existing study lifecycle, trial observation inputs, immutable history, dense settings tables,
  result tables, and shared number formatting are retained.
- No external calls, telemetry, new dependencies, model calculations, or automatic observation values
  were added to the frontend.

## New V2 Boundary

`useBayesianRecommendationState` snapshots the current history ID/hash and sends schema 2 through
the existing batch endpoint. Noise settings are `estimate` (default), raw-unit fixed measurement SD,
or `near_noiseless`. Advanced bounds are standardized-Y variances, not SD or jitter. Exact replicate
compression is explicit; nearby diagnostics require factor-specific tolerances and do not merge data.
The existing search defaults are retained with the V2 MC policy; sample count and optional normalized
batch distance are explicit settings.

`boNoisePolicy` rejects empty/partial/nonfinite numeric strings, reversed bounds, out-of-bounds initial
variance, fractional sample counts, and missing nearby tolerances. Each invalid field has an associated
accessible error. The global `formatLocaleNumber` defaults and model values are not changed.

Changes to requested policy/options and study history invalidate pending creation. Success, error and
finally all check request ownership. Returned study/history/hash are checked before applying results.
Locale and viewport are not request sources. Stored results remain identified as committed snapshots
when settings are edited; the stored result is not recomputed or relabeled as the draft.

`BayesianNoiseBatchResult` separates observed best, latent incumbent, base-posterior mean, latent SD,
new-observation predictive SD, and conditional planning SD. Raw-unit and standardized acquisition values
are separately labeled. MC seed is a string, avoiding JavaScript's integer precision limit. Raw N,
unique-condition N, effective training N, group members, within-group variation, nearby distances,
constraint status, all-zero acquisition status, and saved warnings remain visible.

## Explicit Replicates

`useBayesianReplicateState` and `BayesianReplicatePanel` require a completed parent, count 1-8,
available trial budget, active/no-pending lifecycle, and explicit intent confirmation. New trials use
the same coordinates and retain their parent identity; the existing observation table receives their
actual, independently entered measurements.

A failed or disconnected POST is not automatically repeated. An explicit retry preserves the exact
request ID and payload. The original server commit is not deleted. A successful registration is shown
independently of a subsequent trial-list refresh failure. `bayesianRequestId` uses Web Crypto UUID or
cryptographic random bytes on HTTP LAN; it never substitutes `Math.random`.

An idempotent replay can return the current completed or abandoned state if an operator has already
entered the replicate observation. The hook accepts these terminal states only on replay, preserves
study/version/parent/history ownership checks, and requires finite observations only for completed
trials. A new registration must still return pending trials with no invented observation.

## UI Guidance

Installed `ui-ux-pro-max` was applied narrowly: explicit form labels, field-linked errors, controlled
React inputs, secondary replicate commands, progressive advanced settings, and existing product tokens.
No replacement design system or layout-wide refactor was introduced.

## Verification Evidence

Executed on the Windows worktree during implementation:

- Vitest: `src/features/bayesian` plus `src/asyncHookState.test.ts`, 212 tests passed at the recorded
  run. Covers strict policy inputs, KO/EN static markup, tiny values, escaped user identity, preserved
  payloads, q1 target routing, option/history request races, prior finally protection, explicit replicate
  retry identity, terminal-state replay, inconsistent ownership/observation rejection, and stale
  replicate responses. This is not browser evidence. Before the terminal-state fix, the new tests
  reproduced two failures (completed/abandoned replay); the pending replay case already passed.
- Targeted ESLint: BO feature directory and BO API/type files passed.
- Whole frontend TypeScript check passed after the concurrently updated GPR types were connected.
- Python tests: release receipt and E2E suite-partition tests, 247 passed at the recorded run.
- Ruff: changed BO E2E and release-verification Python files passed.

New executable browser fixtures, **not executed locally by this subtask**:

- `tests/e2e/bo_noise_extension.py::verify_bo_noise_extension`: API-only synthetic initial provisioning,
  then visible q1 target, q2 joint batch, actual observation inputs, replicate registration, exact
  compression (raw 9/effective 7), KO/EN 1024/1440, restore, and no POST on locale/resize/restore.
- `verify_bo_noise_context`: server commits a replicate POST while the client receives a synthetic
  connection failure, then explicit identical retry proves no duplicated trials or altered history.
- Both are wired into distinct native workflow/context stages and the exact built Linux archive
  browser harness. The release verifier rejects missing/incomplete receipts.

Local dev/server startup had already been denied in the parent task; this subtask did not retry it.
Browser layout, native CI, archived installation, performance and release publication remain separate
gates owned by the parent integration. A fixture definition or static markup pass is not a passing
browser/release claim. Full frontend checking is also an integration gate while GPR files change.

## First Native Browser Attempt

CI run `39613148814`, source `1c178d33444d185625418f5bb71270d39d1aa1df`, ran the early Linux
context suite on Python 3.12.15 / Chromium 149.0.7827.55. Its BO child failed before opening the app:
the synthetic study-creation POST lacked an `Origin` header and the development origin guard
correctly returned `dev_origin_not_allowed`.

The actual child `failure.json` and Playwright `trace.zip` in artifact `12352071489` were inspected.
They show `about:blank`, no mounted root or page errors, and the headerless API POST at `_seed`.
This is a test-fixture defect, not evidence that the replicate UI ran or failed. The guard was not
weakened. Synthetic study POST and observation PUT requests now supply the exact test server origin,
matching the other guarded E2E fixtures.

`test_bo_noise_e2e_fixture.py` reproduced both loopback/LAN-base failures before the fix. Afterward,
the fixture and suite-partition checks passed 74 tests; Ruff passed for both changed files.
At this first-run checkpoint the corrected native browser journey was still pending. The workflows
job in this first run stopped earlier in a GP surface locator and did not reach the BO workflow.

## Subsequent Linux Browser Evidence

Early-browser CI run `39616780776`, source `20a5b1f973986cd17dc0dc1e71df7cdc7d72f4c3`, subsequently
executed both BO fixtures on Ubuntu 24.04 / CPython 3.12.15 / Playwright Chromium. This is native
source/Vite browser evidence, not an exact Linux release archive or a Windows browser pass.

- Context job `119279871974`: the complete browser suite step succeeded. Its BO child performed a
  server-committed replicate POST followed by a simulated client-side 503, then an explicit identical
  retry. The assertions verify replay, a single new pending trial, unchanged completed history, and
  identical request ID/payload. Artifact `12352668604` contains the completed BO child trace.
- Workflows job `119279871375`: `verify_bo_noise_extension` returned successfully before the runner
  continued through the legacy workflow and later failed in the separate GPR regression stage. The
  BO fixture exercised visible q1 target / q2 joint batch / individual observation entry / two
  replicates / exact compression (raw 9, unique and effective 7), source-history preservation,
  predictive-minus-latent variance, KO/EN at 1024/1440 CSS pixels, reload, and no new POST caused by
  locale/resize/reload. Artifact `12353896147` contains its completed child trace and all four BO
  screenshots, with no BO child failure record.

The workflow failure is retained as a full-product gate failure. Successful BO stages do not turn the
whole run, release-ready gate, or archive validation into a pass. At that source commit, the
critical-path runner consumed the fixture's assertions without persisting its returned receipt; the
exact-archive harness separately persisted and validated that receipt.

A subsequent test-only change writes `bo-validation-receipt.json` after either BO fixture succeeds.
Its allowlist contains only boolean checks, bounded row counts, locale and viewport size. It excludes
trial/study IDs, hashes, coordinates, observations, and arbitrary extra payload keys. The original
returned receipt remains unchanged for archive verification. Five red tests demonstrated the missing
writer before implementation; focused tests additionally reject invalid metadata before any receipt
file is created. The receipt/fixture, suite-partition, and release-verifier test files passed 262 tests
afterward; targeted Ruff passed. This new diagnostic file does not itself constitute a new browser
execution.

Main integration, the aggregate product/security gates, exact-archive verification, and prerelease
publication are not completed by these BO browser-stage results.

## Transition and Exact-source Follow-up

Visual inspection of the native 1024px screenshots found a narrow sidebar sliver and obscured left
content. Source inspection found a 160ms sidebar transform transition below 1100px, while that fixture
captured immediately after resizing. This does not establish a persistent post-transition product
defect. No sidebar product CSS was changed on that evidence alone.

The BO fixture now awaits the actual sidebar animation completion, then checks viewport/main bounds,
the result title and noise control bounds, and the closed/open sidebar edge. It does not add an
arbitrary sleep or increase an assertion timeout. Explicit finite geometry fields are allowlisted in
the privacy-safe receipt; labels, source IDs and payloads remain excluded. Five focused red tests
failed before this helper existed, and the completed fixture test file passed 15 tests, including
invalid bounds, non-finite receipt geometry, sensitive nested payload exclusion, and rejection when
a visible report cell turns a nonzero SD into zero. These are Python fixture checks, not a replacement
for the next native layout run.

The original in-memory archive receipt now also carries exact study/batch payload digests, both
recommendation-source and current history identity, and replicate parent/child identity. The context
receipt carries the explicit retry request and current history identity. These fields are for the
isolated synthetic restart harness and are not copied into the diagnostic sidecar.

A new visible Report Center step selects the exact stored compressed batch, displays and checks its
source snapshot, creates an EN managed report, downloads and verifies its checksum, and reopens its
deep link. Its returned report descriptor/snapshot supports separate server-stopped offline checks
of the visible numeric table, latent/predictive labels and raw/effective counts. This report step,
the post-transition bounding checks, and the strengthened exact-archive restart checks are pending
native execution at this documentation checkpoint. Earlier native results did not run them.

## Confirmed Narrow-screen Grid Regression

Subsequent Linux workflow run `39619608275`, job `119289235207`, source `6fe0b5`, reached the existing
BO study journey after its GP/DOE/RSM/LHS stages. At 390px the BO settings page exceeded the viewport by
84px. Artifact `12354089397` contains the actual failed page HTML and screenshot
`failure-verify-bayesian-study-observations-and-recommendation-20261021T145111Z`.

The new noise settings introduce a section around scrollable settings tables. The parent
`.bayesian-recommendation-settings` used an implicit auto-minimum grid track, so that section's table
minimum width propagated into the outer grid. Its previously direct scroll-container children did
not have the same intrinsic-size behavior. The narrow fix explicitly uses `minmax(0, 1fr)` and gives
its direct children `min-inline-size: 0`; no global table minimum, design token, or overflow-hiding
rule changes. Tables retain their internal horizontal scrolling.

The existing failed browser assertion is retained. It now also waits for actual layout transitions,
records numeric settings/child/table-wrapper bounds, and checks that any oversized table remains in
an `auto`/`scroll` container. This is separate from the transient sidebar screenshot issue. Actual
native green confirmation of this scoped CSS change remains pending at this checkpoint.
Related local BO settings/presentation tests passed 18 tests; fixture/suite-partition checks passed
87 tests and targeted Ruff passed. None of those local checks executes a browser layout engine.

## Managed-report Locale Fixture Correction

Run `39622753726`, workflow job `119300205851`, source
`16fbaf3447622c4ab1f2ae602000aab7107038ac`, passed the BO calculation/replicate assertions and the
new KO/EN 1024/1440 post-transition bounding checks. The new Report Center journey displayed the
exact snapshot, created an EN report, downloaded it and verified its checksum. It then failed on
the report deep link's locale assertion, before the later legacy 390px workflow was reached.

Actual child artifact `12355722046` was inspected: `failure.json` reports the reports route with a
mounted root, compatible runtime, `lang=ko`, no page errors and no failed JS/CSS. Its trace records
the fixture's unconditional `localStorage.setItem(..., 'ko')` initialization on every navigation.
Thus the fixture overwrote the user's ENG choice before asking the reopened page to remain EN.
This is not evidence of a product LocaleProvider failure. The browser download POST returned 200,
and its saved-file checksum assertion completed. A separate server-log GET returned 405, but it
is not a page navigation/request in the child trace; its initiator is not established and it is
not the failed assertion or a failed saved download.

Only the two BO fixture contexts now seed KO when the locale key is absent. Shared forced-locale
fixtures and product locale code are unchanged. The report step explicitly switches to ENG,
reloads and checks EN before continuing, then also checks the deep-link navigation. Local fixture
and suite-partition checks passed 89 tests; Ruff passed. Executing the actual seed script in a
Node VM verified empty storage initializes KO and an in-memory user's EN value survives repeated
initialization; that is script evidence, not browser persistence evidence. Native re-execution of
the corrected report/restart journey and the 390px CSS fix remains pending.

## Native Follow-up At bb94ab4

Run `39624250223` tested source `bb94ab48125b6edbd49a5cc805131a01b13ec54e`. Artifact API metadata
for both items below explicitly reports that run ID and full source SHA; downloaded ZIP digests
were checked against the API digest, not inferred from artifact-ID ordering.

- Context job `119305400516` succeeded. Artifact `12355394534`, ZIP SHA-256
  `1f40b65691fed7d28e59386d1aeafeae77218453392a5e14ed5cc05f6575440a`, contains the completed BO
  receipt for explicit same-request replay, no duplicate trials and unchanged history.
- Workflow artifact `12356503315`, ZIP SHA-256
  `7d44225a131e2db4f79ed1a7cd04b99dcad3f87e3cddb6d268db764c53505d73`, contains a successful new
  BO fixture receipt and the downloaded managed EN HTML. The fixture completed target q1, joint q2,
  individual observations, explicit repeats, compression 9/7, source-preserving reload, ENG reload
  and report deep-link restoration, exact report snapshot/download checksum, and all four KO/EN
  1024/1440 post-transition bounds. At 1024 the sidebar right edge was -6.2px with main 0..1024px;
  at 1440 they were 248px and 248..1440px. The actual KO1024 screenshot was inspected and no longer
  shows the earlier left sidebar sliver.
- The later existing 390px journey also passed its layout assertions: settings and all direct
  children had left=14px/right=376px; oversized tables remained inside 362px auto-scroll wrappers.
  Thus the previously observed 84px page overflow is corrected in this native execution.

The whole workflows job still failed. Its later constrained, two-observation BO request returned
HTTP 409 `bayesian_optimization_artifact_mismatch`; the old fixture then timed out waiting for a
result heading. Actual failure HTML/screenshot and backend logs confirm the error. This is a new
product/API blocker, not a layout, locale or optimizer-timeout diagnosis. The fixture now checks
each recommendation's actual HTTP status/code and source history identity before its existing UI
assertions, without increasing its timeout. Local fixture/suite-partition checks passed 89 tests
and targeted Ruff passed. The backend cause/fix and native rerun are tracked separately; these
partial successes do not qualify the product or a Linux archive for release.

## Versioned API Inventory Follow-up

The native Python 3.11 run exposed outdated OpenAPI test expectations for legacy-only batch/trial
responses. The contract tests now explicitly require the exact legacy/V2 response unions, current
list/latest envelope types, and legacy/replicate trial unions. They also require the replicate route's
intent/count/history/idempotency fields. The client uses its central, escaped-ID route builder.

The tutorial still executes the legacy schema-1 recommendation route. Its collector now records the
actual response method version `0.6.0`, rather than falsely labeling that algorithm with the current
catalog's `0.7.0`. Existing tutorial data and expected result files were not modified. Local narrow
red tests reproduced seven stale contract expectations (204 passed); after correction, the complete
OpenAPI and tutorial files passed 245 tests, including the real legacy API collector and unchanged
fixture bytes. The new frontend route-encoding test passed, and targeted Ruff passed. These are
Windows CPython 3.10 checks, not a claim that the subsequent native Python 3.11 gate has passed.
