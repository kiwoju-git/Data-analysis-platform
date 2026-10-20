# ContourPy Dependency Contract

Reviewed on 2026-10-21. This is the dependency and packaging contract for
`contourpy==1.3.2`, not a claim that the unfinished DOE/RSM feature or a new
Linux application archive has passed its release gates.

## Choice and Scope

The application needs contour lines and filled regions with explicit ring
boundaries for stored RSM grids. The standard library and the existing
NumPy/SciPy stack do not provide this contour API. ContourPy provides a
dedicated implementation without installing Matplotlib or another chart stack.
The project describes its C++/pybind11 implementation and serial algorithm in
the [official package description](https://pypi.org/project/contourpy/1.3.2/).

The application uses `contourpy.contour_generator(name="serial")`, `Separate`
lines and `OuterOffset` filled geometry. It records `contourpy.serial` and the
library version in the geometry payload. This is geometry generation from a
provided numeric grid, not model fitting, optimizer selection, a replacement
statistical estimator or an automatic refit during HTML export.

- Python support: the pinned release requires Python >=3.10. Application support
  remains Windows CPython 3.10, Linux source/CI 3.11/3.12, and Ubuntu 24.04
  x86_64 CPython 3.12 for the packaged Linux release.
- Runtime dependency: NumPy >=1.23 only. Existing NumPy 2.2.6, SciPy 1.15.3 and
  scikit-learn 1.7.2 pins remain unchanged; no extras are requested.
- CPU-only serial execution; no GPU, external service or new process/thread
  pool is introduced by the selected algorithm.
- Wheel-only installation. Source builds and their Meson/C++ prerequisites are
  not part of the supported install path.
- All geometry executes locally after installation. No runtime data transfer,
  telemetry, CDN or browser chart dependency is added.
- The inspected Windows wheel is 221,188 bytes. Production memory/latency and
  whole-application startup costs have not been benchmarked by the lock
  generation jobs. Grid/output limits and geometry tests remain required.

These dependency requirements are from the
[versioned upstream metadata](https://raw.githubusercontent.com/contourpy/contourpy/v1.3.2/pyproject.toml),
not from the latest unpinned release. PyPI identifies this release as
production/stable; that does not replace the application's security audit or
future maintenance review.

## License and Notices

The exact pinned release is BSD-3-Clause, copyright 2021-2025 ContourPy
Developers. Retain the copyright, conditions and disclaimer in distributions;
the authors' names must not be used to imply endorsement. The authoritative
text is the [upstream 1.3.2 license](https://raw.githubusercontent.com/contourpy/contourpy/v1.3.2/LICENSE).

Actual Windows wheel inspection found:

- `contourpy-1.3.2.dist-info/METADATA`: Python >=3.10 and `numpy>=1.23`.
- `contourpy-1.3.2.dist-info/LICENSE`: BSD 3-Clause License.
- License-file SHA-256:
  `8553102e03001dd966278098cc027d0683c412b34ea141351b060be4330f39a9`.

`scripts/build_linux_release.py` already copies every dependency wheel's
`METADATA` and license/copying/notice files to
`THIRD_PARTY_NOTICES/<wheel-stem>/`. It includes these files in `FILES.sha256`.
The builder downloads from the CPython 3.12 runtime lock with `--require-hashes`
and `--only-binary=:all:`; it does not separately resolve ContourPy.
No ContourPy-specific runtime loader or installer exception is needed.
The completed Linux archive must still be inspected to verify its actual
Linux wheel and copied notice bytes; Windows inspection alone is not that proof.

## Native Hash Evidence

The Windows generator and Linux generator validate the actual interpreter,
OS/architecture and wheel compatibility, then calculate hashes from wheel
bytes. The five lock files are not populated with copied PyPI hashes.

| Target | Environment observed | Locked packages | Verification performed |
| --- | --- | --- | --- |
| Windows dev | CPython 3.10.11 / AMD64 | 49 | All wheel bytes match the Windows lock; existing development venv `pip check` and serial contour smoke passed |
| Linux 3.11 runtime | Ubuntu 24.04 / CPython 3.11.17 / x86_64 | 29 | Native generation, fresh venv wheelhouse-only hash-locked install, `pip check`, serial smoke passed |
| Linux 3.11 dev | Ubuntu 24.04 / CPython 3.11.17 / x86_64 | 47 | Same native generation and install checks passed |
| Linux 3.12 runtime | Ubuntu 24.04 / CPython 3.12.15 / x86_64 | 29 | Same native generation and install checks passed |
| Linux 3.12 dev | Ubuntu 24.04 / CPython 3.12.15 / x86_64 | 47 | Same native generation and install checks passed |

The Windows evidence is **not** a fresh-venv full-lock install claim. Its
read-only `contour-dependency-review.json` receipt is in the operator's external
validation directory, outside the repository and user workspace.

Linux evidence comes from
[generation-only run 39445525189](https://github.com/kiwoju-git/Data-analysis-platform/actions/runs/39445525189)
at source `e002095ed1d426cf96d6fb0ba39c8ea5d11eca03`. The four artifacts are
named `native-contourpy-locks-<target>-<profile>-<source-sha>`. Each contains the
generated `.lock`/`.in`, wheel filename/tag/hash records, OS/Python details,
baseline/input/output digests, installed package inventory, `pip check` output
and analytical serial contour coordinates. Collected copies and an independent
digest/inventory verification are under the ignored
`.tmp/contour-locks-e002095/` directory.

Measured ContourPy wheel hashes:

| Wheel target | SHA-256 |
| --- | --- |
| `cp310-cp310-win_amd64` | `c440093bbc8fc21c637c03bafcbef95ccd963bc6e0514ad887932c18ca2a759a` |
| `cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64` | `3859783aefa2b8355697f16642695a5b9792e7a46ab86da1118a4a23a51a33d7` |
| `cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64` | `f26b383144cf2d2c29f01a1e8170f50dacf0eac02d64139dcd709a8ac4eb3cfe` |

All previously locked package versions and wheel hashes were checked unchanged.
The analytical smoke uses `z=x` on a 3-by-3 grid: levels 0.5 and 1.5 must produce
vertical finite lines spanning y=0 through y=2. The Windows existing-venv smoke
checks level 0.5. This is a geometry/import test, not a model-reference test.

The earlier
[run 39443793234](https://github.com/kiwoju-git/Data-analysis-platform/actions/runs/39443793234)
downloaded and hashed wheels but stopped because its committed `.in` files did
not yet declare ContourPy. The declaration was committed before the successful
rerun; the fail-closed input check was not removed.

## Regeneration and Gate Separation

The `generate_linux_locks=true` workflow-dispatch mode independently runs the
four Linux target/profile combinations. It downloads the existing lock with
`--require-hashes`, adds only the native `contourpy==1.3.2` wheel, runs the
existing generator/validator, and rejects any other package addition, removal,
version change or hash change. It then installs the resulting lock into a new
venv using `--no-index --find-links ... --only-binary=:all: --require-hashes`.

This is local-wheelhouse installation, **not enforced network isolation**.
The evidence explicitly records `network_isolation_enforced=false`.
The application archive verifier separately enforces its network-namespace
installation contract.

Generation-only mode skips product tests, dependency-security audits, archive
packaging and `release-ready`; its success cannot authorize main or a Release.
The normal CI path retains those gates. No new full security audit result is
claimed by this dependency evidence.

## Final Archive Acceptance

After the coherent source/locks/tests/docs commit:

1. Run normal Windows, Linux 3.12, Python 3.11, browser and dependency-security
   gates on that exact SHA. Preserve the existing numerical reference gates.
2. Build the Linux archive from that clean committed SHA with its explicit
   release version. Do not mix an uncommitted wheel or another source artifact.
3. Verify the tar digest, `FILES.sha256`, BUILD_INFO, application-wheel identity,
   runtime lock and the actual ContourPy CPython 3.12 Linux wheel.
4. Compare packaged ContourPy `METADATA`/license notice bytes with the included
   wheel; do not rely solely on a notice directory name.
5. Execute the existing two installations, network-blocked install/reinstall,
   default-LAN and local-only checks, restarts and shared external-workspace
   restore. Keep the existing managed-report/pilot tests. Add the actual
   DOE/RSM contour browser fixture to this archive journey; its integration is
   separate from the dependency smoke.
6. Verify saved contour line/band geometry, SVG and offline HTML match the
   stored result without refitting. Include constant/invalid grids and exact
   selected-model/response ownership tests.
7. Publish only the same verified archive bytes after the exact-source
   `release-ready` gate passes. A CI artifact is not a public Release.

As of the 2026-10-21 read-only release/tag check, the latest numeric Linux
release is `linux-pilot-2026.10.4`; no `linux-*2026.10.5` tag exists.
`2026.10.5` is therefore an available next candidate, not a reserved or published
version. `release-version.json` is still 2026.10.4 at this checkpoint. Recheck
remote tags before assigning a final version; never replace an existing tag.
