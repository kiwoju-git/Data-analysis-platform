# Download Checksum Compatibility

## Decision

Managed reports and existing Factorial assets use `api/downloadDigest.ts` for
SHA-256 over the actual downloaded bytes. The descriptor's exact SHA-256 and
byte count must both match before a file is offered to the browser.

Use native `crypto.subtle.digest` when it exists. On an HTTP LAN origin where
SubtleCrypto is absent, lazy-load the locally bundled
`@noble/hashes/sha2.js` implementation. An available native digest that rejects
is not silently replaced. There is no custom cryptographic implementation,
header-only bypass, CDN, external runtime request, or statistics change.

SHA-256 detects a mismatching artifact; it does not authenticate an HTTP server
or provide TLS. Existing trusted-LAN restrictions still apply.

## Dependency Review (2026-10-18)

- Exact production pin: `@noble/hashes` 2.4.0, matching the npm latest metadata
  observed on this date. Lockfile integrity is recorded by npm, not hand-written.
- MIT license; zero runtime/optional dependencies and no install lifecycle hook.
- Pure ESM JavaScript, Node >=20.19.0; development uses Node 22.23.2 on Windows.
  No Python, native build, GPU, administrator privilege, or platform wheel is
  required. The production bundle works offline after local installation.
- npm reports 691646 unpacked bytes for the complete package. The application
  imports only SHA-256 through the documented subpath, not the package root.
  The measured production build emits a separate 5.33 kB SHA-2 chunk
  (2.64 kB gzip) and a 0.35 kB adapter chunk (0.27 kB gzip).
- Standard browser WebCrypto alone is insufficient on supported HTTP LAN
  origins. No overlapping general-purpose crypto package existed in the app.
- Upstream documents an independent audit of version 1.0.0 in 2022 and later
  test/audit work. This is not a claim that version 2.4.0 has a fresh independent
  audit. The exact dependency still requires normal pin/update/security review.

Primary references:
[package contract](https://github.com/paulmillr/noble-hashes/blob/2.4.0/package.json),
[MIT license](https://github.com/paulmillr/noble-hashes/blob/2.4.0/LICENSE),
[usage and security notes](https://github.com/paulmillr/noble-hashes/tree/2.4.0),
[SubtleCrypto secure-context restriction](https://developer.mozilla.org/en-US/docs/Web/API/Crypto/subtle),
[SHA-256 reference vectors](https://www.rfc-editor.org/rfc/rfc6234).

## Validation Scope

`api/downloadDigest.test.ts` covers published empty/abc/multi-block/million-a
vectors with native and fallback implementations, absent Crypto/SubtleCrypto,
native operational failure, same-length single-byte corruption despite a
matching claimed ETag, and the managed-report/Factorial download integrations.
No fixture contains user data. Browser source guards continue to suppress a
download whose request owner is no longer selected.

The local 16 MiB benchmark records elapsed time and Node process memory deltas.
These are approximate process measurements, not browser peak-memory guarantees.
The existing Blob/ArrayBuffer allocation remains; fallback uses a Uint8Array
view rather than making another input-sized copy. Hashing is synchronous inside
the fallback implementation, so very large files can briefly occupy the UI
thread. Existing backend artifact size limits are unchanged.

Local measurement on Windows x64 / Node 22.23.2, 2026-10-18, synthetic 16 MiB:

| Implementation | Cold call | Three warm calls | Approximate RSS delta | Heap-used delta |
| --- | ---: | --- | ---: | ---: |
| Native WebCrypto | 74.49 ms | 63.28 / 53.38 / 56.03 ms | 16.45 MiB | 0.13 MiB |
| Noble fallback | 211.47 ms | 198.16 / 168.42 / 173.86 ms | 2.27 MiB | 1.14 MiB |

Each digest matched Node's independent `createHash("sha256")` over the same
16777216 bytes. Memory deltas exclude the input allocated before the measurement;
garbage collection and allocator reuse affect these figures. Native and fallback
use the same already-completed bytes and do not read source data again.
`npm ci` completed with zero reported audit vulnerabilities on this date; this
does not guarantee absence of vulnerabilities. Full-browser validation remains
separate from this Node benchmark.
