# Direct Prediction Request Context

## Scope

GPR direct prediction separates the current input draft from a completed
prediction snapshot. This is a frontend ownership and display correction, not a
change to GP training, CV, kernels, optimizer, uncertainty calculations, safe
model storage, or Bayesian Optimization. The backend API and model manifest
versions are unchanged. PLS retains point-only prediction and its separate
schema-1 JSON snapshot contract.

## Ownership and Invalidation

An explicit prediction captures the source analysis ID, saved model ID and
manifest checksum, response column ID, ordered predictor IDs, client row IDs,
and numeric input values. The current request token is combined with a monotonic
source context and input draft revision. Returning to identical text or the same
model after an intervening change cannot reactivate an older request.

Cell edit, add, and delete invalidate pending/completed direct prediction
immediately, before an effect runs. If a pending or completed prediction was
invalidated, the grid shows a localized rerun-needed notice and no previous
means or intervals. A new source begins empty. Old success, failure, and finally
callbacks cannot overwrite newer results, errors, or busy state. Unmount revokes
client ownership; it does not claim that server computation was cancelled.

Locale and viewport changes do not change input or request ownership and do not
trigger prediction. Source identity uses stable IDs and checksums, never display
names or translated text. Input labels and values remain user data.

## Completion Validation

The GPR completion boundary verifies model ID, manifest checksum, response ID,
row count, confidence level 0.95, and interval kind
`latent_and_new_observation`. Request and response row IDs must each be unique
and form exactly the same set. A reordered response is valid; duplicate,
missing, and unexpected IDs are not. Display uses an ID map, not response index.

Means, nonnegative standard deviations, and ordered interval endpoints must be
finite numbers. Zero uncertainty and zero-width intervals remain valid. All
warning strings, including unknown codes, are preserved. Validation does not
derive intervals from standard deviations, round values, fill missing values
with zero, or publish a partial response. An invalid completion produces
`gp_prediction_response_invalid`.

PLS applies corresponding model/response/checksum and row validation before
publishing its point predictions. `intervals_supported` remains false. A
`pls_prediction_snapshot_mismatch` cannot leave a visible invalid result or an
old enabled export. A retry clears the previous completed snapshot immediately.

## Separate GPR JSON Snapshot

Only a current, validated completed prediction enables download. Its client-side
artifact has these fields:

```text
schema_version: 1
artifact_kind: gaussian_process_point_prediction_snapshot
source_analysis_id
predictor_column_ids (exact saved-model order)
client_received_at
prediction_recalculated_on_export: false
request (manifest checksum and submitted rows/values)
response (full validated GPR response, including both interval types and warnings)
```

Input objects, predictor IDs, response rows, interval objects, and warning arrays
are detached copies. The response array order is preserved in the snapshot;
request order and client IDs remain separately available. JSON uses stored full
precision values, not table display rounding. Download uses the existing local
browser download utility and does not call prediction, fit, raw data loading, or
any external service.

This is not a managed model/report asset and does not overwrite the source
analysis or model files. PLS's existing `pls_point_prediction_snapshot` schema 1,
provenance fields, and no-recalculation flag remain compatible.

## Error Presentation and Surface Boundary

GPR direct, PLS direct, and GPR surface retain the original caught cause in state;
known codes are localized at render time. A language change updates error text
without refetching or modifying the error, request, or result. General Factorial
response validation similarly retains a stable validation discriminator rather
than a translated string. Existing safe error display rules remain: raw paths
and tracebacks are not newly exposed.

Surface generation keeps its existing request-time axis/fixed-value snapshot,
latest-request/source guard, and client-row-ID join. Draft selectors do not
rename an already generated grid; a new Generate is explicit. This change only
repairs the surface error's locale-dependent rendering, not its numerical or
selection behavior.

## Validation Boundary

`gpPredictionRequestRace.test.tsx` directly exercises the current React components
using the repository's node hook-runner pattern without adding jsdom. Before
the repair, five regressions failed with stale/foreign values or retained busy
state. Pure snapshot tests cover identity, row permutations, malformed values,
zero intervals, the existing 2000-row limit, and object detachment. PLS tests
protect its existing artifact shape and point-only semantics.

The node harness is not a browser timing/accessibility substitute. The integrated
real-model browser fixture and final whole-project results are recorded in the
end-to-end remediation validation record. No old test count or source inspection
is evidence that an unexecuted browser scenario passed.

UI/UX Pro Max's targeted loading-feedback and error-recovery guidance was used:
the existing dense grid/layout is preserved, busy state is exposed with
`aria-busy`, errors use an alert, and invalidated predictions show a rerun notice.
No design system, chart library, font, dependency, or remote resource was added.
