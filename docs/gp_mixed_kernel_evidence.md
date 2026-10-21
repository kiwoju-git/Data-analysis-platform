# Mixed GPR Calculation Evidence

Date: 2026-10-21. Baseline: `3284a359c31ccfb738ddf16078440f674d52f42f`.

This ledger covers the new pure preprocessing/kernel modules and their unit
tests only. It is not evidence that the analysis API, manifest-4 prediction
reader, UI, report, or Linux release supports mixed predictors end to end.
Those integrations require their own evidence before the capability is exposed.
The existing numeric-only GPR and saved model readers are not replaced here.

## Preprocessing Contract

`gp_preprocessing.py` provides:

- `GpPredictorSpec(column_id, kind)` with `numeric` or `nominal` kind. The caller
  keeps display name, unit and source lineage; display labels are not identity.
- `fit_gp_preprocessor(rows, predictors, standardize_numeric=True)` returns
  a `GpPreprocessor` and finite numeric matrix in original predictor order.
- `transform_gp_rows` uses the already fitted processor. It never learns levels,
  scale, mode or median from prediction/validation rows.
- `validate_encoded_gp_matrix` rejects object/string arrays, non-finite values,
  wrong shape, fractional category codes and codes outside the stored vocabulary.
- `GpPreprocessor.to_payload/from_payload` use a strictly validated JSON mapping,
  with no Python object deserialization. Predictor order, full vocabulary,
  training counts and the numeric transformation are preserved.

Numeric predictors use training-fold mean and sample SD (`ddof=1`) when scaling
is requested. Category integer codes are **equality identifiers**, never scaled
or assigned a numeric-distance interpretation. Input numbers must already be
finite numeric values; the existing dataset parser remains responsible for
decimal/thousands parsing. Nominal values must be nonempty strings; no numeric
conversion, Unicode normalization, case folding, trimming or truncation occurs
inside this module.

Vocabularies follow first training occurrence. Modes use maximum training count,
with first training occurrence as the deterministic tie break. Numeric hold values
are raw-unit training medians. One-level nominal predictors are retained in the
preprocessor but omitted from the active categorical-kernel mapping, contributing
exactly one. Unseen validation/prediction levels fail with `gp_category_unknown`;
they are not excluded or replaced with a learned level.

Limits are product policy: 12 original predictors, at most 4 nominal predictors
and 32 levels per nominal predictor. They are not mathematical GP limits. Warnings
identify one-level training folds, levels represented fewer than 3 times, and
cardinality greater than 16 or more than half the training N.

Numeric constants fail by default. The explicit
`allow_constant_numeric=True, standardize_numeric=False` option preserves the
existing unscaled-fold behavior; it is not permission to bypass the full-data
constant-predictor check. Its policy is persisted and warning is retained.

Integration must fit a fresh processor on **each training fold** after the split,
then transform validation rows. Fitting once on all rows would leak scale and
vocabulary information and is not made safe merely by using this helper.

## Kernel Contract

`MixedPredictorKernel` takes the existing numeric signal-kernel instance, numeric
column indices, active categorical indices, `categorical_theta` and its bounds.
For no numeric predictors the supplied numeric kernel is an amplitude-only
`ConstantKernel`. Otherwise the existing constant-times-Matern 5/2, Matern 3/2,
RBF or rational-quadratic policy is reused unchanged. RQ retains its shared length
scale; this module does not describe it as ARD.

```text
K = K_numeric * exp(-sum(theta_j * category_mismatch_j))
dK/d(log(theta_j)) = -theta_j * category_mismatch_j * K
```

The default category coefficient is 1 with positive bounds `[1e-4, 1e2]`.
Gradient order is existing numeric log parameters followed by active category
log parameters. Kernel cloning, `theta`, `bounds`, deep parameters and fixed
restoration follow scikit-learn 1.7.2's kernel interface. Exponentiation round-off
at a parameter bound is clipped only within a 32-epsilon tolerance; an actual
out-of-bounds parameter fails. Bound contact produces
`gp_category_theta_bound`. It is not silently treated as evidence of an optimal
physical correlation structure.

`mixed_kernel_to_payload/from_payload` serialize only a whitelisted signal type,
positive finite parameters and column mappings. Restored kernels are fixed.
NPZ arrays remain numeric. No pickle, joblib artifact, object array, new package,
internet call or arbitrary user kernel is introduced.

Each categorical factor has equal off-diagonal correlation `exp(-theta)` and
diagonal one. That matrix is positive semidefinite for positive theta; multiplying
the per-factor matrices and the numeric covariance preserves positive
semidefiniteness. This is a restricted categorical model, not JMP's level-pair
correlation model. See [JMP comparison](jmp_gp_bo_alignment.md).

The kernel allocates numeric and categorical gradient arrays. The extended Exact
GP memory estimator must count these temporaries and the concatenated gradient;
this helper does not itself enforce a process memory limit or make 2,000-row
configurations universally feasible.

## Executed Unit Evidence

Environment: Windows, CPython 3.10.11, NumPy 2.2.6, SciPy 1.15.3,
scikit-learn 1.7.2. Synthetic fixtures only. The initial tests were executed before
the new modules existed and failed imports. The first implementation then exposed
a boolean-gradient negation error and the fixed-kernel empty-bounds shape; both
were corrected without relaxing the numerical assertions.

```powershell
$env:PYTHONPATH = (Resolve-Path .\backend).Path
.\.venv\Scripts\python.exe -m pytest `
  backend/tests/unit/test_gp_preprocessing.py `
  backend/tests/unit/test_gp_mixed_kernels.py -q
```

Result: **29 tests passed** in 6.01 seconds using the available Python 3.10 test
environment with this worktree on `PYTHONPATH`. This is not a fresh-install test.

Evidence includes full long-name identity, training-only transformations, unknown
category errors, category renaming/code permutation, product limits, explicit
unscaled constant-fold policy, strict JSON/encoded-array validation, PSD, all four
numeric presets, analytic versus central finite-difference log gradients,
scikit-learn cloning and real L-BFGS-B fit, bound warning, fixed JSON restore,
numeric NPZ round-trip through a Korean/space path with `allow_pickle=False`,
and explicit rejection of missing/non-string nominal values and object NPZ data.

For an independent prediction check, a four-row Matern-5/2 mixed fixture was
evaluated using the scalar covariance formula and a separate NumPy Cholesky solve.
Restored-kernel posterior means/variances agreed at absolute/relative `1e-13`.
Log-gradient checks use a `1e-6` central-difference step, `rtol=2e-6` and
`atol=2e-9`; these are not production helpers generating their own references.

Mypy on the two new modules, using `--follow-imports=silent`, passed. Full-product
type checks, native Linux runs, API save/restore, nominal prediction/profile UI,
report parity, resource benchmarks and final archive validation are not established
by these tests. No actual JMP output was compared.
