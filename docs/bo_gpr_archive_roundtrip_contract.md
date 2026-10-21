# BO/GPR Exact-Archive Roundtrip Evidence

The initial built-UI fixture executes target q=1, joint batch, replicate creation,
individual observations and exact replicate aggregation. The GPR fixture executes
GroupKFold, time validation and positive lag forms, then restores a mixed model,
saves a point prediction and a latent-SD surface with a nominal hold value.
Synthetic dataset/study provisioning is an API setup step, not UI ingestion proof.

Initial evidence must include exact study/history/batch/trial identities and
digests, all three GP analysis/model identities, original prediction requests and
responses, and managed report source/output hashes. Boolean success flags alone
are insufficient. The managed surface must belong to the same model and exact
applied request; a valid but unrelated report cannot satisfy the gate.

`bo_gp_release_resume.py` is run by both existing archive restart phases:

1. Restart the first installation with the same external workspace.
2. Install the same archive bytes in a second directory and open that workspace.

Each phase reads the exact saved BO study and V2 batch, checks replicated trial
parentage, restores each GP result and model in the UI, and compares exact output
rows from unsaved mixed/lag/surface prediction requests. Prediction is allowed;
fitting, CV, recommendations, report regeneration and writes are not. Existing
managed reports are opened by export ID and downloaded byte-for-byte unchanged.
The enclosing archive verifier also checks immutable workspace file hashes.

After the server is stopped, an offline browser opens the original BO and mixed
GP HTML files. It checks stored BO quantities, GP inputs and uncertainty tables,
and the saved latent surface's visible axes, hold values, color quantity and
nonempty geometry against the stored grid values. No HTTP requests are allowed.

The phase identity sets are compared to the initial receipt; missing second-
installation proof, a changed owner/hash/view or a missing surface report fails
the archive gate. Unit tests of this contract do not constitute browser or Linux
archive execution. Native initial-form receipts may be validated independently,
but final release completion still requires both real restart journeys and the
server-stopped offline phase against the final archive.

## Read-Only POST Classification Regression

Archive job `119326239437` in run `39627587187`, source
`0ea7b2120ce4ee22c9b0a45a376b739c878a8ce8`, completed the initial application
journey but failed the first installation's restart guard. The guard incorrectly
classified 15 report lookup/download POSTs as mutations: five each to
`/api/v1/reports/capability`, `/api/v1/reports/artifacts/query`, and
`/api/v1/reports/{export_id}/download`. This was an archive-verifier defect;
the run remains failed and is not reported as a completed archive validation.

Source review of `backend/app/api/v1/reports.py` and the corresponding
`report_sources`/`report_exports` services confirms that these routes validate
and read an exact stored source or report. Download checks the expected source
and output hash and returns existing bytes. They do not invoke report creation,
fitting, CV, or recommendation generation.

The corrected guard recognizes only those exact API paths, the existing exact
source-snapshot path, and a canonical UUID-shaped report download path. Unsaved
GP prediction remains restricted to the exact model route and `save_result`
absent/false. POSTs to report creation, recommendation, replicate creation, or
observation submission remain forbidden, as do saved predictions, suffix
lookalikes, malformed prediction bodies and non-read methods. This is not a
blanket permission for POST or for every route under `/reports`.

Local Windows/Python 3.10 regression evidence:

- Before the correction: 10 failed, 24 passed in the new classifier suite.
  Three failures reproduce the native report routes; the others cover
  over-broad suffix matching and malformed/unknown request boundaries.
- After the correction: classifier, archive journey contract and archive
  verifier suites together passed **239 tests** in 3.99 seconds.

These tests do not replace another exact-archive native run. The restart,
second-installation and server-stopped phases still have to pass on the newly
built archive before publication.
