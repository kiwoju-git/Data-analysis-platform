# Linux Numerical Reference Validation

## Scope And Evidence

This is a test-only compatibility policy. Production GPR, Bayesian calculations,
hyperparameters, tolerances, stored results and the original Windows static
`backend/tests/reference/fixtures/gp_kernel_comparison_reference.json` are not
changed. The full application acceptance gate is separate from the numerical
probe's successful collection status.

Independent evidence was collected by GitHub Actions run
[37714256390](https://github.com/kiwoju-git/Data-analysis-platform/actions/runs/37714256390)
from source `acb6256f838a038f5ba140cc7d9d86acfdddcf56` on actual
`ubuntu-24.04` x86_64 runners. NumPy 2.2.6, SciPy 1.15.3 and scikit-learn 1.7.2
were unchanged. NumPy/SciPy OpenBLAS versions were 0.3.29/0.3.28, with one CPU
thread. Python and BLAS CPU dispatch differed between runners:

| Probe | Python | OpenBLAS architecture | Smooth RBF CV NLPD |
| --- | --- | --- | --- |
| Original Windows static fixture | 3.10 baseline | See original validation | -0.6364381799523708 |
| Linux probe 3.11 | 3.11.16 | Haswell | -0.6364421136365866 |
| Linux probe 3.12 | 3.12.15 | SkylakeX | -0.6365775817441547 |

These differences are observed environment effects, not proof that Python
version or CPU dispatch alone caused them. All four cases' input x/y arrays
were exactly equal to the committed fixture in both probes. Selected kernels
and stored fold indices were unchanged. Each runner's production metrics,
LML and OOF means/SD agreed with its **independently fitted sklearn reference**
within the existing `1e-6` comparison tolerances. Against the Windows static
fixture, only the smooth RBF NLPD exceeded the existing tolerance in these
probes; other assertions passed. The 3.12 probe's maximum OOF mean/SD changes
relative to Windows were approximately `7.93e-7` / `3.77e-7`, illustrating the
sensitivity of density scores to small changes in low predictive uncertainty.

Evidence artifacts include the static independent reference JSON, comparison
JSON, input equality, source hashes, native library metadata, Bayesian
lifecycle diagnostics and the explicit `diagnostics_collected_not_acceptance`
summary. Artifact ZIP digests were verified before safe extraction:

| Artifact | GitHub artifact ID | ZIP SHA-256 |
| --- | --- | --- |
| numerical-probe-py311 | 11523207079 | `3e72aa806ef2aa007fa97e8123e09f3d915683edf4637f66b0adf4d38987376f` |
| numerical-probe-py312 | 11523062044 | `e62f9c3b8d29924e403888cdf69db9f31c28487544b3833411ba4632a64295f1` |

The downloadable static snapshots are audit evidence, not portable golden
values silently substituted for the original Windows reference. They remain
in CI artifacts and the local ignored diagnostic directory. Artifact retention
is finite; durable release evidence should preserve these files with their
provenance. Generated workspaces, database files and credentials are excluded.

## Independent Cross-Check

Windows retains its static comparison path. Linux uses `evaluate_frozen_case`
from the independent reference script only for optimized-kernel expected
metrics, LML and OOF predictions. It receives the committed x/y, seed and
validation indices, constructs training complements in saved row order,
validates an exact fold partition, and never generates replacement samples or
new CV splits. Each fold fits its own ddof=1 predictor/response normalization.
The reference uses sklearn's own optimizer and prediction implementation;
no production kernel, fitting, prediction, parsing or metric helper supplies
expected values. Production calculation supplies only the actual result.

This explicitly supersedes the script's former blanket
"no test-time generation" description for Linux optimized-kernel comparisons.
It does **not** change the following protections:

- Windows static fixture bytes and all existing numerical tolerances.
- Static selected presets and exact validation row indices on every platform.
- Static fixed-hyperparameter posterior reference checks on every platform.
- Legacy result/model tests and independent Bayesian numerical fixtures.
- Failure of the gate when independent same-platform values disagree.

This is neither a test skip nor a claim of bitwise cross-platform optimization
parity. Narrow helper tests prohibit application imports, input regeneration,
new fold generation, mutation of frozen inputs, duplicate/missing rows and
changed seed mapping. Static evidence and independent refits complement one
another; neither production-generated expected values nor wider tolerances
are permitted.

## Bayesian Lifecycle Budget

The 21-record recommendation test validates pagination, latest-record identity,
immutable pending snapshots and completed current trial state. It is not a
numerical reference or a promise to finish a GP fit within 100 evaluations.

In the Haswell/Python 3.11 probe, a request budget of 100 stopped at recommendation
8 (seed 107, nine completed observations), after seven recommendations had
been saved. The unchanged production code correctly reported
`bayesian_optimization_budget_exhausted`. With only the test request budget
increased to 200, all 21 records and lifecycle assertions succeeded; the
largest actual fit count was 106. The SkylakeX/Python 3.12 probe completed both
budgets with a maximum of 76 evaluations. Local Windows 10/Python 3.10.11
completed both with a maximum of 73.

Only this 21-record test now requests 200 model evaluations. The shared test
helper's default remains 100. Production defaults, optimizer, acquisition,
seeds, kernel, search/iteration/time limits and budget-exhaustion unit tests
are unchanged. This does not guarantee that every future numerical environment
can complete the same optimization within 200 evaluations.

## Local Test Check

After implementing this test policy, the following command passed **57 tests**
on Windows 10 build 19045, CPython 3.10.11:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_gp_independent_reference_policy.py backend/tests/unit/test_gaussian_process_kernel_selection.py backend/tests/unit/test_gaussian_process_regression.py backend/tests/unit/test_bayesian_recommendations_api.py
```

This includes the unchanged static Windows/GPML posterior path, existing
kernel/noise checks, new frozen-reference contract tests, the 21-record
lifecycle and existing Bayesian error/budget tests. It does not itself count
as an execution of the updated tests on Linux; that requires the subsequent
Ubuntu CI gate. The Linux probe evidence above predates this test-policy edit.
