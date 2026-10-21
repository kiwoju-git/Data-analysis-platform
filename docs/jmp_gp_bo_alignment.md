# JMP GP And BO Alignment

Research date: 2026-10-21. Baseline source:
`3284a359c31ccfb738ddf16078440f674d52f42f` (API contract 25).

This is a source-backed comparison and an implementation acceptance checklist,
not a claim that the extension is released. Historical baseline and research-handoff
statuses below are explicitly dated; subsequent evidence is summarized in section 8. The current
extension's implementation/test ledger belongs in
`bo_gpr_noise_validation_extension.md`. Baseline observations below are fixed to
the stated commit; later code must be checked independently before changing a
status to verified. No JMP application was run and no same-input JMP output was
provided. Public documentation is not numerical-parity evidence.

## 1. Versions And Evidence

- The JMP sources below are the versioned English **19.2** documentation. This
  identifies the reference manual, not the locally installed JMP version or a
  claim that 19.2 is the latest available product.
- The repository pins NumPy **2.2.6**, SciPy **1.15.3**, and scikit-learn
  **1.7.2** in `backend/pyproject.toml`. Their versioned APIs govern this work.
- On the research date, the scikit-learn `/stable/` GroupKFold page identified
  itself as **1.9.1**, while `/1.7/` identified itself as **1.7.2**. Features
  appearing only in the former are not evidence of local API availability.
  [Current stable page](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html),
  [pinned-version page](https://scikit-learn.org/1.7/modules/generated/sklearn.model_selection.GroupKFold.html).
- Review used only vendor/library documentation and the authors' research
  paper. No user data was uploaded. Reading these sources does not introduce
  an online dependency into the application.

## 2. JMP Features Versus Product Policies

| Topic | Official-source finding | DataLab Studio baseline and extension boundary |
| --- | --- | --- |
| GP modeling | JMP describes regression of a continuous response on predictors using a spatial correlation model. [GP overview](https://www.jmp.com/support/help/en/19.2/jmp/gaussian-process.shtml) | Standalone numeric GPR already exists. BO owns a separate surrogate contract; sharing a statistical family does not make their defaults or artifacts interchangeable. |
| Noisy response | The JMP launch dialog documents nugget estimation for smoothing noisy responses. [Launch options](https://www.jmp.com/support/help/en/19.2/jmp/launch-the-gaussian-process-platform.shtml) | GPR already has estimated/fixed/near-noiseless observation-noise modes. The proposed BO extension adds its own noise policy and separates noise from numerical jitter. The terminology does not imply identical parameterization or fitted values. |
| Iterative optimization | JMP Pro fits a GP for each response, combines predictions, uncertainty and goals, selects a batch, then updates after actual experiments. [BO overview](https://www.jmp.com/support/help/en/19.2/jmp/bayesian-optimization.shtml) | The study/trial/observation loop already exists. This extension remains a **single-response** goal workflow. Recommended values and planning samples must never become actual observations. |
| Candidate set | JMP documents a uniformly sampled candidate set with factor ranges and supported constraints, manual row selection and automated augmentation. [Candidate Set](https://www.jmp.com/support/help/en/19.2/jmp/candidate-set.shtml) | The product uses bounded seeded search and executable constraints, not a claim to reproduce JMP's candidate set or row-selection implementation. Discrete assignment plus continuous local search is the proposed product policy. |
| Batch strategy | JMP documents MaxPro space filling, model refinement, and optimum-confirmation/challenge augmentation strategies. [Candidate Set](https://www.jmp.com/support/help/en/19.2/jmp/candidate-set.shtml) | The requested MC joint-latent marginal-improvement policy is different. A minimum-distance constraint is not MaxPro; greedy EI/ETI is not any of those strategies merely because it produces a batch. |
| Categorical GP | JMP documents level-pair correlation parameters for categorical predictors combined with continuous-predictor correlations. [Categorical model details](https://www.jmp.com/support/help/en/19.2/jmp/statistical-details-for-models-with-categorical-predictors.shtml) | The proposed equality/mismatch factor has one positive parameter per categorical predictor. It is a more restricted equal-correlation model, not JMP's level-pair model. Integer category codes carry no numeric distance. |
| Profiles and surfaces | JMP provides prediction, contour and surface profilers, and saving prediction/variance formulas. [GP options](https://www.jmp.com/support/help/en/19.2/jmp/gaussian-process-platform-options.shtml) | Numeric conditional profiles and selectable X/Y surfaces already exist. This extension concerns held values, numeric-axis eligibility, latent/predictive labels and exact saved-view ownership, not a new surface selector. It does not export JMP formula columns. |
| Large data | JMP describes Fast GASP as a block-based computational option. [Launch options](https://www.jmp.com/support/help/en/19.2/jmp/launch-the-gaussian-process-platform.shtml) | The proposed 2,000-row profile is still dense **Exact GP**, subject to resource preflight and measured budgets. It is not Fast GASP, sparse GP, a universal speed guarantee or a guarantee that every 2,000-row configuration is accepted. |
| Reproducibility | JMP distinguishes saving a response GP fit script from reproducing work in the Batch Selection tab. [Response GP model options](https://www.jmp.com/support/help/en/19.2/jmp/response-gaussian-process-model-options.shtml) | Immutable model/history/config hashes and stored recommendations are the product's own reproducibility boundary. Reopening an old recommendation must not rerun its acquisition under a new policy. |

JMP's Candidate Set page further distinguishes model-free exploration from
model-based refinement: its refinement begins with expected improvement and
then uses uncertainty-oriented criteria, while its confirmation strategy uses
desirability and candidate quality relative to training runs. This does not
establish that either strategy evaluates the conditional MC formula specified
for this product. [Candidate Set](https://www.jmp.com/support/help/en/19.2/jmp/candidate-set.shtml)

## 3. Source-Confirmed Baseline And Requested Extension

These are source observations, not browser or release validation results.

| Area | Baseline evidence | Requested extension status at research handoff |
| --- | --- | --- |
| BO single/batch | `bayesian_optimization.py` and `bayesian_batch.py` fit a constant-times-Matern signal with diagonal jitter. Product registry is method `0.6.0`. | Noise-aware common core and versioned readers require implementation/verification. |
| BO normalization | Both engines explicitly use `np.std(...)` with its default `ddof=0`. | Preserve raw-observation normalization, including under compression. |
| Single target UI | `useBayesianRecommendationState.ts` already sends `sequential_single` as a batch of one and chooses ETI for `match_target`. | Preserve this UI; reconcile the legacy single route without claiming a newly added target UI. |
| Batch planning | The baseline batch contract is `greedy_posterior_mean_fantasy_ei_v1`. | New joint-latent MC policy must be separately identified; legacy results remain unchanged. |
| Mixed search | Both engines disable local starts if any discrete factor is present. | Replace only the new-policy search with fixed discrete assignments and continuous refinement. |
| GPR noise | `gaussian_process_regression.py` already adds `WhiteKernel` in estimated-noise mode. | Do not add a second white-noise component. |
| GPR scaling/CV | Baseline predictor/response SD uses `ddof=1`; validation is row K-fold, LOO or none. | Group and time splits, scored coverage and lag lineage require complete calculation/manifest/UI verification. |
| GPR surface | `GaussianProcessCharts.tsx` already contains X/Y controls and a generated surface with client-row identity matching. | Extend held values and applied-view provenance while preserving those protections. |
| GPR predictors/size | Baseline contract is numeric-only, up to 12 predictors and 500 usable rows; LOO is capped at 200. | Mixed predictors and opt-in extended Exact GP remain pending until their full save/restore/predict/resource gates pass. |

## 4. Validation Purpose Is Not A JMP Equivalence Claim

Scikit-learn 1.7.2 GroupKFold keeps a group out of training whenever it is in
validation, and requires at least as many distinct groups as folds. Its group
shuffle/random-state API was introduced in 1.6 and exists in the pinned
version. A seed has no effect when group shuffling is disabled. The product
must retain the effective settings and exact split plan rather than merely
record a seed. [GroupKFold 1.7.2](https://scikit-learn.org/1.7/modules/generated/sklearn.model_selection.GroupKFold.html)

Scikit-learn TimeSeriesSplit expands training sets and measures `gap` in
samples. Its documentation requires equally spaced samples for equal-duration
fold comparisons. The requested product policy instead splits unique timestamp
**blocks** and measures its gap in those blocks. The adapter must preserve
same-time observations together and report actual durations for irregular
timestamps; passing raw rows directly to TimeSeriesSplit is insufficient.
[TimeSeriesSplit 1.7.2](https://scikit-learn.org/1.7/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)

Product interpretation:

- Row K-fold: prediction for exchangeable rows under the stated sampling design.
- Group K-fold: generalization to held-out groups/batches, not necessarily the
  next measurement within an already observed group.
- Time split: earlier data predict later observations. Initial training-only
  rows have no CV prediction and must not enter scored metrics.
- Lagged rolling one-step prediction: previous actual outcomes are available
  before the next prediction. This is not fixed-origin multi-step forecasting.
- No validation: no external performance estimate. CV used to select a kernel
  is a selection score, not an independent final test.

These are product evaluation contracts. The cited JMP pages do not establish
that their UI or algorithms implement these exact CV policies.

## 5. Noise And Acquisition Definitions

Scikit-learn permits scalar/per-observation `alpha` on the training covariance
diagonal, and estimates a global noise variance through `WhiteKernel` when
included in the kernel. The library also documents local optima and optimizer
restarts. Those facilities do not decide which predictive uncertainty an
acquisition should use. [GPR 1.7.2 guide](https://scikit-learn.org/1.7/modules/gaussian_process.html)

The extension's product definitions, not claims about JMP internals, are:

```text
training covariance = signal covariance + diag(measurement variance + jitter)
latent posterior covariance = K_f(query, query) - V.T @ V
future single-observation variance = latent variance + measurement variance
```

`V` solves the training Cholesky system using signal-only train/query cross
covariance. Future jitter is not physical measurement error. Independent
repeat measurements share latent covariance but not observation-error terms.

Directional EI uses the largest posterior latent mean at **completed observed
locations**, after the explicit maximize/minimize direction transformation.
Target EI fits the response itself and evaluates improvement in distance to
the scaled target. Observed best, latent incumbent and target tolerance are
distinct fields. This is posterior-mean plug-in EI/ETI, **not exact noisy EI or
qNEI**; baseline and hyperparameter uncertainty are not fully integrated.

Wilson, Hutter and Deisenroth describe Monte Carlo acquisition optimization,
joint Gaussian reparameterization and greedy incremental maximization. Their
paper motivates a family of methods; it does not validate this implementation,
its finite sample count, mixed local search, or JMP parity. The paper states a
noiseless-observation simplification in its exposition. No theoretical search
guarantee is transferred to a bounded finite-pool/local-solver implementation.
[Authors' paper, version 2](https://arxiv.org/html/1805.10196v2)

## 6. Independent Formula Sanity Checks

These checks were executed on Windows, Python 3.10.11, NumPy 2.2.6 and SciPy
1.15.3. They used inline independent Cholesky/quadrature code, **not product
calculation helpers**. They check the design mathematics; they do not replace
committed regression tests, API/browser tests or native release validation.

### Exact Replicate Compression

For independent repeated observations at identical locations, define
`v = noise_variance + jitter`, with the same `v` used on each raw diagonal.
For group sizes `n_i`, the group-mean covariance has diagonal addition `v/n_i`.
The exact raw-data log-density is:

```text
L_raw = L_means
        - 0.5 * sum((n_i - 1) * log(2*pi*v) + within_ss_i/v + log(n_i))
```

The `+log(n_i)` inside the subtracted correction is necessary. One derivation
uses an orthonormal group mean direction `sqrt(n_i)*mean_i` and its `n_i-1`
orthogonal residual directions. Switching from that mean direction to the
ordinary mean contributes `-0.5*log(n_i)` to the raw density.

With `noise = exp(eta)` and fixed jitter, the correction's derivative is:

```text
d(correction)/d eta = -0.5 * noise *
                     sum((n_i - 1)/v - within_ss_i/(v*v))
```

The multiplier is `noise`, not `v`: jitter is not optimized as measurement
variance. This correction must accompany the mean-model gradient. Dropping it
loses within-group information and changes the noise estimate.

Probe: unique X `[0, 0.7, 1.4]`, replicate counts `[3, 1, 2]`, raw Y
`[-0.2, 0.1, 0.5, 0.7, -1, 2]`, raw-Y `ddof=0` normalization, RBF signal
amplitude 1.3/length scale 0.6, noise 0.08, jitter `1e-6`, query X
`[0.2, 0.8, 1.1]`. Absolute tolerance was set to `1e-10` before execution.

| Quantity | Raw rows | Compressed means plus correction |
| --- | --- | --- |
| Raw N / effective training N | 6 / 6 | 6 / 3 |
| Log marginal likelihood | -38.133021493224284 | -38.13302149322419 |
| Derivative with respect to log noise | 33.63994556146067 | 33.6399455614605 |
| Maximum posterior-mean difference | Reference | `5.2735593669694936e-15` |
| Maximum latent-covariance difference | Reference | `2.220446049250313e-16` |

This equivalence assumes identical coordinates, the same fixed raw
normalization, a shared Gaussian error variance and independent errors. Nearby
coordinates, differing process states and correlated repeats do not inherit
this identity. Compression never changes the future single-measurement noise
to `noise/n_i`; only an explicitly requested future mean of `m` independent
measurements would use `noise/m`.

### Conditional Marginal Improvement

For an already selected set `S`, sample its **joint latent** posterior. Given
one such sample, integrate the new point conditionally. Directional
incremental utility is `max(f_x - max(b + xi, max(f_S)), 0)`. Consequently the
conditional EI helper receives this threshold and `xi=0`, avoiding a second
subtraction. For target improvement the remaining radius is
`min(d_latent - xi, min(abs(f_S - target)))`; a nonpositive radius yields zero.
The ETI helper also receives no additional `xi` subtraction.

Probe: joint mean `[0.15, 0.42]`, covariance `[[0.25, 0.18], [0.18, 0.49]]`,
`b=0.3`, `xi=0.07`, target `0.1`, initial target distance `0.6`. Numerical
quadrature integrated the raw joint payoff increment separately from the
analytic conditional EI/ETI expression. Integrals were split at payoff kinks,
with normal tails truncated at ten SD and acceptance tolerance `1e-9`.

| Marginal utility | Conditional analytic expression integrated over selected point | Direct joint-payoff increment integration |
| --- | --- | --- |
| Directional improvement | 0.22930799019657622 | 0.22930799019657616 |
| Target improvement | 0.06156206274271663 | 0.06156206274271664 |

This is a deterministic formula check, not a 64-sample MC performance result.
Implementation still needs joint-covariance, common-random-number, seed,
degeneracy, budget and q=1 analytic-parity tests. The baseline ETI helper accepts
a scalar distance; per-sample radii need explicit handling rather than an
accidental scalar comparison against an array.

## 7. Explicit Non-Claims And Remaining Gates

- No actual JMP output comparison, certification or guarantee of identical
  hyperparameters, uncertainty, acquisition values or recommended coordinates.
- No multi-response Bayesian desirability, MaxPro equivalence or implemented
  JMP augmentation strategy is claimed.
- No automatic nearby-observation averaging, response fabrication or history
  rewrite. Replicate entry is a separate lifecycle feature requiring storage
  and idempotency verification.
- No Fast GASP, sparse/variational GP, state-space GP, ARIMA or recursive
  multi-step uncertainty propagation.
- No guarantee that a batch is well separated without an explicit feasible
  distance condition, or that an observed target hit should terminate a study.
- No claim that increasing the Exact GP row cap makes all configurations fast
  or memory-safe. Native measurements and hard-timeout cleanup are separate
  release gates.
- All extension features marked pending above require calculation, API,
  persistence, browser and exact-archive evidence before becoming release
  claims. The formula probes in this document establish none of those gates.

## 8. Subsequent Implementation Evidence

The BO implementation now has the product-specific common surrogate, EI/ETI, correlated conditional
MC acquisition, exact-replicate view and mixed search described above. The new BO policy is method
`0.7.0`, with schema-dispatched legacy readers. The focused numerical run passed 127 committed tests,
including independent Cholesky, finite-difference, quadrature, joint-sampling and known mixed-search
fixtures. This supersedes the *BO implementation pending* entries in the historical handoff table,
but does not turn them into native browser, archive or JMP comparison evidence.

The frontend retains its original q=1 target route and selectable surface workflow. BO noise,
aggregation, MC and explicit-replicate controls are connected to typed schema-2 requests; the
observed/latent/predictive/planning distinctions are visible. Focused static/hook evidence is in
[`bo_frontend_noise_evidence.md`](bo_frontend_noise_evidence.md). The separate reliability audit
records the reproduced minimize-normalization and replicate-replay defects and their fixes in
[`bo_noise_audit_evidence.md`](bo_noise_audit_evidence.md).

The mixed-category preprocessing/kernel layer has independent PSD, analytic-gradient, identity and
safe-payload tests, recorded in [`gp_mixed_kernel_evidence.md`](gp_mixed_kernel_evidence.md).
Those layer tests alone do not establish complete GPR save/restore, CV, surface or resource-profile
coverage. The integrated GPR and release status belongs in
[`bo_gpr_noise_validation_extension.md`](bo_gpr_noise_validation_extension.md), not in the historical
research checklist. No actual JMP output was obtained during these implementation checks.
