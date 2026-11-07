# Statistical Twin

### Current Capability and Compatibility

The [generated capability matrix](docs/generated/analysis_capability_matrix.md)
joins the actual registry, execution routes, canonical menus, help coverage and
stored-report readers. It records the current API/metadata versions and separates
available methods, source prerequisites, limited options, contextual workflows,
historical readers and roadmap-only items. A static declaration is not a runtime
eligibility check or a claim that every stored report is complete.
See the [capability contract](docs/analysis_capability_contract.md) and
[executed journey evidence](docs/remediation_journey_matrix.md); dated validation
records below retain their original scope rather than certifying the current build.

### Result Charts and Two Variances

Result charts share viewport-safe tooltips, explicit pinned selections, visible
axes and bounded responsive frames. Desktop results switch between one/two
columns by available content width; navigation becomes a drawer below1100px.
That chart refresh did not change fitting policies. Subsequent BO/GPR policy
changes are separately versioned below.
`quality.two_variances`0.1 adds explicit two-group BF equality or normal-F ratio
inference; Bonett ratio intervals are not included in this version. Current
runtime compatibility is recorded above. See [method contract](docs/two_variances_method_contract.md) and
[validation record](docs/result_charts_linux_validation.md).

### Noise-Aware BO and GPR

The API31 source workflow separates **Review experiment candidates** from
**Confirm these experiments**. Reviewing does not add trials; confirmation saves
the exact ordered batch without another fit and supports safe explicit retry.
Unconfirmed reviews are temporary (up to20 minutes/eight reviews, or until server
restart). Numeric BO now selects Gaussian, Matern5/2 (default), Matern3/2 or
Exponential. The selected family and fitted parameters remain attached to the
review, committed result and report. This matches JMP19.2's numeric option names,
not a verified match to its fitted results. Multiresponse desirability and editable
candidate tables remain later stages. See the
[implementation stages and evidence](docs/bo_jmp_workflow_stages.md).

API31/metadata25 extends the existing batch table's version constraint for
method0.8.0/config3/result3/model4. Back up an existing workspace offline before
upgrade; old code cannot open metadata25. Legacy recommendation JSON/hashes are
preserved, not recalculated. See [kernel contract and current evidence](docs/bo_kernel_alignment.md).
No new Linux Release is published by this stage.

BO separates observation noise from numerical jitter and uses latent-posterior
EI/ETI, reproducible joint-latent batch planning, executable mixed-domain search
and explicitly registered independent repeats. Standalone GPR adds group/time
validation, optional one-step observed lags, bounded nominal predictors and an
opt-in extended Exact GP resource profile. Extended mode admits at most2,000
valid rows only when the whole requested configuration passes the resource
estimate; it is not a sparse GP or a promise that every2,000-row fit is admitted.

API26/metadata24 adds a real BO storage migration. Back up an existing workspace
offline before upgrade; old code cannot open the new metadata schema. Existing
JSON/NPZ artifacts are not rewritten. Current implementation and actual validation
scope are recorded in the [extension evidence](docs/bo_gpr_noise_validation_extension.md)
and [JMP comparison](docs/jmp_gp_bo_alignment.md), without claiming JMP numeric parity.

### RSM and Gage Follow-up

The API27 source update adds source-locked RSM response paste, final-model raw/
standardized residual diagnostics, explicit CCC cube/axial search regions, and
stable optimizer numeric drafts. Balanced crossed Gage R&R can use three columns
(part, operator, measurement); repeated measurements remain required. The new UI
explicitly requests auto-pooling of a nonsignificant interaction, while legacy
retain-policy results remain readable. Metadata24 is unchanged. See
[implementation and validation scope](docs/rsm_gage_followup.md).

The API27 follow-up did not publish a separate Linux Release. Its changes are
preserved in the subsequent API28 source and release candidate below.

### Gage Graphs and Result Presentation

API28 / Gage0.3.0 result3 adds six saved diagnostic plots without changing the
selected full/pooled ANOVA. Original part/operator identifiers remain redacted;
all summaries use the complete valid sample before the individual-point display
cap. Historical results1/2 remain readable, with only their stored component
chart and explicit missing-plot notices. Metadata24 is unchanged.
Run Chart metrics separate labels and values and preserve small p-values.
Dynamic Capability/Gage system messages are localized at display boundaries;
user text and request data are not translated. See the
[scoped audit and verification record](docs/gage_charts_layout_i18n_audit.md).

### Linux Prerelease

