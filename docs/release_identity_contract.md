# Release Identity Contract

## Boundary

The source checkout and Windows development launch are unchanged. Linux archives
target Ubuntu 24.04 x86_64 CPython 3.12. `run.sh` enters the release-owned
`release_bootstrap.py` under `-I -S -B`, not an installed `app.launch` module.
The bootstrap uses only the standard library until verification succeeds.
System Python/venv/pip remain prerequisites; the archive does not bundle Python.

`verify_release_payload(root)` validates bounded BUILD_INFO/FILES JSON/text,
safe regular paths, package file hashes, lock hash and the actual application
wheel's `app/_release_build.json`. It needs no venv or installation marker.
`verify_installed_release(root)` additionally verifies venv configuration,
application distribution identity, every immutable application wheel file except
pip's rewritten RECORD, absence of unowned application files/bytecode and exact
structured `.installed` marker identity. Installed RECORD is not a trust anchor.
Dependencies retain the hash-locked offline pip install and pip-check boundary;
this is not a per-launch hash scan of every third-party installed binary.

The legacy `app.launch.verify_release` is a payload-only compatibility check, not
an installed-code claim. Direct `python -m app.launch` refuses to start. Only the
verified bootstrap invokes `launch_verified`; runtime contract/network checks
and environment configuration still precede the FastAPI/Uvicorn import.

## Identity Flow

The builder reads the exact clean committed source using git archive. In that
private staging tree only, it writes source SHA, release version, API/schema,
capabilities and platform target into the wheel's build resource. It checks that
the built wheel actually contains that resource. Wheel SHA then enters BUILD_INFO
alongside the completed lock SHA; FILES hashes BUILD_INFO and packaged files.
The archive SHA is external. No resource contains its own wheel/manifest hash,
and no source edit is needed to insert the final commit after the build.

Release version is separate from application/method/API versions. The version
format is bounded numeric major.minor.patch. API 23 and metadata 22 are current
contracts, not constants substituted for the staged commit's real contracts.

## Installation and Launch

Installation holds an exclusive OS advisory lock on a persistent `.release.lock`
inode, invalidates any old marker, creates or validates the private venv, and
runs pip under the explicit private site-packages path with site initialization
disabled. No `.pth` execution, PYTHONPATH or editable app import is needed.
Pip uses force-reinstall, no-index, only-binary, require-hashes and no-compile.
Pip/check/verification failure cannot publish a success marker. Marker publication
uses an exclusive temporary file, file fsync, atomic replace and directory fsync.
The marker is not a substitute for repeating actual installed file verification.

Launch holds a shared installation lock through the server lifetime. Install
conflicts fail without killing processes or unlinking the lock. OS process death
releases ownership. Application workspace leases remain separate; this change
does not move, delete or modify workspace results/models during installation.

The bootstrap adds the verified private site-packages directory explicitly, never
through `site.addsitedir`; it restores venv prefix values needed with Python 3.12
`-S`. Normal spawn workers inherit the verified Python path. Native archive
PCA/PLS/GPR runs must verify that behavior; Windows pure tests do not prove it.
The allowed `workspace-backup` command applies the same verified boundary before
executing the existing backup module. There is no arbitrary-module command.

## Evidence and Limits

Verifier JSON uses direct fields: `verification_status`, source/release/API/schema,
Python target, application wheel SHA, lock SHA and release-manifest SHA. Installed
evidence also includes marker schema and installed-application-file-list SHA.
`payload_verified` and `verified` are different statuses. Platform/argument/hash
errors are fail-closed; there is no skip-marker or downgrade launch option.

Tests use actual ZIP wheels, changed source/resource/marker/RECORD, orphan bytecode,
duplicate distributions, failed marker publication and failed pip steps. A real
Hatch wheel verifies staging JSON inclusion. Pre-import subprocess tests run
under `-I -S -B` with sentinel application/.pth contents. OS lock lifecycle is
tested with real Linux subprocesses and skipped explicitly on Windows.

Hash checks detect mixed/changed installations; they do not authenticate an
attacker-rewritten payload plus checksums or a compromised Python interpreter.
Use the trusted release channel and external archive digest. The CI verifier's
network namespace must separately prove network-blocked installation: no-index
alone is not OS-level isolation. No actual company-peer/firewall validation is
implied by same-host interface-IP browser tests.
