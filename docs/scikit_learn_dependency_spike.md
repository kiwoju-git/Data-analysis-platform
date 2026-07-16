# Scikit-learn Dependency Spike

Last updated: 2026-07-15

## Decision

Status: **technical candidate approved and production-pinned; Windows 11
release validation pending**.

The isolated candidate passed wheel-only installation, `pip check`, offline
installation/runtime, CPU/thread limits, package import, and deterministic
Gaussian Process smoke checks on the measured host. The host identifies as
`Windows 10 Home build 19045`, not Windows 11. On 2026-07-15 the product owner
explicitly changed the policy: an actual Windows 11 x64 workstation run is a
mandatory release gate rather than a dependency-development gate.

The follow-up dependency-promotion slice pins `scikit-learn==1.7.2` in
`backend/pyproject.toml` and commits a wheel-only SHA-256 lock for CPython 3.10
Windows AMD64. It does not add a surrogate, Expected Improvement,
recommendation, objective execution, or Bayesian method result.

## Production Lock Decision

- `backend/requirements-py310-win.in` records the exact project inputs plus
  the reviewed `joblib==1.5.2` and `threadpoolctl==3.6.0` resolver constraints.
- `backend/requirements-py310-win.lock` records 45 exact wheel versions and
  one SHA-256 per wheel. URLs, editable entries, source archives, unpinned
  requirements, and missing reviewed packages are rejected.
- `scripts/generate-python-lock.ps1` targets only CPython 3.10/Windows AMD64
  wheels and keeps its wheelhouse outside the repository.
- `scripts/bootstrap.ps1` consumes the lock with `--require-hashes` and
  `--only-binary=:all:`, then installs the backend with `--no-deps
  --no-build-isolation` and runs `pip check`.
- A fresh external TEMP venv installed the lock with `--no-index`, built the
  editable backend, passed `pip check`, imported the exact five scientific
  versions, and imported `app.main` with `sklearn_loaded=False`.

The schema-2 evidence field
`candidate_approved_for_future_pin=false` remains an honest record of the
original strict Windows 11 environment rule. It is not rewritten. Following
the explicit policy decision, it is interpreted as “Windows 11 release
qualification not yet satisfied,” while technical promotion approval is
recorded here and in the project planning/CI documents.

## Candidate Selection

- The current PyPI release `scikit-learn 1.9.0` requires Python 3.11 or later
  and is incompatible with the fixed CPython 3.10 product runtime.
- `pip index versions scikit-learn` under CPython 3.10.11 selected `1.7.2` as
  the newest compatible stable release.
