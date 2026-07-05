# Method Versioning Policy

This policy explains when a stable `method_id` in `METHOD_VERSIONS` should
receive a method-version bump. It does not change any current method version in
this PR; all current stable IDs remain on `0.1.0`.

## Source Of Truth

- `backend/app/analyses/registry.py` owns the `METHOD_VERSIONS` map.
- The analysis method catalog and `MethodExecutionHandler` specs must read from
  that same map.
- Tests must assert that every stable method ID has a version entry and that
  catalog/handler versions agree.

## Patch Version

Use a patch bump when the same statistical contract is preserved and existing
stored results remain comparable:

- typo or label-only metadata correction in a result field;
- warning wording change with the same machine-readable warning code;
- frontend display or panel layout change only;
- documentation clarification with no result schema or calculation change;
- test-only fixture expansion that confirms the same formulas and output fields.

Frontend-only changes do not require a method-version bump unless they alter the
request sent to the backend or reinterpret a stored result field.

## Minor Version

Use a minor bump when the method remains the same broad analysis but a stored
result contract or numerical output can change:

- adding a new persisted result field, CI, effect size, assumption diagnostic,
  or warning code;
- changing default missing-data handling, alpha, alternative, correction, or
  post-hoc policy;
- changing p-value, confidence interval, effect size, or degrees-of-freedom
  formulas;
- changing the definition of a chart-data payload or diagnostic statistic;
- adding supported request options that change persisted outputs.

Reference fixture updates that change expected statistics, intervals, effect
sizes, warnings, or payload shape must be reviewed as a method-version bump
candidate.

## Major Version

Use a major bump when stored results from the previous version should not be
treated as comparable without an explicit migration or user-visible note:

- replacing the statistical method family;
- changing the null/alternative hypothesis semantics;
- changing the default test from one method to another;
- removing or renaming persisted result fields;
- changing data inclusion rules in a way that changes `n_used` for the same
  request and dataset;
- changing DOE design-generation semantics or run-order determinism.

## No Silent Migration

Stored analysis result envelopes keep their original `method_version`. A catalog
version bump must not rewrite existing result files. If the UI compares old and
new results, it must show the version difference.

## PR Checklist

- Update `METHOD_VERSIONS` when the policy requires it.
- Update method contract docs and audit matrix entries.
- Add or update reference fixtures and explicit tolerance tests.
- Confirm catalog and handler version alignment tests still pass.
- Record the version rationale in `docs/progress_gate_b.md` or the PR summary.
