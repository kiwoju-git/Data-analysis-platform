# BO Factor Identity and Correlation Contract

## Scope and Status

This is the pure-domain/kernel boundary for the approved nominal/ordinal BO gate.
The initial implementation adds no study migration, API route, history mutation,
fit, recommendation, or UI availability by itself. Those integrations must bind
the factor-domain payload and numeric fitted-state payload to the exact source
hash, and preserve existing readers. Statistical tests are authored separately;
they are not recorded as passing before execution.

Numeric-only BO uses the existing `bo_kernels.signal_kernel` unchanged, including
Gaussian, Matern 5/2, Matern 3/2, and Exponential kernels and their bounds. This
module does not change standalone GPR, response normalization, observation noise,
jitter, EI, desirability, or batch selection.

Acceptance: exact factor identities; no category-code distance; explicit,
PSD correlation policy; analytic log-parameter gradients; JSON-only restoration;
unchanged numeric-only covariance; bounded parameter/matrix work; no refit during
kernel restoration. Integration must additionally verify fitted-state, API,
selection, profile, report and lifecycle behavior before advertising support.

## Identity and Encoding

`bo_factor_domains.py` defines numeric and categorical domain types. Numeric
domains delegate bounds and executable step checks to `DoeFactorDomain`.
Numeric coordinates are normalized using their original bounds. Nominal and
ordinal coordinates are complete string identities with an explicitly declared
level sequence. Whitespace, case, Unicode normalization and numeric-looking
strings are not silently changed. Nonempty identities have a stated 1,024
character upper bound; longer values fail rather than being truncated.

Nominal level order establishes a reproducible lookup table only. Ordinal order
is the declared sequence, never an alphabetical or inferred numeric sort.
Numeric encoding uses one integer lookup index per categorical factor, without
numeric scaling. Neither that index nor its difference is a distance. Unknown,
fractional or out-of-range codes and unknown level names are errors. A nominal
string `"1"` and numeric `1` are different inputs. No new category is inferred
when restoring or predicting.

Domain payload schema 1 uses `numeric_normalized_category_index_v1`. Numeric
kernel payload schema 1 uses `bo_product_factor_signal_v1`. Both require exact
known fields. Domain identities live separately from the numeric kernel state;
`validate_bo_factor_kernel_domains` verifies index, level count, kind and policy
agreement. The owning service must also verify the domain/source hash: matrix
shape alone cannot detect a vocabulary reordering of the same size.

## Implemented Product Policies

All factors multiply the existing numeric signal covariance. The product of PSD
factor kernels is PSD. With no numeric factors, the signal is an amplitude
parameter times the categorical product. Noise and jitter remain outside this
signal, so independent observations at the same condition do not acquire shared
measurement-noise covariance.

### Equal Positive Correlation

`equal_positive_correlation_v1`:

`C(a,b) = exp(-theta * I[a != b])`, `theta > 0`.

One parameter per factor, initial 1, bounds `[1e-4, 1e2]`. The diagonal is 1;
all distinct levels have the same positive correlation. The log-gradient is
`-theta * I[a != b] * C(a,b)`. This is the same mathematical restricted
positive-equality structure used by the existing GPR category kernel, not an
assertion that JMP uses that parameterization or forbids negative correlations.
When explicitly selected for an ordinal factor, this policy ignores order.

### Unequal Hyperspherical Correlation

`unequal_hyperspherical_correlation_v1` builds a unit-diagonal correlation matrix
`C = L L^T`. For row `i`, the lower-triangular entries are the successive
products of sines times the next cosine; its diagonal is the product of all row
sines. Angles are in `(0, pi)`, giving a positive triangular diagonal. Both
negative and positive between-level correlations are possible. An arbitrary
array of pairwise correlations is not accepted without a PSD construction.

