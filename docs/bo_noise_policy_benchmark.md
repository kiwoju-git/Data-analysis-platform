# BO V2 Synthetic Characterization

## Scope And Provenance

This adds validation for `greedy_mc_joint_latent_improvement_v2`, not a claim
that the new policy beats legacy EI, qNEI, JMP, random search, or every noisy
objective. The production calculation is unchanged. The historical Branin
reference remains a **legacy single-policy** regression and is not reused as
evidence for V2 batch quality.

The declared fixture is
`backend/tests/reference/fixtures/bo_noise_policy_reference.json`; executable
checks are in `backend/tests/reference/test_bo_noise_policy_reference.py`.
The local measurement used production source at
`16fbaf3447622c4ab1f2ae602000aab7107038ac` with the new test/fixture uncommitted.
It is source-level evidence, not final-archive or native Linux evidence.

Local environment: Windows 10 build 19045, CPython 3.10.11, NumPy 2.2.6,
SciPy 1.15.3, scikit-learn 1.7.2, CPU only. OMP/OpenBLAS/MKL thread counts
were explicitly set to 1. Do not describe this host as a Windows 11 device.

## Joint MC Stability

A hand-declared two-location posterior has mean `[0.15, 0.42]` and covariance
`[[0.25, 0.18], [0.18, 0.49]]`. The reference independently draws 1,048,576
correlated two-dimensional normals with seed 73519, in bounded chunks, and
evaluates the **joint marginal payoff directly**. It does not call production
EI, ETI, or conditional acquisition helpers. Independent quadrature also
checks the reference; target integration evaluates the triangular payoff.

The production planner is then evaluated at 16/32/64/128/256 samples over
32 predeclared root seeds (101 through 132). The gates require the independent
MC reference to agree with quadrature within six estimated standard errors,
and the 256-sample aggregate RMS error to be at most 0.6 times the 16-sample
RMS error. They do not require each seed or each sample-count transition to
improve monotonically.

| Goal | Independent MC mean | MC standard error | Independent quadrature |
| --- | ---: | ---: | ---: |
| Maximize | 0.229103216997 | 0.000344836384 | 0.229307990200 |
| Match target | 0.061546581264 | 0.000119627786 | 0.061562062765 |

| Samples | Directional RMS error | Target RMS error |
| ---: | ---: | ---: |
| 16 | 0.02331232596 | 0.01231481903 |
| 32 | 0.01463288379 | 0.00921974490 |
| 64 | 0.00948909590 | 0.00621992470 |
| 128 | 0.00642449758 | 0.00482199852 |
| 256 | 0.00698038429 | 0.00400901764 |

The directional aggregate error increased from 128 to 256 samples in this
finite seed set. Individual absolute errors increased at 42 directional and
48 target seed/count transitions. Both observations are preserved, not hidden
behind a monotone convergence assertion. This is finite-sample stability
evidence for this posterior, not universal convergence-rate certification.

## Actual Noisy Sequential Batches

Every recommendation calls `calculate_noise_aware_batch`, with estimated
observation noise, retained raw observations, and the production mixed search.
No posterior or suggested coordinates are mocked in this characterization.

- Latent response: `2 - 4*(x-0.68)^2 - 0.2*(d-1)^2`.
- `d` is discrete in `{0,1,2}`; `x` is continuous in `[0,1]`.
- Actual-unit constraint: `x + 0.1*d <= 0.95`.
- The feasible known maximum is 2 at `(d=1,x=0.68)`.
- Target mode requests response 1.2; a feasible exact root is checked separately.
- Actual observations add seeded independent Gaussian noise with SD 0.04.
- Five fixed initial conditions; three q=2 batches; eleven actual trials total.
- Three root seeds: 7, 19, 43. Every batch uses 64 posterior samples and is
  replayed with identical input. All returned item payloads must match exactly
  within the same runtime, and input snapshots must remain unchanged.
