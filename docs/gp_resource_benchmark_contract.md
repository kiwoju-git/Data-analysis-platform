# Exact GP Resource Benchmark Evidence

`scripts/benchmark_gp_resources.py` measures synthetic API execution, saved-result
restoration and restored-model prediction. Its default matrix has 36 cases:
501/1000/2000 rows, numeric/mixed predictors, single/compare kernels, and
row/group/time validation. The fixture uses fixed noise SD 0.03, zero optimizer
restarts, three folds, two comparison kernels, no retained candidate details,
and profile/grid size 10. These measurements do not establish the performance
of every allowed noise, restart, predictor, category or validation setting.

## Source Identity

Evidence schema 2 records source identity before and after the matrix and each
child case. Identity includes HEAD, a SHA-256 over sorted tracked paths and their
actual file bytes, and a Git status digest. File contents, not mtime, determine
the tracked-tree digest. Per-case identities must match the matrix start.

By default the benchmark refuses a dirty checkout before fitting. The explicit
`--allow-dirty-source` option permits diagnostic measurements only. Such a run
returns a nonzero exit status even when its measured cases succeed.

- `verified_clean_unchanged`: clean, identical start/end and case source.
- `diagnostic_dirty_source`: stable but dirty source, not release evidence.
- `invalid_source_changed`: a commit, tracked file, status or case source changed.

For the latter two states, `source_commit` is null. Start/end identities remain
available for diagnosis; the ending SHA is never substituted for the measured
source. Measurements and failures remain in the report without being relabeled.
Source validity is necessary but does not override any failed measured case.

The checks detect observed source differences, not adversarial changes restored
between every observation. Final measurements must run in a dedicated clean
checkout without an editor or concurrent source updates.

## Memory And Timeout Scope

The 512 MiB admission policy is an estimate, not an OS-enforced resident-memory
limit. It includes parameter-dependent kernel/gradient workspaces, retained
state, transfer allowance and chunked predictions. This is task working-memory
admission, not a claim that combined parent/worker RSS stays below 512 MiB.
The parent application's interpreter, imports and existing service baseline
are not included in the fixed worker-process allowance.

`exact_gp_peak_v2` uses a 160 MiB worker-process allowance. The source-identified
Linux job 119267054835 measured up to 174.77 MiB worker RSS at 501 rows, 248.84 MiB
at 1000 rows and 510.34 MiB at 2000 rows. The maximum small-N excess above the
modeled variable terms was approximately 149 MiB; the allowance rounds this up
to the next 32 MiB increment. It is a conservative calibration from these cases,
not a measured universal import footprint or an all-platform memory guarantee.

Let M = 8 N squared bytes. The estimate includes:

- fit phase: `M * (5 + 3 * largest kernel parameter count)`;
- retained candidate state: `M * retained candidate count`;
- comparison allocator reserve: one additional M when comparing kernels;
- prediction workspace: `8 * N * min(query count, 256) * 3`;
- result storage: `128 * query count + 1024 * N * candidate count`;
- transfer phase: final Cholesky M plus a two-M transfer/receiver allowance and
  `8 * N * 64` for smaller state arrays.

The process allowance, retained state, result and prediction allocations are
conservatively retained in both phase estimates. The final estimate is the
maximum of fit and transfer phases: sklearn gradient/inverse temporaries are
released before the worker serializes its final state, so those large buffers
are not summed with the later NPZ/receiver buffers. The transfer allowance does
include copies crossing the worker/parent boundary, not the parent process's
whole baseline. Prediction query count includes all training fitted diagnostics
as well as profiles/surface; small displayed profiles no longer undercount the
256-query prediction chunk actually used by a large training set.

At 2000 rows, a numeric two-parameter single-kernel request can pass this estimate;
the benchmark's mixed three-parameter and two-kernel comparison requests fail
admission without reducing their requested options. Native execution and timing
are still required for admitted settings. No claim covers all 2000-row options.

