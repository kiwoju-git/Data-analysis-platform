# Beta EI Numerical Policy Compatibility

API43 distinguishes the statistical acquisition method from the arithmetic used
to evaluate it. The target remains the existing moment-matched Beta positive-part
expectation; it is not exact transformed-Gaussian EI, qNEI, or a verified JMP
numerical reproduction.

## New Results

Every newly calculated desirability `acquisition` contains
`"numerical_policy": "positive_beta_integral_v2"`. The existing `kind`,
`distribution`, moments, threshold, shapes, and `xi_desirability` retain their
meaning. Point-mass and Bernoulli-limit results also record the calculation
policy, while their distinct `distribution` remains unchanged.

Ordered-batch `planning.sampler` records the same `numerical_policy`. Its base EI
and all conditional sample EI calculations use that policy. This applies to
numeric and mixed-factor recommendations, evaluated candidate rows, manual
selection, and model-based augmentation. Readers reject a policy mismatch within
an ordered batch instead of combining results from different numerical methods.

`positive_beta_integral_v2` uses a positive width-scaled density integral for
supported concentrated shapes, retains survival-function arithmetic for ordinary
shapes, and preserves explicit errors for unresolved precision. The independent
reference and declared tolerances are documented in
`backend/tests/reference/bo_beta_reference.md`.

## Existing Results

An absent `numerical_policy` means the original survival-function-difference
implementation. The read-only implementation in `bo_beta_legacy.py` freezes
BASE0070640's exact operation order, concentration limit, and error checks.
Calculation and first-commit validators still dispatch to that implementation
when explicitly validating a historical calculation. They never substitute v2
for an absent-policy calculation.

Historical numeric result readers use a separate stored-receipt boundary after
verifying document hashes, source relationships and request/policy structure.
For an absent-policy acquisition, this boundary preserves the stored EI instead
of repeating its platform-dependent special-function calculation. It verifies
finite values, mathematical ranges, threshold/xi, distribution and Beta-shape
links. Ordered-batch readers retain the stored conditional score and MC standard
error while checking their proof/source links and bounds. Current explicit-policy
results still undergo the existing numerical replay. Numeric manual and mixed
stored-selection readers already validate their immutable source bindings and
were not relaxed by this repair.

Payoff range checks include the frozen subtraction arithmetic allowance:
`64 * ulp(1) * mean`, an upper bound for its original operand-scaled roundoff
budget. This is not a new EI matching tolerance. Conditional mean/MCSE bounds
propagate each sample's payoff bound and that allowance; for samples in `[0,U]`,
the `ddof=1` standard error is at most `U/(2*sqrt(n-1))`. All-zero payoff bounds
require zero score/error. Stored values are never clamped or rewritten.

The optional typed field is deliberately omitted when serializing an old record,
including through nested Pydantic models. Missing does not become `null`, a
default policy string, or a modified hash input. An explicitly supplied null or
unknown policy is rejected. No stored payload, acquisition value, request,
manifest, or checksum is rewritten. No SQLite migration is needed for this
additive provenance field; the separate dataset-import migration is unrelated.

New calculations use v2 even when their source model snapshot predates API43.
Both new-worker response boundaries reject a missing or non-v2 policy on
acquisitions and conditional samplers. This check is separate from stored-result
readers; model-free rows with no acquisition remain valid. Reading an existing
calculation does not upgrade it. A confirmed result's idempotent replay uses the
stored reader, without creating new trials or rewriting files. A first confirmation
of an old, not-yet-confirmed recommendation/augmentation remains a strict commit
boundary; cross-platform legacy arithmetic can still reject that operation.
This read-compatibility repair does not claim that such a historical candidate
can always be newly committed on another platform. New calculations use v2.

No HTTP option can select the internal receipt boundary. Checksums detect file
corruption relative to stored metadata; they do not authenticate files against
a local administrator who can rewrite both data and metadata. Preserving a
historical value is not a new claim of numerical accuracy or bitwise portability.
Existing package provenance and all other validation requirements still apply.

## Verification

`test_bo_beta_numerical_policy.py` uses a frozen legacy EI whose new v2 value
differs, checks dispatch and strict policy validation, verifies unchanged nested
JSON/hash inputs for legacy acquisitions and numeric/mixed samplers, and checks
conditional-score and augmentation validation without fitting any model.

The regression input is binary64 `mean=0.9`, `variance=1e-9`,
`threshold=0.9000316227766018`. Its saved legacy EI is exactly
`2.6340823912618383e-6`; the independent Decimal-density reference is approximately
`2.6339494963754832e-6`. These are two numerical evaluations of the same stated
Beta approximation, not two different acquisition objectives. Synthetic v2
records created during development before the policy field was introduced are
not legacy compatibility fixtures.

`test_bo_legacy_stored_readers.py` exercises actual saved-result dispatch and
strict calculation/commit boundaries, including bytes/hash preservation,
confirmed replay, current-policy rejection and malformed/source-mismatched
receipts. Its cross-platform legacy value is a recorded numerical fixture used
in a simulated restore, not proof of a native Linux run in this session. See
`bo_completion_validation.md` for commands and actual execution evidence.