- Per-batch search: 64 seed candidates per step, three local starts per step,
  30 local iterations, 4,096 acquisition work units, zero hyperparameter
  restarts, 50 model iterations/200 model evaluations, 30-second deadline.

Each recommended point is checked against actual bounds, discrete levels,
the actual-unit constraint, normalized-coordinate correspondence, novelty,
and the q1-analytic/q2-MC distinction. Reported uncertainty must remain the
completed-observation base posterior. Synthetic measurements, never predicted
means or fantasy values, are appended before the next fit.

Regret is computed from the independent latent formula, not from the largest
noisy observation: `2-best_latent_value` for maximize and
`min(abs(latent_value-1.2))` for target. Best observed values/distances are
recorded separately in the emitted measurement JSON.

| Goal | Seed | Initial oracle regret | After batch 1 | After batch 2 | After batch 3 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Maximize | 7 | 0.2036 | 0.2036 | 0.00204541904 | 0.00204541904 |
| Maximize | 19 | 0.2036 | 0.2036 | 0.20027888929 | 0.20027888929 |
| Maximize | 43 | 0.2036 | 0.2036 | 0.20144627524 | 0.20024377442 |
| Match target | 7 | 0.3236 | 0.03312599245 | 0.00830384502 | 0.00039698445 |
| Match target | 19 | 0.3236 | 0.02522918065 | 0.00072886196 | 0.00072886196 |
| Match target | 43 | 0.3236 | 0.01166303477 | 0.01166303477 | 0.01166303477 |

All 36 recommended points across the six trajectories met the constraint.
The 18 batch calls were each replayed; no replay differences were observed.
Acquisition work per batch ranged from 131 to 221 units, within the fixed
4,096-unit budget. These are calculation tests, not API/UI/archive execution.

## Failure Record And Acceptance Boundary

The first test run had two fixture errors: it supplied an internal constraint
`coefficients` mapping instead of the public worker payload's `terms` list.
Only the fixture was corrected; this was not a production defect.

The first complete calculation run deliberately tested an exploratory
"median regret halves after three batches" condition. **Maximize failed**:
median regret was `0.2002437744180574`, versus initial `0.2036` and threshold
`0.1018`. Target passed that exploratory threshold. The same failure repeated
when collecting the full maximize trace. Seeds 19/43 showed only small
maximize gains, and several complete batches made no oracle improvement.

That arbitrary 50% requirement was not part of the user contract and is not a
release gate. It remains in the fixture and emitted evidence as a diagnostic
criterion, including a false result for maximize. The final gates retain
mathematical correctness, finite regret, cumulative-history consistency,
constraints, discrete executability, source immutability, and exact seeded
replay. No budget, noise, tolerance, seed, initial design, or production
algorithm was changed to make the exploratory criterion pass.

This does **not** establish that V2 reliably finds the global optimum within
eleven trials. The fixed three-seed toy is a bounded characterization, not a
statistical efficacy trial or superiority benchmark. A larger objective/noise
suite and comparisons against other policies remain separate future evidence.

## Reproduction

From a configured checkout in PowerShell:

```powershell
$env:PYTHONPATH = (Resolve-Path .\backend).Path
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -m pytest .\backend\tests\reference\test_bo_noise_policy_reference.py -q -s
```

The file belongs to the existing `backend/tests/reference` collection, so
normal Windows/Linux backend checks execute it without a separate opt-in job.
`-s` additionally emits the complete aggregate and per-seed measurement JSON.
The local final run passed all five new checks in 20.60 seconds. The combined
new reference, batch-acquisition, recommendation-core, and mixed-search suite
passed 50 checks in 24.95 seconds. Ruff check and format-check passed for the
new test file. These timings are test-run elapsed time, not isolated optimizer
latency measurements.
Final native CI and exact Linux archive status must be reported separately;
this local source characterization does not substitute for either gate.
