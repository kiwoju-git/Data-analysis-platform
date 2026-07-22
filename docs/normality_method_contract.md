# Normality Method Contract

This contract records the implementation requirements for `eda.normality`.

## Current State

- Availability: `available`
- Method version: `0.2.0`; result schema: `2`. Stored `0.1.0`/schema 1
  results remain legacy results and are never rewritten.
- NumPy 2.2.6 and SciPy 1.15.3 are pinned in `backend/pyproject.toml`.
- Native Windows CPython 3.10.11 dependency smoke passed and generated `backend/tests/reference/fixtures/normality_scipy_reference.json`.
- The API returns real Shapiro-Wilk, SciPy Anderson-Darling critical-table
  statistics, a separately calculated Stephens approximate AD p-value, and Q-Q
  point payloads only from confirmed canonical dataset rows.

## Required Dependency Gate

The statistical dependency spike was recorded first:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-stat-deps-spike.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\check-stat-deps.ps1
```

Record native Windows results in `docs/stat_dependency_spike.md`.

After the dependency spike passed, SciPy reference output was generated from the synthetic input fixture:

```powershell
.\.venv\Scripts\python.exe .\scripts\generate_normality_reference.py
.\.venv\Scripts\python.exe .\scripts\validate_normality_reference.py
```

The input fixture is `backend/tests/reference/fixtures/normality_input.json`. It intentionally contains no expected p-values or test statistics. The generated output file is `backend/tests/reference/fixtures/normality_scipy_reference.json`.

## Supported Scope

Method ID:

- `eda.normality`

Input:

- confirmed `dataset_version_id`
- one or more numeric, non-ID columns
- optional group column only if group-level fixtures and UI are implemented in the same PR
- `filter_snapshot` using the existing AND filter engine
- options:
  - `column_ids`
  - `alpha`, default `0.05`
  - `missing_policy`, default `available_case_by_column`
  - `include_qq_points`, default `true`
  - `qq_point_limit`, bounded and deterministic

Grouped normality is omitted in this slice. Grouped execution rejects with `normality_grouping_not_supported` instead of silently pooling or fabricating groups.

## Required Result Payload

The result object should use:

- `schema_version`
- `summary_type: "normality_test"`
- `missing_policy`
- `alpha`
- `qq_plot_distribution: "standard_normal"`
- `qq_plotting_position`
- `columns`

Each column result must include:

- column metadata: `column_id`, `display_name`, `data_type`, `measurement_level`, `role`, `unit`
- N metadata: `n_total`, `n_used`, `n_missing`, `n_non_numeric`
- exclusions and warnings
- descriptive shape metadata: mean, standard deviation, skewness, kurtosis if implemented and tested
- Shapiro-Wilk result:
  - statistic
  - p-value
  - valid N range metadata
  - warning when N is greater than the documented p-value accuracy range
- Anderson-Darling result:
  - `computed`
  - statistic
  - adjusted statistic used for the p-value approximation
  - approximate p-value
  - `p_value_method: "stephens_normal_unknown_mean_variance"`
  - `p_value_is_approximate: true`
  - critical values
  - significance levels
  - decision summary by alpha
- Q-Q plot point payload when requested

The result must not automatically choose a downstream parametric or nonparametric method.

## Stable Error Codes

Use stable machine-readable error codes for at least:

- `normality_columns_required`
- `too_many_normality_columns`
- `invalid_normality_columns`
- `duplicate_normality_column`
- `normality_column_not_found`
- `normality_column_is_id`
- `normality_column_not_numeric`
- `invalid_normality_alpha`
- `invalid_normality_qq_point_limit`
- `normality_grouping_not_supported`
- `normality_insufficient_observations`

## Required Warnings

At minimum, warnings must cover:

- non-numeric values excluded
- no numeric values
- fewer than three usable observations for Shapiro-Wilk
- constant column
- Shapiro-Wilk large-N p-value limitation
- Q-Q points truncated deterministically
- normality result must not be used as an automatic method switch

## Required Tests

Backend pure statistics tests:

- hand-checkable small fixture
- reference fixture generated from the pinned SciPy version using `scripts/generate_normality_reference.py`
- Stephens p-value reference fixture generated against statsmodels 0.14.6 by
  `scripts/generate_normality_ad_pvalue_reference.py`; statsmodels is not a
  production or CI runtime dependency
- piecewise boundaries near adjusted A2 0.2, 0.34, 0.6, and 13
- missing/non-numeric exclusions
- N less than 3
- constant column
- large N warning for Shapiro-Wilk p-value limitation
- deterministic Q-Q point truncation

Backend API tests:

- registry changes only when calculation exists
- remaining planned methods still reject without fake results
- execution from confirmed dataset version
- canonical row source remains stable after raw upload mutation
- stored result retrieval validates SHA-256
- filter snapshot row freezing is included in provenance

Frontend tests:

- execution panel appears after backend marks method available
- required column selection and alpha validation
- warnings are rendered in the result panel
- `AD p (근사)` and legacy unavailable state are rendered without replacing the
  SciPy critical-value decision
- the shared Q-Q chart supports pointer, touch, roving keyboard focus,
  Arrow/Home/End navigation, Enter/Space selection, Escape clearing, and a
  text detail region

## Anderson-Darling P-value Meaning

The p-value implementation standardizes usable values using the sample mean and
sample standard deviation (`ddof=1`), computes A2 with normal log-CDF/log-SF,
and applies `A2* = A2 * (1 + 0.75/n + 2.25/n^2)`. The documented Stephens
piecewise approximation is then clamped to `[0, 1]`. Constant columns and
`n < 3` are not computed. The SciPy statistic and critical-value decision are
retained independently and are not assumed numerically identical to the
adjusted p-value statistic. Near alpha the approximate p-value and the tabular
decision can differ; both are shown. Neither Shapiro nor AD silently selects a
downstream test.

## References

- SciPy `scipy.stats.shapiro`: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.shapiro.html
- SciPy `scipy.stats.anderson`: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.anderson.html
- SciPy `scipy.stats.levene`: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.levene.html
