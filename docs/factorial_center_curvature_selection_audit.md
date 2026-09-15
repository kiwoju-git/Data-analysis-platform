# Center Curvature Selection Audit

Pre-implementation review: 2026-09-16. Base origin/main:
`2062546bdf26cf87334264c5e13ec39a40ed20fe`.
Branch: `feat/factorial-curvature-and-gp-kernel-selection`.

## Acceptance and Compatibility Risks

Reproduce the supplied 11-run experiment, remove Center then AB, retain B
because BC remains, and preserve all existing paste/revision/prediction/report
ownership. GP comparison is addressed by its separate contract. No user data,
logs or workspaces enter Git. No new production dependency or metadata migration
is expected. `data_prd.md` is absent; the addendum and current method contracts
govern. The referenced image is not attached to this request; the specified
Coef/P step matrix is the layout contract, not a copied image.

## Official Sources

- [Minitab model terms](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/analyze-factorial-design/perform-the-analysis/specify-the-model-terms/)
- [Minitab stepwise options](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/analyze-factorial-design/perform-the-analysis/perform-stepwise-regression/)
- [Minitab stepwise formulas](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/analyze-factorial-design/methods-and-formulas/stepwise/)
- [Minitab ANOVA/error partition](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/analyze-factorial-design/interpret-the-results/all-statistics-and-graphs/analysis-of-variance-table/)
- [NIST two-level factorial analysis](https://www.itl.nist.gov/div898/handbook/pri/section4/pri471.htm)

Minitab exposes term membership and center inclusion independently of maximum
order. Backward removes the largest eligible partial-F p above alpha. Saturated
starts pool small adjusted SS while preserving hierarchy. These sources do not
establish every undocumented Minitab tie rule; our deterministic ties are an
explicit product policy, validated against the supplied numerical reference.
No Minitab executable is used or claimed.

## Existing Defects

`factorial_analysis.py` labels intercept, block and curvature fixed. The neutral
selection engine also treats every nonfixed block's factor set as hierarchical:
the empty curvature set would be a subset of every factorial term. Merely
changing fixed to false is therefore wrong. Forced interactions also need to
protect their parents; skipping all fixed blocks during hierarchy checks is
insufficient. `model_policy.center_curvature_included` currently reports design
availability rather than final membership.

## Supplied Reference

Temperature 35/37, pH 6/7, Glucose 1/2; unrandomized full factorial, one
replicate, three centers, one block. Standard-order responses:
`1.88, 5.79, 0.91, 4.87, 4.23, 5.39, 5.09, 6.04, 4.11, 4.36, 4.26`.
Order 2, confidence .95, removal alpha .05, strong hierarchy.

| Model | Residual DF | S | R-squared | Adjusted R-squared | Predicted R-squared | PRESS |
|---|---:|---:|---:|---:|---:|---:|
| Initial | 3 | .1156383 | .99838024 | .99460080 | .97528774 | .61205000 |
| Without Center | 4 | .1028403 | .99829190 | .99572976 | .98394324 | .39767873 |
| Without Center and AB | 5 | .0953987 | .99816270 | .99632540 | .99224843 | .19198344 |

Initial p: Center .712962, AB .658244, B .329344. After Center removal,
AB p .611548. Final B p .218078 is retained for BC. Forcing Center reproduces
the previous AB-first path and Center p .676363. Rounded supplied statistics
use absolute tolerance 1e-6; independently generated full-precision fixtures use
absolute 1e-9 / relative 1e-8. Display rounding is not storage precision.

## Error and Prediction Policy

Center included: curvature is one model DF. Center absent: its lack-of-fit
contribution remains in residual error, never duplicated in Model. Replicate
within-setting variation remains pure error. Report the ordinary aggregate
lack-of-fit plus an explicitly nonadditive curvature diagnostic if available;
do not add a second error sum. The prediction basis, not design center count,
decides whether interior numeric settings are permitted. Existing saved bases
and their checksums remain unchanged.

## Release Gate

Baseline, failing old-path regression, independent equations, focused/full
backend, Vitest, strict types, build, localization and Chromium desktop/mobile
must be recorded. Synchronize with origin/main and repeat release gates before
non-force fast-forward publication. Old schema-2 DOE results remain readable.
