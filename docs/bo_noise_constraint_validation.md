# BO V2 Constrained Workflow Validation Correction

## Reproduced Failure

Native workflow job `119305400828` in CI run `39624250223`, source
`bb94ab48125b6edbd49a5cc805131a01b13ec54e`, reached the actual BO form and
received HTTP 409 / `bayesian_optimization_artifact_mismatch` when requesting
a schema-2 single recommendation. This is a product validation defect, not
a browser timeout or an unsupported feature.

The synthetic reproduction uses the same configuration: one factor `x` in
`[-1,1]`, actual constraint `x <= 0.75`, uniform-feasible initial seed 20260715,
two initial trials, observations `[0.8,1.0]`, estimated observation noise, and
the existing UI's q1/EI/search settings. No user workspace or data is involved.

Two consecutive defects were reproduced:

1. `validate_calculation` compared the core's latent-incumbent normalized
   coordinate with the historical trial's supplied normalized coordinate.
   The core correctly trains using the observation view's canonical
   actual-to-normalized coordinate. A previous normalized-to-actual round trip
   is not necessarily bit-identical: the fixture's stored value is
   `0.10821039897810224`, while its canonical value is
   `0.10821039897810225`. The difference is exactly one ULP
   (`1.3877787807814457e-17`). The original direct validator test failed at
   the incumbent block with the same stable error.
2. After correcting that comparison boundary, the same fixture failed with
   `KeyError: coefficients`. Public worker constraints use a typed `terms`
   list; the validator incorrectly read the calculation engine's internal
   `coefficients` mapping. Empty-constraint fixtures had not reached this path.

## Minimal Correction

Only `backend/app/services/bayesian_noise_recommendations.py:validate_calculation`
changes product behavior:

- Resolve the incumbent trial ID in the already-validated observation view and
  compare against that row of `view.raw_x` **exactly**. No tolerance is widened.
- Evaluate actual constraints from the public payload's `terms` list, using
  the original relation, bound, and existing numerical bound tolerance.

GP fitting, latent means, acquisition, target handling, candidate search,
selection, stored coordinates, history, and result hashes are not recalculated
or rewritten by this correction. The prior suspected raw/scaled-mean tie-break
issue was not the cause of this native failure. There is no result schema,
method version, or metadata schema change for this validation fix.

## Regression Boundary

`backend/tests/unit/test_bayesian_noise_constraint_api.py` creates the synthetic
study through the real API, records both actual observations, invokes the real
core and spawn-worker API, and verifies:

- The one-ULP historical/canonical round-trip difference is present.
- The legitimate canonical incumbent is accepted, while a forged one-ULP
  change to the canonical result is still rejected.
- An internally consistent candidate outside the actual upper constraint is
  rejected; the lower-constraint direction is also enforced.
- A forged worker result returns 409 without inserting a batch or pending trial.
- Legitimate creation returns 201, and stored batch/study reads return 200.
- Original trial records and observation-history bytes remain unchanged.
- Managed report source restoration retains exact batch/result hashes and
  cannot call the recommendation engine again.

The first direct reproduction failed with the incumbent error. The next run,
after only the canonical-coordinate correction, failed with the constraint
`KeyError`. Both failures are retained here; neither was treated as an
unrelated timeout or hidden by a retry.

The local host is Windows 10 build 19045 / Python 3.10.11. Native browser and
final archive results are separate gates; a local TestClient pass does not
establish that the original browser workflow or an uploaded archive passed.

## Executed Checks

From the repository root, with this worktree's `backend` on `PYTHONPATH` and
OMP/OpenBLAS/MKL threads capped at one:

- `pytest backend/tests/unit/test_bayesian_noise_constraint_api.py backend/tests/unit/test_bayesian_noise_api.py backend/tests/unit/test_bo_versioned_wrappers.py -q`:
  **31 passed**, three dependency deprecation warnings, 197.69 seconds.
- Ruff check and format check for the changed service and new regression test:
  passed; both files already formatted.
- The repository-standard `mypy backend/app`: **success, 235 source files**.

A separate backend-directory single-file strict mypy probe reported three
errors on unchanged lines of this service (unreachable `or` operands at lines
81/159 and an Any return at line 758). Those same lines were present in the
earlier `bb94ab4` commit of this task; they are not described as warnings from
the original main baseline. That probe is distinct from the root-directory
command used by `scripts/check.ps1` and `scripts/check.sh`, which passed.
No unrelated typing refactor is included in this narrowly scoped correction.
