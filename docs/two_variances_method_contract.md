# Two Variances v0.1

`quality.two_variances` / `0.1.0`, summary `two_variances_test`, result schema 1.
Generic immutable analysis-run storage and exports; no model or DB migration.
API contract increases from 21 to 22; metadata remains 20.

## Scope and Risks

Exactly two independent groups after the recorded filter and complete-case
numeric parsing. Group keys use complete canonical text (including whitespace), never truncated
display labels. Numerator/denominator order is explicit. Maximum 20,000 usable
rows; exceeding the cap fails, rather than sampling. Display points are bounded
deterministically to 500 per group with filtered analysis row identities.
Privacy: no raw values in errors or logs. Preflight creates no analysis asset.

Default median-centered Brown-Forsythe uses SciPy Levene, minimum three values
per group, equality ratio 1 and two-sided alternative only. The ratio estimate
is descriptive; no ratio CI is provided. Degenerate deviations fail explicitly.
Normal-theory F requires at least two values per group and strictly positive
sample variances (ddof=1). No automatic normality-based method selection.
Independence cannot be established by software. F inference is sensitive to
non-normality. Non-rejection does not prove equal variances.

For variance ratio r and hypothesized ratio theta0, F=r/theta0. SD hypotheses
square theta0 first. F uses df=(n1-1,n2-1); lower/upper tails are CDF/SF, and
two-sided p=min(1,2*min(CDF,SF)). Quantiles use SciPy CDF probabilities, not
NIST's upper-tail notation. Two-sided CI is
[r/F.ppf(1-alpha/2), r/F.ppf(alpha/2)]. Greater uses
[r/F.ppf(1-alpha),unbounded), less uses [0,r/F.ppf(alpha)]. SD bounds are square
roots. CI estimates the actual population ratio, not ratio/theta0. Unbounded
endpoints have kind=unbounded, never JSON Infinity. Numerical overflow fails.

The v0.1 scope is intentionally narrower than the earlier Bonett draft:
Bonett ratio CI, Both mode and post-hoc combined conclusions are unsupported.
Existing `eda.equal_variances` and its Bonett implementation are unchanged.

## Verification Contract

Independent supplied reference: [1,2,3,4,5] and [1,3,5,7,9], variances 2.5/10,
ratio .25, SD ratio .5, F=.25, df4/4, p=.208; BF=72/35,
p=.189403661093321. F95% CI [.0260293843634819,2.40113247118072].
Tolerance 1e-11 relative / 1e-13 absolute for these moderate-scale references;
swap, scale, sidedness and SD transformations tested separately. Extreme
non-finite calculations fail rather than widening reference tolerances.
Exports read saved payload only, with escaping, provenance and warnings.

Sources: [SciPy 1.15.3 Levene](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.stats.levene.html),
[NIST F test](https://www.itl.nist.gov/div898/handbook/eda/section3/eda359.htm).
