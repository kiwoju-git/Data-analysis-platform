# DOE Factor Domain and Execution Resolution Audit

## Scope and decision

This audit covers the factor-domain semantics required by Factorial DOE, Latin
Hypercube Sampling (LHS), Response Surface Methodology (RSM), Response
Optimizer, and Bayesian Optimization. It distinguishes display formatting from
the executable values that can actually be set in an experiment.

The implementation decision for this change is:

- Preserve the existing continuous-factor path byte-for-byte where possible.
- Add `discrete_numeric` factors whose legal values are `low + k * step`.
- Validate the grid with decimal arithmetic, not binary floating-point modulo.
- Never create a continuous candidate and silently round only the final result.
- Reject Factorial center points and RSM axial points that are not executable.
- Generate mixed LHS discrete coordinates with balanced level allocation and
  validate uniqueness after conversion to actual units.
- Generate Bayesian candidates on the executable domain and recheck constraints
  and duplicates in actual units.
- Keep explicit, irregular numeric level lists as a follow-up feature.

## Official-source findings

| Source | Relevant finding | Product consequence |
| --- | --- | --- |
| JMP, *Factors* | A continuous factor can conceptually take any value between its limits. A discrete numeric factor takes only ordered numeric levels, while model fitting can still treat it as continuous. | Storage domain and model interpretation are separate. `discrete_numeric` is not a categorical factor. |
| JMP, *Factors in Designed Experiments* | Discrete numeric factors limit a design to available values and designs seek balanced representation across those values. | Mixed designs allocate executable levels deliberately rather than rounding continuous points. |
| SciPy 1.15.3, `LatinHypercube` | A classical LHS places one point in each marginal stratum. `random-cd` is a post-processing optimization and does not promise preservation of every property. | Continuous-only LHS retains the existing SciPy policy. Mixed LHS reports continuous strata and discrete balance separately. |
| SciPy 1.15.3, `qmc.scale` | Unit-cube samples are linearly scaled into actual bounds. | Continuous coordinates keep the established scaling rule. |
| SciPy 1.15.3, `LatinHypercube.integers` | Integer samples are obtained through bounded interval mapping rather than arbitrary decimal display rounding. | Fixed-step values are treated as a bounded executable domain from candidate generation onward. |
| Minitab, *Specify the Design for Create Central Composite Design* | Face-centered axial points use the factor low/high settings; rotatable CCD uses an alpha determined by the design. | A fixed-step factor may be compatible with face-centered CCD but incompatible with a rotatable axial value. |
| Minitab, *What factor values should I use?* | Axial values can lie outside the cube and can be physically infeasible. | The application must expose incompatibility and must not move an axial point to a nearby grid value. |

Official references:

- https://www.jmp.com/support/help/en/19.0/jmp/factors-4.shtml
- https://www.jmp.com/en/statistics-knowledge-portal/design-of-experiments/key-design-of-experiments-concepts/factors-in-designed-experiments
- https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.stats.qmc.LatinHypercube.html
- https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.stats.qmc.scale.html
- https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.stats.qmc.LatinHypercube.integers.html
- https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/response-surface/create-response-surface-design/create-central-composite-design/create-the-design/specify-the-design/
- https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/supporting-topics/response-surface-designs/what-factor-values-should-i-use/

## Method audit

| Method | Continuous | Fixed-step numeric | Duplicate / quality risk | Constraint / model risk | This change |
| --- | --- | --- | --- | --- | --- |
| Factorial | Existing two-level path | Low and high must be grid values; every center point must also be on-grid | No new duplicate risk when validation succeeds | Moving a center point changes the requested design | Validate and reject an incompatible center; never round it |
| LHS | Existing SciPy LHS and `random-cd` | Balanced assignment of LHS ranks to legal levels | Quantization can create duplicate rows and changes classical strata semantics | Constraints must be evaluated on executable coordinates | Mixed policy with deterministic repair, exact run count, uniqueness, continuous-strata and discrete-balance diagnostics |
| RSM | Existing rotatable and face-centered CCD | Every factorial, center, and axial point must be on-grid | Rounding can duplicate points and reduce rank | Rounding rotatable axial points invalidates the rotatability claim | Preflight all generated points; reject incompatible rotatable CCD and suggest compatible settings |
| Response Optimizer | Existing continuous bounded search | Candidate and profile coordinates must be legal levels | Final-only rounding can duplicate or miss optima | A rounded candidate can violate constraints | Search/evaluate on legal levels and validate actual coordinates |
| Bayesian Optimization | Existing continuous LHS/candidate pool | Initial designs use mixed LHS; recommendations use legal-level candidate generation | Rounded recommendations can collide with completed, pending, abandoned, or same-batch trials | Quantized points can violate constraints and alter acquisition values | Generate on-domain, recheck actual constraints and all duplicate sets |

## Contract

Each numeric DOE factor has:

```json
{
  "name": "sample_day",
  "low": 1,
  "high": 10,
  "unit": "day",
  "domain_kind": "continuous",
  "step": null,
  "display_decimals": null
}
```

For `discrete_numeric`, `step` is required, finite, positive, and the high bound
must equal `low + K * step` for an integer `K >= 1`. The legal-level count is
bounded to prevent excessive enumeration. `display_decimals` controls only
presentation and export formatting; it never changes stored or calculated
coordinates.

Legacy factors without the new fields are read as continuous factors with no
step or display precision. Existing stored bytes and checksums are not rewritten.

## Quality and limitations

For a mixed LHS, `continuous_strata_valid` applies only to continuous dimensions.
`discrete_level_balance` reports per-level use counts and whether their maximum
difference is at most one. Centered discrepancy is calculated on the final,
executable normalized coordinates. The product does not claim that a mixed
fixed-step design has all properties of a purely continuous classical LHS.

Explicit non-equidistant numeric levels, custom executable center values, and
custom executable RSM designs are deferred. Users must change bounds, step,
center-point count, or CCD type when a requested design is not executable.

## Version impact

The new factor fields alter generated coordinates and persisted design meaning,
so affected method and result/study schema versions must advance while legacy
readers remain available. The fields fit existing JSON definitions, therefore a
SQLite migration is not required solely for factor-domain support.
