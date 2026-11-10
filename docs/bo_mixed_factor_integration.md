# Mixed BO Integration Gate

Status: source/API integration and the built-UI journey are verified in the
checkpoints below and the [completion ledger](bo_completion_gates.md). Final
full-product CI is still pending. Not a completion declaration.
The owner explicitly included nominal/ordinal BO in the main-integration scope.
Do not describe kernel unit tests as completion of that workflow.

## Preserved Boundaries

- Numeric studies4/5/6, scalar EI/ETI and automatic batches retain their exact
  existing serialization, normalization, sampling and source/hash dispatch.
- A mixed study uses an explicit new factor-union contract. Category labels are
  complete identities, not numeric measurements, distances or sorted strings.
- The existing study/version/trial/history/planning ownership tables remain the
  source of truth. No separate mutable study singleton or parallel owner table.
- Mixed selection uses the immutable fixed-candidate workflow. The existing
  numeric continuous-optimizer path is not fed categorical codes.

## Implemented Contract

1. New study schema7: numeric and nominal/ordinal factor domains, declared levels,
   explicit correlation policy, numeric-only linear constraints, bounded seeded
   executable initial design, and unmodified DS/Gaussian response-goal semantics.
2. Individual trial coordinates preserve category strings and canonical numeric
   levels. Vector observation history2 may remain: it already hashes each
   coordinate identity plus actual response values. No predicted/fantasy response
   becomes an observation. Replicate/close/abandon/retention remain source-CAS.
3. New mixed fitted snapshot, with complete declared level order, typed parameter
   descriptors and strict numeric array bounds. Numeric matrix columns alone are
   normalized to [0,1]; category columns are checked against their level counts.
4. Candidate/profile/selection documents dispatch by version. A category level
   is evaluated as a discrete point; no line implies interpolation between
   nominal values. Conditional views reuse a saved model, not a new fit.
5. Exact ordered confirmation, observations, restart, managed report, backup and
   deletion must succeed before UI capability is advertised.

API39 uses study7/history2, fitted snapshot2, candidate revision3, selection3,
batch/config/model10 and item5; the new method is0.15.0. Metadata32 extends
existing planning and batch constraints without rewriting old JSON or hashes.
The model receipt inside the snapshot has its own kernel metadata version6.
Old numeric study/GP/BO payloads retain their original version dispatch.

## Parameter and Distance Policies

The reviewed pure kernels expose positive equal correlation, PSD unequal
hyperspherical correlation, and monotone ordinal latent coordinates. The latter
two are explicitly documented product parameterizations, not recovered JMP
formulae. Equal/unequal categorical correlation ignores an ordinal declaration's
order; only the latent policy uses that order.

Fit initialization and bound reporting must use parameter descriptors. Existing
numeric screening assumes [amplitude, numeric lengths, noise]; passing original
mixed factor count would mislabel category angles/gaps as lengths. Retain old
numeric fit receipts and introduce a versioned mixed receipt.

Exact repetition uses canonical actual identities. Novelty/space-filling uses
an explicitly named numeric/Hamming/optional ordinal-rank distance, never the
changing fitted latent coordinates. Ordinal rank spacing is an explicit design
distance assumption, separate from the learned GP kernel.

Training level coverage is not equivalent to declared levels. Missing coverage
must be an explicit preflight limitation or a persisted prior-dependence warning;
never substitute the first category. Learned unequal/latent parameters without
observations cannot be presented as evidence about those levels.

## Verification Required

- Independent posterior/Cholesky, finite-difference gradients, PSD and equivalent
  category label/code permutations with the same correlation matrix.
- Long labels, whitespace, numeric-looking strings and declared ordinal order;
  no case folding or silent identity normalization.
- Actual initial design, constraints, q1/q8, per-trial observations, exact saved
  restore/report, mixed profile and source changes during requests.
- Corrupt vocabulary/kernel/Cholesky/source hashes rejected; no object NPZ,
  pickle, refit on read, accidental scalar conversion or future data leakage.
- Existing numeric reference/reader/hash tests remain unchanged in meaning.
- CSV category strings receive the existing formula-injection escaping policy.

Read-only integration review identified these boundaries in `bayesian_studies`,
`bo_surrogate`, `bo_fit_policy`, `bo_surrogate_snapshot`, `bo_candidate_points`,
`bo_observation_groups`, and dedicated report readers. Review did not execute
the mixed product workflow and is not JMP numerical-parity evidence.

## Current Executed Checkpoints

- Mixed model/candidate/profiler real HTTP and safe snapshot tests:35 passed on
  Windows10/Python3.10.11 in the worktree runtime. This includes no-fit replay,
  category-level predictions, restart, hash identity and parameter-codec roundoff.
- Mixed ordered core and existing numeric MC:89 passed at an earlier checkpoint.
  A later mixed/worker/augmentation/numeric-MC set:138 passed in the current
  worktree runtime. Independent Cholesky/quadrature references are separate from
  production output-validation helpers.
- Atomic mixed batch API:3 passed. q2 manual selection, whole confirmation and
  replay, actual response entry/partial-state overlay, KO/EN report download and
  restart; q8 model-free selection with an injected second-item SQL failure,
  zero partial persistence and explicit retry; rewritten outer-hash tamper
  rejected by candidate/source binding.
- The later14-test mixed-batch/kernel API run passed in190.44s. It includes
  model-based mixed Refine/Confirm through actual endpoints with refit forbidden,
  idempotent selection replay, unchanged study history before confirmation,
  backup/restore and explicit closed-study deletion with all planning/report
  dependencies. This is API evidence, not an actual form or packaged execution.
- Historical-report isolation passed its dedicated API regression. The built
  mixed journey and remaining full checks are recorded in the completion ledger.
  No Linux archive or JMP application output was validated by these tests.