There are `m*(m-1)/2` row-major angles for `m` levels. Initial angles are `pi/2`,
with bounds `[1e-4, pi-1e-4]`. Analytic derivatives include the chain rule for
log angles. Products of other category kernels are evaluated without division
by a correlation, because a valid correlation can be zero. An explicitly
requested ordinal use does not exploit ordering; it remains a level-matrix
policy. See the hypersphere approach in [Zhou, Qian and Zhou (2011)](https://doi.org/10.1198/TECH.2011.10025).

### Learned Monotone Ordinal Latent Coordinates

`ordinal_monotone_latent_rbf_v1` requires a declared ordinal domain:

`z_0 = 0`, `z_i = sum(gap_j, j < i)`, and
`C(i,j) = exp(-0.5 * (z_i-z_j)^2)`.

All gaps are positive, initially `1/(m-1)`, bounds `[1e-4, 10]`. The initial
equal spacing is an initialization, not fixed rank distance. Fitting may learn
unequal gaps. Anchoring the first level removes translation indeterminacy;
fixing the RBF length at 1 removes joint gap/length-scale indeterminacy. The
positive gaps also fix orientation. This assumes correlation decreases with
latent ordinal separation, but makes no monotonic-response assumption.

The log-gradient for gap `g_k` is
`-(z_i-z_j) * g_k * (I[i>k]-I[j>k]) * C(i,j)`.

This is an explicit product policy, not a recovered JMP latent-variable formula.
No fixed rank-distance kernel is silently substituted.

## JMP Alignment Boundary

The [JMP 19.2 BO launch documentation](https://www.jmp.com/support/help/en/19.2/jmp/launch-the-bayesian-optimization-platform.shtml)
lists Equal/Unequal options for nominal factors and Equal/Unequal/Latent options
for ordinal factors. Its public option list does not establish the BO optimizer
parameterization, bounds, ordinal covariance formulas or initialization.
The [standalone categorical GP documentation](https://www.jmp.com/support/help/en/19.2/jmp/statistical-details-for-models-with-categorical-predictors.shtml)
describes categorical correlation parameters, but is not evidence that BO uses
all the exact same numerical choices. Our explicit policies provide comparable
user choices without claiming JMP numerical parity. In particular, using an
order-ignoring matrix on ordinal data does not prove that JMP's corresponding
ordinal option has been replicated. No same-input JMP fitted output comparison
has been performed for these new kernels.

## Resource and Restoration Rules

- At most 10 total factors and 32 declared levels per category; at least 2 levels.
- Unequal correlation is limited to 8 levels per factor, and all categorical
  policies together have at most 64 parameters. These are product budgets.
- Covariance requests have at most 10,000 rows and 2,000,000 pair entries;
  gradient evaluation is limited to at most 200 rows. Higher-level budgets must
  include optimizer restarts, parameter count, MC/planning and array temporaries.
- Declared one-level factors are rejected. A fold/source containing only one
  observed declared level is not a different declared domain; its identification
  and coverage warning requires explicit service policy, not silent recoding.
- JSON stores finite numeric parameters, bounds, factor indices and known policy
  identifiers only. Explicit constructors restore kernels; no pickle, joblib,
  arbitrary objects, code loading, or training is used.
- Numeric signal state and category state are independent of observation noise.
  Model restoration must still validate the full training covariance/Cholesky,
  target/alpha relationship, normalization and source identity.

## Tests and Remaining Verification

Authored tests cover independent small correlation matrices, PSD, central
finite-difference gradients, negative unequal correlations, code permutations
with the matching permuted covariance, label bijections, learned ordinal gaps,
exact numeric-only regression, serialization/source immutability, malformed
payloads and resource/level bounds. Gradient tolerances are `rtol=2e-6`,
`atol=2e-9` for centered differences of step `1e-6`; covariance tolerances are
approximately machine-scale `1e-14`, not relaxed prediction tolerances.

At initial authoring, execution is held by the orchestrator's single-heavy-suite
resource policy. Integration tests, fitted reference comparisons, browser
workflows, native Windows/Linux and archive checks remain separate evidence.
