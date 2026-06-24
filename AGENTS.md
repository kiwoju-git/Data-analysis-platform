# AGENTS.md

## 1. Mission and instruction precedence

Build **DataLab Studio**, a local-first statistical analysis web application.

Read these files before changing code:

1. `AGENTS.md`
2. `docs/six_module_implementation_guide.md`
3. `to_do_list.md`
4. `data_prd_addendum.md`
5. `data_prd.md`
6. The nearest nested `AGENTS.md` or `AGENTS.override.md`, if one exists

When product documents conflict, `data_prd_addendum.md` overrides `data_prd.md`. A nested instruction file may specialize rules for its directory but must not weaken security, statistical correctness, or reproducibility requirements.

Do not treat the original PRD's broad feature list as permission to implement every feature at once. Work gate-by-gate and prefer a small, correct vertical slice over a wide set of placeholders.

## 2. Fixed environment and product constraints

These are non-negotiable unless the user explicitly changes them.

- Primary OS: Windows 11
- Shell for documented commands: PowerShell
- Python: CPython 3.10.x
- Compute: CPU-only; no CUDA or required GPU dependency
- Product mode: local, single-user web app
- Default bind address: `127.0.0.1`, never `0.0.0.0`
- Backend: FastAPI
- Frontend: React + Vite + TypeScript
- Core ML: scikit-learn
- Core storage: SQLite metadata plus local workspace files
- No required Docker, WSL, Redis, administrator rights, or external service
- No external data upload, analytics, CDN, remote font, or telemetry in the core flow
- No mandatory PyCaret, Optuna, SHAP, LIME, PyTorch, or GPU package in the MVP
- No arbitrary user Python, shell command, `eval`, pickle, or joblib loading

The application must remain useful with the network disconnected after dependencies are installed.

## 3. Required working style

For every task:

1. Inspect the relevant requirements, existing code, tests, migrations, and nearby instruction files.
2. State the intended acceptance criteria in your task plan.
3. Identify statistical, privacy, compatibility, migration, and performance risks before implementation.
4. Make the smallest coherent change that completes an end-to-end behavior.
5. Add or update tests in the same change.
6. Run the narrowest relevant checks first, then the full project checks before completion.
7. Update API schemas, docs, fixtures, migrations, and exported manifest versions when behavior changes.
8. Report changed files, commands run, test results, and known limitations accurately.

Do not ask for routine implementation choices already resolved by the PRD addendum. Use the documented safe default and record assumptions in the change.

Never:

- claim tests passed without running them;
- return fabricated statistical values;
- hide failures behind broad exception handlers;
- silently sample, coerce, drop rows, change a hypothesis, or switch statistical methods;
- leave a placeholder or TODO presented as a completed feature;
- rewrite unrelated files or reformat the whole repository;
- store user data, generated workspaces, credentials, or model artifacts in Git.

## 4. Target repository layout

Prefer this monorepo layout when scaffolding. Adapt only when existing code already establishes an equivalent structure.

```text
/
├─ AGENTS.md
├─ data_prd.md
├─ data_prd_addendum.md
├─ backend/
│  ├─ pyproject.toml
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ api/v1/
│  │  ├─ core/
│  │  ├─ domain/
│  │  ├─ services/
│  │  ├─ statistics/
│  │  ├─ ml/
│  │  ├─ storage/
│  │  └─ workers/
│  └─ tests/
│     ├─ unit/
│     ├─ integration/
│     ├─ reference/
│     └─ security/
├─ frontend/
│  ├─ package.json
│  ├─ src/
│  └─ tests/
├─ scripts/
│  ├─ bootstrap.ps1
│  ├─ dev.ps1
│  ├─ test.ps1
│  └─ check.ps1
├─ docs/
└─ .github/workflows/
```

Keep domain calculations independent of FastAPI and UI code. Statistical functions must be callable and testable without starting the web server.

## 5. Windows and Python rules

