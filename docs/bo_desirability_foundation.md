# BO Desirability Foundation (Stage 3a)

BASE_SHA: `1db522a12a4023995d52bdcdcf750f9500c47381`.
Working branch: `feat/bo-desirability`. Owner requested local work only:
no GitHub push, remote CI trigger, PR update or Linux publication in this stage.
The owner explicitly selected the publicly verifiable desirability-policy option
on 2026-11-07, with possible numerical differences from JMP disclosed.

## Scope And Acceptance

This is a tested calculation foundation, **not a released multiresponse BO
feature**. Stage 2's single-response kernel selection, EI/ETI, candidate review,
atomic confirmation, trial/history readers and managed reports are unchanged.
No new UI option advertises a feature that cannot yet be stored/restored.

Acceptance for this small step:

1. Explicit maximize/minimize/target curves and positive normalized importance.
2. Independent raw-unit Gaussian posterior moments, with powers inside the
   expectation, nonzero tiny variance and narrow target supports preserved.
3. Explicit moment-matched Beta improvement, with degenerate distributions and
   numerical limitations separated from exact transformed-Gaussian EI.
4. Read-only evaluation of actual existing BO GP models, keeping latent and
   new-observation predictive uncertainty separate. No refit or history change.
5. Independent hand calculations, quadrature and Cholesky fixtures, then current
   regression/static checks. No fabricated JMP output or reused prior test pass.

Risks: undocumented JMP curve details; independence between responses; Beta
approximation bias; numerical cancellation; mistaken response IDs; fitting a
sign-transformed response; unbounded quadrature. These are covered below or
explicitly remain outside this stage. There is no new dependency, filesystem
access, external call, telemetry, SQL migration or change to stored artifacts.
API31 / metadata25 / BO method0.8.0 remain unchanged because the new pure
functions are not connected to the public or stored contracts.

## JMP Alignment And Differences

Inspected official references on 2026-11-07:

