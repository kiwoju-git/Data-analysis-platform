# Trusted LAN Development (2026-09-18)

## Scope and acceptance

The product owner explicitly requested LAN access in place of the former
loopback-only development entry point. This is a shared, trusted-operator
development workspace, not a production multi-user deployment. The acceptance
criteria are a reachable port 8600, same-origin API calls from another host,
unchanged statistical/storage contracts, strict runtime identity checks, and
an explicit local-only escape hatch. No firewall is changed by the application.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
# Only this computer:
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -LocalOnly
```

Normal `dev.ps1` and `npm --prefix frontend run dev` bind the frontend to
`0.0.0.0:8600`. A colleague opens `http://<server-PC-IPv4>:8600`, not
`http://0.0.0.0:8600` and not their own localhost. Find the server's active
Ethernet/Wi-Fi IPv4 with `ipconfig`; do not use a WSL/VPN adapter address.
Use the PowerShell entry point to start both processes with matching build IDs.
Bare npm starts only the frontend and requires the compatible API already running.

The API deliberately remains on `127.0.0.1:8000`. Vite proxies `/api` to it.
This makes datasets, jobs, predictions and downloads available through the one
LAN entry point without exposing an additional direct API port or wildcard CORS.
`VITE_API_BASE_URL=/` selects same-origin requests. `DATALAB_DEV_API_TARGET`
is server-side only, accepts an HTTP `127.0.0.1` origin, and follows custom
`-BackendPort` values. Explicit existing `VITE_API_BASE_URL` configurations remain
supported; a hardcoded loopback API URL is unsuitable for remote browsers.

`-FrontendOnly` retains the exact-compatible-backend check and uses this proxy.
`-BackendOnly` stays loopback. `-LocalOnly` binds the frontend to loopback too.
Vite test mode and preview remain loopback by default. Strict ports prevent
silently moving the app to a different port. API contract 21 and metadata 20,
method/result/manifest versions, data and checksums are unchanged.

## Threat model and deployment boundary

| Boundary | Policy / residual risk |
| --- | --- |
| Trusted peer | Every allowed peer is a workspace operator: can read, upload, analyze, export, edit and delete. No account isolation or ownership. |
| Authentication / RBAC | Not implemented. Network admission is the trust boundary, not an authentication substitute. No production multi-user security claim. |
| HTTP / TLS | HTTP is plaintext; network observers can see data. Sensitive/regulated use requires a separately configured authenticated TLS gateway and IT review. |
| Other websites / CSRF | Frontend middleware allows only local interface IPs/localhost as Host; compares exact Origin including port; rejects cross-site fetches. Unsafe methods require the same origin. Forwarded headers are not trusted. |
| DNS rebinding / CORS | No `allowedHosts: true` or wildcard CORS. Dev-server CORS is disabled. Backend narrow CORS remains unchanged. Interface changes require restart. |
| Direct native clients | Host/Origin are forgeable by native clients; these checks are browser defenses, not authentication. |
| Network exposure | `0.0.0.0` listens on all IPv4 adapters, not only a private subnet. Keep Public-profile access blocked; allow inbound TCP 8600 only for approved PCs/subnets on Private/Domain profiles. No router forwarding, Internet publication, or firewall disabling. |
| Developer source | A Vite dev server exposes application source to admitted peers. Use only trusted operators; this is not a hardened production server. |
| Availability / concurrency | CPU budgets and immutable storage remain; multiple clients share resources. No multi-user load/SLA or per-user audit guarantee. |

Authentication, per-user RBAC, HTTPS/secure session handling and attributable audit
logs remain mandatory gates before expanding beyond these mutually trusted
operators. Do not store secrets in frontend source. Back up the workspace before
allowing peer edits. Browser drafts are per browser; saved assets are shared.

If another PC cannot connect, confirm the listening address, correct adapter IP,
Private/Domain profile, IT-managed firewall inbound TCP 8600 scope, VPN routing
and wireless client isolation. A successful browser check on the server is not
proof that the company's firewall allows another physical PC. The application
does not change firewall/network profiles or request administrative rights.

## Dependency review

`@types/node` 22.19.0 (MIT, dev-only) and its `undici-types` declarations type
the local network adapter. No runtime code, Python/GPU dependency, native wheel,
font/CDN or telemetry is added. Node 22, Windows and offline-after-install usage
are unchanged. The lockfile pins exact resolved versions.

LAN exposure prompted a targeted audit of the existing Vite toolchain. Only
PostCSS and nanoid transitive security patches were updated, not the UI/statistical
libraries. Remaining npm audit findings in ESLint's brace-expansion/js-yaml and
Vitest/mocker are recorded separately; Vitest stays loopback and is not an exposed
application service. No claim of a clean dependency-security audit is made.

Official references: [Vite host/proxy/CORS security](https://vite.dev/config/server-options),
[PostCSS advisory](https://github.com/advisories/GHSA-r28c-9q8g-f849),
[nanoid advisory](https://github.com/advisories/GHSA-2v37-7h3g-55p8).

## Validation

`frontend/src/devNetwork.test.ts` checks actual guard functions, hostile/missing
Origin/Host, same-origin methods, proxy-target validation and relative API URLs.
Startup tests retain version/port checks and assert API isolation. The complete
Chromium critical path now traverses the same-origin API proxy, including data
mutations and downloads. `tests/e2e/lan_grouped_menu.py` starts `dev.ps1` against
a temporary synthetic workspace, verifies an actual adapter IP, browser routes,
host/origin rejection and local-only isolation. It does not touch user data.
