# Persistent BO Candidate Planning

Implementation gate in progress. API38 / metadata31 / manual batch schema8 are
the proposed integrated contract. They are not a claim that native/browser gates
have passed. See `bo_completion_gates.md` for completion state.

## Scope and Source

This gate extends numeric-factor, desirability-capable studies5/6. Scalar EI/ETI
and their historical readers remain separate; a scalar history is not silently
converted to a desirability study. Fit options use existing schema5/6/7 and the
response noise, kernel and versioned curve policies explicitly selected by the
operator. A fit consumes no trial budget and may inspect completed observations
while a real experiment is pending. New selection/confirmation still requires
an active study with no pending trials and an unchanged history and trial count.

A planning model stores validated, bounded numeric fitted state, not pickle,
joblib, executable code, or a kernel string. Restoration validates the signal
kernel, covariance factor, solution, raw-data normalization, exact-repeat counts
and source target binding. Profiling evaluates that fitted state without fitting
or changing observations. Historical state stays historical after evaluation.
Current candidate eligibility has its own trial-count/coordinate hash because
new pending trials can change novelty without changing the completed fit source.

## Candidate Revisions and Selection

Uniform generation has an explicit seed, executable discrete levels, finite
attempt budget and complete count or failure. Imported rows require complete
factor coordinates. Previously used or explicitly included constraint-violating
rows remain visible but cannot be confirmed. Coordinates are not rounded to make
invalid imports executable. Row identity hashes canonical actual conditions.

Tables are immutable revisions with compare-and-swap heads. Append/remove
commands create a new revision from the entire previous table, not the displayed
page. Each revision records model/history/trial-count provenance, input values,
canonical executable coordinates and generation policy. Limits are10,000 rows,
100 rows per read/evaluation,32 tables and64 revisions per table. Server storage
also caps models and selections at32 per study, each document at16MiB, all
planning documents at128MiB per study and256MiB per workspace. These are product
limits, not statistical limits. Capacity failure commits no partial revision.

Manual selection retains an explicit order of1..8 eligible rows. Reorder/subset
edits require a new score against the same model. The first score is analytic
Beta desirability EI; later scores use the existing correlated latent MC
conditional marginal policy with reproducible seeds. The output is a manual
selection, not an automatically optimized candidate. Base predictions use real
completed observations only. Conditional planning uncertainty is separate.

Saving the selection creates no trial. Confirming checks source hashes, budget,
pending state and selected revision inside the existing atomic batch transaction.
All pending trials and their confirmation mapping commit together. Repeating the
same request ID/payload or confirmation returns the saved artifact; reusing an
ID with different content is a conflict. No automatic POST retry is performed.

## Resource and Retention Boundaries

Fit, prediction, conditional scoring and their numerical revalidation run in
one owned spawn process under the shared BO admission semaphore and single-thread
numerical limit. Revalidation uses the original computation deadline, not a fresh
60-second allowance. The parent hard deadline allows the existing20-second
process startup/IPC allowance in addition to the requested computation budget;
this is not advertised as a hard OS memory limit. Parent checks are bounded
typed/JSON/hash/source checks, not a second GP computation.

Candidate pages and selection summaries are distinct from exact details. The
selection list never returns all covariance proofs. No diagnostic field contains
raw observations, factor names, internal paths or user identifiers. Workspace
backup includes the owned database state and verifies its JSON hashes. Deletion
preflight records planning dependencies and a source manifest; explicit owner
deletion removes confirmations, selections, heads/revisions, sets and models in
one transaction with existing dependent report handling.

## Report and Compatibility

Manual batch schema8 retains the exact model/candidate revision/selection hashes,
ordered scores, unmodified actual predictions, fit warnings and optimizer evidence.
HTML reads these saved values and does not refit, rescore, or read source rows.
Automatic batch schemas1..7 and old studies remain readable without rewriting
their JSON or checksums. The automatic recommendation endpoint is distinct from
manual planning; its historical latest lookup must not parse schema8 as schema7.

Migration31 is additive for planning state and extends the batch CHECK tuple to
method0.13/config8/result8/model8/item4. Old rows are copied byte-for-byte. Code
rollback does not undo a database migration or remove new artifacts; use a
verified offline backup in a new destination when running an older application
that cannot read metadata31/schema8. Never delete a user workspace as rollback.

## Alignment and Verification

JMP documents candidate tables, explicit ordered row selection and model-based
refinement/confirmation as distinct workflow operations. These public workflow
concepts inform the UI, but do not establish matching proprietary optimization,
desirability formula or Monte Carlo output. Augmentation is a separate gate.
Source: [JMP19.2 Candidate Set](https://www.jmp.com/support/help/en/19.2/jmp/candidate-set.shtml).

New tests cover independent posterior restore, candidate identity/constraints,
source guards, storage CAS and capacity, atomic lifecycle, migration bytes,
report/backup restore and worker validation boundaries. Authored tests are not
execution evidence; record each actual run in the completion ledger.