- [JMP19.2 response limits](https://www.jmp.com/support/help/en/19.2/jmp/response-limits.shtml)
  describes goals, three control points and relative importance.
- [JMP19.2 curve construction](https://www.jmp.com/support/help/en/19.2/jmp/construction-of-desirability-functions.shtml)
  describes cubic/exponential pieces for directional goals and scaled normal
  density/exponential pieces for target goals. Coefficients, endpoint slopes
  and exact tail joins were not established from the public documentation.
- [JMP19.2 target example](https://www.jmp.com/support/help/ja/19.2/jmp/example-of-the-response-limits-column-property.shtml)
  displays `0.0183 / 1 / 0.0183`. A rounded display does not establish exact
  constants. Generic Profiler defaults are not automatically BO defaults.
- [Official 2026 JSM presentation](https://ww2.amstat.org/meetings/jsm/2026/onlineprogram/abstract.cfm?sid=6583&tid=6584)
  and its attachment describe response moments, their products and a
  moment-matched Beta EI. This presentation is not a same-input JMP19.2 run.
- [NIST desirability equations](https://www.itl.nist.gov/div898/handbook/pri/section5/pri5322.htm)
  supply the explicit Derringer-Suich equations used for this foundation's
  shape-one policy. This is deliberately **not JMP curve emulation**.

The UI workflow may eventually align with JMP while numerical results differ.
No actual JMP installation or matching output is available. Exact JMP curve,
intercept fitting, incumbent, latent-versus-predictive choice and augmentation
parity are not established. Do not rename this policy to imply that parity.

## Explicit Curve Contract

`CURVE_POLICY = derringer_suich_linear_v1`.
Response IDs, not list positions or translated labels, join predictions/goals.
One to four active responses are supported by this internal foundation.
This is a bounded product policy, not a general statistical maximum.

- Maximize: `d=0` below L, `(y-L)/(T-L)` between L/T, `1` above T.
  L<T is required; U must be absent.
- Minimize: `d=1` below T, `(U-y)/(U-T)` between T/U, `0` above U.
  T<U is required; L must be absent.
- Match target: `0` outside [L,U], linear L-to-T rise and T-to-U fall.
  L<T<U is required. This is not the Gaussian target curve described by JMP.

All thresholds are finite raw response values. They are preferences, not factor
bounds or automatic feasibility constraints. No bounds sorting, implicit target,
zero filling or user-string-to-number coercion occurs. Finite positive importance
is normalized using maximum scaling before summation; an unrepresentable positive
normalized weight is rejected rather than removing that response. For weights
`w_i`, `D=prod(d_i**w_i)`. Any exact zero individual desirability makes D zero,
including at extremely small but positive importance. No inactive/None goal,
custom desirability control values or curve-shape option is exposed in this step.

## Moments And Numerical Policy

`MOMENT_POLICY = independent_latent_gaussian_split_quadrature_v1`.
Each response posterior is assumed independent of the other response posteriors.
This is a model assumption, not proof that measured responses are independent.

For response i and normalized importance w:

```text
m_i = E[d_i(Y_i)^w_i]
s_i = E[d_i(Y_i)^(2*w_i)]
M = product(m_i)
S = product(s_i)
Var(D) = S - M^2  (definition, not the unstable implementation)
```

`E[d]^w` and `d(E[Y])` are not replacements. Implementation integrates centered
differences directly and combines independent variances using
`Var(XY)=Var(X)*E[Y^2]+E[X]^2*Var(Y)`. `log1p/expm1` retain differences smaller
than the ULP of the central desirability. The returned second moment can round to
M squared while the separately computed variance remains positive.

Every finite ramp is integrated separately with existing SciPy QUADPACK; plateau
probabilities use normal CDF/survival tails. Narrow ramps use their original
unit-interval coordinate and width/SD Jacobian, avoiding loss of nearly equal
standardized endpoints away from the Gaussian center. Broad ramps use normal z
coordinates split at zero, within [-12,12]. The omitted normal mass bound is at
most `2*Phi(-12)` per response, about3.553e-33. It is an absolute, not relative,
bound; no relative accuracy is promised below floating-point/tail resolution.
`estimated_absolute_error` is the accumulated QUADPACK estimate, **not a rigorous
certified error bound**. It is separate from the analytic normal-tail bound.

Each response permits at most20,000 integrand evaluations and128 subdivisions
per piece; a joint calculation permits at most4 such responses, hence80,000
evaluations. The relative quadrature criterion is2e-10 with an extremely small
absolute floor so positive small values are not accepted merely as zero.
Nonconvergence and budget exhaustion are stable errors, not partial success.
This is not yet a timed candidate-pool optimizer or MC batch implementation.

`evaluate_surrogate_desirability` accepts one explicitly normalized candidate
and response-keyed existing `BoSurrogate` objects. It only calls `predict`:
raw mean = scaled mean*stored scale+stored mean; latent and predictive SD each
use stored scale. Models must fit the original response (`direction_multiplier=1`),
including minimize goals. Latent SD enters desirability integration; measurement
noise is returned separately through predictive SD, and jitter is not added.
Source/hash/owner validation remains the responsibility of the future service
adapter; this helper is not a substitute for a persisted-model reader.

## Beta Improvement

`ACQUISITION_POLICY = independent_desirability_beta_ei_v1`.
The caller explicitly supplies a desirability incumbent. This stage does not
silently choose an observed or latent incumbent policy.

```text
c = M*(1-M)/V - 1
a = M*c; b = (1-M)*c
t = incumbent + xi
EI = M*BetaSF(t; a+1,b) - t*BetaSF(t; a,b)
```

Xi is dimensionless desirability improvement, not the old standardized-Y xi.
It is applied once. V=0 is a point mass; V=M(1-M) is the endpoint Bernoulli limit,
not an invalid Beta(0,0). Inconsistent moments are rejected. Positive variance
is never silently classified as deterministic. The API43 numerical repair uses
positive width-scaled Beta-density quadrature for concentrated distributions,
with high-precision centering of the stored binary64 shape parameters. A
log-concave tangent bound can establish that EI rounds to binary64 zero; zero
is not inferred merely because two survival terms cancel. Unresolved widths,
quadrature error or unsupported shapes still return
`bayesian_desirability_beta_precision_unsupported`. No Gaussian or point-mass
approximation replaces a positive-variance Beta. See `bo_xy_start_validation.md`
for boundary cases and independent reference evidence. The statistical policy
and old saved artifacts are unchanged. New acquisitions and conditional samplers
record `numerical_policy=positive_beta_integral_v2`; absent-policy stored results
use the frozen legacy arithmetic. See `bo_beta_numerical_compatibility.md` for
reader dispatch and unchanged legacy serialization/hash verification.

Independent examples:

- Beta(2,2), t=.5: EI=3/32=.09375.
- Independent `d_i=Phi(Y_i)`, Y_i~N(0,1), equal importance: M=4/9,
  S=1/4 and V=17/324. The moment-matched Beta has a=28/17,b=35/17.
  At t=.5 its EI is about.07153759904846113, whereas the exact product
  distribution EI is `1/72+log(2)/12`, about.07165115393555099.
  The approximately-0.00011355488709 difference is approximation error, not
  evidence that the exact transformed distribution was integrated.

## Current-Run Evidence

- Red: both new test files failed collection because the modules did not exist.
- Initial green:57 tests passed. Independent read-only review then found three
  issues: off-center narrow supports could disappear, complex NumPy scalars could
  lose their imaginary part, and an extreme Beta shortcut could return infinite
  shape metadata. All three received regressions and fixes.
- The tiny-positive-importance regression initially failed due to quadrature
  cancellation. Stable powered differences fixed it without relaxing tolerance.
- Expanded unit/real-GP bridge suite:78 passed in4.47s on Windows10 Home19045,
  CPython3.10.11, SciPy1.15.3, NumPy2.2.6, sklearn1.7.2, CPU-only, one BLAS thread.
  This is not a Windows11, Linux, browser, API or installed-archive test.
- The real-GP fixture uses two independently fitted existing BO surrogates with
  fixed hyperparameters (`optimize=False`, not an optimizer-convergence test) and
  checks raw posterior mean/variance against independently written Matern5/2
  Cholesky equations; response moments use independent raw-payoff integration.
  Model arrays remain element-wise unchanged and refit is forbidden during evaluation.
- The first repository Ruff scan found new import/style and captured-loop-variable
  warnings. They were corrected rather than suppressed. Subsequent checks are
  recorded below as they complete.
- Related BO regression:181 tests passed in158.65s, including existing latent
  EI/ETI, kernel/posterior/compression calculations, real-spawn kernel APIs,
  reviewed recommendation confirmation and legacy storage paths. Five existing
  Starlette deprecation warnings were reported; no dependency was changed.
- Full repository Ruff lint, format (471 files), mypy (249 source modules),
  tutorial Markdown18 blocks and capability AST11 tests/matrix checks passed.
- `powershell -ExecutionPolicy Bypass -File scripts/check.ps1`: the full backend
  phase completed with3408 passed,9 skipped,118 warnings in3218.22s. All80 new
  desirability tests passed in that run. Skips concern Linux-only behavior or
  symlink privileges unavailable to this non-administrator Windows account;
  they are not counted as passes. Existing Starlette deprecations and the
  deliberate duplicate-archive fixture warning remain, without dependency churn.
- Localization2973 strings/4646 keys and frontend lint passed; lint retains12
  existing fast-refresh warnings. Frontend typecheck passed, all129 files/1124
  tests passed in77.79s, and the production build passed in4.37s with the existing
  large-chunk/localization-plugin timing warnings. The complete `check.ps1`
  finished with exit code0. Heavy tests ran sequentially; the unchanged frontend
  test configuration permits at most2 workers.
- This turn did not run actual browser E2E, a Linux interpreter/installed archive,
  new dependency advisory audits, remote CI or a JMP comparison. No UI or public
  multiresponse contract was added. Existing API regression evidence above must
  not be described as new multiresponse API/browser acceptance.

Focused reproduction from this worktree, using the existing locked environment:

```powershell
$env:PYTHONPATH = Join-Path $PWD 'backend'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_desirability.py backend/tests/unit/test_bo_desirability_acquisition.py backend/tests/unit/test_bo_desirability_posterior.py -q
```

## Next Gate And Rollback

The next public integration still requires immutable response definitions and complete observation
vectors, atomic/idempotent observation updates, versioned history hashing,
per-response fit budgets, an explicit incumbent policy, source-locked review and
confirmation, restart/legacy readers, UI/report controls and actual browser tests.
Joint multiresponse batch planning is also not implemented by this foundation.
Do not use calculated joint desirability as a fake measured scalar observation.
Do not enable a multiresponse menu until all these paths work together.

[Stage3b](bo_desirability_recommendation_core.md) now implements the internal q1
model/search/worker contract, explicit incumbent and combined fit budget. Its
current-run evidence is separate from the foundation results above; it does not
yet implement the persistence/UI/report gate.

No production caller, API version, metadata schema or legacy artifact changed.
There is currently no new commit or remote deployment to roll back. After a future
commit, revert only that foundation commit; do not revert previous BO/DOE changes
or delete any workspace, raw data, model, trial, history or report.
