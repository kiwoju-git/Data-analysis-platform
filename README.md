# Statistical Twin

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
This release requires matching frontend/backend API contract 20 and metadata
schema 20; existing saved artifacts are not rewritten.

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

Open [http://127.0.0.1:8600](http://127.0.0.1:8600). The backend runs at `http://127.0.0.1:8000`. Both services bind only to `127.0.0.1` by default.

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
