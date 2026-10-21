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
