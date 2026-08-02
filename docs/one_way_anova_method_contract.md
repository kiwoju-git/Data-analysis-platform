# One-Way ANOVA Method Contract

Last updated: 2026-08-02

## Scope

`hypothesis.one_way_anova` version `0.2.0` accepts one numeric response and one
grouping column from an immutable dataset version. New runs use result schema
`2`; stored `0.1.0`/schema `1` envelopes are read without rewriting their ID,
version, result, or checksum.

Users explicitly select the variance model. Diagnostics may advise but never
change this selection.

| Variance model | Omnibus test | Compatible comparisons |
| --- | --- | --- |
| equal (`standard`) | pooled one-way ANOVA | none, Tukey-Kramer, Dunnett |
| unequal (`welch`) | Welch one-way ANOVA | none, Games-Howell |

Requested comparisons use `comparison_policy="when_requested"` by default,
including when the omnibus p-value is not significant. The legacy
`after_significant` policy remains explicit and restorable.

## Statistical Policy

- Standard ANOVA preserves the existing SS, MS, F, eta-squared, and
  omega-squared calculations.
- Welch ANOVA uses weights `n_i / s_i^2`, the Welch correction, numerator df
  `k - 1`, and Satterthwaite denominator df. It does not present a pooled SS/MS
  table or pooled effect size.
- Tukey-Kramer compares all pairs with pooled within-group variance.
- Dunnett compares exactly `k - 1` treatments with the user-selected control.
  SciPy `dunnett` receives an explicit recorded RNG seed.
- Games-Howell compares all pairs using pair-specific standard errors and df
  with the studentized-range distribution.
- A zero-variance group blocks Welch and Games-Howell with a stable error; the
  implementation does not substitute another method.

## API Options

```json
{
  "response_column_id": "response-column-id",
  "group_column_id": "group-column-id",
  "alpha": 0.05,
  "confidence_level": 0.95,
  "anova_type": "standard",
  "posthoc_method": "dunnett",
  "posthoc_policy": "when_requested",
  "control_group_label": "A",
  "dunnett_rng_seed": 20260802,
  "missing_policy": "complete_case"
}
```

The bounded group-level preflight route applies the current filter snapshot and
returns first-occurrence labels plus usable N. A dataset, filter, or group
column change invalidates the selected control.

## Result And Tests

Schema `2` records the variance model, omnibus method, comparison method and
policy, control group when applicable, group summaries, exclusions, actual df,
confidence intervals, adjusted p-values, warnings, and package provenance.

Numerical and API coverage is in `backend/tests/unit/test_one_way_anova.py` and
`backend/tests/unit/test_api_contracts.py`.