Windows PowerShell/Python3.10 remains supported. Linux source/CI adds Python3.11
and3.12; the offline archive targets Ubuntu24.04 x86_64/Python3.12 only. It ships
built UI and hash-locked wheels, not Python itself. The Linux release defaults to
`0.0.0.0:8600` for owner-approved trusted LAN use; `run.sh --local-only` restores
loopback. All peers share read/write/delete access without login or TLS, so
restrict firewall access and never expose it to the Internet. Runtime requires
no Node/Git/CDN. See [installation guide](README-linux.md) and
[packaging contract](docs/linux_release_contract.md). Availability and actual
validation are recorded in the GitHub prerelease assets; source support alone is
not an archive validation pass.

#### Install and Run the Linux Release

Download the Linux `.tar.gz` and `SHA256SUMS` from the
[2026.10.8 Gage part-ID prerelease](https://github.com/kiwoju-git/Data-analysis-platform/releases/tag/linux-gage-part-id-2026.10.8).
This version is publishable only after the exact-source product/security/resource
and archive gates pass; an absent Release page means publication is not complete.
The supported target is Ubuntu 24.04, x86_64, CPython 3.12 with `venv` and `pip`
already installed. Python itself is not bundled. Node.js and Git are not needed.
Verify the archive against the published checksum before extraction:

```bash
sha256sum -c SHA256SUMS
tar -xzf statistical-twin-linux-2026.10.8-ubuntu24.04-x86_64-py312.tar.gz
cd statistical-twin-linux
bash install.sh
bash run.sh
```

`install.sh` verifies release files and installs the bundled hash-locked wheels
without network access. It does not use `sudo` or modify system Python. Default
listening is `0.0.0.0:8600`; on an approved LAN peer open
`http://<server-IP>:8600`, not `http://0.0.0.0:8600`. The server computer can use
`http://127.0.0.1:8600`. For access only from the server computer:

```bash
bash run.sh --local-only
```

This is a shared operator workspace, **not an authenticated multi-user service**.
All allowed peers can read/change/delete the same workspace. No login, RBAC or
TLS is provided and the installer does not change firewall rules. Restrict access
to trusted company peers; do not expose port 8600 to the public Internet.
Stop the application before replacing an installation, keep the previous release
directory, and use the [offline backup/restore commands](docs/workspace_backup.md)
before upgrading an existing workspace. Never copy an old `.venv` into a new
release: mixed installed-code identities are rejected.

Release assets include exact-source validation, SHA-256 and scoped rollback
instructions. [Pilot follow-up evidence](docs/pilot_followup_0849aaa.md) separates
calculation, API, source-browser and completed-archive checks. A release link is
not a claim of publication until its assets and successful gates are available.

### GPR Reproducibility and Report Parity

Family-domain landings now share compact method cards while sidebar families and
routes remain intact. Standalone GPR exposes length-scale units/bounds and actual
L-BFGS-B or bounded BFGS optimization, with fold-local reproducibility evidence.
New scaled-input drafts propose a 0.5 lower bound; the legacy 0.01 preset remains
available and stronger smoothing is not guaranteed to improve prediction.
PLS HTML now preserves stored tables/plots without recalculation. Other report
coverage and summary-only limitations are documented in the
[method report matrix](docs/html_report_coverage_matrix.md).
See the [validation and rollback record](docs/gpr_ui_report_parity_validation.md).

### Dashboard and Direct Navigation

Home now groups six icon-led quick actions, the eight analysis domains, and
live dataset/recent-analysis/model summaries. Sidebar Analysis and Graphs open
their workspaces directly; separate chevrons only expand their menus. Compact
entry cards share Graph Builder's blue selection state, local icons and KOR/ENG
labels. Statistical workflows and stored assets are unchanged. See the
[UI validation and rollback record](docs/dashboard_navigation_refresh.md).

### Selectable DOE Terms and GP Kernel Comparison

Full-factorial Center curvature is now a removable candidate, with explicit
candidate/forced/excluded term policies and detailed backward-step tables.
Strong hierarchy protects factorial parents without treating Center as one.
Standalone GP compares 2-4 signal kernels on identical CV folds, supports up
to five CV restarts and optionally retains candidate diagnostics. WhiteKernel
remains observation noise, not another signal choice. Only the selected GP
model is saved for prediction; comparison scores are not an independent test.
See the [release verification record](docs/curvature_gp_validation.md).

### Factorial Final-Model Workflow

Full two-level and General Full analyses support explicit hierarchical backward
elimination and disclosed saturated error pooling. Response paste previews into
the draft; saving creates one immutable revision. Final equations, coefficients,
VIF/PRESS, interactive residual/factorial plots, domain-bounded stored-model
prediction and managed KOR/ENG HTML analysis reports share the existing DOE
workspace. Fractional/PB automated selection is intentionally unavailable.
See [contracts and validation](docs/factorial_model_workflow_validation.md).

Fit Regression Model now offers OLS, Ridge, Lasso and Elastic Net in one panel.
Regularized models use training-fold standardization and nested cross-validation,
save checksummed JSON manifests, and support point prediction and response
optimization within the training domain. They do not provide classical OLS
p-values, ANOVA or prediction intervals. The eight analysis domains retain all
current methods with more compact selection cards and initially collapsed guides.
See [the statistical contract](docs/regularized_linear_model_contract.md).
Frontend/backend runtime compatibility must match the current contract in the
generated matrix; existing saved artifacts are not silently rewritten.

The refined UI uses Graph Builder's selection blue with compact, neutral
navigation. Inactive sidebar groups start collapsed; an open analysis keeps its
method catalog under **Change analysis / 분석 변경**, without closing the current
form or results. Short guidance and statistical warnings are retained. See the
[UI design and verification record](docs/refined_ui_design.md).

Statistical Twin is a local-first statistical analysis application for Windows. It provides dataset preparation, statistical analysis, interactive charts, reports, asset management, regression, quality tools, DOE, and Bayesian optimization. The interface supports English and Korean; English is the default.

## Requirements

- Windows 11 and PowerShell 5.1
- CPython 3.10.x
- Node.js 22
- Git

Docker, WSL, administrator rights, a GPU, and an external service are not required.

## Install

```powershell
git clone https://github.com/kiwoju-git/Data-analysis-platform.git
cd Data-analysis-platform
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
```

## Run

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

Open [http://127.0.0.1:8600](http://127.0.0.1:8600), or from an approved LAN PC
open `http://<server-PC-IPv4>:8600`. The frontend binds to `0.0.0.0` and proxies
the loopback API through the same origin. Use `-LocalOnly` for loopback-only use.
**Trusted operators only:** there is no login, per-user permission or TLS; peers
can read, change and delete the shared workspace. Restrict firewall access to
approved PCs and never expose this development server to the Internet.
See [LAN setup and security boundaries](docs/trusted_lan_development.md).

## Basic Use

1. Register a file or pasted table under **Datasets**.
2. Review parsing, column types, measurement levels, roles, and data quality.
3. Choose a method under **Analysis**, review its preflight checks, and run it.
4. Use **Graphs**, **Reports**, and **Manage** to inspect or retain saved work.
5. Choose `KOR` or `ENG` beside the API status to change the interface language without resetting the current work.

Mann-Whitney accepts either a value/group layout or two numeric sample columns.
Create Factorial Design contains two-level full/fractional and General Full
designs; General Full supports 2 to 10 ordered numeric or text levels per factor.
The regression domain includes OLS, PLS Regression, and bounded exact Gaussian
Process Regression with cross-validation, uncertainty diagnostics, safe model
storage, and new-condition prediction.
PCA is available under Basic Statistics & Exploration. LHS and Bayesian
Optimization accept up to 10 factors. Full/general factorial designs still
enforce the 256-run cap; use the 12-run Plackett-Burman screening option for
7-10 two-level factors. Central Composite RSM remains limited to 5 factors.

Guides: [English tutorial](docs/statistical_twin_end_to_end_tutorial_en.md), [한국어 튜토리얼](docs/statistical_twin_end_to_end_tutorial_ko.md), and [synthetic tutorial data](examples/tutorial/README.md).

## Check

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-diagnostics
```

User workspaces, uploads, exports, and generated artifacts remain outside the Git repository. The application does not require telemetry or external data upload for its core workflow.

## Offline Backup

One application process exclusively leases each workspace, even on different
ports. Stop it normally before running the offline backup tool; do not delete
the lock file or terminate an unrelated process to bypass the lease.

```powershell
.\.venv\Scripts\python.exe .\scripts\backup_workspace.py `
  --workspace "$env:LOCALAPPDATA\DataLabStudio" `
  --output "$env:USERPROFILE\Documents\datalab-backup.zip"
.\.venv\Scripts\python.exe .\scripts\restore_workspace.py `
  --archive "$env:USERPROFILE\Documents\datalab-backup.zip" `
  --workspace "$env:LOCALAPPDATA\DataLabStudio-restored"
```

Restore only to a new or empty directory. This preserves registered uploads,
results, models, reports, and database state, without refitting or overwriting
the original workspace. The archive is not encrypted; retain it securely.
See [backup scope, verification, and recovery](docs/workspace_backup.md) and
[workspace lease](docs/workspace_lease.md). Browser downloads outside the
workspace require separate retention.