Worker RSS is sampled after result JSON/NPZ serialization and validated through
the small IPC receipt. Parent and worker peaks are separate process high-water
marks, not a simultaneous combined peak. The model's timeout is enforced by
terminating its owned worker; unrelated processes and completed source files
are not cleanup targets. An admission rejection is not a successful fitted
model, and a timeout is not a passing performance measurement.

The benchmark supervisor retains the unchanged 240-second per-case deadline.
It creates an owned process group and terminates that case's process tree on
deadline, not processes found by name. Progress JSON records the last synthetic
API stage, and a 210-second faulthandler dump provides the stuck case's stacks.
A timed-out/failed child leaves a partial aggregate, synthetic-only failure log,
failed case and explicit not-run count; it never disappears as an absent artifact.
Source paths in this diagnostic stack are benchmark checkout paths, not user
workspace data. Native Windows job 119267055594 stopped at its 1000-row numeric
compare/row-CV case under the old supervisor without a partial aggregate. The
stage is unknown, and that timeout has not been relabeled as a fit defect or pass.

## Diagnostic Run: 2026-10-21

The local Windows/CPython 3.10 run named `gp-resources-windows.json` began on dirty
source based on `3284a359c31ccfb738ddf16078440f674d52f42f`. Source files changed and
were committed while its cases were running. The previous script recorded only
ending HEAD `1c178d33444d185625418f5bb71270d39d1aa1df`; that SHA does **not** identify
all code measured by this run. The original evidence bytes were retained,
SHA-256 `e64feef5a1ec8458b4a3f5341f456cad055ad5f5ae8e305a4d6b025ae02621ce`.

Its 36 recorded cases contain 28 passes, two 180-second time-budget failures
(2000-row numeric single-kernel row/group CV), and six memory-admission
rejections (2000-row mixed predictors). These counts are diagnostic observations,
not verification of the ending commit or a release. No timeout was removed or
converted to success, and the time/memory budgets were not increased to pass it.

The successful cases also expose a calibration limitation: 501-row estimates
were about 90-96 MiB while worker RSS peaks were about 138-146 MiB; 1000-row
estimates were about 165-189 MiB versus 190-209 MiB measured. Successful 2000-row
numeric estimates were about 464-466 MiB versus 398-399 MiB measured. Small-N
import overhead and the conservative N-squared terms have different effects.
Because the source and measurement implementation changed during the run,
these numbers do not justify weakening admission, claiming a total RSS bound,
or replacing a clean native-target rerun.

## Clean Linux Rerun

Run39619608275 / job119289234806 used source
`6fe0b509a726a43be340450b4f0faf47a3ec5927` on Ubuntu24.04 / Python3.12.
Evidence schema2 confirms a clean, unchanged tracked tree before/after all36
cases and each child case. Artifact12354198062 has ZIP SHA-256
`40b71decf33d9c66313611e52bd31ab33b37e35099d07af8c7a70ab198f72e08`.

| Rows | Fit/restore/predict passes | Admission rejections | Maximum worker RSS MiB | Maximum parent RSS MiB | Maximum analysis request seconds |
| --- | --- | --- | --- | --- | --- |
| 501 | 12 | 0 | 179.180 | 192.176 | 2.376 |
| 1000 | 12 | 0 | 263.301 | 203.652 | 6.523 |
| 2000 | 3 | 9 | 507.898 | 243.090 | 13.414 |

The2000-row passes are numeric single-kernel row/group/time CV. Comparison and
mixed settings were explicitly rejected, not silently simplified. All accepted
cases restored their saved result and model, kept the original result checksum,
and matched a stored fitted prediction within1e-9 absolute tolerance (largest
observed difference6.776e-10). These are the specified synthetic configurations,
not arbitrary application workloads or a Windows performance result. RSS peaks
remain separate process high-water marks, not simultaneous combined memory.
The full product, Windows resource and exact-archive gates are separate.
