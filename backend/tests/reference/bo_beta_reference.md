# Independent Beta Improvement Reference

The fixture `fixtures/bo_beta_decimal_reference.json` contains synthetic scalar
inputs. No fitted model, private dataset, or external statistical product is its
reference. The module imports no production BO numerical helper.

## Reproduction

With dependencies installed, from the repository root in PowerShell:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'backend'
.\.venv\Scripts\python.exe -m tests.reference.bo_beta_reference
.\.venv\Scripts\python.exe -m pytest .\backend\tests\reference\test_bo_beta_decimal_reference.py -q
```

The generator prints results, binary64 input hex representations, runtime
versions, quadrature error estimates, and truncation bounds. It does not rewrite
the fixture. There is no random sampling or seed.

## Calculation

The target is `E[(X-t)+]` for `X ~ Beta(a,b)`. It is the positive density
integral from `t` to 1. The Beta density and Gamma normalization follow
[NIST DLMF 8.17](https://dlmf.nist.gov/8.17).

Moment conversion uses the same explicitly stated binary64 model definition,
not a decimal reinterpretation of the printed inputs. Those stored binary64
shapes and threshold are then converted exactly using `Decimal.from_float`.
The reference evaluates `(a-1)*ln(x) + (b-1)*ln(1-x) - ln(B(a,b))` at 80 digits.
It does not use production centering, `log1pmx`, survival-probability subtraction,
reflection, or a Gaussian approximation.

Log-Gamma uses the Stirling expansion through the `x^-13` term, with the first
omitted `3617/(122400*x^15)` magnitude bounding each positive-real remainder.
The reference reports the sum of the three remainder bounds for Beta
normalization. The expansion and remainder rule are from
[NIST DLMF 5.11](https://dlmf.nist.gov/5.11).

For stable positive quadrature, put `x=t+w*u`, factoring out `f(t)*w^2`.
Here `w` is the smaller of the standard deviation and the inverse negative
log-density slope, when that slope is negative. Decimal arithmetic evaluates
the density ratio at every quadrature point. Only the final dimensionless
integrand values are rounded to binary64 for QUADPACK. This is **not** a claim
of arbitrary-precision quadrature.

The finite upper integration limit is 64, or the support boundary if closer.
For an omitted tail and log-concave density, the tangent at `U` bounds its
dimensionless integral by `exp(log_ratio(U))*(U/r+1/r^2)`, where `r` is the
negative slope in width units. The reference rejects a nonnegative slope or an
insufficient bound; it does not silently discard an unvalidated tail.

## Scope And Tolerances

- Shapes are at least 100, their sum at most `1e40`, and `0<t<1`.
- A lower threshold is limited to eight standard deviations below the mean.
- Requested quadrature relative tolerance: `2e-12`; accepted error estimate:
  `2e-11`; accepted omitted-tail relative bound: `2e-12`.
- Frozen reference values must reproduce within `2e-12` relative error.
- Production comparison uses `2e-7` relative error and zero absolute allowance.
  The zero fixture must return exactly zero and also satisfy its log-space bound.
- These are validated fixture limits, not a general-purpose special-function
  library or a formal interval-arithmetic certificate for all binary64 inputs.

An independent hand-checkable normalization test uses integer `a=b=100`,
`t=1/2`, whose exact EI is `binomial(200,100)/4^101`. The far-tail fixture has
`log(EI)=-746.0088854781562` and a tangent log upper bound
`-746.0067839909478`, both below the half-smallest-subnormal boundary
`-1075*ln(2)=-745.1332191019412`. Its zero is binary64 rounding, not a point mass.
