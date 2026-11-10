# Persisted Auto Selection Evidence

## Scope and Acceptance

This checkpoint extends the existing numeric and mixed candidate workflows, not
their statistical selection algorithms. API42 / metadata33. Numeric selection/config4,
calculation2, batch/config/model11 (method0.16.0), unchanged item4. The saved
evidence itself has schema1. Mixed Auto uses selection/config5, calculation4,
batch/config/model12, unchanged item5 and method0.16.0.

Acceptance: Auto Apply -> explicit selection Review -> explicit Confirm ->
exact-source reopen -> managed HTML, with identical decision evidence throughout.
Neither Apply nor Review creates observations. Existing candidate selection2,
mixed selection3, batch9/10 and their original bytes remain readable.

## Source and Meaning

The request contains only a routing model ID/hash, threshold, and expected advice
digest. It does not accept browser-provided R-squared or arbitrary report JSON.
The server rereads that owned immutable model and reruns conditional row-LOO in
the same owned worker as augmentation, under one admission/thread/time budget.
No hyperparameter fitting is performed. Digest disagreement rejects the entire
review. A Refine selection must use that same routing model for prediction.

Model-free MaxPro/maximin retains `model_id=null` and zero prediction evaluations.
Its separate routing model explains why the policy was suggested; it is not a
model used to score candidate predictions. Evidence stores fixed source hashes,
LOO calculation/points, R-squared, threshold, policy and decision hash. Mutable
`source_is_current` / `apply_allowed` are not persisted in it.

LOO remains `fixed_full_fit_parameters_row_loo_v1`, not independent external
validation or group validation. Auto remains the documented product policy
`conditional_loo_any_low_explore_else_refine_v1`, not verified JMP algorithm or
output parity. No new claim of numerical equivalence to JMP is made.

## Atomicity, Restore and Reports

The existing request-ID replay precedes currentness and calculation. The same
saved request can be recovered after a lost response and history advancement;
reusing its ID with a different body conflicts. The storage transaction validates
the routing model owner/version/hash/history even when the actual model is null,
then checks current history, trial count, active state and pending trials.
Confirm retains the existing atomic whole-batch fence and idempotency.

Reads verify typed versions, canonical bytes, hashes, exact observations/response
IDs, model identity and decision/selection consistency. They do not rerun LOO,
fit, ranking or read dataset source rows. Managed HTML renderer1.11.0 shows the
stored threshold, metrics, routing identity, effective policy and limitations.
It creates a new export and does not rewrite an old result/report.

Migration33 rebuilds only the selection and batch CHECK constraints, retaining
all original records, indexes, relationships and hash inputs. Backup/restore
accepts metadata33. No user workspace is opened for this development checkpoint.
Integrity checks detect corruption/inconsistent references; they are not a
cryptographic authentication guarantee against an administrator rewriting all
related records and hashes.

## UI Ownership

Only explicit Apply attaches the reference. Manual strategy/settings changes,
model or candidate-source changes, and advice threshold edits remove it. An old
receipt cannot silently justify a new manual policy. Existing stored selections
display their committed evidence independently of the editable form. Opening a
stored selection does not silently attach its old advice to a new review.
Locale/resize do not change the source or refit a model. Review/Confirm remain
separate, with the same source and latest-request guards.

## Validation Record (2026-11-11)

All fixtures are synthetic. No installed JMP runtime/output was available.
This is the initial numeric Windows Python3.10 checkpoint, not a Linux release
or remote CI claim. The final combined evidence superseding this checkpoint is
recorded in `bo_final_validation_20261111.md`.

- Reviewer: one low-resource agent reviewed source/CAS/replay/provenance, and
  independently implemented/tested migration33. No P1/P2 source finding; this is
  not a substitute for API/browser execution.
- Migration red: schema32 did not satisfy the new schema33 expectation.
  Green: 11 tests, followed by 1 strengthened request-ID/owner-FK test.
- First integration run: 20 pure cases passed; 3 API failures exposed the missing
  method0.16 reader allowlist. Fixed without changing calculation tolerances.
- Next run: 2 API cases passed; a new fixture omitted its tolerance and old backup
  support rejected metadata33. Fixed fixture and explicit backup compatibility.
- Next new journey: saved/confirmed/replayed successfully; report descriptor
  exposed a missing batch11 URL dispatch. Added that exact mapping.
- Latest narrow run: 11 passed (68.69s): saved Auto MaxPro and Refine, immutable
  evidence, rejected digest/threshold/model substitution, exact retry after new
  observations, saved HTML values, rehashed tampering, backup/restart/restore;
  conditional LOO independent Cholesky and three new unit/row-permutation tests.
- At that initial checkpoint, lint/type checks, full regression and built UI
  were not yet complete; consult the combined ledger for their actual outcomes.

## Additional Verification and Limits

Metamorphic tests complement a single JMP example: changing response units with
matching noise units, reversing response direction, and permuting trial rows
must preserve R-squared and Auto routing. Brute deleted-row Cholesky remains the
independent numeric oracle. Tampering and failed-response replay test persistence,
not statistical parity. Browser tests must compare visible metric text with the
API and offline HTML, not only file existence or screenshots.

The owner subsequently requested completing mixed evidence persistence and
integrating into main. The combined verification and publication ledger is
`bo_final_validation_20261111.md`; the numeric checkpoint results above are not
substitutes for that combined rerun. Actual JMP-runtime comparison and Linux
Release publication remain outside the claimed evidence.

## Rollback Boundary

No rollback was performed. Once committed, revert only this checkpoint's commits
in reverse order, not the earlier BO/DOE work. Code revert does not downgrade
metadata33; older code cannot read selection4/5 or batch11/12. Use a verified pre-upgrade
offline backup restored into a new empty location if running older code. Never
delete or rewrite the current workspace, models, trials or results to roll back.
