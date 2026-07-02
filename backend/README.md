# DataLab Studio Backend

FastAPI backend package for the local-first DataLab Studio application.

The public API is versioned under `/api/v1`.

Current Gate B0 surface:

- `GET /api/v1/health`
- `POST /api/v1/datasets`
- `POST /api/v1/datasets/paste`
- `POST /api/v1/datasets/{dataset_id}/confirm-parsing`
- `GET /api/v1/datasets/{dataset_id}/versions`
- `GET /api/v1/dataset-versions/{version_id}`
- `GET /api/v1/dataset-versions/{version_id}/schema`
- `PATCH /api/v1/dataset-versions/{version_id}/schema`
- `GET /api/v1/dataset-versions/{version_id}/rows`
- `GET /api/v1/dataset-versions/{version_id}/profile`
- `GET /api/v1/analysis-methods`
- `POST /api/v1/analysis-runs`
- `GET /api/v1/analysis-runs/{analysis_id}`
- `GET /api/v1/analysis-runs/{analysis_id}/result`
- `DELETE /api/v1/analysis-runs/{analysis_id}`
- `GET /api/v1/jobs/{job_id}`
- `DELETE /api/v1/jobs/{job_id}`

The Gate B0 slice creates immutable dataset-version metadata for delimited text files, materializes canonical JSONL rows plus a manifest, allows column metadata confirmation, and exposes bounded row preview plus an aggregate profile/preflight scan.
Delimited-text parsing confirmation supports both header rows and headerless tabular data after a leading preamble through explicit `has_header` and `data_start_row` options.
It also exposes the 6-module analysis method catalog.
`eda.descriptive` is the first executable inline method and computes real descriptive statistics from validated canonical rows for an immutable dataset version.
`eda.graphical_summary` is the second executable inline method and computes real histogram, boxplot, Q-Q, and ECDF chart-data payloads from the same canonical row source.
`eda.normality` is the third executable inline method and computes SciPy-backed Shapiro-Wilk, Anderson-Darling, and Q-Q point payloads from the same canonical row source.
`eda.equal_variances` is the fourth executable inline method and computes SciPy-backed Brown-Forsythe and Levene(mean) results from the same canonical row source.
`hypothesis.one_sample_t` is the first single-sample Gate B2 executable inline method and computes SciPy-backed one-sample t-test results from the same canonical row source.
`hypothesis.paired_t` is the first paired-design Gate B2 executable inline method and computes SciPy-backed paired t-test results from wide before/after measurement columns on the same canonical row source.
`hypothesis.one_sample_wilcoxon` is the first single-sample rank-based Gate B2 executable inline method and computes SciPy-backed signed-rank results from the same canonical row source.
`hypothesis.two_sample_t` is the first two-group Gate B2 executable inline method and computes SciPy-backed Welch-default or explicit pooled independent two-sample t-test results from the same canonical row source.
`hypothesis.mann_whitney` is the first rank-based Gate B2 executable inline method and computes SciPy-backed Mann-Whitney U results from the same canonical row source.
`hypothesis.kruskal_wallis` is the first 3-or-more-group rank-based Gate B2 executable inline method and computes SciPy-backed Kruskal-Wallis plus Dunn/Holm post-hoc results from the same canonical row source.
`hypothesis.one_way_anova` is the first ANOVA Gate B2 executable inline method and computes SciPy-backed standard one-way ANOVA plus Tukey-Kramer post-hoc results from the same canonical row source.
`hypothesis.equivalence_tost` is the first equivalence Gate B2 executable inline method and computes SciPy-backed one-sample mean TOST results from the same canonical row source.
`categorical.one_proportion` is the first categorical Gate B2 executable inline method and computes a SciPy-backed exact binomial 1-proportion test for one binary response column plus an explicit event level from the same canonical row source.
`categorical.two_proportion` is the second categorical Gate B2 executable inline method and computes a SciPy-backed Fisher exact 2-proportion test for one binary response column, exactly two usable groups, and an explicit event level from the same canonical row source.
`categorical.chi_square_association` is the third categorical Gate B2 executable inline method and computes a SciPy-backed Pearson chi-square test of independence with Cramer's V and expected-count diagnostics from the same canonical row source.
Other methods remain `planned` or `disabled` and return structured unavailable-method errors.
Schema version `5` includes dataset artifact metadata plus analysis run, artifact, and job metadata tables with status/cancel API skeletons.
The profile endpoint reads validated canonical rows, persists a raw-value-free `profile_summary` JSON artifact with SHA-256 metadata, and returns aggregate counts, canonical/profile artifact metadata, duplicate-row count, memory estimate, date/time format and timezone preflight, and warnings only, not raw value samples.
It does not create mock results.
