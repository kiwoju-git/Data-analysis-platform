# Linux Release Browser Journey

The final archive verifier runs this driver against the installed release, not
the Vite development server. The browser driver remains outside the archive and
does not import installed application modules. Its Python/browser environment is
recorded separately from the server's runtime/build identity.

## Phases

The orchestrator owns extraction, offline installation, process shutdown,
same-install restart and a second installation using the same external synthetic
workspace. It invokes these black-box phases:

```text
python tests/e2e/linux_release.py --url <origin> --output <initial-directory>
python tests/e2e/linux_release.py --url <origin> --output <restart-directory> --resume-evidence <initial-directory>/application-smoke.json
python tests/e2e/linux_release.py --output <offline-directory> --offline-reports <initial-directory>/application-smoke.json
python tests/e2e/linux_release.py --url <second-install-origin> --output <second-directory> --resume-evidence <initial-directory>/application-smoke.json
```

The offline phase requires the original server to be stopped, rejects any HTTP
response (including errors), and opens the downloaded files in a browser context
with networking disabled. Namespace-enforced installation isolation is a separate
orchestrator gate; browser offline mode does not prove installer isolation.

## Visible And API Coverage

- A visible paste surface and parsing confirmation create a 16-row synthetic
  dataset. Actual PCA, PLS and GPR panels submit three analyses. The GPR fixture
  uses three folds and zero restarts to bound this packaging smoke; it does not
  replace the separate numerical reference and optimization tests.
- PLS and GPR each predict two explicit rows. The save-completed-prediction
  checkbox is checked before execution and its default-off state is verified.
  Local JSON snapshot downloads are separately checked against the captured
  request/response and must not issue another POST.
- The Report Center inspects the authoritative saved source and creates and
  downloads Korean and English managed HTML for both families. PLS uses
  `predicted_value`; GPR checks `predicted_mean`, latent SD/interval and
  new-observation predictive SD/interval. No PLS field is substituted for GPR.
- Resume uses visible saved-history restoration and exact `report_id` links.
  Identical input values and client row IDs are submitted against the identical
  saved manifest with persistence disabled. All saved prediction numbers and
  warnings must agree, report bytes must be identical, and no analysis POST is
  allowed. Opening history does not fit/CV/retrain a model.
- Two Variances and generic HTML exports remain explicit API smoke coverage.
  The Two Variances direct route/refresh must render its panel, but this is not
  reported as a visible Two Variances form submission. Saved results from all
  four methods are rechecked after restart.
- Offline HTML checks inspect visible input/prediction tables and inline SVG
  reports, not embedded raw JSON strings. Managed report values are compared at
  the renderer's existing ten-significant-digit precision (`rel_tol=6e-10`,
  `abs_tol=0`); this does not alter calculation tolerances.

## Evidence And Failure

`application-smoke.json`, `resume-smoke.json` and `offline-smoke.json` have
`schema_version=2`. Each browser phase also saves `journey-evidence.json`, a
Playwright trace, synthetic screenshots, downloaded reports and local prediction
snapshots. Failure leaves diagnostic evidence and a nonzero process exit; a
missing phase is not a successful full release validation.

The record distinguishes:

- `result_payload_sha256`: canonical inner-result JSON digest, independent of
  JSON key order. This is **not** the stored artifact file checksum.
- `source_result_artifact_sha256`: the backend's exact stored-result artifact
  checksum, verified again by the stored-report capability after restart.
- model manifest hash and full manifest, authoritative typed report source/ref
  hash, and exact completed-prediction request/response/client IDs.
- report/local-snapshot `sha256`: SHA-256 of the actual downloaded file bytes.

The smoke does not claim Windows package execution, another physical LAN client,
all statistical options, all report source kinds, or a supported OS beyond the
native environment in the final validation report. Development-server debugging
is not evidence that the built Linux archive passed installation or runtime gates.

## Source Debug Evidence

The Windows source debug in `.tmp/a15-browser-debug-2` returned exit 0 for the
three visible fits, both persisted predictions, four KO/EN reports, server-stopped
offline values and same-workspace restart. Resume recorded zero analysis POSTs.
The earlier `a15-browser-debug-1` failed at a new driver's exact label selector;
the driver was corrected to target the existing response-label control and the
verified maximum-components table column. No production change or timeout
increase was made. These directories contain synthetic data and are not Git
assets. Final archive/cross-install evidence belongs to the native release
validation output, not this source-debug record.

The separate `.tmp/a15-browser-tail-1` source-debug run also returned exit 0 for
the preserved Two Variances route/reload, its actual API calculation, four
generic HTML exports and their server-stopped offline viewing. The nine release
Host/Origin checks were not claimed from a Vite proxy. Native archive execution
must run the complete unchanged CLI, including those guards.
