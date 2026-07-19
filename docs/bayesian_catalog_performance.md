# Bayesian Catalog Performance

Last updated: 2026-07-19

## Policy

`GET /api/v1/bayesian-studies` pages 20 metadata summaries, but each item is
constructed only after `_load_validated_study()` revalidates its complete Study version,
definition SHA, deterministic initial design, trials, immutable histories,
recommendations, and lifecycle relationship. This benchmark does not bypass that validator,
introduce a cache, or change API/storage meaning.

Run it with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\benchmark-bayesian-catalog.ps1 `
  -Repetitions 3
```

The script uses a temporary workspace outside the repository and deletes it on exit. It creates
real Study records and uses production observation/recommendation transitions. It does not insert
fabricated recommendations or print objective values.

## Development Measurement

- Source base SHA: `695caf2fcfb6a8336ddd29afc77d4ed22911dc63`
- Host: Windows 10 build 19045, CPython 3.10.11, CPU-only
- Date: 2026-07-19
- Page size: 20
- Page repetitions: 3; values below are medians
- Memory: `tracemalloc` Python allocation peak during each page call, not total process RSS
- Fixture build: 194.451 seconds

Profiles:

| Profile | Trials | History revisions | Recommendations |
| --- | ---: | ---: | ---: |
| small | 2 pending initial | 1 | 0 |
| medium | 20 completed initial | 21 | 0 |
| large | 100 completed total | 101 | 36 production GP/EI recommendations |

Results:

| Catalog | First-page composition | First page | Middle offset | Middle page | First-page Python peak |
| --- | --- | ---: | ---: | ---: | ---: |
| 20 Studies | 20 small | 597.932 ms | 0 | 437.274 ms | 0.076 MiB |
| 100 Studies | 1 medium + 19 small | 571.266 ms | 40 | 580.620 ms | 0.112 MiB |
| 500 Studies | 1 large + 19 small | 729.113 ms | 240 | 542.170 ms | 0.722 MiB |

The 20-Study middle page is the first page because only one page exists. Timing variability was
visible, so these numbers are descriptive development evidence rather than a CI threshold or a
Windows 11 release measurement. The large profile demonstrates that one item with 100 trials,
101 histories, and 36 recommendations increases validation allocation and first-page latency;
the current page still fully validates every selected record.

## Follow-up Boundary

A separate reviewed contract may add:

- metadata-only immutable Study summary/index records;
- name/status search and stable paging indexes;
- explicit `integrity_status=not_checked|validated` semantics;
- an immutable summary checksum tied to the full graph;
- a measured pagination latency threshold on the release host;
- full checksum/dependency validation when an exact Study is selected.

Until those relationships and recovery rules are specified, catalog validation is not cached or
silently weakened.
