# Reliability Remediation Release Notes

These notes describe the feature branch's contracts, not a release publication
announcement. Exact source, CI results, archive digest and published assets must
come from the final validation report. See the [status ledger](end_to_end_remediation.md)
and [journey matrix](remediation_journey_matrix.md) for executed scope and gaps.

## Data and Analysis

- Pending upload, schema, source activation and analysis responses cannot
  overwrite a newer input/source context. Server-created immutable artifacts are
  preserved even when their response is no longer eligible for the current UI.
- Schema editing requires the hash from the draft's source. A conflicting save
  returns 409 and preserves the draft for explicit comparison/re-editing.
- Completed analyses revalidate source ownership before publication. A concurrent
  schema change marks retained results stale; deleted owners or replaced model
  identities cannot receive newly orphaned results.
- GPR direct predictions are tied to exact model/manifest/input snapshots and
  client row IDs. Browser JSON downloads and explicitly saved managed results
  remain distinct. Training, OOF, latent and observation uncertainty meanings
  are not interchanged.
- Existing statistical method versions, numerical policies and stored model
  bytes are not changed by these display/lifecycle/report fixes.

## UI and Reports

- API transport preserves request bodies and raw response data. Translation is
  applied at explicit UI error/warning/system-text boundaries, not over JSON.
- Locale initialization tolerates denied browser storage. Startup failures show
  a safe recovery screen rather than exposing a traceback or a blank page.
- Chart tick formatting honors explicit labels, axis-specific formatting and
  legacy fallback without changing data coordinates, pinning or chart geometry.
- Report list filters and pagination are independent of the selected result.
  Only exact-owner deletion removes that selection; transient errors are not
  treated as deletion.
- Generic and dedicated managed reports render stored payloads only. Actual
  capability distinguishes full, summary, unsupported and not-applicable sections.
  Missing legacy values are explained, never reconstructed by fitting or reading
  original rows. Existing reports and result/model files are not rewritten.
- Current synchronous analysis methods explicitly declare cancellation unsupported.
  A button or `cancel_requested` state is not presented as actual interruption.

## Compatibility and Workspace

- The baseline API contract was 22; schema CAS and coordinated contracts use 23.
  Metadata 21 added managed report ownership; metadata 22 adds the nullable
  interrupted-execution reason. These are additive migrations with compatibility
  tests, not a rewrite of historic statistical results.
- One process holds an OS lease for a workspace throughout app lifespan. Another
  server on a different port cannot open the same workspace. Independent
  workspaces may run concurrently. Never delete a live lock file to bypass it.
- Backup/restore is an offline CLI operation with an exclusive lease, file
  manifest and hashes, DB integrity and referenced-file checks. Restore targets
  a new empty location; it does not overwrite or remove the original workspace.
- Windows CPython 3.10 and Linux CPython 3.12 remain separate locked targets;
  Python 3.11 compatibility is checked separately. See actual native results
  rather than interpreting this contract as a physical Windows 11 test claim.

## LAN Boundary

Owner-approved frontend/Linux release LAN binding remains `0.0.0.0:8600` with
`--local-only` on the Linux launcher. The Windows development API stays loopback
behind its same-origin frontend proxy. Host/Origin guards are not authentication.
LAN clients share the same workspace and can exercise its permitted operations.
No firewall change, wildcard CORS, authentication, RBAC or TLS is silently added.
Do not treat this as an authenticated multi-user or public-Internet deployment.

## Rollback Limits

The final report supplies exact task commit IDs in reverse order. Revert only
those IDs; do not use a broad range that could include someone else's commits.
Display-only rollback and coordinated API/storage changes need separate handling.
No reset/force push, workspace deletion or artifact rewrite is a rollback step.

Code revert does not undo an already applied metadata migration. Older code may
refuse metadata 21/22 and may not understand newly managed prediction/report
sources. Before first opening a pre-upgrade workspace with the new version,
make a verified offline backup. Returning to old code may require restoring that
**pre-upgrade** backup to a new directory. A current schema-22 backup does not
magically downgrade into schema 20/21. Keep the current workspace and all newer
analysis/model/report files intact for a compatible application version.

Final Linux mixed-install identity, network-blocked archive installation and
the aggregate `release-ready` gate are A15 requirements; publication must wait
for their actual results, not the existence of these notes.
