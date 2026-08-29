# High-dimensional DOE capability audit

Status: implementation contract

Reviewed: 2026-08-29

Product authoring limit: 10 factors

## Decision

Statistical Twin uses 10 factors as the product-level authoring ceiling for the
DOE workflows in this release. This is a bounded local application running on a
single CPU. Ten factors is large enough for the intended screening,
space-filling, and sequential-optimization workflows while keeping forms,
stored manifests, validation, and deterministic diagnostics reviewable.

The product ceiling is not a promise that every design can run with ten
factors. Each method applies its own statistical and computational feasibility
rule before allocation:

| Method | Previous limit | Authoring limit | Executable rule | This release |
| --- | ---: | ---: | --- | --- |
| 2-level full factorial | 6 | 10 | `2^k * replicates + center runs <= 256` | Authoring expanded; infeasible designs blocked |
| Regular fractional factorial | 6 | 10 | Only an independently verified catalog entry may run | Existing 3-6 factor catalog retained |
| Plackett-Burman screening | none | 10 | 7-10 factors, verified 12-run catalog, main effects only | Added |
| General full factorial | 6 | 10 | `product(level counts) * replicates <= 256` | Authoring expanded; allocation blocked before materialization |
| Latin hypercube | 6 | 10 | 1-10 numeric factors, 2-200 runs | Added with dimension-aware guidance |
| Bayesian Optimization | 6 | 10 | 1-10 numeric factors; completed observations at least `d + 1` | Added with high-dimensional warnings |
| Central composite RSM | 5 | 5 | Existing verified 2-5 factor CCD contract | Unchanged |

## Why the limits are method-specific

A 2-level full factorial requires `2^k` corner runs. Ten factors therefore
require 1,024 corner runs before replicates or center points. The local product
cap remains 256 runs, so the ten-factor full design is rejected before the run
matrix is allocated. Minitab documents the same exponential run relationship
and shows that nine factors already require 512 runs.

A general full factorial has the same combinatorial issue. Ten factors with the
minimum two levels also require 1,024 runs. The editor accepts up to ten factor
definitions so a user can prepare and compare a design, but generation depends
on the level-product preview and the 256-run cap. Eight two-level factors use
exactly 256 runs; nine use 512 and are rejected.

Latin hypercube sampling does not enumerate all level combinations. SciPy's
LatinHypercube produces a stratified marginal sample in `d` dimensions, so ten
numeric factors are feasible within the existing 200-run bound. The product
shows `d + 1` as a calculation reference, `max(8, 3d)` as a recommended start,
and `min(200, 10d)` as a stronger space-filling reference. These are planning
guidelines, not statistical guarantees.

Bayesian Optimization can define ten factors, but exact Gaussian Process and
acquisition search quality degrade without enough observations. The hard
availability threshold is `max(2, d + 1)` completed observations. At eight or
more factors the result includes `bayesian_high_dimensional_study`; the UI also
shows approximately `3d` initial trials as a product recommendation. No rows or
candidate points are silently sampled.

## Seven-to-ten factor workflow

For 7-10 two-level factors the primary bounded workflow is:

1. run a 12-run Plackett-Burman screening design;
2. interpret only main-effect screening estimates with the documented
   interaction-confounding warning;
3. confirm important factors in a higher-resolution factorial design when
   resources permit;
4. use RSM only after reducing the active continuous factors to five or fewer.

The 12-run Plackett-Burman matrix can hold up to 11 factor columns and this
product exposes at most ten. Minitab documents that the 12-run design partially
confounds every main effect with several two-factor interactions. Minitab's
Assistant additionally omits the 12-run option for ten factors because of low
power and offers a 20-run design there. Statistical Twin retains the explicitly
requested bounded 12-run option for ten factors but displays a stronger power
and confounding warning. It must not be described as Minitab Assistant parity.

## RSM boundary and roadmap

The existing Central Composite Design remains limited to 2-5 continuous
factors. A full quadratic model for ten factors contains 66 parameters:

`1 intercept + 10 linear + 10 squared + 45 two-factor interactions`.

The current full-factorial-core CCD would also start with 1,024 corner points,
before axial and center points. Raising the UI limit to ten would therefore be
both computationally misleading and statistically unusable in this bounded
tool.

The planned high-dimensional response-surface path is a separate D-optimal
contract. It must define the candidate set, selected full or reduced model,
required rank, run count, D/A/G/V criterion, exchange algorithm, replicated
points, condition number, lack-of-fit behavior, and independent reference
fixtures. Minitab notes that a D-optimal design is optimal only for the model
terms supplied during selection. It remains planned until those choices are
explicit and tested.

## Complexity and safeguards

| Workflow | Dominant cost | Bounded safeguard |
| --- | --- | --- |
| Full/general factorial | Exponential/product run materialization | Preview and reject above 256 before allocation |
| Plackett-Burman | Fixed 12 by up to 10 matrix | Static catalog SHA, balance, orthogonality, rank tests |
| LHS random-CD | Repeated discrepancy optimization | 200-run cap, one numerical thread, no fallback to unoptimized LHS |
| Bayesian Optimization | Exact GP fit and acquisition candidate scoring | 10-factor cap, observation guidance, configured candidate budget, no silent sampling |
| CCD RSM | Factorial core plus quadratic model | Existing 5-factor cap retained |

## Official references

- Minitab, [Factorial and fractional factorial designs](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/supporting-topics/factorial-and-screening-designs/factorial-and-fractional-factorial-designs/)
- Minitab, [Available 2-level factorial designs](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/supporting-topics/factorial-and-screening-designs/available-2-level-factorial-designs/)
- Minitab, [Plackett-Burman designs](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/supporting-topics/factorial-and-screening-designs/plackett-burman-designs/)
- Minitab, [Overview of Quick Designs](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/quick-designs/overview/)
- Minitab, [Response surface, central composite, and Box-Behnken designs](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/supporting-topics/response-surface-designs/response-surface-central-composite-and-box-behnken-designs/)
- Minitab, [Data considerations for Select Optimal Design](https://support.minitab.com/en-us/minitab/help-and-how-to/statistical-modeling/doe/how-to/factorial/select-optimal-design/before-you-start/data-considerations/)
- SciPy 1.15, [`scipy.stats.qmc.LatinHypercube`](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.stats.qmc.LatinHypercube.html)
- JMP, [Example of Creating a Latin Hypercube Design](https://www.jmp.com/support/help/en/19.1/jmp/example-of-creating-a-latin-hypercube-design.shtml)
- scikit-learn, [Gaussian Processes user guide](https://scikit-learn.org/1.7/modules/gaussian_process.html)
