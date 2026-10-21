# BO/GPR Native Security Follow-up

The first full branch run39613148814 on1c178d33444d185625418f5bb71270d39d1aa1df
failed the existing dependency-security gate. No exception or severity downgrade
is introduced. These are newly reported development-dependency advisories, not
a reason to change NumPy/SciPy/scikit-learn or the BO/GPR calculations.

## Confirmed Advisories

- certifi2026.6.17 (Windows dev) and2026.7.22 (Linux dev) include a compromised
  certificate chain. The patched pin is2026.10.19. Runtime locks do not contain
  this package. Source: [maintainer advisory](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2).
- Vite8.0.16 includes vulnerable launch-editor behavior. The closest patched
  minor release is8.1.6; Node22.23.2 satisfies its Node>=22.12 requirement.
  [Windows path validation](https://github.com/vitejs/launch-editor/security/advisories/GHSA-587h-7wmj-h5pm),
  [Windows percent escaping](https://github.com/vitejs/launch-editor/security/advisories/GHSA-698v-4r3x-3vcv),
  [editor argument handling](https://github.com/vitejs/launch-editor/security/advisories/GHSA-r825-w8mm-5pxw).
  Vite is used by trusted-LAN development, not by the built Linux release server.

`scripts/refresh_certifi_lock.py` runs only on the matching native OS/Python.
It downloads the existing hash-locked wheels, replaces only certifi with an
actual wheel, regenerates hashes with the existing native generator, rejects
every other version/hash change, and verifies offline installation plus pip check
in a new venv. Linux wheel hashes are not copied from a Windows target.
The universal certifi wheel itself is platform independent.

The reusable `security-lock-refresh` workflow is maintenance evidence only.
It does not satisfy product/security/archive/release-ready gates. Generated
locks must be reviewed and committed, followed by the normal complete CI.
Native generation, post-change audits and browser/build results are pending
until explicitly recorded. Existing published releases and tags are unchanged.

## Executed Follow-up

Native maintenance run39614860205 generated three locks on Windows/Python3.10.11,
Ubuntu24.04/Python3.11.17 and3.12.15. Every target completed a fresh no-index,
hash-verified wheel installation and pip check. Only certifi's version/hash
changed in each dev lock; runtime locks are unchanged. Generated universal wheel
SHA-256:42d35340cc5b9ba78e818ddbff0c5b1c2b779de448a340fd1b989f5fa8670e1b.
The initial maintenance dispatch was rejected for an unquoted YAML colon; a
workflow parsing regression was added,2 targeted tests passed and the corrected
maintenance run succeeded. This was not a product test success.

Vite8.1.6 requires a Rolldown1.1.x dependency subtree update; unrelated direct
packages and numerical libraries were not upgraded. Local Node22.23.2 clean
npm install, all973 frontend tests/112 files, TypeScript production build passed.
Fresh `dependency_security.py --frontend frontend` runtime/all npm audits passed;
targeted lock/security tests:11 passed,1 existing platform-scoped skip.
The existing >500kB bundle warning remains. Final native audits and browser suites
must still pass on the committed updated locks before publication.
