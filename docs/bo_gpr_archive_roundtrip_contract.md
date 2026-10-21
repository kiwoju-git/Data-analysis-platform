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
