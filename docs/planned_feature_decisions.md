# Planned Workflow Visibility

The [generated capability matrix](generated/analysis_capability_matrix.md) reads
current visibility and placement from `frontend/src/analysisDomains.ts` and joins
actual backend methods. Its non-menu section distinguishes planned, roadmap-only,
contextual information, current subworkflows and legacy aliases. None of those
labels alone creates an available method or a report action. This document records
the product decisions behind those declarations, not a separate support count.

Roadmap-only (not executable, hidden from sidebar and landing):

- `hypothesis.comparability_assessment`: future integrated comparability
  assessment remains a separate design requirement. Existing t-tests and TOST
  remain available; they do not become a combined comparability verdict.
- `quality.multivariate_monitoring`: future Phase I/II monitoring requires its
  own limits and reference contract. Exploratory PCA D-squared is not a substitute.

`quality.two_variances` is now an executable, separate v0.1 method alongside
`eda.equal_variances` in measurement-variability / variance-comparison. Its
canonical placement occurs once. v0.1 supports BF equality and normal F ratio
inference only; the earlier Bonett/Both draft is deferred, not renamed as shipped.

Visibility defaults to navigation; filtering preserves order and original data.
Contextual GP-surrogate explanations, stored-model prediction and optimization
are not hidden by the planned-workflow policy. Empty supporting wrappers and
planned-only hidden families are omitted. Canonical routes remain unchanged.
