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
Validators dispatch to it for existing q1 acquisitions, conditional sample-score
reduction, numeric/mixed planning, and augmentation. They do not recompute a saved
legacy acquisition using v2 and reject it merely because the floating-point
result changed.

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
calculation does not upgrade it. Retaining legacy arithmetic
does not establish bitwise portability across different numerical-library
versions; existing package provenance and validation requirements still apply.

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
