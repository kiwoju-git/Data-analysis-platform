# Standalone GPR optimizer and length-scale contract

## Scope and sources

Only `regression.gaussian_process` changes. Bayesian Optimization is separate.
The installed implementation already uses SciPy L-BFGS-B, not ADAM.

Reviewed official sources:
- [scikit-learn 1.7 GPR API](https://scikit-learn.org/1.7/modules/generated/sklearn.gaussian_process.GaussianProcessRegressor.html)
- [SciPy 1.15.3 BFGS](https://docs.scipy.org/doc/scipy-1.15.3/reference/optimize.minimize-bfgs.html)
- [StandardScaler](https://scikit-learn.org/1.7/modules/generated/sklearn.preprocessing.StandardScaler.html)

The callable optimizer receives log hyperparameters and log bounds. StandardScaler
uses population SD; Statistical Twin deliberately retains sample SD (`ddof=1`).
Independent comparisons must match preprocessing rather than silently change it.

## Length scale

New scaled-X UI drafts propose lower=0.5, initial=1, upper=100. This is in training
sample-SD coordinates, so 0.5 corresponds to half that predictor's training SD.
It can suppress fast variation as well as noise. No universal improvement claim.
The compatibility preset is 0.01, 1, 100. Omitted settings in legacy requests use
that compatibility preset. Explicit settings carry their coordinate system.
Raw-X settings use original variable units; switching scaling requires explicit
confirmation/reset, and the backend rejects coordinate mismatch.

One common positive finite initial/lower/upper applies to every ARD length scale;
RationalQuadratic remains scalar. Require lower < upper and initial in range.
No per-predictor or physical-to-standardized bound conversion is introduced.

## Optimization

Default L-BFGS-B keeps its existing SciPy defaults and analytic-gradient path.
BFGS uses theta=a+(b-a)*sigmoid(z), and multiplies the theta gradient by
(b-a)*sigmoid(z)*(1-sigmoid(z)). All free kernel parameters use this transform,
not only lengths. Fixed parameters are absent from sklearn's theta vector.
BFGS initial theta must be strictly interior: boundary initial values are rejected,
not clipped. Random restarts follow the existing seeded sklearn initialization.

Record method, actual SciPy options, initial/final theta, bounds, success/status,
iterations/evaluations, objective, gradient norms and bound proximity per start.
For BFGS use gtol=1e-5 (transformed gradient); additionally report the original
projected-gradient check so sigmoid saturation cannot silently imply convergence.
Finite nonconverged fits remain usable with an explicit convergence warning;
nonfinite fits and deadline expiry fail. Never fall back to another optimizer.

## Reproducibility checklist

Compare rows/exclusions, predictor order, X/Y means and sample SDs, kernel/ARD,
amplitude/length/noise initial values and bounds, fixed noise SD versus variance,
jitter, optimizer/options/restarts/seeds/status, actual CV indices and fold-local
scales, training versus OOF predictions, latent versus observation variance, and
NumPy/SciPy/sklearn versions. Persist applied settings and optimizer evidence.

Reference tolerances fixed before implementation: fixed posterior mean/SD 1e-9
absolute/relative; same L-BFGS-B setup 1e-7; finite-difference transformed gradient
1e-5 relative / 1e-6 absolute; deterministic CV 1e-7. Different optimizers need
not select the same local optimum. Artifact predictions must agree to 1e-10.

## Compatibility

Implemented versions: method 0.3.0, result 3, GP manifest 3, API 21; metadata remains
20. Readers retain result/manifest 1 and 2. New records include applied settings;
old models are predicted from their original safe JSON/NPZ state without refitting.
HTML uses saved values and metadata. Existing checksums are never rewritten.

## Synthetic Sensitivity Evidence

Executed `scripts/benchmark_gpr_length_bounds.py`, CPython 3.10.11,
NumPy 2.2.6/SciPy 1.15.3/sklearn 1.7.2, CPU thread limit 1. N=50,
seed 872, RBF, estimated noise, X/Y sample-SD scaling, five shared folds,
zero final/CV restarts, initial 1, upper 100, L-BFGS-B. Concurrent tests and cold
imports mean elapsed times are descriptive, not a performance comparison.

| Synthetic case | Lower | Train RMSE | CV RMSE | NLPD | Coverage | Mean width | Seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Smooth + noise | .01 | .173793 | .198682 | -.128145 | .90 | .772914 | 1.890 |
| Smooth + noise | .5 | .173793 | .198682 | -.128145 | .90 | .772914 | .375 |
| Smooth + noise | 1 | .175661 | .197274 | -.147597 | .90 | .777729 | .282 |
| Rapid + noise | .01 | .084364 | .303559 | -.062996 | .96 | 1.083702 | .375 |
| Rapid + noise | .5 | .705308 | .731015 | 1.121353 | 1.00 | 2.753994 | .359 |
| Rapid + noise | 1 | .705308 | .730855 | 1.121105 | 1.00 | 2.754181 | .328 |
| Three predictors | .01 | .124716 | .237193 | -.081072 | .88 | .738299 | .391 |
| Three predictors | .5 | .124717 | .237193 | -.081072 | .88 | .738299 | .469 |
| Three predictors | 1 | .124717 | .237193 | -.081072 | .88 | .738299 | .343 |

The rapid case disproves universal improvement. Bounds change model assumptions,
not just numerical stability. No user Python code/comparison data was supplied;
their discrepancy remains unverified. Independent sklearn tests match fixed
posterior, L-BFGS-B and fold-local CV without using production fitting helpers
for expected values. BFGS transform gradients are finite-difference tested.