- Use `pathlib.Path`; do not concatenate paths manually.
- Do not hardcode `/tmp`, `/home`, drive letters, or a developer's absolute path.
- Test paths containing spaces, Korean characters, and long filenames.
- Use UTF-8 deliberately and support UTF-8-SIG/CP949 where data ingestion requires it.
- Use `py -3.10` and `.venv\Scripts\python.exe` in PowerShell documentation.
- Do not require `bash`, `make`, `fork`, symlinks, or Unix-only signals.
- Multiprocessing code must be safe under Windows `spawn`; protect process entry points.
- Close file handles before rename/delete and account for Windows file locking.
- Keep Python syntax and dependency metadata compatible with Python 3.10.
- Do not add Python 3.11+ syntax, including `tomllib` without a compatibility path.
- Do not assume admin privileges.
- CPU jobs must cap concurrency and expose configurable time and memory budgets.

Expected initial setup pattern:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
npm --prefix .\frontend ci
```

Once repository scripts exist, use the scripts rather than duplicating commands in multiple documents.

## 6. Backend architecture rules

### API

- Version routes under `/api/v1`.
- Use typed Pydantic request/response models.
- Use dataset, analysis, model, report, and job IDs; never rely on a global mutable DataFrame.
- Page large row responses. Never serialize a full large DataFrame into one JSON response.
- Return stable machine-readable error codes and a `correlation_id`.
- Do not expose tracebacks, absolute paths, SQL, secrets, or raw cell values in client errors.
- Keep OpenAPI examples synthetic and free of sensitive data.
- Use migrations for SQLite schema changes and test upgrades from the previous schema.

### Services and domain logic

- Keep parsing, profiling, statistics, ML, persistence, and reporting in separate modules.
- Domain functions should accept explicit inputs and return typed, serializable results.
- Avoid hidden singleton state.
- Use immutable dataset versions and transformation records.
- Make writes crash-safe with temporary files and atomic replacement where supported.
- Persist raw uploads unchanged and store SHA-256 provenance.

### Long-running work

- Never run heavy pandas, scipy, statsmodels, or sklearn work directly on the async event loop.
- Use a spawn-safe worker process abstraction for CPU-bound jobs.
- Define job states as `queued`, `running`, `succeeded`, `failed`, `cancel_requested`, or `cancelled`.
- Cancellation is best effort; never mark partial output as successful.
- Limit worker count and each model's `n_jobs`.
- Clean temporary files on success, failure, cancellation, and startup recovery.
- P0 progress may use REST polling. Prefer SSE for later one-way progress; do not add WebSocket complexity without a bidirectional requirement.

## 7. Statistical correctness gates

These rules apply to every statistical feature.

- Require or infer with confirmation the variable roles, measurement levels, study design, grouping, pairing/subject ID, alternative hypothesis, alpha, missing-data policy, and multiplicity policy.
- Never select a test solely from pandas dtype.
- Never use a Shapiro-Wilk p-value as the sole automatic switch between parametric and nonparametric methods.
- Treat independence as a design assumption that software cannot prove.
- Report `n_total`, `n_used`, exclusions, group sizes, and missing-data handling.
- Return the method, human-readable rationale, assumptions checked, warnings, statistic, degrees of freedom when applicable, estimate, confidence interval, raw p-value, adjusted p-value when applicable, and effect size.
- Prefer Welch's t-test over equal-variance Student's t-test as the default independent two-group mean comparison.
- Match omnibus and post-hoc methods: Tukey after standard ANOVA, Games-Howell after Welch ANOVA, and Dunn after Kruskal-Wallis.
- Check expected cell counts before chi-square and offer Fisher exact for appropriate sparse 2x2 tables.
- Validate pairing keys for paired analyses and report incomplete pairs.
- Do not label every nonparametric result as a median difference.
- Do not interpret association, feature importance, or model explanation as causation.
- Keep internal numeric precision separate from display rounding.
- Detect empty groups, constant columns, zero variance, non-finite values, singular matrices, non-convergence, separation, and numerical overflow.
- Do not replace a failed method with a different one without an explicit warning and recorded user-visible decision.
- Use Holm as the default suggested family-wise correction; preserve raw and adjusted p-values.
- Provide effect sizes and 95% confidence intervals whenever mathematically supported.
- Generated narrative must be deterministic, qualified, and based only on structured results.

### Statistical tests

For each calculation, add:

1. a hand-checkable small fixture;
2. a reference fixture cross-checked against a trusted independent result;
3. edge cases and failure cases;
4. explicit floating-point tolerances;
5. assertions for warnings and metadata, not only numeric output.

Snapshot-only tests are insufficient for statistical code.

## 8. Missing data and transformations

- Preserve the raw data and record every transformation as a new version.
- Default inferential analyses to explicit complete-case handling unless the method specifies otherwise.
- Pairwise deletion must be labeled and its changing N made visible.
- Do not claim that a dataset is MAR or MNAR from automated inspection.
- Imputation must be an explicit transformation with method, columns, parameters, and seed.
- For ML, fit imputers and all learned preprocessing only inside the training fold.
- Show a before/after preview and affected row count for destructive transformations.
- Never use Python `eval` for formulas. Use a whitelist parser and explicit functions.
- Invalidate or mark stale any result whose source dataset version changes.

## 9. Machine-learning rules

- Split data before fitting imputers, encoders, scalers, feature selection, resampling, or target-derived transforms.
- Implement preprocessing and models as sklearn `Pipeline`/`ColumnTransformer` objects.
- Support ordinary, stratified, group-aware, and time-aware splits as required by data structure.
- Keep a true holdout set or use nested CV for unbiased tuned-model evaluation.
- Record all seeds, folds, split indices or hashes, metrics, threshold, package versions, and `n_jobs`.
- Warn on ID columns, target leakage candidates, future information, duplicate rows across splits, unseen categories, and schema drift.
- Classification reports must not rely on accuracy alone.
- MAPE must warn or be disabled when targets contain zero or near-zero values.
- Hyperparameter searches need explicit time, trial, fold, model, memory, and failure budgets.
- Model explanations must include limitations for correlated features and must not be described as causal.
- Only load artifacts produced by this application and validated by manifest version plus hash.
- Never deserialize an untrusted pickle/joblib upload.

PyCaret, Optuna, SHAP, and LIME are optional enhancements. Do not introduce them into the base install unless the active task explicitly targets their approved gate and compatibility tests exist.

## 10. Data security and privacy rules

- Bind only to `127.0.0.1` by default and keep CORS narrow.
- Do not transmit datasets, column values, file names, or derived statistics externally.
- Validate actual file type, size, dimensions, parser limits, and decompression ratio.
- Sanitize file names and prevent path traversal.
- Render cell values as text, not raw HTML.
- Defend CSV/Excel exports against formula injection for strings beginning with `=`, `+`, `-`, or `@`.
- Do not log raw records, request bodies containing data, secrets, tokens, or full query parameters.
- Redact developer errors before they reach the browser.
- Keep test data synthetic or publicly licensed.
- Store workspaces, logs, exports, and temp data outside the repository.
- Provide retention and explicit deletion behavior.
- Do not expose the local server to a LAN as a shortcut. Intranet deployment requires a separate authentication/RBAC/TLS threat model.
- Do not add an external AI call without an explicit product requirement, opt-in UX, field-level transmission preview, and audit record.

## 11. Frontend rules

- Enable TypeScript strict mode.
- Keep API types synchronized from schemas or a controlled typed client layer.
- Do not keep the entire dataset in browser state.
- Use server pagination and row/column virtualization.
- Show analysis N, filters, dataset version, missing policy, alpha, alternative, and correction before execution.
- Results should emphasize estimate, confidence interval, and effect size before p-value.
- Persist warnings in the result and exported report; do not rely only on disappearing toasts.
- Mark results stale when source data or analysis configuration changes.
- Confirm destructive transformations after showing impact.
- Use accessible labels, keyboard operation, focus handling, non-color cues, and meaningful chart descriptions.
- Preserve original variable names and provide safe display labels separately.
- Never use `dangerouslySetInnerHTML` for user data.
- Keep the core UI functional without a CDN or network request.
- Treat Korean as the default product language while keeping machine-readable codes stable in English.

A table/grid dependency must have an approved license. Do not use a non-commercial/evaluation key in a company application.

## 12. Dependency policy

Before adding a production dependency, verify and record:

- why the standard library or an existing dependency is insufficient;
- Python 3.10 or current Node LTS compatibility;
- Windows wheel/binary availability where applicable;
- CPU-only behavior;
- transitive size and startup/memory cost;
- license compatibility;
- maintenance and security posture;
- offline runtime behavior.

Rules:

- Pin direct dependencies and commit reproducible lockfiles.
- Separate optional heavy features into extras.
- Do not add GPL, AGPL, SSPL, commercial, or evaluation-only components without explicit approval.
- Do not add overlapping libraries for the same purpose.
- Do not update unrelated dependencies during a feature change.
- Do not load code from a CDN at runtime.
- Document any native prerequisite and provide a startup diagnostic.

## 13. Testing and validation commands

Create and maintain PowerShell entry points so contributors and Codex use the same workflow.

Expected commands once scripts are present:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

The full check should cover, as applicable:

```powershell
.\.venv\Scripts\python.exe -m ruff check .\backend
.\.venv\Scripts\python.exe -m ruff format --check .\backend
.\.venv\Scripts\python.exe -m mypy .\backend\app
.\.venv\Scripts\python.exe -m pytest .\backend\tests
npm --prefix .\frontend run lint
npm --prefix .\frontend run typecheck
npm --prefix .\frontend run test -- --run
npm --prefix .\frontend run build
```

Add Playwright E2E tests for the critical path: upload → schema confirmation → profile → analysis → export.

CI must include a Windows runner with Python 3.10. A Linux job may supplement it but cannot replace Windows validation.

## 14. Performance and reliability

- Benchmark on the baseline in `data_prd_addendum.md`.
- Add memory preflight before materializing large datasets.
- Never silently downsample to meet a target.
- Use vectorized operations where clear, but choose correctness and readable tested code over premature optimization.
- Avoid repeated full-file reads and repeated DataFrame copies.
- Cache only immutable results keyed by dataset version and full parameter hash.
- Invalidate caches deterministically.
- Store full-precision results; round only in presentation.
- Add regression benchmarks for parsing, profiling, and representative analyses.
- Preserve the raw file and last completed dataset version across crashes.
- Treat corrupt metadata or incomplete artifacts as explicit recovery errors, not empty successful projects.

## 15. Documentation and schema discipline

Update documentation whenever you change:

- setup or PowerShell commands;
- environment variables;
- API routes or response fields;
- SQLite schema or migration behavior;
- analysis result schema;
- pipeline/manifest version;
- export format;
- security or retention behavior;
- supported statistical assumptions or limitations.

Use requirement IDs from `data_prd_addendum.md` in tests and PR descriptions where practical.

Generated code and reports must state the method, parameters, data version/hash, software versions, seed, N/exclusions, warnings, and limitations needed for reproducibility.

## 16. Definition of done

A task is complete only when:

- its acceptance criteria are met end-to-end;
- relevant unit, reference, integration, security, and E2E tests pass;
- Windows/Python 3.10/CPU-only compatibility is preserved;
- no raw user data or secret is committed or logged;
- statistical outputs include required uncertainty, effect size, assumptions, N, warnings, and provenance;
- migrations and backward compatibility are handled;
- documentation and schemas are current;
- new dependencies passed compatibility and license review;
- there are no fake results, hidden fallbacks, unresolved critical TODOs, or ignored failing checks;
- the final report names every check that was actually run and any check that could not be run.
