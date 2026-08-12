# HTML Report Coverage Matrix

HTML report artifact schema 3 is generated only from the stored result envelope. It records
the requested `en` or `ko` report locale and does not
rerun analyses or read raw dataset rows. All user-provided text is escaped and all graphics are
self-contained inline SVG without scripts or external resources.

| Result family | User summary | Tables | Inline SVG | Stored payload source | Notes |
| --- | --- | --- | --- | --- | --- |
| Descriptive statistics | Yes | Column statistics | No | `result.columns` | HF6 method is shown for schema 2 |
| Graphical Summary | Yes | Distribution/statistics/CI | Histogram normal fit, boxplot, Q-Q, CI plot, ECDF | `result.columns` | Full graph coverage required |
| Normality | Yes | Test summary | Q-Q when stored | Stored test/plot payload | No calculation during export |
| Equal variances | Yes | Multiple comparisons, Levene, groups | Comparison intervals | Stored schema 2 payload | Schema 1 keeps legacy rows |
| Hypothesis methods | Yes | Estimates, intervals, tests/effects | Stored plots when present | Stored result payload | Method-specific renderer |
| Categorical methods | Yes | Counts/tests/effects | Stored plots when present | Stored result payload | Method-specific renderer |
| Regression | Yes | Equation, summary, coefficients, ANOVA, diagnostics | Stored diagnostic/profile payloads | Stored result payload | No model refit |
| Quality methods | Yes | Chart/capability/gage summaries | Stored chart payloads | Stored result payload | No raw samples embedded |
| Unknown future result | Yes | Safe high-level summary | No | Envelope metadata | Closed raw JSON details only |

The large path/value Result Envelope table from artifact schema 1 is removed from the default
body. A closed `details` element may expose escaped pretty JSON for audit use, after all
user-facing sections.