- The [scikit-learn 1.7.2 PyPI metadata](https://pypi.org/project/scikit-learn/1.7.2/)
  requires Python 3.10 or later, declares BSD-3-Clause, and publishes
  `scikit_learn-1.7.2-cp310-cp310-win_amd64.whl`.
- The official [1.7 installation guide](https://scikit-learn.org/1.7/install.html)
  identifies Python 3.10+ support and recommends binary wheels rather than a
  source build for pip installation.

The exact tested set was:

| Package | Version | Role |
| --- | ---: | --- |
| NumPy | 2.2.6 | existing production pin |
| SciPy | 1.15.3 | existing production pin |
| scikit-learn | 1.7.2 | candidate direct dependency |
| joblib | 1.5.2 | candidate transitive dependency |
| threadpoolctl | 3.6.0 | candidate transitive dependency |

## Reproduction Contract

Run from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-scikit-learn-spike.ps1
```

The runner creates a unique directory below
`$env:TEMP\datalab-scikit-learn-spike`, never writes an environment or wheel
into the repository, and rejects an output root inside the repository. It:

1. downloads five exact packages with `--only-binary=:all:` for
   CPython 3.10/Windows AMD64;
2. creates a fresh venv and installs only from that wheelhouse with
   `--no-index`;
3. runs `pip check`;
4. sets BLAS/OpenMP thread limits to one and routes HTTP(S)/all proxies to a
   failing local address for runtime probes;
5. measures an empty interpreter, scientific-stack import, and GP smoke five
   times each, including the venv redirector and child CPython working sets;
6. runs the deterministic GP in separate processes and compares SHA-256
   fingerprints; and
7. validates the redacted evidence schema-2 JSON record, including OS identity
   and PyPI candidate-wheel/download-manifest relationships.

Only the final validated schema-2 run on 2026-07-15 is recorded below. Evidence
schema 2 replaces the earlier schema-1 approval rule because a build-number-only
test could misclassify Windows Server 2025 as Windows 11. It records
`Win32_OperatingSystem` caption, build, and ProductType; only workstation
ProductType 1 with build 22000 or newer passes the Windows 11 gate. GitHub's
hosted `windows-latest` is Windows Server 2025 and is therefore not equivalent
evidence. Schema-1 records are not accepted by the schema-2 validator.

The OS decision follows Microsoft's
[Windows 11 release information](https://learn.microsoft.com/windows/release-health/windows11-release-information)
and [`Win32_OperatingSystem` contract](https://learn.microsoft.com/windows/win32/cimwin32prov/win32-operatingsystem).
The hosted-runner distinction follows the official
[`actions/runner-images` matrix](https://github.com/actions/runner-images),
which identifies `windows-latest` as Windows Server 2025.

## Measured Result

Environment:

- OS caption: Microsoft Windows 10 Home
- OS build: 19045
- OS ProductType: 1 (workstation)
- CPython: 3.10.11, 64-bit
- CPU-only: yes
- `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS`: 1
- Windows 11 acceptance gate: **not verified**

Artifact and compatibility result:

- five wheel-only packages downloaded; total compressed size 60.442 MiB;
- scikit-learn wheel size 8,886,969 bytes;
- scikit-learn wheel SHA-256:
  `ca250e6836d10e6f402436d6463d6c0e4d8e0234cfb6a9a47835bd392b852ce5`;
- offline `--no-index` installation passed;
- `pip check` passed with no broken requirements;
- imports reported the exact five requested versions;
- installed distribution-file total was 217.908 MiB.

Installed distribution sizes are host/wheel measurements, not future bundle
guarantees:

| Package | Installed size |
| --- | ---: |
| NumPy | 48.959 MiB |
| SciPy | 130.600 MiB |
| scikit-learn | 36.709 MiB |
| joblib | 1.534 MiB |
| threadpoolctl | 0.106 MiB |

Each timing includes process launch, a fixed 250 ms measurement hold, and the
probe. Values are five-run summaries on this host and are not an application
SLA:

| Probe | Min elapsed | Median elapsed | Max elapsed | Median peak working set |
| --- | ---: | ---: | ---: | ---: |
| Empty CPython | 965.976 ms | 1,083.500 ms | 1,221.765 ms | 20.641 MiB |
| NumPy/SciPy/scikit-learn import | 4,241.164 ms | 4,406.024 ms | 10,683.676 ms | 87.512 MiB |
| Fixed-kernel GP smoke | 7,558.241 ms | 7,978.231 ms | 8,705.798 ms | 96.652 MiB |

The median scientific import delta over the empty probe was 3,322.524 ms and
66.871 MiB. The outlying import maximum remains visible rather than being
discarded.

## Deterministic GP Smoke

The probe uses six synthetic one-dimensional observations, a fixed
`ConstantKernel * Matern(nu=2.5) + WhiteKernel`, no hyperparameter optimizer,
fixed numerical parameters, and seed `20260715`. It does not represent a
Bayesian optimization recommendation or a statistical reference fixture.

Two isolated process fingerprints matched:

`a0a6c5ab5d4aebb74a4a42bd988b427e3d991ad58db97977d1bc3c818909cfed`

Predicted means were
`[0.149969774298, 0.464367651456, 0.678498801131, 0.686471683379, 0.317938072788]`;
posterior standard deviations were
`[0.050988190801, 0.047280668886, 0.046924425473, 0.047280668886, 0.050988190801]`.
All were finite and all standard deviations were positive. Threadpool
inspection reported both bundled OpenBLAS pools and the OpenMP pool limited to
one thread.

## License Review

- scikit-learn 1.7.2: BSD-3-Clause, also confirmed by its official
  [license file](https://github.com/scikit-learn/scikit-learn/blob/1.7.2/COPYING);
- joblib 1.5.2: BSD 3-Clause metadata;
- threadpoolctl 3.6.0: BSD-3-Clause metadata;
- NumPy 2.2.6 and SciPy 1.15.3 remain the already reviewed production pins;
  their installed metadata includes bundled-library notices that must continue
  to be retained in any future distribution review.

No GPL/AGPL/SSPL/commercial/evaluation-only candidate dependency was added by
this spike.

## Remaining Release Work

1. Before release, run the unchanged script on Windows 11, CPython 3.10.x,
   64-bit, CPU-only.
2. Require the release evidence validator to report
   `candidate_approved_for_future_pin=true` only when OS ProductType is 1
   (workstation) and the Windows build is 22000 or newer. Windows Server does
   not satisfy this gate even when its build is newer.
3. Review the measured startup/memory cost against the implementation slice's
   worker lifecycle; do not import scikit-learn during API startup.
4. The next executable GP/EI slice must define its own
   method/config/result version, reference, numerical-failure, persistence, and
   E2E decisions.
