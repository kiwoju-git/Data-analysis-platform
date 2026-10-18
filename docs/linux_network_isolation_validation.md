# Linux Network-Isolated Install Validation

This is a CI release-validation boundary, not a product installation prerequisite.
The distributed installer continues to run without sudo, namespaces, Node, Git,
or network access. This helper never changes host firewall rules or workspaces.

## Contract

`scripts/network_isolated_install.py` exposes the stdlib-only function
`run_network_blocked_install(root, env, log_path, evidence_path) -> dict`.
The caller first verifies the exact extracted archive payload. Log and evidence
paths must be new diagnostics files outside the release root. Existing evidence
is never overwritten. The caller's environment is not modified.

Native Ubuntu CI with CPython 3.12 must provide passwordless `sudo`, util-linux
`unshare`, and GNU `timeout`. Only creation of an isolated network namespace uses
elevation. `unshare --setgid/--setuid` drops to the original nonroot runner before
the Python helper, grandchild probe, and unmodified `install.sh` execute. Missing
capability is a hard failure; there is no ordinary-network fallback.

The parent owns live IPv4 and IPv6 loopback TCP controls and proves both reachable
before and after installation. Child probes must prove a different network
namespace, the expected real/effective UID and GID, no supplementary root group,
only the loopback interface, no usable routes, no inherited network sockets, and
failure to reach both live parent controls. A Python grandchild repeats the proof
in the same child namespace. All child checks run again after installation.
Every extracted/installed entry's ownership is checked without following symlinks.

Only explicit `PATH` and an absolute `PYTHON` are taken from the caller. HOME and
temporary files are private; locale, CPU limits and pip's no-index/no-config
policies are explicit. Tokens, proxy variables, shell/Python startup hooks, and
dynamic-loader variables are not inherited. A sanitized base Python startup
probe must pass. A runner whose Python requires arbitrary loader environment is
not silently supported.

An outer privileged watchdog caps the complete namespace phase at 600 seconds,
with SIGKILL after five more seconds. An inner unprivileged watchdog caps the
installer at 540 seconds, leaving time for post-checks. The parent uses finite
waits and an eight-MiB bounded log. Unconfirmed process/pipe cleanup is a failure,
not an installation success. No unrelated process is killed.

Only all successful phases publish schema-1 evidence with
`network_blocked_installation: true`, namespace/UID/GID proofs, tool versions,
control results, install exit code, ownership count and elapsed time. Installed
wheel identity and archive/source hashes remain the separate release verifier's
responsibility. Evidence contains synthetic control ports, not application data
or environment credentials.

## Validation Scope

Windows-compatible pure tests exercise argument construction, environment
allowlisting, route/proof validation, failure gates, stale evidence refusal,
bounded logging, and mocked process completion. A small actual local socket test
checks both host controls; it is not a Linux namespace test. Mocks never establish
native network isolation. The final archive must pass actual Ubuntu namespace
installation before a release can claim this gate passed.

The native contract follows Ubuntu 24.04's
[unshare manual](https://manpages.ubuntu.com/manpages/noble/man1/unshare.1.html)
and Linux [network namespace semantics](https://man7.org/linux/man-pages/man7/network_namespaces.7.html).
The fixture isolates the network stack, not a hostile local administrator or the
entire filesystem, and does not claim to sandbox arbitrary untrusted installers.
